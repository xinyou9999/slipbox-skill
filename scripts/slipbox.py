#!/usr/bin/env python3
"""Portable Markdown-first card notes for Slipbox AgentSkills."""

from __future__ import annotations

import argparse
import contextlib
import errno
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

MAX_CONTENT_CHARS = 100_000
MAX_TAGS_PER_CARD = 3
MAX_TAG_CHARS = 64
LOCK_WAIT_SECONDS = 10.0
LOCK_STALE_SECONDS = 120.0
ID_RE = re.compile(r"^[0-9a-f]{32}$")
MERGE_JOURNAL_PREFIX = ".merge-journal-"
MERGE_RETIRED_PREFIX = ".merge-retired-"
MERGE_QUARANTINE_DIRNAME = ".merge-quarantine"


def _warn(message: str) -> None:
    """Report a non-fatal condition on stderr without failing the command."""
    print(f"warning: {message}", file=sys.stderr)


class PostCommitError(OSError):
    """A replacement/removal committed, but a later durability step failed."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def home_path() -> Path:
    raw = os.environ.get("SLIPBOX_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".slipbox"


def paths() -> tuple[Path, Path, Path, Path]:
    home = home_path()
    return home, home / "cards", home / "tags.json", home / "index.sqlite3"


def _chmod(path: Path, mode: int) -> None:
    if os.name != "nt":
        try:
            os.chmod(path, mode, follow_symlinks=False)
        except (OSError, NotImplementedError, TypeError):
            if not path.is_symlink():
                os.chmod(path, mode)


def _fsync_directory(path: Path) -> None:
    if os.name == "posix":
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _reject_symlink(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise ValueError(f"{label} must not be a symbolic link")


def secure_read_text(path: Path, label: str) -> str:
    """Open a regular file without following its final symlink where supported."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        if path.is_symlink():
            raise ValueError(f"{label} must not be a symbolic link") from error
        raise
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"{label} must be a regular file")
        with os.fdopen(fd, "r", encoding="utf-8", newline="") as handle:
            fd = -1
            return handle.read()
    finally:
        if fd >= 0:
            os.close(fd)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _reject_symlink(path, path.name)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    replaced = False
    try:
        _chmod(Path(temporary), 0o600)
        handle = os.fdopen(fd, "w", encoding="utf-8", newline="\n")
        fd = -1
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        replaced = True
        _chmod(path, 0o600)
        _fsync_directory(path.parent)
    except OSError as error:
        if replaced:
            raise PostCommitError(f"atomic replacement committed, but a post-commit durability step failed: {error}") from error
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    finally:
        if fd >= 0:
            os.close(fd)


def _atomic_copy(source: Path, destination: Path) -> None:
    """Copy a regular file to a durable atomic replacement."""
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    source_fd = os.open(source, flags)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    out_fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            raise ValueError(f"{source.name} must be a regular file")
        with contextlib.ExitStack() as stack:
            source_handle = stack.enter_context(os.fdopen(source_fd, "rb"))
            source_fd = -1
            destination_handle = stack.enter_context(os.fdopen(out_fd, "wb"))
            out_fd = -1
            shutil.copyfileobj(source_handle, destination_handle, length=1024 * 1024)
            destination_handle.flush()
            os.fsync(destination_handle.fileno())
        _chmod(Path(temporary), 0o600)
        _reject_symlink(destination, destination.name)
        os.replace(temporary, destination)
        _chmod(destination, 0o600)
        _fsync_directory(destination.parent)
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if out_fd >= 0:
            os.close(out_fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def ensure_safe_home(home: Path) -> None:
    _reject_symlink(home, "SLIPBOX_HOME")
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not home.is_dir():
        raise ValueError("SLIPBOX_HOME must be a directory")
    _chmod(home, 0o700)


def repair_permissions() -> None:
    if os.name == "nt":
        return
    home, cards, tags_path, db_path = paths()
    for directory in (home, cards):
        if directory.exists() and not directory.is_symlink() and directory.is_dir():
            _chmod(directory, 0o700)
    candidates = [tags_path, db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")]
    if cards.exists() and not cards.is_symlink():
        candidates.extend(cards.glob("*.md"))
    for candidate in candidates:
        if candidate.exists() and not candidate.is_symlink() and candidate.is_file():
            _chmod(candidate, 0o600)


def _parse_tags_text(text: str) -> dict[str, Any]:
    """Validate tag-library text; the shared path used by load_tags and journal snapshots."""
    try:
        data = json.loads(text)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid tag library: {error}") from error
    return validate_tag_library(data)


def _snapshot_card_id(relative: str) -> str | None:
    if not relative.startswith("cards/") or not relative.endswith(".md"):
        return None
    identifier = relative[len("cards/"):-len(".md")]
    return identifier if ID_RE.fullmatch(identifier) else None


def _require_regular_snapshot(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        raise ValueError("invalid merge journal index snapshot") from error
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("invalid merge journal index snapshot")
    finally:
        os.close(fd)


def _validate_merge_journal(home: Path, journal: Path, manifest_path: Path, scratch: Path) \
        -> tuple[list[tuple[Path, str]], Path | None]:
    """Parse and validate every snapshot of one journal without touching the library.

    Raises ValueError when any snapshot is not a faithful, loadable copy of an
    authoritative file, so the caller can refuse the whole journal instead of
    overwriting a healthy library with unreadable content.
    """
    manifest = json.loads(secure_read_text(manifest_path, "merge journal"))
    if (not isinstance(manifest, dict)
            or set(manifest) != {"version", "files", "index_present"}
            or isinstance(manifest.get("version"), bool)
            or manifest.get("version") != 1
            or not isinstance(manifest.get("files"), dict)
            or not isinstance(manifest.get("index_present"), bool)):
        raise ValueError("invalid merge journal")
    files = manifest["files"]
    if "tags.json" not in files or not all(
            isinstance(relative, str) and isinstance(text, str) for relative, text in files.items()):
        raise ValueError("invalid merge journal")
    tags_text = files["tags.json"]
    tag_data = _parse_tags_text(tags_text)
    targets: list[tuple[Path, str]] = [(home / "tags.json", tags_text)]
    for relative, text in files.items():
        if relative == "tags.json":
            continue
        identifier = _snapshot_card_id(relative)
        if identifier is None:
            raise ValueError("invalid merge journal path")
        candidate = scratch / f"{identifier}.md"
        # Preserve LF bytes on Windows; parse_card validates the serialized card format.
        candidate.write_bytes(text.encode("utf-8"))
        parse_card(candidate, tag_data)
        targets.append((home / relative, text))
    snapshot: Path | None = None
    if manifest["index_present"] is True:
        snapshot = journal / "index.sqlite3"
        _require_regular_snapshot(snapshot)
    return targets, snapshot


def _is_journal_directory(path: Path) -> bool:
    return not path.is_symlink() and path.is_dir()


def _retire_merge_journal(journal: Path) -> Path:
    """Close a finished journal and return the directory that is left to delete.

    Retirement is the commit marker: the journal stops matching
    `MERGE_JOURNAL_PREFIX`, so `_recover_merge_journals` can only delete the
    remains and never replays it. The rename is one atomic directory operation;
    when the rename fails, removing the manifest writes the same closed state,
    because a manifest-less journal is never replayed either.
    """
    home = journal.parent
    retired = home / f"{MERGE_RETIRED_PREFIX}{journal.name}"
    counter = 0
    while retired.exists() or retired.is_symlink():
        counter += 1
        retired = home / f"{MERGE_RETIRED_PREFIX}{journal.name}-{counter}"
    try:
        os.rename(journal, retired)
    except OSError as rename_error:
        try:
            os.unlink(journal / "manifest.json")
            _fsync_directory(journal)
        except OSError as unlink_error:
            raise ValueError(
                f"merge journal {journal.name} could not be closed and must be removed manually "
                f"({rename_error}; {unlink_error})"
            ) from rename_error
        return journal
    _fsync_directory(home)
    return retired


def _discard_journal_directory(directory: Path) -> None:
    """Delete a closed journal; a failure here is cleanup, never a rollback."""
    try:
        shutil.rmtree(directory)
        _fsync_directory(directory.parent)
    except OSError as error:
        _warn(f"could not remove the closed merge journal {directory.name} ({error}); the next command retries")


def _quarantine_merge_journal(journal: Path) -> None:
    """Move a journal that cannot be replayed out of the recovery location, keeping it whole."""
    home = journal.parent
    quarantine = home / MERGE_QUARANTINE_DIRNAME
    target = quarantine / journal.name
    try:
        quarantine.mkdir(exist_ok=True, mode=0o700)
        _chmod(quarantine, 0o700)
        counter = 0
        while target.exists() or target.is_symlink():
            counter += 1
            target = quarantine / f"{journal.name}-{counter}"
        os.rename(journal, target)
        _fsync_directory(quarantine)
        _fsync_directory(home)
    except OSError as error:
        _warn(
            f"merge journal {journal.name} cannot be replayed and could not be quarantined ({error}); "
            "manual inspection recommended"
        )
        return
    _warn(f"merge journal {journal.name} quarantined at {target}; manual inspection recommended")


def _recover_merge_journals(home: Path) -> None:
    """Replay interrupted merges, quarantine broken journals, clean closed ones.

    A journal is replayed only while it still carries both its recovery name
    (`MERGE_JOURNAL_PREFIX`) and a manifest. A journal whose snapshots do not
    validate is quarantined instead of blocking every command, and the
    authoritative library files are left byte-for-byte untouched either way.
    """
    rollbacks: list[tuple[Path, list[tuple[Path, str]], Path | None]] = []
    quarantine: list[Path] = []
    closed: list[Path] = [path for path in sorted(home.glob(f"{MERGE_RETIRED_PREFIX}*")) if _is_journal_directory(path)]
    with tempfile.TemporaryDirectory(prefix=".merge-snapshot-check-") as scratch_name:
        scratch = Path(scratch_name)
        for journal in sorted(home.glob(f"{MERGE_JOURNAL_PREFIX}*")):
            if not _is_journal_directory(journal):
                continue
            manifest_path = journal / "manifest.json"
            if not manifest_path.is_file() or manifest_path.is_symlink():
                # Without a manifest nothing was ever committed from this
                # journal, so the only safe action is cleanup.
                closed.append(journal)
                continue
            try:
                targets, snapshot = _validate_merge_journal(home, journal, manifest_path, scratch)
            except (OSError, ValueError, TypeError, UnicodeError, json.JSONDecodeError):
                quarantine.append(journal)
                continue
            rollbacks.append((journal, targets, snapshot))
    _, _, _, db_path = paths()
    for journal, targets, snapshot in rollbacks:
        try:
            for target, text in targets:
                atomic_write(target, text)
            if snapshot is not None:
                _atomic_copy(snapshot, db_path)
            else:
                try:
                    db_path.unlink()
                    _fsync_directory(home)
                except FileNotFoundError:
                    pass
        except (OSError, ValueError, TypeError):
            raise ValueError(f"unrecoverable merge journal: {journal.name}") from None
        try:
            closed.append(_retire_merge_journal(journal))
        except (OSError, ValueError) as error:
            _warn(f"merge journal {journal.name} was replayed but could not be closed ({error})")
    for journal in quarantine:
        _quarantine_merge_journal(journal)
    for directory in closed:
        _discard_journal_directory(directory)


def _open_lock_descriptor(lock_path: Path) -> int:
    """Open the persistent lock file read/write without following a final symlink."""
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as error:
        if lock_path.is_symlink():
            raise ValueError("library lock must not be a symbolic link") from error
        if lock_path.is_dir():
            raise ValueError("library lock must be a regular file") from error
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("library lock must be a regular file")
        if os.name != "nt" and hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
    except BaseException:
        os.close(fd)
        raise
    return fd


def _acquire_kernel_lock(fd: int) -> bool:
    """Try to take the exclusive kernel lock on fd; False when another holder owns it."""
    if os.name == "nt":  # pragma: no cover - Windows has no fcntl
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True
    if fcntl is None:  # pragma: no cover - defensive; POSIX always provides fcntl
        raise ValueError("no kernel file locking primitive is available on this platform")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK):
            return False
        raise
    return True


def _release_kernel_lock(fd: int) -> None:
    """Release the kernel lock; closing the descriptor also releases it."""
    if os.name == "nt":  # pragma: no cover - Windows has no fcntl
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return
    if fcntl is None:  # pragma: no cover - defensive; POSIX always provides fcntl
        return
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _record_lock_owner(fd: int) -> None:
    """Best-effort owner metadata for diagnostics; the kernel lock is authoritative."""
    payload = json.dumps({"pid": os.getpid(), "time": time.time(), "token": uuid.uuid4().hex + uuid.uuid4().hex}) + "\n"
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, payload.encode("ascii"))
        os.fsync(fd)
    except OSError:
        pass


def _lock_wait_error(lock_path: Path) -> ValueError:
    detail = ""
    try:
        age = max(0.0, time.time() - lock_path.lstat().st_mtime)
    except OSError:
        age = 0.0
    if age >= LOCK_STALE_SECONDS:
        detail = f"; lock metadata is {age:.0f}s old, inspect the recorded owner"
    return ValueError(f"library is busy; lock wait exceeded {LOCK_WAIT_SECONDS:g}s{detail}")


@contextlib.contextmanager
def library_lock(*, create_home: bool = False) -> Iterator[None]:
    home = home_path()
    if create_home:
        ensure_safe_home(home)
    elif not home.is_dir() or home.is_symlink():
        raise ValueError("library is not initialized; run init first")
    lock_path = home / ".lock"
    fd = _open_lock_descriptor(lock_path)
    acquired = False
    try:
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while not _acquire_kernel_lock(fd):
            if time.monotonic() >= deadline:
                raise _lock_wait_error(lock_path)
            time.sleep(0.05)
        acquired = True
        _record_lock_owner(fd)
        _recover_merge_journals(home)
        yield
    finally:
        try:
            if acquired:
                _release_kernel_lock(fd)
        finally:
            os.close(fd)


def empty_tags() -> dict[str, Any]:
    return {"version": 1, "tags": []}


def _prepare_library() -> None:
    home, cards, tags_path, _ = paths()
    ensure_safe_home(home)
    _reject_symlink(cards, "cards path")
    cards.mkdir(exist_ok=True, mode=0o700)
    if not cards.is_dir():
        raise ValueError("cards path must be a real directory")
    _chmod(cards, 0o700)
    _reject_symlink(tags_path, "tags.json")
    if not tags_path.exists():
        atomic_write(tags_path, json.dumps(empty_tags(), ensure_ascii=False, indent=2) + "\n")
    repair_permissions()


def initialize() -> dict[str, Any]:
    home = home_path()
    ensure_safe_home(home)
    with library_lock(create_home=True):
        _prepare_library()
        count = _rebuild_index_unlocked()["indexed"]
        repair_permissions()
    return {"status": "initialized", "home": str(home), "indexed": count}


def require_library() -> None:
    home, cards, tags_path, _ = paths()
    _reject_symlink(tags_path, "tags.json")
    if not home.is_dir() or home.is_symlink() or not cards.is_dir() or cards.is_symlink() or not tags_path.is_file():
        raise ValueError("library is not initialized; run init first")
    repair_permissions()


def key(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("tag values must be strings")
    return unicodedata.normalize("NFKC", value.strip().lstrip("#")).casefold()


def validate_tag_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("tag must be a string")
    value = unicodedata.normalize("NFKC", value.strip().lstrip("#"))
    if not value or len(value) > MAX_TAG_CHARS or any(ch in value for ch in "\r\n\0"):
        raise ValueError("tag must contain 1-64 safe characters")
    return value


def validate_tag_library(data: Any) -> dict[str, Any]:
    if (not isinstance(data, dict) or set(data) != {"version", "tags"}
            or isinstance(data.get("version"), bool) or data.get("version") != 1
            or not isinstance(data.get("tags"), list)):
        raise ValueError("invalid tag library format")
    canonical_keys: set[str] = set()
    all_keys: set[str] = set()
    for item in data["tags"]:
        if not isinstance(item, dict) or set(item) != {"name", "aliases", "description", "usage_count"}:
            raise ValueError("invalid tag entry schema")
        name = validate_tag_name(item["name"])
        if name != item["name"] or not isinstance(item["aliases"], list) or not isinstance(item["description"], str):
            raise ValueError("invalid tag entry types")
        if isinstance(item["usage_count"], bool) or not isinstance(item["usage_count"], int) or item["usage_count"] < 0:
            raise ValueError("invalid tag usage_count")
        canonical = key(name)
        if canonical in canonical_keys:
            raise ValueError("duplicate canonical tag")
        canonical_keys.add(canonical)
        for candidate in [name, *item["aliases"]]:
            normalized_name = validate_tag_name(candidate)
            if normalized_name != candidate:
                raise ValueError("tag names and aliases must be canonicalized")
            normalized = key(candidate)
            if normalized in all_keys:
                raise ValueError(f"duplicate tag or alias: {candidate}")
            all_keys.add(normalized)
    return data


def load_tags() -> dict[str, Any]:
    require_library()
    _, _, path, _ = paths()
    try:
        return _parse_tags_text(secure_read_text(path, "tags.json"))
    except (OSError, UnicodeError) as error:
        raise ValueError(f"invalid tag library: {error}") from error


def save_tags(data: dict[str, Any]) -> None:
    validate_tag_library(data)
    _, _, path, _ = paths()
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def tag_lookup(data: dict[str, Any]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for item in data["tags"]:
        for candidate in [item["name"], *item["aliases"]]:
            normalized = key(candidate)
            if normalized in lookup:
                raise ValueError(f"tag or alias collision: {candidate}")
            lookup[normalized] = item["name"]
    return lookup


def normalize_tags(values: list[str] | None, data: dict[str, Any]) -> list[str]:
    values = values or []
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError("tags must be a list of strings")
    if len(values) > MAX_TAGS_PER_CARD:
        raise ValueError(f"a card may have at most {MAX_TAGS_PER_CARD} tags")
    lookup = tag_lookup(data)
    result: list[str] = []
    for value in values:
        canonical = lookup.get(key(value))
        if canonical is None:
            raise ValueError(f"unknown tag: {value}; use tag-add explicitly")
        if canonical not in result:
            result.append(canonical)
    if len(result) > MAX_TAGS_PER_CARD:
        raise ValueError(f"a card may have at most {MAX_TAGS_PER_CARD} unique tags")
    return result


def card_path(card_id: str) -> Path:
    if not isinstance(card_id, str) or not ID_RE.fullmatch(card_id):
        raise ValueError("invalid card id")
    _, cards, _, _ = paths()
    return cards / f"{card_id}.md"


def render_card(card: dict[str, Any]) -> str:
    fields = (("id", card["id"]), ("created_at", card["created_at"]), ("updated_at", card["updated_at"]), ("tags", card["tags"]))
    frontmatter = "\n".join(f"{name}: {json.dumps(value, ensure_ascii=False)}" for name, value in fields)
    return f"---\n{frontmatter}\n---\n{card['content']}\n"


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be a UTC ISO 8601 timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError(f"{field} must be a parseable UTC timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must be UTC")
    return parsed


def parse_card(path: Path, tag_data: dict[str, Any] | None = None) -> dict[str, Any]:
    if path.suffix != ".md" or not ID_RE.fullmatch(path.stem):
        raise ValueError(f"unsafe card path: {path.name}")
    _reject_symlink(path, f"card {path.name}")
    try:
        text = secure_read_text(path, f"card {path.name}")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"cannot read card: {path.name}: {error}") from error
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError(f"invalid card frontmatter: {path.name}")
    raw_header, content = text[4:].split("\n---\n", 1)
    metadata: dict[str, Any] = {}
    for line in raw_header.splitlines():
        if ": " not in line:
            raise ValueError(f"invalid card frontmatter: {path.name}")
        name, raw = line.split(": ", 1)
        if name in metadata:
            raise ValueError(f"duplicate card metadata: {path.name}")
        try:
            metadata[name] = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError(f"invalid card frontmatter: {path.name}") from error
    required = {"id", "created_at", "updated_at", "tags"}
    if set(metadata) != required or not isinstance(metadata["id"], str) or metadata["id"] != path.stem:
        raise ValueError(f"invalid card metadata: {path.name}")
    created = _parse_utc(metadata["created_at"], "created_at")
    updated = _parse_utc(metadata["updated_at"], "updated_at")
    if updated < created:
        raise ValueError("updated_at must not precede created_at")
    if not isinstance(metadata["tags"], list) or any(not isinstance(tag, str) for tag in metadata["tags"]):
        raise ValueError(f"invalid card tags: {path.name}")
    if len(metadata["tags"]) > MAX_TAGS_PER_CARD or len(set(metadata["tags"])) != len(metadata["tags"]):
        raise ValueError(f"card tags must contain at most {MAX_TAGS_PER_CARD} unique values")
    tag_data = load_tags() if tag_data is None else tag_data
    canonical = normalize_tags(metadata["tags"], tag_data)
    if canonical != metadata["tags"]:
        raise ValueError(f"card tags must use known canonical names: {path.name}")
    metadata["content"] = content[:-1] if content.endswith("\n") else content
    validate_content(metadata["content"])
    return metadata


def all_cards(tag_data: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    require_library()
    _, cards_path, _, _ = paths()
    tag_data = load_tags() if tag_data is None else tag_data
    cards = [parse_card(path, tag_data) for path in cards_path.glob("*.md")]
    return sorted(cards, key=lambda card: (card["updated_at"], card["id"]), reverse=True)


def validate_content(content: str) -> str:
    if not isinstance(content, str):
        raise ValueError("card content must be a string")
    if len(content) > MAX_CONTENT_CHARS:
        raise ValueError(f"card content exceeds {MAX_CONTENT_CHARS} characters")
    if not content.strip():
        raise ValueError("card content must not be blank")
    return content


def _create_index(path: Path, cards: list[dict[str, Any]]) -> None:
    db = sqlite3.connect(path)
    try:
        db.executescript("""
            PRAGMA journal_mode=DELETE;
            CREATE TABLE cards (
                id TEXT PRIMARY KEY, content TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE card_tags (
                card_id TEXT NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
                tag TEXT NOT NULL, PRIMARY KEY(card_id, tag)
            );
            CREATE INDEX cards_updated ON cards(updated_at DESC);
            CREATE INDEX card_tags_tag ON card_tags(tag, card_id);
        """)
        db.executemany("INSERT INTO cards(id, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
                       [(card["id"], card["content"], card["created_at"], card["updated_at"]) for card in cards])
        db.executemany("INSERT INTO card_tags(card_id, tag) VALUES (?, ?)",
                       [(card["id"], tag) for card in cards for tag in card["tags"]])
        db.commit()
    finally:
        db.close()
    # Windows requires a writable descriptor for FlushFileBuffers/fsync,
    # even though syncing does not modify the SQLite database contents.
    with open(path, "r+b") as handle:
        os.fsync(handle.fileno())
    _chmod(path, 0o600)


def _sync_usage_counts_unlocked(cards: list[dict[str, Any]], data: dict[str, Any]) -> None:
    counts = {item["name"]: 0 for item in data["tags"]}
    for card in cards:
        for tag in card["tags"]:
            counts[tag] += 1
    changed = False
    for item in data["tags"]:
        if item["usage_count"] != counts[item["name"]]:
            item["usage_count"] = counts[item["name"]]
            changed = True
    if changed:
        save_tags(data)


def _rebuild_index_unlocked() -> dict[str, Any]:
    _prepare_library()
    home, _, _, db_path = paths()
    _reject_symlink(db_path, "index.sqlite3")
    tag_data = load_tags()
    cards = all_cards(tag_data)
    fd, temporary = tempfile.mkstemp(prefix=".index.sqlite3.", dir=home)
    if os.name != "nt" and hasattr(os, "fchmod"):
        os.fchmod(fd, 0o600)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        _create_index(temp_path, cards)
        for sidecar in (db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")):
            _reject_symlink(sidecar, sidecar.name)
            try:
                sidecar.unlink()
            except FileNotFoundError:
                pass
        os.replace(temp_path, db_path)
        _chmod(db_path, 0o600)
        _fsync_directory(home)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
    _sync_usage_counts_unlocked(cards, tag_data)
    repair_permissions()
    return {"indexed": len(cards)}


def rebuild_index() -> dict[str, Any]:
    with library_lock(create_home=True):
        return _rebuild_index_unlocked()


def ensure_index() -> None:
    _, _, _, path = paths()
    _reject_symlink(path, "index.sqlite3")
    if not path.exists():
        rebuild_index()


def refresh_derived() -> dict[str, Any]:
    return _rebuild_index_unlocked()


def _with_repair_warning(result: dict[str, Any], error: BaseException, previous: BaseException | None = None) -> dict[str, Any]:
    result = dict(result)
    result["repair_required"] = True
    details = "; ".join(str(item) for item in (previous, error) if item is not None)
    result["warning"] = f"authoritative Markdown changed, but durability or derived data needs repair; run rebuild-index and verify permissions: {details}"
    return result


def add_card(content: str, tags: list[str] | None) -> dict[str, Any]:
    with library_lock():
        require_library()
        content = validate_content(content)
        canonical = normalize_tags(tags, load_tags())
        timestamp = now()
        card = {"id": uuid.uuid4().hex, "created_at": timestamp, "updated_at": timestamp, "tags": canonical, "content": content}
        commit_warning: BaseException | None = None
        try:
            atomic_write(card_path(card["id"]), render_card(card))
        except PostCommitError as error:
            commit_warning = error
        try:
            refresh_derived()
        except (OSError, ValueError, sqlite3.Error) as error:
            return _with_repair_warning(card, error, commit_warning)
        if commit_warning is not None:
            return _with_repair_warning(card, commit_warning)
        return card


def show_card(card_id: str) -> dict[str, Any]:
    path = card_path(card_id)
    if not path.exists():
        raise ValueError(f"card not found: {card_id}")
    return parse_card(path)


def edit_card(card_id: str, content: str | None, tags: list[str] | None, clear_tags: bool = False) -> dict[str, Any]:
    if clear_tags and tags:
        raise ValueError("--clear-tags cannot be combined with --tag")
    with library_lock():
        card = show_card(card_id)
        if content is not None:
            card["content"] = validate_content(content)
        if clear_tags:
            card["tags"] = []
        elif tags is not None:
            card["tags"] = normalize_tags(tags, load_tags())
        if content is None and tags is None and not clear_tags:
            raise ValueError("edit requires content, --tag, or --clear-tags")
        card["updated_at"] = now()
        commit_warning = None
        try:
            atomic_write(card_path(card_id), render_card(card))
        except PostCommitError as error:
            commit_warning = error
        try:
            refresh_derived()
        except (OSError, ValueError, sqlite3.Error) as error:
            return _with_repair_warning(card, error, commit_warning)
        if commit_warning is not None:
            return _with_repair_warning(card, commit_warning)
        return card


def delete_card(card_id: str) -> dict[str, Any]:
    with library_lock():
        path = card_path(card_id)
        if not path.exists():
            return {"id": card_id, "deleted": False}
        _reject_symlink(path, f"card {path.name}")
        path.unlink()
        result: dict[str, Any] = {"id": card_id, "deleted": True}
        commit_warning = None
        try:
            _fsync_directory(path.parent)
        except OSError as error:
            commit_warning = PostCommitError(f"deletion committed, but directory fsync failed: {error}")
        try:
            refresh_derived()
        except (OSError, ValueError, sqlite3.Error) as error:
            return _with_repair_warning(result, error, commit_warning)
        if commit_warning is not None:
            return _with_repair_warning(result, commit_warning)
        return result


def _index_connection() -> sqlite3.Connection:
    _, _, _, db_path = paths()
    _reject_symlink(db_path, "index.sqlite3")
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    return db


def query_cards(search: str = "", tag: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
    if limit < 1 or limit > 1000 or offset < 0:
        raise ValueError("limit must be 1-1000 and offset must be non-negative")
    ensure_index()
    clauses: list[str] = []
    params: list[Any] = []
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("cards.content LIKE ? ESCAPE '\\'")
        params.append(f"%{escaped}%")
    if tag:
        canonical = normalize_tags([tag], load_tags())[0]
        clauses.append("EXISTS (SELECT 1 FROM card_tags WHERE card_tags.card_id = cards.id AND card_tags.tag = ?)")
        params.append(canonical)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    try:
        with contextlib.closing(_index_connection()) as db:
            total = db.execute(f"SELECT COUNT(*) FROM cards{where}", params).fetchone()[0]
            rows = db.execute(f"SELECT * FROM cards{where} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
            ids = [row["id"] for row in rows]
            tags_by_id = {card_id: [] for card_id in ids}
            if ids:
                placeholders = ",".join("?" for _ in ids)
                for tag_row in db.execute(f"SELECT card_id, tag FROM card_tags WHERE card_id IN ({placeholders}) ORDER BY rowid", ids):
                    tags_by_id[tag_row["card_id"]].append(tag_row["tag"])
    except sqlite3.Error:
        rebuild_index()
        return query_cards(search, tag, limit, offset)
    cards = [{"id": row["id"], "content": row["content"], "created_at": row["created_at"], "updated_at": row["updated_at"], "tags": tags_by_id[row["id"]]} for row in rows]
    return {"cards": cards, "count": total, "limit": limit, "offset": offset, "has_more": offset + len(cards) < total}


def tag_add(name: str, aliases: list[str], description: str) -> dict[str, Any]:
    with library_lock():
        data = load_tags()
        name = validate_tag_name(name)
        aliases = [validate_tag_name(alias) for alias in aliases]
        existing = tag_lookup(data)
        for candidate in [name, *aliases]:
            if key(candidate) in existing:
                raise ValueError(f"tag or alias already exists: {candidate}")
        deduped: list[str] = []
        seen = {key(name)}
        for alias in aliases:
            if key(alias) not in seen:
                seen.add(key(alias))
                deduped.append(alias)
        item = {"name": name, "aliases": deduped, "description": description.strip(), "usage_count": 0}
        data["tags"].append(item)
        save_tags(data)
        return item


def tag_list(match: str = "") -> dict[str, Any]:
    data = load_tags()
    tags = data["tags"]
    if match:
        haystack = key(match)
        tags = [item for item in tags if any(key(term) in haystack for term in [item["name"], *item["aliases"]])]
    return {"tags": tags, "count": len(tags)}


def _write_merge_journal(originals: dict[str, str]) -> Path:
    home = home_path()
    journal = home / f"{MERGE_JOURNAL_PREFIX}{uuid.uuid4().hex}"
    journal.mkdir(mode=0o700)
    _chmod(journal, 0o700)
    _, _, _, db_path = paths()
    index_present = db_path.exists()
    if index_present:
        _reject_symlink(db_path, "index.sqlite3")
        _atomic_copy(db_path, journal / "index.sqlite3")
    atomic_write(journal / "manifest.json", json.dumps(
        {"version": 1, "files": originals, "index_present": index_present}, ensure_ascii=False
    ) + "\n")
    _fsync_directory(home)
    return journal


def tag_merge(source: str, target: str) -> dict[str, Any]:
    with library_lock():
        data = load_tags()
        lookup = tag_lookup(data)
        source_name = lookup.get(key(source))
        target_name = lookup.get(key(target))
        if source_name is None or target_name is None:
            raise ValueError("source and target tags must exist")
        if source_name == target_name:
            raise ValueError("source and target must be different tags")
        cards = all_cards(data)
        changed_cards: list[dict[str, Any]] = []
        source_item = next(item for item in data["tags"] if item["name"] == source_name)
        target_item = next(item for item in data["tags"] if item["name"] == target_name)
        merged_aliases = [*target_item["aliases"], source_item["name"], *source_item["aliases"]]
        target_item["aliases"] = []
        seen_aliases = {key(target_name)}
        for alias in merged_aliases:
            if key(alias) not in seen_aliases:
                seen_aliases.add(key(alias))
                target_item["aliases"].append(alias)
        data["tags"] = [item for item in data["tags"] if item["name"] != source_name]
        for card in cards:
            if source_name in card["tags"]:
                card["tags"] = list(dict.fromkeys(target_name if value == source_name else value for value in card["tags"]))
                card["updated_at"] = now()
                changed_cards.append(card)
        _, _, tags_path, _ = paths()
        originals = {"tags.json": secure_read_text(tags_path, "tags.json")}
        for card in changed_cards:
            path = card_path(card["id"])
            originals[f"cards/{path.name}"] = secure_read_text(path, f"card {path.name}")
        journal = _write_merge_journal(originals)
        try:
            save_tags(data)
            for card in changed_cards:
                atomic_write(card_path(card["id"]), render_card(card))
            _rebuild_index_unlocked()
        except (OSError, ValueError, sqlite3.Error, TypeError) as error:
            try:
                for relative, text in originals.items():
                    atomic_write(home_path() / relative, text)
                _, _, _, db_path = paths()
                manifest = json.loads(secure_read_text(journal / "manifest.json", "merge journal"))
                if manifest["index_present"]:
                    _atomic_copy(journal / "index.sqlite3", db_path)
                else:
                    try:
                        db_path.unlink()
                        _fsync_directory(home_path())
                    except FileNotFoundError:
                        pass
                # The rollback is complete: close the journal before deleting
                # anything, so a cleanup failure cannot look like an unfinished
                # merge and can never turn into a second rollback.
                _discard_journal_directory(_retire_merge_journal(journal))
            except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError) as rollback_error:
                raise ValueError(f"tag merge failed and repair is required; journal {journal.name}: {rollback_error}") from error
            raise ValueError(f"tag merge failed; authoritative files rolled back: {error}") from error
        # Commit marker: the closed journal is written after the commit and
        # before any cleanup, so an interrupted or failing rmtree can only leave
        # remains to delete - never a journal that rolls the merge back.
        _discard_journal_directory(_retire_merge_journal(journal))
        return {"source": source_name, "target": target_name, "cards_updated": len(changed_cards)}


def tag_stats() -> dict[str, Any]:
    with library_lock():
        data = load_tags()
        cards = all_cards(data)
        _sync_usage_counts_unlocked(cards, data)
        data = load_tags()
        tags = sorted(data["tags"], key=lambda item: (-item["usage_count"], item["name"].casefold()))
        return {"tags": tags, "count": len(tags)}


def review(days: int, limit: int) -> dict[str, Any]:
    if days < 1 or limit < 1 or limit > 1000:
        raise ValueError("days must be positive and limit must be 1-1000")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cards = [card for card in all_cards() if _parse_utc(card["updated_at"], "updated_at") >= cutoff][:limit]
    return {"cards": cards, "count": len(cards), "days": days, "limit": limit}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Slipbox portable Markdown card CLI")
    _add_json_flag(root)
    sub = root.add_subparsers(dest="command", required=True)

    def command(name: str) -> argparse.ArgumentParser:
        """Register a subcommand that also accepts `--json` after its name."""
        return _add_json_flag(sub.add_parser(name))

    command("init")
    add = command("add")
    add.add_argument("content")
    add.add_argument("--tag", action="append", dest="tags")
    listing = command("list")
    listing.add_argument("--tag", default="")
    listing.add_argument("--limit", type=int, default=50)
    listing.add_argument("--offset", type=int, default=0)
    search = command("search")
    search.add_argument("query")
    search.add_argument("--tag", default="")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--offset", type=int, default=0)
    show = command("show")
    show.add_argument("id")
    edit = command("edit")
    edit.add_argument("id")
    edit.add_argument("content", nargs="?")
    edit.add_argument("--tag", action="append", dest="tags")
    edit.add_argument("--clear-tags", action="store_true")
    delete = command("delete")
    delete.add_argument("id")
    command("rebuild-index")
    tags = command("tag-list")
    tags.add_argument("--match", default="")
    create_tag = command("tag-add")
    create_tag.add_argument("name")
    create_tag.add_argument("--alias", action="append", default=[])
    create_tag.add_argument("--description", default="")
    merge = command("tag-merge")
    merge.add_argument("source")
    merge.add_argument("target")
    command("tag-stats")
    review_parser = command("review")
    review_parser.add_argument("--days", type=int, default=7)
    review_parser.add_argument("--limit", type=int, default=20)
    return root


def dispatch(args: argparse.Namespace) -> Any:
    if args.command == "init": return initialize()
    if args.command == "add": return add_card(args.content, args.tags)
    if args.command == "list": return query_cards(tag=args.tag, limit=args.limit, offset=args.offset)
    if args.command == "search": return query_cards(search=args.query, tag=args.tag, limit=args.limit, offset=args.offset)
    if args.command == "show": return show_card(args.id)
    if args.command == "edit": return edit_card(args.id, args.content, args.tags, args.clear_tags)
    if args.command == "delete": return delete_card(args.id)
    if args.command == "rebuild-index": return rebuild_index()
    if args.command == "tag-list": return tag_list(args.match)
    if args.command == "tag-add": return tag_add(args.name, args.alias, args.description)
    if args.command == "tag-merge": return tag_merge(args.source, args.target)
    if args.command == "tag-stats": return tag_stats()
    if args.command == "review": return review(args.days, args.limit)
    raise ValueError(f"unknown command: {args.command}")


def _add_json_flag(target: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Register the machine-output flag on a parser or on a subcommand parser."""
    target.add_argument("--json", action="store_true", help="emit compact single-line JSON output")
    return target


def _argv_with_literal_json(argv: list[str]) -> list[str] | None:
    """Re-read a literal `--json` as a positional value behind `--`.

    Only the first occurrence is redirected: everything after `--` is
    positional, so the token is moved to the end and the remaining options keep
    parsing normally.
    """
    if "--json" not in argv:
        return None
    index = argv.index("--json")
    return [*argv[:index], *argv[index + 1:], "--", "--json"]


def _parse_argv(argv: list[str]) -> tuple[argparse.Namespace, bool]:
    """Parse argv with `--json` as a real flag, plus a literal-positional fallback.

    `--json` is registered on the root parser and on every subcommand, so
    `cmd --json` keeps working without stripping tokens. When `--json` is meant
    as content or as a query, the flag parse fails because the positional is
    missing; the retry then reads it as a positional value behind `--`, so
    `add --json` stores the text and `search --json` searches for it instead of
    silently returning everything. Attempts parse with stderr silenced, so a
    successful fallback leaves no usage noise behind; when nothing parses, the
    original argv is parsed once more to print the real usage message.
    """
    attempts = [argv]
    literal = _argv_with_literal_json(argv)
    if literal is not None:
        attempts.append(literal)
    for candidate in attempts:
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                namespace = parser().parse_args(candidate)
            except SystemExit:
                continue
        return namespace, bool(namespace.json)
    return parser().parse_args(argv), "--json" in argv


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args, json_output = _parse_argv(raw)
        result = dispatch(args)
        print(json.dumps(result, ensure_ascii=False, indent=None if json_output else 2))
        return 0
    except (ValueError, OSError, sqlite3.Error, UnicodeError, TypeError, KeyError, OverflowError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

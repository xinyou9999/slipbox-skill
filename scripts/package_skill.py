#!/usr/bin/env python3
"""Build a local Agent Skills ZIP using an explicit, reviewed file allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
# Never replace this list with directory traversal or a repository-wide glob.
FILES = (
    "LICENSE",
    "scripts/slipbox.py",
    "references/data-format.md",
    "references/tagging-policy.md",
    "templates/tags.example.json",
    "docs/INSTALL.md",
    "docs/QUICKSTART.md",
    "docs/AI_INSTALL.md",
    "docs/capabilities.json",
)
WORKBUDDY_FIELDS = {
    "display_name": "Slipbox 卡片笔记",
    "display_name_en": "Slipbox Card Notes",
    "description_zh": "在需要记录、查找、修改或回顾本地 Markdown 卡片笔记时使用。",
    "description_en": "Use when capturing, finding, revising, or reviewing local Markdown card notes.",
    "version": VERSION,
    "author": "Slipbox contributors",
}


def build_package(language: str, target: str, output_dir: Path) -> Path:
    source = "SKILL.en.md" if language == "en" else "SKILL.md"
    payload = {}
    for source_name, destination in [(source, "SKILL.md"), *((name, name) for name in FILES)]:
        path = ROOT / source_name
        if any(part.is_symlink() for part in (path, *path.parents) if part.is_relative_to(ROOT)):
            raise ValueError(f"refusing symlink in package source: {source_name}")
        if not path.is_file():
            raise ValueError(f"missing package source: {source_name}")
        payload[f"slipbox/{destination}"] = path.read_bytes()

    if target == "workbuddy":
        skill = payload["slipbox/SKILL.md"].decode("utf-8")
        lines = skill.splitlines(keepends=True)
        if not lines or lines[0].strip() != "---":
            raise ValueError("SKILL.md must start with YAML frontmatter")
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if closing is None:
            raise ValueError("SKILL.md has no closing frontmatter delimiter")
        fields = "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in WORKBUDDY_FIELDS.items())
        payload["slipbox/SKILL.md"] = ("".join(lines[:closing]) + fields + "".join(lines[closing:])).encode("utf-8")

    payload["slipbox/PACKAGE_SHA256SUMS"] = "".join(
        f"{hashlib.sha256(content).hexdigest()}  {name.removeprefix('slipbox/')}\n"
        for name, content in sorted(payload.items())
    ).encode("utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"slipbox-{VERSION}-{target}-{language}.zip"
    descriptor, temporary = tempfile.mkstemp(prefix=".slipbox-", suffix=".zip", dir=output_dir)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, content in payload.items():
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(entry, content)
        os.replace(temporary, archive)
    finally:
        Path(temporary).unlink(missing_ok=True)
    # Artifact discovery is restricted to the requested build directory. The
    # package payload above continues to use only the reviewed explicit list.
    sums = []
    for built in sorted(output_dir.glob("*.zip")):
        if built.is_symlink() or not built.is_file():
            raise ValueError(f"checksum source must be a regular archive: {built.name}")
        sums.append(f"{hashlib.sha256(built.read_bytes()).hexdigest()}  {built.name}\n")
    descriptor, temporary = tempfile.mkstemp(prefix=".slipbox-sums-", dir=output_dir)
    os.close(descriptor)
    try:
        Path(temporary).write_text("".join(sums), encoding="utf-8", newline="\n")
        os.replace(temporary, output_dir / "SHA256SUMS")
    finally:
        Path(temporary).unlink(missing_ok=True)
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    parser.add_argument("--target", choices=("generic", "workbuddy"), default="generic")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        archive = build_package(args.language, args.target, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"package error: {exc}\n")
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

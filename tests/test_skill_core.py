import contextlib
import errno
import io
import json
import importlib.util
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "slipbox.py"


class SlipboxSkillCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "library"
        self.env = {**os.environ, "SLIPBOX_HOME": str(self.home)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, ok=True, stdin=None):
        result = subprocess.run(
            [sys.executable, str(CLI), *args, "--json"],
            cwd=ROOT,
            env=self.env,
            input=stdin,
            text=True,
            capture_output=True,
        )
        if ok and result.returncode != 0:
            self.fail(f"CLI failed ({result.returncode}): {result.stderr}\n{result.stdout}")
        if not ok:
            self.assertNotEqual(result.returncode, 0)
            return json.loads(result.stderr)
        return json.loads(result.stdout)

    def run_cli_completed(self, *args):
        """Run the CLI and keep the raw process result, so stderr warnings stay visible."""
        return subprocess.run(
            [sys.executable, str(CLI), *args, "--json"],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def run_cli_raw(self, *args):
        """Run the CLI exactly as written, without the helper's implicit --json."""
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            env=self.env,
            text=True,
            capture_output=True,
        )

    def init_with_tags(self):
        result = self.run_cli("init")
        self.assertEqual(result["status"], "initialized")
        self.run_cli("tag-add", "工作", "--alias", "work", "--description", "工作事项")
        self.run_cli("tag-add", "灵感", "--alias", "idea", "--description", "可发展的想法")

    def test_init_add_show_and_markdown_is_source_of_truth(self):
        self.init_with_tags()
        note = self.run_cli("add", "第一条中文卡片", "--tag", "work")
        self.assertEqual(note["tags"], ["工作"])
        self.assertRegex(note["id"], r"^[0-9a-f]{32}$")
        card_path = self.home / "cards" / f"{note['id']}.md"
        text = card_path.read_text(encoding="utf-8")
        self.assertIn(f'id: "{note["id"]}"', text)
        self.assertIn('tags: ["工作"]', text)
        self.assertTrue(text.endswith("第一条中文卡片\n"))
        shown = self.run_cli("show", note["id"])
        self.assertEqual(shown["content"], "第一条中文卡片")

        (self.home / "index.sqlite3").unlink()
        found = self.run_cli("search", "中文")
        self.assertEqual([card["id"] for card in found["cards"]], [note["id"]])

    def test_unknown_tags_are_rejected_and_aliases_are_normalized(self):
        self.init_with_tags()
        error = self.run_cli("add", "不能静默造标签", "--tag", "新标签", ok=False)
        self.assertIn("unknown tag", error["error"])
        card = self.run_cli("add", "别名应规范化", "--tag", "IDEA", "--tag", "work")
        self.assertEqual(card["tags"], ["灵感", "工作"])
        error = self.run_cli(
            "add", "标签太多", "--tag", "工作", "--tag", "灵感", "--tag", "第三", "--tag", "第四", ok=False
        )
        self.assertIn("at most 3", error["error"])

    def test_list_search_edit_delete_review_and_rebuild(self):
        self.init_with_tags()
        first = self.run_cli("add", "苹果计划", "--tag", "工作")
        second = self.run_cli("add", "香蕉灵感", "--tag", "idea")
        listed = self.run_cli("list", "--tag", "work")
        self.assertEqual([item["id"] for item in listed["cards"]], [first["id"]])
        found = self.run_cli("search", "香蕉")
        self.assertEqual([item["id"] for item in found["cards"]], [second["id"]])

        edited = self.run_cli("edit", first["id"], "苹果项目已完成", "--tag", "idea")
        self.assertEqual(edited["content"], "苹果项目已完成")
        self.assertEqual(edited["tags"], ["灵感"])
        self.assertEqual(edited["created_at"], first["created_at"])
        self.assertGreaterEqual(edited["updated_at"], first["updated_at"])

        review = self.run_cli("review", "--days", "30", "--limit", "10")
        self.assertEqual({item["id"] for item in review["cards"]}, {first["id"], second["id"]})
        rebuilt = self.run_cli("rebuild-index")
        self.assertEqual(rebuilt["indexed"], 2)
        deleted = self.run_cli("delete", second["id"])
        self.assertTrue(deleted["deleted"])
        self.assertFalse((self.home / "cards" / f"{second['id']}.md").exists())
        self.assertEqual(self.run_cli("list")["count"], 1)

    def test_edit_clear_tags_and_rejects_tag_combination(self):
        self.init_with_tags()
        card = self.run_cli("add", "clear me", "--tag", "工作")
        cleared = self.run_cli("edit", card["id"], "--clear-tags")
        self.assertEqual(cleared["tags"], [])
        error = self.run_cli("edit", card["id"], "--clear-tags", "--tag", "工作", ok=False)
        self.assertIn("cannot be combined", error["error"])

    def test_corrupt_index_is_atomically_rebuilt_without_json1(self):
        self.init_with_tags()
        card = self.run_cli("add", "indexed", "--tag", "工作")
        index = self.home / "index.sqlite3"
        index.write_bytes(b"not sqlite")
        rebuilt = self.run_cli("rebuild-index")
        self.assertEqual(rebuilt["indexed"], 1)
        self.assertEqual(self.run_cli("list", "--tag", "工作")["cards"][0]["id"], card["id"])
        db = sqlite3.connect(index)
        try:
            self.assertEqual(db.execute("SELECT tag FROM card_tags").fetchone()[0], "工作")
        finally:
            db.close()

    def test_strict_tag_and_card_validation_returns_json_errors(self):
        self.run_cli("init")
        bad_tag_documents = [[], {"version": 1, "tags": "bad"}, {"version": 1, "tags": [{"name": 3}]},
                             {"version": 1, "tags": [{"name": "x", "aliases": [2], "description": "", "usage_count": 0}]}]
        for document in bad_tag_documents:
            (self.home / "tags.json").write_text(json.dumps(document), encoding="utf-8")
            error = self.run_cli("tag-list", ok=False)
            self.assertIn("error", error)
        (self.home / "tags.json").write_text('{"version":1,"tags":[{"name":"工作","aliases":[],"description":"","usage_count":0}]}', encoding="utf-8")
        card_id = "a" * 32
        malformed = (
            '---\nid: "' + card_id + '"\ncreated_at: "not-a-time"\nupdated_at: "2026-01-01T00:00:00+01:00"\n'
            'tags: ["工作", 2]\n---\ntext\n'
        )
        (self.home / "cards" / f"{card_id}.md").write_text(malformed, encoding="utf-8")
        result = subprocess.run([sys.executable, str(CLI), "rebuild-index", "--json"], env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("error", json.loads(result.stderr))
        self.assertNotIn("Traceback", result.stderr)

    def test_all_card_metadata_constraints_return_structured_errors(self):
        self.run_cli("init")
        for name in ("one", "two", "three", "four"):
            self.run_cli("tag-add", name)
        card_id = "a" * 32
        card_path = self.home / "cards" / f"{card_id}.md"
        valid = {"id": card_id, "created_at": "2026-01-01T00:00:00.000Z",
                 "updated_at": "2026-01-01T00:00:00.000Z", "tags": ["one"]}
        cases = [
            ({**valid, "id": "b" * 32}, "body"),
            ({**valid, "updated_at": "not-a-time"}, "body"),
            ({**valid, "tags": [1]}, "body"),
            ({**valid, "tags": ["one", "two", "three", "four"]}, "body"),
            ({**valid, "tags": ["unknown"]}, "body"),
            (valid, "x" * 100001),
        ]
        for metadata, content in cases:
            card_path.write_text("---\n" + "\n".join(
                f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in metadata.items()
            ) + "\n---\n" + content + "\n", encoding="utf-8")
            failure = subprocess.run([sys.executable, str(CLI), "rebuild-index", "--json"], env=self.env,
                                     text=True, capture_output=True)
            self.assertEqual(failure.returncode, 2, failure.stdout + failure.stderr)
            self.assertIsInstance(json.loads(failure.stderr)["error"], str)
            self.assertNotIn("Traceback", failure.stderr)

    @unittest.skipIf(os.name == "nt", "POSIX mode bits are not enforced on Windows")
    def test_private_permissions_are_repaired_for_existing_paths(self):
        self.run_cli("init")
        card = self.run_cli("add", "private")
        for path in (self.home, self.home / "cards"):
            path.chmod(0o777)
        for path in (self.home / "tags.json", self.home / "index.sqlite3", self.home / "cards" / f"{card['id']}.md"):
            path.chmod(0o666)
        self.run_cli("rebuild-index")
        self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.home / "cards").stat().st_mode), 0o700)
        for path in (self.home / "tags.json", self.home / "index.sqlite3", self.home / "cards" / f"{card['id']}.md"):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_concurrent_tag_additions_do_not_get_lost(self):
        self.run_cli("init")
        processes = [subprocess.Popen([sys.executable, str(CLI), "tag-add", f"tag-{i}", "--json"], env=self.env,
                                      text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for i in range(12)]
        completed = []
        for process in processes:
            stdout, stderr = process.communicate()
            completed.append((process.returncode, stdout, stderr))
        failures = [(stdout, stderr) for returncode, stdout, stderr in completed if returncode != 0]
        self.assertEqual(failures, [])
        self.assertEqual({item["name"] for item in self.run_cli("tag-list")["tags"]}, {f"tag-{i}" for i in range(12)})

    def test_stale_lock_is_recovered(self):
        self.run_cli("init")
        lock = self.home / ".lock"
        lock.write_text("stale", encoding="utf-8")
        old = time.time() - 121
        os.utime(lock, (old, old))
        self.assertEqual(self.run_cli("tag-add", "recovered")["name"], "recovered")

    def test_old_live_lock_is_not_stolen_or_entered_concurrently(self):
        self.run_cli("init")
        module = self._load_cli_module()
        active = 0
        maximum_active = 0
        entered = threading.Event()

        def contender():
            nonlocal active, maximum_active
            with module.library_lock():
                active += 1
                maximum_active = max(maximum_active, active)
                entered.set()
                active -= 1

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            with module.library_lock():
                active += 1
                maximum_active = max(maximum_active, active)
                old = time.time() - module.LOCK_STALE_SECONDS - 1
                os.utime(self.home / ".lock", (old, old))
                thread = threading.Thread(target=contender)
                thread.start()
                time.sleep(0.15)
                self.assertFalse(entered.is_set())
                active -= 1
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertTrue(entered.is_set())
        self.assertEqual(maximum_active, 1)

    @unittest.skipIf(os.name == "nt", "Windows does not allow replacing an open lock file")
    def test_lock_release_does_not_delete_replacement_owner(self):
        self.run_cli("init")
        module = self._load_cli_module()
        lock = self.home / ".lock"
        replacement_token = "b" * 64
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            with module.library_lock():
                replacement = self.home / ".replacement-lock"
                replacement.write_text(json.dumps({"pid": os.getpid(), "token": replacement_token}) + "\n", encoding="ascii")
                os.replace(replacement, lock)
        self.assertTrue(lock.is_file())
        self.assertEqual(json.loads(lock.read_text(encoding="ascii"))["token"], replacement_token)

    @unittest.skipIf(_fcntl is None, "POSIX kernel locks are unavailable on this platform")
    def test_lock_is_a_kernel_lock_that_persists_and_excludes_a_second_descriptor(self):
        self.run_cli("init")
        module = self._load_cli_module()
        fcntl_module = _fcntl
        if fcntl_module is None:  # pragma: no cover - the decorator already skips this
            self.skipTest("POSIX kernel locks are unavailable on this platform")
        lock = self.home / ".lock"
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            with module.library_lock():
                second = os.open(lock, os.O_RDWR)
                try:
                    with self.assertRaises(OSError) as raised:
                        fcntl_module.flock(second, fcntl_module.LOCK_EX | fcntl_module.LOCK_NB)
                    self.assertIn(raised.exception.errno, (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK))
                finally:
                    os.close(second)
            self.assertTrue(lock.is_file(), "the lock file must persist across release")
            second = os.open(lock, os.O_RDWR)
            try:
                fcntl_module.flock(second, fcntl_module.LOCK_EX | fcntl_module.LOCK_NB)
                fcntl_module.flock(second, fcntl_module.LOCK_UN)
            finally:
                os.close(second)

    def test_lock_path_symlink_and_directory_are_refused_without_touching_the_target(self):
        self.run_cli("init")
        lock = self.home / ".lock"
        lock.unlink(missing_ok=True)
        external = Path(self.tmp.name) / "external-lock"
        external.write_text("{}\n", encoding="utf-8")
        try:
            lock.symlink_to(external)
        except (OSError, NotImplementedError):
            if os.name != "nt":
                raise
        else:
            error = self.run_cli("tag-add", "符号链接锁", ok=False)
            self.assertIn("symbolic link", error["error"])
            self.assertEqual(external.read_text(encoding="utf-8"), "{}\n")

        lock.mkdir()
        error = self.run_cli("tag-add", "目录锁", ok=False)
        self.assertIn("regular file", error["error"])
        lock.rmdir()
        self.assertEqual(self.run_cli("tag-add", "恢复")["name"], "恢复")

    def test_separate_processes_never_overlap_in_the_critical_section(self):
        self.run_cli("init")
        state = self.home / "state.json"
        state.write_text(json.dumps({"active": 0, "entered": 0, "overlap": False}), encoding="utf-8")
        child = Path(self.tmp.name) / "critsection.py"
        child.write_text(
            "import importlib.util, json, os, sys, time\n"
            "from pathlib import Path\n"
            "spec = importlib.util.spec_from_file_location('slipbox_cli', os.environ['SLIPBOX_CLI'])\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "state = Path(os.environ['SLIPBOX_STATE'])\n"
            "with module.library_lock():\n"
            "    data = json.loads(state.read_text())\n"
            "    if data['active'] != 0:\n"
            "        data['overlap'] = True\n"
            "    data['active'] += 1\n"
            "    data['entered'] += 1\n"
            "    state.write_text(json.dumps(data))\n"
            "    time.sleep(0.2)\n"
            "    data = json.loads(state.read_text())\n"
            "    data['active'] -= 1\n"
            "    state.write_text(json.dumps(data))\n",
            encoding="utf-8",
        )
        env = {**self.env, "SLIPBOX_CLI": str(CLI), "SLIPBOX_STATE": str(state)}
        children = [
            subprocess.Popen(
                [sys.executable, str(child)], cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            for _ in range(3)
        ]
        for index, process in enumerate(children):
            _, stderr = process.communicate(timeout=60)
            self.assertEqual(process.returncode, 0, f"child {index} failed: {stderr}")
        data = json.loads(state.read_text())
        self.assertEqual(data["entered"], 3)
        self.assertEqual(data["active"], 0)
        self.assertFalse(data["overlap"], "critical sections must never overlap")

    def test_release_never_removes_a_lock_file_taken_over_by_a_new_owner(self):
        self.run_cli("init")
        module = self._load_cli_module()
        lock = self.home / ".lock"
        replacement_token = "c" * 64
        real_unlink = module.os.unlink
        removals = []

        def racing_unlink(path, *args, **kwargs):
            # A new owner takes the lock file over in the window between the
            # ownership check and the removal performed by the old release path.
            if Path(path) == lock and not removals:
                replacement = self.home / ".racing-lock"
                replacement.write_text(
                    json.dumps({"pid": os.getpid(), "token": replacement_token}) + "\n", encoding="ascii"
                )
                os.replace(replacement, lock)
                removals.append(Path(path))
            return real_unlink(path, *args, **kwargs)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module.os, "unlink", side_effect=racing_unlink
        ):
            with module.library_lock():
                expected = lock.read_bytes() if os.name != "nt" else None
        self.assertEqual(removals, [], "release must not remove the lock file")
        self.assertTrue(lock.is_file(), "the lock file must persist across release")
        if expected is not None:
            self.assertEqual(lock.read_bytes(), expected, "release must not disturb lock file content")
            self.assertNotEqual(json.loads(expected)["token"], replacement_token, "release must not reach the removal step")

    def test_invalid_merge_journal_is_quarantined_without_blocking_the_library(self):
        self.init_with_tags()
        card = self.run_cli("add", "keep me", "--tag", "工作")
        tags_before = (self.home / "tags.json").read_text(encoding="utf-8")
        card_file = self.home / "cards" / f"{card['id']}.md"
        card_before = card_file.read_text(encoding="utf-8")
        valid_tags = tags_before
        broken_card = (
            "---\n" + 'id: "' + "f" * 32 + '"\n'
            'created_at: "2026-01-01T00:00:00.000Z"\nupdated_at: "not-a-time"\ntags: []\n---\nbody\n'
        )
        cases = [
            {"version": 1, "files": {"tags.json": "not-json"}, "index_present": False},
            {"version": 1, "files": {"tags.json": '{"version": 1, "tags": "bad"}'}, "index_present": False},
            {"version": 1, "files": {"tags.json": valid_tags, "cards/" + "e" * 32 + ".md": broken_card},
             "index_present": False},
            {"version": 1, "files": {"tags.json": valid_tags, "cards/not-a-card.md": valid_tags}, "index_present": False},
        ]
        for index, manifest in enumerate(cases):
            journal = self.home / f".merge-journal-{index:032x}"
            journal.mkdir(mode=0o700)
            (journal / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            completed = self.run_cli_completed("rebuild-index")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["indexed"], 1, "a bad journal must not break commands")
            self.assertIn(f"warning: merge journal {journal.name} quarantined at", completed.stderr)
            self.assertIn("manual inspection recommended", completed.stderr)
            self.assertFalse(journal.exists(), "the invalid journal must leave the recovery location")
            quarantined = self.home / ".merge-quarantine" / journal.name
            self.assertTrue(quarantined.is_dir(), "the invalid journal must be kept for inspection")
            self.assertTrue((quarantined / "manifest.json").is_file())
            self.assertEqual((self.home / "tags.json").read_text(encoding="utf-8"), tags_before)
            self.assertEqual(card_file.read_text(encoding="utf-8"), card_before)
        self.assertEqual(self.run_cli("tag-list")["count"], 2)
        self.assertEqual(self.run_cli("show", card["id"])["content"], "keep me")

    def test_journal_is_kept_intact_when_quarantine_is_impossible(self):
        self.run_cli("init")
        module = self._load_cli_module()
        tags_before = (self.home / "tags.json").read_text(encoding="utf-8")
        journal = self.home / (".merge-journal-" + "b" * 32)
        journal.mkdir(mode=0o700)
        (journal / "manifest.json").write_text(
            json.dumps({"version": 1, "files": {"tags.json": "not-json"}, "index_present": False}), encoding="utf-8"
        )
        real_rename = module.os.rename

        def failing_rename(source, destination, *args, **kwargs):
            if ".merge-quarantine" in str(destination):
                raise OSError("injected quarantine failure")
            return real_rename(source, destination, *args, **kwargs)

        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module.os, "rename", side_effect=failing_rename
        ), contextlib.redirect_stderr(stderr):
            with module.library_lock():
                pass
        message = stderr.getvalue()
        self.assertIn("could not be quarantined", message)
        self.assertTrue(journal.is_dir(), "a failed quarantine must never lose the journal")
        self.assertTrue((journal / "manifest.json").is_file())
        self.assertEqual((self.home / "tags.json").read_text(encoding="utf-8"), tags_before)
        self.assertEqual(list((self.home / ".merge-quarantine").glob("*")), [])

    def test_valid_journal_replays_while_invalid_journal_is_quarantined(self):
        self.init_with_tags()
        card = self.run_cli("add", "replayed", "--tag", "工作")
        module = self._load_cli_module()
        tags_text = (self.home / "tags.json").read_text(encoding="utf-8")
        card_file = self.home / "cards" / f"{card['id']}.md"
        card_text = card_file.read_text(encoding="utf-8")
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            journal = module._write_merge_journal({"tags.json": tags_text, f"cards/{card_file.name}": card_text})
        card_file.write_text(card_text.replace("replayed\n", "corrupted\n"), encoding="utf-8")
        bad = self.home / (".merge-journal-" + "c" * 32)
        bad.mkdir(mode=0o700)
        (bad / "manifest.json").write_text(
            json.dumps({"version": 1, "files": {"tags.json": "not-json"}, "index_present": False}), encoding="utf-8"
        )
        completed = self.run_cli_completed("rebuild-index")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn(f"warning: merge journal {bad.name} quarantined at", completed.stderr)
        self.assertEqual(card_file.read_text(encoding="utf-8"), card_text, "the valid journal must still be replayed")
        self.assertFalse(journal.exists())
        self.assertTrue((self.home / ".merge-quarantine" / bad.name).is_dir())

    def test_tag_merge_commit_outlives_journal_cleanup_failure(self):
        self.init_with_tags()
        card = self.run_cli("add", "merge me", "--tag", "灵感")
        module = self._load_cli_module()
        real_rmtree = module.shutil.rmtree

        def failing_rmtree(path, *args, **kwargs):
            name = Path(path).name
            if name.startswith(".merge-journal-") or name.startswith(".merge-retired-"):
                raise OSError("injected rmtree failure")
            return real_rmtree(path, *args, **kwargs)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module.shutil, "rmtree", side_effect=failing_rmtree
        ):
            merged = module.tag_merge("灵感", "工作")
        self.assertEqual(merged["cards_updated"], 1)
        self.assertEqual(list(self.home.glob(".merge-journal-*")), [],
                         "the commit marker must retire the journal before cleanup")
        retired = list(self.home.glob(".merge-retired-*"))
        self.assertEqual(len(retired), 1, "an unremovable journal must stay retired, not replayable")
        card_file = self.home / "cards" / f"{card['id']}.md"
        self.assertIn("工作", card_file.read_text(encoding="utf-8"))
        self.assertEqual(self.run_cli("rebuild-index")["indexed"], 1)
        self.assertEqual(self.run_cli("show", card["id"])["tags"], ["工作"])
        self.assertEqual([item["name"] for item in self.run_cli("tag-list")["tags"]], ["工作"])
        self.assertEqual(list(self.home.glob(".merge-retired-*")), [], "the retired journal is only cleaned up")

    def test_closed_journals_are_only_cleaned_up_never_replayed(self):
        self.init_with_tags()
        card = self.run_cli("add", "committed new", "--tag", "工作")
        module = self._load_cli_module()
        tags_text = (self.home / "tags.json").read_text(encoding="utf-8")
        card_file = self.home / "cards" / f"{card['id']}.md"
        card_text = card_file.read_text(encoding="utf-8")
        stale = card_text.replace("committed new\n", "OLD-PRE-MERGE\n")
        self.assertIn("OLD-PRE-MERGE", stale)
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            journal = module._write_merge_journal({"tags.json": tags_text, f"cards/{card_file.name}": stale})
            retired = self.home / f".merge-retired-{journal.name}"
            os.rename(journal, retired)
        self.assertTrue(retired.is_dir())
        orphan = self.home / (".merge-journal-" + "a" * 32)
        orphan.mkdir(mode=0o700)
        (orphan / "manifest.json.partial").write_text("{}", encoding="utf-8")

        self.run_cli("rebuild-index")
        shown = self.run_cli("show", card["id"])
        self.assertEqual(shown["content"], "committed new", "a closed journal must never roll the library back")
        self.assertEqual(shown["tags"], ["工作"])
        self.assertEqual((self.home / "tags.json").read_text(encoding="utf-8"), tags_text)
        self.assertEqual(card_file.read_text(encoding="utf-8"), card_text)
        self.assertFalse(retired.exists(), "the retired journal must be cleaned up")
        self.assertFalse(orphan.exists(), "a manifest-less journal is closed and must only be cleaned up")
        self.assertEqual([path.name for path in self.home.glob(".merge-*")], [])

    def test_valid_merge_journal_is_still_applied_and_removed(self):
        self.init_with_tags()
        card = self.run_cli("add", "journaled", "--tag", "工作")
        module = self._load_cli_module()
        tags_text = (self.home / "tags.json").read_text(encoding="utf-8")
        card_file = self.home / "cards" / f"{card['id']}.md"
        card_text = card_file.read_text(encoding="utf-8")
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}):
            journal = module._write_merge_journal({"tags.json": tags_text, f"cards/{card_file.name}": card_text})
        self.assertTrue(journal.is_dir())
        card_file.write_text('---\nid: "' + card["id"] + '"\ncreated_at: "2026-01-01T00:00:00.000Z"\n'
                             'updated_at: "2026-01-01T00:00:00.000Z"\ntags: []\n---\ncorrupted\n', encoding="utf-8")
        self.assertEqual(self.run_cli("add", "after recovery")["content"], "after recovery")
        self.assertEqual(card_file.read_text(encoding="utf-8"), card_text)
        self.assertFalse(journal.exists())
        self.assertEqual(self.run_cli("list")["count"], 2)

    def _load_cli_module(self):
        spec = importlib.util.spec_from_file_location("slipbox_skill_cli", CLI)
        if spec is None or spec.loader is None:
            self.fail("could not load CLI module")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_markdown_commit_reports_repair_required_when_index_refresh_fails(self):
        self.init_with_tags()
        module = self._load_cli_module()
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module, "refresh_derived", side_effect=sqlite3.DatabaseError("injected")
        ):
            result = module.add_card("authoritative", ["工作"])
        self.assertTrue(result["repair_required"])
        self.assertIn("warning", result)
        self.assertTrue((self.home / "cards" / f"{result['id']}.md").is_file())

    def test_add_reports_committed_card_when_post_replace_chmod_fails(self):
        self.init_with_tags()
        module = self._load_cli_module()
        real_chmod = module._chmod

        def injected(path, mode):
            if path.parent == self.home / "cards" and path.suffix == ".md" and not path.name.startswith("."):
                raise OSError("injected chmod failure")
            return real_chmod(path, mode)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(module, "_chmod", side_effect=injected):
            result = module.add_card("committed despite chmod", ["工作"])
        self.assertTrue(result["repair_required"])
        self.assertIn("chmod failure", result["warning"])
        tags = json.loads((self.home / "tags.json").read_text(encoding="utf-8"))
        self.assertEqual(module.parse_card(self.home / "cards" / f"{result['id']}.md", tags)["content"], "committed despite chmod")

    def test_add_pre_replace_failure_is_a_normal_failure(self):
        self.init_with_tags()
        module = self._load_cli_module()
        real_replace = module.os.replace

        def injected(source, destination):
            destination = Path(destination)
            if destination.parent == self.home / "cards" and destination.suffix == ".md":
                raise OSError("injected pre-commit replace failure")
            return real_replace(source, destination)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module.os, "replace", side_effect=injected
        ):
            with self.assertRaisesRegex(OSError, "pre-commit replace failure"):
                module.add_card("not committed", ["工作"])
        self.assertEqual(list((self.home / "cards").glob("*.md")), [])

    def test_edit_reports_committed_card_when_post_replace_directory_fsync_fails(self):
        self.init_with_tags()
        card = self.run_cli("add", "before", "--tag", "工作")
        module = self._load_cli_module()
        real_fsync_directory = module._fsync_directory

        def injected(path):
            if path == self.home / "cards":
                raise OSError("injected directory fsync failure")
            return real_fsync_directory(path)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module, "_fsync_directory", side_effect=injected
        ):
            result = module.edit_card(card["id"], "after", None)
        self.assertEqual(result["id"], card["id"])
        self.assertTrue(result["repair_required"])
        self.assertIn("fsync failure", result["warning"])
        tags = json.loads((self.home / "tags.json").read_text(encoding="utf-8"))
        self.assertEqual(module.parse_card(self.home / "cards" / f"{card['id']}.md", tags)["content"], "after")

    def test_delete_reports_committed_deletion_when_directory_fsync_fails(self):
        self.init_with_tags()
        card = self.run_cli("add", "delete me")
        module = self._load_cli_module()
        real_fsync_directory = module._fsync_directory

        def injected(path):
            if path == self.home / "cards":
                raise OSError("injected delete fsync failure")
            return real_fsync_directory(path)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module, "_fsync_directory", side_effect=injected
        ):
            result = module.delete_card(card["id"])
        self.assertEqual(result["id"], card["id"])
        self.assertTrue(result["deleted"])
        self.assertTrue(result["repair_required"])
        self.assertFalse((self.home / "cards" / f"{card['id']}.md").exists())

    def test_content_round_trip_preserves_user_whitespace(self):
        self.run_cli("init")
        original = "  leading\nbody\n\n  "
        card = self.run_cli("add", original)
        self.assertEqual(card["content"], original)
        self.assertEqual(self.run_cli("show", card["id"])["content"], original)
        edited = "\n\t edited with edges \t\n"
        result = self.run_cli("edit", card["id"], edited)
        self.assertEqual(result["content"], edited)
        self.assertEqual(self.run_cli("show", card["id"])["content"], edited)

    def test_raw_content_limit_counts_leading_and_trailing_whitespace(self):
        self.run_cli("init")
        tags = self.home / "tags.json"
        tags.write_text('{"version": 1, "tags": []}\n', encoding="utf-8")
        if os.name == "nt":
            module = self._load_cli_module()
            with self.assertRaisesRegex(ValueError, "exceeds 100000"):
                module.validate_content("x" + " " * 100000)
        else:
            error = self.run_cli("add", "x" + " " * 100000, ok=False)
            self.assertIn("exceeds 100000", error["error"])
        card_id = "c" * 32
        card = self.home / "cards" / f"{card_id}.md"
        card.write_bytes(
            ('---\nid: "' + card_id + '"\ncreated_at: "2026-01-01T00:00:00.000Z"\n'
             'updated_at: "2026-01-01T00:00:00.000Z"\ntags: []\n---\n' + " " * 100001 + "\n").encode("utf-8")
        )
        error = self.run_cli("rebuild-index", ok=False)
        self.assertIn("exceeds 100000", error["error"])

    @unittest.skipIf(os.name == "nt", "POSIX mode bits are not enforced on Windows")
    def test_sqlite_rebuild_never_unlinks_secure_temporary_descriptor(self):
        self.run_cli("init")
        module = self._load_cli_module()
        real_unlink = module.os.unlink

        def guarded_unlink(path, *args, **kwargs):
            candidate = Path(path)
            if candidate.parent == self.home and candidate.name.startswith(".index.sqlite3.") and candidate.exists():
                raise AssertionError("temporary SQLite descriptor was unlinked before use")
            return real_unlink(path, *args, **kwargs)

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module.os, "unlink", side_effect=guarded_unlink
        ):
            result = module.rebuild_index()
        self.assertEqual(result["indexed"], 0)
        self.assertEqual(stat.S_IMODE((self.home / "index.sqlite3").stat().st_mode), 0o600)

    def test_merge_journal_manifest_rejects_extra_fields_and_unsafe_card_names(self):
        self.run_cli("init")
        module = self._load_cli_module()
        cases = [
            {"version": 1, "files": {"tags.json": "{}"}, "index_present": False, "extra": 1},
            {"version": 2, "files": {"tags.json": "{}"}, "index_present": False},
            {"version": 1, "files": {"tags.json": "{}", "cards/not-a-card.md": "bad"}, "index_present": False},
            {"version": 1, "files": {"tags.json": "{}", "cards/../tags.json": "bad"}, "index_present": False},
            {"version": 1, "files": {"tags.json": "{}"}, "index_present": 1},
        ]
        for index, manifest in enumerate(cases):
            journal = self.home / f".merge-journal-{index:032x}"
            journal.mkdir(mode=0o700)
            (journal / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            stderr = io.StringIO()
            with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), contextlib.redirect_stderr(stderr):
                module._recover_merge_journals(self.home)
            self.assertIn(f"warning: merge journal {journal.name} quarantined at", stderr.getvalue())
            self.assertFalse(journal.exists())
            self.assertTrue((self.home / ".merge-quarantine" / journal.name).is_dir())

    def test_merge_journal_requires_regular_index_snapshot(self):
        self.run_cli("init")
        module = self._load_cli_module()
        journal = self.home / (".merge-journal-" + "d" * 32)
        journal.mkdir(mode=0o700)
        manifest = {"version": 1, "files": {"tags.json": (self.home / "tags.json").read_text()}, "index_present": True}
        (journal / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (journal / "index.sqlite3").mkdir()
        stderr = io.StringIO()
        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), contextlib.redirect_stderr(stderr):
            module._recover_merge_journals(self.home)
        self.assertIn(f"warning: merge journal {journal.name} quarantined at", stderr.getvalue())
        self.assertFalse(journal.exists())
        self.assertTrue((self.home / ".merge-quarantine" / journal.name / "index.sqlite3").is_dir())

    def test_tag_merge_rolls_back_authoritative_files_on_rebuild_failure(self):
        self.init_with_tags()
        card = self.run_cli("add", "merge rollback", "--tag", "灵感")
        before_tags = (self.home / "tags.json").read_text(encoding="utf-8")
        before_card = (self.home / "cards" / f"{card['id']}.md").read_text(encoding="utf-8")
        module = self._load_cli_module()
        original_rebuild = module._rebuild_index_unlocked

        def fail_after_rebuild():
            original_rebuild()
            raise sqlite3.DatabaseError("injected after index replacement")

        with mock.patch.dict(os.environ, {"SLIPBOX_HOME": str(self.home)}), mock.patch.object(
            module, "_rebuild_index_unlocked", side_effect=fail_after_rebuild
        ):
            with self.assertRaises(ValueError):
                module.tag_merge("灵感", "工作")
        self.assertEqual((self.home / "tags.json").read_text(encoding="utf-8"), before_tags)
        self.assertEqual((self.home / "cards" / f"{card['id']}.md").read_text(encoding="utf-8"), before_card)
        db = sqlite3.connect(self.home / "index.sqlite3")
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM card_tags WHERE tag = ?", ("灵感",)).fetchone()[0], 1)
        finally:
            db.close()

    @unittest.skipIf(os.name == "nt", "symlink semantics differ on Windows")
    def test_symlinked_home_ancestor_is_allowed(self):
        real_parent = Path(self.tmp.name) / "real-parent"
        real_parent.mkdir()
        linked_parent = Path(self.tmp.name) / "linked-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        self.env["SLIPBOX_HOME"] = str(linked_parent / "library")
        self.assertEqual(self.run_cli("init")["status"], "initialized")
        self.assertEqual(self.run_cli("add", "through ancestor")["content"], "through ancestor")

    def test_default_library_directory_uses_public_project_name(self):
        with tempfile.TemporaryDirectory() as home:
            home_variable = "USERPROFILE" if os.name == "nt" else "HOME"
            env = {**os.environ, home_variable: home}
            env.pop("SLIPBOX_HOME", None)
            result = subprocess.run(
                [sys.executable, str(CLI), "init", "--json"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(home) / ".slipbox" / "cards").is_dir())

    def test_skill_runs_from_resolved_absolute_path_in_install_layouts(self):
        for relative in (Path(".hermes/skills/slipbox"), Path(".openclaw/skills/slipbox")):
            root = Path(self.tmp.name) / relative
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            env = {**os.environ, "SLIPBOX_HOME": str(Path(self.tmp.name) / (relative.parts[0] + "-library"))}
            script = root.resolve() / "scripts" / "slipbox.py"
            unrelated = Path(self.tmp.name) / "unrelated"
            unrelated.mkdir(exist_ok=True)
            def invoke(*args):
                completed = subprocess.run([sys.executable, str(script), *args, "--json"], cwd=unrelated, env=env,
                                           text=True, capture_output=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)
            invoke("init")
            invoke("tag-add", "portable")
            invoke("add", "smoke", "--tag", "portable")
            self.assertEqual(invoke("list")["count"], 1)
            self.assertEqual(invoke("rebuild-index")["indexed"], 1)

    def test_tag_list_stats_candidate_matching_and_merge_rewrite_cards(self):
        self.init_with_tags()
        first = self.run_cli("add", "work 项目推进", "--tag", "work")
        second = self.run_cli("add", "另一个工作想法", "--tag", "工作", "--tag", "idea")

        tags = self.run_cli("tag-list", "--match", "这是一个 work 项目 idea")
        self.assertEqual([tag["name"] for tag in tags["tags"]], ["工作", "灵感"])
        stats = self.run_cli("tag-stats")
        counts = {item["name"]: item["usage_count"] for item in stats["tags"]}
        self.assertEqual(counts, {"工作": 2, "灵感": 1})

        merged = self.run_cli("tag-merge", "灵感", "工作")
        self.assertEqual(merged["source"], "灵感")
        self.assertEqual(merged["target"], "工作")
        self.assertEqual(self.run_cli("show", second["id"])["tags"], ["工作"])
        tag_names = [item["name"] for item in self.run_cli("tag-list")["tags"]]
        self.assertEqual(tag_names, ["工作"])
        self.assertIn("idea", self.run_cli("tag-list")["tags"][0]["aliases"])
        self.assertEqual(self.run_cli("show", first["id"])["tags"], ["工作"])

    def test_path_traversal_is_rejected_and_content_is_never_executed(self):
        self.init_with_tags()
        marker = self.home / "executed"
        payload = f'$(touch "{marker}") <script>alert(1)</script>'
        card = self.run_cli("add", payload, "--tag", "工作")
        self.assertFalse(marker.exists())
        self.assertEqual(self.run_cli("show", card["id"])["content"], payload)
        error = self.run_cli("show", "../tags", ok=False)
        self.assertIn("invalid card id", error["error"])

    @unittest.skipIf(os.name == "nt", "creating symlinks requires Windows Developer Mode or elevation")
    def test_symlinked_metadata_and_index_files_are_rejected(self):
        self.run_cli("init")
        external = Path(self.tmp.name) / "external"
        external.write_text("{}", encoding="utf-8")
        tags_path = self.home / "tags.json"
        tags_path.unlink()
        tags_path.symlink_to(external)
        error = self.run_cli("tag-list", ok=False)
        self.assertIn("symbolic link", error["error"])

        tags_path.unlink()
        tags_path.write_text('{"version": 1, "tags": []}\n', encoding="utf-8")
        index_path = self.home / "index.sqlite3"
        index_path.unlink()
        index_path.symlink_to(external)
        error = self.run_cli("list", ok=False)
        self.assertIn("symbolic link", error["error"])

    def test_json_flag_literal_add_content_is_stored_verbatim(self):
        self.init_with_tags()
        completed = self.run_cli_raw("add", "--json", "--tag", "工作")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        card = json.loads(completed.stdout)
        self.assertEqual(card["content"], "--json")
        shown = self.run_cli("show", card["id"])
        self.assertEqual(shown["content"], "--json")
        self.assertEqual(shown["tags"], ["工作"])

    def test_json_flag_literal_search_query_never_returns_everything(self):
        self.init_with_tags()
        self.run_cli("add", "苹果", "--tag", "工作")
        self.run_cli("add", "香蕉", "--tag", "灵感")
        self.assertEqual(self.run_cli("list")["count"], 2)
        completed = self.run_cli_raw("search", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        found = json.loads(completed.stdout)
        self.assertEqual(found["cards"], [], "a literal --json query must not silently match every card")
        self.assertEqual(found["count"], 0)

    def test_repository_contains_portable_skill_assets(self):
        self.assertTrue(any((ROOT / name).is_file() for name in ("README.en.md", "README.zh-CN.md")))
        self.assertTrue((ROOT / "SKILL.en.md").is_file())
        self.assertTrue((ROOT / "LICENSE").is_file())
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: slipbox\ndescription:"))
        frontmatter = skill.split("---", 2)[1]
        self.assertNotIn("platforms:", frontmatter)
        self.assertIn("最多 3 个", skill)
        self.assertIn("先读标签库", skill)
        self.assertIn("{baseDir}", skill)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        # Both the private bilingual layout and the English-first public tree
        # must expose installation and the actual library-selection contract.
        # Legacy Web/API wording is not a requirement of the exported Skill.
        self.assertIn("docs/INSTALL.md", readme)
        self.assertIn("SLIPBOX_HOME", readme)
        self.assertTrue((ROOT / "templates" / "tags.example.json").is_file())
        self.assertTrue((ROOT / "references" / "tagging-policy.md").is_file())
        self.assertTrue((ROOT / "references" / "data-format.md").is_file())
        self.assertIn(".smoke-slipbox/", (ROOT / ".gitignore").read_text(encoding="utf-8"))
        self.assertFalse((ROOT / ".smoke-slipbox").exists())
        data_format = (ROOT / "references" / "data-format.md").read_text(encoding="utf-8")
        self.assertIn("every directory", data_format)
        self.assertIn("`0700`", data_format)
        self.assertIn("every regular file", data_format)
        self.assertIn("`0600`", data_format)


if __name__ == "__main__":
    unittest.main()

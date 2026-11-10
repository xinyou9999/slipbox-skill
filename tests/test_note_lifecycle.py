import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('lifecycle_core', Path(__file__).resolve().parents[1] / 'scripts/slipbox.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'SLIPBOX_HOME': self.temp.name})
        self.env.start()
        core.initialize()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_delete_restore_and_explicit_purge(self):
        original = core.add_card('keep me', [])
        result = core.delete_card(original['id'], original['updated_at'])
        self.assertTrue(result['deleted'])
        self.assertTrue(result['trashed'])
        self.assertEqual(core.query_cards()['count'], 0)
        trash = core.trash_list()['cards'][0]
        self.assertEqual(trash['content'], 'keep me')
        restored = core.restore_card(original['id'], trash['updated_at'])
        self.assertEqual(restored['id'], original['id'])
        self.assertEqual(restored['created_at'], original['created_at'])
        self.assertGreater(restored['updated_at'], original['updated_at'])
        self.assertEqual(core.trash_list()['count'], 0)
        core.delete_card(original['id'], restored['updated_at'])
        with self.assertRaises(ValueError):
            core.purge_card(original['id'], restored['updated_at'])
        self.assertTrue(core.purge_card(original['id'], restored['updated_at'], True)['purged'])
        self.assertFalse(list((Path(self.temp.name) / 'history').rglob('*.json')))

    def test_revision_conflict_and_restore_conflict(self):
        card = core.add_card('one', [])
        edited = core.edit_card(card['id'], 'two', None, expected_updated_at=card['updated_at'])
        with self.assertRaises(ValueError):
            core.edit_card(card['id'], 'stale', None, expected_updated_at=card['updated_at'])
        core.delete_card(card['id'], edited['updated_at'])
        core.atomic_write(core.card_path(card['id']), core.render_card(card))
        with self.assertRaisesRegex(ValueError, 'conflict'):
            core.restore_card(card['id'], edited['updated_at'])
        self.assertEqual(core.show_card(card['id'])['content'], 'one')

    def test_history_restores_without_destroying_later_version(self):
        card = core.add_card('one', [])
        edited = core.edit_card(card['id'], 'two', None)
        version = core.history(card['id'])['versions'][0]
        restored = core.restore_version(card['id'], version['version_id'], edited['updated_at'])
        self.assertEqual(restored['content'], 'one')
        self.assertEqual({v['card']['content'] for v in core.history(card['id'])['versions']}, {'one', 'two'})
        with self.assertRaises(ValueError):
            core.restore_version(card['id'], version['version_id'], edited['updated_at'])

    def test_tag_merge_keeps_history_and_trash_restorable(self):
        core.tag_add('old', [], '')
        core.tag_add('new', [], '')
        card = core.add_card('a', ['old'])
        other = core.add_card('b', ['old'])
        core.delete_card(other['id'])
        core.tag_merge('old', 'new')
        version = core.history(card['id'])['versions'][0]
        self.assertEqual(version['card']['tags'], ['old'])
        active = core.show_card(card['id'])
        self.assertEqual(core.restore_version(card['id'], version['version_id'], active['updated_at'])['tags'], ['new'])
        self.assertEqual(core.restore_card(other['id'], other['updated_at'])['tags'], ['new'])

    def test_interrupted_transaction_recovers_before_next_write(self):
        card = core.add_card('one', [])
        target = core.card_path(card['id'])
        before = core.secure_read_text(target, 'card')
        core.atomic_write(Path(self.temp.name) / '.lifecycle-journal.json', json.dumps({'version': 1, 'files': {f'cards/{card["id"]}.md': before}}))
        core.atomic_write(target, core.render_card({**card, 'content': 'partial'}))
        core.add_card('next', [])
        self.assertEqual(core.show_card(card['id'])['content'], 'one')

    def test_transaction_rolls_back_on_failure(self):
        card = core.add_card('one', [])
        core.delete_card(card['id'])
        real = core.atomic_write
        def fail_once(path, text):
            if path == core.card_path(card['id']):
                raise OSError('disk full')
            return real(path, text)
        with mock.patch.object(core, 'atomic_write', side_effect=fail_once):
            with self.assertRaises(OSError):
                core.restore_card(card['id'], card['updated_at'])
        self.assertEqual(core.trash_list()['count'], 1)
        self.assertFalse(core.card_path(card['id']).exists())

    def test_filter_alias_exclusions_and_untagged(self):
        core.tag_add('work', ['w'], '')
        tagged = core.add_card('find me', ['work'])
        blank = core.add_card('find me too', [])
        self.assertEqual([c['id'] for c in core.query_cards(untagged=True)['cards']], [blank['id']])
        self.assertEqual([c['id'] for c in core.search_candidates(['find'], exclude_tags=['w'])['cards']], [blank['id']])

    def test_paths_are_rejected(self):
        for operation in (core.history, core.delete_card):
            with self.assertRaises(ValueError):
                operation('../outside')
        with self.assertRaises(ValueError):
            core._transaction_target('cards/../../outside')

    def test_two_processes_cannot_apply_the_same_revision(self):
        card = core.add_card('start', [])
        script = str(Path(__file__).resolve().parents[1] / 'scripts/slipbox.py')
        jobs = [subprocess.Popen([sys.executable, script, 'edit', card['id'], body, '--expected', card['updated_at'], '--json'],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                for body in ['writer one', 'writer two']]
        results = [job.communicate(timeout=20) for job in jobs]
        self.assertEqual(sorted(job.returncode for job in jobs), [0, 2])
        self.assertEqual(core.history(card['id'])['count'], 1)
        self.assertIn(core.show_card(card['id'])['content'], ['writer one', 'writer two'])

    def test_process_exit_during_transaction_is_recovered(self):
        card = core.add_card('before crash', [])
        script = str(Path(__file__).resolve().parents[1] / 'scripts/slipbox.py')
        code = '''import importlib.util, os, sys
spec=importlib.util.spec_from_file_location('core',sys.argv[1])
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
card=c.show_card(sys.argv[2]);card['content']='partial write'
real=c._apply_text_files
def crash(files):
    real(files)
    os._exit(17)
c._apply_text_files=crash
with c.library_lock():
    c._commit_text_files({'cards/'+card['id']+'.md':c.render_card(card)})
'''
        result = subprocess.run([sys.executable, '-c', code, script, card['id']], capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 17)
        self.assertTrue((Path(self.temp.name) / '.lifecycle-journal.json').exists())
        core.initialize()
        self.assertEqual(core.show_card(card['id'])['content'], 'before crash')
        self.assertFalse((Path(self.temp.name) / '.lifecycle-journal.json').exists())

    def test_invalid_recovery_snapshot_never_overwrites_authoritative_files(self):
        card = core.add_card('original', [])
        before = core.card_path(card['id']).read_bytes()
        journal = Path(self.temp.name) / '.lifecycle-journal.json'
        journal.write_text(json.dumps({'version': 1, 'files': {f'cards/{card["id"]}.md': 'invalid'}}), encoding='utf-8')
        with self.assertRaises(ValueError):
            core.initialize()
        self.assertEqual(core.card_path(card['id']).read_bytes(), before)

    def test_retained_directories_reject_symlinks(self):
        card = core.add_card('private', [])
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        link = Path(self.temp.name) / 'history'
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('symlink creation is unavailable')
        with self.assertRaises(ValueError):
            core.edit_card(card['id'], 'blocked', None)
        self.assertEqual(core.show_card(card['id'])['content'], 'private')
        self.assertFalse(list(outside.iterdir()))


if __name__ == '__main__':
    unittest.main()

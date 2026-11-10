import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location('portability_core', Path(__file__).resolve().parents[1] / 'scripts/slipbox.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / 'library'
        self.env = mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(self.library)})
        self.env.start()
        core.initialize()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def source(self, name, text):
        path = self.root / name
        path.write_text(text, encoding='utf-8')
        return str(path)

    def snapshot(self):
        return {str(p.relative_to(self.library)): p.read_bytes() for p in self.library.rglob('*') if p.is_file()}

    def test_complete_backup_roundtrip_preserves_ids_dates_vocabulary_history_trash(self):
        core.tag_add('research', ['study'], 'Preserved definition')
        card = core.add_card('first', ['study'])
        changed = core.edit_card(card['id'], 'second', None)
        deleted = core.add_card('discarded', ['research'])
        core.delete_card(deleted['id'])
        output = str(self.root / 'backup.json')
        core.export_cards('backup', output)
        destination = self.root / 'other'
        with mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(destination)}):
            core.initialize()
            preview = core.import_preview(output)
            self.assertEqual(preview['new_count'], 2)
            result = core.import_apply(output, preview['digest'])
            self.assertEqual(result['imported'], 2)
            self.assertEqual(core.show_card(card['id']), changed)
            self.assertEqual(core.history(card['id'])['versions'][0]['card'], card)
            self.assertEqual(core.trash_list()['cards'][0]['id'], deleted['id'])
            self.assertEqual(core.load_tags()['tags'][0]['aliases'], ['study'])
            self.assertEqual(core.load_tags()['tags'][0]['description'], 'Preserved definition')
            self.assertEqual(core.import_preview(output)['duplicate_count'], 2)

    def test_context_only_exports_selected_cards_without_vocabulary_leak(self):
        core.tag_add('public', ['private-alias'], 'secret vocabulary description')
        core.tag_add('classified', [], 'another secret')
        selected = core.add_card('selected body', ['public'])
        core.add_card('hidden unrelated card', ['classified'])
        output = self.root / 'context.md'
        core.export_cards('context', str(output), [selected['id']])
        text = output.read_text(encoding='utf-8')
        self.assertIn('selected body', text)
        for hidden in ['hidden unrelated card', 'classified', 'private-alias', 'secret vocabulary']:
            self.assertNotIn(hidden, text)
        with self.assertRaises(ValueError):
            core.export_cards('context', str(self.root / 'all.md'))

    def test_preview_is_readonly_and_digest_detects_change(self):
        path = self.source('flomo.html', '<div class="memo"><div class="time">2026-10-01 10:20:30</div><div class="content"><p>hello #topic</p></div></div>')
        before = self.snapshot()
        preview = core.import_preview(path)
        self.assertEqual(self.snapshot(), before)
        Path(path).write_text(Path(path).read_text(encoding='utf-8').replace('hello', 'changed'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed'):
            core.import_apply(path, preview['digest'])
        self.assertEqual(self.snapshot(), before)

    def test_flomo_plain_text_dates_hashtags_and_duplicate_import(self):
        html = '''<!DOCTYPE html><html><body><div class="memo"><div class="time">2026-10-01 10:20:30</div><div class="content"><p>hello <a href="javascript:evil()">#topic/sub</a></p><p>second &amp; line<script>DO_NOT_IMPORT</script><img src="https://tracker.invalid/a" onerror="evil()"></p></div></div></body></html>'''
        path = self.source('flomo.html', html)
        preview = core.import_preview(path)
        self.assertEqual(preview['new_count'], 1)
        card = preview['cards'][0]
        self.assertEqual(card['tags'], ['topic/sub'])
        self.assertIn('second & line', card['content'])
        self.assertNotIn('DO_NOT_IMPORT', card['content'])
        self.assertNotIn('javascript', card['content'])
        self.assertTrue(card['created_at'].startswith('2026-10-01'))
        self.assertTrue(preview['warnings'])
        self.assertEqual(core.import_apply(path, preview['digest'])['imported'], 1)
        self.assertEqual(core.import_preview(path)['duplicate_count'], 1)
        self.assertEqual(core.import_apply(path, preview['digest'])['imported'], 0)

    def test_zip_rejects_traversal_links_ambiguous_and_large_archives(self):
        html = '<div class="memo"><div class="time">2026-01-01</div><div class="content">ok</div></div>'
        for evil in ['../escape', '/absolute', 'C:/escape', r'folder\escape']:
            path = self.root / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('index.html', html)
                # ZipInfo's constructor normalizes backslashes on Windows;
                # preserve malicious raw archive names for this fixture.
                entry = zipfile.ZipInfo('fixture')
                entry.filename = evil
                archive.writestr(entry, 'evil')
            with self.assertRaisesRegex(ValueError, 'unsafe'):
                core.import_preview(str(path))
        path = self.root / 'link.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            entry = zipfile.ZipInfo('link')
            entry.create_system = 3
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(entry, '../escape')
            archive.writestr('index.html', html)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            core.import_preview(str(path))
        path = self.root / 'valid.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('flomo/index.html', html)
            archive.writestr('flomo/assets/image.png', b'not loaded')
        self.assertEqual(core.import_preview(str(path))['new_count'], 1)
        with mock.patch.object(core, 'MAX_ARCHIVE_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                core.import_preview(str(path))

    def test_conflicting_ids_are_reported_and_never_overwritten(self):
        card = core.add_card('first', [])
        output = str(self.root / 'backup.json')
        core.export_cards('backup', output)
        core.edit_card(card['id'], 'local edit', None)
        preview = core.import_preview(output)
        self.assertEqual(preview['conflict_count'], 1)
        result = core.import_apply(output, preview['digest'])
        self.assertEqual(result['conflicts'], 1)
        self.assertEqual(core.show_card(card['id'])['content'], 'local edit')

    def test_new_conflict_after_preview_is_rechecked_under_lock(self):
        path = self.source('flomo.html', '<div class="memo"><div class="time">2026-01-01</div><div class="content">ok</div></div>')
        preview = core.import_preview(path)
        core.import_apply(path, preview['digest'])
        card_id = preview['cards'][0]['id']
        core.edit_card(card_id, 'new local edit', None)
        result = core.import_apply(path, preview['digest'])
        self.assertEqual(result['conflicts'], 1)
        self.assertEqual(core.show_card(card_id)['content'], 'new local edit')

    def test_import_failure_rolls_back_every_authoritative_file(self):
        path = self.source('flomo.html', '<div class="memo"><div class="time">2026-01-01</div><div class="content">ok #new</div></div>')
        preview = core.import_preview(path)
        tags = core.load_tags()
        real = core.atomic_write
        def failing(target, text):
            if target.parent.name == 'cards':
                raise OSError('injected failure')
            return real(target, text)
        with mock.patch.object(core, 'atomic_write', side_effect=failing):
            with self.assertRaises(OSError):
                core.import_apply(path, preview['digest'])
        self.assertEqual(core.load_tags(), tags)
        self.assertEqual(core.query_cards()['count'], 0)

    def test_export_cannot_clobber_library_or_existing_file(self):
        core.add_card('keep', [])
        with self.assertRaises(ValueError):
            core.export_cards('backup', str(self.library / 'tags.json'))
        output = self.source('keep.json', 'existing data')
        with self.assertRaises(FileExistsError):
            core.export_cards('backup', output)
        self.assertEqual(Path(output).read_text(encoding='utf-8'), 'existing data')

    def test_invalid_html_and_malformed_metadata_are_rejected(self):
        path = self.source('bad.html', '<script>alert(1)</script>not flomo')
        with self.assertRaises(ValueError):
            core.import_preview(path)
        core.add_card('original', [])
        output = self.root / 'backup.json'
        core.export_cards('backup', str(output))
        data = json.loads(output.read_text(encoding='utf-8'))
        data['cards'][0]['id'] = '../escape'
        output.write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            core.import_preview(str(output))

    def test_preview_missing_target_is_readonly_and_apply_initializes(self):
        path = self.source('flomo.html', '<div class="memo"><div class="time">2026-01-01</div><div class="content">new library</div></div>')
        target = self.root / 'new-target'
        with mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(target)}):
            preview = core.import_preview(path)
            self.assertFalse(target.exists())
            self.assertEqual(preview['new_count'], 1)
            self.assertEqual(core.import_apply(path, preview['digest'])['imported'], 1)
            self.assertEqual(core.query_cards()['count'], 1)

    def test_partial_library_is_not_misidentified_as_empty(self):
        path = self.source('flomo.html', '<div class="memo"><div class="time">2026-01-01</div><div class="content">new library</div></div>')
        target = self.root / 'partial'
        target.mkdir()
        (target / 'cards').mkdir()
        with mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(target)}):
            with self.assertRaises((ValueError, OSError)):
                core.import_preview(path)
            self.assertFalse((target / '.lock').exists())

    def test_backup_after_tag_merge_preserves_historical_trash_and_history(self):
        core.tag_add('old', [], 'Old name')
        core.tag_add('new', [], 'New name')
        card = core.add_card('trashed old tag', ['old'])
        core.delete_card(card['id'])
        core.tag_merge('old', 'new')
        output = str(self.root / 'merged-backup.json')
        core.export_cards('backup', output)
        with mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(self.root / 'restored')}):
            preview = core.import_preview(output)
            self.assertEqual(core.import_apply(output, preview['digest'])['imported'], 1)
            self.assertEqual(core.trash_list()['cards'][0]['tags'], ['old'])
            self.assertEqual(core.history(card['id'])['versions'][0]['card']['tags'], ['old'])
            self.assertEqual(core.restore_card(card['id'], card['updated_at'])['tags'], ['new'])

    def test_complete_backup_keeps_distinct_ids_with_identical_content_and_date(self):
        with mock.patch.object(core, 'now', return_value='2026-01-01T00:00:00.000Z'):
            first = core.add_card('identical', [])
            second = core.add_card('identical', [])
        output = str(self.root / 'duplicate-content-backup.json')
        core.export_cards('backup', output)
        with mock.patch.dict(os.environ, {'SLIPBOX_HOME': str(self.root / 'restored')}):
            preview = core.import_preview(output)
            self.assertEqual(preview['new_count'], 2)
            self.assertEqual(core.import_apply(output, preview['digest'])['imported'], 2)
            self.assertEqual({c['id'] for c in core.query_cards()['cards']}, {first['id'], second['id']})


if __name__ == '__main__':
    unittest.main()

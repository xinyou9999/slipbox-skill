import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location('slipbox_ai_test', Path(__file__).resolve().parents[1] / 'scripts/slipbox.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class AtomicAiTagsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {'SLIPBOX_HOME': self.temp.name})
        self.env.start()
        core.initialize()
        core.tag_add('manual', [], '')
        self.card = core.add_card('Original body', ['manual'])

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_ai_tags_commit_definitions_and_card_without_rewriting_body(self):
        result = core.apply_card_tags(self.card['id'], self.card['updated_at'], ['manual', 'topic'], [{'name': 'topic', 'description': 'A durable topic'}])
        self.assertTrue(result['applied'])
        self.assertEqual(core.show_card(self.card['id'])['content'], 'Original body')
        self.assertEqual(core.show_card(self.card['id'])['tags'], ['manual', 'topic'])
        self.assertEqual(core.tag_list()['count'], 2)

    def test_stale_result_neither_overwrites_note_nor_creates_unused_tags(self):
        changed = core.edit_card(self.card['id'], 'New body', [])
        result = core.apply_card_tags(self.card['id'], self.card['updated_at'], ['manual', 'topic'], [{'name': 'topic', 'description': 'New concept'}])
        self.assertFalse(result['applied'])
        self.assertEqual(core.show_card(self.card['id']), changed)
        self.assertEqual(core.tag_list()['count'], 1)

    def test_failed_derived_update_rolls_back_both_authoritative_files(self):
        tags_before = core.load_tags()
        with mock.patch.object(core, '_rebuild_index_unlocked', side_effect=OSError('disk full')):
            with self.assertRaises(ValueError):
                core.apply_card_tags(self.card['id'], self.card['updated_at'], ['manual', 'topic'], [{'name': 'topic', 'description': 'Topic'}])
        self.assertEqual(core.show_card(self.card['id']), self.card)
        self.assertEqual(core.load_tags(), tags_before)

    def test_model_cannot_drop_existing_manual_tag(self):
        core.tag_add('topic', [], '')
        with self.assertRaises(ValueError):
            core.apply_card_tags(self.card['id'], self.card['updated_at'], ['topic'], [])
        self.assertEqual(core.show_card(self.card['id']), self.card)

    def test_metadata_update_preserves_usage_and_detects_alias_collisions(self):
        before = core.tag_list()['tags'][0]
        result = core.tag_update('manual', ['m'], 'Hand chosen', {'name': 'manual', 'aliases': [], 'description': ''})
        self.assertEqual(result['aliases'], ['m'])
        self.assertEqual(result['usage_count'], before['usage_count'])
        core.tag_add('other', [], '')
        with self.assertRaises(ValueError):
            core.tag_update('manual', ['other'], 'Changed', {'name': 'manual', 'aliases': ['m'], 'description': 'Hand chosen'})
        self.assertEqual(core.tag_list()['tags'][0]['description'], 'Hand chosen')

    def test_metadata_conflict_preserves_manual_description(self):
        core.tag_update('manual', [], 'User meaning', {'name': 'manual', 'aliases': [], 'description': ''})
        with self.assertRaises(ValueError):
            core.tag_update('manual', [], 'Late AI meaning', {'name': 'manual', 'aliases': [], 'description': ''})
        self.assertEqual(core.tag_list()['tags'][0]['description'], 'User meaning')

    def test_same_clock_tick_edit_invalidates_old_ai_revision(self):
        with mock.patch.object(core, 'now', return_value=self.card['updated_at']):
            changed = core.edit_card(self.card['id'], 'New body', [])
        self.assertNotEqual(changed['updated_at'], self.card['updated_at'])
        result = core.apply_card_tags(self.card['id'], self.card['updated_at'], ['manual'], [])
        self.assertFalse(result['applied'])

    def test_ai_cannot_create_multiple_new_concepts(self):
        with self.assertRaises(ValueError):
            core.apply_card_tags(self.card['id'], self.card['updated_at'], ['manual', 'one', 'two'], [
                {'name': 'one', 'description': 'One'}, {'name': 'two', 'description': 'Two'}])
        self.assertEqual(core.tag_list()['count'], 1)

    def test_confirmed_deletion_rejects_a_note_changed_since_confirmation(self):
        changed = core.edit_card(self.card['id'], 'Newer note', None)
        with self.assertRaises(ValueError):
            core.delete_card(self.card['id'], self.card['updated_at'])
        self.assertEqual(core.show_card(self.card['id']), changed)
        self.assertTrue(core.delete_card(changed['id'], changed['updated_at'])['deleted'])

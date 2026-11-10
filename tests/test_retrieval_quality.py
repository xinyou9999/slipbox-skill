"""Deterministic retrieval fixtures; these do not measure real-model quality."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('slipbox_quality', Path(__file__).resolve().parents[1]/'scripts/slipbox.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class RetrievalQualityTests(unittest.TestCase):
    def test_multilingual_candidates_filters_long_text_and_empty_results(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, SLIPBOX_HOME=directory):
            core.initialize()
            core.tag_add('读书', ['阅读'], '')
            sleep = core.add_card('睡前进行缓慢呼吸，帮助身体放松。', [])
            book = core.add_card('今天读了四书，整理其中关于学习的观点。', ['读书'])
            long = core.add_card('背景文字。'*1200+'旅行时把想法立即记下来。', [])
            # Explicit expansion fixtures simulate supplied terms, not a successful real LLM call.
            cases = [(['睡眠','呼吸'], sleep['id']), (['学习','读书'], book['id']), (['旅行'],long['id'])]
            for terms, expected in cases:
                with self.subTest(terms=terms):
                    self.assertIn(expected, [c['id'] for c in core.search_candidates(terms)['cards']])
            self.assertEqual(core.query_cards('阅读')['cards'][0]['id'], book['id'])
            self.assertEqual(core.query_cards('读书 学习')['cards'][0]['id'], book['id'])
            self.assertEqual(core.query_cards('不存在的内容')['count'], 0)
            self.assertEqual(core.query_cards('读书', untagged=True)['count'], 0)
            self.assertEqual(core.query_cards('学习', exclude_tags=['读书'])['count'], 0)
            self.assertEqual(core.query_cards('旅行', created_from='2099-01-01')['count'], 0)


if __name__ == '__main__':
    unittest.main()

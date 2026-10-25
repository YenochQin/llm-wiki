import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import research_wiki as wiki


class RemoveEdgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'graph').mkdir()
        self.path = self.root / 'graph/edges.jsonl'
        self.edge = {'from': 'papers/a', 'to': 'concepts/b', 'type': 'uses_concept', 'evidence': '旧证据', 'custom': 17}
        self.path.write_text(json.dumps(self.edge) + '\n', encoding='utf8')

    def call(self, evidence='旧证据', **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            wiki.remove_edge(str(self.root), kwargs.get('from_id', 'papers/a'), kwargs.get('to_id', 'concepts/b'), kwargs.get('edge_type', 'uses_concept'), evidence)

    def reject(self, **kwargs):
        before = self.path.read_bytes()
        with self.assertRaises(SystemExit):
            self.call(**kwargs)
        self.assertEqual(before, self.path.read_bytes())

    def test_only_target_removed_preserving_unrelated_bytes(self):
        tail = b'\r\n{ "from":"papers/c", "to":"concepts/d", "type":"uses_concept", "custom":42 }'
        self.path.write_bytes(self.path.read_bytes() + tail)
        self.call()
        self.assertEqual(tail, self.path.read_bytes())

    def test_wrong_evidence_and_missing_match_rejected(self):
        self.reject(evidence='different')
        self.reject(to_id='concepts/absent')

    def test_duplicates_and_malformed_tail_rejected(self):
        original = self.path.read_bytes()
        self.path.write_bytes(original + original)
        self.reject()
        self.path.write_bytes(original + b'not-json\n')
        self.reject()
        self.path.write_bytes(original + b'[]\n')
        self.reject()

    def test_symmetric_reverse_order(self):
        self.path.write_text(json.dumps({'from': 'papers/b', 'to': 'papers/a', 'type': 'similar_method_to', 'evidence': '旧证据', 'symmetric': True}) + '\n')
        self.call(to_id='papers/b', edge_type='similar_method_to')
        self.assertEqual(b'', self.path.read_bytes())

    def test_atomic_replace_failure_preserves_original(self):
        before = self.path.read_bytes()
        with mock.patch.object(wiki.os, 'replace', side_effect=OSError('simulated failure')):
            with self.assertRaises(OSError):
                self.call()
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([self.path], list(self.path.parent.iterdir()))

    def test_concurrent_writer_is_not_overwritten(self):
        original_mkstemp = wiki.tempfile.mkstemp
        def concurrent_write(*args, **kwargs):
            self.path.write_bytes(b'concurrent update\n')
            return original_mkstemp(*args, **kwargs)
        with mock.patch.object(wiki.tempfile, 'mkstemp', side_effect=concurrent_write):
            with self.assertRaises(SystemExit):
                self.call()
        self.assertEqual(b'concurrent update\n', self.path.read_bytes())
        self.assertEqual([self.path], list(self.path.parent.iterdir()))


if __name__ == '__main__':
    unittest.main()

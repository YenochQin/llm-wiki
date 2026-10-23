import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import research_wiki as wiki


class EdgeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "graph").mkdir()
        self.path = self.root / "graph/edges.jsonl"
        self.edge = {"from": "papers/a", "to": "claims/b", "type": "supports",
                     "evidence": "old", "confidence": "low", "date": "2020-01-01",
                     "custom": {"source_page": 3}}
        self.path.write_text(json.dumps(self.edge) + "\n", encoding="utf-8")

    def update(self, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            wiki.set_edge_evidence(str(self.root), "papers/a", "claims/b",
                                   "supports", kwargs.pop("evidence", "new"), **kwargs)
        return json.loads(out.getvalue())

    def assert_rejected_unchanged(self, **kwargs):
        before = self.path.read_bytes()
        with self.assertRaises(SystemExit) as caught:
            self.update(**kwargs)
        self.assertEqual(caught.exception.code, 1)
        self.assertEqual(self.path.read_bytes(), before)

    def test_preserves_fields_and_unrelated_bytes_with_multiline_unicode(self):
        tail = b'\n{ "from":"papers/c", "to":"claims/d", "type":"supports" }\r\n'
        self.path.write_bytes(self.path.read_bytes() + tail)
        result = self.update(evidence="比值 F₁/F₂\nNot absolute F.", expected_evidence="old")
        updated, rest = self.path.read_bytes().split(b"\n", 1)
        self.assertEqual(json.loads(updated), dict(self.edge, evidence=result["evidence"]))
        self.assertEqual(rest, tail)
        self.assertEqual(result["previous_evidence"], "old")

    def test_noop_does_not_replace_file(self):
        with mock.patch.object(wiki.os, "replace") as replace:
            self.assertFalse(self.update(evidence="old")["changed"])
        replace.assert_not_called()

    def test_unicode_line_separator_inside_evidence_is_not_a_jsonl_boundary(self):
        text = "First clause.\u2028第二句。"
        self.update(evidence=text)
        self.assertFalse(self.update(evidence=text)["changed"])

    def test_stale_expected_value_and_empty_evidence_are_rejected(self):
        self.assert_rejected_unchanged(expected_evidence="different")
        self.assert_rejected_unchanged(evidence=" \n ")

    def test_missing_and_duplicate_targets_are_rejected(self):
        self.path.write_text("", encoding="utf-8")
        self.assert_rejected_unchanged()
        self.path.write_text((json.dumps(self.edge) + "\n") * 2, encoding="utf-8")
        self.assert_rejected_unchanged()

    def test_invalid_rows_fail_without_rewriting(self):
        for row in ["not json", "[]"]:
            self.path.write_text(json.dumps(self.edge) + "\n" + row, encoding="utf-8")
            self.assert_rejected_unchanged()

    def test_symmetric_target_can_be_addressed_in_reverse(self):
        edge = dict(self.edge, **{"from": "papers/a", "to": "papers/b",
                                  "type": "same_problem_as", "symmetric": True})
        self.path.write_text(json.dumps(edge), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            wiki.set_edge_evidence(str(self.root), "papers/b", "papers/a", "same_problem_as", "new")
        self.assertEqual(json.loads(self.path.read_text()), dict(edge, evidence="new"))

    def test_atomic_replace_failure_preserves_file_and_cleans_temp(self):
        before = self.path.read_bytes()
        with mock.patch.object(wiki.os, "replace", side_effect=OSError("failed")):
            with self.assertRaises(OSError):
                self.update()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.glob(".edges-*.tmp")), [])

    def test_cli_reads_evidence_file(self):
        text = "Only the ratio is checked.\n保留条件。\n"
        evidence_file = self.root / "evidence.txt"
        evidence_file.write_text(text, encoding="utf-8")
        argv = ["research_wiki.py", "set-edge-evidence", str(self.root),
                "--from", "papers/a", "--to", "claims/b", "--type", "supports",
                "--evidence-file", str(evidence_file), "--expected-evidence", "old"]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            wiki.main()
        self.assertEqual(json.loads(self.path.read_text())["evidence"], text)


if __name__ == "__main__":
    unittest.main()

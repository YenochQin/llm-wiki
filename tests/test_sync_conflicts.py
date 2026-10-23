import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import grounding_lint
import lint
import research_wiki


class SyncConflictTests(unittest.TestCase):
    def test_scanners_report_and_skip_conflicts_even_without_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / "papers"
            papers.mkdir()
            (papers / "normal.md").write_text("---\ntitle: Normal\n---\n")
            for name in ("copy-NSConflict-湛蓝-mac26.6.2.md",
                         "orphan-NSConflict8473-湛蓝-linux7.2.9.md"):
                (papers / name).write_text("invalid: [frontmatter\n")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                pages = lint.find_all_pages(root)
                with contextlib.redirect_stdout(io.StringIO()):
                    research_wiki.rebuild_index(str(root))
                grounded = grounding_lint._all_markdown_pages(root)
            self.assertEqual(set(pages), {"normal"})
            self.assertEqual([p.stem for p in grounded], ["normal"])
            self.assertNotIn("NSConflict", (root / "index.md").read_text())
            self.assertIn("NSConflict8473", stderr.getvalue())
            self.assertEqual(len([i for i in lint.lint(root)
                                  if i.category == "sync-conflict"]), 2)
            self.assertEqual(len(list(papers.glob("*.md"))), 3)

    def test_graph_remap_preserves_metadata_and_unrelated_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "papers").mkdir()
            (root / "papers/a.md").touch()
            (root / "graph").mkdir()
            old = "papers/a-NSConflict-host"
            rows = [{"from": old, "to": "claims/c", "type": "supports",
                     "evidence": "E1", "date": "2026-01-01", "custom": [1]},
                    {"from": "papers/unrelated", "to": "claims/z", "type": "supports"}]
            path = root / "graph/edges.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            with contextlib.redirect_stdout(io.StringIO()):
                research_wiki.remap_graph_nodes(str(root), {old: "papers/a"})
            actual = [json.loads(s) for s in path.read_text().splitlines()]
            rows[0]["from"] = "papers/a"
            self.assertEqual(actual, rows)

    def test_conflicting_collision_aborts_both_graph_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "papers").mkdir()
            (root / "papers/a.md").touch()
            (root / "graph").mkdir()
            old = "papers/a-NSConflict-host"
            path = root / "graph/edges.jsonl"
            rows = [{"from": f, "to": "claims/c", "type": "supports", "evidence": e}
                    for f, e in [(old, "old"), ("papers/a", "new")]]
            before = "".join(json.dumps(r) + "\n" for r in rows)
            path.write_text(before)
            with self.assertRaises(ValueError):
                research_wiki.remap_graph_nodes(str(root), {old: "papers/a"})
            self.assertEqual(path.read_text(), before)

    def test_equivalent_collision_keeps_canonical_date_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "papers").mkdir()
            (root / "papers/a.md").touch()
            (root / "graph").mkdir()
            old = "papers/a-NSConflict-host"
            canonical = {"from": "papers/a", "to": "claims/c", "type": "supports",
                         "evidence": "E1", "date": "2026-01-01", "custom": [1]}
            copy = {**canonical, "from": old, "date": "2026-02-01"}
            path = root / "graph/edges.jsonl"
            path.write_text(json.dumps(copy) + "\n" + json.dumps(canonical) + "\n")
            with contextlib.redirect_stdout(io.StringIO()):
                research_wiki.remap_graph_nodes(str(root), {old: "papers/a"})
                before = path.read_bytes()
                research_wiki.remap_graph_nodes(str(root), {old: "papers/a"})
            self.assertEqual([json.loads(s) for s in path.read_text().splitlines()], [canonical])
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_second_file_prevents_first_file_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "papers").mkdir()
            (root / "papers/a.md").touch()
            (root / "graph").mkdir()
            old = "papers/a-NSConflict-host"
            path = root / "graph/edges.jsonl"
            before = json.dumps({"from": old, "to": "claims/c", "type": "supports"}) + "\n"
            path.write_text(before)
            (root / "graph/citations.jsonl").write_text("invalid json\n")
            with self.assertRaises(ValueError):
                research_wiki.remap_graph_nodes(str(root), {old: "papers/a"})
            self.assertEqual(path.read_text(), before)

    def test_rejects_traversal_and_missing_canonical_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            for target in ("../escape", "papers/../escape", "papers/missing"):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    research_wiki.remap_graph_nodes(tmp, {"papers/old": target})


if __name__ == "__main__":
    unittest.main()

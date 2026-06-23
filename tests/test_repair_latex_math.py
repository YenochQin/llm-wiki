import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from _paths import RuntimePaths
from repair_latex_math import main, repair_latex_math, resolve_ingest_check_target


class RepairLatexMathTests(unittest.TestCase):
    def test_removes_padding_between_dollar_delimiters_and_formula(self) -> None:
        text = "Inline $ x ^ { 2 } $ and display $$ E = m c ^ { 2 } $$."

        repaired, report = repair_latex_math(text)

        self.assertEqual(repaired, "Inline $x^{2}$ and display $$E = m c^{2}$$.")
        self.assertTrue(report.changed)
        self.assertEqual(report.math_spans, 2)

    def test_converted_latex_delimiters_are_not_padded_inside(self) -> None:
        text = r"Display \[ \frac { a } { b } \] and inline \( y _ { 0 } \)."

        repaired, report = repair_latex_math(text)

        self.assertEqual(repaired, r"Display $$\frac{a}{b}$$ and inline $y_{0}$.")
        self.assertTrue(report.changed)
        self.assertEqual(report.converted_delimiters, 2)

    def test_preserves_text_command_internal_spaces_while_trimming_delimiters(self) -> None:
        text = r"$ \text{ keep these words } $"

        repaired, _ = repair_latex_math(text)

        self.assertEqual(repaired, r"$\text{ keep these words }$")

    def test_inserts_latex_space_before_adjacent_superscript(self) -> None:
        text = r"Bad term $4d^{1 0}^{1} S_{0}$ and code `$4d^{1 0}^{1} S_{0}$`."

        repaired, report = repair_latex_math(text)

        self.assertEqual(
            repaired,
            r"Bad term $4d^{1 0} \ ^{1}S_{0}$ and code `$4d^{1 0}^{1} S_{0}$`.",
        )
        self.assertTrue(report.changed)

    def test_ingest_check_target_resolves_slug_to_generated_paper_page_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            paths = RuntimePaths(
                project_root=root,
                wiki_root=wiki,
                raw_root=root / "raw",
                config_path=root / "config" / "paths.json",
                used_config=False,
                profile="test",
            )

            target = resolve_ingest_check_target("sample-paper", paths)

            self.assertEqual(target, wiki / "papers" / "sample-paper.md")

    def test_ingest_check_cli_reports_only_generated_paper_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            papers_dir = wiki / "papers"
            sources_dir = wiki / "sources" / "papers"
            papers_dir.mkdir(parents=True)
            sources_dir.mkdir(parents=True)
            (papers_dir / "sample-paper.md").write_text("Generated $ x ^ { 2 } $", encoding="utf-8")
            (sources_dir / "sample-paper.md").write_text("Source $ y ^ { 2 } $", encoding="utf-8")
            paths = RuntimePaths(
                project_root=root,
                wiki_root=wiki,
                raw_root=root / "raw",
                config_path=root / "config" / "paths.json",
                used_config=False,
                profile="test",
            )
            stdout = StringIO()

            with (
                patch("repair_latex_math.load_paths", return_value=paths),
                patch("sys.argv", ["repair_latex_math.py", "--dry-run", "--ingest-check", "sample-paper"]),
                redirect_stdout(stdout),
            ):
                main()

            output = stdout.getvalue()
            self.assertIn(str(papers_dir / "sample-paper.md"), output)
            self.assertNotIn(str(sources_dir / "sample-paper.md"), output)

    def test_ingest_check_cli_fails_when_generated_paper_page_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = RuntimePaths(
                project_root=root,
                wiki_root=root / "wiki",
                raw_root=root / "raw",
                config_path=root / "config" / "paths.json",
                used_config=False,
                profile="test",
            )

            with (
                patch("repair_latex_math.load_paths", return_value=paths),
                patch("sys.argv", ["repair_latex_math.py", "--dry-run", "--ingest-check", "missing-paper"]),
                self.assertRaises(FileNotFoundError),
            ):
                main()


if __name__ == "__main__":
    unittest.main()

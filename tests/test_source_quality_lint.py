import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import source_quality_lint as quality


class SourceQualityTests(unittest.TestCase):
    def rules(self, text, **kwargs):
        return {i["rule"] for i in quality.scan_text(text, **kwargs)["issues"]}

    def test_missing_symbols_outside_math_are_flagged_with_exact_location(self):
        text = "# Paper\n\n**A B S T R A C T**\n\nStates 5??24?? and 5??2????.\n"
        report = quality.scan_text(text)
        issues = [i for i in report["issues"] if i["rule"] == "missing-character"]
        self.assertEqual(len(issues), 4)
        self.assertEqual(issues[0]["line"], 5)
        self.assertEqual(issues[0]["column"], 9)
        self.assertEqual(issues[0]["severity"], "red")
        self.assertEqual(issues[0]["scope"], "fragment")
        self.assertEqual(report["status"], "review_required")

    def test_code_metadata_urls_and_inline_code_are_not_scientific_damage(self):
        text = ('---\ntitle: "??"\n---\n# Abstract\n'
                'A clean description with `??` and [link](https://example.org/??).\n'
                '```python\nx = "??"\n```\n<!-- ?? -->\n')
        self.assertNotIn("missing-character", self.rules(text))

    def test_replacement_character_and_invalid_control(self):
        self.assertIn("missing-character", self.rules("# Abstract\nA \ufffd state."))
        self.assertIn("control-character", self.rules("# Abstract\nA \x00 state."))

    def test_math_damage_and_escaped_braces(self):
        self.assertIn("math-braces", self.rules("# Abstract\nAn equation $x_{i$."))
        self.assertNotIn("math-braces", self.rules(r"# Abstract" + "\n" + r"$\{x\}$"))
        self.assertIn("math-delimiter", self.rules("# Abstract\n$$\nx = 1\n"))
        self.assertIn("math-environment", self.rules(
            "# Abstract\n$$\\begin{aligned} x=1 \\end{matrix}$$"))

    def test_table_width_respects_math_pipes_and_escaped_pipes(self):
        good = "# Abstract\n| A | B |\n|---|---|\n| $|x|$ | a\\|b |\n"
        self.assertNotIn("table-columns", self.rules(good))
        self.assertIn("table-columns", self.rules(good + "| 1 | 2 | 3 |\n"))

    def test_one_broken_math_span_does_not_cascade_into_valid_following_cells(self):
        for broken in (r"\(lost", "$$lost", "$lost"):
            text = '# Abstract\r\n<table><tr><td>' + broken + '</td>'
            text += '<td>$x_{i}$</td>' * 100 + '</tr></table>'
            issues = quality.scan_text(text)["issues"]
            math = [i for i in issues if i["rule"].startswith("math-")]
            self.assertEqual(len(math), 1, math)
        text = '# Abstract\r\n\\(lost\r\n\r\n' + '$x_i$ ' * 100
        self.assertEqual(sum(i["rule"] == "math-delimiter" for i in quality.scan_text(text)["issues"]), 1)

    def test_control_character_does_not_shift_following_line_coordinates(self):
        issues = quality.scan_text('# Abstract\nA\x0cB\nLost ??')['issues']
        missing = next(i for i in issues if i['rule'] == 'missing-character')
        self.assertEqual(missing['line'], 3)

    def test_rendered_report_uses_safe_fences_for_exact_excerpts(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.md'
            source.write_text('# Abstract\nStates ??', encoding='utf-8')
            report = quality.scan_paths([source])
            rendered = quality.render_markdown(report)
            self.assertIn('States ??', rendered)
            self.assertIn('L2:8', rendered)
            self.assertIn('No findings means only', rendered)

    def test_html_colspan_and_rowspan_do_not_make_false_ragged_tables(self):
        good = ('# Abstract\n<table><tr><th colspan="2">Title</th></tr>'
                '<tr><td>A</td><td>B</td></tr></table>')
        self.assertNotIn("table-columns", self.rules(good))
        rowspan = ('# Abstract\n<table><tr><td rowspan="2">A</td><td>B</td></tr>'
                   '<tr><td>C</td></tr></table>')
        self.assertNotIn("table-columns", self.rules(rowspan))
        bad = good.replace('<td>A</td><td>B</td>', '<td>A</td>')
        self.assertIn("table-columns", self.rules(bad))

    def test_abstract_variant_and_exclusions_are_review_findings(self):
        text = ('---\nskippedSectionHeadings: [Appendix, Funding]\n---\n'
                '**A B S T R A C T**\nActual abstract.\n# 1. Introduction\nBody.')
        rules = self.rules(text)
        self.assertIn("abstract-heading-variant", rules)
        self.assertIn("excluded-source-section", rules)
        self.assertNotIn("abstract-not-located", rules)

    def test_empty_or_broken_frontmatter_cannot_be_reported_clean(self):
        self.assertEqual(quality.scan_text("---\ntitle: Empty\n---\n")["status"], "blocked")
        self.assertIn("frontmatter-invalid", self.rules("---\ntitle: [\n---\nBody"))
        self.assertIn("frontmatter-invalid", self.rules("---\ntitle: Test\nBody"))

    def test_short_source_only_warns_with_page_count_evidence(self):
        self.assertIn("low-text-per-page", self.rules('---\ntotalPages: 10\n---\nShort.'))
        self.assertNotIn("low-text-per-page", self.rules('# Abstract\nShort.'))

    def test_duplicate_paragraph_and_suspicious_mixed_case(self):
        paragraph = "A repeated paragraph about measured atomic transitions. " * 4
        rules = self.rules("# Abstract\n" + paragraph + "\n\n" + paragraph +
                           "\n\ncYanmaGGentalowb")
        self.assertIn("repeated-paragraph", rules)
        self.assertIn("suspicious-word", rules)

    def test_cli_is_read_only_and_deduplicates_overlapping_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            source.write_text("# Abstract\nStates 5??24??.", encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = quality.main([str(root), str(source), "--json"])
            data = json.loads(out.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(data["summary"]["files_scanned"], 1)
            self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(list(root.iterdir()), [source])

    def test_clean_source_has_no_findings_and_warnings_are_not_pdf_verification(self):
        clean = quality.scan_text('# Abstract\nMeasured levels are reported.\n\n# Results\n$x_{i}=1$.')
        self.assertEqual(clean['status'], 'no_findings')
        self.assertEqual(clean['issues'], [])
        warning = quality.scan_text('# Abstract\nAn incomplete formula $x_{i$.')
        self.assertEqual(warning['status'], 'review_required')
        self.assertFalse(any(i['severity'] == 'red' for i in warning['issues']))

    def test_missing_input_is_an_error_and_invalid_utf8_is_a_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(quality.main([str(root / "missing.md")]), 2)
                self.assertEqual(quality.main([str(root)]), 2)
            source = root / "bad.md"
            source.write_bytes(b"# Abstract\n\xff")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = quality.main([str(source), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out.getvalue())["files"][0]["status"], "blocked")

    def test_reference_mapping_uses_links_not_matching_slugs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sources/papers").mkdir(parents=True)
            (root / "papers").mkdir()
            source = root / "sources/papers/source-name.md"
            source.write_text("# Abstract\nStates ??", encoding="utf-8")
            page = root / "papers/different-name.md"
            page.write_text('[prepared markdown](../sources/papers/source-name.md)', encoding="utf-8")
            mapping = quality.reference_index(root)
            self.assertEqual(mapping[str(source.resolve())], [str(page.resolve())])


if __name__ == "__main__":
    unittest.main()

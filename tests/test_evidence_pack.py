import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from evidence_pack import EvidenceCard, main, render_card, render_pack


class EvidencePackTests(unittest.TestCase):
    def test_render_card_does_not_prefix_display_math_continuation_lines(self) -> None:
        card = EvidenceCard(
            evidence_id="E1",
            use_label="Method",
            short_label="rate expression",
            source_slug="sample-paper",
            source_section="Eq. 2",
            excerpt="$$\nA = x\n+ y\n$$",
        )

        rendered = render_card(card)

        self.assertEqual(
            rendered,
            "- `E1` Method — rate expression ([prepared markdown](../sources/papers/sample-paper.md), Eq. 2): ^E1\n"
            "  > $$\n"
            "  A = x\n"
            "  + y\n"
            "  $$",
        )

    def test_render_card_prefixes_ordinary_multiline_quotes(self) -> None:
        card = EvidenceCard(
            evidence_id="E2",
            use_label="Results",
            short_label="main result",
            source_slug="sample-paper",
            source_section="Table 1",
            excerpt="First source line.\nSecond source line.",
        )

        rendered = render_card(card)

        self.assertIn("  > First source line.", rendered)
        self.assertIn("  > Second source line.", rendered)

    def test_render_pack_adds_heading_and_blank_lines(self) -> None:
        cards = [
            EvidenceCard(
                evidence_id="E1",
                use_label="Problem",
                short_label="motivation",
                source_slug="sample-paper",
                source_section="Introduction",
                excerpt="A source sentence.",
            ),
            EvidenceCard(
                evidence_id="E2",
                use_label="Limitations",
                short_label="scope",
                source_slug="sample-paper",
                source_section="Conclusion",
                excerpt="A limitation sentence.",
            ),
        ]

        rendered = render_pack(cards)

        self.assertTrue(rendered.startswith("## Evidence Pack\n\n"))
        self.assertIn("\n\n- `E2` Limitations", rendered)
        self.assertTrue(rendered.endswith("A limitation sentence."))

    def test_render_card_accepts_citation_key_source_slug_characters(self) -> None:
        card = EvidenceCard(
            evidence_id="E1",
            use_label="Method",
            short_label="citation-key source",
            source_slug="Smith2024.foo+bar",
            source_section="Methods",
            excerpt="A source sentence.",
        )

        rendered = render_card(card)

        self.assertIn(
            "[prepared markdown](../sources/papers/Smith2024.foo+bar.md)",
            rendered,
        )

    def test_rejects_invalid_evidence_id(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceCard(
                evidence_id="1",
                use_label="Method",
                short_label="bad id",
                source_slug="sample-paper",
                source_section="Sec. 1",
                excerpt="Text.",
            )

    def test_rejects_source_slug_path_separators(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceCard(
                evidence_id="E1",
                use_label="Method",
                short_label="bad source path",
                source_slug="../sample-paper",
                source_section="Sec. 1",
                excerpt="Text.",
            )

    def test_cli_renders_json_cards(self) -> None:
        payload = {
            "cards": [
                {
                    "id": "E1",
                    "use_label": "Method",
                    "short_label": "rate expression",
                    "source_slug": "sample-paper",
                    "source_section": "Eq. 2",
                    "excerpt": "$$\nA = x\n+ y\n$$",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "cards.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            stdout = StringIO()

            with (
                patch("sys.argv", ["evidence_pack.py", "--input", str(input_path)]),
                redirect_stdout(stdout),
            ):
                main()

        self.assertIn("## Evidence Pack", stdout.getvalue())
        self.assertIn("  + y\n", stdout.getvalue())
        self.assertNotIn("  > + y", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

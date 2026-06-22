import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from repair_latex_math import repair_latex_math


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


if __name__ == "__main__":
    unittest.main()

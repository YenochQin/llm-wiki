import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import grounding_lint


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).strip() + "\n", encoding="utf-8")


class GroundingLintTests(unittest.TestCase):
    def test_flags_paper_without_evidence_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(
                wiki / "papers" / "sample.md",
                """
                ---
                title: Sample
                slug: sample
                ---

                ## Method

                The method is very effective.
                """,
            )

            issues = grounding_lint.lint(wiki, only=["papers/sample.md"])

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].category, "missing-evidence-pack")
            self.assertEqual(issues[0].level, "red")

    def test_accepts_paper_with_source_backed_evidence_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(
                wiki / "sources" / "papers" / "sample.md",
                """
                # Sample

                The experiment used a controlled sample and reported accuracy.
                """,
            )
            write(
                wiki / "papers" / "sample.md",
                """
                ---
                title: Sample
                slug: sample
                ---

                ## Evidence Pack

                - `E1` ([prepared markdown](../sources/papers/sample.md), Method):
                  > The experiment used a controlled sample

                ## Method

                The experiment used a controlled sample.
                """,
            )

            issues = grounding_lint.lint(wiki, only=["papers/sample.md"])

            self.assertEqual(issues, [])

    def test_flags_evidence_excerpt_missing_from_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(wiki / "sources" / "papers" / "sample.md", "# Sample\nActual source text.")
            write(
                wiki / "papers" / "sample.md",
                """
                ---
                title: Sample
                slug: sample
                ---

                ## Evidence Pack

                - `E1` ([prepared markdown](../sources/papers/sample.md), Results):
                  > Fabricated result that is absent
                """,
            )

            issues = grounding_lint.lint(wiki, only=["papers/sample.md"])

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].category, "source-excerpt-not-found")

    def test_accepts_concept_excerpts_backed_by_different_linked_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(wiki / "sources" / "papers" / "one.md", "# One\nFirst exact source excerpt.")
            write(wiki / "sources" / "papers" / "two.md", "# Two\nSecond exact source excerpt.")
            write(
                wiki / "concepts" / "sample-concept.md",
                """
                ---
                title: Sample concept
                slug: sample-concept
                ---

                ## Definition

                A concept with two source-backed examples.

                ## Source excerpts

                - [[one]] ([prepared markdown](../sources/papers/one.md)):
                  > First exact source excerpt.
                - [[two]] ([prepared markdown](../sources/papers/two.md)):
                  > Second exact source excerpt.
                """,
            )

            issues = grounding_lint.lint(wiki, only=["concepts/sample-concept.md"])

            self.assertEqual(issues, [])

    def test_flags_claim_evidence_without_source_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(
                wiki / "claims" / "sample-claim.md",
                """
                ---
                title: Sample claim
                slug: sample-claim
                source_papers: [sample]
                evidence:
                  - source: sample
                    type: supports
                    strength: strong
                    detail: "The paper proves a broad claim."
                ---

                ## Statement

                The paper proves a broad claim.
                """,
            )

            issues = grounding_lint.lint(wiki, only=["claims/sample-claim.md"])

            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0].category, "missing-source-anchor")

    def test_cli_json_reports_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            write(
                wiki / "papers" / "sample.md",
                """
                ---
                title: Sample
                slug: sample
                ---
                """,
            )

            result = grounding_lint.run_cli(["--wiki-dir", str(wiki), "--json"])

            self.assertEqual(result.exit_code, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload[0]["category"], "missing-evidence-pack")


if __name__ == "__main__":
    unittest.main()

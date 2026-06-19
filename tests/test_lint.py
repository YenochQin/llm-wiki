import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import lint  # noqa: E402


class LintClaimProvenanceTests(unittest.TestCase):
    def test_claim_yaml_rejects_obsidian_block_links_without_broken_link_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            (wiki / "papers").mkdir()
            (wiki / "claims").mkdir()

            (wiki / "papers" / "lange_2021_Improved.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: "Improved"
                    slug: lange_2021_Improved
                    paper_type: paper
                    research_modes: [experiment]
                    theory_tags: []
                    computation_tags: []
                    experiment_tags: [measurement]
                    research_object_tags: [atom]
                    importance: 4
                    date_added: 2026-06-18
                    source_type: pdf
                    external_ids: {}
                    keywords: []
                    domain: test
                    code_url: ""
                    cited_by: []
                    ---

                    # Improved

                    ## Evidence Pack

                    - `E12` Claim — example ([prepared markdown](../sources/papers/lange_2021_Improved.md), Results): ^E12
                      > exact source fragment

                    ## Related

                    - [[bad-claim]]
                    """
                ),
                encoding="utf-8",
            )
            (wiki / "claims" / "bad-claim.md").write_text(
                textwrap.dedent(
                    """\
                    ---
                    title: "Bad claim"
                    slug: bad-claim
                    status: supported
                    confidence: 0.75
                    tags: [test]
                    source_papers: ["[[lange_2021_Improved#^E12]]"]
                    evidence:
                      - source: "[[lange_2021_Improved#^E12]]"
                        source_anchor: "[[#^E12]]"
                        type: supports
                        strength: strong
                        detail: "uses Obsidian syntax in YAML"
                    conditions: ""
                    date_proposed: 2026-06-18
                    date_updated: 2026-06-18
                    ---

                    # Bad claim

                    ## Statement

                    Bad claim.
                    """
                ),
                encoding="utf-8",
            )

            issues = lint.lint(wiki)
            categories = [issue.category for issue in issues]
            self.assertIn("invalid-claim-provenance", categories)
            self.assertNotIn("broken-link", categories)


if __name__ == "__main__":
    unittest.main()

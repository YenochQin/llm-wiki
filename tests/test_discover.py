import sys
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import discover


def candidate(
    title: str,
    *,
    doi: str = "",
    authors: list[str] | None = None,
    sources: list[str] | None = None,
    anchors: list[str] | None = None,
    score: float = 0.0,
    rationale: str = "candidate",
    zotero: str = "unknown",
) -> dict:
    external_ids = {"DOI": doi} if doi else {}
    return {
        "paperId": doi or title,
        "externalIds": external_ids,
        "title": title,
        "authors": authors or [],
        "_sources": sources or ["literature_recommend"],
        "_anchors": anchors or ["anchor-a"],
        "_score": score,
        "_rationale": rationale,
        "_zotero_status": zotero,
        "_zotero_match": {},
    }


class DiscoverRecommendationQualityTests(unittest.TestCase):
    def test_anchor_shortlist_keeps_only_heavily_related_candidates(self) -> None:
        candidates = [
            candidate("single high-score related-search hit", score=0.91),
            candidate("direct reference from anchor", sources=["literature_reference"], score=0.10),
            candidate("appears in recommendation and references", sources=["literature_recommend", "literature_reference"], score=0.32),
            candidate("appears from two anchors", anchors=["anchor-a", "anchor-b"], score=0.30),
            candidate("influential edge", score=0.10) | {"is_influential_edge": True},
        ]

        kept = discover._filter_heavily_related(candidates, anchor_mode=True)

        self.assertEqual(
            [c["title"] for c in kept],
            [
                "direct reference from anchor",
                "appears in recommendation and references",
                "appears from two anchors",
                "influential edge",
            ],
        )

    def test_topic_mode_does_not_apply_anchor_heavy_relation_gate(self) -> None:
        candidates = [candidate("topic search result", score=0.05, anchors=[])]

        kept = discover._filter_heavily_related(candidates, anchor_mode=False)

        self.assertEqual(kept, candidates)

    def test_markdown_includes_title_authors_doi_and_zotero_status(self) -> None:
        payload = {
            "seed": {"mode": "anchors", "positive_ids": ["anchor"]},
            "shortlist_count": 1,
            "candidates_total": 1,
            "wiki_dedup_count": 0,
            "shortlist": [
                candidate(
                    "A Complete Candidate",
                    doi="10.1234/example",
                    authors=["Ada Lovelace", "Grace Hopper", "Alan Turing"],
                    score=0.52,
                    rationale="from 1 anchor(s); 2024",
                    zotero="collected",
                )
            ],
        }

        markdown = discover._format_markdown(payload)

        self.assertIn("**A Complete Candidate**", markdown)
        self.assertIn("Authors: Ada Lovelace, Grace Hopper, Alan Turing", markdown)
        self.assertIn("DOI: 10.1234/example", markdown)
        self.assertIn("Zotero: collected", markdown)
        self.assertNotIn("`10.1234/example`", markdown)

    def test_metadata_enrichment_fills_missing_title_and_authors_from_doi(self) -> None:
        candidates = [
            candidate(
                "",
                doi="10.1234/enriched",
                authors=[],
            )
        ]
        enriched_record = {
            "title": "An Enriched Paper",
            "authors": [{"name": "Katherine Johnson"}, {"name": "Dorothy Vaughan"}],
            "externalIds": {"DOI": "10.1234/enriched"},
            "venue": "Journal of Useful Metadata",
            "year": 2026,
        }

        with mock.patch.object(discover.fetch_literature, "paper", return_value=enriched_record):
            discover._enrich_candidate_metadata(candidates)

        self.assertEqual(candidates[0]["title"], "An Enriched Paper")
        self.assertEqual(candidates[0]["authors"], ["Katherine Johnson", "Dorothy Vaughan"])
        self.assertEqual(candidates[0]["venue"], "Journal of Useful Metadata")
        self.assertEqual(candidates[0]["year"], 2026)


if __name__ == "__main__":
    unittest.main()

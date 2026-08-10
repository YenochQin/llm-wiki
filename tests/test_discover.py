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
    year: int | None = None,
    citation_count: int = 0,
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
        "year": year,
        "citation_count": citation_count,
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

    def test_old_candidates_need_more_than_one_hundred_citations(self) -> None:
        candidates = [
            candidate("old low-cited paper", year=1989, citation_count=100),
            candidate("old highly cited paper", year=1989, citation_count=101),
            candidate("boundary-year paper", year=1990, citation_count=0),
            candidate("undated paper", year=None, citation_count=0),
        ]

        kept = discover._filter_low_cited_old_candidates(candidates)

        self.assertEqual(
            [c["title"] for c in kept],
            ["old highly cited paper", "boundary-year paper", "undated paper"],
        )

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
                | {"_providers": ["openalex"]}
            ],
        }

        markdown = discover._format_markdown(payload)

        self.assertIn("**A Complete Candidate**", markdown)
        self.assertIn("Authors: Ada Lovelace, Grace Hopper, Alan Turing", markdown)
        self.assertIn("DOI: [10.1234/example](https://doi.org/10.1234/example)", markdown)
        self.assertIn("Zotero: collected", markdown)
        self.assertIn("Sources: OpenAlex", markdown)
        self.assertNotIn("`10.1234/example`", markdown)

    def test_topic_relevance_gate_drops_broad_high_citation_hits(self) -> None:
        queries = ["neutral transition metal atomic structure calculations"]
        candidates = [
            candidate(
                "Atomic structure calculations for neutral transition-metal atoms",
                authors=["Relevant Author"],
                year=2024,
                citation_count=2,
            )
            | {"abstract": "Energy levels and transition probabilities are calculated."},
            candidate(
                "Transition-metal catalysts for electrochemical reduction",
                authors=["Broad Author"],
                year=2025,
                citation_count=5000,
            )
            | {"abstract": "Catalytic materials for energy conversion."},
        ]

        kept = discover._annotate_and_filter_topic_relevance(candidates, queries)

        self.assertEqual([c["title"] for c in kept], [candidates[0]["title"]])

    def test_topic_score_prioritizes_relevance_over_citations(self) -> None:
        relevant = candidate(
            "Relevant recent paper",
            year=2024,
            citation_count=5,
        ) | {"_topic_relevance": 0.8, "influential_citation_count": 0}
        broad = candidate(
            "Broad highly cited paper",
            year=2024,
            citation_count=10000,
        ) | {"_topic_relevance": 0.2, "influential_citation_count": 0}

        self.assertGreater(
            discover._score(relevant, anchor_mode=False, topic_mode=True),
            discover._score(broad, anchor_mode=False, topic_mode=True),
        )

    def test_required_term_groups_enforce_all_topic_constraints(self) -> None:
        groups = [
            "neutral atom|neutral niobium",
            "transition probability|transition probabilities|oscillator strength|oscillator strengths",
            "transition metal|niobium",
        ]
        relevant = candidate(
            "Transition probabilities of neutral niobium",
            authors=["Relevant Author"],
        ) | {"abstract": "Oscillator strengths for this transition metal are reported."}
        catalyst = candidate(
            "Neutral electrosynthesis with single metal atoms",
            authors=["Catalyst Author"],
        ) | {"abstract": "A transition metal catalyst is reported."}

        kept = discover._filter_required_term_groups([relevant, catalyst], groups)

        self.assertEqual(kept, [relevant])

    def test_title_term_groups_reject_abstract_only_matches(self) -> None:
        groups = [
            "neutral atom|nb i",
            "transition probability|transition probabilities|atomic structure",
        ]
        direct = candidate(
            "Transition probabilities of Nb I",
            authors=["Direct Author"],
        )
        abstract_only = candidate(
            "Solar abundance analysis",
            authors=["Context Author"],
        ) | {"abstract": "Transition probabilities of Nb I are used."}

        kept = discover._filter_required_term_groups(
            [direct, abstract_only],
            groups,
            title_only=True,
        )

        self.assertEqual(kept, [direct])

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
            "citationCount": 42,
            "influentialCitationCount": 7,
        }

        with mock.patch.object(discover.fetch_literature, "paper", return_value=enriched_record):
            discover._enrich_candidate_metadata(candidates)

        self.assertEqual(candidates[0]["title"], "An Enriched Paper")
        self.assertEqual(candidates[0]["authors"], ["Katherine Johnson", "Dorothy Vaughan"])
        self.assertEqual(candidates[0]["venue"], "Journal of Useful Metadata")
        self.assertEqual(candidates[0]["year"], 2026)
        self.assertEqual(candidates[0]["citation_count"], 42)
        self.assertEqual(candidates[0]["influential_citation_count"], 7)

    def test_metadata_enrichment_does_not_refetch_complete_openalex_candidates(self) -> None:
        candidates = [
            candidate(
                "OpenAlex Complete Paper",
                doi="10.1234/openalex-complete",
                authors=["Ada Lovelace"],
                year=2024,
                citation_count=0,
            )
            | {
                "venue": "Journal of Provider Metadata",
                "abstract": "Already complete enough for discovery.",
                "externalIds": {
                    "DOI": "10.1234/openalex-complete",
                    "OpenAlex": "https://openalex.org/W1",
                },
                "influential_citation_count": 0,
            }
        ]

        with mock.patch.object(discover.fetch_literature, "paper") as paper:
            discover._enrich_candidate_metadata(candidates)

        paper.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import os
import sys
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import fetch_literature


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class OpenAlexSearchTests(unittest.TestCase):
    def test_search_prefers_openalex_when_limit_truncates_provider_results(self) -> None:
        crossref_result = {
            "paperId": "10.1234/crossref",
            "title": "Crossref Result",
            "authors": [{"name": "Crossref Author"}],
            "externalIds": {"DOI": "10.1234/crossref"},
            "_provider": "crossref",
        }
        openalex_result = {
            "paperId": "https://openalex.org/W1",
            "title": "OpenAlex Result",
            "authors": [{"name": "OpenAlex Author"}],
            "externalIds": {"OpenAlex": "https://openalex.org/W1"},
            "_provider": "openalex",
        }

        with (
            mock.patch.object(fetch_literature, "_crossref_search", return_value=[crossref_result]) as crossref,
            mock.patch.object(fetch_literature, "_openalex_search", return_value=[openalex_result]),
        ):
            results = fetch_literature.search("neutral atoms", limit=1)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["_provider"], "openalex")
        crossref.assert_not_called()

    def test_search_uses_crossref_to_fill_short_openalex_results(self) -> None:
        openalex_result = {
            "paperId": "https://openalex.org/W1",
            "title": "OpenAlex Result",
            "externalIds": {"OpenAlex": "https://openalex.org/W1"},
            "_provider": "openalex",
        }
        crossref_result = {
            "paperId": "10.1234/crossref",
            "title": "Crossref Result",
            "externalIds": {"DOI": "10.1234/crossref"},
            "_provider": "crossref",
        }
        with (
            mock.patch.object(fetch_literature, "_openalex_search", return_value=[openalex_result]),
            mock.patch.object(fetch_literature, "_crossref_search", return_value=[crossref_result]) as crossref,
        ):
            results = fetch_literature.search("neutral atoms", limit=2, since_year=2018)

        self.assertEqual([item["_provider"] for item in results], ["openalex", "crossref"])
        crossref.assert_called_once_with("neutral atoms", limit=1, since_year=2018)

    def test_search_can_add_small_crossref_supplement_after_full_openalex_pool(self) -> None:
        openalex_result = {
            "paperId": "https://openalex.org/W1",
            "title": "OpenAlex Result",
            "externalIds": {"OpenAlex": "https://openalex.org/W1"},
            "_provider": "openalex",
        }
        crossref_result = {
            "paperId": "10.1234/crossref",
            "title": "Crossref Result",
            "externalIds": {"DOI": "10.1234/crossref"},
            "_provider": "crossref",
        }
        with (
            mock.patch.object(fetch_literature, "_openalex_search", return_value=[openalex_result]),
            mock.patch.object(fetch_literature, "_crossref_search", return_value=[crossref_result]) as crossref,
        ):
            results = fetch_literature.search(
                "neutral atoms",
                limit=1,
                since_year=2018,
                crossref_supplement=1,
            )

        self.assertEqual([item["_provider"] for item in results], ["openalex", "crossref"])
        crossref.assert_called_once_with("neutral atoms", limit=1, since_year=2018)

    def test_openalex_search_uses_works_search_api_and_normalizes_results(self) -> None:
        payload = {
            "results": [
                {
                    "id": "https://openalex.org/W123",
                    "doi": "https://doi.org/10.1234/example",
                    "display_name": "Example Work",
                    "abstract_inverted_index": {
                        "OpenAlex": [0],
                        "search": [1],
                        "works.": [2],
                    },
                    "authorships": [
                        {"author": {"display_name": "Ada Lovelace"}},
                        {"raw_author_name": "Grace Hopper"},
                    ],
                    "publication_year": 2024,
                    "cited_by_count": 42,
                    "primary_location": {
                        "source": {"display_name": "Journal of Examples"}
                    },
                    "type": "article",
                }
            ]
        }

        with (
            mock.patch.dict(
                os.environ,
                {
                    "OPENALEX_MAILTO": "researcher@example.org",
                    "OPENALEX_API_KEY": "test-key",
                },
                clear=False,
            ),
            mock.patch.object(fetch_literature.requests, "get") as get,
        ):
            get.return_value = FakeResponse(payload)

            results = fetch_literature._openalex_search("isotope shift", limit=7)

        get.assert_called_once()
        url = get.call_args.args[0]
        params = get.call_args.kwargs["params"]

        self.assertEqual(url, "https://api.openalex.org/works")
        self.assertEqual(params["search"], "isotope shift")
        self.assertEqual(params["per-page"], 7)
        self.assertIn("display_name", params["select"])
        self.assertIn("abstract_inverted_index", params["select"])
        self.assertEqual(params["mailto"], "researcher@example.org")
        self.assertEqual(params["api_key"], "test-key")

        self.assertEqual(len(results), 1)
        paper = results[0]
        self.assertEqual(paper["paperId"], "https://openalex.org/W123")
        self.assertEqual(paper["externalIds"]["DOI"], "10.1234/example")
        self.assertEqual(paper["externalIds"]["OpenAlex"], "https://openalex.org/W123")
        self.assertEqual(paper["title"], "Example Work")
        self.assertEqual(paper["abstract"], "OpenAlex search works.")
        self.assertEqual(paper["authors"], [{"name": "Ada Lovelace"}, {"name": "Grace Hopper"}])
        self.assertEqual(paper["year"], 2024)
        self.assertEqual(paper["citationCount"], 42)
        self.assertEqual(paper["venue"], "Journal of Examples")
        self.assertEqual(paper["publicationTypes"], ["article"])
        self.assertEqual(paper["_provider"], "openalex")

    def test_openalex_search_applies_since_year_filter(self) -> None:
        with mock.patch.object(fetch_literature.requests, "get") as get:
            get.return_value = FakeResponse({"results": []})

            fetch_literature._openalex_search(
                "neutral transition atoms",
                limit=12,
                since_year=2018,
            )

        params = get.call_args.kwargs["params"]
        self.assertEqual(params["filter"], "from_publication_date:2018-01-01")


if __name__ == "__main__":
    unittest.main()

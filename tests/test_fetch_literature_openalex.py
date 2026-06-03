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


if __name__ == "__main__":
    unittest.main()

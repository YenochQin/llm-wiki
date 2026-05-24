import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import research_wiki


class ResearchWikiFindTests(unittest.TestCase):
    def test_find_entities_filters_by_slug_and_serializes_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            papers = root / "papers"
            papers.mkdir()
            (papers / "forest_2014_High.md").write_text(
                """---
title: High resolution laser spectroscopy
date_added: 2026-05-18
tags:
  - benchmark
---

## Problem
""",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                research_wiki.find_entities(
                    str(root),
                    "papers",
                    [("slug", "forest_2014_High")],
                )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["slug"], "forest_2014_High")
        self.assertEqual(payload[0]["date_added"], "2026-05-18")

    def test_find_similar_concept_serializes_frontmatter_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            concepts = root / "concepts"
            foundations = root / "foundations"
            concepts.mkdir()
            foundations.mkdir()
            (concepts / "mcdhf.md").write_text(
                """---
title: MCDHF
aliases:
  - Multiconfiguration Dirac-Hartree-Fock
date_updated: 2026-05-24
key_papers:
  - "[[forest_2014_High]]"
---

## Definition
""",
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                research_wiki.find_similar_concept(str(root), "MCDHF")

            payload = json.loads(stdout.getvalue())

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["slug"], "mcdhf")
        self.assertEqual(payload[0]["score"], 1.0)


if __name__ == "__main__":
    unittest.main()

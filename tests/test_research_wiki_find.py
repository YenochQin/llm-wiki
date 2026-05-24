import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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

    def test_add_edge_accepts_legacy_positional_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            stdout = io.StringIO()
            argv = [
                "research_wiki.py",
                "add-edge",
                str(root),
                "papers/sahoo_2020_Analytic",
                "uses_concept",
                "concepts/isotope-shift",
                "--confidence",
                "high",
                "--evidence",
                "Uses isotope-shift analysis.",
            ]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
                research_wiki.main()

            payload = json.loads(stdout.getvalue())

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(
            payload["edge"],
            "papers/sahoo_2020_Analytic --uses_concept--> concepts/isotope-shift",
        )

    def test_add_edge_legacy_positional_still_requires_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            stdout = io.StringIO()
            argv = [
                "research_wiki.py",
                "add-edge",
                str(root),
                "papers/sahoo_2020_Analytic",
                "uses_concept",
                "concepts/isotope-shift",
                "--confidence",
                "high",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(stdout),
                self.assertRaises(SystemExit) as raised,
            ):
                research_wiki.main()

            payload = json.loads(stdout.getvalue())

        self.assertEqual(raised.exception.code, 1)
        self.assertIn("uses_concept requires --evidence text", payload["errors"])


if __name__ == "__main__":
    unittest.main()

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

    def test_add_edge_missing_wiki_root_reports_configured_alias(self) -> None:
        argv = [
            "research_wiki.py",
            "add-edge",
            "--from",
            "papers/huet_2015_Isotope",
            "--to",
            "concepts/isotope-shift",
            "--type",
            "uses_concept",
            "--evidence",
            "Uses isotope-shift analysis.",
            "--confidence",
            "high",
        ]

        stderr = io.StringIO()
        with (
            mock.patch.object(sys, "argv", argv),
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            research_wiki.main()

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("add-edge '@configured' --from <id>", stderr.getvalue())

    def test_append_log_writes_weekly_skill_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with mock.patch.object(
                research_wiki,
                "datetime",
                wraps=research_wiki.datetime,
            ) as mocked_datetime:
                mocked_datetime.now.return_value = research_wiki.datetime(
                    2026,
                    6,
                    10,
                    12,
                    0,
                    tzinfo=research_wiki.timezone.utc,
                )
                research_wiki.append_log(str(root), "ingest-light | added papers/example")
                research_wiki.append_log(str(root), "ingest | added papers/full")

            log_file = root / "log" / "2026-06-w2.md"
            content = log_file.read_text(encoding="utf-8")

        self.assertEqual(
            content,
            "# log\n\n"
            "## ingest-light\n"
            "[2026-06-10] added papers/example\n\n"
            "## ingest\n"
            "[2026-06-10] added papers/full\n",
        )

    def test_append_log_normalizes_skill_args_into_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with mock.patch.object(
                research_wiki,
                "datetime",
                wraps=research_wiki.datetime,
            ) as mocked_datetime:
                mocked_datetime.now.return_value = research_wiki.datetime(
                    2026,
                    6,
                    3,
                    12,
                    0,
                    tzinfo=research_wiki.timezone.utc,
                )
                research_wiki.append_log(str(root), "check --fix | repaired lint issues")

            log_file = root / "log" / "2026-06-w1.md"
            content = log_file.read_text(encoding="utf-8")

        self.assertEqual(
            content,
            "# log\n\n"
            "## check\n"
            "[2026-06-03] --fix | repaired lint issues\n",
        )


if __name__ == "__main__":
    unittest.main()

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import migrate_log


class MigrateLogTests(unittest.TestCase):
    def test_parse_legacy_log_preserves_multiline_body(self) -> None:
        entries, warnings = migrate_log.parse_legacy_log(
            """## [2026-05-14] ingest | Zhang paper

- Paper: zhang_2024_Variational
- Edges: 4
# LLMWiki Log
## [2026-05-16] check --fix | repaired lint issues
"""
        )

        self.assertEqual(warnings, [])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].skill, "ingest")
        self.assertEqual(
            entries[0].lines,
            [
                "[2026-05-14] Zhang paper",
                "- Paper: zhang_2024_Variational",
                "- Edges: 4",
            ],
        )
        self.assertEqual(entries[1].skill, "check")
        self.assertEqual(
            entries[1].lines, ["[2026-05-16] --fix | repaired lint issues"]
        )

    def test_migrate_log_groups_by_week_and_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "log.md").write_text(
                """# LLMWiki Log

## [2026-05-14] ingest | added paper A
## [2026-05-12] ingest-light | added paper B
## [2026-05-13] ingest | added paper C
""",
                encoding="utf-8",
            )

            result = migrate_log.migrate_log(root, dry_run=False)
            content = (root / "log" / "2026-05-w2.md").read_text(encoding="utf-8")

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entries_found"], 3)
        self.assertEqual(result["entries_to_add"], 3)
        self.assertEqual(
            content,
            "# log\n\n"
            "## ingest\n"
            "[2026-05-14] added paper A\n"
            "[2026-05-13] added paper C\n\n"
            "## ingest-light\n"
            "[2026-05-12] added paper B\n",
        )

    def test_migrate_log_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "log.md").write_text(
                "## [2026-06-03] edit | migrated log format\n",
                encoding="utf-8",
            )

            first = migrate_log.migrate_log(root, dry_run=False)
            second = migrate_log.migrate_log(root, dry_run=False)
            content = (root / "log" / "2026-06-w1.md").read_text(encoding="utf-8")

        self.assertEqual(first["entries_to_add"], 1)
        self.assertEqual(second["entries_to_add"], 0)
        self.assertEqual(second["entries_skipped_existing"], 1)
        self.assertEqual(content.count("[2026-06-03] migrated log format"), 1)

    def test_parse_legacy_log_warns_on_conflict_markers(self) -> None:
        left = "<" * 7
        middle = "=" * 7
        right = ">" * 7
        entries, warnings = migrate_log.parse_legacy_log(
            f"## [2026-06-03] discover | mode=wiki\n{left}\n{middle}\n{right}\n"
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(
            warnings,
            [
                "conflict marker line 2: <<<<<<<",
                "conflict marker line 3: =======",
                "conflict marker line 4: >>>>>>>",
            ],
        )

    def test_rename_old_weekly_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_dir = root / "log"
            log_dir.mkdir()
            (log_dir / "2026-06-01.md").write_text("# log\n", encoding="utf-8")
            (log_dir / "2026-06-15.md").write_text(
                "daily-looking file\n", encoding="utf-8"
            )
            (log_dir / "notes.md").write_text("not a weekly log\n", encoding="utf-8")

            dry_run = migrate_log.rename_old_weekly_logs(root, dry_run=True)
            result = migrate_log.rename_old_weekly_logs(root, dry_run=False)

            self.assertEqual(
                dry_run["renamed"],
                [
                    {
                        "from": str(log_dir / "2026-06-01.md"),
                        "to": str(log_dir / "2026-06-w1.md"),
                    }
                ],
            )
            self.assertEqual(result["status"], "ok")
            self.assertFalse((log_dir / "2026-06-01.md").exists())
            self.assertTrue((log_dir / "2026-06-w1.md").exists())
            self.assertTrue((log_dir / "2026-06-15.md").exists())
            self.assertTrue((log_dir / "notes.md").exists())

    def test_rename_wrong_log_extension_to_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_dir = root / "log"
            log_dir.mkdir()
            (log_dir / "2026-06-w1.log").write_text("# log\n", encoding="utf-8")

            result = migrate_log.rename_old_weekly_logs(root, dry_run=False)

            self.assertEqual(
                result["renamed"],
                [
                    {
                        "from": str(log_dir / "2026-06-w1.log"),
                        "to": str(log_dir / "2026-06-w1.md"),
                    }
                ],
            )
            self.assertFalse((log_dir / "2026-06-w1.log").exists())
            self.assertTrue((log_dir / "2026-06-w1.md").exists())


if __name__ == "__main__":
    unittest.main()

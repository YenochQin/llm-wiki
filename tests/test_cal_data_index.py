import json
import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import cal_data_index  # noqa: E402


class CalDataIndexTests(unittest.TestCase):
    def test_build_reports_summarizes_run_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            run_dir = raw / "cal_data" / "run-2026-07-08"
            run_dir.mkdir(parents=True)
            (run_dir / "metrics.csv").write_text(
                "model,split,accuracy\nbase,test,0.82\nlarge,test,0.91\n",
                encoding="utf-8",
            )
            (run_dir / "samples.jsonl").write_text(
                '{"id": 1, "ok": true}\n{"id": 2, "ok": false}\n',
                encoding="utf-8",
            )
            (run_dir / "config.yaml").write_text("seed: 42\n", encoding="utf-8")
            (run_dir / "plot.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            result = cal_data_index.build_reports(
                cal_data_index.IndexRequest(wiki_root=wiki, data_root=raw)
            )

            report = wiki / "experiments" / "cal_reports" / "run-2026-07-08.md"
            content = report.read_text(encoding="utf-8")
            index_content = (wiki / "experiments" / "cal_reports" / "index.md").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result.run_count, 1)
        self.assertIn("[[run-2026-07-08]]", index_content)
        self.assertIn("[metrics.csv](../../../raw/cal_data/run-2026-07-08/metrics.csv)", content)
        self.assertIn("| model | split | accuracy |", content)
        self.assertIn("| base | test | 0.82 |", content)
        self.assertIn("```jsonl", content)
        self.assertIn('{"id": 1, "ok": true}', content)
        self.assertIn("![plot.png](../../../raw/cal_data/run-2026-07-08/plot.png)", content)
        self.assertNotIn("## Notes", content)

    def test_cli_uses_configured_raw_root_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            wiki = root / "vault"
            raw = root / "raw"
            project.mkdir()
            wiki.mkdir()
            config_path = project / "paths.json"
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "test",
                        "profiles": {
                            "test": {
                                "wiki_root": str(wiki),
                                "raw_root": str(raw),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            run_dir = raw / "cal_data" / "trial"
            run_dir.mkdir(parents=True)
            (run_dir / "metrics.csv").write_text("name,value\nx,1\n", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cal_data_index._main(
                    ["@configured", "--paths-config", str(config_path)]
                )

            report = wiki / "experiments" / "cal_reports" / "trial.md"
            report_exists = report.exists()

        self.assertEqual(exit_code, 0)
        self.assertIn("generated 2 report file(s)", stdout.getvalue())
        self.assertTrue(report_exists)

    def test_cli_can_index_legacy_wiki_root_data_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            wiki = root / "vault"
            raw = root / "raw"
            project.mkdir()
            wiki.mkdir()
            config_path = project / "paths.json"
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "test",
                        "profiles": {
                            "test": {
                                "wiki_root": str(wiki),
                                "raw_root": str(raw),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            run_dir = wiki / "temp" / "cal_data" / "trial"
            run_dir.mkdir(parents=True)
            (run_dir / "metrics.csv").write_text("name,value\nx,1\n", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cal_data_index._main(
                    [
                        "@configured",
                        "--paths-config",
                        str(config_path),
                        "--data-root",
                        "@configured",
                        "--data-dir",
                        "temp/cal_data",
                    ]
                )

            report = wiki / "experiments" / "cal_reports" / "trial.md"
            report_exists = report.exists()

        self.assertEqual(exit_code, 0)
        self.assertIn("generated 2 report file(s)", stdout.getvalue())
        self.assertTrue(report_exists)

    def test_build_reports_removes_stale_report_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            old_run = raw / "cal_data" / "old-run"
            new_run = raw / "cal_data" / "new-run"
            old_run.mkdir(parents=True)
            (old_run / "metrics.csv").write_text("name,value\nold,1\n", encoding="utf-8")

            cal_data_index.build_reports(cal_data_index.IndexRequest(wiki_root=wiki, data_root=raw))
            old_report = wiki / "experiments" / "cal_reports" / "old-run.md"
            old_report.write_text(
                old_report.read_text(encoding="utf-8").replace(
                    "<!-- generated_by: cal_data_index -->\n", ""
                ),
                encoding="utf-8",
            )
            shutil.rmtree(old_run)
            new_run.mkdir()
            (new_run / "metrics.csv").write_text("name,value\nnew,2\n", encoding="utf-8")

            cal_data_index.build_reports(cal_data_index.IndexRequest(wiki_root=wiki, data_root=raw))

            report_root = wiki / "experiments" / "cal_reports"
            self.assertFalse((report_root / "old-run.md").exists())
            self.assertTrue((report_root / "new-run.md").exists())

    def test_build_reports_preserves_user_authored_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            run_dir = raw / "cal_data" / "run"
            report_root = wiki / "experiments" / "cal_reports"
            run_dir.mkdir(parents=True)
            report_root.mkdir(parents=True)
            (run_dir / "metrics.csv").write_text("name,value\nx,1\n", encoding="utf-8")
            manual_note = report_root / "manual-notes.md"
            manual_note.write_text("# Manual notes\n\nKeep this.\n", encoding="utf-8")

            cal_data_index.build_reports(cal_data_index.IndexRequest(wiki_root=wiki, data_root=raw))

            self.assertEqual(manual_note.read_text(encoding="utf-8"), "# Manual notes\n\nKeep this.\n")

    def test_scoped_refresh_preserves_reports_from_other_data_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            ca_like = raw / "cal_data" / "Ni_Ca-like"
            ni_ml = raw / "cal_data" / "Ni_I_ML"
            ca_like.mkdir(parents=True)
            ni_ml.mkdir(parents=True)
            (ca_like / "levels.csv").write_text("name,value\nca,1\n", encoding="utf-8")
            (ni_ml / "levels.csv").write_text("name,value\nni,2\n", encoding="utf-8")

            cal_data_index.build_reports(
                cal_data_index.IndexRequest(
                    wiki_root=wiki,
                    data_root=raw.resolve(),
                    data_dir="cal_data/Ni_Ca-like",
                )
            )
            cal_data_index.build_reports(
                cal_data_index.IndexRequest(
                    wiki_root=wiki,
                    data_root=raw.resolve(),
                    data_dir="cal_data/Ni_I_ML",
                )
            )

            report_root = wiki / "experiments" / "cal_reports"
            report_names = {path.name for path in report_root.glob("*.md")}
            index_content = (report_root / "index.md").read_text(encoding="utf-8")

        self.assertIn("ni-ca-like.md", report_names)
        self.assertIn("ni-i-ml.md", report_names)
        self.assertIn("[[ni-ca-like]]", index_content)
        self.assertIn("[[ni-i-ml]]", index_content)
        self.assertIn("run_count: 2", index_content)

    def test_separate_scoped_refreshes_disambiguate_slug_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = (root / "raw").resolve()
            for directory, value in (("Run-A", "first"), ("run_a", "second")):
                run = raw / "cal_data" / directory
                run.mkdir(parents=True)
                (run / "metrics.csv").write_text(
                    f"name,value\n{value},1\n", encoding="utf-8"
                )
                cal_data_index.build_reports(
                    cal_data_index.IndexRequest(
                        wiki_root=wiki,
                        data_root=raw,
                        data_dir=f"cal_data/{directory}",
                    )
                )

            report_root = wiki / "experiments" / "cal_reports"
            report_names = {path.name for path in report_root.glob("*.md")}
            index_content = (report_root / "index.md").read_text(encoding="utf-8")

        self.assertIn("run-a.md", report_names)
        self.assertIn("run-a-2.md", report_names)
        self.assertIn("run_count: 2", index_content)

    def test_build_reports_disambiguates_slug_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            raw = root / "raw"
            run_a = raw / "cal_data" / "Run-A"
            run_b = raw / "cal_data" / "run_a"
            run_a.mkdir(parents=True)
            run_b.mkdir()
            (run_a / "metrics.csv").write_text("name,value\nfirst,1\n", encoding="utf-8")
            (run_b / "metrics.csv").write_text("name,value\nsecond,2\n", encoding="utf-8")

            result = cal_data_index.build_reports(
                cal_data_index.IndexRequest(wiki_root=wiki, data_root=raw)
            )
            report_root = wiki / "experiments" / "cal_reports"
            index_content = (report_root / "index.md").read_text(encoding="utf-8")
            report_names = {path.name for path in report_root.glob("*.md")}

        self.assertEqual(result.run_count, 2)
        self.assertEqual(result.report_count, 3)
        self.assertIn("run-a.md", report_names)
        self.assertIn("run-a-2.md", report_names)
        self.assertIn("[[run-a]]", index_content)
        self.assertIn("[[run-a-2]]", index_content)


if __name__ == "__main__":
    unittest.main()

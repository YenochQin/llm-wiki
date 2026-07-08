import json
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import cal_data_index  # noqa: E402


class CalDataIndexTests(unittest.TestCase):
    def test_build_reports_summarizes_run_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp)
            run_dir = wiki / "temp" / "cal_data" / "run-2026-07-08"
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
                cal_data_index.IndexRequest(wiki_root=wiki)
            )

            report = wiki / "experiments" / "cal_reports" / "run-2026-07-08.md"
            content = report.read_text(encoding="utf-8")
            index_content = (wiki / "experiments" / "cal_reports" / "index.md").read_text(
                encoding="utf-8"
            )

        self.assertEqual(result.run_count, 1)
        self.assertIn("[[run-2026-07-08]]", index_content)
        self.assertIn("[metrics.csv](../../temp/cal_data/run-2026-07-08/metrics.csv)", content)
        self.assertIn("| model | split | accuracy |", content)
        self.assertIn("| base | test | 0.82 |", content)
        self.assertIn("```jsonl", content)
        self.assertIn('{"id": 1, "ok": true}', content)
        self.assertIn("![plot.png](../../temp/cal_data/run-2026-07-08/plot.png)", content)

    def test_cli_uses_paths_config_for_configured_wiki_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            wiki = root / "vault"
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
                                "raw_root": str(root / "raw"),
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
                    ["@configured", "--paths-config", str(config_path)]
                )

            report = wiki / "experiments" / "cal_reports" / "trial.md"
            report_exists = report.exists()

        self.assertEqual(exit_code, 0)
        self.assertIn("generated 2 report file(s)", stdout.getvalue())
        self.assertTrue(report_exists)


if __name__ == "__main__":
    unittest.main()

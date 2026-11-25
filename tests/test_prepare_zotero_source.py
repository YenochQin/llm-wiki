import io
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import prepare_paper_source
import prepare_zotero_source
from _paths import RuntimePaths


class PrepareZoteroSourceTests(unittest.TestCase):
    def test_select_pdf_requires_one_existing_attachment(self) -> None:
        candidate = {"pdf_paths": ["C:/Zotero/storage/A/paper.pdf"]}
        self.assertEqual(
            prepare_zotero_source.select_pdf(candidate),
            Path("C:/Zotero/storage/A/paper.pdf"),
        )

    def test_select_pdf_rejects_ambiguous_attachment(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            prepare_zotero_source.select_pdf(
                {"pdf_paths": ["a.pdf", "b.pdf"]}
            )

    def test_build_manifest_keeps_pdf_source_and_embeds_metadata(self) -> None:
        metadata = {
            "status": "ok",
            "source": "zotero-local-api",
            "metadata": {
                "item_key": "ABC123",
                "title": "A paper",
                "paper_slug": "doe2019paper",
                "citation_key": "doe2019paper",
                "bibtex": "@article{doe2019paper}",
            },
        }
        manifest = prepare_zotero_source.build_manifest(
            candidate={"item_key": "ABC123", "pdf_paths": ["paper.pdf"]},
            metadata_result=metadata,
            prepared_result={"canonical_ingest_path": "source.md", "usable": True},
            metadata_path=Path(".checkpoints/ingest/ABC123/metadata.json"),
        )
        self.assertEqual(manifest["source_pdf"], "paper.pdf")
        self.assertEqual(manifest["metadata_path"], ".checkpoints/ingest/ABC123/metadata.json")
        self.assertEqual(manifest["metadata"]["paper_slug"], "doe2019paper")

    def test_run_writes_checkpoint_and_passes_pdf_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata_output = root / ".checkpoints" / "ingest" / "ABC123" / "metadata.json"
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF")
            paths = RuntimePaths(
                project_root=root,
                wiki_root=root / "wiki",
                raw_root=root / "raw",
                config_path=root / "config" / "paths.toml",
                used_config=False,
            )
            args = Namespace(
                item_key="ABC123",
                zotero_root=None,
                api_base="",
                timeout=5,
                output_dir=str(root / "wiki" / "sources" / "papers"),
                cache_root=str(root / ".checkpoints" / "mineru-cache"),
                metadata_output=str(metadata_output),
                paths_config=paths.config_path,
                overwrite=False,
            )
            metadata = {
                "item_key": "ABC123",
                "title": "A paper",
                "citation_key": "doe2019paper",
                "authors": ["Jane Doe"],
                "year": 2019,
                "bibtex": "@article{doe2019paper}",
            }

            with (
                patch("prepare_zotero_source.load_paths", return_value=paths),
                patch(
                    "prepare_zotero_source.find_zotero_pdf.find",
                    return_value={
                        "status": "ok",
                        "candidates": [{"item_key": "ABC123", "pdf_paths": [str(pdf)]}],
                    },
                ),
                patch("prepare_zotero_source.fetch_zotero_metadata.fetch_item", return_value=metadata),
                patch(
                    "prepare_zotero_source.prepare_paper_source.prepare_paper_source",
                    return_value={"canonical_ingest_path": "source.md", "usable": True},
                ) as prepare,
            ):
                result = prepare_zotero_source.run(args)

            self.assertEqual(json_load(metadata_output)["metadata"]["citation_key"], "doe2019paper")
            self.assertTrue(metadata_output.with_name("manifest.json").exists())
            self.assertEqual(result["status"], "ok")
            self.assertEqual(prepare.call_args.args[0], pdf)
            self.assertEqual(prepare.call_args.kwargs["citation_key"], "doe2019paper")

    def test_both_cli_entrypoints_use_the_configured_mineru_backend(self) -> None:
        def write_ocr_fixture(pdf: Path, cache: Path, _language: str) -> None:
            (cache / f"{pdf.stem}.md").write_text(
                "# Fixture Paper\n\n## Abstract\n\nThis is a test.\n", encoding="utf-8"
            )
            (cache / f"{pdf.stem}.json").write_text("[]", encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            paths = RuntimePaths(
                project_root=root,
                wiki_root=root / "wiki",
                raw_root=root / "raw",
                config_path=root / "paths.toml",
                used_config=False,
            )
            cases = (
                (prepare_paper_source, ["--source", str(pdf)]),
                (
                    prepare_zotero_source,
                    ["--item-key", "ABC123", "--metadata-output", str(root / "metadata.json")],
                ),
            )
            with (
                patch.dict("os.environ", {"MINERU_BACKEND": "local"}),
                patch.object(prepare_paper_source, "load_paths", return_value=paths),
                patch.object(prepare_zotero_source, "load_paths", return_value=paths),
                patch.object(
                    prepare_zotero_source.find_zotero_pdf,
                    "find",
                    return_value={
                        "status": "ok",
                        "candidates": [{"item_key": "ABC123", "pdf_paths": [str(pdf)]}],
                    },
                ),
                patch.object(
                    prepare_zotero_source.fetch_zotero_metadata,
                    "fetch_item",
                    return_value={"title": "Fixture Paper"},
                ),
                patch("_mineru._extract_via_api", side_effect=RuntimeError("unexpected cloud OCR")) as api,
                patch("_mineru._extract_via_local", side_effect=write_ocr_fixture) as local,
            ):
                for entrypoint, arguments in cases:
                    with self.subTest(entrypoint=entrypoint.__name__):
                        api.reset_mock()
                        local.reset_mock()
                        argv = [
                            entrypoint.__name__, *arguments,
                            "--output-dir", str(root / entrypoint.__name__ / "sources"),
                            "--cache-root", str(root / entrypoint.__name__ / "cache"),
                        ]
                        stdout = io.StringIO()
                        with (
                            patch.object(sys, "argv", argv),
                            redirect_stdout(stdout),
                            redirect_stderr(io.StringIO()),
                        ):
                            entrypoint.main()
                        api.assert_not_called()
                        local.assert_called_once()
                        result = json.loads(stdout.getvalue())
                        self.assertTrue(result.get("prepared", result)["usable"])


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

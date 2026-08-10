import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

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
                config_path=root / "config" / "paths.json",
                used_config=False,
                profile="test",
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


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

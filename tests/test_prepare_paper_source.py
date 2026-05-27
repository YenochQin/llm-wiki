import sys
import unittest
from pathlib import Path, PureWindowsPath


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import prepare_paper_source


class PreparePaperSourcePathTests(unittest.TestCase):
    def test_portable_pdf_source_rewrites_windows_zotero_storage_path(self) -> None:
        path = PureWindowsPath(
            r"E:\Literatures\Zotero\data\storage\4JD8LMPB\Paper.pdf"
        )

        self.assertEqual(
            prepare_paper_source._portable_pdf_source(path),
            "${Zotero data directory}/storage/4JD8LMPB/Paper.pdf",
        )

    def test_portable_pdf_source_preserves_non_zotero_path(self) -> None:
        path = Path("/tmp/raw/papers/Paper.pdf")

        self.assertEqual(prepare_paper_source._portable_pdf_source(path), str(path))


if __name__ == "__main__":
    unittest.main()

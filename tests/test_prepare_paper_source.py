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


class PreparePaperSourceTitleTests(unittest.TestCase):
    def test_cover_title_match_allows_cover_noise_prefix(self) -> None:
        title = (
            "PAPER Large-scale multiconfiguration Dirac-Hartree-Fock "
            "calculations of atomic data"
        )
        heading = (
            "Large-scale multiconfiguration Dirac-Hartree-Fock "
            "calculations of atomic data"
        )

        self.assertTrue(
            prepare_paper_source._cover_title_heading_matches(heading, title)
        )

    def test_title_match_does_not_drop_similar_numbered_section(self) -> None:
        title = (
            "The Gaia-ESO Survey: Homogenisation of stellar parameters "
            "and elemental abundances"
        )
        full_md = f"""# {title}

Opening text.

## 3.2. The homogenisation flow: From stellar parameters to elemental abundances

Section content that must remain.
"""

        body, _, _, _ = prepare_paper_source._transform_markdown(
            full_md,
            "gaia-eso",
            title,
        )

        self.assertIn(
            "3.2. The homogenisation flow: From stellar parameters to elemental abundances",
            body,
        )
        self.assertIn("Section content that must remain.", body)

    def test_plain_text_title_starts_body_when_mineru_emits_no_markdown_headings(self) -> None:
        title = "Bose-Einstein Condensation of Erbium"
        full_md = f"""{title}

K. Aikawa, A. Frisch, and F. Ferlaino

We report on the achievement of Bose-Einstein condensation of erbium atoms.

DOI: 10.1103/PhysRevLett.108.210401
"""

        body, _, _, _ = prepare_paper_source._transform_markdown(
            full_md,
            "aikawa-2012-erbium",
            title,
        )

        self.assertIn(f"# {title}", body)
        self.assertIn(
            "We report on the achievement of Bose-Einstein condensation of erbium atoms.",
            body,
        )


if __name__ == "__main__":
    unittest.main()

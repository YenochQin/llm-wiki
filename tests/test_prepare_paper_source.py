import json
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath

import frontmatter

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

    def test_prepare_preserves_multilevel_titles_sections_and_figure_association(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "filename-unrelated-to-title.pdf"
            pdf.write_bytes(b"%PDF-1.7\n")
            cache_root = root / "cache"
            cache = cache_root / prepare_paper_source._sha16_of_file(pdf)
            cache.mkdir(parents=True)
            (cache / "paper.md").write_text(
                "## MinerU Integration Test\n\n## Abstract\n\nAbstract text.\n\n"
                "### 1 Introduction\n\nBody text.\n\n![Figure 1](images/figure.jpg)\n\n"
                "![Figure 2](images/chart.jpg)\n\n"
                "## References\n\nReference text.\n",
                encoding="utf-8",
            )
            (cache / "paper.json").write_text(json.dumps([
                {"type": "text", "text": "MinerU Integration Test", "text_level": 2, "page_idx": 0},
                {"type": "text", "text": "Abstract", "text_level": 2, "page_idx": 0},
                {"type": "text", "text": "Abstract text.", "page_idx": 0},
                {"type": "text", "text": "1 Introduction", "text_level": 3, "page_idx": 1},
                {"type": "image", "img_path": "images/figure.jpg", "img_caption": ["Figure 1: Test image."], "page_idx": 1},
                {"type": "chart", "img_path": "images/chart.jpg", "chart_caption": ["Figure 2: Test chart $ x ^ { 2 } $."], "page_idx": 1},
                {"type": "text", "text": "References", "text_level": 2, "page_idx": 2},
            ]), encoding="utf-8")
            (cache / "images").mkdir()
            (cache / "images" / "figure.jpg").write_bytes(b"image fixture")
            (cache / "images" / "chart.jpg").write_bytes(b"chart fixture")

            result = prepare_paper_source.prepare(
                pdf, root / "raw", cache_root=cache_root,
                output_dir=root / "prepared", project_root=root,
            )
            post = frontmatter.load(root / result["prepared_path"])

            self.assertTrue(result["usable"])
            self.assertEqual(result["title"], "MinerU Integration Test")
            self.assertIn("# MinerU Integration Test", post.content)
            self.assertIn("Reference text.", post.content)
            self.assertEqual(post["totalPages"], 3)
            self.assertEqual([s["heading"] for s in post["sections"]], [
                "MinerU Integration Test", "Abstract", "1 Introduction", "References",
            ])
            self.assertEqual(post["figures"][0]["section"], "1 Introduction")
            self.assertEqual([f["label"] for f in post["figures"]], ["Figure 1", "Figure 2"])
            self.assertEqual(post["figures"][1]["section"], "1 Introduction")
            self.assertEqual(post["figures"][1]["caption"], "Figure 2: Test chart $x^{2}$.")
            self.assertTrue((root / "prepared" / post["figures"][0]["path"]).exists())
            self.assertTrue((root / "prepared" / post["figures"][1]["path"]).exists())

    def test_abstract_excerpt_excludes_authors_and_following_sections(self) -> None:
        body = (
            "# Paper title\n\nAuthor and institution.\n\n## ABSTRACT\n\n"
            "The actual abstract.\n\n# 1. Introduction\n\nFollowing section.\n"
        )

        self.assertEqual(
            prepare_paper_source._build_abstract_excerpt(body),
            "The actual abstract.",
        )

    def test_cached_manifest_is_refreshed_with_current_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            md = cache / "paper.md"
            blocks = cache / "paper.json"
            md.write_text("# MinerU Integration Test\n", encoding="utf-8")
            blocks.write_text(json.dumps([
                {"type": "text", "text": "MinerU Integration Test", "text_level": 1, "page_idx": 0},
            ]), encoding="utf-8")
            manifest = cache / "manifest.json"
            manifest.write_text('{"sections": [], "allFigures": [], "totalPages": 1}', encoding="utf-8")

            prepare_paper_source._normalize_cache(cache, md, blocks)

            refreshed = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(prepare_paper_source._detect_title(refreshed), "MinerU Integration Test")

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

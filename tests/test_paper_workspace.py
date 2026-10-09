import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from _paths import load_paths, require_paper_root, resolve_runtime_path, write_paths_config
from paper_workspace import create_workspace, draft_directory, fork_workspace, list_workspaces, paper_directory, resolve_workspace

DRAFT = "2026-10-06-initial"


class PaperWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / "code"
        self.project.mkdir()
        self.config = self.project / "config" / "paths.json"
        self.config.parent.mkdir()
        self.env = patch.dict(os.environ, {
            "LLM_WIKI_PATH_PROFILE": "test",
            "LLM_WIKI_PAPER_ROOT": "",
            "LLM_WIKI_WIKI_ROOT": "",
            "LLM_WIKI_RAW_ROOT": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.write_config(self.root / "papers")

    def write_config(self, paper_root: Path | None) -> None:
        profile = {"wiki_root": str(self.root / "wiki"), "raw_root": str(self.root / "raw")}
        if paper_root is not None:
            profile["paper_root"] = str(paper_root)
        self.config.write_text(json.dumps({"active_profile": "auto", "profiles": {"test": profile}}))

    def paths(self, **kwargs):
        return load_paths(config_path=self.config, project_root=self.project, **kwargs)

    def test_profile_and_alias_subdirectory(self) -> None:
        paths = self.paths()
        self.assertEqual(paths.profile, "test")
        expected = self.root / "papers" / "atomic-radials" / DRAFT / "paper.tex"
        self.assertEqual(resolve_runtime_path(f"@paper-root/atomic-radials/{DRAFT}/paper.tex", paths, role="paper"), expected)
        self.assertEqual(resolve_runtime_path("@configured-papers", paths, role="paper"), self.root / "papers")
        self.assertEqual(resolve_runtime_path("@configured/outputs/report.md", paths, role="report"), self.root / "wiki" / "outputs" / "report.md")

    def test_environment_and_explicit_argument_precedence(self) -> None:
        os.environ["LLM_WIKI_PAPER_ROOT"] = str(self.root / "env-papers")
        self.assertEqual(self.paths().paper_root, self.root / "env-papers")
        self.assertEqual(self.paths(paper_root=self.root / "argument-papers").paper_root, self.root / "argument-papers")

    def test_legacy_flat_configuration(self) -> None:
        self.config.write_text(json.dumps({"paper_root": str(self.root / "flat-papers")}))
        self.assertEqual(self.paths().paper_root, self.root / "flat-papers")

    def test_missing_root_does_not_break_legacy_wiki_tools_or_create_fallback(self) -> None:
        self.write_config(None)
        paths = self.paths()
        self.assertIsNone(paths.paper_root)
        self.assertEqual(resolve_runtime_path("@configured", paths, role="wiki"), self.root / "wiki")
        with self.assertRaisesRegex(ValueError, "not configured"):
            create_workspace(paths, "first-paper", DRAFT)
        self.assertFalse((self.project / "paper").exists())

    def test_no_in_repository_or_overlapping_roots(self) -> None:
        for root in (self.project / "papers", self.project, self.root, self.root / "wiki" / "drafts", self.root / "raw"):
            with self.subTest(root=root), self.assertRaises(ValueError):
                require_paper_root(self.paths(paper_root=root))

    def test_symlink_root_to_repository_is_rejected(self) -> None:
        link = self.root / "paper-link"
        link.symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            create_workspace(self.paths(paper_root=link), "first-paper", DRAFT)

    def test_traversal_and_unknown_alias_are_rejected(self) -> None:
        for value in ("@paper-root/../code", "@paper-root//tmp", "@unknown/x"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_runtime_path(value, self.paths(), role="paper")

    def test_invalid_ids_are_rejected_before_writing(self) -> None:
        for value in ("", "../escape", "a/b", "a\\b", "Upper", "a b", "a--b", "a" * 97, "rmcdhf-2026-10-06"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                create_workspace(self.paths(), value, DRAFT)
        self.assertFalse((self.root / "papers").exists())

    def test_multiple_papers_and_resume_preserve_manuscript(self) -> None:
        paths = self.paths()
        first = create_workspace(paths, "first-paper", DRAFT)
        second = create_workspace(paths, "second-paper", DRAFT)
        source = first / "paper.tex"
        source.write_text("existing standalone manuscript")
        self.assertEqual(resolve_workspace(paths, "first-paper", DRAFT), first)
        self.assertEqual(source.read_text(), "existing standalone manuscript")
        self.assertEqual(list_workspaces(paths), [
            {"paper_id": "first-paper", "draft_id": DRAFT, "draft_dir": str(first)},
            {"paper_id": "second-paper", "draft_id": DRAFT, "draft_dir": str(second)},
        ])

    def test_create_refuses_existing_paper(self) -> None:
        first = create_workspace(self.paths(), "first-paper", DRAFT)
        source = first / "paper.tex"
        source.write_text("preserve me")
        with self.assertRaises(FileExistsError):
            create_workspace(self.paths(), "first-paper", DRAFT)
        self.assertEqual(source.read_text(), "preserve me")

    def test_resolve_is_read_only_for_missing_paper(self) -> None:
        with self.assertRaises(FileNotFoundError):
            resolve_workspace(self.paths(), "missing-paper", DRAFT)
        self.assertFalse((self.root / "papers").exists())
        self.assertEqual(list_workspaces(self.paths()), [])

    def test_symlink_child_cannot_escape_root(self) -> None:
        root = self.root / "papers"
        root.mkdir()
        (root / "escaped-paper").symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            paper_directory(self.paths(), "escaped-paper")
        self.assertEqual(list_workspaces(self.paths()), [])

    def test_wiki_path_reconfiguration_preserves_paper_root(self) -> None:
        with patch("_paths.current_platform_profile", return_value="test"):
            write_paths_config(self.config, self.root / "new-wiki", self.root / "new-raw")
        self.assertEqual(self.paths().paper_root, self.root / "papers")

    def test_cli_create_resolve_list_and_collision(self) -> None:
        script = Path(__file__).resolve().parents[1] / "tools" / "paper_workspace.py"
        def run(*args):
            result = subprocess.run([sys.executable, str(script), *args, "--paths-config", str(self.config)], capture_output=True, text=True, check=False)
            return result.returncode, json.loads(result.stdout)
        code, created = run("create", "cli-paper", DRAFT)
        self.assertEqual(code, 0)
        self.assertEqual(created["draft_dir"], str(self.root / "papers" / "cli-paper" / DRAFT))
        self.assertEqual(run("resolve", "cli-paper", DRAFT), (0, created))
        self.assertEqual(run("list")[1]["drafts"][0]["paper_id"], "cli-paper")
        self.assertEqual(run("create", "cli-paper", DRAFT)[0], 2)
        second_id = "2026-10-06-restructure"
        code, forked = run("fork", "cli-paper", DRAFT, second_id)
        self.assertEqual(code, 0)
        self.assertEqual(forked["draft_id"], second_id)
        self.assertEqual(len(run("list", "cli-paper")[1]["drafts"]), 2)


    def test_invalid_draft_ids_and_dates_are_rejected_before_writing(self) -> None:
        for value in ("initial", "2026-02-29-initial", "2026-13-01-initial", "2026-10-06-../escape", "2026-10-06-Upper", "2026-10-06-a/b"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                create_workspace(self.paths(), "atomic-radials", value)
        self.assertFalse((self.root / "papers").exists())

    def test_fork_preserves_original_and_keeps_versions_independent(self) -> None:
        paths = self.paths()
        first = create_workspace(paths, "atomic-radials", DRAFT)
        (first / "paper.tex").write_text("original structure")
        (first / "evidence" / "results.csv").write_text("recorded measurements")
        second_id = "2026-10-06-restructure"
        second = fork_workspace(paths, "atomic-radials", DRAFT, second_id)
        self.assertEqual((second / "paper.tex").read_text(), "original structure")
        self.assertEqual((second / "evidence" / "results.csv").read_text(), "recorded measurements")
        (second / "paper.tex").write_text("new structure")
        (second / "reviews" / "evaluation.md").write_text("assessment of the new structure")
        self.assertEqual((first / "paper.tex").read_text(), "original structure")
        self.assertFalse((first / "reviews" / "evaluation.md").exists())
        metadata = json.loads((second / "draft.json").read_text())
        self.assertEqual(metadata["parent_draft_id"], DRAFT)
        self.assertEqual(metadata["draft_id"], second_id)
        self.assertEqual(len(list_workspaces(paths, "atomic-radials")), 2)

    def test_fork_refuses_existing_destination_and_self(self) -> None:
        paths = self.paths()
        first = create_workspace(paths, "atomic-radials", DRAFT)
        (first / "paper.tex").write_text("preserve me")
        with self.assertRaises(FileExistsError):
            fork_workspace(paths, "atomic-radials", DRAFT, DRAFT)
        second_id = "2026-10-06-second"
        second = create_workspace(paths, "atomic-radials", second_id)
        (second / "paper.tex").write_text("second manuscript")
        with self.assertRaises(FileExistsError):
            fork_workspace(paths, "atomic-radials", DRAFT, second_id)
        self.assertEqual((second / "paper.tex").read_text(), "second manuscript")

    def test_fork_rejects_symbolic_link_to_external_content(self) -> None:
        paths = self.paths()
        first = create_workspace(paths, "atomic-radials", DRAFT)
        (first / "evidence" / "outside").symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            fork_workspace(paths, "atomic-radials", DRAFT, "2026-10-06-second")
        self.assertFalse((first.parent / "2026-10-06-second").exists())

    def test_draft_symlink_cannot_select_another_version(self) -> None:
        paths = self.paths()
        first = create_workspace(paths, "atomic-radials", DRAFT)
        link_id = "2026-10-06-link"
        (first.parent / link_id).symlink_to(first, target_is_directory=True)
        with self.assertRaises(ValueError):
            draft_directory(paths, "atomic-radials", link_id)
        self.assertEqual(len(list_workspaces(paths, "atomic-radials")), 1)

    def test_list_can_select_one_topic(self) -> None:
        paths = self.paths()
        create_workspace(paths, "first-paper", DRAFT)
        create_workspace(paths, "second-paper", DRAFT)
        selected = list_workspaces(paths, "first-paper")
        self.assertEqual([item["paper_id"] for item in selected], ["first-paper"])


if __name__ == "__main__":
    unittest.main()

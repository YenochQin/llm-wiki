import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from _paths import load_paths, resolve_runtime_path


class ResolvePathAliasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.project = self.root / "code"
        (self.project / "tools").mkdir(parents=True)
        (self.project / "pyproject.toml").write_text("", encoding="utf-8")
        self.config = self.project / "paths.toml"
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("LLM_WIKI_")}

    def configure(self, root=None, **switches):
        root = root or self.root / "vault"
        lines = ["[wiki]", f"root_dir = {json.dumps(str(root))}"]
        lines.extend(f"{key} = {str(value).lower()}" for key, value in switches.items())
        self.config.write_text("\n".join([*lines, "[zotero]", ""]))

    def resolve(self, *aliases, env=None):
        result = subprocess.run(
            [sys.executable, str(TOOLS / "resolve_path_alias.py"),
             *aliases, "--paths-config", str(self.config), "--json"],
            cwd=self.project, env=self.env if env is None else env,
            capture_output=True, text=True, check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_missing_configuration_fails_without_creating_content(self):
        for alias, name in (("@configured", "wiki_root"), ("@raw-root", "raw_root"),
                            ("@paper-root", "paper_root")):
            with self.subTest(alias=alias):
                code, data = self.resolve(alias)
                self.assertEqual(code, 2)
                self.assertEqual(data["status"], "error")
                self.assertIn(f"{name} is not configured", data["message"])
        self.assertFalse((self.project / "wiki").exists())
        self.assertFalse((self.project / "raw").exists())
        self.assertFalse(self.config.exists())

    def test_unused_roots_do_not_block_wiki(self):
        self.configure(paper_draft=False)
        code, data = self.resolve("@configured/sources/new.md")
        self.assertEqual(code, 0)
        self.assertEqual(data["paths"]["@configured/sources/new.md"], str(self.root / "vault/wiki/sources/new.md"))
        self.assertFalse((self.root / "vault").exists())

    def test_raw_configuration_does_not_require_paper(self):
        self.configure(raw=True)
        code, data = self.resolve("@raw-root")
        self.assertEqual(code, 0)
        self.assertEqual(data["paths"]["@raw-root"], str(self.root / "vault/raw"))

    def test_paper_configuration_does_not_require_raw(self):
        self.configure(paper_draft=True)
        code, data = self.resolve("@paper-root")
        self.assertEqual(code, 0)
        self.assertEqual(data["paths"]["@paper-root"], str(self.root / "vault/paper_draft"))

    def test_environment_override_counts_as_configuration(self):
        env = {**self.env, "LLM_WIKI_WIKI_ROOT": str(self.root / "environment-vault")}
        code, data = self.resolve("@configured", env=env)
        self.assertEqual(code, 0)
        self.assertFalse(data["used_config"])
        self.assertEqual(data["paths"]["@configured"], str(self.root / "environment-vault"))

    def test_environment_override_takes_precedence_over_invalid_configured_root(self):
        self.configure(root=self.project)
        env = {**self.env, "LLM_WIKI_WIKI_ROOT": str(self.root / "vault")}
        self.assertEqual(self.resolve("@configured", env=env)[0], 0)

    def test_requested_directory_must_be_enabled(self):
        self.configure(raw=False)
        self.assertEqual(self.resolve("@raw-root")[0], 2)
        self.configure(raw=True)
        self.assertEqual(self.resolve("@raw-root")[0], 0)

    def test_configured_repository_root_descendant_and_parent_are_rejected(self):
        for root in (self.project, self.project / "content", self.root):
            self.configure(root=root, raw=True)
            for alias in ("@configured", "@raw-root"):
                with self.subTest(alias=alias, root=root):
                    code, data = self.resolve(alias)
                    self.assertEqual(code, 2)
                    self.assertIn("outside the code repository", data["message"])

    def test_symlinked_repository_root_is_rejected(self):
        link = self.root / "vault-link"
        link.symlink_to(self.project, target_is_directory=True)
        self.configure(root=link)
        self.assertEqual(self.resolve("@configured")[0], 2)

    def test_symlinked_default_does_not_count_as_configuration(self):
        (self.project / "wiki").symlink_to(self.root / "vault", target_is_directory=True)
        code, data = self.resolve("@configured")
        self.assertEqual(code, 2)
        self.assertIn("not configured", data["message"])

    def test_derived_source_alias_cannot_escape_through_symlink(self):
        vault = self.root / "vault"
        (vault / "wiki").mkdir(parents=True)
        (vault / "wiki/sources").symlink_to(self.project, target_is_directory=True)
        self.configure(root=vault)
        self.assertEqual(self.resolve("@configured-sources-papers")[0], 2)

    def test_every_content_alias_validates_its_own_root(self):
        wiki_aliases = ("@wiki-root", "@wiki", "@configured", "@configured-wiki",
                        "@configured-sources", "@wiki-sources",
                        "@configured-sources-papers", "@wiki-sources-papers")
        raw_aliases = ("@raw-root", "@raw", "@configured-raw")
        for alias in (*wiki_aliases, *raw_aliases):
            with self.subTest(alias=alias):
                self.assertEqual(self.resolve(alias)[0], 2)
        self.configure(raw=True)
        self.assertEqual(self.resolve(*wiki_aliases, *raw_aliases)[0], 0)

    def test_project_cache_and_explicit_paths_remain_available(self):
        explicit = self.project / "docs/reference.md"
        code, data = self.resolve("@project-root", "@mineru-cache", str(explicit))
        self.assertEqual(code, 0)
        self.assertEqual(data["paths"]["@project-root"], str(self.project))
        self.assertEqual(data["paths"][str(explicit)], str(explicit))

    def test_bad_aliases_and_traversal_fail(self):
        self.configure()
        for alias in ("@unknown", "@configured/../code", "@configured//tmp"):
            with self.subTest(alias=alias):
                self.assertEqual(self.resolve(alias)[0], 2)

    def test_legacy_low_level_paths_remain_available_for_migrations(self):
        with patch.dict(os.environ, self.env, clear=True):
            paths = load_paths(config_path=self.config, project_root=self.project)
        self.assertEqual(resolve_runtime_path("@configured", paths, role="fixture"), self.project / "wiki")
        with self.assertRaisesRegex(ValueError, "not configured"):
            resolve_runtime_path("@configured", paths, role="content", require_external=True)


if __name__ == "__main__":
    unittest.main()

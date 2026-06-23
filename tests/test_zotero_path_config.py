import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import find_zotero_pdf
import _paths


class ZoteroPathConfigTests(unittest.TestCase):
    def test_profiled_paths_config_uses_selected_profile_zotero_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            win_root = root / "win-zotero"
            linux_root = root / "linux-zotero"
            disabled_root = root / "disabled-zotero"
            config_path = root / "paths.json"
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "windows",
                        "profiles": {
                            "windows": {
                                "wiki_root": "E:/wiki",
                                "raw_root": "E:/raw",
                                "zotero_roots": [
                                    {"label": "win", "path": str(win_root), "enabled": True},
                                    {"label": "disabled", "path": str(disabled_root), "enabled": False},
                                ],
                            },
                            "linux": {
                                "wiki_root": "~/wiki",
                                "raw_root": "~/raw",
                                "zotero_roots": [str(linux_root)],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            roots, notes = find_zotero_pdf._candidate_roots_from_config(config_path)

            self.assertEqual(roots, [win_root.resolve()])
            self.assertTrue(any("profile windows" in note for note in notes))

    def test_path_profile_env_override_selects_another_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "paths.json"
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "windows",
                        "profiles": {
                            "windows": {"zotero_roots": [str(root / "win")]},
                            "linux": {"zotero_roots": [str(root / "linux")]},
                        },
                    }
                ),
                encoding="utf-8",
            )
            old = os.environ.get("LLM_WIKI_PATH_PROFILE")
            os.environ["LLM_WIKI_PATH_PROFILE"] = "linux"
            try:
                roots, _notes = find_zotero_pdf._candidate_roots_from_config(config_path)
            finally:
                if old is None:
                    os.environ.pop("LLM_WIKI_PATH_PROFILE", None)
                else:
                    os.environ["LLM_WIKI_PATH_PROFILE"] = old

            self.assertEqual(roots, [(root / "linux").resolve()])

    def test_legacy_roots_config_is_still_accepted_when_explicitly_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "zotero-roots.json"
            config_path.write_text(
                json.dumps({"roots": [str(root / "legacy")]}),
                encoding="utf-8",
            )

            roots, notes = find_zotero_pdf._candidate_roots_from_config(config_path)

            self.assertEqual(roots, [(root / "legacy").resolve()])
            self.assertTrue(any("legacy roots" in note for note in notes))

class RuntimePathsConfigTests(unittest.TestCase):
    def test_write_paths_config_preserves_profile_zotero_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "paths.json"
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "auto",
                        "profiles": {
                            "windows": {
                                "wiki_root": "old-wiki",
                                "raw_root": "old-raw",
                                "zotero_roots": [
                                    {"label": "custom", "path": "E:/Literatures/Zotero/data", "enabled": True}
                                ],
                            },
                            "linux": {
                                "wiki_root": "~/wiki",
                                "raw_root": "~/raw",
                                "zotero_roots": ["~/Zotero"],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            _paths.write_paths_config(config_path, root / "new-wiki", root / "new-raw")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            profile = payload["profiles"][_paths.current_platform_profile()]

            self.assertEqual(profile["wiki_root"], str((root / "new-wiki").resolve()))
            self.assertEqual(profile["raw_root"], str((root / "new-raw").resolve()))
            self.assertEqual(
                profile["zotero_roots"],
                [{"label": "custom", "path": "E:/Literatures/Zotero/data", "enabled": True}],
            )
            self.assertIn("linux", payload["profiles"])

    def test_write_paths_config_keeps_current_profile_custom_zotero_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "paths.json"
            current_profile = _paths.current_platform_profile()
            config_path.write_text(
                json.dumps(
                    {
                        "active_profile": "auto",
                        "profiles": {
                            current_profile: {
                                "wiki_root": "~/wiki",
                                "raw_root": "~/raw",
                                "zotero_roots": [
                                    {"label": "current-custom", "path": str(root / "current"), "enabled": True}
                                ],
                            },
                            "windows": {
                                "wiki_root": "old-wiki",
                                "raw_root": "old-raw",
                                "zotero_roots": [
                                    {"label": "other-custom", "path": "E:/Literatures/Zotero/data", "enabled": True}
                                ],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            _paths.write_paths_config(config_path, root / "new-wiki", root / "new-raw")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            profile = payload["profiles"][current_profile]

            self.assertEqual(
                profile["zotero_roots"],
                [{"label": "current-custom", "path": str(root / "current"), "enabled": True}],
            )


if __name__ == "__main__":
    unittest.main()

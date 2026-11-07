"""Machine-local TOML paths: derivation, containment, lazy creation, Zotero."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import _paths
import find_zotero_pdf
from separate_wiki_repository import execute


class TomlPathsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / 'code'
        self.project.mkdir()
        self.vault = self.base / 'vault'
        self.config = self.project / 'paths.toml'
        self.environment = patch.dict(os.environ, {
            k: v for k, v in os.environ.items() if not k.startswith('LLM_WIKI_')
        }, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def configure(self, flags='', zotero=''):
        self.config.write_text(f'[wiki]\nroot_dir = {json.dumps(str(self.vault))}\n'
                               f'{flags}\n[zotero]\n{zotero}\n', encoding='utf-8')

    def load(self, **kwargs):
        return _paths.load_paths(config_path=self.config, project_root=self.project, **kwargs)

    def resolve(self, alias, paths=None):
        return _paths.resolve_runtime_path(alias, paths or self.load(),
                                           role='test', require_external=True)

    def test_derives_roots_and_custom_directories_without_os_detection_or_writes(self):
        self.configure('experiment = true\npaper_draft = true\nraw = true\noutput = true\n'
                       'beamer = true\nreading_notes = true')
        with patch('platform.system', side_effect=AssertionError('OS detected')):
            with patch.dict(os.environ, {'LLM_WIKI_PATH_PROFILE': 'windows'}):
                paths = self.load()
        for alias, name in {'@configured': 'wiki', '@experiment-root': 'experiment',
                            '@paper-root': 'paper_draft', '@raw-root': 'raw',
                            '@output-root': 'output', '@directory/beamer': 'beamer',
                            '@directory/reading_notes': 'reading_notes'}.items():
            self.assertEqual(self.resolve(alias, paths), self.vault / name)
        self.assertFalse(self.vault.exists())
        self.assertEqual(self.resolve('@directory/beamer/talk.tex'), self.vault / 'beamer/talk.tex')

    def test_disabled_and_omitted_directories_fail_without_affecting_wiki(self):
        self.configure('experiment = false\nbeamer = false')
        self.assertEqual(self.resolve('@configured'), self.vault / 'wiki')
        for alias in ('@experiment-root', '@paper-root', '@raw-root', '@output-root',
                      '@directory/beamer', '@directory/missing'):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                self.resolve(alias)

    def test_invalid_config_is_rejected(self):
        for flags in ('experiment = "true"', 'beamer = 1', 'wiki = true',
                      '"../escape" = true', '"/tmp" = true', '"a/b" = true'):
            self.configure(flags)
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                self.load()
        for data in ('[wiki]\nroot_dir = "relative"', '[wiki]\nexperiment = true',
                     '[wiki]\nroot_dir = 12', '[wrong]\na = true',
                     '[zotero]\ndata_dir = false', '[zotero]\nunknown = "foo"'):
            self.config.write_text(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load()

    def test_initialization_preflights_every_directory_and_preserves_contents(self):
        self.configure('experiment = true\npaper_draft = true\nbeamer = false')
        _paths.initialize_directories(self.load())
        marker = self.vault / 'experiment/existing.txt'
        marker.write_text('preserve')
        _paths.initialize_directories(self.load())
        self.assertEqual(marker.read_text(), 'preserve')
        self.assertTrue((self.vault / 'paper_draft').is_dir())
        self.assertFalse((self.vault / 'beamer').exists())
        self.configure('new_dir = true\nfile_target = true')
        (self.vault / 'file_target').write_text('file')
        with self.assertRaisesRegex(ValueError, 'target is a file'):
            _paths.initialize_directories(self.load())
        self.assertFalse((self.vault / 'new_dir').exists())

    def test_escape_overlap_and_repository_roots_are_rejected(self):
        self.configure('beamer = true')
        self.vault.mkdir()
        (self.vault / 'beamer').symlink_to(self.base / 'outside', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.resolve('@directory/beamer')
        with self.assertRaises(ValueError):
            _paths.initialize_directories(self.load())
        self.assertFalse((self.vault / 'wiki').exists())
        (self.vault / 'beamer').unlink()
        (self.vault / 'beamer').symlink_to(self.vault / 'wiki', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            self.resolve('@directory/beamer')
        for root in (self.project, self.base):
            self.config.write_text(f'[wiki]\nroot_dir = {json.dumps(str(root))}')
            with self.assertRaises(ValueError):
                self.resolve('@configured')

    def test_traversal_rejected_for_custom_directory(self):
        self.configure('beamer = true')
        for alias in ('@directory/beamer/../wiki', '@directory/beamer//tmp', '@directory'):
            with self.assertRaises(ValueError):
                self.resolve(alias)

    def test_explicit_and_environment_overrides_keep_precedence(self):
        self.configure('experiment = true')
        with patch.dict(os.environ, {'LLM_WIKI_EXPERIMENT_ROOT': str(self.base / 'env')}):
            self.assertEqual(self.load().experiment_root, self.base / 'env')
            self.assertEqual(self.load(experiment_root=self.base / 'arg').experiment_root,
                             self.base / 'arg')
            self.assertEqual(self.resolve('@directory/experiment'), self.vault / 'experiment')

    def test_cli_defaults_work_without_optional_roots_and_create_dirs_is_explicit(self):
        self.configure('beamer = true')
        cmd = [sys.executable, str(TOOLS / 'resolve_path_alias.py'),
               '--paths-config', str(self.config), '--json']
        result = subprocess.run(cmd, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse(self.vault.exists())
        result = subprocess.run([*cmd, '--create-dirs'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertTrue((self.vault / 'beamer').is_dir())

    def test_zotero_explicit_data_takes_precedence_without_os_detection(self):
        data, profile = self.base / 'zotero', self.base / 'profile'
        data.mkdir()
        (data / 'zotero.sqlite').touch()
        self.config.write_text(f'[zotero]\ndata_dir = {json.dumps(str(data))}\n'
                               f'profile_dir = {json.dumps(str(profile))}\n')
        with patch('platform.system', side_effect=AssertionError('OS detected')):
            roots, _ = find_zotero_pdf._candidate_roots_from_config(self.config)
            chosen, _ = find_zotero_pdf._discover_zotero_root(self.config)
        self.assertEqual(roots, [data, profile])
        self.assertEqual(chosen, data)
        self.assertFalse(self.load().wiki_root_configured)

    def test_zotero_profile_fallback_and_empty_settings(self):
        data, profile = self.base / 'zotero', self.base / 'profile'
        data.mkdir()
        profile.mkdir()
        (data / 'zotero.sqlite').touch()
        (profile / 'prefs.js').write_text(f'user_pref("extensions.zotero.dataDir", {json.dumps(str(data))});')
        self.config.write_text(f'[zotero]\ndata_dir = ""\nprofile_dir = {json.dumps(str(profile))}')
        self.assertEqual(find_zotero_pdf._discover_zotero_root(self.config)[0], data)
        self.config.write_text('[zotero]\nprofile_dir = ""\ndata_dir = ""')
        self.assertEqual(find_zotero_pdf._candidate_roots_from_config(self.config)[0], [])

    def test_config_writer_preserves_booleans_and_zotero(self):
        self.configure('beamer = false\npaper_draft = true', 'data_dir = "~/Zotero"')
        target = self.base / 'new-vault'
        _paths.write_paths_config(self.config, target / 'wiki', target / 'raw')
        cfg = _paths.read_toml_config(self.config)
        self.assertFalse(cfg['wiki']['beamer'])
        self.assertTrue(cfg['wiki']['paper_draft'])
        self.assertEqual(cfg['zotero']['data_dir'], '~/Zotero')
        self.assertEqual(self.load().root_dir, target)

    def test_invalid_migration_layout_fails_before_copying(self):
        (self.project / 'wiki').mkdir()
        (self.project / 'wiki/test.md').write_text('source')
        target = self.base / 'wrong-name'
        with self.assertRaisesRegex(ValueError, 'requires sibling'):
            execute(self.project, target, self.base / 'raw', self.config, 'copy', False)
        self.assertFalse(target.exists())
        self.assertFalse(self.config.exists())


if __name__ == '__main__':
    unittest.main()

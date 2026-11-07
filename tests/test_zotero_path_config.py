"""Zotero and path writers share the single machine-local TOML contract."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import find_zotero_pdf
import _paths
from separate_wiki_repository import execute


class ZoteroPathConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.config = self.root / "paths.toml"

    def test_identical_data_and_profile_paths_are_deduplicated(self):
        value = json.dumps(str(self.root / 'zotero'))
        self.config.write_text(f'[zotero]\ndata_dir = {value}\nprofile_dir = {value}')
        roots, _ = find_zotero_pdf._candidate_roots_from_config(self.config)
        self.assertEqual(roots, [self.root / 'zotero'])

    def test_missing_config_has_actionable_diagnostic(self):
        roots, notes = find_zotero_pdf._candidate_roots_from_config(self.config)
        self.assertEqual(roots, [])
        self.assertIn('not found', notes[0])

    def test_invalid_toml_reports_error_without_candidates(self):
        for content in ('[zotero', '[zotero]\ndata_dir = 12',
                        '[zotero]\nroots = ["~/Zotero"]'):
            self.config.write_text(content)
            with self.subTest(content=content):
                roots, notes = find_zotero_pdf._candidate_roots_from_config(self.config)
                self.assertEqual(roots, [])
                self.assertIn('failed to read path config', notes[0])

    def test_json_paths_are_rejected_by_readers_and_writer_without_mutation(self):
        legacy = self.root / 'paths.json'
        original = json.dumps({'profiles': {'macos': {'zotero_roots': ['~/Zotero']}}})
        legacy.write_text(original)
        with self.assertRaisesRegex(ValueError, 'must be a .toml file'):
            _paths.load_paths(config_path=legacy)
        roots, notes = find_zotero_pdf._candidate_roots_from_config(legacy)
        self.assertEqual(roots, [])
        self.assertIn('must be a .toml file', notes[0])
        with self.assertRaisesRegex(ValueError, 'must be a .toml file'):
            _paths.write_paths_config(legacy, self.root / 'wiki', self.root / 'raw')
        self.assertEqual(legacy.read_text(), original)
        # An obsolete destination must fail before the migration copies files.
        project = self.root / 'code'
        (project / 'wiki').mkdir(parents=True)
        (project / 'wiki/existing.md').write_text('preserve')
        target = self.root / 'vault'
        with self.assertRaisesRegex(ValueError, 'must be a .toml file'):
            execute(project, target / 'wiki', target / 'raw', legacy, 'copy', False)
        self.assertFalse(target.exists())

    def test_profile_tables_in_toml_are_rejected(self):
        self.config.write_text('[profiles.macos]\nwiki_root = "~/wiki"')
        with self.assertRaisesRegex(ValueError, 'unknown path configuration tables'):
            _paths.load_paths(config_path=self.config)
        self.assertEqual(find_zotero_pdf._candidate_roots_from_config(self.config)[0], [])


if __name__ == '__main__':
    unittest.main()

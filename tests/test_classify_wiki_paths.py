"""Classifier reads the same TOML vault as other wiki commands."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import classify_wiki_papers as classifier


class ClassifierPathTests(unittest.TestCase):
    def test_toml_root_is_used_before_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            config, output = root / 'paths.toml', root / 'report.json'
            vault = root / 'vault'
            config.write_text(f'[wiki]\nroot_dir = {json.dumps(str(vault))}\n[zotero]\n')
            argv = ['classifier', '--paths-config', str(config), '--out', str(output)]
            environment = {k: v for k, v in os.environ.items() if not k.startswith('LLM_WIKI_')}
            with patch.dict(os.environ, environment, clear=True), patch.object(sys, 'argv', argv), \
                    patch.object(classifier, 'parse_pages', return_value=[]) as pages, \
                    patch.object(classifier, 'fetch_items', return_value=[]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(classifier.main(), 0)
            pages.assert_called_once_with(vault / 'wiki')
            self.assertEqual(json.loads(output.read_text())['wikiPaperCount'], 0)

    def test_missing_config_stops_before_reading_pages_or_calling_zotero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            output = root / 'report.json'
            argv = ['classifier', '--paths-config', str(root / 'missing.toml'), '--out', str(output)]
            environment = {k: v for k, v in os.environ.items() if not k.startswith('LLM_WIKI_')}
            with patch.dict(os.environ, environment, clear=True), patch.object(sys, 'argv', argv), \
                    patch.object(classifier, 'parse_pages') as pages, \
                    patch.object(classifier, 'fetch_items') as fetch, \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                classifier.main()
            self.assertEqual(error.exception.code, 2)
            pages.assert_not_called()
            fetch.assert_not_called()
            self.assertFalse(output.exists())

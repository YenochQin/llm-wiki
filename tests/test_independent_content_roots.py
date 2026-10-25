"""Integration contracts for independently configured research content."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import _content
from _paths import load_paths, resolve_runtime_path
import research_wiki as wiki
import lint
import reset_wiki


class IndependentContentRootsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.config = self.root / 'paths.json'
        self.wiki = self.root / 'knowledge'
        self.experiments = self.root / 'lab-records'
        self.outputs = self.root / 'reading'
        self.config.write_text(json.dumps(dict(wiki_root=str(self.wiki),
            experiment_root=str(self.experiments), output_root=str(self.outputs))))
        self.paths = load_paths(config_path=self.config)
        token = _content.configure_content_paths(self.paths)
        self.addCleanup(_content._runtime.reset, token)
        self.capture(wiki.init_wiki, str(self.wiki))

    def capture(self, func, *args, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            func(*args, **kwargs)
        return json.loads(out.getvalue())

    def seed(self):
        (self.wiki / 'claims' / 'claim.md').write_text('''---
title: Example claim
slug: claim
status: proposed
confidence: 0.5
tags: []
evidence:
  - source: measurement
    type: tested_by
    strength: moderate
---
## Evidence summary
[[measurement]]
''')
        (self.experiments / 'measurement.md').write_text('''---
title: Example measurement
slug: measurement
status: planned
target_claim: "[[claim]]"
hypothesis: Example
date_planned: 2026-10-25
key_result: Recorded result
tags: []
---
## Objective
[[claim]]
''')
        (self.outputs / 'report.md').write_text('---\ntitle: Reading report\n---\n[[measurement]]\n')

    def test_init_uses_custom_roots_and_does_not_recreate_old_directories(self):
        self.assertTrue(self.experiments.is_dir())
        self.assertTrue(self.outputs.is_dir())
        self.assertFalse((self.wiki / 'experiments').exists())
        self.assertFalse((self.wiki / 'outputs').exists())

    def test_evidence_query_index_context_stats_and_graph_survive_move(self):
        self.seed()
        data = self.capture(wiki.query_evidence_for, str(self.wiki), 'claim')
        self.assertEqual(data['experiments'][0]['slug'], 'measurement')
        self.assertEqual(data['evidence'][0]['source'], 'measurement')
        found = self.capture(wiki.find_entities, str(self.wiki), 'experiments', [])
        self.assertEqual(found[0]['slug'], 'measurement')
        self.capture(wiki.add_edge, str(self.wiki), 'claims/claim', 'experiments/measurement',
                     'tested_by', 'Measurement tests claim')
        self.capture(wiki.add_edge, str(self.wiki), 'outputs/report', 'claims/claim',
                     'derived_from', 'Report cites claim')
        before = (self.wiki / 'graph/edges.jsonl').read_bytes()
        self.capture(wiki.prune_dangling_graph, str(self.wiki))
        self.assertEqual((self.wiki / 'graph/edges.jsonl').read_bytes(), before)
        self.assertEqual(wiki._validate_node_refs(self.wiki, 'experiments/measurement'), [])
        self.capture(wiki.rebuild_index, str(self.wiki))
        index = (self.wiki / 'index.md').read_text()
        self.assertIn('../lab-records/measurement.md', index)
        self.assertIn('../reading/report.md', index)
        self.assertEqual(yaml.safe_load(index)['outputs'][0]['title'], 'Reading report')
        self.assertEqual(self.capture(wiki.get_stats, str(self.wiki), as_json=True)['experiments'], 1)
        with contextlib.redirect_stdout(io.StringIO()):
            wiki.compile_context(str(self.wiki), purpose='experiment')
        self.assertIn('Example measurement', (self.wiki / 'graph/context_brief.md').read_text())
        issues = lint.lint(self.wiki)
        self.assertFalse([i for i in issues if i.category in
            {'broken-link', 'broken-claim-ref', 'xref-asymmetry', 'dangling-edge'}], issues)

    def test_index_quotes_tags_and_titles_and_preserves_metadata_types(self):
        self.seed()
        page = self.experiments / 'measurement.md'
        page.write_text(page.read_text().replace('tags: []', 'tags: ["V^{N-M}", "a: b"]'))
        self.capture(wiki.rebuild_index, str(self.wiki))
        data = yaml.safe_load((self.wiki / 'index.md').read_text())
        self.assertEqual(data['experiments'][0]['tags'], ['V^{N-M}', 'a: b'])
        self.assertEqual(data['experiments'][0]['target_claim'], '[[claim]]')

    def test_missing_field_fix_and_lifecycle_use_custom_root(self):
        self.seed()
        page = self.experiments / 'measurement.md'
        page.write_text(page.read_text().replace('tags: []\n', ''))
        issues = lint.lint(self.wiki)
        missing = [i for i in issues if i.file == 'experiments/measurement.md' and i.category == 'missing-field']
        self.assertTrue(missing)
        lint.fix_issues(self.wiki, missing)
        self.assertIn('tags:', page.read_text())
        self.capture(wiki.transition, str(page), 'running')
        self.assertIn('running', page.read_text())

    def test_reset_preview_and_execution_target_configured_roots(self):
        self.seed()
        plan = reset_wiki.plan(self.paths.project_root, self.wiki, self.root / 'raw', ['wiki'])
        self.assertIn(str(self.experiments / 'measurement.md'), plan['delete_files'])
        self.assertIn(str(self.outputs / 'report.md'), plan['delete_files'])
        reset_wiki.execute(self.paths.project_root, self.wiki, self.root / 'raw', ['wiki'])
        self.assertFalse((self.experiments / 'measurement.md').exists())
        self.assertFalse((self.outputs / 'report.md').exists())
        self.assertFalse((self.wiki / 'experiments').exists())
        self.assertFalse((self.wiki / 'outputs').exists())

    def test_aliases_validate_independence_missing_config_and_escape(self):
        for alias, key in [('@experiment-root', 'experiment_root'), ('@output-root', 'output_root')]:
            self.assertEqual(resolve_runtime_path(alias + '/a.md', self.paths, role='test'),
                             getattr(self.paths, key) / 'a.md')
            for value in (None, self.paths.project_root / 'bad', self.wiki / 'bad', self.wiki.parent):
                from dataclasses import replace
                invalid = replace(self.paths, **{key: value})
                with self.assertRaises(ValueError):
                    resolve_runtime_path(alias, invalid, role='test')
            with self.assertRaises(ValueError):
                resolve_runtime_path(alias + '/../escape.md', self.paths, role='test')
        for alias in ('@configured/experiments/x.md', '@configured/outputs/x.md'):
            with self.assertRaisesRegex(ValueError, 'retired'):
                resolve_runtime_path(alias, self.paths, role='test')
        (self.outputs / 'escape').symlink_to(self.wiki, target_is_directory=True)
        with self.assertRaises(ValueError):
            resolve_runtime_path('@output-root/escape/a.md', self.paths, role='test')

    def test_output_identity_does_not_require_experiment_configuration(self):
        from dataclasses import replace
        token = _content.configure_content_paths(replace(self.paths, experiment_root=None))
        try:
            self.assertEqual(_content.content_relative(self.outputs / 'report.md', self.wiki),
                             'outputs/report.md')
        finally:
            _content._runtime.reset(token)

    def test_init_missing_independent_root_fails_before_creating_directories(self):
        from dataclasses import replace
        other = self.root / 'new-wiki'
        token = _content.configure_content_paths(replace(self.paths, wiki_root=other, output_root=None))
        try:
            with self.assertRaisesRegex(ValueError, 'output_root is not configured'):
                wiki.init_wiki(str(other))
            self.assertFalse(other.exists())
        finally:
            _content._runtime.reset(token)

    def test_reset_cli_explicit_fixture_does_not_borrow_vault_roots(self):
        self.seed()
        fixture = self.root / 'fixture'
        (fixture / 'experiments').mkdir(parents=True)
        (fixture / 'experiments' / 'local.md').write_text('local')
        process = subprocess.run([sys.executable, str(TOOLS / 'reset_wiki.py'), '--paths-config',
            str(self.config), '--wiki-root', str(fixture), '--scope', 'wiki'],
            capture_output=True, text=True, check=True)
        plan = json.loads(process.stdout)
        self.assertIn(str(fixture / 'experiments/local.md'), plan['delete_files'])
        self.assertNotIn(str(self.experiments / 'measurement.md'), plan['delete_files'])
        self.assertNotIn(str(self.outputs / 'report.md'), plan['delete_files'])

    def test_cli_custom_paths_config_scans_external_experiments(self):
        self.seed()
        page = self.experiments / 'measurement.md'
        page.write_text(page.read_text().replace('tags: []\n', ''))
        process = subprocess.run([sys.executable, str(TOOLS / 'lint.py'), '--paths-config',
            str(self.config), '--only', str(page), '--json'], capture_output=True, text=True)
        issues = json.loads(process.stdout)
        self.assertTrue(any(i['file'] == 'experiments/measurement.md' for i in issues), process.stderr)


if __name__ == '__main__':
    unittest.main()

import sys
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import batch_reocr as batch


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class BatchReocrTests(unittest.TestCase):
    def test_portable_and_windows_paths_use_exact_zotero_attachment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "zotero/storage/ABCDEFGH/a paper.pdf"
            write(pdf, "PDF fixture")
            for source in ("${Zotero data directory}/storage/ABCDEFGH/a paper.pdf",
                           r"E:\Zotero\storage\ABCDEFGH\a paper.pdf"):
                self.assertEqual(batch.locate_pdf(source, [root / "zotero"], root / "raw", root), [pdf])
            self.assertEqual(batch.locate_pdf("/old/a paper.pdf", [root / "zotero"], root / "raw", root), [])

    def test_rank_existing_importance_deduplicate_pdf_and_preserve_broken_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wiki = root / "wiki"
            pdf = root / "zotero/storage/ABCDEFGH/paper.pdf"
            write(pdf, "read-only PDF fixture")
            source = wiki / "sources/papers/different-source-name.md"
            write(source, '---\ntitle: Shared\nsource: "${Zotero data directory}/storage/ABCDEFGH/paper.pdf"\n---\nBody')
            for slug, importance in [("z-high", 5), ("a-low", 2)]:
                write(wiki / f"papers/{slug}.md", f'---\ntitle: Shared\nimportance: {importance}\n---\n[prepared markdown](../sources/papers/different-source-name.md)')
            write(wiki / 'papers/missing.md', '---\ntitle: Missing\nimportance: 3\n---\n[prepared markdown](../sources/papers/not-there.md)')
            before = batch.digest(source)
            fake = unittest.mock.MagicMock()
            fake.PdfDocument.return_value.__len__.return_value = 7
            with patch.dict(sys.modules, {'pypdfium2': fake}):
                rows, jobs = batch.build_plan(wiki, root/'raw', root, [root/'zotero'])
            self.assertEqual([r['slug'] for r in rows], ['z-high', 'missing', 'a-low'])
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]['importance'], 5)
            self.assertEqual(len(jobs[0]['papers']), 2)
            self.assertEqual(rows[1]['status'], 'unresolved')
            self.assertTrue(any('broken source link' in n for n in rows[1]['notes']))
            self.assertEqual(batch.digest(source), before)

    def test_source_scalar_provenance_survives_broken_section_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.md'
            write(path, '---\nsource: "${Zotero data directory}/storage/ABCDEFGH/paper.pdf"\nsections: [\n---\nBody')
            meta, warning = batch.metadata(path)
            self.assertIn('/ABCDEFGH/', meta['source'])
            self.assertTrue(warning)

    def test_native_run_is_local_and_resume_requires_unchanged_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / 'paper.pdf'
            write(pdf, 'PDF fixture')
            executable = root / 'fake-mineru'
            script = f'''#!{sys.executable}
import sys,os,json,zipfile
assert '--remote' not in sys.argv
assert os.environ['MINERU_MODEL_SOURCE']=='local'
assert sys.argv[sys.argv.index('--tier')+1]=='basic'
p=sys.argv[sys.argv.index('--output')+1]
with zipfile.ZipFile(p,'w') as z:
 z.writestr('markdown.md','# Abstract\\nReadable source.')
 z.writestr('middle_json.json',json.dumps({{'pages':[{{}}]}}))
'''
            write(executable, script)
            executable.chmod(0o700)
            job = {'id':'one','pdf':str(pdf),'pdf_sha256':batch.digest(pdf),'pages':1,'papers':[],'sources':[]}
            engine = {'mineru_version':'4.fixture','tier':'basic','ocr_mode':'auto'}
            output = root / 'output'
            result = batch.execute_job(job, output, engine, executable, root/'mineru-home', 10)
            self.assertEqual(result['pages'], 1)
            self.assertFalse(result['pdf_fidelity_verified'])
            self.assertEqual(batch.digest(pdf), job['pdf_sha256'])
            self.assertIsNotNone(batch.completed_result(job, output, engine))
            self.assertIsNone(batch.completed_result(job, output, dict(engine, mineru_version='other')))
            write(Path(result['markdown']), 'modified')
            self.assertIsNone(batch.completed_result(job, output, engine))

    def test_archive_traversal_and_missing_markdown_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('../escape.md','bad')
            with self.assertRaises(ValueError):
                batch.extract_result(archive, root/'output')
            self.assertFalse((root/'escape.md').exists())
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('middle_json.json','{"pages":[]}')
            with self.assertRaises(ValueError):
                batch.extract_result(archive, root/'output')

    def test_lock_prevents_two_workers(self):
        with tempfile.TemporaryDirectory() as tmp, batch.worker_lock(Path(tmp)), self.assertRaises(RuntimeError), batch.worker_lock(Path(tmp)):
            pass

    def test_worker_activity_uses_lock_and_releases_after_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue=Path(tmp)
            self.assertFalse(batch.worker_active(queue))
            with batch.worker_lock(queue):
                self.assertTrue(batch.worker_active(queue))
            self.assertFalse(batch.worker_active(queue))

    def test_failure_does_not_stop_later_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); queue=root/'queue'; queue.mkdir()
            wiki=root/'wiki'; output=wiki/'sources/reocr/run'
            jobs=[{'id':str(i),'rank':i,'importance':5,'pages':1,'label':f'p{i}'} for i in [1,2]]
            batch.atomic_json(queue/'queue.json',{'wiki_root':str(wiki),'output_root':str(output),'jobs':jobs})
            bin_dir=root/'bin'; write(bin_dir/'mineru-kit','fixture')
            args=Namespace(queue_dir=queue,mineru_home=root/'home',max_items=0,retry_failed=False,timeout_seconds=0)
            with patch.object(batch.sys,'executable',str(bin_dir/'python')), patch.object(batch.importlib.metadata,'version',return_value='4.0.12'), patch.object(batch,'load_paths'), patch.object(batch,'resolve_runtime_path',return_value=wiki), patch.object(batch,'completed_result',return_value=None), patch.object(batch,'execute_job',side_effect=[RuntimeError('broken PDF'),{'quality_issues':0}]):
                state=batch.run_queue(args)
            self.assertEqual(state['jobs']['1']['status'],'failed')
            self.assertEqual(state['jobs']['2']['status'],'completed')
            self.assertEqual(state['status'],'finished_with_failures')


if __name__ == '__main__':
    unittest.main()

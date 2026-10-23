import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import batch_reocr as batch


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class BatchReocrTests(unittest.TestCase):
    def test_live_output_preserves_progress_and_unicode_in_console_and_log(self):
        expected = 'Layout 10%\r公式 100%\n'
        proc = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdout.buffer.write(' + repr(expected.encode('utf-8')) + ')'],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        console, log = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(console):
                self.assertEqual(batch.wait_with_output(proc, log, 5), 0)
            self.assertEqual(console.getvalue(), expected)
            self.assertEqual(log.getvalue(), expected)
        finally:
            proc.stdout.close()

    def test_live_output_timeout_is_enforced_for_a_silent_child(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'], stdout=subprocess.PIPE)
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                batch.wait_with_output(proc, io.StringIO(), 0.1)
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            proc.stdout.close()

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
            wiki=root/'wiki'; output=root/'staging/run'
            jobs=[{'id':str(i),'rank':i,'importance':5,'pages':1,'label':f'p{i}'} for i in [1,2]]
            batch.atomic_json(queue/'queue.json',{'wiki_root':str(wiki),'output_root':str(output),'jobs':jobs})
            bin_dir=root/'bin'; write(bin_dir/'mineru-kit','fixture')
            args=Namespace(queue_dir=queue,mineru_home=root/'home',max_items=0,retry_failed=False,timeout_seconds=0)
            with patch.object(batch.sys,'executable',str(bin_dir/'python')), patch.object(batch.importlib.metadata,'version',return_value='4.0.12'), patch.object(batch,'load_paths'), patch.object(batch,'resolve_runtime_path',return_value=wiki), patch.object(batch,'completed_result',return_value=None), patch.object(batch,'execute_job',side_effect=[RuntimeError('broken PDF'),{'quality_issues':0}]):
                state=batch.run_queue(args)
            self.assertEqual(state['jobs']['1']['status'],'failed')
            self.assertEqual(state['jobs']['2']['status'],'completed')
            self.assertEqual(state['status'],'finished_with_failures')

    def test_staging_rejects_vault_raw_and_symlink_destinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); vault=root/'vault'; (vault/'.obsidian').mkdir(parents=True)
            wiki=vault/'wiki'; raw=root/'raw'; raw.mkdir()
            link=root/'link'; link.symlink_to(vault, target_is_directory=True)
            for output in (wiki/'sources/reocr', vault/'temp', raw/'cache', root, link/'cache'):
                with self.assertRaises(ValueError):
                    batch.validate_staging_root(output,wiki,raw)
            self.assertEqual(batch.validate_staging_root(root/'cache',wiki,raw),root/'cache')

    def test_plan_defaults_to_ignored_tool_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); wiki=root/'vault/wiki'; raw=root/'vault/raw'; queue=root/'temp/run'
            runtime=SimpleNamespace(project_root=root,config_path=root/'config.json')
            with patch.object(batch,'load_paths',return_value=runtime), \
                 patch.object(batch,'resolve_runtime_path',side_effect=[wiki,raw]), \
                 patch.object(batch,'build_plan',return_value=([],[])), \
                 patch.object(batch,'exact_zotero_lookup'), \
                 patch('find_zotero_pdf._candidate_roots_from_config',return_value=([],[])), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(batch.main(['plan','--queue-dir',str(queue)]),0)
            plan=json.loads((queue/'queue.json').read_text())
            self.assertEqual(plan['output_root'],str(root/'.checkpoints/reocr/run'))
            self.assertFalse((wiki/'sources/reocr').exists())

    def test_relocation_preserves_markdown_and_completed_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); wiki=root/'wiki'; old=wiki/'sources/reocr/old'; new=root/'cache/new'; queue=root/'queue'
            pdf=root/'paper.pdf'; write(pdf,'input'); md=old/'job/attempt/native/markdown.md'; write(md,'# Original OCR\nExact body')
            job={'id':'job','rank':1,'importance':4,'pages':1,'label':'paper','title':'Paper','papers':[], 'pdf':str(pdf),'pdf_sha256':batch.digest(pdf)}
            engine={'mineru_version':'4.fixture'}
            batch.atomic_json(old/'job/result.json',{'markdown':str(md),'markdown_sha256':batch.digest(md),'pdf_sha256':batch.digest(pdf),'engine':engine})
            batch.atomic_json(queue/'queue.json',{'created_utc':batch.now(),'wiki_root':str(wiki),'output_root':str(old),'jobs':[job],'papers':[]})
            batch.atomic_json(queue/'progress.json',{'status':'interrupted','jobs':{'job':{'status':'completed','result':str(old/'job/result.json')}}})
            with patch.object(batch,'load_paths'),patch.object(batch,'resolve_runtime_path',side_effect=[wiki,root/'raw',new]):
                result=batch.relocate_queue(queue,new)
            self.assertEqual(result['receipts_verified'],1)
            self.assertFalse(old.exists())
            self.assertEqual((new/'job/attempt/native/markdown.md').read_text(),'# Original OCR\nExact body')
            self.assertIsNotNone(batch.completed_result(job,new,engine))
            self.assertEqual(json.loads((queue/'queue.json').read_text())['output_root'],str(new))

    def test_worker_refuses_plan_relocated_before_lock_acquisition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); queue=root/'queue'; wiki=root/'wiki'
            plan={'wiki_root':str(wiki),'output_root':str(root/'old-cache'),'jobs':[]}
            batch.atomic_json(queue/'queue.json',plan)
            executable=root/'bin/python'; write(executable.parent/'mineru-kit','fixture')
            @contextlib.contextmanager
            def relocated(_):
                batch.atomic_json(queue/'queue.json',dict(plan,output_root=str(root/'new-cache')))
                yield
            args=Namespace(queue_dir=queue)
            with patch.object(batch,'worker_lock',relocated),patch.object(batch,'load_paths'), \
                 patch.object(batch,'resolve_runtime_path',return_value=wiki), \
                 patch.object(batch.sys,'executable',str(executable)), \
                 patch.object(batch.importlib.metadata,'version',return_value='4.0.12'), \
                 self.assertRaisesRegex(RuntimeError,'Queue changed'):
                batch.run_queue(args)
            self.assertFalse((queue/'progress.json').exists())


if __name__ == '__main__':
    unittest.main()

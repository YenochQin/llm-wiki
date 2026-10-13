# Batch local re-parsing of ingested PDFs

`tools/batch_reocr.py` inventories existing `papers/*.md`, follows actual
prepared-source links, resolves portable/migrated Zotero attachment paths, and
falls back only to a unique exact Zotero DOI/title match. Missing or ambiguous
sources remain visible in the priority report. Both full and light-ingested
paper pages participate; raw PDFs without a paper page do not.

The existing integer `importance` is the only priority score: descending 5 to
1, then paper filename. Missing/invalid values sort last and are not invented.
PDF SHA-256 deduplication combines all corresponding paper/source references
and uses their highest importance. The report shows both the per-paper order
and unique PDF execution order.

Run from the repository root with the project environment containing MinerU 4.
The worker currently requires POSIX `fcntl` locks (Linux/macOS). Plan/status
are separate from parsing. The tested inference mode is `basic/auto`, with
local models only; this is not forced full-page image OCR. The runner invokes
the MinerU 4 `mineru-kit` CLI, independent of the legacy 3.x ingestion wrapper.

```bash
uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@raw-root'
uv run python -X utf8 tools/batch_reocr.py plan \
  --queue-dir temp/reocr-2026-10-13 \
  --output-root '@configured/sources/reocr/2026-10-13-mineru4-basic'
uv run python -X utf8 tools/batch_reocr.py run \
  --queue-dir temp/reocr-2026-10-13 \
  --mineru-home .checkpoints/batch-reocr-2026-10-13/mineru-home
uv run python -X utf8 tools/batch_reocr.py status --queue-dir temp/reocr-2026-10-13
uv run python -X utf8 tools/batch_reocr.py stop --queue-dir temp/reocr-2026-10-13
```

Use the selected run directory instead of reusing the example date for a new
run. Planning refuses to overwrite an existing queue. The explicit repository
`temp/` report location is for operational queues; actual converted source
content stays under the external wiki's `sources/reocr/` staging root.

`run` resumes an existing queue. A stop request takes effect after the current
PDF. Ctrl-C/SIGTERM terminates the active child and checkpoints interruption.
OS locks prevent two workers from running the same queue. Each attempt has its
own output/log directory. A crash leaves incomplete attempts intact; resume
only trusts a completed receipt whose input hash, parser version/settings and
Markdown hash still match. Failed documents do not stop later jobs; retry them
only with `--retry-failed`. `--max-items N` bounds attempts for a smoke test;
omitting it processes the full queue. Per-document timeout defaults to none.

In a normal host terminal, add `--background` for a detached worker. In a
managed command sandbox, keep foreground `run` in a long-running execution
session: detached children may be terminated with their launcher. `status`
probes the OS lock as `worker_active`; it does not trust namespaced/stale PIDs.
The example model home was populated for this run. For another machine, prepare
the `basic` ONNX models in the selected MinerU home first; run preflight rejects
missing models before attempting documents.

Outputs:

- `priority.md`: stable inventory, priority order and unresolved provenance.
- `queue.json`: original PDF paths/hashes, expected page counts and references.
- `progress.json` / `progress.md`: per-document state and output/error locations.
- Staged `jobs` (named by PDF hash): native ZIP, extracted Markdown, structured
  JSON/images, source-quality findings and a completion receipt.

The runner checks page coverage and performs mechanical source-quality
screening. Completion means conversion succeeded, not that PDF fidelity was
verified. Original PDFs, canonical sources, paper/concept/claim pages and graph
state are never replaced. Promotion of staged results and subsequent wiki
reingest remain separately scoped work.

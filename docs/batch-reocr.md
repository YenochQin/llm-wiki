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
  --queue-dir temp/reocr-2026-10-13
uv run python -X utf8 tools/batch_reocr.py run \
  --queue-dir temp/reocr-2026-10-13 \
  --mineru-home .checkpoints/batch-reocr-2026-10-13/mineru-home --verbose
uv run python -X utf8 tools/batch_reocr.py status --queue-dir temp/reocr-2026-10-13
uv run python -X utf8 tools/batch_reocr.py stop --queue-dir temp/reocr-2026-10-13
```

Use the selected run directory instead of reusing the example date for a new
run. Planning refuses to overwrite an existing queue. The explicit repository
`temp/` report location is for operational queues. Parser output defaults to
`.checkpoints/reocr/<queue-directory-name>` in the tool repository, an ignored
disposable cache outside the Obsidian vault. An explicit `--output-root` may
select another cache location. Planning and running reject output inside the
wiki, its enclosing Obsidian vault, or raw inputs (including symlink aliases).

An existing queue that used vault-visible staging must be relocated before
resuming. The queue must be idle. This moves its cache, verifies Markdown
hashes, updates receipt/progress paths, and preserves completed-job status:

```bash
uv run python -X utf8 tools/batch_reocr.py relocate \
  --queue-dir temp/reocr-2026-10-13 \
  --output-root .checkpoints/reocr/reocr-2026-10-13
```

`relocation.json` in the queue records the old location and original queue
state. If interrupted after the directory move, rerunning the same relocation
can finish repairing paths. A pre-existing unrelated destination is refused.
Wiki-root comparisons and relocated artifact paths resolve filesystem aliases,
including macOS `/var` and `/private/var`. Receipts written through an alias
remain usable after relocation or recovery; a genuinely different wiki root
is still rejected. No `TMPDIR` override is required.

`run` resumes an existing queue. A stop request takes effect after the current
PDF. Ctrl-C/SIGTERM terminates the active child and checkpoints interruption.
OS locks prevent two workers from running the same queue. Each attempt has its
own output/log directory. A crash leaves incomplete attempts intact; resume
only trusts a completed receipt whose input hash, parser version/settings and
Markdown hash still match. Failed documents do not stop later jobs; retry them
only with `--retry-failed`. `--max-items N` bounds attempts for a smoke test;
omitting it processes the full queue. Per-document timeout defaults to none.

`--verbose` streams MinerU's layout, formula and OCR progress directly to the
terminal while preserving the same per-document `mineru.log`. Without it,
the terminal prints document-level progress and details stay in log files.

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

## Reviewed promotion and retention

Keep one stable canonical path per source, for example
`<wiki_root>/sources/papers/<source-slug>.md`. After source review, update that
file and its stable asset directory; do not accumulate dated OCR copies in
`sources`. Preserve good older evidence that the new OCR cannot replace as
explicitly attributed excerpts, rather than copying the entire old article
into the new file. Excluded or unverified historical quotations must not be
promoted into active source evidence.

Before replacing a canonical source, archive the old files and affected pages
outside the vault. Validate all referencing Evidence Packs/Source excerpts
against the proposed source, preserve their anchors, and run scoped grounding
and link checks. Deduplicate images by file content; remove only assets with
no remaining live references, after the archive is verified. Include Markdown
images, HTML `img src` (including images inside tables), and Obsidian embeds in
the image-reference checks. Keep raw PDFs
unchanged.

Keep backups compressed by batch outside the vault, and retain parser ZIPs
and receipts in the external cache while the queue is resumable. Cache and
backup cleanup is an explicit batch operation after review; deleting a live
queue's receipts/Markdown can cause those documents to be parsed again.


## MinerU 4.0.12 zero-area OCR crop compatibility

The batch runner invokes `tools/mineru_compat_cli.py` for MinerU 4.0.12.
Its version-scoped guard discards zero-area, unrecognized OCR boxes before
perspective cropping. Formula masking can leave a singleton interval; without
the guard the crop has width zero and docvortex raises `Unsupported warp
settings`. Normal boxes, formula recognition, parser tier and OCR mode are
unchanged. Discarded coordinates are logged as `[mineru-compat]` for review.
The guard does not edit the installed dependency or the input PDF. Other
MinerU versions use their original CLI. Existing successful receipts remain
valid; a failed job must be retried explicitly.

To retry just the first outstanding failed job, first inspect `status` and the
queue order, then use `run --retry-failed --max-items 1` with the same queue and
MinerU home. This is an attempt limit, not a rank selector: it may select an
earlier pending/interrupted item if one exists.

# Phase A — Source and identity

> Shared ingest phase. Obeys `.claude/skills/shared-references/ingest-invariants.md` (path, Zotero, slug rules) — do not restate those here.

## Purpose

Turn the chosen input into one usable prepared MinerU markdown, and settle the paper's identity (slug, bibliographic metadata, classification) before any interpretive writing.

## Steps

1. **Resolve the source by mode** (first match wins):
   - **INIT MODE** (source path from `.checkpoints/init-sources.json`, or prompt says "INIT MODE"): consume the handed-off `canonical_ingest_path` verbatim. Do not rescan `@raw-root`, do not re-prepare. See `.claude/skills/ingest/references/init-mode.md`.
   - **Prepared markdown** (`@configured-sources-papers/*.md`): use it directly.
   - **Zotero lookup** (`--title`/`--doi`): follow invariants §2 to select an unambiguous candidate, then run the single orchestration command below. Do not hand-compose a `prepare_paper_source.py` command and never pass `--item-key` or `--zotero-root` to it. The orchestration command writes a checkpoint metadata bundle and manifest, then prepares the selected PDF. Continue only when its JSON result has `status: ok` or `status: unusable`; a metadata/API error is a hard stop. Do not use SQLite/Crossref fallback for failed Zotero metadata.
   - **Raw local PDF**: not handled here — it must arrive pre-prepared from `/ingest-local-pdf`.
2. **Stop if the prepared source is unusable** (`usable: false`): surface the `warnings` verbatim and stop. Never substitute raw PDF text or MinerU cache intermediates. See `.claude/skills/ingest/references/error-handling.md`.
3. **Derive the paper slug** per invariants §3 and run **stop-if-exists**: if `@configured/papers/{slug}.md` exists with matching title/DOI, report and exit; if it collides with a *different* paper, stop per error-handling.
4. **Enrich bibliographic metadata** when a DOI or confident title is available: `tools/fetch_literature.py paper <doi-or-title>` for `venue`, `year`, `external_ids`, and citation-derived `importance` (1–5; default 3 and mark provisional if citation counts are unavailable). Zotero wins for user-curated identity fields; MinerU is the source of record for content.
5. **Classify the source** (fields defined in `docs/runtime-page-templates.en.md` §papers): `paper_type`, `research_modes` (∈ theory/computation/experiment), and `theory_tags` / `computation_tags` / `experiment_tags` / `research_object_tags`. Write `unclear` / `[]` rather than inventing.

For Zotero lookup mode, use this command after the candidate has been selected. The tool owns metadata-to-preprocessor wiring and writes `.checkpoints/ingest/<item-key>/metadata.json` and `manifest.json`:

```shell
uv run python -X utf8 tools/prepare_zotero_source.py --item-key <candidate.item_key> --output-dir '@configured-sources-papers' --cache-root '@mineru-cache'
```

Read `prepared.canonical_ingest_path`, `prepared.usable`, and `metadata_path` from its JSON output. If `status` is `error`, stop; if `status` is `unusable`, surface the warnings and stop. Do not invoke `prepare_paper_source.py` separately in this mode.

## Gate A — output this block before Phase B; if any line is ✗, stop and fix

```text
[Gate A] source & identity
- Zotero Local API metadata status: ok | n/a for non-Zotero handoff: ✓/✗
- prepared source path: <…>  (exists, size > 0B): ✓/✗
- source usable:true: ✓/✗
- slug source: zotero paper_slug | prepared paperSlug | paper-slug fallback  → "{slug}"
- stop-if-exists checked (no different-paper collision): ✓/✗
- importance: <n> (provisional? yes/no)
- paper_type ∈ {paper,review,book,degree_thesis,preprint,report,chapter,dataset,other}: ✓/✗
- research_modes ⊆ {theory,computation,experiment} and non-empty: ✓/✗
- for each mode present, its *_tags non-empty (or justified unclear): ✓/✗
- research_object_tags non-empty (or justified unclear): ✓/✗
```

Verify the prepared file is non-empty before proceeding:

```shell
uv run python -X utf8 tools/resolve_path_alias.py '@configured-sources-papers'
# then confirm the prepared <source-slug>.md exists and is > 0 bytes
```

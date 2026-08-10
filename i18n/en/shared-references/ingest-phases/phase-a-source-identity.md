# Phase A — Source and identity

> Shared ingest phase. Obeys `.claude/skills/shared-references/ingest-invariants.md` (path, Zotero, slug rules) — do not restate those here.

## Purpose

Turn the chosen input into one usable prepared MinerU markdown, and settle the paper's identity (slug, bibliographic metadata, classification) before any interpretive writing.

## Steps

1. **Resolve the source by mode** (first match wins):
   - **INIT MODE** (source path from `.checkpoints/init-sources.json`, or prompt says "INIT MODE"): consume the handed-off `canonical_ingest_path` verbatim. Do not rescan `@raw-root`, do not re-prepare. See `.claude/skills/ingest/references/init-mode.md`.
   - **Prepared markdown** (`@configured-sources-papers/*.md`): use it directly.
   - **Zotero lookup** (`--title`/`--doi`): follow invariants §2 to select an unambiguous candidate, then call `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>`. Continue only when the JSON result has `status: ok`; on a timeout, connection refusal, or any other non-`ok` status, stop immediately and ask the user to open Zotero Desktop, enable local API access, and rerun `/ingest` from the beginning. Do not use SQLite/Crossref fallback and do not start PDF preprocessing. After metadata succeeds, preprocess the selected PDF with `tools/prepare_paper_source.py`; see `.claude/skills/ingest/references/pdf-preprocessing.md`.
   - **Raw local PDF**: not handled here — it must arrive pre-prepared from `/ingest-local-pdf`.
2. **Stop if the prepared source is unusable** (`usable: false`): surface the `warnings` verbatim and stop. Never substitute raw PDF text or MinerU cache intermediates. See `.claude/skills/ingest/references/error-handling.md`.
3. **Derive the paper slug** per invariants §3 and run **stop-if-exists**: if `@configured/papers/{slug}.md` exists with matching title/DOI, report and exit; if it collides with a *different* paper, stop per error-handling.
4. **Enrich bibliographic metadata** when a DOI or confident title is available: `tools/fetch_literature.py paper <doi-or-title>` for `venue`, `year`, `external_ids`, and citation-derived `importance` (1–5; default 3 and mark provisional if citation counts are unavailable). Zotero wins for user-curated identity fields; MinerU is the source of record for content.
5. **Classify the source** (fields defined in `docs/runtime-page-templates.en.md` §papers): `paper_type`, `research_modes` (∈ theory/computation/experiment), and `theory_tags` / `computation_tags` / `experiment_tags` / `research_object_tags`. Write `unclear` / `[]` rather than inventing.

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

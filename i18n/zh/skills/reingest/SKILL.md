---
name: reingest
description: Regenerate an already-ingested paper page from its raw PDF or prepared MinerU markdown, refreshing paper analysis and migrating affected concept/claim/people pages when the new source changes the wiki's knowledge.
argument-hint: "<local-pdf-or-raw/tmp/papers/*.md> [--paper-only] [--update-entities] [--refresh-metadata] [--discover]"
---

# /reingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。

Regenerate an existing `wiki/papers/{slug}.md` from a raw PDF or prepared `mineru-md` source. Use this when the PDF→markdown adapter changed, the paper template changed, or the previous ingest was incomplete. By default, `/reingest` also audits and migrates affected `concepts`, `claims`, and `people` pages. `--update-entities` is now the default behavior and can be treated as a backward-compatible no-op. Use `--paper-only` only when the user explicitly wants to skip entity migration.

## Scope

`/reingest` updates the paper page, its canonical prepared source, and affected knowledge entities. It is not a reset:

- raw files under `raw/papers/`, `raw/notes/`, `raw/web/` remain read-only.
- `raw/tmp/papers/<slug>.md` may be overwritten via `tools/prepare_paper_source.py --overwrite`.
- entity migration is enabled by default; `--update-entities` does not need to be provided.
- `--paper-only` disables entity migration for this run.
- existing concept/claim/people pages must be reviewed and migrated when the regenerated source makes an old definition, claim status, confidence, evidence detail, alias, author metadata, or research-area summary stale or incomplete.
- entity migration may edit frontmatter and body text, but must preserve provenance: do not delete old evidence entries; qualify, supersede, or add counter-evidence instead.
- never delete concept/claim/people pages during reingest. If an entity appears obsolete, mark it as stale/deprecated where the schema supports it and report it.
- `wiki/graph/*` is updated only through `tools/research_wiki.py`.
- user-created custom sections in the old paper page should be preserved unless the user explicitly asks for a full rewrite.

## Workflow

Resolve `PYTHON_BIN` using the same logic as `/ingest`; prefer `.venv/bin/python`.

### Step 1: Resolve and refresh source

1. If input is a PDF, run:

   ```bash
   "$PYTHON_BIN" tools/prepare_paper_source.py \
     --raw-root raw \
     --source <pdf-path> \
     --overwrite
   ```

   Pass `--title` or `--arxiv-id` only when confidently recovered from the PDF itself or an existing trusted paper page.
2. If input is a prepared `raw/tmp/papers/*.md`, use it directly.
3. Stop if the prep manifest has `usable: false`; report warnings verbatim.

### Step 2: Match existing paper

1. Read the prepared markdown frontmatter title and generate slug:

   ```bash
   "$PYTHON_BIN" tools/research_wiki.py slug "<title>"
   ```

2. If `wiki/papers/{slug}.md` does not exist, stop and suggest `/ingest`; do not silently create a new paper page.
3. Read the existing paper page and preserve:
   - `cited_by`
   - stable identity metadata not present in the new source (`external_ids`, `code_url`, manually curated `importance` rationale)
   - existing `## Related` links unless the regenerated analysis still includes them elsewhere
   - any non-template custom section (sections other than Problem, Key idea, Research classification, Method, Results, Limitations, Open questions, My take, Related)

### Step 3: Regenerate paper analysis

Follow `/ingest` Step 2-4, but write to the existing paper page instead of creating a new one.

Required current paper fields include:

- `research_modes`: one or more of `theory`, `computation`, `experiment`
- `theory_tags`
- `computation_tags`
- `experiment_tags`
- `research_object_tags`

Body sections to regenerate:

`## Problem` / `## Key idea` / `## Research classification` / `## Method` / `## Results` / `## Limitations` / `## Open questions` / `## My take` / `## Related`

Use the retained bibliography in the prepared markdown to resolve inline references where useful. Do not cite references not present in either the bibliography or metadata lookup.

### Step 4: Audit and migrate entities

Unless `--paper-only` is explicitly set, review all existing entities connected to the old or regenerated paper page:

- pages linked in old/new `## Related`
- concepts whose `key_papers` includes this paper
- claims whose `source_papers` or `evidence[].source` includes this paper
- people pages linked from the paper or already listing it under `## Key papers`
- graph neighbors from `tools/research_wiki.py neighbors wiki/ papers/<slug>`

For each connected entity:

1. Compare the old entity statement against the regenerated source and bibliography-backed evidence.
2. Migrate when there is a substantive mismatch or missing precision:
   - **Concepts**: update Definition, Variants, Known limitations, Open problems, aliases, related_concepts, and `date_updated`; keep `key_papers`.
   - **Claims**: update Statement, Evidence summary, Conditions and scope, Counter-evidence, `confidence`, `status`, and `date_updated`; append new evidence or counter-evidence rather than deleting old entries.
   - **People**: update affiliation, research areas, recent work, collaborators, and key papers when the regenerated metadata/source gives clearer information.
3. If a new concept/claim is needed, run `find-similar-concept` or `find-similar-claim` before creating it. Prefer merging/migrating over creating duplicates.
4. For every paper → concept / claim / person link written in the regenerated page, ensure the reverse link/evidence exists.
5. Add new semantic edges with `tools/research_wiki.py add-edge`; it deduplicates existing edges.
6. Add bibliographic citations only when a reference resolves to an existing wiki paper and is truly cited by the source.

Do not remove old graph edges automatically. If the regenerated page or migrated entities no longer support an old edge, report it as “possibly stale” for `/check` or user review.

### Step 5: Rebuild and validate

Run:

```bash
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
"$PYTHON_BIN" tools/lint.py --wiki-dir wiki
"$PYTHON_BIN" tools/research_wiki.py log wiki/ "reingest | refreshed papers/<slug> | updated: <list>"
```

If lint fails, fix deterministic issues in the same turn unless doing so would delete user-authored content.

## Report

Summarize:

- prepared source refreshed path and warnings
- paper page updated
- entity migration summary: concepts/claims/people reviewed, updated, created, or marked stale
- graph edges/citations added
- stale relationships or ambiguous old links that need review
- lint result

Close with:

```text
Wiki: reingested papers/<slug> | updated: <list> | lint: <summary>
```

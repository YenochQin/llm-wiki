---
name: init
description: Use when building an initial wiki from user-owned local papers, notes, and web clips under the configured raw root. For environment or API-key configuration use /setup; for a single new paper use the appropriate ingest skill.
argument-hint: ""
---

# /init

> Build a wiki from `raw/` with deterministic source preparation, provisional notes/web scaffolding, and sequential handoff to the standard `/ingest` pipeline. Local papers only — `/init` does not search or download external papers.

Use these local references on demand:

- `references/prepare.md` — prepare flow and source-manifest rules

## Inputs

- User-owned sources under `raw/papers/`, `raw/notes/`, `raw/web/`

## Outputs

- `wiki/` scaffold and provisional pages (Summary, topics, ideas, concepts, claims)
- `wiki/sources/` prepared sources
- Final paper pages and linked entities through the standard `/ingest` pipeline
- `.checkpoints/init-*.json` manifests for resume and replay
- Updated `wiki/index.md`, `wiki/log/`, `wiki/graph/*`

## Wiki Interaction

### Reads

- `raw/papers/`, `raw/notes/`, `raw/web/`
- `.checkpoints/init-prepare.json` and `.checkpoints/init-sources.json` for source order and resume
- `wiki/index.md` plus existing `wiki/topics/`, `wiki/ideas/`, `wiki/concepts/`, `wiki/claims/` for duplicate avoidance and scaffold alignment

### Writes

- `wiki/` scaffold and provisional pages
- `wiki/sources/`
- `wiki/index.md`, `wiki/log/`, `wiki/graph/*`
- `.checkpoints/init-prepare.json`, `.checkpoints/init-sources.json`, and `init-session` checkpoint metadata

### Graph edges created

- `/init` itself creates only scaffold-level edges when provisional pages need them
- all paper-driven pages and edges are delegated to `/ingest` using the prepared source handoff

## Workflow

**Pre-condition**: working directory is the project root containing `tools/`, `pyproject.toml`, and `config/paths.json`. Run Python tools through `uv run python -X utf8`, matching `README.md`. Do not hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, `@raw-root`, `@configured-sources`, `@configured-sources-papers`, and `@mineru-cache`. By default, `tools/_paths.py` loads `config/paths.json` and the documented `LLM_WIKI_*` overrides; only override these roots when the user explicitly requests it.

Run commands from the repository root.

```shell
uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@raw-root' '@experiment-root' '@output-root'
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

If path diagnosis is needed, use `uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@raw-root' '@experiment-root' '@output-root' '@configured-sources' '@configured-sources-papers' '@mineru-cache'`. Do not import path helpers from `tools._env`; runtime path aliases are resolved by `tools/_paths.py` through this CLI.

On resume, load `init-session` with `checkpoint-load` and read the existing preparation/source manifests before starting new work. Reuse unchanged prepared sources and scaffold pages; when Steps 1–4 are already valid, continue at Step 5. Per-paper recovery state is defined in [../ingest/references/init-handoff.md](../ingest/references/init-handoff.md).

### Step 1: Initialize wiki structure

```shell
uv run python -X utf8 tools/research_wiki.py init '@configured'
```

Create the standard wiki directories, `graph/`, `index.md`, and `log/`, plus the configured independent experiment and output roots. Do not add a second init log entry here.

### Step 2: Prepare local inputs into `wiki/sources/`

```shell
uv run python -X utf8 tools/init_discovery.py prepare --raw-root '@raw-root' --wiki-root '@configured' --sources-output-dir '@configured-sources' --cache-root '@mineru-cache' --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json
```

- before running `prepare`, inspect each local PDF and write the recovery handoff to `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }`, `{ "@raw-root/papers/foo.pdf": "Recovered Paper Title" }`, or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title" } }`
- use `uv run python -X utf8 tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source <local-path> [--title "<recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]` for local paper normalization; the helper also attempts Zotero metadata enrichment and uses the citation key for source naming when available; enrichment failure is non-blocking and falls back to `author_year_veryshorttitle` source naming
- local PDF recovery order: agent-recovered title from the first page -> MinerU produces structured markdown under `@configured-sources-papers/<source-slug>.md`; `<source-slug>` uses the sanitized Zotero citation key when metadata enrichment finds one, otherwise `author_year_veryshorttitle`
- never pass literal relative output paths such as `wiki/sources` or `wiki/sources/papers`; these resolve inside the code repository when the wiki is split into an external vault. Use `@configured-sources` and `@configured-sources-papers`.
- when the agent supplied a PDF title, treat that title as authoritative for the prepared manifest; fetched/source titles are sanitized fallback metadata only and must not overwrite it
- metadata or filename titles may remain as provisional display labels only; they are not trusted identity or title-search inputs
- keep notes/web on their original source paths; `/init` reads them directly during scaffolding
- set each local paper's `canonical_ingest_path` to the prepared configured source path when available; if preparation fails, mark the paper skipped instead of handing off the original `raw/papers/...` path
- record warnings for failed decode / title recovery rather than aborting `/init`
- see `references/prepare.md` for the prepare decision tree and source-preference rules

### Step 3: Build the source manifest

```shell
uv run python -X utf8 tools/init_discovery.py manifest --raw-root '@raw-root' --wiki-root '@configured' --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json
```

- `manifest` reads `.checkpoints/init-prepare.json` and emits one `origin=user_local` entry per usable prepared paper
- `.checkpoints/init-sources.json` is the single source of truth for downstream ingest order
- if no parseable papers exist, `manifest` still writes an empty `sources` array; skip Step 5 and finalize the scaffold-only run in Step 6

### Step 4: Create scaffold pages before paper ingest

Create one `wiki/Summary/{area}.md`, the needed `wiki/topics/{slug}.md`, and provisional `ideas/`, `concepts/`, and `claims/` from notes/web when warranted.

Rules:

- notes/web are authoritative for user intent, not for literature confidence
- every notes/web-derived page must include this exact line immediately after frontmatter:

```markdown
Provisional note: seeded from raw/notes or raw/web during /init; pending validation from ingested papers.
```

- `topics/`: create when a direction is explicit or repeated
- `ideas/`: create when the user states or strongly implies a research direction or hypothesis
- `concepts/`: create only when the mechanism recurs across notes/web, or appears once in notes/web and once in the final paper set
- `claims/`: create only from explicit assertive statements, never by inference
- for notes/web-derived claims, use `status: proposed`, `confidence: 0.2`, `source_papers: []`, and `evidence: []`
- `/prefill` is optional background seeding and is not part of `/init`
- `/init` must not create `people/` pages directly and must not auto-create foundations

### Step 5: Run the standard ingest pipeline for each prepared paper

Read paper entries from `.checkpoints/init-sources.json` in `shortlist_rank` order. Every entry is `origin=user_local` with a usable `canonical_ingest_path` already prepared by MinerU.

For each entry:

1. Check the entry's `init-session` recovery record before deciding whether an existing paper should be skipped. Follow `.claude/skills/ingest/references/init-handoff.md`: completed entries and papers predating this session are skipped; verified incomplete entries resume their unfinished work. An existing file alone does not establish completion.
2. Pass `canonical_ingest_path` and the verified recovery state to `/ingest`. Use its Phases A–E and Gate checks; reuse validated completed work on resume. `/ingest` owns paper/entities, deduplication, links, citations, navigation, logs, and scoped grounding checks.
3. Persist the recovery record before the first content write and after each write/phase, as specified in the handoff reference. Mark completed only after Gate E passes; otherwise retain the incomplete state and concrete remaining steps.
4. Preserve completed writes on failure and continue with other entries. If provenance or intervening edits prevent safe recovery, keep the entry incomplete and report the blocker; do not relabel it skipped or silently switch to reingest.

Do not enable omitted user-facing flags such as `--discover`. Prepared sources enter `/ingest` directly; `/ingest-local-pdf` remains the entrypoint for separate user requests to prepare local PDFs.

### Step 6: Finalize navigation and report

After processing the manifest entries (or completing a scaffold-only run), refresh the final wiki navigation:

```shell
uv run python -X utf8 tools/research_wiki.py dedup-edges '@configured'
uv run python -X utf8 tools/research_wiki.py dedup-citations '@configured'
uv run python -X utf8 tools/research_wiki.py rebuild-index '@configured'
uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'
uv run python -X utf8 tools/research_wiki.py rebuild-open-questions '@configured'
uv run python -X utf8 tools/lint.py --wiki-dir '@configured' --fix
```

Report separately:

- user-provided papers ingested through prepared `wiki/sources/` paths
- provisional pages seeded from notes/web
- pages created by `/ingest`
- pages updated by `/ingest`
- any skipped or failed papers

## Constraints

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs
- `wiki/sources/` is a generated handoff area; `/ingest-local-pdf` may also prepare reusable local sidecars under `wiki/sources/`
- `/init` may write generated prepared local sources to `wiki/sources/`; it does not download external papers
- `/prefill` is optional background seeding, not part of `/init`
- no skill other than `/prefill` may auto-create foundations
- `/init` must not create `people/` pages directly
- notes/web-derived pages are provisional and must carry the exact notice line above
- paper evidence outranks notes/web for claim confidence and concept consolidation
- prepared local papers run sequentially through the existing `/ingest` Phases A–E, including reverse links and final checks
- Step 5 must read paper inputs from `.checkpoints/init-sources.json`, not by ad hoc folder scanning

## Error Handling

- **No parseable paper in `raw/papers/`**: skip Step 5 and finalize the scaffold and provisional pages in Step 6
- **`raw/notes/` and `raw/web/` empty**: skip provisional seeding, continue
- **MinerU prep fails (token unset, API outage, manifest `usable: false`)**: skip that paper, record the warning in `.checkpoints/init-prepare.json`, and continue. Do not silently substitute the raw PDF — `mineru-md` is the contract
- **No confident PDF title is recovered**: omit `--title`; any metadata-or-filename title is display-only
- **Single paper ingest fails**: record it via checkpoint, skip it, continue the rest, and list it in the report

## Dependencies

### Tools

- `uv run python -X utf8 tools/research_wiki.py init '@configured'`
- `uv run python -X utf8 tools/research_wiki.py checkpoint-set-meta '@configured' init-session <key> <value>`
- `uv run python -X utf8 tools/research_wiki.py checkpoint-save/load/clear '@configured' init-session ...`
- `uv run python -X utf8 tools/research_wiki.py dedup-edges '@configured'`
- `uv run python -X utf8 tools/research_wiki.py dedup-citations '@configured'`
- `uv run python -X utf8 tools/research_wiki.py rebuild-index '@configured'`
- `uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'`
- `uv run python -X utf8 tools/research_wiki.py rebuild-open-questions '@configured'`
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"`
- `uv run python -X utf8 tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source <local-path> [--title "<recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]`
- `uv run python -X utf8 tools/init_discovery.py prepare --raw-root '@raw-root' --wiki-root '@configured' --sources-output-dir '@configured-sources' --cache-root '@mineru-cache' --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`
- `uv run python -X utf8 tools/init_discovery.py manifest --raw-root '@raw-root' --wiki-root '@configured' --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json`
- `uv run python -X utf8 tools/lint.py --wiki-dir '@configured' --fix`

### Skills

- `/ingest` — consumes each prepared source directly and runs the standard paper/entity pipeline

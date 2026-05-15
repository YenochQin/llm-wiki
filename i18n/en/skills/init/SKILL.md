---
description: Bootstrap LLM-Wiki from local user sources, then ingest the prepared local paper set in parallel through /ingest-local-pdf
argument-hint: ""
---

# /init

> Build a wiki from `raw/` with deterministic source preparation, provisional notes/web scaffolding, and parallel `/ingest-local-pdf` fan-out/fan-in. Local papers only — `/init` does not search or download external papers.

Use these local references on demand:

- `references/prepare.md` — prepare flow and source-manifest rules
- `references/parallel-ingest.md` — worktree isolation, subagent prompt contract, merge, and cleanup

## Inputs

- User-owned sources under `raw/papers/`, `raw/notes/`, `raw/web/`

## Outputs

- `wiki/` scaffold and provisional pages (Summary, topics, ideas, concepts, claims)
- `wiki/sources/` prepared sources
- Final paper pages via parallel `/ingest-local-pdf` subagents
- `.checkpoints/init-*.json` manifests for resume and replay
- Updated `wiki/index.md`, `wiki/log.md`, `wiki/graph/*`

## Wiki Interaction

### Reads

- `raw/papers/`, `raw/notes/`, `raw/web/`
- `.checkpoints/init-prepare.json` and `.checkpoints/init-sources.json` for resume and fan-out
- `wiki/index.md` plus existing `wiki/topics/`, `wiki/ideas/`, `wiki/concepts/`, `wiki/claims/` for duplicate avoidance and scaffold alignment

### Writes

- `wiki/` scaffold and provisional pages
- `wiki/sources/`
- `wiki/index.md`, `wiki/log.md`, `wiki/graph/*`
- `.checkpoints/init-prepare.json`, `.checkpoints/init-sources.json`, and `init-session` checkpoint metadata

### Graph edges created

- `/init` itself creates only scaffold-level edges when provisional pages need them
- all paper-driven edges are delegated to `/ingest-local-pdf`, which hands prepared sources to `/ingest`

## Workflow

**Pre-condition**: working directory is the project root containing `tools/`, `pyproject.toml`, and `config/paths.json`. Run Python tools through `uv run python`, matching `README.md`. Do not hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, `@raw-root`, `@configured-sources`, `@configured-sources-papers`, and `@mineru-cache`. By default, `tools/_paths.py` loads `config/paths.json` and the documented `LLM_WIKI_*` overrides; only override these roots when the user explicitly requests it.

```bash
# Run all commands from the repository root; runtime paths are resolved by tool aliases.
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT=$(pwd)
fi
cd "$PROJECT_ROOT"

uv run python tools/research_wiki.py stats @configured --json >/dev/null
```

### Step 1: Initialize wiki structure

```bash
uv run python tools/research_wiki.py init @configured
```

Create the standard wiki directories, `graph/`, `outputs/`, `index.md`, and `log.md`. Do not add a second init log entry here.

### Step 2: Prepare local inputs into `wiki/sources/`

```bash
uv run python tools/init_discovery.py prepare --raw-root @raw-root --wiki-root @configured --sources-output-dir @configured-sources --cache-root @mineru-cache --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json
```

- before running `prepare`, inspect each local PDF and write the recovery handoff to `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }`, `{ "@raw-root/papers/foo.pdf": "Recovered Paper Title" }`, or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title" } }`
- use `uv run python tools/prepare_paper_source.py --raw-root @raw-root --output-dir @configured-sources-papers --cache-root @mineru-cache --source <local-path> [--title "<recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]` for local paper normalization; the helper also attempts Zotero metadata enrichment and uses the citation key for source naming when available; enrichment failure is non-blocking and falls back to `author_year_veryshorttitle` source naming
- local PDF recovery order: agent-recovered title from the first page -> MinerU produces structured markdown at `wiki/sources/papers/<source-slug>.md`; `<source-slug>` uses the sanitized Zotero citation key when metadata enrichment finds one, otherwise `author_year_veryshorttitle`
- when the agent supplied a PDF title, treat that title as authoritative for the prepared manifest; fetched/source titles are sanitized fallback metadata only and must not overwrite it
- metadata or filename titles may remain as provisional display labels only; they are not trusted identity or title-search inputs
- keep notes/web on their original source paths; `/init` reads them directly during scaffolding
- set each local paper's `canonical_ingest_path` to a prepared `wiki/sources/` path when available; if preparation fails, mark the paper skipped instead of handing off the original `raw/papers/...` path
- record warnings for failed decode / title recovery rather than aborting `/init`
- see `references/prepare.md` for the prepare decision tree and source-preference rules

### Step 3: Build the source manifest

```bash
uv run python tools/init_discovery.py manifest --raw-root @raw-root --wiki-root @configured --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json
```

- `manifest` reads `.checkpoints/init-prepare.json` and emits one `origin=user_local` entry per usable prepared paper
- `.checkpoints/init-sources.json` is the single source of truth for downstream ingest order
- if no parseable papers exist, `manifest` still writes an empty `sources` array; in that case stop after Step 4 (scaffold-only run) and report the result

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

### Step 5: Parallel paper ingest with worktree isolation

Paper sources for this step come strictly from `.checkpoints/init-sources.json`. Every entry is `origin=user_local` with a canonical prepared `wiki/sources/papers/<source-slug>.md` (MinerU output); the helper refuses to fall back to a raw PDF.

Parallel local ingest contract:

- stash unrelated dirty files before fan-out, then record `stash_ref`, `base_branch`, and `base_commit` in checkpoint metadata
- commit the freshly created scaffold and init manifests before fan-out so `BASE_COMMIT` actually contains the pages, manifests, and handoff metadata that subagents must branch from
- verify `.gitattributes` contains `merge=union` for `wiki/log.md`, `wiki/graph/edges.jsonl`, `wiki/graph/citations.jsonl`, and `wiki/index.md` before creating worktrees
- `/init` worktree mode must run from a named branch, not detached HEAD
- create each worktree from `BASE_COMMIT`, not from the already checked-out `BASE_BRANCH`
- subagent prompts must use **relative paths only**, and the subagent's shell working directory must be the worktree path (`$WT_PATH`), not the main repository root
- execute `/ingest-local-pdf` for exactly one handed-off source path; do not bypass `/ingest-local-pdf`
- in INIT MODE, consume the handed-off canonical path exactly as provided
- skip `fetch_literature.py citations`
- skip `fetch_literature.py references`
- skip per-subagent `rebuild-index`
- skip per-subagent `rebuild-context-brief`
- skip per-subagent `rebuild-open-questions`
- skip conflict-prone topic writes
- commit the ingest result inside the worktree before exiting so fan-in merges a real paper-specific commit instead of an empty branch
- see `references/parallel-ingest.md` for worktree commands, merge order, fan-in, and cleanup

### Step 6: Fan-in, rebuild, and final report

After all subagents complete:

- merge worktree branches sequentially on `BASE_BRANCH`
- resolve true concept / claim conflicts conservatively: merge, do not multiply near-duplicates
- run:

```bash
uv run python tools/research_wiki.py dedup-edges @configured
uv run python tools/research_wiki.py dedup-citations @configured
uv run python tools/research_wiki.py rebuild-index @configured
uv run python tools/research_wiki.py rebuild-context-brief @configured
uv run python tools/research_wiki.py rebuild-open-questions @configured
uv run python tools/lint.py --wiki-dir @configured --fix
```

Report separately:

- user-provided papers ingested through prepared `wiki/sources/` paths
- user-provided papers that fell back to original `raw/papers/` paths
- provisional pages seeded from notes/web
- pages created by `/ingest`
- pages updated by `/ingest`
- any skipped or failed papers

If `stash_ref` exists, pop it at the end. If stash pop fails, keep the checkpoint and report the failure.

## Constraints

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs
- `wiki/sources/` is a generated handoff area; `/ingest-local-pdf` may also prepare reusable local sidecars under `wiki/sources/`
- `/init` may write generated prepared local sources to `wiki/sources/`; it does not download external papers
- `/prefill` is optional background seeding, not part of `/init`
- no skill other than `/prefill` may auto-create foundations
- `/init` must not create `people/` pages directly
- notes/web-derived pages are provisional and must carry the exact notice line above
- paper evidence outranks notes/web for claim confidence and concept consolidation
- all local paper ingest must run through parallel `/ingest-local-pdf` subagents with worktree isolation
- Step 5 must read paper inputs from `.checkpoints/init-sources.json`, not by ad hoc folder scanning

## Error Handling

- **No parseable paper in `raw/papers/`**: skip Step 5 entirely; `/init` finishes after the scaffold and provisional pages
- **`raw/notes/` and `raw/web/` empty**: skip provisional seeding, continue
- **MinerU prep fails (token unset, API outage, manifest `usable: false`)**: skip that paper, record the warning in `.checkpoints/init-prepare.json`, and continue. Do not silently substitute the raw PDF — `mineru-md` is the contract
- **No confident PDF title is recovered**: omit `--title`; any metadata-or-filename title is display-only
- **Single paper ingest fails**: record it via checkpoint, skip it, continue the rest, and list it in the report
- **Current checkout is detached HEAD**: stop before worktree fan-out and ask the user to switch to or create a named branch first
- **stash pop fails**: keep checkpoint metadata and report the manual recovery step

## Dependencies

### Tools (via Bash)

- `uv run python tools/research_wiki.py init @configured`
- `uv run python tools/research_wiki.py checkpoint-set-meta @configured init-session <key> <value>`
- `uv run python tools/research_wiki.py checkpoint-save/load/clear @configured init-session ...`
- `uv run python tools/research_wiki.py dedup-edges @configured`
- `uv run python tools/research_wiki.py dedup-citations @configured`
- `uv run python tools/research_wiki.py rebuild-index @configured`
- `uv run python tools/research_wiki.py rebuild-context-brief @configured`
- `uv run python tools/research_wiki.py rebuild-open-questions @configured`
- `uv run python tools/research_wiki.py log @configured "<message>"`
- `uv run python tools/prepare_paper_source.py --raw-root @raw-root --output-dir @configured-sources-papers --cache-root @mineru-cache --source <local-path> [--title "<recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]`
- `uv run python tools/init_discovery.py prepare --raw-root @raw-root --wiki-root @configured --sources-output-dir @configured-sources --cache-root @mineru-cache --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`
- `uv run python tools/init_discovery.py manifest --raw-root @raw-root --wiki-root @configured --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json`
- `uv run python tools/lint.py --wiki-dir @configured --fix`

### Skills

- `/ingest-local-pdf` — one local prepared paper per subagent, in INIT MODE handoff
- `/ingest` — consumes each prepared source after `/ingest-local-pdf` handoff

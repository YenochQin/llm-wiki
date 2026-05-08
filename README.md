# llm-wiki

A personal LLM-maintained research wiki. Adopts the OmegaWiki workflow (24 → 21 Claude Code skills, 9 typed page kinds, claim/experiment graph) but swaps the PDF preprocessing layer for [MinerU](https://mineru.net/) — a vision-language parser that gives section-aware structured markdown.

See [`llm-wiki.md`](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md) for the underlying pattern (Karpathy).

## Quick start

```bash
# 1. Install uv if you don't have it: https://docs.astral.sh/uv/
# 2. From the project root:
bash setup.sh

# 3. Set MINERU_API_TOKEN in ~/.config/llm-wiki/.env (required for PDF ingest)
#    Get a free token at https://mineru.net/

# 4. Start Claude Code:
claude

# 5. Inside Claude Code:
/setup              # guided API key configuration
/init <topic>       # bootstrap the wiki around a research topic
/ingest <pdf>       # add a single source
/reingest <pdf>     # regenerate an existing paper and migrate linked entities
/ask <question>     # query the wiki with citations
```

## Architecture

```
raw/         — user-owned source documents (PDFs, notes, web clips). Read-only to the LLM.
raw/prepared/ — MinerU-prepared structured markdown (canonical_ingest_path lives here).
wiki/        — LLM-maintained markdown: papers, concepts, topics, people, ideas, experiments, claims, Summary, foundations, outputs.
wiki/graph/  — auto-derived graph state (edges, citations, context_brief). Never hand-edit.
tools/       — Python tooling (run via `uv run python tools/<name>.py`).
skills/      — canonical skills entrypoint for the active language; `.claude/skills` and `.agents/skills` point here.
omega/       — optional OmegaWiki spillover (remote experiment helpers, compatibility config).
```

## Skills (21)

`setup, reset, init, prefill, ingest, reingest, discover, ask, edit, check, novelty, review, ideate, exp-design, exp-eval, refine, paper-plan, paper-draft, survey, research, rebuttal`.

Dropped from upstream OmegaWiki: `daily-arxiv, paper-compile, exp-run, exp-status`. `/research` stays design-only: the user runs experiments externally and reports results back to `/exp-eval`.

## PDF preprocessing

PDF → MinerU markdown adapter. See [`docs/mineru-pipeline.md`](docs/mineru-pipeline.md) for the full pipeline, cache layout, and adapter passes. The output format is `mineru-md`; `/ingest` consumes it via the `canonical_ingest_path` field of the prep tool's JSON manifest.

`/ingest` can also locate a PDF from Zotero with `--zotero-root <Zotero data dir or profile dir>` plus `--title`, `--doi`, or `--item-key`. The Zotero helper reads `prefs.js` when needed, then opens `zotero.sqlite` and attachments read-only before feeding the selected PDF into the same MinerU pipeline without copying it into `raw/papers/`.

Use `/reingest <pdf-or-raw/prepared/papers/*.md>` when a paper already exists in `wiki/papers/` but the PDF adapter, template, or analysis policy has changed. It refreshes the prepared markdown, regenerates the paper page, and by default audits/migrates linked `concepts`, `claims`, and `people` pages. Pass `--paper-only` only for a paper-page-only refresh; `--update-entities` is kept as a compatibility flag and is already the default behavior.

## Python tooling

All Python operations run through `uv` — no manual venv activation needed:

```bash
uv run python tools/research_wiki.py --help
uv run python tools/lint.py
uv run python tools/prepare_paper_source.py --raw-root raw --source raw/papers/<file>.pdf
```

The optional local MinerU backend (downloads several GB of models on first run) is opt-in:

```bash
uv sync --extra local
```

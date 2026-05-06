# llm-wiki

A personal LLM-maintained research wiki. Adopts the OmegaWiki workflow (24 → 20 Claude Code skills, 9 typed page kinds, claim/experiment graph) but swaps the PDF preprocessing layer for [MinerU](https://mineru.net/) — a vision-language parser that gives section-aware structured markdown.

See [`../llm-wiki.md`](../llm-wiki.md) for the underlying pattern (Karpathy).

## Quick start

```bash
# 1. Install uv if you don't have it: https://docs.astral.sh/uv/
# 2. From the project root:
bash setup.sh

# 3. Set MINERU_API_TOKEN in ~/.config/MinerU/mineru.env (required for PDF ingest)
#    Get a free token at https://mineru.net/

# 4. Start Claude Code:
claude

# 5. Inside Claude Code:
/setup              # guided API key configuration
/init <topic>       # bootstrap the wiki around a research topic
/ingest <pdf>       # add a single source
/ask <question>     # query the wiki with citations
```

## Architecture

```
raw/         — user-owned source documents (PDFs, notes, web clips). Read-only to the LLM.
raw/tmp/     — MinerU-prepared structured markdown (canonical_ingest_path lives here).
wiki/        — LLM-maintained markdown: papers, concepts, topics, people, ideas, experiments, claims, Summary, foundations, outputs.
wiki/graph/  — auto-derived graph state (edges, citations, context_brief). Never hand-edit.
tools/       — Python tooling (run via `uv run python tools/<name>.py`).
i18n/en/     — canonical skills + shared references (synced into .claude/ by setup.sh).
```

## Skills (20)

`setup, reset, init, prefill, ingest, discover, ask, edit, check, novelty, review, ideate, exp-design, exp-eval, refine, paper-plan, paper-draft, survey, research, rebuttal`.

Dropped from upstream OmegaWiki: `daily-arxiv, paper-compile, exp-run, exp-status` (and `/research` is design-only — user runs experiments externally and reports results back to `/exp-eval`).

## PDF preprocessing

PDF → MinerU markdown adapter. See [`docs/mineru-pipeline.md`](docs/mineru-pipeline.md) for the full pipeline, cache layout, and adapter passes. The output format is `mineru-md`; `/ingest` consumes it via the `canonical_ingest_path` field of the prep tool's JSON manifest.

## Python tooling

All Python operations run through `uv` — no manual venv activation needed:

```bash
uv run python tools/research_wiki.py --help
uv run python tools/lint.py
uv run python tools/prepare_paper_source.py --raw-root raw --source raw/papers/<file>.pdf
```

The optional local MinerU backend (downloads several GB of models on first run) is opt-in:

```bash
uv pip install -e ".[local]"
```

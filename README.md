# llm-wiki

A personal LLM-maintained research wiki. Adapts the [LLM-Wiki](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md) workflow and replaces the PDF preprocessing layer with [MinerU](https://mineru.net/) — a vision-language parser that produces section-aware structured markdown.

Supported agents: **Claude Code** and **Codex**. Runtime entry points:
- [`CLAUDE.md`](CLAUDE.md) — spec loaded by Claude Code
- [`AGENTS.md`](AGENTS.md) — spec loaded by Codex
- [`skills/`](skills) — symlink to the active-language skill set under `i18n/`; both agents share the same set via `.claude/skills` and `.agents/skills`.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python environment + dependency manager)
- Python >= 3.10, or a compatible interpreter resolved by `uv`
- One of:
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI, or
  - [Codex CLI](https://github.com/openai/codex)
- `MINERU_API_TOKEN` from [mineru.net](https://mineru.net/) — free, required for the default cloud PDF backend. Skip only if you install the local backend (`uv sync --extra local`, several GB of models).

## Quick start

```bash
# 1. From the project root, install deps and activate English runtime files:
bash setup.sh                # or: ./setup.sh --lang zh

# 2. Put your MinerU token in ~/.config/llm-wiki/.env
#    (setup.sh seeded the file from config/.env.example)
```

Then pick the agent you want to drive the wiki with.

### Using Claude Code

```bash
claude
/setup                           # guided API key configuration
/init <topic>                    # seed the wiki around a research topic
/ingest --doi <doi>              # add a Zotero-backed paper
/ingest-local-pdf <pdf>          # normalize a local PDF, then ingest it
/ask <question>                  # query the wiki with citations
```

### Using Codex

Codex reads `AGENTS.md` and the same skill files under `skills/` (via the `.agents/skills` symlink). From the Codex CLI, launch `codex` in the project root and ask it to read and follow the relevant skill file with your arguments:

```text
read and follow skills/setup/SKILL.md
read and follow skills/init/SKILL.md with: <topic>
read and follow skills/ingest/SKILL.md with: --doi <doi>
read and follow skills/ingest-local-pdf/SKILL.md with: <pdf>
read and follow skills/ask/SKILL.md with: <question>
```

If your Codex build exposes slash commands directly, you can use the same `/setup`, `/init`, `/ingest`, `/ingest-local-pdf`, and `/ask` forms as above. The skill files are self-contained and agent-agnostic.

`setup.sh` copies `i18n/{lang}/{CLAUDE,AGENTS}.md` to the repo root and points `skills/`, `.claude/skills`, and `.agents/skills` at `i18n/{lang}/skills/`. Its prompts are still Claude-oriented, but it installs the shared Codex runtime files too. Edit the originals under `i18n/`, not the root copies.

## Architecture

```
raw/           user-owned originals (PDFs, notes, web clips). Read-only to the LLM.
wiki/sources/  vault-visible sources: MinerU-converted paper markdown, copied notes and web clips.
wiki/          LLM-maintained pages: papers, concepts, topics, people, ideas, experiments, claims, Summary, foundations, outputs.
wiki/graph/    auto-derived edges, citations, context_brief — never hand-edit.
tools/         Python CLIs (run via uv).
skills/        active-language skill entrypoint (symlinked from i18n/).
mcp-servers/   optional project MCP servers (includes llm-review for cross-model review).
i18n/          source of truth for CLAUDE.md, AGENTS.md, and skills in each language.
docs/          pipeline docs, runtime references, page templates.
```

`wiki/` renders as an Obsidian vault: internal links use `[[slug]]` wikilinks, and every forward link has a required reverse link (see the cross-reference rules in `CLAUDE.md` or `AGENTS.md`).

### External vault paths

`wiki/` and `raw/` can live outside this code repository. Put OS-specific absolute paths in `config/paths.json` (gitignored; see `config/paths.json.example`), then copy the vault out:

```bash
uv run python tools/separate_wiki_repository.py \
  --wiki-root /abs/path/to/wiki \
  --raw-root /abs/path/to/raw \
  --mode copy --yes
```

After verifying the external copy, optionally clean the in-repo `wiki/` and `raw/` directories:

```bash
uv run python tools/clean_wiki_repository.py --target all --yes
```

`active_profile: "auto"` chooses `macos`, `windows`, or `linux` based on the current OS. Override with `LLM_WIKI_PATH_PROFILE`. Graph commands accept `@wiki` to resolve the configured vault:

```bash
uv run python tools/research_wiki.py rebuild-index @wiki
```

## Skills (22)

Grouped by workflow phase:

| Phase | Skills |
|-------|--------|
| Setup | `setup`, `reset` |
| Bootstrap & ingest | `init`, `prefill`, `ingest`, `ingest-local-pdf`, `reingest`, `discover` |
| Explore & maintain | `ask`, `edit`, `check`, `novelty`, `review` |
| Research cycle | `ideate`, `exp-design`, `exp-eval`, `refine`, `research` |
| Produce | `paper-plan`, `paper-draft`, `survey`, `rebuttal` |

## PDF preprocessing

PDF → MinerU markdown adapter. See [`docs/mineru-pipeline.md`](docs/mineru-pipeline.md) for the full pipeline, cache layout, and adapter passes. Canonical ingest format is `mineru-md`.

- **`/ingest-local-pdf`** — for raw PDFs or directory batches. Prepares `wiki/sources/papers/*.md` and hands off to `/ingest`.
- **`/ingest`** — consumes prepared markdown or resolves a Zotero attachment via `--title` or `--doi`. Scans the cross-platform candidates in `config/zotero-roots.json`; override with `--zotero-root <Zotero data dir>`. The Zotero helper snapshots `zotero.sqlite` into `config/zotero-cache/` and queries it read-only. If Zotero Desktop's local API is running, metadata (title, DOI, year, venue, creators, abstract, tags, citation key, `bibtex`) is pulled from there and falls back to SQLite + Crossref. Zotero `--item-key` is not a user-facing `/ingest` selector; selected candidates may still use their internal `item_key` for metadata enrichment.
- **`/ingest-light`** — lightweight intake for dissertation-introduction or background papers. Creates a compact paper page, tags it for `thesis-introduction`, and links it to a target Summary without expanding the full concept/claim/people graph.
- **`/reingest`** — rerun the adapter and migrate linked entities after the PDF adapter, template, or analysis policy changes. `--paper-only` skips the entity audit.

Metadata-only inputs don't create paper pages on their own — they enrich an existing content source (prepared markdown, note, or web clip).

## Python tooling

All Python operations run through `uv` — no manual venv activation:

```bash
uv run python tools/research_wiki.py --help
uv run python tools/lint.py
uv run python tools/prepare_paper_source.py --source raw/papers/<file>.pdf
```

Optional local MinerU backend (downloads several GB of models on first run):

```bash
uv sync --extra local
```

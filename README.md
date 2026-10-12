# llm-wiki

A personal LLM-maintained research wiki. Adapts the [LLM-Wiki](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md) workflow and replaces the PDF preprocessing layer with [MinerU](https://mineru.net/) — a vision-language parser that produces section-aware structured markdown.

Supported agents: **Claude Code** and **Codex**. Runtime entry points:
- [`CLAUDE.md`](CLAUDE.md) — spec loaded by Claude Code
- [`AGENTS.md`](AGENTS.md) — spec loaded by Codex
- [`skills/`](skills) — canonical English skills and shared references; both agents use this same directory via `.claude/skills` and `.agents/skills`.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python environment + dependency manager)
- Python >= 3.10, or a compatible interpreter resolved by `uv`
- One of:
  - [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI, or
  - [Codex CLI](https://github.com/openai/codex)
- `MINERU_API_TOKEN` from [mineru.net](https://mineru.net/) — free, required for the default cloud PDF backend. Skip only if you install the local backend (`uv sync --extra local`, several GB of models).

## Quick start

```bash
# 1. From the project root, install dependencies and link agent skill entrypoints:
bash setup.sh

# 2. Put your MinerU token in ~/.config/llm-wiki/.env
#    (setup.sh seeded the file from config/.env.example)
```

On Windows, run the PowerShell setup. It creates symlinks from
`.claude/skills` and `.agents/skills` to the canonical `skills/` directory; enable Developer Mode or
run PowerShell as Administrator if symlink creation is denied:

```powershell
pwsh -File .\setup.ps1
```

Then pick the agent you want to drive the wiki with.

### Using Claude Code

```bash
claude
/setup                           # guided API key configuration
/init                            # build the wiki from configured local sources
/ingest --doi <doi>              # add a Zotero-backed paper
/ingest-local-pdf <pdf>          # normalize a local PDF, then ingest it
/ask <question>                  # query the wiki with citations
```

### Using Codex

Codex reads `AGENTS.md` and the same skill files under `skills/` (via the `.agents/skills` symlink). From the Codex CLI, launch `codex` in the project root and ask it to read and follow the relevant skill file with your arguments:

```text
read and follow skills/setup/SKILL.md
read and follow skills/init/SKILL.md
read and follow skills/ingest/SKILL.md with: --doi <doi>
read and follow skills/ingest-local-pdf/SKILL.md with: <pdf>
read and follow skills/ask/SKILL.md with: <question>
```

If your Codex build exposes slash commands directly, you can use the same `/setup`, `/init`, `/ingest`, `/ingest-local-pdf`, and `/ask` forms as above. The skill files are self-contained and agent-agnostic.

Maintain `skills/`, `skills/shared-references/`, `AGENTS.md`, and `CLAUDE.md` directly. Setup links both agents to the same skill directory and never copies or overwrites runtime specifications. Use `./setup.sh --sync-only`, `./setup.fish --sync-only`, or `pwsh -File .\setup.ps1 -SyncOnly` to repair the agent entrypoints without reinstalling dependencies or changing user configuration.

The specifications are English-only. Agent replies follow the language of the current conversation unless you request another language. Formal wiki pages still default to English; source excerpts and metadata keep their original language.

## Architecture

```
raw/           user-owned originals (PDFs, notes, web clips). Read-only to the LLM.
wiki/sources/  vault-visible sources: MinerU-converted paper markdown, copied notes and web clips.
wiki/          LLM-maintained pages: papers, concepts, topics, people, ideas, experiments, claims, Summary, foundations, outputs.
wiki/graph/    auto-derived edges, citations, context_brief — never hand-edit.
tools/         Python CLIs (run via uv).
skills/        canonical English skill files; includes shared-references/.
AGENTS.md      Codex runtime rules, maintained directly.
CLAUDE.md      Claude Code runtime rules, maintained directly.
docs/          pipeline docs, runtime references, page templates.
```

`wiki/` renders as an Obsidian vault: internal links use `[[slug]]` wikilinks, and every forward link has a required reverse link (see [Cross-Reference Rules](docs/runtime-support-files.en.md#cross-reference-rules)).

### External content paths

This repository stores skills, tools, configuration, and maintained runtime
documentation. Generated research content lives outside it. Set OS-specific
`wiki_root`, `raw_root`, and `paper_root` in `config/paths.json` (gitignored;
see [`config/README.md`](config/README.md)). `paper_root` stores independent
research topics in stable `<paper-id>/` directories, each containing multiple
`YYYY-MM-DD-<purpose>/` manuscript versions; `wiki_root/papers/` continues
to store literature summaries.

To move an existing in-repository vault out:

```bash
uv run python -X utf8 tools/separate_wiki_repository.py \
  --wiki-root /abs/path/to/wiki \
  --raw-root /abs/path/to/raw \
  --mode copy --yes
```

After verifying the external copy, optionally clean the in-repo `wiki/` and `raw/` directories:

```bash
uv run python -X utf8 tools/clean_wiki_repository.py --target all --yes
```

`active_profile: "auto"` chooses `macos`, `windows`, or `linux` based on the current OS. Override with `LLM_WIKI_PATH_PROFILE`. Graph commands accept `@wiki` to resolve the configured vault:

```bash
uv run python -X utf8 tools/research_wiki.py rebuild-index @wiki
```

## Skills

Choose a skill here, then read its `SKILL.md` and only the references relevant to the current action. Parameters/defaults and write permissions are defined in the skill itself.

| Phase | Skill | Specification | Invocation |
|-------|-------|---------------|------------|
| Setup | `/setup` | [SKILL.md](skills/setup/SKILL.md) | manual (first-time config) |
| Setup | `/reset` | [SKILL.md](skills/reset/SKILL.md) | manual (`--scope wiki\|raw\|log\|checkpoints\|all`) |
| Bootstrap & ingest | `/init` | [SKILL.md](skills/init/SKILL.md) | manual (build from configured local papers, notes, and web clips) |
| Bootstrap & ingest | `/prefill` | [SKILL.md](skills/prefill/SKILL.md) | manual (`[domain] [--add concept]`) |
| Bootstrap & ingest | `/ingest` | [SKILL.md](skills/ingest/SKILL.md) | manual (new Zotero-backed paper, full analysis and linked entities) |
| Bootstrap & ingest | `/ingest-light` | [SKILL.md](skills/ingest-light/SKILL.md) | manual (lightly ingest dissertation-introduction/background papers) |
| Bootstrap & ingest | `/promote-light-ingest` | [SKILL.md](skills/promote-light-ingest/SKILL.md) | manual (rank light-ingested papers for promotion to full ingest) |
| Bootstrap & ingest | `/zotero-collection-list` | [SKILL.md](skills/zotero-collection-list/SKILL.md) | manual (list citationKey, title, and DOI by Zotero collection/subcollection) |
| Bootstrap & ingest | `/ingest-local-pdf` | [SKILL.md](skills/ingest-local-pdf/SKILL.md) | manual (new local PDF/directory or prepared MinerU source, full ingest) |
| Bootstrap & ingest | `/reingest` | [SKILL.md](skills/reingest/SKILL.md) | manual (regenerate an existing paper page) |
| Bootstrap & ingest | `/reingest-force` | [SKILL.md](skills/reingest-force/SKILL.md) | manual (clean-room rebuild of an existing paper page when old wiki state is unreliable) |
| Bootstrap & ingest | `/discover` | [SKILL.md](skills/discover/SKILL.md) | manual / internal (called by `/ingest --discover`) |
| Explore & maintain | `/ask` | [SKILL.md](skills/ask/SKILL.md) | manual (read-only wiki question answering) |
| Explore & maintain | `/edit` | [SKILL.md](skills/edit/SKILL.md) | manual (requested saves and modifications) |
| Explore & maintain | `/code-analyze` | [SKILL.md](skills/code-analyze/SKILL.md) | manual (trace code execution and processing stages; other analysis directions only when requested) |
| Explore & maintain | `/check` | [SKILL.md](skills/check/SKILL.md) | biweekly/manual |
| Explore & maintain | `/source-audit` | [SKILL.md](skills/source-audit/SKILL.md) | manual (audit wiki interpretations against original source text) |
| Explore & maintain | `/novelty` | [SKILL.md](skills/novelty/SKILL.md) | manual |
| Explore & maintain | `/llm-review` | [SKILL.md](skills/llm-review/SKILL.md) | manual |
| Research cycle | `/ideate` | [SKILL.md](skills/ideate/SKILL.md) | manual |
| Research cycle | `/refine` | [SKILL.md](skills/refine/SKILL.md) | manual |
| Produce | `/paper-plan` | [SKILL.md](skills/paper-plan/SKILL.md) | manual |
| Produce | `/paper-draft` | [SKILL.md](skills/paper-draft/SKILL.md) | manual |
| Produce | `/survey` | [SKILL.md](skills/survey/SKILL.md) | manual |
| Produce | `/rebuttal` | [SKILL.md](skills/rebuttal/SKILL.md) | manual |

## Query and edit

`/ask` answers from existing wiki pages with citations and performs no writes, including logs, initialization, or graph rebuilds. Use `/edit` to save an answer or apply requested changes. Missing index/derived files fall back to direct page retrieval during a query. Default `/check` and `/source-audit` runs are read-only; their explicit repair/report modes retain the documented write scope.

## Review workflow

Reviews run in the current agent without an additional model API or reviewer service. Use `/source-audit` to verify ingested pages against canonical sources, and `/llm-review` to critique research artifacts. You can run the same skill in another agent/session for a separate assessment; agent/model switching is user-controlled. See [`review-protocol.md`](skills/shared-references/review-protocol.md) for review provenance and evidence rules.

Calculation and experiment plans are developed through conversation around your actual workflow and manual steps. You carry out calculations/experiments externally; results are assessed through iterative conversation using the data you provide. Findings and supported changes to experiment, claim, and idea pages are recorded when you request wiki updates.

## Source grounding

Generated research content is source-first. The shared rule lives in `skills/shared-references/source-grounding.md`.

- Generated paper pages use `## Evidence Pack` cards from prepared MinerU markdown.
- Concept pages include exact `## Source excerpts`.
- Claim evidence carries source anchors.
- `papers/`, `concepts/`, and `claims/` should pass the scoped grounding gate before a generating skill reports success:

```bash
uv run python -X utf8 tools/grounding_lint.py --wiki-dir @configured --only papers/<slug>.md --json
```

## PDF preprocessing

PDF → MinerU markdown adapter. See [`docs/mineru-pipeline.md`](docs/mineru-pipeline.md) for the full pipeline, cache layout, and adapter passes. Canonical ingest format is `mineru-md`.

- **`/ingest-local-pdf`** — for raw PDFs or directory batches. Prepares `wiki/sources/papers/*.md` and hands off to `/ingest`.
- **`/ingest`** — consumes prepared markdown or resolves a Zotero attachment via `--title` or `--doi`. Scans the selected profile's `zotero_roots` candidates in `config/paths.json`; override with `--zotero-root <Zotero data dir>`. The Zotero helper snapshots `zotero.sqlite` into `config/zotero-cache/` and queries it read-only. If Zotero Desktop's local API is running, metadata (title, DOI, year, venue, creators, abstract, tags, citation key, `bibtex`) is pulled from there and falls back to SQLite + Crossref. Zotero `--item-key` is not a user-facing `/ingest` selector; selected candidates may still use their internal `item_key` for metadata enrichment.
- **`/ingest-light`** — lightweight intake for dissertation-introduction or background papers. Creates a compact paper page, tags it for `thesis-introduction`, and links it to a target Summary without expanding the full concept/claim/people graph.
- **`/promote-light-ingest`** — ranks light-ingested pages that are worth upgrading to full `/ingest` or `/reingest`.
- **`/reingest`** — rerun the adapter and migrate linked entities after the PDF adapter, template, or analysis policy changes. `--paper-only` skips the entity audit.
- **`/code-analyze`** — reconstructs a code repository's execution flow and processing stages with source evidence and LaTeX; other analysis directions apply only when requested. It can archive reports to `wiki/outputs/`.

Metadata-only inputs don't create paper pages on their own — they enrich an existing content source (prepared markdown, note, or web clip).

### Zotero citation keys

PDF ingest expects Zotero items to have a Better BibTeX citation key. This project uses that key as the preferred filename stem for both prepared sources and paper pages:

```text
wiki/sources/papers/<citationKey>.md
wiki/papers/<citationKey>.md
```

The configured Better BibTeX key pattern is:

```text
auth.lower + "_" + year + "_" + veryshorttitle
```

If a Zotero citation key is unavailable, the tools fall back to an equivalent `author_year_veryshorttitle` stem derived from available metadata.

## Python tooling

All Python operations run through `uv` — no manual venv activation:

```bash
uv run python -X utf8 tools/research_wiki.py --help
uv run python -X utf8 tools/lint.py
uv run python -X utf8 tools/prepare_paper_source.py \
  --raw-root @raw-root \
  --output-dir @configured-sources-papers \
  --cache-root @mineru-cache \
  --source raw/papers/<file>.pdf
```

Optional local MinerU backend (downloads several GB of models on first run):

```bash
uv sync --extra local
```

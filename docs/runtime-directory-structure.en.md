# Runtime Directory Chart

> On-demand reference for storage layout and runtime operations. `AGENTS.md` and `CLAUDE.md` keep the essential execution rules; page and support-file schemas live in their dedicated runtime documents.

`wiki/`, `experiment/`, `output/`, `raw/`, and `paper_draft/` below are external roots derived from `[wiki].root_dir` and enabled booleans, exposed internally as
`wiki_root`, `experiment_root`, `output_root`, `raw_root`, and `paper_root`. Generated research content does not
belong in the code repository; tools, skills, maintained docs, and templates do.

```text
wiki/
├── index.md           ← content catalog (YAML)
├── log/               ← weekly skill-grouped activity logs
│   └── yyyy-mm-wN.md
├── papers/            ← structured paper summaries
├── concepts/          ← cross-paper technical concepts
├── topics/            ← research direction maps
├── people/            ← researcher profiles
├── ideas/             ← research ideas (with lifecycle status)
├── claims/            ← testable research claims
├── Summary/           ← domain-wide surveys
├── foundations/       ← background knowledge (terminal: receives inward links, writes none)
├── sources/           ← vault-visible source markdown, notes, and web clips
│   ├── papers/        ← MinerU-generated markdown; source PDFs stay in raw/papers/
│   ├── notes/         ← copied markdown/text notes from raw/notes/
│   └── web/           ← copied markdown/text web clips from raw/web/
└── graph/             ← auto-generated (do not edit)
    ├── edges.jsonl
    ├── citations.jsonl
    ├── context_brief.md
    └── open_questions.md

experiment/            ← experiment_root; experiment entities and supporting records
output/                ← output_root; reports, saved answers, and paper plans

raw/
├── papers/            ← user-owned source PDFs and other original paper files
├── notes/             ← user-owned .md notes
└── web/               ← user-owned HTML / Markdown

paper_draft/           ← paper_root; author manuscripts, not wiki literature summaries
├── rmcdhf-radial-research/  ← stable, undated research topic
│   ├── 2026-10-06-rmcdhf-research/
│   │   ├── paper.tex      ← or a split-file main.tex
│   │   ├── draft.json     ← version identity and optional parent version
│   │   ├── figures/
│   │   ├── evidence/      ← reports, data, source manifests, reproduction scripts
│   │   ├── reviews/
│   │   └── history/
│   └── 2026-10-06-structure-v2/  ← independent alternative and evaluations
└── another-research-topic/
    └── 2026-10-06-initial-draft/

tools/                 ← Python tooling (run via uv)
├── _mineru.py         ← MinerU client (api + local backends)
├── prepare_paper_source.py  ← PDF → MinerU markdown adapter
├── research_wiki.py   ← graph CLI (add-edge, add-citation, rebuilds)
├── lint.py            ← link / field health checks
├── paper_workspace.py ← create/resolve/fork/list topic-specific draft versions
└── …                  ← discover, init, fetch_*, reset_wiki

config/
├── .env.example       ← template for ~/.config/llm-wiki/.env
├── paths.toml.example ← machine-local [wiki] and [zotero] configuration
└── settings.local.json.example

AGENTS.md              ← maintained Codex runtime rules
CLAUDE.md              ← maintained Claude Code runtime rules
skills/                ← canonical English skills; both agent entrypoints point here
├── shared-references/ ← shared policies and ingest phases
└── <skill>/SKILL.md    ← skill entrypoint and optional local resources
docs/                  ← long-form runtime references (this file lives here)
└── templates/         ← copy/edit page starter templates
```

## Fast Reminders

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned original inputs.
- `wiki/sources/` is the vault-visible source layer: converted paper markdown, copied notes, and copied web clips.
- Source PDFs stay outside the knowledge directory in `raw/papers/`; only their MinerU markdown goes under `wiki/sources/papers/`.
- `config/paths.toml` contains `[wiki]` (`root_dir` plus directory booleans) and `[zotero]` (`profile_dir`, `data_dir`). It is machine-local and ignored by git. Knowledge uses `root_dir/wiki`; enabled keys use `root_dir/<key>`. Manuscripts use `paper_draft = true` and have no in-repository fallback.
- `@paper-root/<paper-id>/<draft-id>/` selects a version under a stable research topic. Routine revisions keep that directory; major structural changes or independent evaluations fork a sibling draft, preserving the original and recording its parent.
- `docs/templates/` is the maintained template library; do not keep a root-level `templates/` directory.
- `graph/` is derived and should be maintained only through `tools/research_wiki.py`.
- All Python tools run via `uv run python -X utf8 tools/<tool>.py …` (no manual venv activation needed).

## External Path Resolution

- Path configuration uses `config/paths.toml` (or `LLM_WIKI_WIKI_ROOT`, `LLM_WIKI_EXPERIMENT_ROOT`, `LLM_WIKI_OUTPUT_ROOT`, `LLM_WIKI_RAW_ROOT`, `LLM_WIKI_PAPER_ROOT`) for external `wiki_root`, `experiment_root`, `output_root`, `raw_root`, and `paper_root`; TOML uses explicit local paths without OS/profile selection. `resolve_path_alias.py` strictly validates each requested content root: missing configuration and roots inside or containing the code repository are errors. Validate the aliases needed by the task before content reads/writes, including tool writes; an unused raw/manuscript root is not required. Roots may be absent on disk before initialization. Legacy low-level wiki/raw defaults remain for migration tools and test fixtures, not skill content operations.
- `@configured`, `@experiment-root`, `@output-root`, `@raw-root`, `@paper-root`, `@configured-sources-papers`, and alias-relative paths such as `@paper-root/<paper-id>/<draft-id>/paper.tex` are resolved only by Python tools supporting `tools/_paths.py`. For direct file operations, first run `uv run python -X utf8 tools/resolve_path_alias.py ...` and use the returned absolute paths; never create literal alias directories. `tools/paper_workspace.py create|resolve|fork|list` manages topics and draft versions; create/fork refuse existing destinations.

See `config/README.md` for TOML examples and manuscript workspace commands. `paper_root` is separate from wiki/raw storage; create/fork refuse existing destinations, and inherited evidence is not a newly executed experiment.

## Independent Experiments and Outputs

Enable `experiment = true` and `output = true` in `[wiki]` to derive
`experiment_root = root_dir/experiment` and `output_root = root_dir/output`. Each must be outside the repository and disjoint from every other
content root. Disabled or omitted switches have no fallback. Reading config is read-only;
`resolve_path_alias.py --create-dirs` explicitly creates all enabled directories.
Custom keys such as `beamer = true` resolve through `@directory/beamer`. Resolve
`@experiment-root` and `@output-root` before accessing them; an unused root does
not block a wiki-only operation. Retired `@configured/experiments/...` and
`@configured/outputs/...` aliases fail with a migration hint.

`tools/_content.py` maps logical `experiments/<slug>` identities to the configured
experiment root. Graph edges and claim/idea provenance retain those identities.
Index, evidence queries, context compilation, lint, lifecycle, reset, and source
rename maintenance use that mapping. Outputs are indexed documents; existing `outputs/<slug>` provenance edges
remain valid, without treating report prose as new claim evidence. `wiki/index.md` records relative paths to both independent
roots. Flat entity pages remain at the experiment root; supporting files may
live below it. Existing standalone legacy trees can be passed explicitly to
low-level tools for migration/testing; they never borrow another vault's roots.

A move requires copying and checking every file, rebasing both incoming and
outgoing relative links, updating root configuration and the index, and checking
graph endpoints before removing the originals. Keep a recovery archive outside
the active content trees; no symlink or redirect-page compatibility layer is
needed. `reset --scope wiki` retains its logical scope, including experiment and
output pages in their configured roots; its dry-run lists their actual paths.

## Python Environment and Backends

- Python tools load API keys through `tools/_env.py`: first process environment, then `~/.config/llm-wiki/.env` (or `$XDG_CONFIG_HOME/llm-wiki/.env`); project-root `.env` and `~/.env` are legacy fallbacks only
- To enable local MinerU preprocessing, run `uv sync --extra local` and set `MINERU_BACKEND=local` in the llm-wiki `.env`.
- The default `api` backend requires `MINERU_API_TOKEN`.

Use the invocation policy in the active runtime entrypoint. `setup.sh` manages dependencies from `pyproject.toml` with `uv sync`. Repository tests live in `tests/`; inspect relevant tests when changing code. `tools/lint.py` validates wiki content.

## Source Preparation and Handoff

- **`raw/papers/`, `raw/notes/`, `raw/web/` are user-owned**: treat them as authoritative inputs. `/init` and `/ingest-local-pdf` may add vault-visible source copies under `wiki/sources/`: PDFs must be converted to `wiki/sources/papers/*.md` and never copied into `wiki/`; notes/web may be copied to `wiki/sources/notes/` and `wiki/sources/web/`. `/edit` may add or delete explicitly requested raw-source targets; it must not rewrite existing raw contents. `/init` hands prepared papers to `/ingest` sequentially; raw inputs remain strictly read-only during source preparation/ingest, and each handed-off canonical path is consumed directly.
- **`/init` handoff is manifest-driven**: when `/init` writes `.checkpoints/init-sources.json`, that manifest becomes the single source of truth for ingest order and canonical source paths. Prepared local inputs should point to `wiki/sources/papers/<slug>.md` (MinerU output).
- **mineru-md is the canonical ingest format**: PDFs are preprocessed by MinerU (`tools/_mineru.py`) into structured markdown with frontmatter (`sections`, `figures`). `/ingest-local-pdf` and `/init` produce/consume the prepared `wiki/sources/papers/<slug>.md`; `/ingest` only consumes already prepared `wiki/sources/papers/<slug>.md`, the canonical path handed off by `/init`, or Zotero-located paper sources — never the raw PDF directly.

## Zotero and Literature Lookup

- **Zotero integration**: `tools/find_zotero_pdf.py`, `tools/fetch_zotero_metadata.py`, and `tools/_zotero_snapshot.py` look up PDFs by `--title` or `--doi`, then use the selected candidate's internal `item_key` to read parent-item metadata. `--item-key` is not a user-facing paper selector for `/ingest` or `/reingest`. Zotero roots are configured via explicit `[zotero].data_dir` and `profile_dir` in `config/paths.toml` or `--zotero-root`. `/ingest` can use this to auto-locate Zotero attachments and derive plain BibTeX from Zotero metadata; BibTeX is written to the body `## BibTeX` fenced code block, not YAML frontmatter. Raw local PDFs belong to `/ingest-local-pdf`.
- **Literature lookup**: `tools/fetch_literature.py` uses no-key Crossref search and metadata. Citation graph coverage is best-effort because public sources expose fewer citation edges than key-gated services.

## Repository Migration and Cleanup

- **Repository and wiki can be separated**: use `tools/separate_wiki_repository.py` to copy/move `wiki/` and `raw/` to external absolute paths and write `config/paths.toml`; use `tools/clean_wiki_repository.py` to remove leftover in-repo `wiki/` and `raw/`. Cleanup is dry-run by default and deletes only with `--yes`.

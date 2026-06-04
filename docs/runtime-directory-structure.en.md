# Runtime Directory Chart

> On-demand reference for the repo layout. The main `CLAUDE.md` keeps only the schema and rules that should stay in immediate context.

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
├── experiments/       ← experiment records (wiki pages)
├── claims/            ← testable research claims
├── Summary/           ← domain-wide surveys
├── foundations/       ← background knowledge (terminal: receives inward links, writes none)
├── outputs/           ← generated artifacts (Related Work, paper drafts)
├── sources/           ← vault-visible source markdown, notes, and web clips
│   ├── papers/        ← MinerU-generated markdown; source PDFs stay in raw/papers/
│   ├── notes/         ← copied markdown/text notes from raw/notes/
│   └── web/           ← copied markdown/text web clips from raw/web/
└── graph/             ← auto-generated (do not edit)
    ├── edges.jsonl
    ├── citations.jsonl
    ├── context_brief.md
    └── open_questions.md

raw/
├── papers/            ← user-owned source PDFs and other original paper files
├── notes/             ← user-owned .md notes
└── web/               ← user-owned HTML / Markdown

tools/                 ← Python tooling (run via uv)
├── _mineru.py         ← MinerU client (api + local backends)
├── prepare_paper_source.py  ← PDF → MinerU markdown adapter
├── research_wiki.py   ← graph CLI (add-edge, add-citation, rebuilds)
├── lint.py            ← link / field health checks
└── …                  ← discover, init, fetch_*, reset_wiki

mcp-servers/
└── llm-review/        ← optional Review LLM cross-model server

config/
├── .env.example       ← template for ~/.config/llm-wiki/.env
├── paths.json.example ← template for cross-platform wiki/raw path config
├── zotero-roots.json  ← Zotero data/profile directory candidates
└── settings.local.json.example

i18n/en/               ← canonical English skills + shared references
skills/                ← canonical skills; `.claude/skills` and `.agents/skills` point here
docs/                  ← long-form runtime references (this file lives here)
└── templates/         ← copy/edit page starter templates
```

## Fast Reminders

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned original inputs.
- `wiki/sources/` is the vault-visible source layer: converted paper markdown, copied notes, and copied web clips.
- Source PDFs stay outside the vault in `raw/papers/`; only their MinerU markdown goes under `wiki/sources/papers/`.
- `config/paths.json` may point `wiki_root` and `raw_root` to OS-specific external directories via `profiles.macos/windows/linux`; it is machine-local and ignored by git.
- `docs/templates/` is the maintained template library; do not keep a root-level `templates/` directory.
- `graph/` is derived and should be maintained only through `tools/research_wiki.py`.
- All Python tools run via `uv run python -X utf8 tools/<tool>.py …` (no manual venv activation needed).

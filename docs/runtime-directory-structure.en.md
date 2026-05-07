# Runtime Directory Chart

> On-demand reference for the repo layout. The main `CLAUDE.md` keeps only the schema and rules that should stay in immediate context.

```text
wiki/
├── index.md           ← content catalog (YAML)
├── log.md             ← chronological log (append-only)
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
└── graph/             ← auto-generated (do not edit)
    ├── edges.jsonl
    ├── citations.jsonl
    ├── context_brief.md
    └── open_questions.md

raw/
├── papers/            ← user-owned .tex / .pdf sources
├── tmp/papers/        ← MinerU-generated prepared markdown for /init and direct local /ingest
├── notes/             ← user-owned .md notes
└── web/               ← user-owned HTML / Markdown

tools/                 ← Python tooling (run via uv)
├── _mineru.py         ← MinerU client (api + local backends)
├── prepare_paper_source.py  ← PDF → MinerU markdown adapter
├── research_wiki.py   ← graph CLI (add-edge, add-citation, rebuilds)
├── lint.py            ← link / field health checks
└── …                  ← discover, init, fetch_*, reset_wiki

omega/
├── tools/remote.py    ← optional remote experiment helper (moved out of main wiki path)
└── config/server.yaml.example ← optional remote GPU config template
└── mcp-servers/llm-review/ ← Review LLM cross-model server

config/
├── server.yaml        ← remote GPU server config (optional)
├── server.yaml.example
├── .env.example       ← template for ~/.config/llm-wiki/.env
└── settings.local.json.example

i18n/en/               ← canonical English skills + shared references
skills/                ← canonical skills; `.claude/skills` and `.agents/skills` point here
docs/                  ← long-form runtime references (this file lives here)
```

## Fast Reminders

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs.
- `raw/tmp/papers/` holds MinerU-generated prepared markdown (`<slug>.md` + `assets/<slug>/*`).
- `graph/` is derived and should be maintained only through `tools/research_wiki.py`.
- All Python tools run via `uv run python tools/<tool>.py …` (no manual venv activation needed).

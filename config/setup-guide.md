# llm-wiki — Configuration Guide

> This file is read by the `/setup` skill to guide users through API key configuration.
> It describes each key: what it does, which skills use it, how to get it,
> and what happens when it is not set.

---

## How Configuration Works

All llm-wiki API keys live in the user config file `~/.config/llm-wiki/.env`
(or `$XDG_CONFIG_HOME/llm-wiki/.env` when `XDG_CONFIG_HOME` is set). `setup.sh`
creates this file from `config/.env.example`.

Python tools load this file automatically on startup via `tools/_env.py` — no manual
`export` needed. Real environment variables still take precedence over file values.

The `/setup` skill checks which keys are currently set, explains each one, and writes values
directly into the user config file using available file-editing tools.

---

## Key 1: MinerU API Token

| Field | Value |
|-------|-------|
| Config variable | `MINERU_API_TOKEN` in `~/.config/llm-wiki/.env` or `$XDG_CONFIG_HOME/llm-wiki/.env` |
| Required? | **Yes** for any PDF ingest path |
| Free? | Yes (free tier on mineru.net) |

**What it does**: MinerU is a vision-language PDF parser that extracts text + figure crops
with section structure. `tools/prepare_paper_source.py` calls it to turn raw PDFs into the
structured markdown that `/ingest` consumes.

**Which skills use it**:
- `/ingest` — every PDF source goes through MinerU before downstream extraction
- `/init` — bulk PDF preparation routes through the same prep tool

**Without this token**: PDF ingest fails. The escape hatch is the local MinerU backend
(`uv sync --extra local`), which downloads several GB of models on first use and runs
fully on-device — no token required, but heavy.

**How to get it**:
1. Go to https://mineru.net/
2. Sign up (free)
3. Create an API token in your account settings
4. Paste the token into `MINERU_API_TOKEN` in llm-wiki's `.env`

**Optional override**: `MINERU_API_BASE` lets you point at a non-default API host (rarely
needed). Leave commented unless MinerU publishes a new endpoint.

**Format**: Bearer token string (alphanumeric).

---

## Review Workflow

Reviews run in the current agent and require no additional API key or reviewer service. `/source-audit` checks ingested pages against their canonical prepared sources; `/llm-review` critiques research artifacts. The user can select another agent/model and run the same skill there when a separate assessment is wanted.

Follow `skills/shared-references/review-protocol.md` for provenance and evidence requirements. A self-review remains a self-review; agreement between reports alone does not raise claim confidence. Existing unrelated values in the user's config file are preserved.

---

## Configuration Verification

After setting keys, verify they are loaded correctly (uv-based, no venv activation needed):

```bash
uv run python -X utf8 -c "
import sys; sys.path.insert(0, 'tools')
import _env, os
keys = ['MINERU_API_TOKEN']
for k in keys:
    v = os.environ.get(k, '')
    status = '✓ set' if v else '✗ not set'
    print(f'{status}  {k}')
"
```

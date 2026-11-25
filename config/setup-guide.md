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
| Required? | For the `api` backend |
| Free? | Yes (free tier on mineru.net) |

**What it does**: MinerU is a vision-language PDF parser that extracts text + figure crops
with section structure. `tools/prepare_paper_source.py` calls it to turn raw PDFs into the
structured markdown that `/ingest` consumes.

**Which skills use it**:
- `/ingest` — every PDF source goes through MinerU before downstream extraction
- `/init` — bulk PDF preparation routes through the same prep tool

Local parsing uses the MinerU 4 SDK installed with `uv sync --extra local`.
MinerU may download model weights on first use.

**How to get it**:
1. Go to https://mineru.net/
2. Sign up (free)
3. Create an API token in your account settings
4. Paste the token into `MINERU_API_TOKEN` in llm-wiki's `.env`

**Optional override**: `MINERU_API_BASE` lets you point at a non-default API host (rarely
needed). Leave commented unless MinerU publishes a new endpoint.

**Format**: Bearer token string (alphanumeric).

### Select the MinerU backend

Set `MINERU_BACKEND=local` or `MINERU_BACKEND=api` in the same `.env` file.
Single-PDF preparation, Zotero ingest, and `/init` all read this setting.
If omitted, the default is `api`.

```bash
uv run python -X utf8 tools/prepare_paper_source.py --show-backend
```

The command reports the selected backend and installed MinerU package version
without processing a PDF. Actual preparation reports if it parsed the PDF or
reused extraction data from its cache.

---

## Review Workflow

`/source-audit` checks ingested pages against their canonical prepared sources and `/llm-review` critiques research artifacts in the current agent. The user can select another agent/model and run the same skill there for a separate assessment.

Follow `skills/shared-references/review-protocol.md` for provenance and evidence requirements. A self-review remains a self-review; agreement between reports alone does not raise claim confidence. Existing unrelated values in the user's config file are preserved.

### Optional API review

Set `LLM_BASE_URL` to your provider's OpenAI-compatible API base (typically ending in `/v1`), `LLM_MODEL` to the model ID, and `LLM_API_KEY` if the provider requires bearer authentication. Add these values to your existing llm-wiki `.env` or export them in your shell. The tool accepts HTTPS or a loopback HTTP endpoint.

`/api-review` sends the full artifact and selected wiki excerpts to that endpoint. Preview the file list and excerpt sizes locally with `--dry-run`.

```bash
uv run python -X utf8 tools/api_review.py claims/example-claim --context papers/example-paper --dry-run
```

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

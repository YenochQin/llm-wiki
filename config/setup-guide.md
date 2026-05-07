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
`export` needed. The Review LLM MCP server reads the same file on startup. Real
environment variables still take precedence over file values.

The `/setup` skill checks which keys are currently set, explains each one, and writes values
directly into the user config file using the Edit tool.

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

## Key 2: Review LLM (three variables)

| Field | Value |
|-------|-------|
| Config variables | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` |
| Required? | No (optional) |
| Free? | Depends on provider |

**What it does**: Connects llm-wiki to a second LLM (independent of Claude) for
adversarial cross-model review. The reviewer independently critiques research artifacts
without seeing Claude's prior analysis, improving review quality.

**Which skills use it**:
- `/review` — general-purpose cross-model review
- `/novelty` — second-opinion on novelty assessment
- `/ideate` — dual-model brainstorm + independent filter
- `/exp-eval` — verdict gate on experiment results
- `/exp-design` — review experiment plan
- `/paper-plan` — review paper outline (mandatory gate)
- `/paper-draft` — review each section
- `/rebuttal` — stress-test rebuttal responses
- `/refine` — review in multi-round improve cycle

**Without these keys**: Skills skip the cross-model review step and proceed with
Claude-only analysis. Everything still works, but you lose the independent second-opinion.
The `/review` skill will note that cross-model review is unavailable.

**Works with any OpenAI-compatible API**:

| Provider | LLM_BASE_URL | Example LLM_MODEL |
|----------|-------------|-------------------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| OpenRouter | `https://openrouter.ai/api/v1` | any model slug |
| Qwen (DashScope) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-max` |
| SiliconFlow | `https://api.siliconflow.cn/v1` | see their docs |
| Local (Ollama) | `http://localhost:11434/v1` | `llama3.2` |

**How to set up**:
1. Choose a provider and get an API key from them
2. Note the base URL and model name from the table above
3. Set all three variables in the llm-wiki user config file
4. Restart Claude Code (the MCP server re-reads the config file on startup)

**Optional**: `LLM_FALLBACK_MODEL` — fallback model if the primary fails (defaults to `LLM_MODEL`)

**Reviewer independence principle** (from `shared-references/cross-model-review.md`):
Never share Claude's analysis with the Review LLM before it gives its independent assessment.
The value of cross-model review comes from genuine independence.

---

## Configuration Verification

After setting keys, verify they are loaded correctly (uv-based, no venv activation needed):

```bash
uv run --python .venv/bin/python python -c "
import sys; sys.path.insert(0, 'tools')
import _env, os
keys = ['MINERU_API_TOKEN', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for k in keys:
    v = os.environ.get(k, '')
    status = '✓ set' if v else '✗ not set'
    print(f'{status}  {k}')
"
```

After adding `LLM_*` variables, restart Claude Code so the MCP server picks them up.

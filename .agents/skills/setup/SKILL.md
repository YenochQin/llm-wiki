---
description: Interactive API key configuration guide — checks current .env and MinerU config state, then walks you through MinerU, Semantic Scholar, and Review LLM setup
---

# /setup

> Guides you through llm-wiki's API key configuration.
> Reads your current `.env` plus MinerU user config, shows what is and isn't configured, and helps you
> set up each key with clear explanations of what it does and how to get it.
> Safe to re-run at any time — only updates keys you choose to configure.

## Inputs

- No arguments required
- Reads: `.env` (current project configuration state)
- Reads: `~/.config/MinerU/mineru.env` or `$XDG_CONFIG_HOME/MinerU/mineru.env` (MinerU cloud API token)
- Reads: `config/setup-guide.md` (reference for what each key does)

## Outputs

- Updated MinerU `mineru.env` with the MinerU token, if configured
- Updated `.env` with any newly configured non-MinerU keys
- A summary of current configuration status

## Wiki Interaction

### Reads
- None (setup runs before any wiki exists)

### Writes
- None (does not touch the wiki)

## Workflow

### Step 1: Read Configuration Reference

Read `config/setup-guide.md` to load the complete reference for all configurable keys,
including what each does, which skills use it, how to get it, and fallback behavior.

### Step 2: Detect Current Environment

Run the following to check what is already configured (uv-based, no manual venv activation):

```bash
uv run --python .venv/bin/python python -c "
import sys, os
from pathlib import Path
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
mineru_env = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'MinerU' / 'mineru.env'
if mineru_env.exists():
    for line in mineru_env.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('\"').strip(\"'\"))
keys = {
    'MINERU_API_TOKEN':         'MinerU API token',
    'SEMANTIC_SCHOLAR_API_KEY': 'Semantic Scholar',
    'LLM_API_KEY':              'Review LLM (API key)',
    'LLM_BASE_URL':             'Review LLM (base URL)',
    'LLM_MODEL':                'Review LLM (model)',
}
for k, label in keys.items():
    v = os.environ.get(k, '').strip()
    print(f'SET:{k}' if v else f'UNSET:{k}')
"
```

Also detect the Python environment and `.venv` status:
```bash
ls .venv/ 2>/dev/null && echo "venv:present" || echo "venv:absent"
uv --version
```

### Step 3: Show Configuration Status

Present a clear summary to the user, grouped by status:

```
llm-wiki Configuration Status
================================
✓  ANTHROPIC_API_KEY      — managed by Codex (Codex login)

Required for PDF ingest:
✗  MinerU API token       — not set  (PDF ingest will fail — get free token)

Recommended:
✗  Semantic Scholar        — not set  (citation expansion 3x slower — get free key)

Optional:
✗  Review LLM              — not set  (cross-model review unavailable)
```

Ask the user: "Which would you like to configure? (You can skip any or all.)"

### Step 4: Configure Each Key (user-directed)

For each key the user wants to configure, follow the specific sub-flow below.
Always ask for user confirmation before writing to `.env`.

---

#### 4a: MinerU API Token (required for PDF ingest)

**Explain**: "MinerU is a vision-language PDF parser. `tools/prepare_paper_source.py`
calls it to turn raw PDFs into structured markdown that /ingest consumes. Without it,
PDF ingest fails. Free tier is generous; sign up at https://mineru.net/."

**Guide to get it**:
1. Go to https://mineru.net/
2. Sign up (free)
3. Create an API token in account settings
4. Copy the token

**Ask**: "Do you have a MinerU API token? (paste it, or 'skip')"

**If provided**, write to MinerU's user config file:
- Resolve the path as `$XDG_CONFIG_HOME/MinerU/mineru.env` when `XDG_CONFIG_HOME` is set, otherwise `~/.config/MinerU/mineru.env`
- Create the `MinerU` directory if needed
- If `MINERU_API_TOKEN=` line exists (even empty), replace it
- Otherwise append `MINERU_API_TOKEN=<value>`
- Do not write the MinerU token to project `.env` unless the user explicitly asks for an additional environment export

**Local-backend escape hatch**: If the user explicitly wants offline-only operation,
mention that the local MinerU backend can be installed with
`uv pip install -e ".[local]"` (downloads several GB of models on first use).
No token is required for the local backend.

---

#### 4b: Semantic Scholar API Key

**Explain**: "Semantic Scholar gives citation data and paper search.
Used by /ingest, /init, /novelty, /ideate. Free to get.
**Recommended** — without it, /init runs 3x slower and citation-chain expansion is much less effective."

**Guide to get it**: "Go to https://www.semanticscholar.org/product/api and click 'Get API Key'. It's free."

**Ask**: "Do you have a Semantic Scholar API key? (paste it, or 'skip')"

**If provided**, write to `.env`:
```python
# Read current .env, update or append SEMANTIC_SCHOLAR_API_KEY=<value>
```
Use the Edit tool to update `.env`:
- If `SEMANTIC_SCHOLAR_API_KEY=` line exists (even empty), replace it
- Otherwise append `SEMANTIC_SCHOLAR_API_KEY=<value>`

---

#### 4c: Review LLM

**Explain**: "The Review LLM connects llm-wiki to a second AI model for independent
adversarial review. It's used by /review, /novelty, /ideate, /paper-plan, /paper-draft,
/rebuttal, /refine, /exp-eval, and /exp-design. Works with any OpenAI-compatible API.
Without it, those skills skip the cross-model review step (everything still works)."

**Present the provider table** from `config/setup-guide.md` (Key 3 section).

**Clarify what 'OpenAI-compatible' means** if the user asks: any API that accepts
`POST /chat/completions` with `{"model": "...", "messages": [...]}` in the OpenAI format.

**Ask for**:
1. `LLM_BASE_URL` — e.g. `https://api.deepseek.com/v1`
2. `LLM_API_KEY` — their API key for that provider
3. `LLM_MODEL` — model name, e.g. `deepseek-chat`

**Validate format**: Base URL should start with `http://` or `https://` and end with `/v1`
(or similar path). If it looks wrong, ask for confirmation before writing.

**Write all three** to `.env` once the user confirms.

**After writing**: Remind the user that the Review LLM MCP server starts when Codex
launches and reads `.env` at that time — changes take effect after restarting Codex.

---

#### 4d: arXiv Categories (only if user asks)

This key has a sensible default (`cs.LG,cs.CV,cs.CL,cs.AI,stat.ML`). Only configure
it if the user explicitly asks, or if their research area is clearly outside ML/AI.

---

### Step 5: Verify Configuration

After the user finishes configuring, run the verification check from `config/setup-guide.md`:

```bash
uv run --python .venv/bin/python python -c "
import sys, os
from pathlib import Path
sys.path.insert(0, 'tools')
try:
    import _env
except Exception:
    pass
mineru_env = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'MinerU' / 'mineru.env'
if mineru_env.exists():
    for line in mineru_env.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip('\"').strip(\"'\"))
keys = ['MINERU_API_TOKEN', 'SEMANTIC_SCHOLAR_API_KEY', 'LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL']
for k in keys:
    v = os.environ.get(k, '').strip()
    print(f'SET   {k}' if v else f'UNSET {k}')
"
```

Show a final summary. For any keys still not set, briefly note what they unlock
and that the user can run `/setup` again anytime to add them.

### Step 6: Next Steps

If this is a fresh install (no `wiki/` directory):
```
Configuration done. Next:
  • Put your own papers in raw/papers/ (.pdf — MinerU will convert to mineru-md)
  • Optional: add intent notes to raw/notes/ and saved pages to raw/web/
  • /init and direct local /ingest will manage generated inputs under raw/discovered/ and raw/tmp/
  • Run: /init [your-research-topic]
```

If `wiki/` already exists:
```
Configuration updated. Restart Codex for Review LLM changes to take effect.
```

## Constraints

- **Never overwrite existing non-empty values** without asking the user first
- **Never expose the full key value** in output — show only the first 8 characters + `...`
- **Write MinerU only to MinerU config** — write `MINERU_API_TOKEN` to `~/.config/MinerU/mineru.env` or `$XDG_CONFIG_HOME/MinerU/mineru.env`
- **Write non-MinerU keys only to `.env`** — never to `~/.env`
- **No wiki reads or writes** — this skill runs before the wiki may exist
- **Skip gracefully**: if the user says "skip all", show the status summary and exit cleanly

## Error Handling

- **`.env` not found**: Inform the user that `setup.sh` was not run yet. Offer to create `.env` from `.env.example`:
  ```bash
  cp config/.env.example .env
  ```
  Then continue with configuration.

- **`config/setup-guide.md` not found**: Proceed using the information in this SKILL.md directly.

- **MinerU connectivity fails** (network error, 4xx/5xx): Tell the user the token format
  looks fine but the API call failed; suggest testing with `curl -H "Authorization: Bearer <token>" https://mineru.net/api/v4/...`
  or installing the local backend (`uv pip install -e ".[local]"`) as an offline escape hatch.

- **Python environment issue** (`tools/_env.py` not found): Note that `.venv` may not be present,
  but still read `.env` directly using shell or Python file I/O to check current state.

## Dependencies

### Tools (via Bash)
- `uv run --python .venv/bin/python python -c "import _env; ..."` — read current `.env` state

### Files Read
- `config/setup-guide.md` — complete reference for all configurable keys
- `.env` — current non-MinerU project configuration (read + write)
- `~/.config/MinerU/mineru.env` or `$XDG_CONFIG_HOME/MinerU/mineru.env` — MinerU token configuration (read + write)

### Files Written
- `.env` — updated with newly configured non-MinerU keys (via Edit tool)
- MinerU user config — updated with `MINERU_API_TOKEN` when provided

### No MCP servers, no wiki, no external skills called

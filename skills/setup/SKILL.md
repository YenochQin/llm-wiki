---
name: setup
description: Use when configuring the MinerU API token for llm-wiki, checking whether it is set, or updating the chosen key in the user configuration.
---

# /setup

> Guides you through llm-wiki's API key configuration.
> Reads your current `~/.config/llm-wiki/.env`, shows what is and isn't configured, and helps you
> set up each key with clear explanations of what it does and how to get it.
> Safe to re-run at any time — only updates keys you choose to configure.

## Inputs

- No arguments required
- Reads: `~/.config/llm-wiki/.env` or `$XDG_CONFIG_HOME/llm-wiki/.env` (current API key state)
- Reads: `config/setup-guide.md` (reference for what each key does)

## Outputs

- Updated llm-wiki user config `.env` with any newly configured keys
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

Use the **Configuration Verification** command in `config/setup-guide.md` to report which supported keys are set. Run it through the current project environment; report status only, never full values. Agent authentication belongs to the selected application and is not verified by the presence of a MinerU token.

Also detect the Python environment and `.venv` status:
```shell
uv run python -X utf8 -c "from pathlib import Path; print('venv:present' if Path('.venv').exists() else 'venv:absent')"
uv --version
```

### Step 3: Show Configuration Status

Present a clear summary to the user, grouped by status:

```
llm-wiki Configuration Status
================================
✓  Agent authentication   — managed by the selected agent application

Required for PDF ingest:
✗  MinerU API token       — not set  (PDF ingest will fail — get free token)

Review:
✓  Current agent          — no additional API key required
```

Ask the user: "Which would you like to configure? (You can skip any or all.)"

### Step 4: Configure Each Key (user-directed)

For each key the user wants to configure, follow the specific sub-flow below.
Always ask for user confirmation before writing to the llm-wiki user config file.

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

**If provided**, write to llm-wiki's user config file:
- Resolve the path as `$XDG_CONFIG_HOME/llm-wiki/.env` when `XDG_CONFIG_HOME` is set, otherwise `~/.config/llm-wiki/.env`
- Create the `llm-wiki` directory if needed
- If `MINERU_API_TOKEN=` line exists (even empty), replace it
- Otherwise append `MINERU_API_TOKEN=<value>`

**Local-backend escape hatch**: If the user explicitly wants offline-only operation,
mention that the local MinerU backend can be installed with
`uv sync --extra local` (downloads several GB of models on first use).
No token is required for the local backend.

---

#### 4b: Review Workflow (no API key)

Reviews run in the current agent. No additional model API key or reviewer service is required. The user can run `/source-audit` in another agent/session to verify ingested pages against their canonical sources, or `/llm-review` to critique research artifacts. Agent/model selection is user-controlled; do not prompt for reviewer credentials or switch agents automatically.

### Step 5: Verify Configuration

After the user finishes configuring, rerun the **Configuration Verification** command from `config/setup-guide.md`. This checks effective key loading, not successful API connectivity.

Show a final summary. For any keys still not set, briefly note what they unlock
and that the user can run `/setup` again anytime to add them.

### Step 6: Next Steps

If this is a fresh install (no `wiki/` directory):
```
Configuration done. Next:
  • Put your own papers in raw/papers/ (.pdf — MinerU will convert to mineru-md)
  • Optional: add intent notes to raw/notes/ and saved pages to raw/web/
  • /init copies notes/web and writes converted paper markdown under wiki/sources/
  • Run: /init
```

If `wiki/` already exists:
```
Configuration updated. Reviews run in the current agent without additional setup.
```

## Constraints

- **Never overwrite existing non-empty values** without asking the user first
- **Never expose the full key value** in output — show only the first 8 characters + `...`
- **Write all keys only to llm-wiki user config** — `~/.config/llm-wiki/.env` or `$XDG_CONFIG_HOME/llm-wiki/.env`
- **Never write keys to project `.env` or `~/.env`** unless the user explicitly asks for a compatibility export
- **No wiki reads or writes** — this skill runs before the wiki may exist
- **Skip gracefully**: if the user says "skip all", show the status summary and exit cleanly

## Error Handling

- **User config `.env` not found**: Inform the user that `setup.sh` was not run yet. Offer to create it from `config/.env.example`:
  ```shell
  mkdir -p ~/.config/llm-wiki
  cp config/.env.example ~/.config/llm-wiki/.env
  chmod 600 ~/.config/llm-wiki/.env
  ```
  Then continue with configuration.

- **`config/setup-guide.md` not found**: Proceed using the information in this SKILL.md directly.

- **MinerU connectivity fails** (network error, 4xx/5xx): Tell the user the token format
  looks fine but the API call failed; suggest testing with `curl -H "Authorization: Bearer <token>" https://mineru.net/api/v4/...`
  or installing the local backend (`uv sync --extra local`) as an offline escape hatch.

- **Python environment issue** (`tools/_env.py` not found): Note that `.venv` may not be present,
  but still read the user config file directly using shell or Python file I/O to check current state.

## Dependencies

### Tools
- `uv run python -X utf8` with the verification command in `config/setup-guide.md` — read effective key status

### Files Read
- `config/setup-guide.md` — complete reference for all configurable keys
- `~/.config/llm-wiki/.env` or `$XDG_CONFIG_HOME/llm-wiki/.env` — API key configuration (read + write)

### Files Written
- llm-wiki user config `.env` — updated with newly configured keys through available file-editing tools

### No MCP servers, no wiki, no external skills called

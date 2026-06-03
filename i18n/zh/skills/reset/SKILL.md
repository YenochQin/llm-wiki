---
description: Reset wiki state to a clean scaffold by scope (wiki / raw / log / checkpoints / all). Useful during development or carefree restarts after a botched setup.
argument-hint: "--scope wiki|raw|log|checkpoints|all"
---

# /reset

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> Resets the wiki to a clean scaffold by scope. Designed for development iteration and recovery after a failed setup — not a routine operation.

## Trigger

Manual: `/reset --scope wiki` / `--scope raw` / `--scope log` / `--scope checkpoints` / `--scope all`. Multiple scopes may be combined comma-separated: `--scope wiki,log`.

## Inputs

- `--scope` *(required)*: one of
  - `wiki` — delete every `*.md` under `wiki/<entity>/` and `wiki/outputs/`, every entry under `wiki/sources/`, plus `wiki/index.md`, `wiki/log/`, and `wiki/graph/` files. Preserves `.gitkeep` and `wiki/CLAUDE.md`.
  - `raw` — delete every entry under `raw/papers/`, `raw/notes/`, `raw/web/`, and legacy `raw/prepared/` / `raw/tmp/` (except `.gitkeep`). It does not delete vault-visible copies under `wiki/sources/`.
  - `log` — reset `wiki/log/` to the empty header.
  - `checkpoints` — clear batch state via `research_wiki.py checkpoint-clear`.
  - `all` — every scope above.

## Outputs

- Cleared / reset files on disk.
- Console summary of deleted files and reset files.

## Wiki Interaction

### Reads
- All `wiki/<entity>/*.md` (to enumerate the deletion plan).
- `raw/<sub>/*` (to enumerate raw deletions).

### Writes
- Deletes `wiki/<entity>/*.md` (preserves `.gitkeep`).
- Rewrites `wiki/index.md`, `wiki/graph/*`, optionally `wiki/log/`.
- Deletes `raw/<sub>/*` for raw scope, and `wiki/sources/*` for wiki scope (except `.gitkeep`).

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python tools/research_wiki.py stats '@configured' --json
```

### Step 1: Build the deletion plan (dry-run)

```shell
uv run python tools/reset_wiki.py --scope <scope>
```

This prints a JSON plan listing every file that would be deleted or reset, **without modifying anything**. Display the plan to the user grouped by scope (wiki entity dirs, raw subdirs, log, checkpoints).

### Step 2: Confirm with the user

Print the plan summary and ask for explicit confirmation:

```
About to delete N files and reset M files. Continue? [y/N]
```

If the user says no, exit. **Never proceed without explicit approval** — `/reset` is destructive and `raw/` deletions are not tracked by git.

### Step 3: Execute

```shell
uv run python tools/reset_wiki.py --scope <scope> --yes
```

The tool prints a JSON status report (`{deleted_files, reset_files}`).

### Step 4: Log (unless `log` scope was reset)

If the executed scope did not include `log`, append a log entry so future sessions can see the reset happened:

```shell
uv run python tools/research_wiki.py log '@configured' "reset | scope: <scope>"
```

### Step 5: Report

Print the result and suggest next steps:

```
## Reset complete — scope: <scope>

Deleted: N files
Reset:   M files

Next steps:
- /init       — bootstrap wiki from raw/
- /prefill    — seed foundational background
- /ingest     — add a single source manually
```

## Constraints

- **Confirm before destructive action**: never call `--yes` without showing the plan and asking the user.
- **Preserves**: `.gitkeep` placeholders, `wiki/CLAUDE.md`, `.claude/` (skills are never touched).
- **`raw/` deletes are irreversible**: PDFs are not in git history. Warn the user before executing `raw` or `all` scopes.
- **`/reset` does not touch `tools/`, `mcp-servers/`, `i18n/`, llm-wiki user config, or git state.**
- **Scope is required**: no default action (`/reset` with no flag prompts for scope rather than guessing).

## Error Handling

- **Unknown scope**: print valid scopes and exit nonzero.
- **Missing wiki directory**: report and suggest running `/init`.
- **`checkpoint-clear` failure**: log a warning but do not fail other scopes.

## Dependencies

### Tools
- `uv run python tools/reset_wiki.py --scope <scope> [--yes] [--project-root .]` — deterministic destructive helper
- `uv run python tools/research_wiki.py log '@configured' "<message>"` — append log
- `reset_wiki.py` clears `wiki/.checkpoints/*.json` directly for `checkpoints` scope (no CLI dispatch — the `checkpoint-clear` subcommand requires a specific `task_id`, while `/reset --scope checkpoints` semantics is "clear everything")

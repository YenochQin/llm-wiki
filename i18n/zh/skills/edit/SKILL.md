---
name: edit
description: Add or remove raw sources, or update wiki content, per user request
argument-hint: "[request]"
---

# /edit

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> Add or remove raw sources, or update wiki content, per user request.

## Trigger

User manual: `/edit <user request>`

## Inputs

User request, for example:
- "Download this paper to raw/papers/"
- "Delete raw/papers/xxx.pdf"
- "Update the SOTA tracker in topics/efficient-llm-adaptation"
- "Add a new variant to concepts/lora"

## Outputs

Updated wiki files, `index.md`, `log.md`

## Steps

**Pre-condition**: 已配置的 llm-wiki 仓库（参见 `/setup`）。先解析 Python 解释器和运行时路径，整段流程复用。不要硬编码 `wiki/` 或 `raw/`；两者都来自 `config/paths.json`（或 `LLM_WIKI_WIKI_ROOT` / `LLM_WIKI_RAW_ROOT`）。对 wiki 或 raw 文件调用 `Edit`/`Write` 时，将 `$WIKI_ROOT` / `$RAW_ROOT` 展开为 bootstrap 打印出的绝对路径：

```bash
# Find the project root via git so every command runs through the repository's
# uv-managed Python environment and path configuration.
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT=$(pwd)
fi
cd "$PROJECT_ROOT"

eval "$(uv run python -c 'import shlex, sys; sys.path.insert(0, "tools"); from _paths import load_paths; p = load_paths(); print("WIKI_ROOT=" + shlex.quote(str(p.wiki_root))); print("RAW_ROOT=" + shlex.quote(str(p.raw_root))); print("PROJECT_ROOT=" + shlex.quote(str(p.project_root)))')"
export PROJECT_ROOT WIKI_ROOT RAW_ROOT
```

### STEP 1: Parse User Intent

1. **Add raw sources**:
   - If the user provides a local path: copy to the corresponding directory under `$RAW_ROOT/`
   - If the user provides a web URL: fetch readable markdown/text content and save to `$RAW_ROOT/web/`
2. **Delete raw sources**:
   - Confirm then execute deletion
3. **Update wiki**:
   - Read the relevant pages under `$WIKI_ROOT/` and modify content per user instructions

### STEP 2: Execute Updates

1. Newly added raw sources can later be incorporated into the wiki via `/ingest`
2. Direct wiki modifications: update the specified fields/content in specific pages per user instructions
3. When writing forward links, simultaneously write reverse links

### STEP 3: Update Navigation

1. `EDIT $WIKI_ROOT/index.md`: update relevant entries
2. Append a log entry via the tool (not by manually editing `log.md`):

   ```bash
   uv run python tools/research_wiki.py log "$WIKI_ROOT" "edit | {description}"
   ```

### STEP 4: Report

- List all changes made
- Suggest follow-up actions (e.g. ingest newly added raw sources if applicable)

## Constraints

- `raw/` is read-only for existing files (this skill may add files to `raw/`, but must not modify existing ones)
- Wiki modifications must follow template structure
- Bidirectional links must be kept in sync

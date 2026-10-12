#!/usr/bin/env fish
# ============================================================================
# llm-wiki — One-Click Setup (uv-based, fish shell)
# ============================================================================
# Usage:
#   chmod +x setup.fish && ./setup.fish       # Install dependencies and agent entrypoints
#   ./setup.fish --sync-only                  # Repair agent entrypoints only
#
# What it does:
#   1. Checks prerequisites (uv, Python via uv, Claude Code)
#   2. Creates .venv and installs dependencies via uv
#   3. Copies configuration templates and links the canonical skills
#   4. Verifies the installation
#
# MinerU API key configuration is handled interactively
# by the selected agent — run /setup after starting it.
# ============================================================================

function info
    set_color blue; echo -n "[INFO]  "; set_color normal; echo $argv[1]
end
function ok
    set_color green; echo -n "[OK]    "; set_color normal; echo $argv[1]
end
function warn
    set_color yellow; echo -n "[WARN]  "; set_color normal; echo $argv[1]
end
function fail
    set_color red; echo -n "[FAIL]  "; set_color normal; echo $argv[1]
end

# ── Setup options ──────────────────────────────────────────────────
set -l SYNC_ONLY false
for option in $argv
    switch $option
        case '--sync-only'
            set SYNC_ONLY true
        case '*'
            fail "Unknown option: $option (supported: --sync-only)"
            exit 1
    end
end
set -l PROJECT_ROOT (cd (dirname (status --current-filename)) && pwd)
if not test -d "$PROJECT_ROOT/skills"; or test -L "$PROJECT_ROOT/skills"
    fail "Expected the canonical skills/ directory — run setup from a current checkout"
    exit 1
end

set -l CONFIG_DIR "$XDG_CONFIG_HOME/llm-wiki"
if test -z "$XDG_CONFIG_HOME"
    set CONFIG_DIR "$HOME/.config/llm-wiki"
end
set -l ENV_FILE "$CONFIG_DIR/.env"
set -l VENV_PYTHON "$PROJECT_ROOT/.venv/bin/python"

cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "  llm-wiki — Setup"
echo "============================================"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────────────────

if test "$SYNC_ONLY" = false
info "Checking prerequisites..."

# uv
if command -v uv &>/dev/null
    set -l UV_VERSION (uv --version 2>&1 | awk '{print $2}')
    ok "uv $UV_VERSION"
else
    fail "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  See https://docs.astral.sh/uv/getting-started/installation/ for alternatives."
    exit 1
end

# Claude Code
if command -v claude &>/dev/null
    ok "Claude Code installed"
else
    warn "Claude Code not found."
    echo ""
    echo "  Claude Code is required to use llm-wiki skills."
    echo "  Install with:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    read -n 1 -P "  Continue setup without Claude Code? [y/N] " REPLY
    echo ""
    if not string match -qr '^[Yy]$' -- "$REPLY"
        echo "  Install Claude Code first, then re-run setup.fish"
        exit 1
    end
end

# ── Step 2: Python environment + dependencies (uv) ──────────────────────

echo ""
info "Setting up Python environment with uv..."

if test -n "$VIRTUAL_ENV"; or begin
        test -n "$CONDA_DEFAULT_ENV"; and test "$CONDA_DEFAULT_ENV" != "base"
    end
    warn "Active environment detected; setup always installs llm-wiki into .venv"
end

info "Syncing dependencies from pyproject.toml..."
uv sync --python ">=3.10"; or exit 1
ok "Dependencies synced into .venv"

if not test -x "$VENV_PYTHON"
    fail "Expected $VENV_PYTHON but it does not exist"
    exit 1
end
ok "Using $VENV_PYTHON"

# ── Step 3: Configuration files ─────────────────────────────────────────

echo ""
info "Setting up configuration..."

# llm-wiki user config
mkdir -p "$CONFIG_DIR"; or exit 1
if test -f "$ENV_FILE"
    warn "$ENV_FILE already exists, not overwriting"
else
    cp config/.env.example "$ENV_FILE"; or exit 1
    chmod 600 "$ENV_FILE" 2>/dev/null
    ok "Created $ENV_FILE from config/.env.example"
end
if test -f ".env"
    warn "Legacy project .env detected; tools prefer $ENV_FILE"
end

# Claude Code settings
mkdir -p .claude; or exit 1
if test -f ".claude/settings.local.json"
    warn ".claude/settings.local.json already exists, not overwriting"
else
    cp config/settings.local.json.example .claude/settings.local.json; or exit 1
    ok "Created .claude/settings.local.json"
end

end

# ── Step 3b: Link the canonical skills ──────────────────────────────
echo ""
info "Linking agent entrypoints to skills/"
mkdir -p .claude .agents; or exit 1

function link_skills --argument-names link_path
    if test -L "$link_path"
        if test (readlink "$link_path") = "../skills"
            return 0
        end
        rm "$link_path"; or return 1
    else if test -e "$link_path"
        fail "$link_path is not a symlink; preserve or move it before retrying"
        return 1
    end
    ln -s "../skills" "$link_path"
end
link_skills ".claude/skills"; or exit 1
link_skills ".agents/skills"; or exit 1

mkdir -p ".claude/commands"; or exit 1

echo '---
description: Ingest one paper into llm-wiki.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>) [--discover]"
---

Read and follow @skills/ingest/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```' > ".claude/commands/ingest.md"

echo '---
description: Prepare and ingest local PDF files into llm-wiki.
argument-hint: "(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]"
---

Read and follow @skills/ingest-local-pdf/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```' > ".claude/commands/ingest-local-pdf.md"

echo '---
description: Rank light-ingested paper pages for promotion to full ingest.
argument-hint: "[--limit N] [--min-score N] [--apply <paper-slug>]"
---

Read and follow @skills/promote-light-ingest/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```' > ".claude/commands/promote-light-ingest.md"

echo '---
description: List Zotero collection papers with citationKey, title, and DOI.
argument-hint: "<collection-path> [--zotero-root <dir>] [--no-recursive] [--output-md <path>]"
---

Read and follow @skills/zotero-collection-list/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```' > ".claude/commands/zotero-collection-list.md"

ok "Both agents use the canonical English skills/ directory"
if test "$SYNC_ONLY" = true
    exit 0
end

# ── Step 4: Verify installation ─────────────────────────────────────────

echo ""
info "Verifying installation..."

set -l ERRORS 0
set -l WARNINGS 0

function check_python_snippet
    set -l label $argv[1]
    set -l snippet $argv[2]
    if uv run --python "$VENV_PYTHON" python -c "$snippet" >/dev/null 2>&1
        ok "$label"
        return 0
    else
        fail "$label missing"
        return 1
    end
end

function check_tool_import
    set -l label $argv[1]
    set -l import_stmt $argv[2]
    if pushd tools >/dev/null; and uv run --python "$VENV_PYTHON" python -c "$import_stmt" >/dev/null 2>&1
        popd >/dev/null
        ok "$label"
        return 0
    else
        popd >/dev/null
        fail "$label import error"
        return 1
    end
end

# Real runtime dependencies
if not check_python_snippet "requests" "import requests"
    set ERRORS (math $ERRORS + 1)
end

# Tools
if not check_tool_import "tools/_mineru.py" "from _mineru import extract"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/prepare_paper_source.py" "from prepare_paper_source import main"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/init_discovery.py" "from init_discovery import prepare_inputs"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/fetch_literature.py" "from fetch_literature import search"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/research_wiki.py" "from research_wiki import slugify"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/lint.py" "from lint import check_missing_fields"
    set ERRORS (math $ERRORS + 1)
end
if not check_tool_import "tools/list_zotero_collection.py" "from list_zotero_collection import list_collection"
    set ERRORS (math $ERRORS + 1)
end

# MinerU API token diagnostic (warn-only). The api backend reads process env or
# the unified llm-wiki user config.
if begin
        test -f "$ENV_FILE"; and grep -E '^MINERU_API_TOKEN=.+' "$ENV_FILE" >/dev/null 2>&1
    end; or test -n "$MINERU_API_TOKEN"
    ok "MINERU_API_TOKEN is configured for MinerU"
else
    warn "MINERU_API_TOKEN not set — PDF ingest will fail until you add it"
    echo "        Get a token at https://mineru.net/ and put it in $ENV_FILE"
    set WARNINGS (math $WARNINGS + 1)
end

# Local MinerU backend is opt-in (large download); surface as a hint
if uv run --python "$VENV_PYTHON" python -c "import mineru" >/dev/null 2>&1
    ok "MinerU local backend available (optional)"
else
    info "MinerU local backend not installed (optional). Enable with: uv sync --extra local"
end

# ── Done ────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
if test $ERRORS -eq 0; and test $WARNINGS -eq 0
    set_color green; echo "  Setup complete!"; set_color normal
else if test $ERRORS -eq 0
    set_color yellow; echo "  Setup complete with $WARNINGS warning(s)"; set_color normal
else
    set_color yellow; echo "  Setup complete with $ERRORS error(s) and $WARNINGS warning(s)"; set_color normal
end
echo "============================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Authenticate Claude Code (if not already):"
echo "     claude login"
echo ""
echo "  2. Set MINERU_API_TOKEN in $ENV_FILE (required for PDF ingest):"
echo "     https://mineru.net/  →  create token  →  paste into .env"
echo ""
echo "  3. Run Python tools through uv (no need to activate the venv):"
echo "     uv run python -X utf8 tools/research_wiki.py --help"
echo ""
echo "  4. Start Claude Code:"
echo "     claude"
echo ""
echo "  5. Complete API key configuration (guided):"
echo "     /setup"
echo "     Claude Code will walk you through llm-wiki API keys —"
echo "     skip any you don't have yet."
echo ""
echo "  6. Then initialize your wiki:"
echo "     /init [your-research-topic]"
echo ""
echo "  For more, see README.md"
echo ""

if test $ERRORS -gt 0
    exit 1
end

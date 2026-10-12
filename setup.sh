#!/usr/bin/env bash
# ============================================================================
# llm-wiki — One-Click Setup (uv-based)
# ============================================================================
# Usage:
#   chmod +x setup.sh && ./setup.sh            # Install dependencies and agent entrypoints
#   ./setup.sh --sync-only                     # Repair agent entrypoints only
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

set -e

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; }

# ── Setup options ──────────────────────────────────────────────────
SYNC_ONLY=false
while [ $# -gt 0 ]; do
  case "$1" in
    --sync-only) SYNC_ONLY=true; shift ;;
    *) fail "Unknown option: $1 (supported: --sync-only)"; exit 1 ;;
  esac
done
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$PROJECT_ROOT/skills" ] || [ -L "$PROJECT_ROOT/skills" ]; then
    fail "Expected the canonical skills/ directory — run setup from a current checkout"
    exit 1
fi
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/llm-wiki"
ENV_FILE="$CONFIG_DIR/.env"
cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "  llm-wiki — Setup"
echo "============================================"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────────────────

if [ "$SYNC_ONLY" = false ]; then
info "Checking prerequisites..."

# uv
if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
    ok "uv $UV_VERSION"
else
    fail "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  See https://docs.astral.sh/uv/getting-started/installation/ for alternatives."
    exit 1
fi

# Claude Code
if command -v claude &>/dev/null; then
    ok "Claude Code installed"
else
    warn "Claude Code not found."
    echo ""
    echo "  Claude Code is required to use llm-wiki skills."
    echo "  Install with:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo ""
    read -p "  Continue setup without Claude Code? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "  Install Claude Code first, then re-run setup.sh"
        exit 1
    fi
fi

# ── Step 2: Python environment + dependencies (uv) ──────────────────────

echo ""
info "Setting up Python environment with uv..."

if [ -n "$VIRTUAL_ENV" ] || { [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" != "base" ]; }; then
    warn "Active environment detected; setup always installs llm-wiki into .venv"
fi

info "Syncing dependencies from pyproject.toml..."
uv sync --python ">=3.10"
ok "Dependencies synced into .venv"

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    fail "Expected $VENV_PYTHON but it does not exist"
    exit 1
fi
ok "Using $VENV_PYTHON"

# ── Step 3: Configuration files ─────────────────────────────────────────

echo ""
info "Setting up configuration..."

# llm-wiki user config
mkdir -p "$CONFIG_DIR"
if [ -f "$ENV_FILE" ]; then
    warn "$ENV_FILE already exists, not overwriting"
else
    cp config/.env.example "$ENV_FILE"
    chmod 600 "$ENV_FILE" 2>/dev/null || true
    ok "Created $ENV_FILE from config/.env.example"
fi
if [ -f ".env" ]; then
    warn "Legacy project .env detected; tools prefer $ENV_FILE"
fi

# Claude Code settings
mkdir -p .claude
if [ -f ".claude/settings.local.json" ]; then
    warn ".claude/settings.local.json already exists, not overwriting"
else
    cp config/settings.local.json.example .claude/settings.local.json
    ok "Created .claude/settings.local.json"
fi
fi

# ── Step 3b: Link the canonical skills ──────────────────────────────
echo ""
info "Linking agent entrypoints to skills/"
mkdir -p .claude .agents

link_skills() {
    local link_path="$1"
    if [ -L "$link_path" ]; then
        [ "$(readlink "$link_path")" = "../skills" ] && return 0
        rm "$link_path"
    elif [ -e "$link_path" ]; then
        fail "$link_path is not a symlink; preserve or move it before retrying"
        return 1
    fi
    ln -s "../skills" "$link_path"
}
link_skills ".claude/skills"
link_skills ".agents/skills"

mkdir -p ".claude/commands"
cat > ".claude/commands/ingest.md" <<'EOF'
---
description: Ingest one paper into llm-wiki.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>) [--discover]"
---

Read and follow @skills/ingest/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```
EOF

cat > ".claude/commands/ingest-local-pdf.md" <<'EOF'
---
description: Prepare and ingest local PDF files into llm-wiki.
argument-hint: "(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]"
---

Read and follow @skills/ingest-local-pdf/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```
EOF

cat > ".claude/commands/promote-light-ingest.md" <<'EOF'
---
description: Rank light-ingested paper pages for promotion to full ingest.
argument-hint: "[--limit N] [--min-score N] [--apply <paper-slug>]"
---

Read and follow @skills/promote-light-ingest/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```
EOF

cat > ".claude/commands/zotero-collection-list.md" <<'EOF'
---
description: List Zotero collection papers with citationKey, title, and DOI.
argument-hint: "<collection-path> [--zotero-root <dir>] [--no-recursive] [--output-md <path>]"
---

Read and follow @skills/zotero-collection-list/SKILL.md exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```
EOF

ok "Both agents use the canonical English skills/ directory"
if [ "$SYNC_ONLY" = true ]; then
    exit 0
fi

# ── Step 4: Verify installation ─────────────────────────────────────────

echo ""
info "Verifying installation..."

ERRORS=0
WARNINGS=0

check_python_snippet() {
    local label="$1"
    local snippet="$2"
    if uv run --python "$VENV_PYTHON" python -c "$snippet" >/dev/null 2>&1; then
        ok "$label"
    else
        fail "$label missing"
        ERRORS=$((ERRORS+1))
    fi
}

check_tool_import() {
    local label="$1"
    local import_stmt="$2"
    if (cd tools && uv run --python "$VENV_PYTHON" python -c "$import_stmt") >/dev/null 2>&1; then
        ok "$label"
    else
        fail "$label import error"
        ERRORS=$((ERRORS+1))
    fi
}

# Real runtime dependencies
check_python_snippet "requests" "import requests"

# Tools
check_tool_import "tools/_mineru.py" "from _mineru import extract"
check_tool_import "tools/prepare_paper_source.py" "from prepare_paper_source import main"
check_tool_import "tools/init_discovery.py" "from init_discovery import prepare_inputs"
check_tool_import "tools/fetch_literature.py" "from fetch_literature import search"
check_tool_import "tools/research_wiki.py" "from research_wiki import slugify"
check_tool_import "tools/lint.py" "from lint import check_missing_fields"
check_tool_import "tools/list_zotero_collection.py" "from list_zotero_collection import list_collection"

# MinerU API token diagnostic (warn-only). The api backend reads process env or
# the unified llm-wiki user config.
if { [ -f "$ENV_FILE" ] && grep -E '^MINERU_API_TOKEN=.+' "$ENV_FILE" >/dev/null 2>&1; } \
   || [ -n "${MINERU_API_TOKEN:-}" ]; then
    ok "MINERU_API_TOKEN is configured for MinerU"
else
    warn "MINERU_API_TOKEN not set — PDF ingest will fail until you add it"
    echo "        Get a token at https://mineru.net/ and put it in $ENV_FILE"
    WARNINGS=$((WARNINGS+1))
fi

# Local MinerU backend is opt-in (large download); surface as a hint
if uv run --python "$VENV_PYTHON" python -c "import mineru" >/dev/null 2>&1; then
    ok "MinerU local backend available (optional)"
else
    info "MinerU local backend not installed (optional). Enable with: uv sync --extra local"
fi

# ── Done ────────────────────────────────────────────────────────────────

echo ""
echo "============================================"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "  ${GREEN}Setup complete!${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "  ${YELLOW}Setup complete with $WARNINGS warning(s)${NC}"
else
    echo -e "  ${YELLOW}Setup complete with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
fi
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

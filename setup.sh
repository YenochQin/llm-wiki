#!/usr/bin/env bash
# ============================================================================
# llm-wiki — One-Click Setup (uv-based)
# ============================================================================
# Usage:
#   chmod +x setup.sh && ./setup.sh            # English (default; only lang for now)
#
# What it does:
#   1. Checks prerequisites (uv, Python via uv, Claude Code)
#   2. Creates .venv and installs dependencies via uv
#   3. Copies configuration templates and activates language files
#   4. Verifies the installation
#
# API key configuration (Semantic Scholar, MinerU, Review LLM) is handled
# interactively by Claude Code — run /setup after starting Claude Code.
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

# ── Language selection ──────────────────────────────────────────────
LANG_CODE="en"
while [ $# -gt 0 ]; do
  case "$1" in
    --lang=*) LANG_CODE="${1#*=}"; shift ;;
    --lang)   LANG_CODE="${2:-en}"; shift 2 ;;
    *)        shift ;;
  esac
done
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
# Only `en` is shipped today; the lang flag stays in place for future i18n/zh.
[[ "$LANG_CODE" == "en" ]] || { fail "Unknown lang: $LANG_CODE (only 'en' is shipped)"; exit 1; }
I18N_DIR="$PROJECT_ROOT/i18n/$LANG_CODE"
[ -d "$I18N_DIR" ] || { fail "i18n/$LANG_CODE not found — run from the project root"; exit 1; }
cd "$PROJECT_ROOT"

echo ""
echo "============================================"
echo "  llm-wiki — Setup"
echo "============================================"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────────────────

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

if [ -d ".venv" ]; then
    warn ".venv already exists, using it"
else
    uv venv .venv --python ">=3.10"
    ok "Created .venv (uv-managed)"
fi

VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    fail "Expected $VENV_PYTHON but it does not exist"
    exit 1
fi
ok "Using $VENV_PYTHON"

info "Installing dependencies into .venv via uv..."
uv pip install -e . --python "$VENV_PYTHON" -q
ok "Dependencies installed into .venv"

# ── Step 3: Configuration files ─────────────────────────────────────────

echo ""
info "Setting up configuration..."

# .env
if [ -f ".env" ]; then
    warn ".env already exists, not overwriting"
else
    cp .env.example .env
    ok "Created .env from template"
fi

# MinerU user config
MINERU_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/MinerU"
MINERU_ENV_FILE="$MINERU_CONFIG_DIR/mineru.env"
mkdir -p "$MINERU_CONFIG_DIR"
if [ -f "$MINERU_ENV_FILE" ]; then
    warn "$MINERU_ENV_FILE already exists, not overwriting"
else
    cp config/mineru.env.example "$MINERU_ENV_FILE"
    ok "Created $MINERU_ENV_FILE from template"
fi

# Claude Code settings
mkdir -p .claude
if [ -f ".claude/settings.local.json" ]; then
    warn ".claude/settings.local.json already exists, not overwriting"
else
    cp config/settings.local.json.example .claude/settings.local.json
    ok "Created .claude/settings.local.json"
fi

# ── Step 3b: Activate language files ───────────────────────────────
echo ""
info "Activating language: $LANG_CODE"
cp "$I18N_DIR/CLAUDE.md" CLAUDE.md
for src in "$I18N_DIR/skills"/*/SKILL.md; do
    skill_dir=$(dirname "$src")
    name=$(basename "$skill_dir")
    mkdir -p ".claude/skills/$name"
    cp -R "$skill_dir"/. ".claude/skills/$name/"
done
mkdir -p ".claude/skills/shared-references"
cp "$I18N_DIR/shared-references"/*.md ".claude/skills/shared-references/"
echo "$LANG_CODE" > .claude/.current-lang
ok "Language files activated ($LANG_CODE)"

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
check_python_snippet "PyMuPDF (fitz)" "import fitz"
check_python_snippet "requests" "import requests"
check_python_snippet "feedparser" "import feedparser"

# Tools
check_tool_import "tools/_mineru.py" "from _mineru import extract"
check_tool_import "tools/prepare_paper_source.py" "from prepare_paper_source import main"
check_tool_import "tools/init_discovery.py" "from init_discovery import prepare_inputs"
check_tool_import "tools/fetch_s2.py" "from fetch_s2 import search"
check_tool_import "tools/fetch_arxiv.py" "from fetch_arxiv import fetch_recent"
check_tool_import "tools/research_wiki.py" "from research_wiki import slugify"
check_tool_import "tools/lint.py" "from lint import check_missing_fields"

# MinerU API token diagnostic (warn-only). The api backend reads process env or
# ~/.config/MinerU/mineru.env; /setup writes the token there.
if { [ -f "$MINERU_ENV_FILE" ] && grep -E '^MINERU_API_TOKEN=.+' "$MINERU_ENV_FILE" >/dev/null 2>&1; } \
   || [ -n "${MINERU_API_TOKEN:-}" ]; then
    ok "MINERU_API_TOKEN is configured for MinerU"
else
    warn "MINERU_API_TOKEN not set — PDF ingest will fail until you add it"
    echo "        Get a token at https://mineru.net/ and put it in $MINERU_ENV_FILE"
    WARNINGS=$((WARNINGS+1))
fi

# Local MinerU backend is opt-in (large download); surface as a hint
if uv run --python "$VENV_PYTHON" python -c "import mineru" >/dev/null 2>&1; then
    ok "MinerU local backend available (optional)"
else
    info "MinerU local backend not installed (optional). Enable with: uv pip install -e .[local]"
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
echo "  2. Set MINERU_API_TOKEN in $MINERU_ENV_FILE (required for PDF ingest):"
echo "     https://mineru.net/  →  create token  →  paste into mineru.env"
echo ""
echo "  3. Run Python tools through uv (no need to activate the venv):"
echo "     uv run python tools/research_wiki.py --help"
echo ""
echo "  4. Start Claude Code:"
echo "     claude"
echo ""
echo "  5. Complete API key configuration (guided):"
echo "     /setup"
echo "     Claude Code will walk you through Semantic Scholar, MinerU,"
echo "     and Review LLM — skip any you don't have yet."
echo ""
echo "  6. Then initialize your wiki:"
echo "     /init [your-research-topic]"
echo ""
echo "  For more, see README.md"
echo ""

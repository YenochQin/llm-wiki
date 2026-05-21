#!/usr/bin/env nu
# ============================================================================
# llm-wiki - One-Click Setup (uv-based, Nushell)
# ============================================================================
# Usage:
#   nu setup.nu                 # English (default)
#   nu setup.nu --lang zh       # Chinese runtime files
#
# This is the Nushell counterpart to setup.sh. It keeps the same setup flow:
# checks prerequisites, syncs the uv environment, writes local config files,
# activates runtime language files, creates skill links, and verifies imports.
# ============================================================================

def info [message: string] { print $"(ansi blue)[INFO](ansi reset)  ($message)" }
def ok [message: string] { print $"(ansi green)[OK](ansi reset)    ($message)" }
def warn [message: string] { print $"(ansi yellow)[WARN](ansi reset)  ($message)" }
def fail [message: string] { print $"(ansi red)[FAIL](ansi reset)  ($message)" }

def command-exists [name: string] {
    not (which $name | is-empty)
}

def config-root [] {
    if ($env.XDG_CONFIG_HOME? | is-not-empty) {
        $env.XDG_CONFIG_HOME
    } else if ($env.HOME? | is-not-empty) {
        $env.HOME | path join ".config"
    } else if ($nu.home-dir? | is-not-empty) {
        $nu.home-dir | path join ".config"
    } else {
        error make { msg: "Could not determine a home directory for llm-wiki config" }
    }
}

def venv-python [project_root: string] {
    let unix_python = ($project_root | path join ".venv" "bin" "python")
    let windows_python = ($project_root | path join ".venv" "Scripts" "python.exe")

    if ($unix_python | path exists) {
        $unix_python
    } else {
        $windows_python
    }
}

def powershell-single-quote [value: string] {
    "'" + ($value | str replace --all "'" "''") + "'"
}

def force-symlink [target: string, link_path: string] {
    if ($link_path | path exists --no-symlink) {
        rm -r -f $link_path
    }

    let result = if (command-exists "ln") {
        ln -s $target $link_path | complete
    } else if ((sys host | get name | str downcase) | str contains "windows") {
        let ps_dir = (powershell-single-quote ($link_path | path dirname))
        let ps_name = (powershell-single-quote ($link_path | path basename))
        let ps_target = (powershell-single-quote $target)
        let ps_command = $"Set-Location -LiteralPath ($ps_dir); New-Item -ItemType SymbolicLink -Path ($ps_name) -Target ($ps_target) | Out-Null"
        ^powershell -NoProfile -Command $ps_command | complete
    } else {
        {
            exit_code: 127,
            stdout: "",
            stderr: "ln command not found"
        }
    }
    if $result.exit_code != 0 {
        fail $"Could not create symlink ($link_path) -> ($target)"
        let detail = ((($result.stderr | default "") + ($result.stdout | default "")) | str trim)
        if ($detail | is-not-empty) {
            print $"      symlink output: ($detail)"
        }
        if ((sys host | get name | str downcase) | str contains "windows") {
            print "      On Windows, enable Developer Mode or run Nushell as Administrator."
            print "      If Developer Mode was just enabled, close this terminal and open a new one."
        }
        error make { msg: "symlink creation failed" }
    }
}

def write-lines [path: string, lines: list<string>] {
    let newline = (char nl)
    let content = (($lines | str join $newline) + $newline)
    $content | save --force $path
}

def write-command-file [
    path: string,
    description: string,
    argument_hint: string,
    skill_path: string
] {
    write-lines $path [
        "---"
        $"description: ($description)"
        $"argument-hint: \"($argument_hint)\""
        "---"
        ""
        $"Read and follow @($skill_path) exactly."
        ""
        "Use these user-provided invocation arguments for the skill:"
        ""
        "```"
        "$ARGUMENTS"
        "```"
    ]
}

def check-python-snippet [label: string, venv_python: string, snippet: string] {
    let result = (^uv run --python $venv_python python -c $snippet | complete)
    if $result.exit_code == 0 {
        ok $label
        true
    } else {
        fail $"($label) missing"
        false
    }
}

def check-tool-import [label: string, project_root: string, venv_python: string, import_stmt: string] {
    let previous = (pwd)
    cd ($project_root | path join "tools")
    let result = (^uv run --python $venv_python python -c $import_stmt | complete)
    cd $previous

    if $result.exit_code == 0 {
        ok $label
        true
    } else {
        fail $"($label) import error"
        false
    }
}

def main [
    --lang: string = "en"
] {
    let lang_code = $lang
    let supported_langs = ["en" "zh"]
    let project_root = ($env.CURRENT_FILE | path dirname | path expand)
    let i18n_dir = ($project_root | path join "i18n" $lang_code)
    let config_dir = ((config-root) | path join "llm-wiki")
    let env_file = ($config_dir | path join ".env")

    if not ($lang_code in $supported_langs) {
        fail ($"Unknown lang: ($lang_code)" + " (supported: en, zh)")
        exit 1
    }

    if not ($i18n_dir | path exists) {
        fail $"i18n/($lang_code) not found - run from the project root"
        exit 1
    }

    cd $project_root

    print ""
    print "============================================"
    print "  llm-wiki - Setup"
    print "============================================"
    print ""

    info "Checking prerequisites..."

    if (command-exists "uv") {
        let uv_output = (^uv --version | complete)
        let uv_version = if $uv_output.exit_code == 0 {
            ($uv_output.stdout | str trim | split row " " | get 1?)
        } else {
            null
        }
        ok $"uv ($uv_version | default 'installed')"
    } else {
        fail "uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        print "  See https://docs.astral.sh/uv/getting-started/installation/ for alternatives."
        exit 1
    }

    if (command-exists "claude") {
        ok "Claude Code installed"
    } else {
        warn "Claude Code not found."
        print ""
        print "  Claude Code is required to use llm-wiki skills."
        print "  Install with:"
        print "    npm install -g @anthropic-ai/claude-code"
        print ""
        let reply = (input "  Continue setup without Claude Code? [y/N] ")
        if not (($reply | str trim | str downcase | str starts-with "y")) {
            print "  Install Claude Code first, then re-run setup.nu"
            exit 1
        }
    }

    print ""
    info "Setting up Python environment with uv..."

    let has_virtual_env = ($env.VIRTUAL_ENV? | is-not-empty)
    let conda_env = ($env.CONDA_DEFAULT_ENV? | default "")
    if ($has_virtual_env or (($conda_env | is-not-empty) and $conda_env != "base")) {
        warn "Active environment detected; setup always installs llm-wiki into .venv"
    }

    info "Syncing dependencies from pyproject.toml..."
    ^uv sync --python ">=3.10"
    ok "Dependencies synced into .venv"

    let venv_python_path = (venv-python $project_root)
    if not ($venv_python_path | path exists) {
        fail $"Expected ($venv_python_path) but it does not exist"
        exit 1
    }
    ok $"Using ($venv_python_path)"

    print ""
    info "Setting up configuration..."

    mkdir $config_dir
    if ($env_file | path exists) {
        warn $"($env_file) already exists, not overwriting"
    } else {
        cp ($project_root | path join "config" ".env.example") $env_file
        if not (((sys host | get name | str downcase) | str contains "windows")) {
            try { ^chmod 600 $env_file } catch { }
        }
        ok $"Created ($env_file) from config/.env.example"
    }

    if ($project_root | path join ".env" | path exists) {
        warn $"Legacy project .env detected; tools prefer ($env_file)"
    }

    mkdir ($project_root | path join ".claude")
    let claude_settings = ($project_root | path join ".claude" "settings.local.json")
    if ($claude_settings | path exists) {
        warn ".claude/settings.local.json already exists, not overwriting"
    } else {
        cp ($project_root | path join "config" "settings.local.json.example") $claude_settings
        ok "Created .claude/settings.local.json"
    }

    print ""
    info $"Activating language: ($lang_code)"
    cp --force ($i18n_dir | path join "CLAUDE.md") ($project_root | path join "CLAUDE.md")
    cp --force ($i18n_dir | path join "AGENTS.md") ($project_root | path join "AGENTS.md")

    let root_skills_target = ("i18n" | path join $lang_code "skills")
    let shared_references_target = "../shared-references"
    let app_skills_target = "../skills"

    force-symlink $root_skills_target ($project_root | path join "skills")
    force-symlink $shared_references_target ($i18n_dir | path join "skills" "shared-references")

    mkdir ($project_root | path join ".agents")
    force-symlink $app_skills_target ($project_root | path join ".claude" "skills")
    force-symlink $app_skills_target ($project_root | path join ".agents" "skills")

    let commands_dir = ($project_root | path join ".claude" "commands")
    mkdir $commands_dir

    write-command-file ($commands_dir | path join "ingest.md") "Ingest one paper into llm-wiki." "[--zotero-root <dir>] (--title <str>|--doi <doi>|--item-key <key>) [--discover]" "skills/ingest/SKILL.md"

    write-command-file ($commands_dir | path join "ingest-local-pdf.md") "Prepare and ingest local PDF files into llm-wiki." "(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]" "skills/ingest-local-pdf/SKILL.md"

    write-command-file ($commands_dir | path join "promote-light-ingest.md") "Rank light-ingested paper pages for promotion to full ingest." "[--limit N] [--min-score N] [--apply <paper-slug>]" "skills/promote-light-ingest/SKILL.md"

    write-command-file ($commands_dir | path join "zotero-collection-list.md") "List Zotero collection papers with citationKey, title, and DOI." "<collection-path> [--zotero-root <dir>] [--no-recursive] [--output-md <path>]" "skills/zotero-collection-list/SKILL.md"

    write-lines ($project_root | path join ".claude" ".current-lang") [$lang_code]
    write-lines ($project_root | path join ".agents" ".current-lang") [$lang_code]
    ok ($"Language files activated \(" + $lang_code + ")")

    print ""
    info "Verifying installation..."

    mut errors = 0
    mut warnings = 0

    if not (check-python-snippet "requests" $venv_python_path "import requests") { $errors = ($errors + 1) }

    let tool_imports = [
        [label, import_stmt];
        ["tools/_mineru.py", "from _mineru import extract"]
        ["tools/prepare_paper_source.py", "from prepare_paper_source import main"]
        ["tools/init_discovery.py", "from init_discovery import prepare_inputs"]
        ["tools/fetch_literature.py", "from fetch_literature import search"]
        ["tools/research_wiki.py", "from research_wiki import slugify"]
        ["tools/lint.py", "from lint import check_missing_fields"]
        ["tools/list_zotero_collection.py", "from list_zotero_collection import list_collection"]
    ]

    for row in $tool_imports {
        if not (check-tool-import $row.label $project_root $venv_python_path $row.import_stmt) {
            $errors = ($errors + 1)
        }
    }

    let token_from_file = if ($env_file | path exists) {
        open $env_file | lines | any {|line| $line =~ '^MINERU_API_TOKEN=.+' }
    } else {
        false
    }
    let token_from_env = ($env.MINERU_API_TOKEN? | is-not-empty)

    if ($token_from_file or $token_from_env) {
        ok "MINERU_API_TOKEN is configured for MinerU"
    } else {
        warn "MINERU_API_TOKEN not set - PDF ingest will fail until you add it"
        print $"        Get a token at https://mineru.net/ and put it in ($env_file)"
        $warnings = ($warnings + 1)
    }

    let mineru_result = (^uv run --python $venv_python_path python -c "import mineru" | complete)
    if $mineru_result.exit_code == 0 {
        ok "MinerU local backend available (optional)"
    } else {
        info "MinerU local backend not installed (optional). Enable with: uv sync --extra local"
    }

    print ""
    print "============================================"
    if $errors == 0 and $warnings == 0 {
        print $"  (ansi green)Setup complete!(ansi reset)"
    } else if $errors == 0 {
        print ((ansi yellow) + $"  Setup complete with ($warnings) warnings" + (ansi reset))
    } else {
        print ((ansi yellow) + $"  Setup complete with ($errors) errors and ($warnings) warnings" + (ansi reset))
    }
    print "============================================"
    print ""
    print "  Next steps:"
    print ""
    print "  1. Authenticate Claude Code (if not already):"
    print "     claude login"
    print ""
    print ($"  2. Set MINERU_API_TOKEN in ($env_file)" + " (required for PDF ingest):")
    print "     https://mineru.net/  ->  create token  ->  paste into .env"
    print ""
    print "  3. Run Python tools through uv (no need to activate the venv):"
    print "     uv run python tools/research_wiki.py --help"
    print ""
    print "  4. Start Claude Code:"
    print "     claude"
    print ""
    print "  5. Complete API key configuration (guided):"
    print "     /setup"
    print "     Claude Code will walk you through llm-wiki API keys -"
    print "     skip any you don't have yet."
    print ""
    print "  6. Then initialize your wiki:"
    print "     /init [your-research-topic]"
    print ""
    print "  For more, see README.md"
    print ""

    if $errors > 0 {
        exit 1
    }
}

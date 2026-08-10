#!/usr/bin/env pwsh
<#
  llm-wiki — One-Click Setup (uv-based, PowerShell)

  Usage:
    pwsh -File .\setup.ps1                 # English (default)
    pwsh -File .\setup.ps1 -Lang zh        # Chinese runtime files
#>

[CmdletBinding()]
param(
    [ValidateSet('en', 'zh')]
    [string]$Lang = 'en'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Info([string]$Message) { Write-Host '[INFO] ' -ForegroundColor Blue -NoNewline; Write-Host $Message }
function Write-Ok([string]$Message) { Write-Host '[OK]   ' -ForegroundColor Green -NoNewline; Write-Host $Message }
function Write-Warn([string]$Message) { Write-Host '[WARN] ' -ForegroundColor Yellow -NoNewline; Write-Host $Message }
function Write-Fail([string]$Message) { Write-Host '[FAIL] ' -ForegroundColor Red -NoNewline; Write-Host $Message }

function Test-Command([string]$Name) {
    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Set-Symlink([string]$Target, [string]$LinkPath) {
    $existing = Get-Item -LiteralPath $LinkPath -Force -ErrorAction SilentlyContinue
    if ($null -ne $existing) {
        Remove-Item -LiteralPath $LinkPath -Force -Recurse
    }

    try {
        New-Item -ItemType SymbolicLink -Path $LinkPath -Target $Target -ErrorAction Stop | Out-Null
    }
    catch {
        Write-Fail "Could not create symlink $LinkPath -> $Target"
        Write-Host '       On Windows, enable Developer Mode or run PowerShell as Administrator.'
        Write-Host '       If Developer Mode was just enabled, open a new terminal and retry.'
        throw
    }
}

function Write-TextFile([string]$Path, [string]$Content) {
    $normalized = $Content.TrimEnd("`r", "`n") + "`n"
    $existing = if (Test-Path -LiteralPath $Path) { Get-Content -LiteralPath $Path -Raw } else { $null }
    if ($existing -ne $normalized) {
        Set-Content -LiteralPath $Path -Value $normalized -NoNewline -Encoding utf8
    }
}

function Write-CommandFile([string]$Path, [string]$Description, [string]$ArgumentHint, [string]$SkillPath) {
    $content = @'
---
description: {0}
argument-hint: "{1}"
---

Read and follow @{2} exactly.

Use these user-provided invocation arguments for the skill:

```
$ARGUMENTS
```
'@ -f $Description, $ArgumentHint, $SkillPath
    Write-TextFile -Path $Path -Content $content
}

function Test-PythonSnippet([string]$Label, [string]$VenvPython, [string]$Snippet) {
    & uv run --python $VenvPython python -c $Snippet *> $null
    if ($LASTEXITCODE -eq 0) {
        Write-Ok $Label
        return $true
    }

    Write-Fail "$Label missing"
    return $false
}

function Test-ToolImport([string]$Label, [string]$ProjectRoot, [string]$VenvPython, [string]$ImportStatement) {
    $succeeded = $false
    Push-Location (Join-Path $ProjectRoot 'tools')
    try {
        & uv run --python $VenvPython python -c $ImportStatement *> $null
        $succeeded = $LASTEXITCODE -eq 0
    }
    finally {
        Pop-Location
    }

    if ($succeeded) {
        Write-Ok $Label
        return $true
    }

    Write-Fail "$Label import error"
    return $false
}

$projectRoot = $PSScriptRoot
$i18nDir = Join-Path $projectRoot "i18n\$Lang"
$configBase = if ($env:XDG_CONFIG_HOME) {
    $env:XDG_CONFIG_HOME
} else {
    Join-Path ([Environment]::GetFolderPath('UserProfile')) '.config'
}
$configDir = Join-Path $configBase 'llm-wiki'
$envFile = Join-Path $configDir '.env'

if (-not (Test-Path -LiteralPath $i18nDir -PathType Container)) {
    Write-Fail "i18n/$Lang not found — run from the project root"
    exit 1
}

Set-Location -LiteralPath $projectRoot

Write-Host ''
Write-Host '============================================'
Write-Host '  llm-wiki — Setup'
Write-Host '============================================'
Write-Host ''

Write-Info 'Checking prerequisites...'
if (-not (Test-Command 'uv')) {
    Write-Fail 'uv not found. Install it from https://docs.astral.sh/uv/getting-started/installation/'
    exit 1
}
$uvVersion = (& uv --version).Trim()
Write-Ok $uvVersion

if (Test-Command 'claude') {
    Write-Ok 'Claude Code installed'
} else {
    Write-Warn 'Claude Code not found.'
    Write-Host ''
    Write-Host '  Claude Code is required to use llm-wiki skills.'
    Write-Host '  Install with: npm install -g @anthropic-ai/claude-code'
    $reply = Read-Host '  Continue setup without Claude Code? [y/N]'
    if ($reply -notmatch '^[Yy]') {
        Write-Host '  Install Claude Code first, then re-run setup.ps1'
        exit 1
    }
}

Write-Host ''
Write-Info 'Setting up Python environment with uv...'
if ($env:VIRTUAL_ENV -or ($env:CONDA_DEFAULT_ENV -and $env:CONDA_DEFAULT_ENV -ne 'base')) {
    Write-Warn 'Active environment detected; setup always installs llm-wiki into .venv'
}

Write-Info 'Syncing dependencies from pyproject.toml...'
& uv sync --python '>=3.10'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Ok 'Dependencies synced into .venv'

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Fail "Expected $venvPython but it does not exist"
    exit 1
}
Write-Ok "Using $venvPython"

Write-Host ''
Write-Info 'Setting up configuration...'
New-Item -ItemType Directory -Path $configDir -Force | Out-Null
if (Test-Path -LiteralPath $envFile -PathType Leaf) {
    Write-Warn "$envFile already exists, not overwriting"
} else {
    Copy-Item -LiteralPath (Join-Path $projectRoot 'config\.env.example') -Destination $envFile
    Write-Ok "Created $envFile from config/.env.example"
}
if (Test-Path -LiteralPath (Join-Path $projectRoot '.env') -PathType Leaf) {
    Write-Warn "Legacy project .env detected; tools prefer $envFile"
}

$claudeDir = Join-Path $projectRoot '.claude'
New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
$claudeSettings = Join-Path $claudeDir 'settings.local.json'
if (Test-Path -LiteralPath $claudeSettings -PathType Leaf) {
    Write-Warn '.claude/settings.local.json already exists, not overwriting'
} else {
    Copy-Item -LiteralPath (Join-Path $projectRoot 'config\settings.local.json.example') -Destination $claudeSettings
    Write-Ok 'Created .claude/settings.local.json'
}

Write-Host ''
Write-Info "Activating language: $Lang"
Copy-Item -LiteralPath (Join-Path $i18nDir 'CLAUDE.md') -Destination (Join-Path $projectRoot 'CLAUDE.md') -Force
Copy-Item -LiteralPath (Join-Path $i18nDir 'AGENTS.md') -Destination (Join-Path $projectRoot 'AGENTS.md') -Force

Set-Symlink -Target "i18n\$Lang\skills" -LinkPath (Join-Path $projectRoot 'skills')
Set-Symlink -Target '..\shared-references' -LinkPath (Join-Path $i18nDir 'skills\shared-references')

$agentsDir = Join-Path $projectRoot '.agents'
New-Item -ItemType Directory -Path $agentsDir -Force | Out-Null
Set-Symlink -Target '..\skills' -LinkPath (Join-Path $claudeDir 'skills')
Set-Symlink -Target '..\skills' -LinkPath (Join-Path $agentsDir 'skills')

$commandsDir = Join-Path $claudeDir 'commands'
New-Item -ItemType Directory -Path $commandsDir -Force | Out-Null
Write-CommandFile -Path (Join-Path $commandsDir 'ingest.md') -Description 'Ingest one paper into llm-wiki.' -ArgumentHint '[--zotero-root <dir>] (--title <str>| --doi <doi>) [--discover]' -SkillPath 'skills/ingest/SKILL.md'
Write-CommandFile -Path (Join-Path $commandsDir 'ingest-local-pdf.md') -Description 'Prepare and ingest local PDF files into llm-wiki.' -ArgumentHint '(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]' -SkillPath 'skills/ingest-local-pdf/SKILL.md'
Write-CommandFile -Path (Join-Path $commandsDir 'promote-light-ingest.md') -Description 'Rank light-ingested paper pages for promotion to full ingest.' -ArgumentHint '[--limit N] [--min-score N] [--apply <paper-slug>]' -SkillPath 'skills/promote-light-ingest/SKILL.md'
Write-CommandFile -Path (Join-Path $commandsDir 'zotero-collection-list.md') -Description 'List Zotero collection papers with citationKey, title, and DOI.' -ArgumentHint '<collection-path> [--zotero-root <dir>] [--no-recursive] [--output-md <path>]' -SkillPath 'skills/zotero-collection-list/SKILL.md'
Write-CommandFile -Path (Join-Path $commandsDir 'cal-report-analysis.md') -Description 'Index calculation data and write a grounded analysis report.' -ArgumentHint '[scope] [--data-root <dir>] [--data-dir <dir>] [--report-dir <dir>] [--table-rows N] [--text-lines N] [--no-write]' -SkillPath 'skills/cal-report-analysis/SKILL.md'
Write-TextFile -Path (Join-Path $claudeDir '.current-lang') -Content $Lang
Write-TextFile -Path (Join-Path $agentsDir '.current-lang') -Content $Lang
Write-Ok "Language files activated ($Lang)"

Write-Host ''
Write-Info 'Verifying installation...'
$errors = 0
$warnings = 0

if (-not (Test-PythonSnippet -Label 'requests' -VenvPython $venvPython -Snippet 'import requests')) { $errors++ }

$toolImports = @(
    @{ Label = 'tools/_mineru.py'; Import = 'from _mineru import extract' },
    @{ Label = 'tools/prepare_paper_source.py'; Import = 'from prepare_paper_source import main' },
    @{ Label = 'tools/init_discovery.py'; Import = 'from init_discovery import prepare_inputs' },
    @{ Label = 'tools/fetch_literature.py'; Import = 'from fetch_literature import search' },
    @{ Label = 'tools/research_wiki.py'; Import = 'from research_wiki import slugify' },
    @{ Label = 'tools/lint.py'; Import = 'from lint import check_missing_fields' },
    @{ Label = 'tools/list_zotero_collection.py'; Import = 'from list_zotero_collection import list_collection' },
    @{ Label = 'tools/cal_data_index.py'; Import = 'from cal_data_index import build_reports' }
)
foreach ($tool in $toolImports) {
    if (-not (Test-ToolImport -Label $tool.Label -ProjectRoot $projectRoot -VenvPython $venvPython -ImportStatement $tool.Import)) { $errors++ }
}

$tokenFromFile = (Test-Path -LiteralPath $envFile -PathType Leaf) -and (Select-String -LiteralPath $envFile -Pattern '^MINERU_API_TOKEN=.+' -Quiet)
if ($tokenFromFile -or $env:MINERU_API_TOKEN) {
    Write-Ok 'MINERU_API_TOKEN is configured for MinerU'
} else {
    Write-Warn 'MINERU_API_TOKEN not set — PDF ingest will fail until you add it'
    Write-Host "       Get a token at https://mineru.net/ and put it in $envFile"
    $warnings++
}

& uv run --python $venvPython python -c 'import mineru' *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Ok 'MinerU local backend available (optional)'
} else {
    Write-Info 'MinerU local backend not installed (optional). Enable with: uv sync --extra local'
}

Write-Host ''
Write-Host '============================================'
if ($errors -eq 0 -and $warnings -eq 0) {
    Write-Host '  Setup complete!' -ForegroundColor Green
} elseif ($errors -eq 0) {
    Write-Host "  Setup complete with $warnings warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "  Setup complete with $errors error(s) and $warnings warning(s)" -ForegroundColor Yellow
}
Write-Host '============================================'
Write-Host ''
Write-Host '  Next steps:'
Write-Host ''
Write-Host '  1. Authenticate Claude Code (if not already):'
Write-Host '     claude login'
Write-Host ''
Write-Host "  2. Set MINERU_API_TOKEN in $envFile (required for PDF ingest):"
Write-Host '     https://mineru.net/  →  create token  →  paste into .env'
Write-Host ''
Write-Host '  3. Run Python tools through uv (no need to activate the venv):'
Write-Host '     uv run python -X utf8 tools/research_wiki.py --help'
Write-Host ''
Write-Host '  4. Start Claude Code:'
Write-Host '     claude'
Write-Host ''
Write-Host '  5. Complete API key configuration (guided):'
Write-Host '     /setup'
Write-Host '     Claude Code will walk you through llm-wiki API keys — skip any you do not have yet.'
Write-Host ''
Write-Host '  6. Then initialize your wiki:'
Write-Host '     /init [your-research-topic]'
Write-Host ''
Write-Host '  For more, see README.md'
Write-Host ''

if ($errors -gt 0) { exit 1 }

# Configuration Templates

This directory contains configuration templates. Copy them to the correct locations during setup.

## Files

### `.env.example`

Environment variables for API keys. Copy to the llm-wiki user config directory:

```bash
mkdir -p ~/.config/llm-wiki
cp config/.env.example ~/.config/llm-wiki/.env
chmod 600 ~/.config/llm-wiki/.env
```

Then edit `~/.config/llm-wiki/.env` to add your API keys. See comments in the file for detailed instructions on each key.

### `settings.local.json.example`

Claude Code permission settings. Copy to `.claude/`:

```bash
mkdir -p .claude
cp config/settings.local.json.example .claude/settings.local.json
```

**What the permissions do:**

| Permission | Why it's needed |
|-----------|-----------------|
| `Bash(pip install:*)` | Install Python packages (e.g., during setup) |
| `Bash(python:*)` | Run Python tools (fetch_literature, lint, etc.) |
| `Bash(python3:*)` | Same as above, for systems where `python3` is the command |
| `Bash(cp:*)` | Copy files (e.g., templates during /init) |
| `Bash(mkdir:*)` | Create directories (e.g., wiki subdirectories) |
| `Bash(git ls-tree:*)` | List files in git (used by some tools for discovery) |

These are the **minimum permissions** for LLM-Wiki skills to function. Claude Code will prompt you for approval when a skill tries to use a tool not in this list.

**To customize:** You can add more permissions (e.g., `Bash(git add:*)` for auto-commit) or remove permissions if you want more manual control. See [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for the full permissions format.

### `paths.json.example`

Cross-platform paths that connect this code repository to an external wiki
vault, raw source directory, manuscript root, and Zotero lookup candidates. Copy it to
`config/paths.json` and fill in the profiles you use:

```bash
cp config/paths.json.example config/paths.json
```

Then edit the profile values:

```json
{
  "active_profile": "auto",
  "profiles": {
    "macos": {
      "wiki_root": "/Users/you/Documents/ResearchWiki/wiki",
      "raw_root": "/Users/you/Documents/ResearchWiki/raw",
      "paper_root": "/Users/you/Documents/ResearchWiki/papers",
      "zotero_roots": [
        "~/Library/Application Support/Zotero/Profiles/*",
        "~/Zotero"
      ]
    },
    "windows": {
      "wiki_root": "%USERPROFILE%/Documents/ResearchWiki/wiki",
      "raw_root": "%USERPROFILE%/Documents/ResearchWiki/raw",
      "paper_root": "%USERPROFILE%/Documents/ResearchWiki/papers",
      "zotero_roots": [
        "%APPDATA%/Zotero/Zotero/Profiles/*",
        "%USERPROFILE%/Zotero"
      ]
    },
    "linux": {
      "wiki_root": "~/Documents/ResearchWiki/wiki",
      "raw_root": "~/Documents/ResearchWiki/raw",
      "paper_root": "~/Documents/ResearchWiki/papers",
      "zotero_roots": [
        "~/.zotero/zotero/*",
        "~/Zotero"
      ]
    }
  }
}
```

With `"active_profile": "auto"`, tools choose `macos`, `windows`, or `linux`
from the current OS. Set `active_profile` to a concrete profile name to force
one, or set `LLM_WIKI_PATH_PROFILE` temporarily. Environment variables
`LLM_WIKI_WIKI_ROOT`, `LLM_WIKI_RAW_ROOT`, and `LLM_WIKI_PAPER_ROOT` override the selected
profile.

The legacy flat format with top-level `wiki_root`, `raw_root`, and `paper_root` is still
accepted, but the profiled format is preferred for synced multi-platform use.
Most tools read this file automatically; `tools/research_wiki.py` accepts
`@wiki` as a shortcut for the configured wiki root.

Before skill content operations, run `tools/resolve_path_alias.py` for the
aliases needed by that task. For example, `@configured` validates only the wiki
root; it does not require raw or manuscript configuration. Content aliases fail
with exit code 2 if their root is unconfigured or overlaps the code repository,
including through a symlink. Explicit environment overrides count as configuration.
The root may be created later during initialization. Project/cache aliases and
explicit file paths do not require content-root configuration; legacy low-level
path defaults are retained for migration tools and disposable test fixtures.

### Independent manuscripts

The code repository holds skills and tools; generated content belongs in the
configured external roots. `paper_root` stores author manuscripts, distinct
from literature-summary pages in `wiki_root/papers/`. It must be outside the
code repository and separate from the wiki and raw roots. There is no
repository-local fallback when `paper_root` is missing.

Each research topic has a stable directory without a date. Under it, each
manuscript version uses `YYYY-MM-DD-<purpose>` (a valid calendar date and a
lowercase slug). Multiple drafts can be created on the same day with different
purpose names or `-v2`, `-v3` suffixes:

```text
<paper_root>/
├── rmcdhf-radial-research/
│   ├── 2026-10-06-rmcdhf-research/
│   │   ├── paper.tex
│   │   ├── draft.json
│   │   ├── evidence/
│   │   ├── reviews/
│   │   └── history/
│   └── 2026-10-06-structure-v2/
│       ├── paper.tex
│       └── reviews/
└── another-research-topic/
    └── 2026-10-06-initial-draft/
```

Use these commands from the code repository:

```bash
uv run python -X utf8 tools/resolve_path_alias.py '@paper-root' --json
uv run python -X utf8 tools/paper_workspace.py create another-research-topic 2026-10-06-initial-draft
uv run python -X utf8 tools/paper_workspace.py resolve rmcdhf-radial-research 2026-10-06-rmcdhf-research
uv run python -X utf8 tools/paper_workspace.py fork rmcdhf-radial-research 2026-10-06-rmcdhf-research 2026-10-06-structure-v2
uv run python -X utf8 tools/paper_workspace.py list
uv run python -X utf8 tools/paper_workspace.py list rmcdhf-radial-research
uv run python -X utf8 tools/resolve_path_alias.py '@paper-root/rmcdhf-radial-research/2026-10-06-rmcdhf-research/paper.tex'
```

`create` starts an empty draft. `fork` copies an existing version for major
structural changes or a separate evaluation, recording its parent in
`draft.json`; it preserves the original version. Both refuse existing
destinations. `resolve` and `list` are read-only. The tool returns `paper_dir`
for the topic and `draft_dir` for the selected manuscript version.

Routine revisions retain the selected draft and source filename. Major
alternatives use sibling draft directories with their own figures, results,
bibliography checks, reviews, and history. Copied results remain inherited
evidence. `/paper-draft` accepts `--paper-id <topic-id>` and
`--draft-id <YYYY-MM-DD-slug>`; omission behavior is defined in the skill.

`zotero_roots` is used by `/ingest` when the user passes `--title` or `--doi`
without an explicit `--zotero-root`. Put each platform's likely Zotero data
directory or profile directory in that platform's profile; nonexistent paths
are ignored. Entries support `~`, Unix environment variables such as
`$HOME/Zotero`, Windows variables such as `%APPDATA%`, and glob patterns such
as `~/Library/Application Support/Zotero/Profiles/*`.

Each entry may be either a string path or an object:

```json
{
  "zotero_roots": [
    "~/Zotero",
    {
      "label": "work laptop profile",
      "path": "~/Library/Application Support/Zotero/Profiles/*",
      "enabled": true
    }
  ]
}
```

`tools/find_zotero_pdf.py` accepts both Zotero data directories containing
`zotero.sqlite` and `storage/`, and profile directories containing `prefs.js`
that points to the real data directory.

Optional richer metadata comes from Zotero Desktop's local API. Keep Zotero
Desktop open and enable local API access, then `tools/fetch_zotero_metadata.py`
can read `http://127.0.0.1:23119/api` by item key. Override the endpoint with
`ZOTERO_LOCAL_API` only when Zotero is exposed at a different local address.

Helpers:

```bash
uv run python tools/separate_wiki_repository.py --wiki-root /abs/wiki --raw-root /abs/raw
uv run python tools/clean_wiki_repository.py --target all
```

## All Done by `setup.sh`

`setup.sh` seeds API and agent settings. Configure your external content roots
in `config/paths.json` separately; it is private and is not overwritten by setup.
Runtime specifications are maintained directly in `skills/`, `AGENTS.md`, and
`CLAUDE.md`; edits take effect without a copy/sync step. Use `./setup.sh --sync-only`
(or `./setup.fish --sync-only`, `pwsh -File .\setup.ps1 -SyncOnly`) to repair agent
skill entrypoints without reinstalling dependencies or changing user API configuration.

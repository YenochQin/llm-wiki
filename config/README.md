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

These are the **minimum permissions** for ΩmegaWiki skills to function. Claude Code will prompt you for approval when a skill tries to use a tool not in this list.

**To customize:** You can add more permissions (e.g., `Bash(git add:*)` for auto-commit) or remove permissions if you want more manual control. See [Claude Code docs](https://docs.anthropic.com/en/docs/claude-code) for the full permissions format.

### `paths.json.example`

Cross-platform paths that connect this code repository to an external wiki
vault and raw source directory. Copy it to `config/paths.json` and fill in the
profiles you use:

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
      "raw_root": "/Users/you/Documents/ResearchWiki/raw"
    },
    "windows": {
      "wiki_root": "%USERPROFILE%/Documents/ResearchWiki/wiki",
      "raw_root": "%USERPROFILE%/Documents/ResearchWiki/raw"
    },
    "linux": {
      "wiki_root": "~/Documents/ResearchWiki/wiki",
      "raw_root": "~/Documents/ResearchWiki/raw"
    }
  }
}
```

With `"active_profile": "auto"`, tools choose `macos`, `windows`, or `linux`
from the current OS. Set `active_profile` to a concrete profile name to force
one, or set `LLM_WIKI_PATH_PROFILE` temporarily. Environment variables
`LLM_WIKI_WIKI_ROOT` and `LLM_WIKI_RAW_ROOT` still override the selected
profile.

The legacy flat format with top-level `wiki_root` and `raw_root` is still
accepted, but the profiled format is preferred for synced multi-platform use.
Most tools read this file automatically; `tools/research_wiki.py` accepts
`@wiki` as a shortcut for the configured wiki root.

Helpers:

```bash
uv run python tools/separate_wiki_repository.py --wiki-root /abs/wiki --raw-root /abs/raw
uv run python tools/clean_wiki_repository.py --target all
```

### `zotero-roots.json`

Cross-platform Zotero lookup candidates used by `/ingest` when the user passes
`--title`, `--doi`, or `--item-key` without an explicit `--zotero-root`.

The file is meant to be synced with the wiki. Put every machine's likely Zotero
data directory or profile directory in the `roots` list; nonexistent paths are
ignored. Entries support `~`, Unix environment variables such as
`$HOME/Zotero`, Windows variables such as `%APPDATA%`, and glob patterns such
as `~/Library/Application Support/Zotero/Profiles/*`.

Each entry may be either a string path or an object:

```json
{
  "roots": [
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

## All Done by `setup.sh`

If you ran `setup.sh`, these files are already copied to the right locations. You only need to edit `~/.config/llm-wiki/.env` if you want to add API keys.

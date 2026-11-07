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

### `paths.toml.example`

Copy `config/paths.toml.example` to `config/paths.toml` and fill in this machine's
paths. The local file is gitignored. There are exactly two configuration tables;
no operating-system detection or profile selection is used for TOML.

```toml
[wiki]
root_dir = "/Users/you/Documents/ResearchWiki"
experiment = true
paper_draft = true
beamer = false
raw = true
output = true

[zotero]
profile_dir = "/Users/you/Library/Application Support/Zotero/Profiles/example.default"
data_dir = "/Users/you/Zotero"
```

`root_dir` is the whole Obsidian vault. Knowledge always uses `root_dir/wiki`.
Every other key in `[wiki]` must be a boolean: `true` enables `root_dir/<key>`;
`false` or omission disables it. Add arbitrary lowercase directory names such as
`reading_notes = true` without changing code. Names may contain letters, digits,
underscores, and hyphens, starting with a letter; `wiki` is reserved. Paths must
be absolute on the current machine after expanding `~` and environment variables.
Use forward slashes for Windows paths, or TOML literal strings for backslashes.
Changing a boolean never moves or deletes existing files.

| Setting | Internal root / alias | Directory |
|---|---|---|
| `root_dir` | `wiki_root`, `@configured` | `<root_dir>/wiki` |
| `experiment = true` | `experiment_root`, `@experiment-root` | `<root_dir>/experiment` |
| `paper_draft = true` | `paper_root`, `@paper-root` | `<root_dir>/paper_draft` |
| `raw = true` | `raw_root`, `@raw-root` | `<root_dir>/raw` |
| `output = true` | `output_root`, `@output-root` | `<root_dir>/output` |
| `beamer = true` (or another key) | `@directory/beamer` | `<root_dir>/beamer` |

Reading configuration and resolving aliases do not create directories. Writers
create their required directories when needed. To explicitly initialize all enabled
directories, including arbitrary keys, run:

```bash
uv run python -X utf8 tools/resolve_path_alias.py --create-dirs --json
```

For read-only resolution, omit `--create-dirs`:

```bash
uv run python -X utf8 tools/resolve_path_alias.py @configured @experiment-root @paper-root
uv run python -X utf8 tools/resolve_path_alias.py '@directory/beamer/talk.tex'
```

The second example requires `beamer = true`. Disabled directories produce an
error when requested. Validate only aliases needed by the task before content
I/O; unused disabled roots do not block work. Roots must be outside the code
repository. Derived directories must remain inside `root_dir` after resolving
symlinks and must not overlap one another. Use returned absolute paths for direct
filesystem operations. No directory is moved by changing config: when replacing
older `experiments/` or `papers/` locations, migrate their contents and references
separately before expecting existing records in the new locations.

Explicit tool arguments still override `LLM_WIKI_WIKI_ROOT`,
`LLM_WIKI_EXPERIMENT_ROOT`, `LLM_WIKI_OUTPUT_ROOT`, `LLM_WIKI_RAW_ROOT`, and
`LLM_WIKI_PAPER_ROOT`, which override TOML-derived roots. The `@directory/<name>`
alias and `--create-dirs` always use the TOML directories, independent of these
legacy root overrides. Overrides do not change the vault boundary for persisted
links. Only `.toml` configuration files are accepted; JSON configurations and
OS/profile selection are not supported.

Logical graph identities such as `experiments/<slug>` and `outputs/<slug>` stay
unchanged; content helpers map them to the configured physical roots. Old
`@configured/experiments/...` and `@configured/outputs/...` aliases are rejected.

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

### Zotero directories

`[zotero].data_dir` explicitly names the directory containing `zotero.sqlite`
and `storage/`. `[zotero].profile_dir` explicitly names the profile containing
`prefs.js`, which can point to a data directory. Fill in actual paths for this
machine; no OS-specific search or glob expansion is performed for TOML. Empty
or omitted values disable that lookup source. The data directory is tried first,
then the profile; `--zotero-root` remains an explicit override. Zotero-only tools
do not require a configured wiki root.

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
in `config/paths.toml` separately; it is private and is not overwritten by setup.
Runtime specifications are maintained directly in `skills/`, `AGENTS.md`, and
`CLAUDE.md`; edits take effect without a copy/sync step. Use `./setup.sh --sync-only`
(or `./setup.fish --sync-only`, `pwsh -File .\setup.ps1 -SyncOnly`) to repair agent
skill entrypoints without reinstalling dependencies or changing user API configuration.

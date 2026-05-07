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

### `server.yaml.example`

Remote GPU server configuration for the optional Omega spillover in `omega/tools/remote.py`.
Copy it to `config/server.yaml` if you still use the remote helper:

```bash
cp omega/config/server.yaml.example config/server.yaml
```

Then edit `config/server.yaml` with your server's SSH details, GPU info, conda environment, and work directory. See comments in the file for each field.

**Only needed if you run experiments on a remote server.** Local-only users can skip this.

**Key fields:**

| Field | Required | Example |
|-------|----------|---------|
| `host` | Yes | `gpu1.cs.university.edu` |
| `user` | Yes | `researcher` |
| `work_dir` | Yes | `/home/researcher/experiments` |
| `conda.path` + `conda.env` | One of conda or env_setup | `/opt/conda` + `research` |
| `port` | No (default 22) | `2222` |
| `identity_file` | No | `~/.ssh/id_ed25519` |
| `proxy_jump` | No | `bastion.cs.edu` |

## All Done by `setup.sh`

If you ran `setup.sh`, these files are already copied to the right locations. You only need to edit `~/.config/llm-wiki/.env` if you want to add API keys.

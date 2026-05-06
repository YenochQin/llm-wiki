"""Shared environment loader for llm-wiki tools.

Loads environment variables from .env files so that API keys configured
by the user are available even when Claude Code spawns a fresh shell.

Load order (later files do NOT override earlier ones):
  1. os.environ                    (always takes precedence)
  2. ~/.config/llm-wiki/.env       (or $XDG_CONFIG_HOME/llm-wiki/.env)
  3. ~/.env                        (legacy global fallback)
  4. ./.env                        (legacy project fallback)

Usage in any tool:
    import _env  # noqa: F401  (side-effect import, loads env vars)
"""

from __future__ import annotations

import os
import pathlib

_LOADED = False


def config_env_path() -> pathlib.Path:
    """Return the user-level llm-wiki config file path."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = pathlib.Path(xdg).expanduser() if xdg else pathlib.Path.home() / ".config"
    return base / "llm-wiki" / ".env"


def load() -> None:
    """Load .env files into os.environ (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True

    for env_path in [config_env_path(), pathlib.Path.home() / ".env", pathlib.Path(".env")]:
        if not env_path.exists():
            continue
        try:
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Never override existing env vars
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            pass


# Auto-load on import
load()

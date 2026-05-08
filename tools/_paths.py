#!/usr/bin/env python3
"""Runtime path configuration for a split llm-wiki codebase and wiki vault."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("config/paths.json")


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    wiki_root: Path
    raw_root: Path
    config_path: Path
    used_config: bool


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root by walking up from start."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "tools").is_dir():
            return candidate
        if (candidate / ".git").exists() and (candidate / "tools").is_dir():
            return candidate
    return current


def expand_path(raw: str | Path, base: Path) -> Path:
    """Expand ~, environment variables, and relative paths against base."""
    text = os.path.expandvars(os.path.expanduser(str(raw)))
    path = Path(text)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_paths(
    *,
    config_path: Path | None = None,
    project_root: Path | None = None,
    wiki_root: Path | None = None,
    raw_root: Path | None = None,
) -> RuntimePaths:
    """Load runtime paths, with explicit args > env vars > config > local defaults."""
    root = (project_root or find_project_root()).resolve()
    cfg_path = expand_path(config_path or DEFAULT_CONFIG_PATH, root)
    cfg = _read_json(cfg_path)

    env_wiki = os.environ.get("LLM_WIKI_WIKI_ROOT", "").strip()
    env_raw = os.environ.get("LLM_WIKI_RAW_ROOT", "").strip()

    wiki_value = wiki_root or env_wiki or cfg.get("wiki_root") or (root / "wiki")
    raw_value = raw_root or env_raw or cfg.get("raw_root") or (root / "raw")

    return RuntimePaths(
        project_root=root,
        wiki_root=expand_path(wiki_value, root),
        raw_root=expand_path(raw_value, root),
        config_path=cfg_path,
        used_config=bool(cfg),
    )


def display_path(path: Path, project_root: Path) -> str:
    """Prefer project-relative paths for in-repo files; use absolute paths otherwise."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(project_root.resolve()))
    except ValueError:
        return str(resolved)


def write_paths_config(config_path: Path, wiki_root: Path, raw_root: Path) -> None:
    payload = {
        "wiki_root": str(wiki_root.resolve()),
        "raw_root": str(raw_root.resolve()),
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

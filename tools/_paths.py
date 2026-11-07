#!/usr/bin/env python3
"""Runtime paths for the code repository, wiki vault, sources, and manuscripts."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

DEFAULT_CONFIG_PATH = Path("config/paths.toml")


@dataclass(frozen=True)
class RuntimePaths:
    project_root: Path
    wiki_root: Path
    raw_root: Path
    config_path: Path
    used_config: bool
    paper_root: Path | None = None
    wiki_root_configured: bool = False
    raw_root_configured: bool = False
    experiment_root: Path | None = None
    output_root: Path | None = None
    root_dir: Path | None = None
    directories: dict[str, Path] = field(default_factory=dict)


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


def read_toml_config(path: Path) -> dict[str, Any]:
    """Read the machine-local two-table config without OS/profile selection."""
    if path.suffix.lower() != ".toml":
        raise ValueError(f"path configuration must be a .toml file: {path}")
    try:
        cfg = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    unknown = set(cfg) - {"wiki", "zotero"}
    if unknown:
        raise ValueError(f"unknown path configuration tables: {sorted(unknown)}")
    for table in ("wiki", "zotero"):
        if not isinstance(cfg.get(table, {}), dict):
            raise ValueError(f"[{table}] must be a table")
    wiki = cfg.get("wiki", {})
    if "root_dir" in wiki:
        _absolute_config_path(wiki["root_dir"], "wiki.root_dir")
    for name, enabled in wiki.items():
        if name == "root_dir":
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or name == "wiki":
            raise ValueError(f"invalid directory name in [wiki]: {name!r}")
        if type(enabled) is not bool:
            raise ValueError(f"wiki.{name} must be a boolean")
    zotero = cfg.get("zotero", {})
    unknown = set(zotero) - {"profile_dir", "data_dir"}
    if unknown:
        raise ValueError(f"unknown [zotero] settings: {sorted(unknown)}")
    for name, value in zotero.items():
        if value != "":
            _absolute_config_path(value, f"zotero.{name}")
    return cfg


def _absolute_config_path(value: Any, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty absolute path")
    expanded = Path(os.path.expandvars(os.path.expanduser(value)))
    if not expanded.is_absolute():
        raise ValueError(f"{name} must be an absolute path on this machine: {value}")
    return expanded.resolve()


def _toml_roots(cfg: dict[str, Any]) -> tuple[Path | None, dict[str, Path], dict[str, Path]]:
    wiki = cfg.get("wiki", {})
    if "root_dir" not in wiki:
        if any(wiki.values()):
            raise ValueError("wiki.root_dir is required when directories are enabled")
        return None, {}, {}
    root = _absolute_config_path(wiki["root_dir"], "wiki.root_dir")
    directories = {"wiki": root / "wiki"}
    directories.update({name: root / name for name, enabled in wiki.items()
                        if name != "root_dir" and enabled})
    names = {"wiki_root": "wiki", "raw_root": "raw", "paper_root": "paper_draft",
             "experiment_root": "experiment", "output_root": "output"}
    roots = {key: directories[name] for key, name in names.items() if name in directories}
    return root, directories, roots


def require_directory(paths: RuntimePaths, name: str) -> Path:
    """Resolve an enabled directory, rejecting symlinks outside the vault."""
    if name not in paths.directories or paths.root_dir is None:
        raise ValueError(f"directory {name!r} is not enabled in [wiki]")
    root = paths.root_dir.resolve()
    project = paths.project_root.resolve()
    if root.is_relative_to(project) or project.is_relative_to(root):
        raise ValueError("wiki.root_dir must be outside the code repository and must not contain it")
    target = paths.directories[name].resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError(f"directory {name!r} escapes wiki.root_dir")
    for other_name, other in paths.directories.items():
        if other_name == name:
            continue
        other = other.resolve()
        if target.is_relative_to(other) or other.is_relative_to(target):
            raise ValueError(f"directory {name!r} overlaps {other_name!r}")
    return target


def initialize_directories(paths: RuntimePaths) -> list[Path]:
    """Explicitly create configured directories; config loading stays read-only."""
    if paths.root_dir is None:
        raise ValueError("wiki.root_dir is not configured")
    targets = [require_directory(paths, name) for name in paths.directories]
    # Validate all targets before creating any directory.
    for target in targets:
        if target.exists() and not target.is_dir():
            raise ValueError(f"directory target is a file: {target}")
    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
    return targets


def load_paths(
    *,
    config_path: Path | None = None,
    project_root: Path | None = None,
    wiki_root: Path | None = None,
    raw_root: Path | None = None,
    paper_root: Path | None = None,
    experiment_root: Path | None = None,
    output_root: Path | None = None,
) -> RuntimePaths:
    """Load runtime paths, with explicit args > env vars > config > local defaults."""
    root = (project_root or find_project_root()).resolve()
    cfg_path = expand_path(config_path or DEFAULT_CONFIG_PATH, root)
    cfg = read_toml_config(cfg_path)
    root_dir, directories, configured_roots = _toml_roots(cfg)

    env_wiki = os.environ.get("LLM_WIKI_WIKI_ROOT", "").strip()
    env_raw = os.environ.get("LLM_WIKI_RAW_ROOT", "").strip()
    env_paper = os.environ.get("LLM_WIKI_PAPER_ROOT", "").strip()

    wiki_value = wiki_root or env_wiki or configured_roots.get("wiki_root")
    raw_value = raw_root or env_raw or configured_roots.get("raw_root")
    # Manuscripts never fall back to a directory in the code repository.
    paper_value = paper_root or env_paper or configured_roots.get("paper_root")
    experiment_value = (experiment_root or os.environ.get("LLM_WIKI_EXPERIMENT_ROOT", "").strip()
                        or configured_roots.get("experiment_root"))
    output_value = (output_root or os.environ.get("LLM_WIKI_OUTPUT_ROOT", "").strip()
                    or configured_roots.get("output_root"))

    return RuntimePaths(
        project_root=root,
        wiki_root=expand_path(wiki_value or root / "wiki", root),
        raw_root=expand_path(raw_value or root / "raw", root),
        config_path=cfg_path,
        used_config=bool(cfg),
        root_dir=root_dir,
        directories=directories,
        paper_root=expand_path(paper_value, root) if paper_value else None,
        wiki_root_configured=bool(wiki_value),
        raw_root_configured=bool(raw_value),
        experiment_root=expand_path(experiment_value, root) if experiment_value else None,
        output_root=expand_path(output_value, root) if output_value else None,
    )


def _validate_derived_root(paths: RuntimePaths, root: Path) -> None:
    for name, directory in paths.directories.items():
        if directory.resolve() == root:
            require_directory(paths, name)


def _require_external_root(paths: RuntimePaths, name: str) -> Path:
    """Validate a requested wiki/raw root without requiring unrelated roots."""
    if not getattr(paths, f"{name}_configured"):
        raise ValueError(
            f"{name} is not configured; set it in config/paths.toml "
            f"or LLM_WIKI_{name.upper()} (no in-repository fallback)"
        )
    root = getattr(paths, name).resolve()
    _validate_derived_root(paths, root)
    project = paths.project_root.resolve()
    if root.is_relative_to(project) or project.is_relative_to(root):
        raise ValueError(f"{name} must be outside the code repository and must not contain it")
    return root


def require_paper_root(paths: RuntimePaths) -> Path:
    """Require an external manuscript root before resolving or writing papers."""
    return require_independent_root(paths, "paper_root")


def require_independent_root(paths: RuntimePaths, name: str) -> Path:
    """Validate one requested independent root; unused roots need not be set."""
    value = getattr(paths, name)
    if value is None:
        raise ValueError(
            f"{name} is not configured; set it in config/paths.toml "
            f"or LLM_WIKI_{name.upper()} (no in-repository fallback)"
        )
    root = value.resolve()
    _validate_derived_root(paths, root)
    project = paths.project_root.resolve()
    if root.is_relative_to(project) or project.is_relative_to(root):
        raise ValueError(f"{name} must be outside the code repository and must not contain it")
    for label in ("wiki_root", "raw_root", "paper_root", "experiment_root", "output_root"):
        other = getattr(paths, label)
        if label == name or other is None:
            continue
        other = other.resolve()
        if root.is_relative_to(other) or other.is_relative_to(root):
            raise ValueError(f"{name} must be separate from {label}")
    return root


def display_path(path: Path, project_root: Path) -> str:
    """Prefer project-relative paths for in-repo files; use absolute paths otherwise."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(project_root.resolve()))
    except ValueError:
        return str(resolved)


def resolve_runtime_path(
    value: str | Path | None,
    paths: RuntimePaths,
    *,
    role: str,
    require_external: bool = False,
) -> Path | None:
    """Resolve paths; strict callers reject missing or in-repository content roots.

    The default retains legacy wiki/raw resolution for migration tools and test
    fixtures. Skills use the strict resolve_path_alias.py CLI before content I/O.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise ValueError(f"{role} is empty; pass an explicit path or configured alias")

    aliases = {
        "@project-root": paths.project_root,
        "@project": paths.project_root,
        "@wiki-root": paths.wiki_root,
        "@wiki": paths.wiki_root,
        "@configured": paths.wiki_root,
        "@configured-wiki": paths.wiki_root,
        "@raw-root": paths.raw_root,
        "@raw": paths.raw_root,
        "@configured-raw": paths.raw_root,
        "@configured-sources": paths.wiki_root / "sources",
        "@wiki-sources": paths.wiki_root / "sources",
        "@configured-sources-papers": paths.wiki_root / "sources" / "papers",
        "@wiki-sources-papers": paths.wiki_root / "sources" / "papers",
        "@mineru-cache": paths.project_root / ".checkpoints" / "mineru-cache",
        "@project-checkpoints-mineru-cache": paths.project_root / ".checkpoints" / "mineru-cache",
    }
    if text.startswith("@"):
        alias, separator, suffix = text.replace("\\", "/").partition("/")
        content_root = None
        if alias == "@directory":
            name, separator, suffix = suffix.partition("/")
            base = require_directory(paths, name)
        elif alias in {"@paper-root", "@configured-papers"}:
            base = require_paper_root(paths)
        elif alias in {"@experiment-root", "@output-root"}:
            base = require_independent_root(paths, alias[1:].replace("-", "_"))
        elif alias in aliases:
            base = aliases[alias].resolve()
            if require_external:
                if alias in {
                    "@wiki-root", "@wiki", "@configured", "@configured-wiki",
                    "@configured-sources", "@wiki-sources",
                    "@configured-sources-papers", "@wiki-sources-papers",
                }:
                    content_root = _require_external_root(paths, "wiki_root")
                elif alias in {"@raw-root", "@raw", "@configured-raw"}:
                    content_root = _require_external_root(paths, "raw_root")
            if alias in {"@wiki-root", "@wiki", "@configured", "@configured-wiki"}:
                moved = {"experiments": "@experiment-root", "outputs": "@output-root"}
                if suffix.split("/", 1)[0] in moved:
                    raise ValueError(f"{text} uses a retired wiki subdirectory; use "
                                     f"{moved[suffix.split('/', 1)[0]]} instead")
        else:
            raise ValueError(f"unknown runtime path alias: {alias}")
        target = (base / suffix).resolve() if separator else base
        if not target.is_relative_to(base):
            raise ValueError(f"{role} escapes runtime root {alias}: {text}")
        if content_root is not None and not target.is_relative_to(content_root):
            raise ValueError(f"{role} escapes configured content root: {text}")
        return target
    return expand_path(text, paths.project_root)


def write_paths_config(config_path: Path, wiki_root: Path, raw_root: Path) -> None:
    payload = toml_paths_payload(config_path, wiki_root, raw_root)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(payload, encoding="utf-8")


def toml_paths_payload(config_path: Path, wiki_root: Path, raw_root: Path) -> str:
    """Prepare config before migration I/O; reject layouts TOML cannot represent."""
    wiki, raw = wiki_root.resolve(), raw_root.resolve()
    if wiki.name != "wiki" or raw != wiki.parent / "raw":
        raise ValueError("TOML requires sibling <root_dir>/wiki and <root_dir>/raw destinations")
    cfg = read_toml_config(config_path)
    tables = {"wiki": {**cfg.get("wiki", {}), "root_dir": str(wiki.parent), "raw": True},
              "zotero": cfg.get("zotero", {})}
    lines = []
    for name, values in tables.items():
        lines.append(f"[{name}]")
        for key, value in values.items():
            encoded = str(value).lower() if type(value) is bool else json.dumps(value, ensure_ascii=False)
            lines.append(f"{key} = {encoded}")
        lines.append("")
    return "\n".join(lines)

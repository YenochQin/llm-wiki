#!/usr/bin/env python3
"""Runtime paths for the code repository, wiki vault, sources, and manuscripts."""

from __future__ import annotations

import json
import os
import platform
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
    profile: str
    paper_root: Path | None = None
    wiki_root_configured: bool = False
    raw_root_configured: bool = False
    experiment_root: Path | None = None
    output_root: Path | None = None


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


def current_platform_profile() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return system or "unknown"


def _select_profile(cfg: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    profiles = cfg.get("profiles")
    if not isinstance(profiles, dict):
        return "legacy", cfg

    requested = os.environ.get("LLM_WIKI_PATH_PROFILE", "").strip()
    active = requested or str(cfg.get("active_profile") or "auto")
    selected = current_platform_profile() if active == "auto" else active
    profile_cfg = profiles.get(selected)

    if not isinstance(profile_cfg, dict):
        fallback = cfg.get("fallback_profile")
        if isinstance(fallback, str) and isinstance(profiles.get(fallback), dict):
            selected = fallback
            profile_cfg = profiles[fallback]
        else:
            profile_cfg = {}
    return selected, profile_cfg


def _looks_like_default_zotero_root(entry: Any) -> bool:
    if isinstance(entry, str):
        return entry.strip() in {"~/Zotero"}
    if not isinstance(entry, dict):
        return False
    label = str(entry.get("label") or "").strip().lower()
    path = str(entry.get("path") or "").strip()
    return (
        "default" in label or "profile candidates" in label
    ) and path in {
        "~/Zotero",
        "~/.zotero/zotero/*",
        "~/Library/Application Support/Zotero/Profiles/*",
        "%APPDATA%/Zotero/Zotero/Profiles/*",
        "%USERPROFILE%/Zotero",
    }


def _custom_zotero_roots(profile_cfg: dict[str, Any]) -> list[Any]:
    raw_entries = profile_cfg.get("zotero_roots")
    if not isinstance(raw_entries, list):
        return []
    custom_entries = [entry for entry in raw_entries if not _looks_like_default_zotero_root(entry)]
    return custom_entries


def _preserved_zotero_roots(
    profiles: dict[str, Any], profile_name: str, profile_cfg: dict[str, Any]
) -> list[Any] | None:
    current_custom = _custom_zotero_roots(profile_cfg)
    if current_custom:
        return current_custom

    for other_name, other_cfg in profiles.items():
        if other_name == profile_name or not isinstance(other_cfg, dict):
            continue
        other_custom = _custom_zotero_roots(other_cfg)
        if other_custom:
            return other_custom
    return None


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
    cfg = _read_json(cfg_path)

    profile_name, profile_cfg = _select_profile(cfg)

    env_wiki = os.environ.get("LLM_WIKI_WIKI_ROOT", "").strip()
    env_raw = os.environ.get("LLM_WIKI_RAW_ROOT", "").strip()
    env_paper = os.environ.get("LLM_WIKI_PAPER_ROOT", "").strip()

    wiki_value = wiki_root or env_wiki or profile_cfg.get("wiki_root") or cfg.get("wiki_root")
    raw_value = raw_root or env_raw or profile_cfg.get("raw_root") or cfg.get("raw_root")
    # Manuscripts never fall back to a directory in the code repository.
    paper_value = paper_root or env_paper or profile_cfg.get("paper_root") or cfg.get("paper_root")
    experiment_value = (experiment_root or os.environ.get("LLM_WIKI_EXPERIMENT_ROOT", "").strip()
                        or profile_cfg.get("experiment_root") or cfg.get("experiment_root"))
    output_value = (output_root or os.environ.get("LLM_WIKI_OUTPUT_ROOT", "").strip()
                    or profile_cfg.get("output_root") or cfg.get("output_root"))

    return RuntimePaths(
        project_root=root,
        wiki_root=expand_path(wiki_value or root / "wiki", root),
        raw_root=expand_path(raw_value or root / "raw", root),
        config_path=cfg_path,
        used_config=bool(cfg),
        profile=profile_name,
        paper_root=expand_path(paper_value, root) if paper_value else None,
        wiki_root_configured=bool(wiki_value),
        raw_root_configured=bool(raw_value),
        experiment_root=expand_path(experiment_value, root) if experiment_value else None,
        output_root=expand_path(output_value, root) if output_value else None,
    )


def _require_external_root(paths: RuntimePaths, name: str) -> Path:
    """Validate a requested wiki/raw root without requiring unrelated roots."""
    if not getattr(paths, f"{name}_configured"):
        raise ValueError(
            f"{name} is not configured; set it in config/paths.json "
            f"or LLM_WIKI_{name.upper()} (no in-repository fallback)"
        )
    root = getattr(paths, name).resolve()
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
            f"{name} is not configured; set it in config/paths.json "
            f"or LLM_WIKI_{name.upper()} (no in-repository fallback)"
        )
    root = value.resolve()
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
        if alias in {"@paper-root", "@configured-papers"}:
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
    existing = _read_json(config_path)
    profiles = existing.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}

    profile_name = current_platform_profile()
    profile_cfg = profiles.get(profile_name)
    if not isinstance(profile_cfg, dict):
        profile_cfg = {}
    preserved_zotero_roots = _preserved_zotero_roots(profiles, profile_name, profile_cfg)
    profile_cfg = {
        **profile_cfg,
        "wiki_root": str(wiki_root.resolve()),
        "raw_root": str(raw_root.resolve()),
    }
    if preserved_zotero_roots is not None:
        profile_cfg["zotero_roots"] = preserved_zotero_roots
    profiles[profile_name] = profile_cfg

    payload = {
        **existing,
        "active_profile": existing.get("active_profile") or profile_name,
        "profiles": profiles,
    }
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

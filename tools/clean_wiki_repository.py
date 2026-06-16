#!/usr/bin/env python3
"""Clean local wiki vault data from the code repository after path separation.

This is a repository cleanup helper, not a wiki content reset. It removes the
in-repo `wiki/` and/or `raw/` directories after you have configured external
absolute paths in `config/paths.json`.

Default mode is dry-run. Pass --yes to modify files.

Purpose:
    Remove stale in-repository vault copies once the active wiki/raw roots live
    outside the code repository.

When to use:
    Use after `separate_wiki_repository.py` has written external absolute paths
    to `config/paths.json` and you have confirmed the external vault works.

Writes:
    Deletes only the selected in-repo `wiki/` and/or `raw/` directories when
    --yes is provided. The configured external vault is never deleted.

Usage:
    uv run python -X utf8 tools/clean_wiki_repository.py
    uv run python -X utf8 tools/clean_wiki_repository.py --target wiki
    uv run python -X utf8 tools/clean_wiki_repository.py --target all --yes
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, display_path, load_paths


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _check_external_config(paths) -> list[str]:
    problems: list[str] = []
    local_wiki = paths.project_root / "wiki"
    local_raw = paths.project_root / "raw"
    if paths.wiki_root == local_wiki.resolve():
        problems.append("wiki_root still points to the in-repo wiki/ directory")
    if paths.raw_root == local_raw.resolve():
        problems.append("raw_root still points to the in-repo raw/ directory")
    if _is_inside(paths.wiki_root, paths.project_root):
        problems.append(f"wiki_root is still inside the code repository: {paths.wiki_root}")
    if _is_inside(paths.raw_root, paths.project_root):
        problems.append(f"raw_root is still inside the code repository: {paths.raw_root}")
    if not paths.wiki_root.exists():
        problems.append(f"wiki_root does not exist: {paths.wiki_root}")
    if not paths.raw_root.exists():
        problems.append(f"raw_root does not exist: {paths.raw_root}")
    return problems


def build_plan(paths, targets: list[str]) -> dict:
    delete_paths: list[str] = []
    if "wiki" in targets and (paths.project_root / "wiki").exists():
        delete_paths.append(display_path(paths.project_root / "wiki", paths.project_root))
    if "raw" in targets and (paths.project_root / "raw").exists():
        delete_paths.append(display_path(paths.project_root / "raw", paths.project_root))
    return {
        "project_root": str(paths.project_root),
        "config_path": display_path(paths.config_path, paths.project_root),
        "active_profile": paths.profile,
        "configured_wiki_root": str(paths.wiki_root),
        "configured_raw_root": str(paths.raw_root),
        "targets": targets,
        "delete_paths": delete_paths,
    }


def execute(paths, targets: list[str]) -> dict:
    deleted: list[str] = []
    for target in targets:
        path = paths.project_root / target
        if not path.exists():
            continue
        shutil.rmtree(path)
        deleted.append(display_path(path, paths.project_root))
    return {"status": "ok", "deleted": deleted}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--target", choices=("wiki", "raw", "all"), default="all",
                        help="Which in-repo directories to remove after separation.")
    parser.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path,
                        help="Path config JSON (default: config/paths.json).")
    parser.add_argument("--project-root", default=None, type=Path,
                        help="Code repository root (default: auto-detect).")
    parser.add_argument("--allow-missing-config", action="store_true",
                        help="Permit cleanup even when config/paths.json is missing or still local.")
    parser.add_argument("--yes", action="store_true",
                        help="Apply the plan. Without this flag, only prints the plan.")
    args = parser.parse_args()

    paths = load_paths(config_path=args.paths_config, project_root=args.project_root)
    targets = ["wiki", "raw"] if args.target == "all" else [args.target]
    problems = _check_external_config(paths)
    plan = build_plan(paths, targets)

    if problems and not args.allow_missing_config:
        print(json.dumps({
            "status": "blocked",
            "message": "Refusing to remove in-repo wiki/raw until external paths are configured.",
            "problems": problems,
            "plan": plan,
        }, ensure_ascii=False, indent=2))
        return

    if not args.yes:
        print(json.dumps({"status": "plan", "warnings": problems, **plan},
                         ensure_ascii=False, indent=2))
        return

    try:
        result = execute(paths, targets)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc), "plan": plan},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

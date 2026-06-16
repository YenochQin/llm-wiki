#!/usr/bin/env python3
"""Separate the llm-wiki code repository from the user wiki vault.

The script copies or moves the current in-repo `wiki/` and `raw/` directories to
absolute external paths, then writes `config/paths.json` so tools can reconnect
the code repository to the external vault.

Default mode is a dry-run plan. Pass --yes to modify files.

Purpose:
    Split code and personal wiki data so the repository can stay lightweight
    while tools continue to resolve the active vault through config/paths.json.

Inputs:
    Existing in-repo wiki/raw directories plus absolute destination paths.

Writes:
    Only with --yes: copies or moves wiki/raw to the requested destinations and
    writes config/paths.json.

Usage:
    uv run python -X utf8 tools/separate_wiki_repository.py --wiki-root /abs/wiki --raw-root /abs/raw
    uv run python -X utf8 tools/separate_wiki_repository.py --wiki-root /abs/wiki --raw-root /abs/raw --mode copy --yes
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, display_path, expand_path, find_project_root, write_paths_config


def _nonempty(path: Path) -> bool:
    return path.exists() and any(path.iterdir())


def _copy_tree(src: Path, dst: Path, merge: bool) -> None:
    if not src.exists():
        return
    if dst.exists() and _nonempty(dst) and not merge:
        raise FileExistsError(f"destination exists and is non-empty: {dst}")
    shutil.copytree(src, dst, dirs_exist_ok=merge)


def build_plan(project_root: Path, wiki_root: Path, raw_root: Path, config_path: Path, mode: str, merge: bool) -> dict:
    local_wiki = project_root / "wiki"
    local_raw = project_root / "raw"
    return {
        "project_root": str(project_root),
        "mode": mode,
        "merge": merge,
        "config_path": display_path(config_path, project_root),
        "write_config": {
            "wiki_root": str(wiki_root),
            "raw_root": str(raw_root),
        },
        "copy_or_move": [
            {
                "source": display_path(local_wiki, project_root),
                "destination": str(wiki_root),
                "exists": local_wiki.exists(),
            },
            {
                "source": display_path(local_raw, project_root),
                "destination": str(raw_root),
                "exists": local_raw.exists(),
            },
        ],
        "remove_local_after_copy": mode == "move",
    }


def execute(project_root: Path, wiki_root: Path, raw_root: Path, config_path: Path, mode: str, merge: bool) -> dict:
    local_wiki = project_root / "wiki"
    local_raw = project_root / "raw"

    if wiki_root == local_wiki.resolve() or raw_root == local_raw.resolve():
        raise ValueError("destination paths must be outside the current in-repo wiki/raw paths")
    for destination in (wiki_root, raw_root):
        try:
            destination.relative_to(project_root.resolve())
        except ValueError:
            pass
        else:
            raise ValueError(f"destination must be outside the code repository: {destination}")
    if wiki_root == raw_root or wiki_root in raw_root.parents or raw_root in wiki_root.parents:
        raise ValueError("wiki_root and raw_root must be separate directories, not nested inside each other")

    changed: list[str] = []
    _copy_tree(local_wiki, wiki_root, merge=merge)
    changed.append(f"copied {display_path(local_wiki, project_root)} -> {wiki_root}")
    _copy_tree(local_raw, raw_root, merge=merge)
    changed.append(f"copied {display_path(local_raw, project_root)} -> {raw_root}")

    write_paths_config(config_path, wiki_root, raw_root)
    changed.append(f"wrote {display_path(config_path, project_root)}")

    if mode == "move":
        if local_wiki.exists():
            shutil.rmtree(local_wiki)
            changed.append(f"removed {display_path(local_wiki, project_root)}")
        if local_raw.exists():
            shutil.rmtree(local_raw)
            changed.append(f"removed {display_path(local_raw, project_root)}")

    return {"status": "ok", "changed": changed}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wiki-root", required=True, type=Path,
                        help="Absolute destination for the wiki vault directory.")
    parser.add_argument("--raw-root", required=True, type=Path,
                        help="Absolute destination for raw source files.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, type=Path,
                        help="Path config to write (default: config/paths.json).")
    parser.add_argument("--project-root", default=None, type=Path,
                        help="Code repository root (default: auto-detect).")
    parser.add_argument("--mode", choices=("copy", "move"), default="copy",
                        help="copy keeps in-repo wiki/raw; move removes them after successful copy.")
    parser.add_argument("--merge", action="store_true",
                        help="Allow copying into existing non-empty destination directories.")
    parser.add_argument("--yes", action="store_true",
                        help="Apply the plan. Without this flag, only prints the plan.")
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)
    wiki_root = expand_path(args.wiki_root, project_root)
    raw_root = expand_path(args.raw_root, project_root)
    config_path = expand_path(args.config, project_root)

    plan = build_plan(project_root, wiki_root, raw_root, config_path, args.mode, args.merge)
    if not args.yes:
        print(json.dumps({"status": "plan", **plan}, ensure_ascii=False, indent=2))
        return

    try:
        result = execute(project_root, wiki_root, raw_root, config_path, args.mode, args.merge)
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc), "plan": plan},
                         ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

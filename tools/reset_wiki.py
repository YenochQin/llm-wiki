#!/usr/bin/env python3
"""Reset wiki state to a clean scaffold (used by /reset skill).

Scopes:
    wiki         delete all .md content under wiki/<entity>/, wiki/outputs/,
                 wiki/sources/, wiki/index.md, wiki/log.md, and wiki/graph/ files.
                 Preserves .gitkeep and wiki/CLAUDE.md.
    raw          delete all files under raw/<sub>/ except .gitkeep; does not
                 delete vault-visible copies under wiki/sources/.
    log          reset wiki/log.md to empty header.
    checkpoints  call `research_wiki.py checkpoint-clear` to drop batch state.
    all          all of the above.

Usage:
    python3 tools/reset_wiki.py --scope wiki --yes
    python3 tools/reset_wiki.py --scope all --dry-run

Without --yes the tool prints the plan and exits without touching the filesystem.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from _paths import DEFAULT_CONFIG_PATH, display_path, load_paths

ENTITY_DIRS = [
    "papers", "concepts", "topics", "people",
    "ideas", "experiments", "claims", "Summary",
    "foundations",
]
# Keep raw/prepared/ and raw/tmp/ here as legacy cleanup targets so older
# worktrees can still be reset cleanly. New vault-visible source sidecars live
# under wiki/sources/ and are cleaned by the wiki scope.
RAW_SUBDIRS = ["papers", "discovered", "prepared", "tmp", "notes", "web"]
ALL_SCOPES = ["wiki", "raw", "log", "checkpoints"]

INDEX_TEMPLATE = "# Wiki Index\n\n" + "\n".join(f"{e}:" for e in ENTITY_DIRS) + "\n"
LOG_TEMPLATE = "# OmegaWiki Log\n\n"
GRAPH_FILES = ["edges.jsonl", "citations.jsonl", "context_brief.md", "open_questions.md"]


def _list_md(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.glob("*.md") if p.is_file()]


def _list_raw(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.iterdir() if p.name != ".gitkeep"]


def _list_source_entries(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return [p for p in directory.iterdir() if p.name != ".gitkeep"]


def _show(path: Path, project_root: Path) -> str:
    return display_path(path, project_root)


def plan(project_root: Path, wiki_root: Path, raw_root: Path, scopes: list[str]) -> dict:
    """Return a structured plan of what will be deleted/reset."""
    p: dict = {
        "scopes": scopes,
        "wiki_root": _show(wiki_root, project_root),
        "raw_root": _show(raw_root, project_root),
        "delete_files": [],
        "reset_files": [],
        "actions": [],
    }
    wiki = wiki_root

    if "wiki" in scopes:
        for entity in ENTITY_DIRS:
            for f in _list_md(wiki / entity):
                p["delete_files"].append(_show(f, project_root))
        for f in _list_md(wiki / "outputs"):
            p["delete_files"].append(_show(f, project_root))
        for f in _list_source_entries(wiki / "sources"):
            p["delete_files"].append(_show(f, project_root))
        # Scaffold files — deleted, not reset (init recreates them)
        if (wiki / "index.md").exists():
            p["delete_files"].append(_show(wiki / "index.md", project_root))
        if (wiki / "log.md").exists():
            p["delete_files"].append(_show(wiki / "log.md", project_root))
        for gf in GRAPH_FILES:
            gf_path = wiki / "graph" / gf
            if gf_path.exists():
                p["delete_files"].append(_show(gf_path, project_root))

    if "raw" in scopes:
        for sub in RAW_SUBDIRS:
            for f in _list_raw(raw_root / sub):
                p["delete_files"].append(_show(f, project_root))

    if "log" in scopes and "wiki" not in scopes:
        p["reset_files"].append(_show(wiki / "log.md", project_root))

    if "checkpoints" in scopes:
        p["actions"].append("research_wiki.py checkpoint-clear")

    return p


def execute(project_root: Path, wiki_root: Path, raw_root: Path, scopes: list[str]) -> dict:
    """Apply the plan. Returns counts of what was actually changed."""
    deleted = 0
    reset = 0
    wiki = wiki_root

    if "wiki" in scopes:
        for entity in ENTITY_DIRS + ["outputs"]:
            for f in _list_md(wiki / entity):
                f.unlink()
                deleted += 1
            # Ensure .gitkeep exists so the directory survives commits
            keep = wiki / entity / ".gitkeep"
            if not keep.parent.exists():
                keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.touch()
        # Delete scaffold files (init recreates them from scratch)
        for scaffold in ["index.md", "log.md"]:
            sp = wiki / scaffold
            if sp.exists():
                sp.unlink()
                deleted += 1
        graph = wiki / "graph"
        if graph.exists():
            for gf in GRAPH_FILES:
                gfp = graph / gf
                if gfp.exists():
                    gfp.unlink()
                    deleted += 1
        sources = wiki / "sources"
        for f in _list_source_entries(sources):
            if f.is_dir():
                shutil.rmtree(f)
            else:
                f.unlink()
            deleted += 1
        for sub in ["papers", "notes", "web"]:
            keep = sources / sub / ".gitkeep"
            keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.touch()

    if "raw" in scopes:
        for sub in RAW_SUBDIRS:
            for f in _list_raw(raw_root / sub):
                if f.is_dir():
                    shutil.rmtree(f)
                else:
                    f.unlink()
                deleted += 1
            keep = raw_root / sub / ".gitkeep"
            if not keep.parent.exists():
                keep.parent.mkdir(parents=True, exist_ok=True)
            if not keep.exists():
                keep.touch()

    if "log" in scopes and "wiki" not in scopes:
        # Standalone log scope: reset to empty header
        (wiki / "log.md").write_text(LOG_TEMPLATE, encoding="utf-8")
        reset += 1

    if "checkpoints" in scopes:
        cp_dir = wiki / ".checkpoints"
        if cp_dir.exists():
            for cp_file in cp_dir.glob("*.json"):
                cp_file.unlink()
                deleted += 1

    return {"deleted_files": deleted, "reset_files": reset}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scope", required=True,
                   help="Comma-separated list, or one of: wiki, raw, log, checkpoints, all")
    p.add_argument("--project-root", default=None, type=Path, help="Project root (default: auto-detect)")
    p.add_argument("--wiki-root", default=None, type=Path, help="Wiki vault root (default: config/paths.json or ./wiki)")
    p.add_argument("--raw-root", default=None, type=Path, help="Raw source root (default: config/paths.json or ./raw)")
    p.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path, help="Path config JSON")
    p.add_argument("--yes", action="store_true", help="Apply changes (default: dry-run plan only)")
    p.add_argument("--dry-run", action="store_true", help="Print plan and exit (default behavior)")
    args = p.parse_args()

    if args.scope == "all":
        scopes = list(ALL_SCOPES)
    else:
        scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
        for s in scopes:
            if s not in ALL_SCOPES:
                print(json.dumps({"status": "error",
                                  "message": f"unknown scope: {s}",
                                  "valid": ALL_SCOPES}))
                sys.exit(1)

    paths = load_paths(
        config_path=args.paths_config,
        project_root=args.project_root,
        wiki_root=args.wiki_root,
        raw_root=args.raw_root,
    )
    root = paths.project_root
    the_plan = plan(root, paths.wiki_root, paths.raw_root, scopes)

    if not args.yes or args.dry_run:
        print(json.dumps({
            "status": "dry_run",
            "changed": False,
            "message": "No files were changed. Re-run with --yes to apply this reset.",
            **the_plan,
        }, ensure_ascii=False, indent=2))
        return

    result = execute(root, paths.wiki_root, paths.raw_root, scopes)
    print(json.dumps({"status": "ok", "scopes": scopes, **result}, ensure_ascii=False))


if __name__ == "__main__":
    main()

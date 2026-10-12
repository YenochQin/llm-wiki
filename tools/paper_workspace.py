#!/usr/bin/env python3
"""Manage research topics and independent manuscript versions under paper_root.

Usage (from the code repository):
    uv run python -X utf8 tools/paper_workspace.py create my-research 2026-10-06-first-draft
    uv run python -X utf8 tools/paper_workspace.py resolve my-research 2026-10-06-first-draft
    uv run python -X utf8 tools/paper_workspace.py fork my-research 2026-10-06-first-draft 2026-10-06-restructure
    uv run python -X utf8 tools/paper_workspace.py list [my-research]

Create and fork refuse existing destinations. Resolve and list are read-only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, RuntimePaths, load_paths, require_paper_root


def paper_directory(paths: RuntimePaths, paper_id: str) -> Path:
    """Resolve a stable, undated research-topic directory."""
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", paper_id) or len(paper_id) > 96:
        raise ValueError("paper-id must be 1–96 lowercase letters/digits separated by hyphens")
    if re.search(r"(?:^|-)\d{4}-\d{2}-\d{2}(?:-|$)", paper_id):
        raise ValueError("paper-id is a stable research topic; put the date in draft-id instead")
    root = require_paper_root(paths)
    candidate = root / paper_id
    if candidate.is_symlink():
        raise ValueError("paper directory must not be a symbolic link")
    directory = candidate.resolve()
    if not directory.is_relative_to(root) or directory == root:
        raise ValueError("paper directory escapes paper_root")
    return directory


def draft_directory(paths: RuntimePaths, paper_id: str, draft_id: str) -> Path:
    """Resolve one dated manuscript version within its research topic."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*", draft_id) or len(draft_id) > 120:
        raise ValueError("draft-id must be YYYY-MM-DD-<slug> (maximum 120 characters)")
    try:
        date.fromisoformat(draft_id[:10])
    except ValueError as exc:
        raise ValueError("draft-id must start with a valid calendar date") from exc
    paper = paper_directory(paths, paper_id)
    candidate = paper / draft_id
    if candidate.is_symlink():
        raise ValueError("draft directory must not be a symbolic link")
    directory = candidate.resolve()
    if not directory.is_relative_to(paper) or directory == paper:
        raise ValueError("draft directory escapes its research topic")
    return directory


def _write_metadata(directory: Path, paper_id: str, draft_id: str, *, parent_draft_id: str | None = None) -> None:
    metadata = {
        "paper_id": paper_id,
        "draft_id": draft_id,
        "parent_draft_id": parent_draft_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (directory / "draft.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def create_workspace(paths: RuntimePaths, paper_id: str, draft_id: str) -> Path:
    directory = draft_directory(paths, paper_id, draft_id)
    directory.mkdir(parents=True, exist_ok=False)
    for name in ("sections", "figures", "tables", "evidence", "reviews", "history"):
        (directory / name).mkdir()
    _write_metadata(directory, paper_id, draft_id)
    return directory


def resolve_workspace(paths: RuntimePaths, paper_id: str, draft_id: str) -> Path:
    directory = draft_directory(paths, paper_id, draft_id)
    if not directory.is_dir():
        raise FileNotFoundError(f"manuscript version does not exist: {directory}")
    return directory


def fork_workspace(paths: RuntimePaths, paper_id: str, source_draft_id: str, draft_id: str) -> Path:
    """Copy a version for structural revisions, preserving the original."""
    source = resolve_workspace(paths, paper_id, source_draft_id)
    directory = draft_directory(paths, paper_id, draft_id)
    if directory.exists():
        raise FileExistsError(f"manuscript version already exists: {directory}")
    # Do not copy files from outside the selected bundle through symbolic links.
    for item in source.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"cannot fork a bundle containing a symbolic link: {item}")
    shutil.copytree(source, directory)
    _write_metadata(directory, paper_id, draft_id, parent_draft_id=source_draft_id)
    return directory


def list_workspaces(paths: RuntimePaths, paper_id: str | None = None) -> list[dict[str, str]]:
    root = require_paper_root(paths)
    if not root.exists():
        return []
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    papers = [paper_directory(paths, paper_id)] if paper_id is not None else sorted(root.iterdir())
    results = []
    for paper in papers:
        if paper.is_symlink() or not paper.is_dir():
            continue
        try:
            paper_directory(paths, paper.name)
        except ValueError:
            continue
        for draft in sorted(paper.iterdir()):
            if draft.is_symlink() or not draft.is_dir():
                continue
            try:
                directory = draft_directory(paths, paper.name, draft.name)
            except ValueError:
                continue
            results.append({"paper_id": paper.name, "draft_id": draft.name, "draft_dir": str(directory)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("create", "resolve", "fork", "list"))
    parser.add_argument("paper_id", nargs="?")
    parser.add_argument("draft_id", nargs="?")
    parser.add_argument("new_draft_id", nargs="?", help="Destination draft-id for fork")
    parser.add_argument("--paths-config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    if args.command == "list":
        if args.draft_id is not None or args.new_draft_id is not None:
            parser.error("list takes at most one paper-id")
    elif args.paper_id is None or args.draft_id is None:
        parser.error("create/resolve/fork require a paper-id and draft-id")
    elif (args.command == "fork") != (args.new_draft_id is not None):
        parser.error("only fork requires a third id (destination draft-id)")
    try:
        paths = load_paths(config_path=args.paths_config)
        if args.command == "list":
            payload = {"status": "ok", "drafts": list_workspaces(paths, args.paper_id)}
        else:
            draft_id = args.new_draft_id if args.command == "fork" else args.draft_id
            if args.command == "fork":
                directory = fork_workspace(paths, args.paper_id, args.draft_id, draft_id)
            else:
                operation = create_workspace if args.command == "create" else resolve_workspace
                directory = operation(paths, args.paper_id, draft_id)
            payload = {
                "status": "ok", "paper_id": args.paper_id, "draft_id": draft_id,
                "paper_dir": str(paper_directory(paths, args.paper_id)), "draft_dir": str(directory),
            }
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(2) from exc
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

"""Scan live wiki pages without treating sync-conflict copies as entities."""

from pathlib import Path
import sys
from typing import Iterable, Iterator


def is_sync_conflict(path: Path) -> bool:
    return "nsconflict" in path.name.casefold()


def exclude_sync_conflicts(paths: Iterable[Path]) -> Iterator[Path]:
    for path in paths:
        if is_sync_conflict(path):
            print(f"warning: sync-conflict: skipped {path}; reconcile the copy before indexing", file=sys.stderr)
        else:
            yield path


def markdown_pages(directory: Path) -> Iterator[Path]:
    yield from exclude_sync_conflicts(sorted(p for p in directory.glob("*.md") if p.is_file()))


def sync_conflict_files(wiki_dir: Path) -> list[Path]:
    return sorted(p for p in wiki_dir.rglob("*") if p.is_file() and is_sync_conflict(p))

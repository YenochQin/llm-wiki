"""Resolve stable content identities independently of their physical roots.

Graph ids stay experiments/<slug>; the configured vault stores those pages in
experiment_root. Explicit standalone legacy trees remain usable for migrations
and disposable fixtures, without borrowing a different vault's configured roots.
"""

from contextvars import ContextVar, Token
from pathlib import Path
from typing import Iterator

from _paths import RuntimePaths, load_paths, require_independent_root

_runtime: ContextVar[RuntimePaths | None] = ContextVar("content_paths", default=None)
INDEPENDENT_DIRS = {"experiments": "experiment_root", "outputs": "output_root"}


def configure_content_paths(paths: RuntimePaths) -> Token:
    """Bind the CLI's selected configuration for the lifetime of its invocation."""
    return _runtime.set(paths)


def content_directory(wiki_root: Path, kind: str) -> Path:
    wiki_root = wiki_root.resolve()
    if kind not in INDEPENDENT_DIRS:
        return wiki_root / kind
    paths = _runtime.get() or load_paths()
    if wiki_root == paths.wiki_root.resolve() and paths.wiki_root_configured:
        return require_independent_root(paths, INDEPENDENT_DIRS[kind])
    return wiki_root / kind


def content_path(wiki_root: Path, identity: str) -> Path:
    """Resolve a logical relative filename, rejecting traversal and symlink escape."""
    logical = Path(identity)
    if logical.is_absolute() or ".." in logical.parts or "\\" in identity:
        raise ValueError(f"Invalid content identity: {identity}")
    if not logical.parts:
        raise ValueError("Empty content identity")
    base = content_directory(wiki_root, logical.parts[0])
    target = base.joinpath(*logical.parts[1:]).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"Content identity escapes its root: {identity}")
    return target


def content_relative(path: Path, wiki_root: Path) -> str:
    """Display a physical path as a stable logical filename."""
    path = path.resolve()
    wiki_root = wiki_root.resolve()
    if path.is_relative_to(wiki_root):
        return path.relative_to(wiki_root).as_posix()
    paths = active_content_paths()
    for kind, name in INDEPENDENT_DIRS.items():
        if wiki_root == paths.wiki_root.resolve() and paths.wiki_root_configured:
            candidate = getattr(paths, name)
            if candidate is None or not path.is_relative_to(candidate.resolve()):
                continue
        base = content_directory(wiki_root, kind)
        if path.is_relative_to(base):
            return f"{kind}/{path.relative_to(base).as_posix()}"
    raise ValueError(f"Path is outside the configured content roots: {path}")


def content_kind(path: Path, wiki_root: Path) -> str:
    return content_relative(path, wiki_root).split("/", 1)[0]


def content_roots(wiki_root: Path) -> list[Path]:
    """Roots for cross-content reference maintenance (never raw or manuscripts)."""
    wiki_root = wiki_root.resolve()
    roots = [wiki_root]
    for kind in INDEPENDENT_DIRS:
        base = content_directory(wiki_root, kind)
        if not base.is_relative_to(wiki_root):
            roots.append(base)
    return roots


def content_files(wiki_root: Path, pattern: str = "*.md") -> Iterator[Path]:
    for root in content_roots(wiki_root):
        yield from sorted(root.rglob(pattern))


def active_content_paths() -> RuntimePaths:
    return _runtime.get() or load_paths()


def reference_slug(value: object) -> str:
    """Normalize a slug or Obsidian entity reference, preserving its identity."""
    text = str(value or "").strip().removeprefix("[[").removesuffix("]]")
    target = text.split("|", 1)[0].split("#", 1)[0]
    return target.removesuffix(".md").rsplit("/", 1)[-1]

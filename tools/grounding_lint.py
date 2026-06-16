#!/usr/bin/env python3
"""Source-grounding gate for generated wiki pages.

This checker is intentionally conservative and mechanical. It does not try to
prove that every sentence is faithful; it blocks pages that lack explicit
source anchors or quote excerpts that cannot be found in prepared sources.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import frontmatter

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
PREPARED_LINK_RE = re.compile(r"\[prepared markdown\]\(([^)]+)\)")
BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$", re.MULTILINE)
SOURCE_ANCHOR_RE = re.compile(r"source_anchor\s*:", re.IGNORECASE)
SOURCE_FILE_RE = re.compile(r"source_file\s*:", re.IGNORECASE)
EVIDENCE_ID_RE = re.compile(r"`E\d+`")


@dataclass(frozen=True)
class GroundingIssue:
    level: str
    category: str
    file: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "level": self.level,
            "category": self.category,
            "file": self.file,
            "message": self.message,
        }


@dataclass(frozen=True)
class CliResult:
    exit_code: int
    stdout: str
    stderr: str = ""


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_section(content: str, heading: str) -> str:
    for match in SECTION_RE.finditer(content):
        if match.group(1).strip().lower() != heading.lower():
            continue
        start = match.end()
        next_match = SECTION_RE.search(content, start)
        end = next_match.start() if next_match else len(content)
        return content[start:end]
    return ""


def _all_markdown_pages(wiki_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for subdir in ("papers", "concepts", "claims"):
        root = wiki_dir / subdir
        if root.exists():
            paths.extend(sorted(root.glob("*.md")))
    return paths


def _relative_file(path: Path, wiki_dir: Path) -> str:
    return str(path.relative_to(wiki_dir)).replace("\\", "/")


def _matches_only(path: Path, wiki_dir: Path, only: Sequence[str]) -> bool:
    if not only:
        return True
    rel = _relative_file(path, wiki_dir)
    wanted = [item.replace("\\", "/").lstrip("./") for item in only if item.strip()]
    return any(rel == item or rel.startswith(item.rstrip("/") + "/") for item in wanted)


def _resolve_markdown_link(page_path: Path, link_target: str) -> Path:
    target = link_target.split("#", 1)[0].strip()
    return (page_path.parent / target).resolve()


def _excerpt_present(source_path: Path, excerpt: str) -> bool:
    if not source_path.exists() or not source_path.is_file():
        return False
    source_text = _normalize_text(source_path.read_text(encoding="utf-8"))
    quoted = _normalize_text(excerpt)
    return bool(quoted) and quoted in source_text


def _check_source_quotes(
    wiki_dir: Path,
    page_path: Path,
    rel: str,
    section: str,
) -> list[GroundingIssue]:
    issues: list[GroundingIssue] = []
    links = PREPARED_LINK_RE.findall(section)
    quotes = [quote.strip() for quote in BLOCKQUOTE_RE.findall(section) if quote.strip()]

    if not links:
        issues.append(
            GroundingIssue(
                "red",
                "missing-prepared-source-link",
                rel,
                "Source-grounded section must link to prepared markdown.",
            )
        )
        return issues
    if not quotes:
        issues.append(
            GroundingIssue(
                "red",
                "missing-source-excerpt",
                rel,
                "Source-grounded section must include at least one exact blockquote.",
            )
        )
        return issues

    source_paths: list[Path] = []
    for link in links:
        source_path = _resolve_markdown_link(page_path, link)
        try:
            source_path.relative_to(wiki_dir.resolve())
        except ValueError:
            issues.append(
                GroundingIssue(
                    "red",
                    "prepared-source-outside-wiki",
                    rel,
                    f"Prepared markdown link resolves outside wiki root: {link}",
                )
            )
            continue
        if not source_path.exists():
            issues.append(
                GroundingIssue(
                    "red",
                    "prepared-source-missing",
                    rel,
                    f"Prepared markdown link target does not exist: {link}",
                )
            )
            continue
        source_paths.append(source_path)
    if not source_paths:
        return issues

    for quote in quotes:
        if not any(_excerpt_present(source_path, quote) for source_path in source_paths):
            issues.append(
                GroundingIssue(
                    "red",
                    "source-excerpt-not-found",
                    rel,
                    f"Quoted excerpt was not found in any linked prepared source: {quote[:120]}",
                )
            )
    return issues


def _check_paper(wiki_dir: Path, page_path: Path, content: str) -> list[GroundingIssue]:
    rel = _relative_file(page_path, wiki_dir)
    section = _extract_section(content, "Evidence Pack")
    if not section:
        return [
            GroundingIssue(
                "red",
                "missing-evidence-pack",
                rel,
                "Paper pages must include ## Evidence Pack before generated interpretation sections.",
            )
        ]
    issues = _check_source_quotes(wiki_dir, page_path, rel, section)
    if not (EVIDENCE_ID_RE.search(section) or SOURCE_FILE_RE.search(section)):
        issues.append(
            GroundingIssue(
                "red",
                "missing-evidence-card-id",
                rel,
                "Evidence Pack entries must include evidence ids like `E1` or explicit source_file fields.",
            )
        )
    return issues


def _check_concept(wiki_dir: Path, page_path: Path, content: str) -> list[GroundingIssue]:
    rel = _relative_file(page_path, wiki_dir)
    section = _extract_section(content, "Source excerpts")
    if not section:
        return [
            GroundingIssue(
                "red",
                "missing-source-excerpts",
                rel,
                "Concept pages must include ## Source excerpts.",
            )
        ]
    return _check_source_quotes(wiki_dir, page_path, rel, section)


def _claim_evidence_items(content: str) -> list[dict]:
    try:
        post = frontmatter.loads(content)
    except Exception:
        return []
    evidence = post.metadata.get("evidence", [])
    return evidence if isinstance(evidence, list) else []


def _check_claim(wiki_dir: Path, page_path: Path, content: str) -> list[GroundingIssue]:
    rel = _relative_file(page_path, wiki_dir)
    issues: list[GroundingIssue] = []
    evidence_items = _claim_evidence_items(content)
    for index, item in enumerate(evidence_items, start=1):
        if not isinstance(item, dict):
            continue
        detail = str(item.get("detail", ""))
        source_anchor = str(item.get("source_anchor", ""))
        if not source_anchor and not SOURCE_ANCHOR_RE.search(detail):
            issues.append(
                GroundingIssue(
                    "red",
                    "missing-source-anchor",
                    rel,
                    f"Claim evidence item {index} must include source_anchor or a source_anchor: marker in detail.",
                )
            )
    return issues


def lint(wiki_dir: Path, only: Sequence[str] | None = None) -> list[GroundingIssue]:
    wiki_dir = wiki_dir.resolve()
    only = only or []
    issues: list[GroundingIssue] = []
    for page_path in _all_markdown_pages(wiki_dir):
        if not _matches_only(page_path, wiki_dir, only):
            continue
        content = page_path.read_text(encoding="utf-8")
        kind = page_path.parent.name
        if kind == "papers":
            issues.extend(_check_paper(wiki_dir, page_path, content))
        elif kind == "concepts":
            issues.extend(_check_concept(wiki_dir, page_path, content))
        elif kind == "claims":
            issues.extend(_check_claim(wiki_dir, page_path, content))
    return issues


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Source-grounding gate for llm-wiki pages")
    parser.add_argument(
        "--wiki-dir",
        default=None,
        help="Path to wiki directory. Accepts @configured (default: config/paths.json or ./wiki)",
    )
    parser.add_argument(
        "--paths-config",
        default=DEFAULT_CONFIG_PATH,
        type=Path,
        help="Path config JSON (default: config/paths.json)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Report only issues for this wiki-relative path or directory. May repeat.",
    )
    return parser


def _main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base_paths = load_paths(config_path=args.paths_config)
    wiki_root = (
        resolve_runtime_path(args.wiki_dir, base_paths, role="--wiki-dir")
        if args.wiki_dir
        else base_paths.wiki_root
    )
    paths = load_paths(config_path=args.paths_config, wiki_root=wiki_root)
    wiki_dir = paths.wiki_root
    if not wiki_dir.exists():
        print(f"Error: {wiki_dir} does not exist", file=sys.stderr)
        return 2

    issues = lint(wiki_dir, only=args.only)
    if args.json:
        print(json.dumps([issue.to_dict() for issue in issues], indent=2, ensure_ascii=False))
    else:
        print(f"Grounding lint: {len(issues)} issue(s)")
        for issue in issues:
            print(f"{issue.level} [{issue.category}] {issue.file}: {issue.message}")
    return 1 if any(issue.level == "red" for issue in issues) else 0


def run_cli(argv: Sequence[str] | None = None) -> CliResult:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = _main(argv)
    return CliResult(exit_code=exit_code, stdout=stdout.getvalue(), stderr=stderr.getvalue())


def main() -> None:
    configure_utf8_stdio()
    raise SystemExit(_main())


if __name__ == "__main__":
    main()

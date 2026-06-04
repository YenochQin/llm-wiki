#!/usr/bin/env python3
"""Move paper BibTeX from YAML frontmatter into body fenced code blocks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import frontmatter

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths

BIBTEX_SECTION_RE = re.compile(
    r"\n*## BibTeX\s*\n+```bibtex\n(?P<bibtex>.*?)\n```\s*",
    re.DOTALL,
)
FIELD_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=", re.MULTILINE)
ALLOWED_FIELDS = {
    "author",
    "title",
    "year",
    "journal",
    "booktitle",
    "publisher",
    "school",
    "institution",
    "howpublished",
    "volume",
    "number",
    "pages",
    "doi",
}


def _format_bibtex_section(bibtex: str) -> str:
    bibtex = bibtex.rstrip("\n")
    if not bibtex:
        return ""
    return f"\n\n## BibTeX\n\n```bibtex\n{bibtex}\n```\n"


def _extract_body_bibtex(text: str) -> str:
    match = BIBTEX_SECTION_RE.search(text)
    return match.group("bibtex").strip() if match else ""


def _move_bibtex(text: str, fallback_bibtex: str = "") -> tuple[str, bool, list[str]]:
    post = frontmatter.loads(text)
    metadata = dict(post.metadata)
    frontmatter_bibtex = str(metadata.pop("bibtex", "") or "").strip()
    body_bibtex = _extract_body_bibtex(post.content)
    bibtex = body_bibtex or frontmatter_bibtex or fallback_bibtex.strip()
    body = BIBTEX_SECTION_RE.sub("", post.content).rstrip()

    warnings = []
    if bibtex:
        extra_fields = sorted(
            {field.lower() for field in FIELD_RE.findall(bibtex)} - ALLOWED_FIELDS
        )
        if extra_fields:
            warnings.append(
                "BibTeX has non-core fields: " + ", ".join(extra_fields)
            )
        body += _format_bibtex_section(bibtex)

    new_text = frontmatter.dumps(frontmatter.Post(body, **metadata)).rstrip() + "\n"
    return new_text, new_text != text, warnings


def migrate_file(path: Path, dry_run: bool, fallback_bibtex: str = "") -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    new_text, changed, warnings = _move_bibtex(text, fallback_bibtex=fallback_bibtex)
    if changed and not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return changed, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paper markdown files or directories. Defaults to configured wiki_root/papers.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--bibtex-from-paper-dir",
        type=Path,
        help="When a target file has no BibTeX, copy the body BibTeX block from a same-named paper file in this directory.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    targets = [Path(p) for p in args.paths]
    if not targets:
        targets = [load_paths(args.config).wiki_root / "papers"]

    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.glob("*.md")))
        elif target.is_file():
            files.append(target)
        else:
            print(f"skip missing target: {target}", file=sys.stderr)

    changed_count = 0
    warning_count = 0
    for path in files:
        fallback_bibtex = ""
        if args.bibtex_from_paper_dir:
            paper_path = args.bibtex_from_paper_dir / path.name
            if paper_path.exists():
                fallback_bibtex = _extract_body_bibtex(
                    paper_path.read_text(encoding="utf-8")
                )
        changed, warnings = migrate_file(path, args.dry_run, fallback_bibtex)
        if changed:
            changed_count += 1
            action = "would update" if args.dry_run else "updated"
            print(f"{action}: {path}")
        for warning in warnings:
            warning_count += 1
            print(f"warning: {path}: {warning}", file=sys.stderr)

    print(
        f"bibtex migration complete: files={len(files)} changed={changed_count} warnings={warning_count}"
    )
    return 1 if warning_count else 0


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())

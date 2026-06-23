#!/usr/bin/env python3
"""Backfill existing wiki paper BibTeX blocks from Zotero metadata.

Purpose:
    Refresh paper pages and matching prepared sources with BibTeX derived from
    local Zotero metadata, without re-ingesting paper content.

When to use:
    Use after old pages have missing, stale, or frontmatter-only BibTeX and the
    corresponding PDF/item is already present in Zotero.

Inputs:
    - Configured wiki root, or --wiki-root.
    - Existing wiki/papers/*.md pages.
    - Zotero Desktop local API or local Zotero database fallback.

Writes:
    - Paper page ## BibTeX blocks.
    - Matching prepared source ## BibTeX blocks when source metadata links them.
    Use --dry-run to inspect the report without writing.

Usage:
    uv run python -X utf8 tools/backfill_bibtex_from_zotero.py --dry-run
    uv run python -X utf8 tools/backfill_bibtex_from_zotero.py --slug paper_slug --dry-run
    uv run python -X utf8 tools/backfill_bibtex_from_zotero.py --slug paper_slug
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import frontmatter

from _cli_io import configure_utf8_stdio
import enrich_local_pdf_bibtex
from _paths import DEFAULT_CONFIG_PATH, load_paths

BIBTEX_SECTION_RE = re.compile(
    r"\n*## BibTeX\s*\n+```bibtex\n(?P<bibtex>.*?)\n```\s*",
    re.DOTALL,
)


def _format_bibtex_section(bibtex: str) -> str:
    return f"\n\n## BibTeX\n\n```bibtex\n{bibtex.rstrip()}\n```\n"


def _extract_bibtex(text: str) -> str:
    match = BIBTEX_SECTION_RE.search(text)
    return match.group("bibtex").strip() if match else ""


def _replace_bibtex_block(text: str, bibtex: str) -> tuple[str, bool]:
    body = BIBTEX_SECTION_RE.sub("", text).rstrip()
    new_text = body + _format_bibtex_section(bibtex)
    return new_text, new_text != text


def _doi_from_metadata(metadata: dict[str, Any]) -> str:
    external_ids = metadata.get("external_ids")
    if isinstance(external_ids, dict):
        for key in ("DOI", "doi"):
            value = str(external_ids.get(key) or "").strip()
            if value:
                return value
    return str(metadata.get("doi") or "").strip()


def _source_pdf_for_slug(wiki_root: Path, slug: str) -> Path | None:
    source_path = wiki_root / "sources" / "papers" / f"{slug}.md"
    if not source_path.exists():
        return None
    try:
        metadata = frontmatter.loads(source_path.read_text(encoding="utf-8")).metadata
    except Exception:
        return None
    source = str(metadata.get("source") or "").strip()
    return Path(source).expanduser() if source else None


def _result(
    slug: str,
    status: str,
    message: str = "",
    **extra: Any,
) -> dict[str, Any]:
    payload = {"slug": slug, "status": status}
    if message:
        payload["message"] = message
    payload.update(extra)
    return payload


def backfill_one(
    paper_path: Path,
    wiki_root: Path,
    dry_run: bool,
    force: bool,
    zotero_root: Path | None,
    zotero_config: Path,
    api_base: str,
    timeout: float,
) -> dict[str, Any]:
    slug = paper_path.stem
    source_path = wiki_root / "sources" / "papers" / f"{slug}.md"
    text = paper_path.read_text(encoding="utf-8")
    try:
        post = frontmatter.loads(text)
    except Exception as exc:
        return _result(slug, "failed", f"paper frontmatter parse failed: {exc}")

    title = str(post.metadata.get("title") or "").strip()
    doi = _doi_from_metadata(dict(post.metadata))
    source_pdf = _source_pdf_for_slug(wiki_root, slug)
    if source_pdf is None:
        return _result(slug, "skipped", "no prepared source or source PDF path")
    if not source_pdf.exists():
        return _result(slug, "skipped", f"source PDF not found: {source_pdf}")

    old_bibtex = _extract_bibtex(text)
    enrichment = enrich_local_pdf_bibtex.enrich(
        source=source_pdf,
        title=title,
        doi=doi,
        zotero_root=zotero_root,
        zotero_config=zotero_config,
        api_base=api_base,
        timeout=timeout,
    )
    if enrichment.get("status") != "ok":
        return _result(
            slug,
            "skipped",
            str(enrichment.get("message") or enrichment.get("status")),
            source=str(source_pdf),
        )

    new_bibtex = str(enrichment.get("bibtex") or "").strip()
    if not new_bibtex:
        return _result(slug, "skipped", "Zotero enrichment returned empty BibTeX")
    if old_bibtex == new_bibtex and not force:
        return _result(
            slug,
            "unchanged",
            match=enrichment.get("match", {}),
            source=str(source_pdf),
        )

    paper_new, paper_changed = _replace_bibtex_block(text, new_bibtex)
    source_changed = False
    if source_path.exists():
        source_text = source_path.read_text(encoding="utf-8")
        source_new, source_changed = _replace_bibtex_block(source_text, new_bibtex)
    else:
        source_new = ""

    if not dry_run:
        if paper_changed or force:
            paper_path.write_text(paper_new, encoding="utf-8")
        if source_path.exists() and (source_changed or force):
            source_path.write_text(source_new, encoding="utf-8")

    status = "would_update" if dry_run else "updated"
    return _result(
        slug,
        status,
        match=enrichment.get("match", {}),
        warnings=enrichment.get("warnings", []),
        source=str(source_pdf),
        paper_changed=paper_changed,
        source_changed=source_changed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wiki-root", type=Path, help="Wiki root. Defaults to configured wiki_root.")
    parser.add_argument("--paths-config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--slug", action="append", default=[], help="Only process this paper slug; may repeat.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Rewrite matching BibTeX blocks even when unchanged.")
    parser.add_argument("--zotero-root", type=Path)
    parser.add_argument("--zotero-config", default=enrich_local_pdf_bibtex.find_zotero_pdf.DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--api-base", default="")
    parser.add_argument("--timeout", type=float, default=enrich_local_pdf_bibtex.fetch_zotero_metadata.DEFAULT_TIMEOUT)
    parser.add_argument("--json", action="store_true", help="Emit JSON summary only.")
    args = parser.parse_args()

    paths = load_paths(config_path=args.paths_config, wiki_root=args.wiki_root)
    wiki_root = paths.wiki_root
    papers_dir = wiki_root / "papers"
    slugs = set(args.slug)
    paper_paths = sorted(papers_dir.glob("*.md"))
    if slugs:
        paper_paths = [path for path in paper_paths if path.stem in slugs]

    results = [
        backfill_one(
            paper_path=path,
            wiki_root=wiki_root,
            dry_run=args.dry_run,
            force=args.force,
            zotero_root=args.zotero_root,
            zotero_config=args.zotero_config,
            api_base=args.api_base,
            timeout=args.timeout,
        )
        for path in paper_paths
    ]
    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    summary = {"wiki_root": str(wiki_root), "counts": counts, "results": results}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        for item in results:
            msg = f"{item['status']}: {item['slug']}"
            if item.get("message"):
                msg += f" | {item['message']}"
            elif item.get("match"):
                match = item["match"]
                msg += f" | {match.get('reason', '')} | {match.get('item_key', '')}"
            print(msg)
        print("summary:", json.dumps(counts, ensure_ascii=False, sort_keys=True))
    return 0 if all(item["status"] not in {"failed"} for item in results) else 1


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())

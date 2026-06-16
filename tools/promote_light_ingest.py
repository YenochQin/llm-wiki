#!/usr/bin/env python3
"""Rank light-ingested paper pages for promotion to full ingest.

Purpose:
    Score light-ingested background papers and produce a shortlist for full
    `/ingest` or `/reingest` promotion.

Inputs:
    Existing wiki/papers/*.md pages, especially pages tagged or structured by
    `/ingest-light`.

Writes:
    Nothing by default. With --output, writes a Markdown promotion report.

Usage:
    uv run python -X utf8 tools/promote_light_ingest.py --wiki-dir @configured
    uv run python -X utf8 tools/promote_light_ingest.py --wiki-dir @configured --min-score 5 --output .checkpoints/promote.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path

ROLE_WEIGHTS = {
    "method-foundation": 5,
    "gap-evidence": 5,
    "benchmark": 4,
    "application": 2,
    "review-context": 1,
    "background": 0,
}

MODE_WEIGHTS = {
    "computation": 3,
    "theory": 3,
    "experiment": 2,
}

KEYWORD_WEIGHTS = {
    "mcdhf": 4,
    "rci": 4,
    "grasp": 4,
    "grasp2018": 4,
    "isotope-shift": 4,
    "isotope shift": 4,
    "field-shift": 4,
    "field shift": 4,
    "mass-shift": 4,
    "mass shift": 4,
    "hyperfine-structure": 4,
    "hyperfine": 3,
    "transition-rate": 3,
    "transition rate": 3,
    "energy-level": 3,
    "energy level": 3,
    "configuration-mixing": 3,
    "configuration mixing": 3,
    "open-shell": 3,
    "open shell": 3,
    "lanthanide": 3,
    "heavy atom": 3,
    "uncertainty": 2,
    "discrepancy": 2,
    "benchmark": 2,
    "validation": 2,
    "database": 2,
}

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)")


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _frontmatter_tags(meta: dict[str, Any]) -> list[str]:
    return [tag.strip() for tag in _as_list(meta.get("tags")) if tag.strip()]


def _detect_role(meta: dict[str, Any], body: str) -> str:
    tags = set(_frontmatter_tags(meta))
    for role in ROLE_WEIGHTS:
        if role in tags:
            return role
    match = re.search(r"Primary role:\s*`?([a-z-]+)`?", body)
    if match and match.group(1) in ROLE_WEIGHTS:
        return match.group(1)
    return "unknown"


def _sections(body: str) -> set[str]:
    return {match.group(1).strip().lower() for match in SECTION_RE.finditer(body)}


def _source_slug(meta: dict[str, Any], slug: str) -> str:
    for key in ("sourceSlug", "source_slug", "citationKey", "citation_key"):
        value = str(meta.get(key) or "").strip()
        if value:
            return value
    return slug


def _score_page(path: Path, wiki_root: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    parse_warning = ""
    try:
        post = frontmatter.loads(text)
        meta = dict(post.metadata)
        body = post.content
    except Exception as exc:
        if "light-ingest" not in text:
            return None
        parse_warning = f"frontmatter parse warning: {exc.__class__.__name__}"
        meta = {"slug": path.stem, "title": path.stem, "tags": ["light-ingest"]}
        body = text
    tags = _frontmatter_tags(meta)
    if "light-ingest" not in tags:
        return None

    slug = str(meta.get("slug") or path.stem)
    role = _detect_role(meta, body)
    research_modes = [mode.lower() for mode in _as_list(meta.get("research_modes"))]
    keyword_blob = " ".join(
        _as_list(meta.get("tags"))
        + _as_list(meta.get("keywords"))
        + _as_list(meta.get("theory_tags"))
        + _as_list(meta.get("computation_tags"))
        + _as_list(meta.get("experiment_tags"))
        + _as_list(meta.get("research_object_tags"))
        + [body[:5000]]
    ).lower()

    score = 0
    reasons: list[str] = []
    if parse_warning:
        reasons.append(parse_warning)

    role_score = ROLE_WEIGHTS.get(role, 0)
    if role_score:
        score += role_score
        reasons.append(f"role={role} (+{role_score})")

    for mode in sorted(set(research_modes)):
        weight = MODE_WEIGHTS.get(mode, 0)
        if weight:
            score += weight
            reasons.append(f"research_mode={mode} (+{weight})")

    matched_keywords: list[str] = []
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in keyword_blob:
            score += weight
            matched_keywords.append(keyword)
    if matched_keywords:
        reasons.append("keywords=" + ", ".join(matched_keywords[:8]))

    try:
        importance = int(meta.get("importance") or 0)
    except (TypeError, ValueError):
        importance = 0
    if importance >= 3:
        score += importance
        reasons.append(f"importance={importance} (+{importance})")

    external_ids = meta.get("external_ids") if isinstance(meta.get("external_ids"), dict) else {}
    doi = str(external_ids.get("DOI") or external_ids.get("doi") or "").strip()
    if doi:
        score += 1
        reasons.append("has DOI (+1)")

    source_slug = _source_slug(meta, slug)
    source_path = wiki_root / "sources" / "papers" / f"{source_slug}.md"
    if source_path.exists():
        score += 2
        reasons.append("prepared source exists (+2)")

    sections = _sections(body)
    full_ingest_like_sections = {"method", "results", "open questions", "my take"} & sections
    if full_ingest_like_sections:
        score += 1
        reasons.append("already has analysis sections (+1)")

    links = sorted(set(WIKILINK_RE.findall(body)))
    non_summary_links = [
        link for link in links
        if link not in {"thesis-introduction-literature"} and not link.startswith("Summary/")
    ]
    if non_summary_links:
        score += min(3, len(non_summary_links))
        reasons.append(f"non-summary links={len(non_summary_links)} (+{min(3, len(non_summary_links))})")

    priority = "low"
    if score >= 18:
        priority = "high"
    elif score >= 11:
        priority = "medium"

    suggested_command = (
        f"/reingest @configured-sources-papers/{source_slug}.md --update-entities"
        if source_path.exists()
        else f"/ingest --doi {doi}" if doi else f"/ingest --title \"{str(meta.get('title') or path.stem)}\""
    )

    return {
        "slug": slug,
        "title": str(meta.get("title") or path.stem),
        "path": f"papers/{path.name}",
        "role": role,
        "score": score,
        "priority": priority,
        "doi": doi,
        "year": meta.get("year"),
        "research_modes": research_modes,
        "source_slug": source_slug,
        "source_exists": source_path.exists(),
        "source_path": f"@configured-sources-papers/{source_slug}.md",
        "reasons": reasons,
        "suggested_command": suggested_command,
    }


def _to_markdown(items: list[dict[str, Any]], limit: int) -> str:
    lines = [
        "# Light-ingest promotion candidates",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
    ]
    if not items:
        lines.append("No `light-ingest` paper pages found.")
        return "\n".join(lines)

    visible = items[:limit]
    for priority in ("high", "medium", "low"):
        group = [item for item in visible if item["priority"] == priority]
        if not group:
            continue
        lines.append(f"## {priority.title()} priority")
        lines.append("")
        for item in group:
            doi = f" DOI: `{item['doi']}`." if item["doi"] else ""
            source = "source ok" if item["source_exists"] else "source missing"
            lines.append(f"- [[{item['slug']}]] — score {item['score']} ({item['role']}, {source}).{doi}")
            lines.append(f"  - Why: {'; '.join(item['reasons'][:5])}")
            lines.append(f"  - Suggested: `{item['suggested_command']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wiki-dir", default="@configured", help="Wiki root or alias.")
    parser.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional markdown report output path.")
    args = parser.parse_args()

    paths = load_paths(config_path=args.paths_config)
    wiki_root = resolve_runtime_path(args.wiki_dir, paths, role="--wiki-dir")
    if wiki_root is None:
        raise SystemExit("--wiki-dir resolved to empty path")

    papers_dir = wiki_root / "papers"
    items: list[dict[str, Any]] = []
    for path in sorted(papers_dir.glob("*.md")):
        item = _score_page(path, wiki_root)
        if item and int(item["score"]) >= args.min_score:
            items.append(item)
    items.sort(key=lambda item: (-int(item["score"]), str(item["slug"]).lower()))

    if args.json:
        print(json.dumps({"status": "ok", "wiki_root": str(wiki_root), "candidates": items[:args.limit]}, ensure_ascii=False, indent=2))
        return

    markdown = _to_markdown(items, args.limit)
    if args.output:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = paths.project_root / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

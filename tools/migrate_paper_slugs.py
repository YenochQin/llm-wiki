#!/usr/bin/env python3
"""Migrate ``wiki/papers/<slug>.md`` to citation-key based slugs.

This is the paper-page counterpart of ``migrate_source_slugs.py``. Existing
paper pages use a deterministic title-keyword slug, which collides whenever two
papers share opening keywords. This tool renames each paper page to the same
citation-key style now used for prepared sources:

    citationKey, if Zotero/Better BibTeX has one for the paper
    otherwise author_year_veryshorttitle (matched against an existing source)
    otherwise the existing paper slug (recorded as ``fallback``)

It also updates ``slug:`` frontmatter, all Obsidian wikilinks, the graph
``papers/<slug>`` endpoints in ``edges.jsonl`` / ``citations.jsonl``,
``open_questions.md`` mentions, ``index.md`` entries, and ``log.md`` records.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import frontmatter

import find_zotero_pdf
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path
from _zotero_snapshot import prepare_snapshot
from prepare_paper_source import _safe_source_slug_part, _source_slug


# ---------------------------------------------------------------------------
# Title normalization (independent of source slug logic — only used here for
# matching paper pages to existing source files)
# ---------------------------------------------------------------------------

def _norm_title(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_n_words(text: str, n: int) -> str:
    return " ".join(_norm_title(text).split()[:n])


_YEAR_FROM_STEM_RE = re.compile(r"^[A-Za-z]+_(\d{4})_")


def _year_from_source_stem(stem: str) -> str:
    match = _YEAR_FROM_STEM_RE.match(stem)
    return match.group(1) if match else ""


# ---------------------------------------------------------------------------
# Zotero scaffolding (mirrors migrate_source_slugs.py)
# ---------------------------------------------------------------------------

@dataclass
class ZoteroItem:
    item_key: str
    title: str
    year: str
    creators: list[str]
    citation_key: str
    doi: str = ""


def _resolve_zotero_items(
    zotero_root: Path | None, zotero_config: Path
) -> tuple[list[ZoteroItem], list[str]]:
    notes: list[str] = []
    if zotero_root is None:
        zotero_root, discover_notes = find_zotero_pdf._discover_zotero_root(zotero_config)
        notes.extend(discover_notes)
    else:
        input_root = Path(find_zotero_pdf._expand_path_template(str(zotero_root))).resolve()
        zotero_root, resolve_notes = find_zotero_pdf._resolve_zotero_root(input_root)
        notes.extend(resolve_notes)

    if zotero_root is None:
        notes.append("Zotero root not found; falling back to source-file matches only")
        return [], notes

    snapshot_root, snapshot_notes = prepare_snapshot(Path.cwd(), zotero_root)
    notes.extend(snapshot_notes)
    db_path = snapshot_root / "zotero.sqlite"
    if not db_path.exists():
        notes.append(f"Zotero database not found: {db_path}")
        return [], notes

    conn = find_zotero_pdf._connect(db_path)
    try:
        out = [
            ZoteroItem(
                item_key=item.key,
                title=item.title,
                year=item.year,
                creators=item.creators,
                citation_key=item.citation_key,
                doi=find_zotero_pdf._normalize_doi(item.doi or ""),
            )
            for item in find_zotero_pdf._all_parent_items(conn)
        ]
        notes.append(f"loaded {len(out)} Zotero parent item(s)")
        return out, notes
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Source-file index (existing wiki/sources/papers/*.md)
# ---------------------------------------------------------------------------

@dataclass
class SourceMeta:
    stem: str
    title: str
    citation_key: str
    year: str
    norm: str
    first8: str
    first6: str
    first4: str


def _index_sources(source_dir: Path) -> dict[str, SourceMeta]:
    out: dict[str, SourceMeta] = {}
    for path in sorted(source_dir.glob("*.md")):
        try:
            post = frontmatter.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        title = str(post.metadata.get("title") or "").strip()
        citation_key = str(post.metadata.get("citationKey") or "").strip() or path.stem
        year = str(post.metadata.get("year") or "").strip() or _year_from_source_stem(path.stem)
        out[path.stem] = SourceMeta(
            stem=path.stem,
            title=title,
            citation_key=citation_key,
            year=year,
            norm=_norm_title(title),
            first8=_first_n_words(title, 8),
            first6=_first_n_words(title, 6),
            first4=_first_n_words(title, 4),
        )
    return out


def _doi_from_metadata(metadata: dict[str, Any]) -> str:
    raw = metadata.get("external_ids") or {}
    if isinstance(raw, dict):
        for key in ("DOI", "doi"):
            value = str(raw.get(key) or "").strip().lower()
            if value:
                return value
    return ""


def _match_source(
    title: str,
    year: str,
    doi: str,
    sources: dict[str, SourceMeta],
) -> tuple[str, str]:
    """Return (source_stem, reason) or ("", "unmatched")."""
    nt = _norm_title(title)
    f8 = _first_n_words(title, 8)
    f6 = _first_n_words(title, 6)
    f4 = _first_n_words(title, 4)

    for stem, meta in sources.items():
        if meta.norm and meta.norm == nt:
            return stem, "title-exact"

    candidates = [
        stem for stem, meta in sources.items()
        if meta.first8 == f8 and meta.year == year
    ]
    if len(candidates) == 1:
        return candidates[0], "first8+year"

    candidates = [
        stem for stem, meta in sources.items()
        if meta.first6 == f6 and meta.year == year
    ]
    if len(candidates) == 1:
        return candidates[0], "first6+year"

    candidates = [
        stem for stem, meta in sources.items()
        if meta.first4 == f4 and meta.year == year
    ]
    if len(candidates) == 1:
        return candidates[0], "first4+year"

    if len(candidates) > 1:
        return "", f"ambiguous:{','.join(candidates)}"
    return "", "unmatched"


def _match_zotero(
    title: str,
    year: str,
    doi: str,
    zotero_items: list[ZoteroItem],
) -> tuple[ZoteroItem | None, str]:
    if doi:
        for item in zotero_items:
            if item.doi and item.doi == doi:
                return item, "zotero-doi"
    nt = _norm_title(title)
    matches = [item for item in zotero_items if _norm_title(item.title) == nt]
    if len(matches) == 1:
        return matches[0], "zotero-title-exact"
    f6 = _first_n_words(title, 6)
    matches = [
        item for item in zotero_items
        if _first_n_words(item.title, 6) == f6 and item.year == year
    ]
    if len(matches) == 1:
        return matches[0], "zotero-first6+year"
    return None, ""


# ---------------------------------------------------------------------------
# Migration plan
# ---------------------------------------------------------------------------

@dataclass
class PaperRow:
    old_stem: str
    new_stem: str
    desired_stem: str
    source_path: Path
    target_path: Path
    title: str
    year: str
    citation_key: str
    match_reason: str
    matched_source_stem: str

    def as_dict(self, wiki_root: Path) -> dict[str, Any]:
        return {
            "old": str(self.source_path.relative_to(wiki_root)),
            "new": str(self.target_path.relative_to(wiki_root)),
            "old_stem": self.old_stem,
            "new_stem": self.new_stem,
            "desired_stem": self.desired_stem,
            "title": self.title,
            "year": self.year,
            "citation_key": self.citation_key,
            "match_reason": self.match_reason,
            "matched_source_stem": self.matched_source_stem,
        }


def _authors_from_metadata(metadata: dict[str, Any]) -> str:
    authors = metadata.get("authors") or metadata.get("author") or ""
    if isinstance(authors, list):
        return ", ".join(str(x) for x in authors)
    return str(authors).strip()


def _desired_slug_for_paper(
    *,
    title: str,
    year: str,
    citation_key: str,
    authors: str,
) -> str:
    return _source_slug(
        title=title,
        citation_key=citation_key,
        authors=authors,
        year=year,
        bibtex="",
    )


def build_plan(
    wiki_root: Path,
    zotero_root: Path | None,
    zotero_config: Path,
) -> tuple[list[PaperRow], dict[str, Any]]:
    paper_dir = wiki_root / "papers"
    source_dir = wiki_root / "sources" / "papers"
    paper_files = sorted(p for p in paper_dir.glob("*.md") if p.is_file())
    sources = _index_sources(source_dir) if source_dir.exists() else {}
    zotero_items, notes = _resolve_zotero_items(zotero_root, zotero_config)

    rows: list[PaperRow] = []
    for paper_path in paper_files:
        post = frontmatter.loads(paper_path.read_text(encoding="utf-8", errors="ignore"))
        metadata = dict(post.metadata)
        title = str(metadata.get("title") or "").strip() or paper_path.stem
        year = str(metadata.get("year") or "").strip()
        doi = _doi_from_metadata(metadata)

        source_stem, source_reason = _match_source(title, year, doi, sources)

        citation_key = ""
        match_reason = ""

        if source_stem:
            citation_key = sources[source_stem].citation_key
            match_reason = f"source:{source_reason}"
        else:
            zotero_item, zotero_reason = _match_zotero(title, year, doi, zotero_items)
            if zotero_item and zotero_item.citation_key:
                citation_key = zotero_item.citation_key
                match_reason = zotero_reason
            else:
                match_reason = source_reason or "unmatched"

        if citation_key:
            desired = _desired_slug_for_paper(
                title=title,
                year=year,
                citation_key=citation_key,
                authors=_authors_from_metadata(metadata),
            )
        else:
            desired = paper_path.stem

        rows.append(
            PaperRow(
                old_stem=paper_path.stem,
                new_stem=desired,
                desired_stem=desired,
                source_path=paper_path,
                target_path=paper_path.with_name(f"{desired}.md"),
                title=title,
                year=year,
                citation_key=citation_key,
                match_reason=match_reason,
                matched_source_stem=source_stem,
            )
        )

    conflicts = _dedupe_targets(rows)
    target_collisions = _detect_target_collisions(rows, wiki_root)

    meta = {
        "wiki_root": str(wiki_root),
        "paper_count": len(paper_files),
        "rename_count": sum(1 for row in rows if row.old_stem != row.new_stem),
        "unchanged_count": sum(1 for row in rows if row.old_stem == row.new_stem),
        "unmatched": [
            row.old_stem for row in rows
            if row.match_reason in ("unmatched",)
            or row.match_reason.startswith("ambiguous")
        ],
        "zotero_notes": notes,
        "paper_level_conflicts_resolved_with_old_stem_suffix": conflicts,
        "existing_target_collisions": sorted(set(target_collisions)),
    }
    return rows, meta


def _dedupe_targets(rows: list[PaperRow]) -> dict[str, list[str]]:
    groups: dict[str, list[PaperRow]] = {}
    for row in rows:
        groups.setdefault(row.desired_stem, []).append(row)
    conflicts: dict[str, list[str]] = {}
    for desired, group in groups.items():
        if len(group) <= 1:
            continue
        conflicts[desired] = [row.old_stem for row in group]
        for row in group:
            row.new_stem = f"{desired}-{_safe_source_slug_part(row.old_stem)}"
            row.target_path = row.source_path.with_name(f"{row.new_stem}.md")
    return conflicts


def _detect_target_collisions(rows: list[PaperRow], wiki_root: Path) -> list[str]:
    planned_sources = {row.source_path.resolve() for row in rows}
    out: list[str] = []
    for row in rows:
        if row.target_path.resolve() == row.source_path.resolve():
            continue
        if row.target_path.exists() and row.target_path.resolve() not in planned_sources:
            out.append(str(row.target_path.relative_to(wiki_root)))
    return out


# ---------------------------------------------------------------------------
# Apply step — replace slug occurrences across the vault
# ---------------------------------------------------------------------------

# Patterns that mark a "papers/<slug>" reference (graph edges, citations,
# open_questions, ingest log). The wikilink form is handled separately.
PAPER_PREFIX_PATTERNS = (
    "papers/",
    "paper/",  # singular form used in open_questions.md ([paper/<slug>])
)


def _wikilink_pattern(stem: str) -> re.Pattern[str]:
    # Match [[stem]], [[stem|alias]], [[stem#anchor]]; do not match longer slugs
    return re.compile(r"\[\[" + re.escape(stem) + r"(?P<rest>[\]|#])")


def _prefix_pattern(prefix: str, stem: str) -> re.Pattern[str]:
    # Match "prefix<stem>" only when followed by a non-slug character so we
    # don't rewrite a slug that happens to be a prefix of another slug.
    return re.compile(re.escape(prefix) + re.escape(stem) + r"(?P<rest>[^A-Za-z0-9_-]|$)")


def _bare_slug_pattern(stem: str) -> re.Pattern[str]:
    # Match a bare slug as an isolated token: preceded by whitespace, line
    # start, or a YAML/markdown delimiter; followed by similar boundary.
    # Slug characters are [A-Za-z0-9_-], so the boundary must be outside that
    # set. Quote/bracket/list-marker characters are common YAML contexts.
    return re.compile(
        r"(?P<lead>(?:^|[\s,\"'\[\]])"
        + r")"
        + re.escape(stem)
        + r"(?P<rest>[\s,\"'\[\]\)#|.]|$)"
    )


def _replace_in_text(text: str, rows: list[PaperRow]) -> str:
    # Order from longest to shortest to avoid prefix collisions.
    ordered = sorted(
        (r for r in rows if r.old_stem != r.new_stem),
        key=lambda r: len(r.old_stem),
        reverse=True,
    )
    out = text
    for row in ordered:
        wl_re = _wikilink_pattern(row.old_stem)
        out = wl_re.sub(lambda m, s=row.new_stem: f"[[{s}{m.group('rest')}", out)
        for prefix in PAPER_PREFIX_PATTERNS:
            pre_re = _prefix_pattern(prefix, row.old_stem)
            out = pre_re.sub(
                lambda m, p=prefix, s=row.new_stem: f"{p}{s}{m.group('rest')}",
                out,
            )
        bare_re = _bare_slug_pattern(row.old_stem)
        out = bare_re.sub(
            lambda m, s=row.new_stem: f"{m.group('lead')}{s}{m.group('rest')}",
            out,
        )
    return out


def _update_paper_frontmatter(text: str, row: PaperRow) -> str:
    post = frontmatter.loads(text)
    metadata = dict(post.metadata)
    metadata["slug"] = row.new_stem
    if row.citation_key:
        metadata["citationKey"] = row.citation_key
    return frontmatter.dumps(frontmatter.Post(post.content, **metadata)).rstrip() + "\n"


def _walk_text_files(wiki_root: Path) -> Iterable[Path]:
    for path in sorted(wiki_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in {".md", ".jsonl"}:
            yield path


def apply_plan(wiki_root: Path, rows: list[PaperRow]) -> dict[str, Any]:
    rename_rows = [row for row in rows if row.old_stem != row.new_stem]
    if not rename_rows:
        return {
            "renamed_paper_files": 0,
            "updated_text_files": 0,
        }

    _assert_apply_permissions(wiki_root, rename_rows)

    paper_paths = {row.source_path.resolve(): row for row in rename_rows}

    updated_files = 0
    for path in _walk_text_files(wiki_root):
        original = path.read_text(encoding="utf-8", errors="ignore")
        new_text = _replace_in_text(original, rename_rows)
        if path.resolve() in paper_paths:
            new_text = _update_paper_frontmatter(new_text, paper_paths[path.resolve()])
        if new_text != original:
            path.write_text(new_text, encoding="utf-8")
            updated_files += 1

    renamed = 0
    for row in rename_rows:
        if row.source_path.exists() and row.source_path.resolve() != row.target_path.resolve():
            row.source_path.rename(row.target_path)
            renamed += 1

    return {
        "renamed_paper_files": renamed,
        "updated_text_files": updated_files,
    }


def _assert_apply_permissions(wiki_root: Path, rename_rows: list[PaperRow]) -> None:
    probe = wiki_root / ".llm-wiki-paper-rename-test.tmp"
    try:
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise PermissionError(f"wiki root is not writable: {wiki_root} ({exc})") from exc

    blocked: list[str] = []
    for row in rename_rows:
        if row.source_path.exists() and row.source_path.resolve() != row.target_path.resolve():
            try:
                with row.source_path.open("a", encoding="utf-8"):
                    pass
            except OSError as exc:
                blocked.append(f"{row.source_path} ({exc})")
    if blocked:
        sample = "; ".join(blocked[:10])
        extra = f"; ... {len(blocked) - 10} more" if len(blocked) > 10 else ""
        raise PermissionError(f"paper migration cannot write required path(s): {sample}{extra}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(wiki_root: Path) -> dict[str, Any]:
    paper_dir = wiki_root / "papers"
    issues: list[dict[str, str]] = []

    paper_files = sorted(p for p in paper_dir.glob("*.md") if p.is_file())
    paper_stems = {p.stem for p in paper_files}

    for path in paper_files:
        try:
            post = frontmatter.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception as exc:
            issues.append({"file": str(path.relative_to(wiki_root)), "issue": f"frontmatter parse failed: {exc}"})
            continue
        slug = str(post.metadata.get("slug") or "").strip()
        if slug != path.stem:
            issues.append({
                "file": str(path.relative_to(wiki_root)),
                "issue": f"slug mismatch: {slug or '<missing>'} != {path.stem}",
            })

    paper_endpoint_re = re.compile(r"\bpapers/([A-Za-z0-9_.+-]+?)(?=[\s\"',)\]}]|\.md\b|$)")
    for path in _walk_text_files(wiki_root):
        # Skip prepared-source files: their frontmatter ``source:`` field
        # contains raw PDF paths like ``raw/papers/Bilous 等 - 2024…`` that
        # the regex would otherwise pick up as fake paper endpoints.
        if path.is_relative_to(wiki_root / "sources"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in paper_endpoint_re.finditer(text):
            stem = match.group(1)
            # Skip ``sources/papers/...`` markdown links, which embed the
            # ``papers/`` token but are scoped to the sources tree.
            start = match.start()
            if start >= len("sources/") and text[start - len("sources/"):start] == "sources/":
                continue
            if stem not in paper_stems:
                issues.append({
                    "file": str(path.relative_to(wiki_root)),
                    "issue": f"broken paper endpoint: papers/{stem}",
                })
                break

    return {
        "wiki_root": str(wiki_root),
        "paper_count": len(paper_files),
        "issue_count": len(issues),
        "issues": issues[:200],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _write_report(report_path: Path | None, payload: dict[str, Any]) -> None:
    if not report_path:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-root", default="@configured", help="Wiki root path or runtime alias (default: @configured)")
    parser.add_argument("--zotero-root", default="", help="Optional Zotero data root")
    parser.add_argument("--zotero-config", default="config/zotero-roots.json", help="Zotero roots config")
    parser.add_argument("--report", default=".checkpoints/paper-slug-migration.json", help="Write JSON report here")
    parser.add_argument("--yes", action="store_true", help="Apply the migration")
    parser.add_argument("--validate", action="store_true", help="Validate current paper slug consistency")
    parser.add_argument(
        "--repair-from-report",
        action="store_true",
        help="Re-apply the text-replacement pass using old→new pairs from --report. "
             "Use this after a successful rename when the rewriter logic has been tightened "
             "and stale slug strings remain in non-link contexts.",
    )
    args = parser.parse_args(argv)

    paths = load_paths(config_path=DEFAULT_CONFIG_PATH)
    wiki_root = resolve_runtime_path(args.wiki_root, paths, role="wiki-root")
    if wiki_root is None:
        raise SystemExit("wiki root could not be resolved")
    zotero_root = Path(args.zotero_root).expanduser().resolve() if args.zotero_root.strip() else None
    zotero_config = Path(args.zotero_config)
    report_path = Path(args.report) if args.report.strip() else None

    if args.validate:
        payload = validate(wiki_root)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["issue_count"] == 0 else 1

    if args.repair_from_report:
        if not report_path or not report_path.exists():
            raise SystemExit(f"--repair-from-report requires an existing report at {report_path}")
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        rows = [
            PaperRow(
                old_stem=r["old_stem"],
                new_stem=r["new_stem"],
                desired_stem=r.get("desired_stem", r["new_stem"]),
                source_path=wiki_root / "papers" / f"{r['new_stem']}.md",
                target_path=wiki_root / "papers" / f"{r['new_stem']}.md",
                title=r.get("title", ""),
                year=str(r.get("year", "")),
                citation_key=r.get("citation_key", ""),
                match_reason=r.get("match_reason", ""),
                matched_source_stem=r.get("matched_source_stem", ""),
            )
            # Re-introduce the old->new mapping by overriding source_path to a
            # dummy path we will not rename. The rewriter only consults
            # ``old_stem``/``new_stem`` for text replacements.
            for r in previous.get("renames", [])
        ]
        updated = 0
        for path in _walk_text_files(wiki_root):
            original = path.read_text(encoding="utf-8", errors="ignore")
            new_text = _replace_in_text(original, rows)
            if new_text != original:
                path.write_text(new_text, encoding="utf-8")
                updated += 1
        validation = validate(wiki_root)
        payload = {
            "mode": "repair-from-report",
            "wiki_root": str(wiki_root),
            "rename_count": len(rows),
            "updated_text_files": updated,
            "validation": validation,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if validation["issue_count"] == 0 else 1

    rows, meta = build_plan(wiki_root, zotero_root, zotero_config)
    payload = {
        "mode": "apply" if args.yes else "dry-run",
        **meta,
        "renames": [row.as_dict(wiki_root) for row in rows if row.old_stem != row.new_stem],
        "unchanged": [
            {"slug": row.old_stem, "title": row.title, "match_reason": row.match_reason}
            for row in rows if row.old_stem == row.new_stem
        ],
    }

    if meta["existing_target_collisions"]:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    if not args.yes:
        _write_report(report_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    apply_result = apply_plan(wiki_root, rows)
    validation = validate(wiki_root)
    payload["apply_result"] = apply_result
    payload["validation"] = validation
    _write_report(report_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if validation["issue_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

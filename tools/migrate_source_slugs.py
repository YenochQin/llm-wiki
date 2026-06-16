#!/usr/bin/env python3
"""Migrate prepared paper sources to citation-key based source slugs.

This tool renames ``wiki/sources/papers/<old>.md`` files to the current
prepared-source naming rule used by ``prepare_paper_source.py``:

    citationKey, if Zotero/Better BibTeX has one
    otherwise author_year_veryshorttitle

It also updates prepared-source frontmatter, asset directories, image paths,
and markdown links to prepared sources across the wiki.

Purpose:
    Bring existing prepared MinerU markdown files into the current source-slug
    convention.

Inputs:
    Configured wiki root and optional Zotero metadata.

Writes:
    Only with --yes: renames source files/assets and rewrites prepared-source
    links across the wiki. Without --yes, writes a JSON migration report only.

Usage:
    uv run python -X utf8 tools/migrate_source_slugs.py --wiki-root @configured
    uv run python -X utf8 tools/migrate_source_slugs.py --wiki-root @configured --validate
    uv run python -X utf8 tools/migrate_source_slugs.py --wiki-root @configured --yes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import frontmatter

from _cli_io import configure_utf8_stdio
import find_zotero_pdf
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path
from _zotero_snapshot import prepare_snapshot
from prepare_paper_source import _safe_source_slug_part, _source_slug


SOURCE_LINK_PREFIXES = (
    "sources/papers/",
    "@configured-sources-papers/",
    "@wiki-sources-papers/",
    "wiki/sources/papers/",
)


@dataclass
class ZoteroItem:
    item_key: str
    title: str
    year: str
    creators: list[str]
    citation_key: str
    pdf_paths: list[str]


@dataclass
class MigrationRow:
    old_stem: str
    new_stem: str
    desired_stem: str
    source_path: Path
    target_path: Path
    asset_path: Path
    target_asset_path: Path
    title: str
    citation_key: str
    match_reason: str
    zotero_item_key: str

    def as_dict(self, wiki_root: Path) -> dict[str, Any]:
        return {
            "old": str(self.source_path.relative_to(wiki_root)),
            "new": str(self.target_path.relative_to(wiki_root)),
            "old_stem": self.old_stem,
            "new_stem": self.new_stem,
            "desired_stem": self.desired_stem,
            "title": self.title,
            "citation_key": self.citation_key,
            "match_reason": self.match_reason,
            "zotero_item_key": self.zotero_item_key,
            "asset_old": str(self.asset_path.relative_to(wiki_root)) if self.asset_path.exists() else None,
            "asset_new": str(self.target_asset_path.relative_to(wiki_root)),
        }


def _normalize(value: str) -> str:
    return find_zotero_pdf._normalize_text(value or "")


def _read_post(path: Path) -> frontmatter.Post:
    return frontmatter.loads(path.read_text(encoding="utf-8", errors="ignore"))


def _plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _first_year(value: str) -> str:
    match = re.search(r"\d{4}", value or "")
    return match.group(0) if match else ""


def _resolve_zotero_items(zotero_root: Path | None, zotero_config: Path) -> tuple[list[ZoteroItem], list[str]]:
    notes: list[str] = []
    if zotero_root is None:
        zotero_root, discover_notes = find_zotero_pdf._discover_zotero_root(zotero_config)
        notes.extend(discover_notes)
    else:
        input_root = Path(find_zotero_pdf._expand_path_template(str(zotero_root))).resolve()
        zotero_root, resolve_notes = find_zotero_pdf._resolve_zotero_root(input_root)
        notes.extend(resolve_notes)

    if zotero_root is None:
        notes.append("Zotero root not found; falling back to source frontmatter only")
        return [], notes

    snapshot_root, snapshot_notes = prepare_snapshot(Path.cwd(), zotero_root)
    notes.extend(snapshot_notes)
    db_path = snapshot_root / "zotero.sqlite"
    if not db_path.exists():
        notes.append(f"Zotero database not found: {db_path}")
        return [], notes

    conn = find_zotero_pdf._connect(db_path)
    try:
        out: list[ZoteroItem] = []
        for item in find_zotero_pdf._all_parent_items(conn):
            attachments = find_zotero_pdf._attachments_for_item(conn, zotero_root, item.item_id)
            out.append(
                ZoteroItem(
                    item_key=item.key,
                    title=item.title,
                    year=item.year,
                    creators=item.creators,
                    citation_key=item.citation_key,
                    pdf_paths=[str(att.get("path") or "") for att in attachments if att.get("exists")],
                )
            )
        notes.append(f"loaded {len(out)} Zotero parent item(s)")
        return out, notes
    finally:
        conn.close()


def _path_key(path: str) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).expanduser().resolve())
    except OSError:
        return str(Path(path).expanduser())


def _basename_key(path: str) -> str:
    if not path:
        return ""
    return _normalize(Path(path).stem)


def _zotero_lookup(items: list[ZoteroItem]) -> dict[str, dict[str, ZoteroItem]]:
    by_pdf: dict[str, ZoteroItem] = {}
    by_pdf_stem: dict[str, ZoteroItem] = {}
    by_title: dict[str, ZoteroItem] = {}
    for item in items:
        title_key = _normalize(item.title)
        if title_key and title_key not in by_title:
            by_title[title_key] = item
        for pdf in item.pdf_paths:
            key = _path_key(pdf)
            if key:
                by_pdf[key] = item
            stem_key = _basename_key(pdf)
            if stem_key and stem_key not in by_pdf_stem:
                by_pdf_stem[stem_key] = item
    return {"by_pdf": by_pdf, "by_pdf_stem": by_pdf_stem, "by_title": by_title}


def _match_zotero_item(metadata: dict[str, Any], lookup: dict[str, dict[str, ZoteroItem]]) -> tuple[ZoteroItem | None, str]:
    source = _plain_text(metadata.get("source")).strip()
    if source:
        item = lookup["by_pdf"].get(_path_key(source))
        if item:
            return item, "zotero-pdf-path"
        item = lookup["by_pdf_stem"].get(_basename_key(source))
        if item:
            return item, "zotero-pdf-filename"

    title = _plain_text(metadata.get("title")).strip()
    if title:
        item = lookup["by_title"].get(_normalize(title))
        if item:
            return item, "zotero-title-exact"
    return None, "frontmatter-fallback"


def _authors_for_slug(item: ZoteroItem | None, metadata: dict[str, Any]) -> str:
    if item and item.creators:
        return item.creators[0]
    authors = metadata.get("authors") or metadata.get("author") or ""
    if isinstance(authors, list):
        return ", ".join(str(x) for x in authors)
    return _plain_text(authors)


def _year_for_slug(item: ZoteroItem | None, metadata: dict[str, Any]) -> str:
    if item and item.year:
        return item.year
    for key in ("year", "date", "published", "publicationDate"):
        year = _first_year(_plain_text(metadata.get(key)))
        if year:
            return year
    return ""


def _title_for_slug(source_path: Path, metadata: dict[str, Any], item: ZoteroItem | None) -> str:
    return _plain_text(metadata.get("title")).strip() or (item.title if item else "") or source_path.stem


def _dedupe_targets(rows: list[MigrationRow]) -> dict[str, list[str]]:
    groups: dict[str, list[MigrationRow]] = {}
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
            row.target_asset_path = row.asset_path.with_name(row.new_stem)
    return conflicts


def build_plan(wiki_root: Path, zotero_root: Path | None, zotero_config: Path) -> tuple[list[MigrationRow], dict[str, Any]]:
    source_dir = wiki_root / "sources" / "papers"
    asset_dir = source_dir / "assets"
    source_files = sorted(p for p in source_dir.glob("*.md") if p.is_file())
    zotero_items, notes = _resolve_zotero_items(zotero_root, zotero_config)
    lookup = _zotero_lookup(zotero_items)

    rows: list[MigrationRow] = []
    for source_path in source_files:
        post = _read_post(source_path)
        metadata = dict(post.metadata)
        item, match_reason = _match_zotero_item(metadata, lookup)
        title = _title_for_slug(source_path, metadata, item)
        citation_key = _plain_text(metadata.get("citationKey")).strip() or (item.citation_key if item else "")
        desired = _source_slug(
            title=title,
            citation_key=citation_key,
            authors=_authors_for_slug(item, metadata),
            year=_year_for_slug(item, metadata),
            bibtex="",
        )
        new_stem = desired
        rows.append(
            MigrationRow(
                old_stem=source_path.stem,
                new_stem=new_stem,
                desired_stem=desired,
                source_path=source_path,
                target_path=source_path.with_name(f"{new_stem}.md"),
                asset_path=asset_dir / source_path.stem,
                target_asset_path=asset_dir / new_stem,
                title=title,
                citation_key=citation_key,
                match_reason=match_reason,
                zotero_item_key=item.item_key if item else "",
            )
        )

    conflicts = _dedupe_targets(rows)
    existing_target_collisions = []
    planned_sources = {row.source_path.resolve() for row in rows}
    for row in rows:
        if row.target_path.resolve() == row.source_path.resolve():
            continue
        if row.target_path.exists() and row.target_path.resolve() not in planned_sources:
            existing_target_collisions.append(str(row.target_path.relative_to(wiki_root)))
        if row.target_asset_path.exists() and row.target_asset_path.resolve() != row.asset_path.resolve():
            existing_target_collisions.append(str(row.target_asset_path.relative_to(wiki_root)))

    meta = {
        "wiki_root": str(wiki_root),
        "source_count": len(source_files),
        "rename_count": sum(1 for row in rows if row.old_stem != row.new_stem),
        "zotero_notes": notes,
        "source_level_conflicts_resolved_with_old_stem_suffix": conflicts,
        "existing_target_collisions": sorted(set(existing_target_collisions)),
    }
    return rows, meta


def _replace_in_value(value: Any, replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, str):
        out = value
        for old, new in replacements:
            out = out.replace(old, new)
        return out
    if isinstance(value, list):
        return [_replace_in_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_in_value(item, replacements) for key, item in value.items()}
    return value


def _replacement_pairs(rows: list[MigrationRow]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if row.old_stem == row.new_stem:
            continue
        for prefix in SOURCE_LINK_PREFIXES:
            pairs.append((f"{prefix}{row.old_stem}.md", f"{prefix}{row.new_stem}.md"))
        pairs.append((f"assets/{row.old_stem}/", f"assets/{row.new_stem}/"))
    pairs.sort(key=lambda pair: len(pair[0]), reverse=True)
    return pairs


def _update_source_text(path: Path, row: MigrationRow, replacements: list[tuple[str, str]]) -> str:
    post = _read_post(path)
    metadata = dict(post.metadata)
    metadata = _replace_in_value(metadata, replacements)
    metadata["sourceSlug"] = row.new_stem
    if row.citation_key:
        metadata["citationKey"] = row.citation_key
    content = post.content
    for old, new in replacements:
        content = content.replace(old, new)
    return frontmatter.dumps(frontmatter.Post(content, **metadata)).rstrip() + "\n"


def apply_plan(wiki_root: Path, rows: list[MigrationRow], report_path: Path | None) -> dict[str, Any]:
    collisions = []
    planned_sources = {row.source_path.resolve() for row in rows}
    for row in rows:
        if row.source_path.resolve() != row.target_path.resolve():
            if row.target_path.exists() and row.target_path.resolve() not in planned_sources:
                collisions.append(str(row.target_path))
        if row.asset_path.exists() and row.asset_path.resolve() != row.target_asset_path.resolve():
            if row.target_asset_path.exists():
                collisions.append(str(row.target_asset_path))
    if collisions:
        raise RuntimeError("target collision(s): " + ", ".join(sorted(set(collisions))))

    replacements = _replacement_pairs(rows)
    _assert_apply_permissions(wiki_root, rows, replacements)
    by_source = {row.source_path.resolve(): row for row in rows}
    updated_markdown = 0

    for md_path in sorted(wiki_root.rglob("*.md")):
        resolved = md_path.resolve()
        old_text = md_path.read_text(encoding="utf-8", errors="ignore")
        if resolved in by_source:
            new_text = _update_source_text(md_path, by_source[resolved], replacements)
        else:
            new_text = old_text
            for old, new in replacements:
                new_text = new_text.replace(old, new)
        if new_text != old_text:
            md_path.write_text(new_text, encoding="utf-8")
            updated_markdown += 1

    moved_assets = 0
    for row in rows:
        if row.asset_path.exists() and row.asset_path.resolve() != row.target_asset_path.resolve():
            row.asset_path.rename(row.target_asset_path)
            moved_assets += 1

    renamed_sources = 0
    for row in rows:
        if row.source_path.exists() and row.source_path.resolve() != row.target_path.resolve():
            row.source_path.rename(row.target_path)
            renamed_sources += 1

    result = {
        "updated_markdown_files": updated_markdown,
        "renamed_source_files": renamed_sources,
        "renamed_asset_dirs": moved_assets,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _assert_apply_permissions(wiki_root: Path, rows: list[MigrationRow], replacements: list[tuple[str, str]]) -> None:
    """Fail before edits if the wiki vault is not writable from this process."""
    probe = wiki_root / ".llm-wiki-write-test.tmp"
    try:
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        raise PermissionError(f"wiki root is not writable: {wiki_root} ({exc})") from exc

    files_to_write: list[Path] = []
    source_paths = {row.source_path.resolve() for row in rows}
    for md_path in sorted(wiki_root.rglob("*.md")):
        resolved = md_path.resolve()
        if resolved in source_paths:
            files_to_write.append(md_path)
            continue
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        if any(old in text for old, _ in replacements):
            files_to_write.append(md_path)

    blocked = [str(path) for path in files_to_write if not path.exists()]
    for path in files_to_write:
        try:
            with path.open("a", encoding="utf-8"):
                pass
        except OSError as exc:
            blocked.append(f"{path} ({exc})")

    for row in rows:
        if row.source_path.exists() and row.source_path.resolve() != row.target_path.resolve():
            try:
                with row.source_path.open("a", encoding="utf-8"):
                    pass
            except OSError as exc:
                blocked.append(f"{row.source_path} ({exc})")
        if row.asset_path.exists() and row.asset_path.resolve() != row.target_asset_path.resolve():
            parent = row.asset_path.parent
            try:
                asset_probe = parent / ".llm-wiki-asset-rename-test.tmp"
                asset_probe.write_text("ok\n", encoding="utf-8")
                asset_probe.unlink()
            except OSError as exc:
                blocked.append(f"{parent} ({exc})")
                break

    if blocked:
        sample = "; ".join(blocked[:10])
        extra = f"; ... {len(blocked) - 10} more" if len(blocked) > 10 else ""
        raise PermissionError(f"wiki migration cannot write required path(s): {sample}{extra}")


def validate(wiki_root: Path) -> dict[str, Any]:
    source_dir = wiki_root / "sources" / "papers"
    issues: list[dict[str, str]] = []
    source_files = sorted(p for p in source_dir.glob("*.md") if p.is_file())

    for path in source_files:
        try:
            post = _read_post(path)
        except Exception as exc:
            issues.append({"file": str(path), "issue": f"frontmatter parse failed: {exc}"})
            continue
        source_slug = _plain_text(post.metadata.get("sourceSlug")).strip()
        if source_slug != path.stem:
            issues.append({
                "file": str(path.relative_to(wiki_root)),
                "issue": f"sourceSlug mismatch: {source_slug or '<missing>'} != {path.stem}",
            })
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"assets/([^)/]+)/", text):
            if match.group(1) != path.stem:
                issues.append({
                    "file": str(path.relative_to(wiki_root)),
                    "issue": f"asset stem mismatch: assets/{match.group(1)}/",
                })
                break

    source_link_re = re.compile(r"(?P<link>(?:\.\./|\./)?sources/papers/[^\s)]+\.md|@configured-sources-papers/[^\s)]+\.md|@wiki-sources-papers/[^\s)]+\.md)")
    for md_path in sorted(wiki_root.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8", errors="ignore")
        for match in source_link_re.finditer(text):
            link = match.group("link")
            if link.startswith("@configured-sources-papers/") or link.startswith("@wiki-sources-papers/"):
                target = source_dir / link.rsplit("/", 1)[-1]
            else:
                target = (md_path.parent / link).resolve()
            if not target.exists():
                issues.append({
                    "file": str(md_path.relative_to(wiki_root)),
                    "issue": f"broken prepared-source link: {link}",
                })

    return {
        "wiki_root": str(wiki_root),
        "source_count": len(source_files),
        "issue_count": len(issues),
        "issues": issues[:200],
    }


def _write_plan_report(report_path: Path | None, payload: dict[str, Any]) -> None:
    if not report_path:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--wiki-root", default="@configured", help="Wiki root path or runtime alias (default: @configured)")
    parser.add_argument("--zotero-root", default="", help="Optional Zotero data root")
    parser.add_argument("--zotero-config", default=str(find_zotero_pdf.DEFAULT_CONFIG_PATH), help="Path config containing zotero_roots")
    parser.add_argument("--report", default=".checkpoints/source-slug-migration.json", help="Write JSON report here")
    parser.add_argument("--yes", action="store_true", help="Apply the migration")
    parser.add_argument("--validate", action="store_true", help="Validate current wiki links/sourceSlug consistency")
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

    rows, meta = build_plan(wiki_root, zotero_root, zotero_config)
    payload = {
        "mode": "apply" if args.yes else "dry-run",
        **meta,
        "renames": [row.as_dict(wiki_root) for row in rows if row.old_stem != row.new_stem],
    }

    if meta["existing_target_collisions"]:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    if not args.yes:
        _write_plan_report(report_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    apply_result = apply_plan(wiki_root, rows, None)
    validation = validate(wiki_root)
    payload["apply_result"] = apply_result
    payload["validation"] = validation
    _write_plan_report(report_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if validation["issue_count"] == 0 else 1


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())

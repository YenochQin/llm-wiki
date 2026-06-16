#!/usr/bin/env python3
"""Locate a paper PDF in a local Zotero data directory.

This is a small, read-only helper for `/ingest`: given a Zotero data root and a
paper identifier (title, DOI, Zotero item key, or a filename-like attachment
hint), inspect `zotero.sqlite` and return candidate PDF attachments with enough
metadata for the caller to pick or prepare the source.

Supported Zotero attachment forms:
  - imported attachments under storage/<attachmentKey>/<filename>.pdf
  - linked-file attachments with a file:// path
  - linked-file attachments relative to the configured Zotero data root

The tool never modifies Zotero files and opens the database in read-only mode.

Purpose:
    Resolve a paper identifier to candidate local PDF attachment paths and
    normalized Zotero metadata.

Inputs:
    Title/query, DOI, or Zotero item key plus an optional Zotero root/config.

Writes:
    Nothing. Results are printed as JSON. A read-only SQLite snapshot may be
    created under config/zotero-cache/ to avoid locking the live Zotero DB.

Usage:
    uv run python -X utf8 tools/find_zotero_pdf.py --title "Paper title"
    uv run python -X utf8 tools/find_zotero_pdf.py --doi 10.1234/example
    uv run python -X utf8 tools/find_zotero_pdf.py --item-key ABC123
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from _cli_io import configure_utf8_stdio
from _zotero_snapshot import prepare_snapshot

ATTACHMENT_LINK_MODE_IMPORTED_URL = 0
ATTACHMENT_LINK_MODE_IMPORTED_FILE = 1
ATTACHMENT_LINK_MODE_LINKED_FILE = 2
DEFAULT_CONFIG_PATH = Path("config/paths.json")


@dataclass
class ItemRecord:
    item_id: int
    key: str
    item_type: str
    title: str
    doi: str
    year: str
    creators: list[str]
    citation_key: str = ""


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"doi:\s*", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value)
    return " ".join(value.split())


def _normalize_doi(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.strip().strip(".")


def _looks_like_filename_query(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if any(sep in text for sep in ("/", "\\")):
        return True
    lower = text.lower()
    if lower.endswith(".pdf"):
        return True
    base = Path(unquote(text)).name
    stem = Path(base).stem
    return bool(
        re.search(r"\d", base)
        and (
            re.search(r"[_-]", stem)
            or len(_tokens(stem)) <= 3
        )
    )


def _tokens(value: str) -> set[str]:
    return {t for t in _normalize_text(value).split() if len(t) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _connect(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _expand_path_template(value: str) -> str:
    expanded = os.path.expandvars(value)
    expanded = re.sub(
        r"%([A-Za-z_][A-Za-z0-9_]*)%",
        lambda m: os.environ.get(m.group(1), m.group(0)),
        expanded,
    )
    return os.path.expanduser(expanded)


def _current_platform_profile() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return system or "unknown"


def _select_paths_profile(payload: dict) -> tuple[str, dict]:
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        return "legacy", payload

    requested = os.environ.get("LLM_WIKI_PATH_PROFILE", "").strip()
    active = requested or str(payload.get("active_profile") or "auto")
    selected = _current_platform_profile() if active == "auto" else active
    profile_cfg = profiles.get(selected)

    if not isinstance(profile_cfg, dict):
        fallback = payload.get("fallback_profile")
        if isinstance(fallback, str) and isinstance(profiles.get(fallback), dict):
            selected = fallback
            profile_cfg = profiles[fallback]
        else:
            profile_cfg = {}
    return selected, profile_cfg


def _unescape_pref_string(value: str) -> str:
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def _data_dir_from_prefs(path: Path) -> Path | None:
    prefs = path / "prefs.js"
    if not prefs.exists():
        return None
    text = prefs.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        r'user_pref\("extensions\.zotero\.dataDir",\s*"((?:\\.|[^"])*)"\)',
        text,
    )
    if not match:
        return None
    raw = _unescape_pref_string(match.group(1)).strip()
    if not raw:
        return None
    data_dir = Path(raw).expanduser()
    if not data_dir.is_absolute():
        data_dir = (path / data_dir).resolve()
    return data_dir


def _resolve_zotero_root(input_root: Path) -> tuple[Path, list[str]]:
    root = Path(_expand_path_template(str(input_root))).resolve()
    notes: list[str] = []
    if (root / "zotero.sqlite").exists():
        return root, notes
    prefs_data_dir = _data_dir_from_prefs(root)
    if prefs_data_dir:
        notes.append(f"resolved Zotero dataDir from prefs.js: {prefs_data_dir}")
        return prefs_data_dir.expanduser().resolve(), notes
    nested = root / "Zotero"
    if (nested / "zotero.sqlite").exists():
        notes.append(f"resolved nested Zotero data directory: {nested}")
        return nested.resolve(), notes
    return root, notes


def _candidate_roots_from_config(config_path: Path) -> tuple[list[Path], list[str]]:
    notes: list[str] = []
    if not config_path.exists():
        return [], [f"path config not found: {config_path}"]
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"failed to read path config {config_path}: {exc}"]

    profile_note = ""
    if isinstance(payload, dict) and "profiles" in payload:
        profile_name, profile_cfg = _select_paths_profile(payload)
        raw_entries = profile_cfg.get("zotero_roots") or payload.get("zotero_roots") or []
        profile_note = f" for profile {profile_name}"
    elif isinstance(payload, dict):
        raw_entries = payload.get("zotero_roots", payload.get("roots", payload))
        if "roots" in payload:
            profile_note = " from legacy roots config"
    else:
        raw_entries = payload
        profile_note = " from legacy roots config"

    if not isinstance(raw_entries, list):
        return [], [f"path config must contain a zotero_roots list or legacy roots list: {config_path}"]

    roots: list[Path] = []
    seen: set[str] = set()
    for entry in raw_entries:
        if isinstance(entry, str):
            enabled = True
            raw_path = entry
        elif isinstance(entry, dict):
            enabled = bool(entry.get("enabled", True))
            raw_path = str(entry.get("path") or "")
        else:
            continue
        if not enabled or not raw_path.strip():
            continue

        expanded = _expand_path_template(raw_path)
        matches = sorted(Path(p).resolve() for p in glob.glob(expanded))
        if not matches:
            matches = [Path(expanded).resolve()]
        for path in matches:
            key = str(path)
            if key in seen:
                continue
            roots.append(path)
            seen.add(key)
    notes.append(f"loaded {len(roots)} zotero root candidate(s){profile_note} from {config_path}")
    return roots, notes


def _discover_zotero_root(config_path: Path) -> tuple[Path | None, list[str]]:
    roots, notes = _candidate_roots_from_config(config_path)
    for candidate in roots:
        resolved, root_notes = _resolve_zotero_root(candidate)
        notes.extend([f"{candidate}: {note}" for note in root_notes])
        if (resolved / "zotero.sqlite").exists():
            notes.append(f"selected Zotero root: {resolved}")
            return resolved, notes
    notes.append("no configured Zotero root contains zotero.sqlite")
    return None, notes


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1]) for row in rows}


def _field_id_map(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        str(name): int(field_id)
        for field_id, name in conn.execute("SELECT fieldID, fieldName FROM fields")
    }


def _item_type_map(conn: sqlite3.Connection) -> dict[int, str]:
    return {
        int(type_id): str(type_name)
        for type_id, type_name in conn.execute("SELECT itemTypeID, typeName FROM itemTypes")
    }


def _value_for_field(
    conn: sqlite3.Connection,
    item_id: int,
    field_ids: dict[str, int],
    field_names: list[str],
) -> str:
    ids = [field_ids[name] for name in field_names if name in field_ids]
    if not ids:
        return ""
    placeholders = ",".join("?" for _ in ids)
    row = conn.execute(
        f"""
        SELECT itemDataValues.value
        FROM itemData
        JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        WHERE itemData.itemID = ? AND itemData.fieldID IN ({placeholders})
        LIMIT 1
        """,
        [item_id, *ids],
    ).fetchone()
    return str(row[0]) if row else ""


def _creators_for_item(conn: sqlite3.Connection, item_id: int) -> list[str]:
    try:
        rows = conn.execute(
            """
            SELECT creators.firstName, creators.lastName
            FROM itemCreators
            JOIN creators ON itemCreators.creatorID = creators.creatorID
            WHERE itemCreators.itemID = ?
            ORDER BY itemCreators.orderIndex
            """,
            (item_id,),
        ).fetchall()
    except sqlite3.Error:
        return []
    creators = []
    for first, last in rows:
        name = " ".join(part for part in (str(first or "").strip(), str(last or "").strip()) if part)
        if name:
            creators.append(name)
    return creators


def _all_parent_items(conn: sqlite3.Connection) -> list[ItemRecord]:
    field_ids = _field_id_map(conn)
    item_types = _item_type_map(conn)
    rows = conn.execute(
        """
        SELECT items.itemID, items.key, items.itemTypeID
        FROM items
        LEFT JOIN itemAttachments ON items.itemID = itemAttachments.itemID
        WHERE itemAttachments.itemID IS NULL
        """
    ).fetchall()
    records: list[ItemRecord] = []
    for item_id, key, item_type_id in rows:
        item_id = int(item_id)
        records.append(
            ItemRecord(
                item_id=item_id,
                key=str(key),
                item_type=item_types.get(int(item_type_id), ""),
                title=_value_for_field(conn, item_id, field_ids, ["title"]),
                doi=_normalize_doi(_value_for_field(conn, item_id, field_ids, ["DOI"])),
                year=_value_for_field(conn, item_id, field_ids, ["date"])[:4],
                creators=_creators_for_item(conn, item_id),
                citation_key=_value_for_field(conn, item_id, field_ids, ["citationKey"]),
            )
        )
    return records


def _score_item(item: ItemRecord, query: str, doi: str, item_key: str) -> tuple[float, str]:
    if item_key and item.key.lower() == item_key.lower():
        return 1.0, "item-key"
    if doi and item.doi and _normalize_doi(item.doi) == doi:
        return 0.98, "doi"
    q_norm = _normalize_text(query)
    title_norm = _normalize_text(item.title)
    if q_norm and title_norm:
        if q_norm == title_norm:
            return 0.95, "exact-title"
        if q_norm in title_norm or title_norm in q_norm:
            return 0.88, "title-containment"
        token_score = _jaccard(_tokens(q_norm), _tokens(title_norm))
        if token_score:
            return min(0.80, token_score), "title-token-overlap"
    return 0.0, ""


def _attachment_name_values(attachment: dict) -> list[str]:
    values: list[str] = []
    path = str(attachment.get("path") or "").strip()
    title = str(attachment.get("title") or "").strip()
    if path:
        values.extend([path, Path(path).name, Path(path).stem])
    if title:
        values.append(title)
    return values


def _score_attachment_match(attachments: list[dict], query: str) -> tuple[float, str]:
    q_raw = query.strip()
    if not q_raw:
        return 0.0, ""
    q_norm = _normalize_text(q_raw)
    q_base = Path(unquote(q_raw)).name
    q_stem = Path(q_base).stem
    q_base_norm = _normalize_text(q_base)
    q_stem_norm = _normalize_text(q_stem)
    q_tokens = _tokens(q_norm)
    filename_like = _looks_like_filename_query(q_raw)

    best_score = 0.0
    best_reason = ""
    for attachment in attachments:
        if not attachment.get("exists"):
            continue
        for value in _attachment_name_values(attachment):
            v_norm = _normalize_text(value)
            if not v_norm:
                continue
            score = 0.0
            reason = ""
            if q_base_norm and q_base_norm == v_norm:
                score, reason = 0.99, "attachment-filename-exact"
            elif q_stem_norm and q_stem_norm == v_norm:
                score, reason = 0.98, "attachment-stem-exact"
            elif q_base_norm and (q_base_norm in v_norm or v_norm in q_base_norm):
                score, reason = 0.90, "attachment-filename-containment"
            elif q_stem_norm and (q_stem_norm in v_norm or v_norm in q_stem_norm):
                score, reason = 0.88, "attachment-stem-containment"
            else:
                token_score = _jaccard(q_tokens, _tokens(v_norm))
                if token_score:
                    score = min(0.85, token_score if filename_like else token_score * 0.8)
                    reason = "attachment-token-overlap"
            if score > best_score:
                best_score = score
                best_reason = reason
    return best_score, best_reason


def _candidate_items(
    conn: sqlite3.Connection,
    zotero_root: Path,
    query: str,
    doi: str,
    item_key: str,
    limit: int,
) -> list[tuple[ItemRecord, float, str, list[dict], tuple[float, str]]]:
    scored = []
    for item in _all_parent_items(conn):
        attachments = _attachments_for_item(conn, zotero_root, item.item_id)
        score, reason = _score_item(item, query, doi, item_key)
        attachment_score, attachment_reason = _score_attachment_match(attachments, query)
        if attachment_score > score:
            score, reason = attachment_score, attachment_reason
        if score >= 0.20:
            scored.append((item, score, reason, attachments, (attachment_score, attachment_reason)))
    scored.sort(key=lambda x: (-x[1], x[0].title.lower()))
    return scored[:limit]


def _resolve_attachment_path(zotero_root: Path, attachment_key: str, path_value: str, link_mode: int | None) -> Path | None:
    raw = (path_value or "").strip()
    if not raw:
        return None
    raw = raw.replace("storage:", "")
    if raw.startswith("file://"):
        parsed = urlparse(raw)
        return Path(unquote(parsed.path)).expanduser()
    candidate = Path(unquote(raw)).expanduser()
    if candidate.is_absolute():
        return candidate
    if link_mode in {ATTACHMENT_LINK_MODE_IMPORTED_URL, ATTACHMENT_LINK_MODE_IMPORTED_FILE}:
        return zotero_root / "storage" / attachment_key / candidate.name
    return zotero_root / candidate


def _attachments_for_item(conn: sqlite3.Connection, zotero_root: Path, parent_item_id: int) -> list[dict]:
    columns = _table_columns(conn, "itemAttachments")
    select_cols = ["itemAttachments.itemID", "items.key"]
    for col in ("path", "contentType", "linkMode", "title"):
        if col in columns:
            select_cols.append(f"itemAttachments.{col}")
        else:
            select_cols.append(f"NULL AS {col}")
    rows = conn.execute(
        f"""
        SELECT {", ".join(select_cols)}
        FROM itemAttachments
        JOIN items ON itemAttachments.itemID = items.itemID
        WHERE itemAttachments.parentItemID = ?
        """,
        (parent_item_id,),
    ).fetchall()
    attachments = []
    for row in rows:
        att_item_id, att_key, path_value, content_type, link_mode, title = row
        resolved = _resolve_attachment_path(
            zotero_root,
            str(att_key),
            str(path_value or ""),
            int(link_mode) if link_mode is not None else None,
        )
        is_pdf = False
        if resolved and resolved.suffix.lower() == ".pdf":
            is_pdf = True
        if str(content_type or "").lower() == "application/pdf":
            is_pdf = True
        if not is_pdf:
            continue
        attachments.append({
            "attachment_item_id": int(att_item_id),
            "attachment_key": str(att_key),
            "title": str(title or ""),
            "path": str(resolved) if resolved else "",
            "exists": bool(resolved and resolved.exists()),
            "link_mode": int(link_mode) if link_mode is not None else None,
            "content_type": str(content_type or ""),
        })
    attachments.sort(key=lambda x: (not x["exists"], x["path"]))
    return attachments


def find(zotero_root: Path | None, query: str, doi: str, item_key: str, limit: int, config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if zotero_root is None:
        input_root = None
        zotero_root, notes = _discover_zotero_root(config_path)
        if zotero_root is None:
            return {
                "status": "error",
                "message": "no usable Zotero root found",
                "input_root": None,
                "zotero_root": None,
                "config_path": str(config_path),
                "notes": notes,
                "candidates": [],
            }
    else:
        input_root = Path(_expand_path_template(str(zotero_root))).resolve()
        zotero_root, notes = _resolve_zotero_root(input_root)
    snapshot_root, snapshot_notes = prepare_snapshot(Path.cwd(), zotero_root)
    notes.extend(snapshot_notes)
    db_path = snapshot_root / "zotero.sqlite"
    if not db_path.exists():
        return {
            "status": "error",
            "message": f"zotero.sqlite not found under {zotero_root}",
            "input_root": str(input_root) if input_root is not None else None,
            "zotero_root": str(zotero_root),
            "config_path": str(config_path),
            "notes": notes,
            "candidates": [],
        }
    conn = _connect(db_path)
    try:
        candidates = []
        for item, score, reason, attachments, attachment_match in _candidate_items(
            conn, zotero_root, query, _normalize_doi(doi), item_key, limit
        ):
            best_attachment_score, best_attachment_reason = attachment_match
            best_attachment_path = ""
            if best_attachment_score >= 0.20:
                for att in attachments:
                    if not att.get("exists"):
                        continue
                    att_score, att_reason = _score_attachment_match([att], query)
                    if att_score == best_attachment_score and att_reason == best_attachment_reason:
                        best_attachment_path = str(att.get("path") or "")
                        break
            candidates.append({
                "score": round(score, 3),
                "match_reason": reason,
                "item_key": item.key,
                "item_id": item.item_id,
                "item_type": item.item_type,
                "title": item.title,
                "doi": item.doi,
                "year": item.year,
                "creators": item.creators,
                "citation_key": item.citation_key,
                "attachments": attachments,
                "best_attachment": {
                    "path": best_attachment_path,
                    "score": round(best_attachment_score, 3),
                    "match_reason": best_attachment_reason,
                } if best_attachment_path else None,
                "pdf_paths": [att["path"] for att in attachments if att.get("exists")],
            })
        return {
            "status": "ok",
            "input_root": str(input_root) if input_root is not None else None,
            "zotero_root": str(zotero_root),
            "config_path": str(config_path),
            "notes": notes,
            "query": query,
            "doi": _normalize_doi(doi),
            "item_key": item_key,
            "candidates": candidates,
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--zotero-root", type=Path,
                        help="Zotero data directory containing zotero.sqlite and storage/, or a profile directory with prefs.js. If omitted, config/paths.json is scanned.")
    parser.add_argument("--zotero-config", default=DEFAULT_CONFIG_PATH, type=Path,
                        help="JSON path config with profile zotero_roots, or a legacy roots file (default: config/paths.json).")
    parser.add_argument("--query", default="", help="Paper title or free-text query.")
    parser.add_argument("--title", default="", help="Paper title. Alias for --query.")
    parser.add_argument("--doi", default="", help="DOI to match.")
    parser.add_argument("--item-key", default="", help="Zotero item key to match exactly.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum item candidates to return.")
    args = parser.parse_args()

    query = args.query or args.title
    if not (query or args.doi or args.item_key):
        parser.error("provide at least one of --title, --query, --doi, or --item-key")

    result = find(args.zotero_root, query, args.doi, args.item_key, args.limit, args.zotero_config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "ok":
        raise SystemExit(2)


if __name__ == "__main__":
    configure_utf8_stdio()
    try:
        main()
    except sqlite3.DatabaseError as exc:
        print(json.dumps({"status": "error", "message": f"sqlite error: {exc}"}), file=sys.stderr)
        raise SystemExit(2)

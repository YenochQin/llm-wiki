#!/usr/bin/env python3
"""List Zotero item citation keys, titles, and DOIs under a collection path."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

import find_zotero_pdf
from _zotero_snapshot import prepare_snapshot


EXCLUDED_ITEM_TYPES = {"attachment", "note", "annotation"}


def _connect(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _field_ids(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        str(name): int(field_id)
        for field_id, name in conn.execute("SELECT fieldID, fieldName FROM fields")
    }


def _item_types(conn: sqlite3.Connection) -> dict[int, str]:
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


def _all_values(conn: sqlite3.Connection, item_id: int) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT fields.fieldName, itemDataValues.value
        FROM itemData
        JOIN fields ON itemData.fieldID = fields.fieldID
        JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        WHERE itemData.itemID = ?
        """,
        (item_id,),
    ).fetchall()
    return {str(row["fieldName"]): str(row["value"]) for row in rows}


def _collection_path(conn: sqlite3.Connection, collection_id: int) -> list[str]:
    parts: list[str] = []
    current: int | None = collection_id
    while current is not None:
        row = conn.execute(
            """
            SELECT collectionName, parentCollectionID
            FROM collections
            WHERE collectionID = ?
            """,
            (current,),
        ).fetchone()
        if row is None:
            break
        parts.append(str(row["collectionName"]))
        current = row["parentCollectionID"]
    return list(reversed(parts))


def _normalize_collection_path(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*(?:/|>|::)\s*", value.strip()) if part.strip()]


def _find_collection_ids(conn: sqlite3.Connection, collection_path: str) -> list[int]:
    wanted = _normalize_collection_path(collection_path)
    if not wanted:
        raise ValueError("collection path is empty")
    matches: list[int] = []
    rows = conn.execute(
        "SELECT collectionID FROM collections WHERE collectionName = ?",
        (wanted[-1],),
    ).fetchall()
    for row in rows:
        collection_id = int(row["collectionID"])
        actual = _collection_path(conn, collection_id)
        if actual[-len(wanted) :] == wanted:
            matches.append(collection_id)
    return matches


def _descendant_collection_ids(conn: sqlite3.Connection, collection_id: int) -> list[int]:
    out = [collection_id]
    stack = [collection_id]
    while stack:
        current = stack.pop()
        rows = conn.execute(
            "SELECT collectionID FROM collections WHERE parentCollectionID = ?",
            (current,),
        ).fetchall()
        for row in rows:
            child = int(row["collectionID"])
            out.append(child)
            stack.append(child)
    return out


def _collection_item_rows(
    conn: sqlite3.Connection,
    collection_ids: list[int],
) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in collection_ids)
    return conn.execute(
        f"""
        SELECT DISTINCT items.itemID, items.key, items.itemTypeID
        FROM collectionItems
        JOIN items ON collectionItems.itemID = items.itemID
        LEFT JOIN deletedItems ON deletedItems.itemID = items.itemID
        WHERE collectionItems.collectionID IN ({placeholders})
          AND deletedItems.itemID IS NULL
        ORDER BY collectionItems.orderIndex, items.itemID
        """,
        collection_ids,
    ).fetchall()


def list_collection(
    *,
    collection_path: str,
    zotero_root: Path | None = None,
    zotero_config: Path = find_zotero_pdf.DEFAULT_CONFIG_PATH,
    recursive: bool = True,
) -> dict[str, Any]:
    if zotero_root is None:
        resolved_root, notes = find_zotero_pdf._discover_zotero_root(zotero_config)
        input_root = None
        if resolved_root is None:
            return {
                "status": "error",
                "message": "no usable Zotero root found",
                "zotero_root": None,
                "config_path": str(zotero_config),
                "notes": notes,
                "items": [],
            }
        zotero_root = resolved_root
    else:
        input_root = Path(find_zotero_pdf._expand_path_template(str(zotero_root))).resolve()
        zotero_root, notes = find_zotero_pdf._resolve_zotero_root(input_root)

    snapshot_root, snapshot_notes = prepare_snapshot(Path.cwd(), zotero_root)
    notes.extend(snapshot_notes)
    db_path = snapshot_root / "zotero.sqlite"
    if not db_path.exists():
        return {
            "status": "error",
            "message": f"zotero.sqlite not found under {zotero_root}",
            "input_root": str(input_root) if input_root is not None else None,
            "zotero_root": str(zotero_root),
            "config_path": str(zotero_config),
            "notes": notes,
            "items": [],
        }

    conn = _connect(db_path)
    try:
        matches = _find_collection_ids(conn, collection_path)
        if not matches:
            return {
                "status": "error",
                "message": f"collection path not found: {collection_path}",
                "zotero_root": str(zotero_root),
                "config_path": str(zotero_config),
                "notes": notes,
                "items": [],
            }
        if len(matches) > 1:
            paths = [{"collection_id": cid, "path": _collection_path(conn, cid)} for cid in matches]
            return {
                "status": "error",
                "message": f"ambiguous collection path: {collection_path}",
                "zotero_root": str(zotero_root),
                "config_path": str(zotero_config),
                "notes": notes,
                "matches": paths,
                "items": [],
            }

        collection_id = matches[0]
        collection_ids = (
            _descendant_collection_ids(conn, collection_id)
            if recursive
            else [collection_id]
        )
        field_ids = _field_ids(conn)
        item_types = _item_types(conn)
        items: list[dict[str, Any]] = []
        for row in _collection_item_rows(conn, collection_ids):
            item_id = int(row["itemID"])
            item_type = item_types.get(int(row["itemTypeID"]), "")
            if item_type in EXCLUDED_ITEM_TYPES:
                continue
            values = _all_values(conn, item_id)
            items.append({
                "citationKey": _value_for_field(conn, item_id, field_ids, ["citationKey"]).strip(),
                "title": values.get("title") or values.get("name") or "",
                "doi": find_zotero_pdf._normalize_doi(values.get("DOI", "")),
            })

        return {
            "status": "ok",
            "collection_path": _collection_path(conn, collection_id),
            "collection_id": collection_id,
            "recursive": recursive,
            "item_count": len(items),
            "missing_citation_key_count": sum(1 for item in items if not item["citationKey"]),
            "missing_doi_count": sum(1 for item in items if not item["doi"]),
            "zotero_root": str(zotero_root),
            "config_path": str(zotero_config),
            "notes": notes,
            "items": items,
        }
    finally:
        conn.close()


def _escape_md_cell(value: Any) -> str:
    text = str(value or "").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|").strip()


def _to_markdown(result: dict[str, Any]) -> str:
    path = " / ".join(result.get("collection_path") or [])
    lines = [
        f"# Zotero collection: {path}",
        "",
        f"- Items: {result.get('item_count', 0)}",
        f"- Missing citationKey: {result.get('missing_citation_key_count', 0)}",
        f"- Missing DOI: {result.get('missing_doi_count', 0)}",
        "",
        "| citationKey | title | doi |",
        "|---|---|---|",
    ]
    for item in result.get("items", []):
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_md_cell(item.get("citationKey", "")),
                    _escape_md_cell(item.get("title", "")),
                    _escape_md_cell(item.get("doi", "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _write_markdown(result: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_to_markdown(result), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("collection", nargs="?", default="", help="Collection path, e.g. '2026/202605/0507'.")
    parser.add_argument("--collection", dest="collection_flag", default="", help="Collection path. Alias for positional argument.")
    parser.add_argument("--zotero-root", type=Path, help="Zotero data/profile root. Defaults to config scan.")
    parser.add_argument("--zotero-config", default=find_zotero_pdf.DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--no-recursive", action="store_true", help="Only list direct items, not subcollection descendants.")
    parser.add_argument("--output-md", type=Path, help="Write citationKey/title/doi table to a Markdown file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Default output is JSON.")
    args = parser.parse_args()

    collection = args.collection_flag or args.collection
    if not collection.strip():
        parser.error("provide a collection path, e.g. '2026/202605/0507'")

    result = list_collection(
        collection_path=collection,
        zotero_root=args.zotero_root,
        zotero_config=args.zotero_config,
        recursive=not args.no_recursive,
    )
    if args.output_md and result.get("status") == "ok":
        _write_markdown(result, args.output_md)
        result["output_md"] = str(args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "ok":
        raise SystemExit(2)


if __name__ == "__main__":
    try:
        main()
    except sqlite3.DatabaseError as exc:
        print(json.dumps({"status": "error", "message": f"sqlite error: {exc}"}), file=sys.stderr)
        raise SystemExit(2)

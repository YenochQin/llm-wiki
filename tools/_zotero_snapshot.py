#!/usr/bin/env python3
"""Lightweight Zotero SQLite snapshot helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

SNAPSHOT_DB_FILES = ("zotero.sqlite", "zotero.sqlite-wal", "zotero.sqlite-shm")


def snapshot_key(zotero_root: Path) -> str:
    return hashlib.sha1(str(zotero_root.resolve()).encode("utf-8")).hexdigest()[:16]


def snapshot_dir(project_root: Path, zotero_root: Path) -> Path:
    return project_root.resolve() / "config" / "zotero-cache" / snapshot_key(zotero_root)


def snapshot_signature(zotero_root: Path) -> dict[str, object]:
    signature: dict[str, object] = {"root": str(zotero_root.resolve())}
    for name in SNAPSHOT_DB_FILES:
        src = zotero_root / name
        if src.exists():
            stat = src.stat()
            signature[name] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        else:
            signature[name] = None
    return signature


def prepare_snapshot(project_root: Path, zotero_root: Path) -> tuple[Path, list[str]]:
    snapshot = snapshot_dir(project_root, zotero_root)
    snapshot.mkdir(parents=True, exist_ok=True)
    manifest_path = snapshot / "snapshot.json"
    signature = snapshot_signature(zotero_root)
    notes: list[str] = []

    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            notes.append(f"ignored unreadable Zotero snapshot manifest: {exc}")
        else:
            if existing.get("signature") == signature and (snapshot / "zotero.sqlite").exists():
                notes.append(f"reused Zotero snapshot: {snapshot}")
                return snapshot, notes

    for name in SNAPSHOT_DB_FILES:
        src = zotero_root / name
        dst = snapshot / name
        if src.exists():
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()

    manifest_path.write_text(
        json.dumps({"signature": signature}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    notes.append(f"created Zotero snapshot: {snapshot}")
    return snapshot, notes

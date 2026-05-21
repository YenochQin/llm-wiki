#!/usr/bin/env python3
"""Resolve Zotero metadata for a local PDF and return a derived BibTeX entry.

This helper is for `/ingest-local-pdf`: the PDF content still comes from the
user-provided local file, but bibliographic metadata may be enriched from a
matching Zotero item when the user has already imported that PDF into Zotero.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from _cli_io import configure_utf8_stdio
import fetch_zotero_metadata
import find_zotero_pdf


CONFIDENT_REASONS = {
    "item-key",
    "doi",
    "exact-title",
    "title-containment",
    "attachment-filename-exact",
    "attachment-stem-exact",
    "attachment-filename-containment",
    "attachment-stem-containment",
}


def _norm_path(value: str) -> str:
    try:
        return str(Path(value).expanduser().resolve())
    except OSError:
        return str(Path(value).expanduser())


def _attachment_matches_source(candidate: dict[str, Any], source: Path) -> bool:
    source_path = _norm_path(str(source))
    paths = [str(p or "") for p in candidate.get("pdf_paths") or []]
    attachments = candidate.get("attachments") or []
    if isinstance(attachments, list):
        paths.extend(str(att.get("path") or "") for att in attachments if isinstance(att, dict))
    return any(path and _norm_path(path) == source_path for path in paths)


def _choose_candidate(candidates: list[dict[str, Any]], source: Path) -> tuple[dict[str, Any] | None, str]:
    if not candidates:
        return None, "no Zotero candidates"

    exact_attachment = [c for c in candidates if _attachment_matches_source(c, source)]
    if len(exact_attachment) == 1:
        return exact_attachment[0], "exact local PDF attachment path"
    if len(exact_attachment) > 1:
        return None, "multiple Zotero items have the same local PDF attachment path"

    top = candidates[0]
    score = float(top.get("score") or 0.0)
    reason = str(top.get("match_reason") or "")
    if score >= 0.88 and reason in CONFIDENT_REASONS:
        return top, f"{reason} score={score:.2f}"
    return None, f"top candidate not confident enough: {reason} score={score:.2f}"


def _validate_core_bibtex(bibtex: str) -> list[str]:
    fields = {
        field.lower()
        for field in re.findall(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=", bibtex, flags=re.MULTILINE)
    }
    missing = sorted({"author", "title", "year"} - fields)
    warnings = [f"BibTeX missing required field: {field}" for field in missing]
    return warnings


def enrich(
    source: Path,
    title: str = "",
    doi: str = "",
    zotero_root: Path | None = None,
    zotero_config: Path = find_zotero_pdf.DEFAULT_CONFIG_PATH,
    api_base: str = "",
    timeout: float = fetch_zotero_metadata.DEFAULT_TIMEOUT,
    limit: int = 5,
) -> dict[str, Any]:
    query = title.strip() or source.name
    result = find_zotero_pdf.find(
        zotero_root=zotero_root,
        query=query,
        doi=doi,
        item_key="",
        limit=limit,
        config_path=zotero_config,
    )
    notes = list(result.get("notes") or [])
    if result.get("status") != "ok":
        return {
            "status": "not_found",
            "message": result.get("message", "Zotero lookup failed"),
            "query": query,
            "notes": notes,
            "candidates": result.get("candidates", []),
        }

    candidates = result.get("candidates") or []
    candidate, reason = _choose_candidate(candidates, source)
    if not candidate:
        return {
            "status": "not_found",
            "message": reason,
            "query": query,
            "notes": notes,
            "candidates": candidates,
        }

    item_key = str(candidate.get("item_key") or "")
    try:
        metadata_result = {
            "status": "ok",
            "source": "zotero-local-api",
            "metadata": fetch_zotero_metadata.fetch_item(
                item_key,
                api_base=api_base,
                timeout=timeout,
            ),
        }
    except Exception as exc:
        return {
            "status": "metadata_error",
            "message": str(exc),
            "hint": "Open Zotero Desktop and enable local API access, then retry; SQLite matching found the item but local API metadata fetch failed.",
            "query": query,
            "candidate": candidate,
            "notes": notes,
        }

    metadata = metadata_result["metadata"]
    bibtex = str(metadata.get("bibtex") or "").strip()
    warnings = _validate_core_bibtex(bibtex)
    return {
        "status": "ok",
        "query": query,
        "match": {
            "reason": reason,
            "item_key": item_key,
            "title": candidate.get("title", ""),
            "doi": candidate.get("doi", ""),
            "score": candidate.get("score", 0),
        },
        "metadata": metadata,
        "citation_key": str(metadata.get("citation_key") or metadata.get("citekey") or ""),
        "paper_slug": str(metadata.get("paper_slug") or ""),
        "authors": metadata.get("authors") or [],
        "year": metadata.get("year") or "",
        "bibtex": bibtex,
        "warnings": warnings,
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path, help="Local PDF path being ingested.")
    parser.add_argument("--title", default="", help="Confident title recovered from the PDF first page.")
    parser.add_argument("--doi", default="", help="Optional DOI hint.")
    parser.add_argument("--zotero-root", type=Path, help="Zotero data/profile root. Defaults to config scan.")
    parser.add_argument("--zotero-config", default=find_zotero_pdf.DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--api-base", default="", help="Zotero Local API base URL.")
    parser.add_argument("--timeout", type=float, default=fetch_zotero_metadata.DEFAULT_TIMEOUT)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    result = enrich(
        source=args.source,
        title=args.title,
        doi=args.doi,
        zotero_root=args.zotero_root,
        zotero_config=args.zotero_config,
        api_base=args.api_base,
        timeout=args.timeout,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") != "ok":
        raise SystemExit(2)


if __name__ == "__main__":
    configure_utf8_stdio()
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)

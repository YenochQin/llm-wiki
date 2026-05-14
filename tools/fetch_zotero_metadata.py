#!/usr/bin/env python3
"""Fetch read-only bibliographic metadata from Zotero Desktop's local API.

The helper is intentionally optional for `/ingest`: when Zotero Desktop is not
running or local API access is disabled, callers should fall back to the
existing SQLite PDF lookup plus Crossref enrichment path. Successful responses
include normalized metadata plus a derived plain BibTeX entry in
``metadata.bibtex``.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_API_BASE = "http://127.0.0.1:23119/api"
DEFAULT_TIMEOUT = 5
ENTRY_TYPE_MAP = {
    "journalarticle": "article",
    "book": "book",
    "booksection": "incollection",
    "conferencepaper": "inproceedings",
    "conference": "inproceedings",
    "thesis": "thesis",
    "report": "techreport",
    "webpage": "misc",
    "preprint": "misc",
    "dataset": "misc",
    "patent": "patent",
}


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _key_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _plain_note(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _year_from_date(value: Any) -> int | None:
    match = re.search(r"\d{4}", str(value or ""))
    return int(match.group(0)) if match else None


def _bibtex_escape(value: str) -> str:
    text = re.sub(r"<[^>]+>", "", str(value or ""))
    text = html.unescape(text)
    replacements = {
        "\\": r"\\",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "$": r"\$",
        "_": r"\_",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _bibtex_pages(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return re.sub(r"(?<=\d)\s*[-\u2010-\u2015]\s*(?=\d)", "--", text)


def _creator_name(creator: dict[str, Any]) -> str:
    first = _clean_text(creator.get("firstName"))
    last = _clean_text(creator.get("lastName"))
    literal = _clean_text(creator.get("name"))
    return " ".join(part for part in (first, last) if part) or literal


def _creators(data: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for creator in data.get("creators") or []:
        if not isinstance(creator, dict):
            continue
        name = _creator_name(creator)
        if not name:
            continue
        role = _clean_text(creator.get("creatorType") or "author")
        result.append({"name": name, "role": role})
    return result


def _external_ids(data: dict[str, Any], key: str) -> dict[str, str]:
    ids: dict[str, str] = {}
    if key:
        ids["zotero_key"] = key
    citation_key = _clean_text(data.get("citationKey") or data.get("citekey"))
    if citation_key:
        ids["citekey"] = citation_key
    for source, target in [
        ("DOI", "DOI"),
        ("doi", "DOI"),
        ("ISBN", "ISBN"),
        ("ISSN", "ISSN"),
        ("url", "URL"),
        ("archiveID", "archiveID"),
        ("libraryCatalog", "libraryCatalog"),
    ]:
        value = _clean_text(data.get(source))
        if value and target not in ids:
            ids[target] = value
    return ids


def _bibtex_key(metadata: dict[str, Any]) -> str:
    for candidate in (
        metadata.get("citekey"),
        metadata.get("citation_key"),
        metadata.get("external_ids", {}).get("citekey") if isinstance(metadata.get("external_ids"), dict) else "",
    ):
        text = _clean_text(candidate)
        if text:
            return text
    key = _clean_text(metadata.get("item_key"))
    if key:
        return f"zotero_{key}"
    authors = metadata.get("authors") or []
    first_author = _clean_text(authors[0]).split()[-1] if authors else ""
    year = str(metadata.get("year") or "")
    title_words = [
        _key_fragment(word)
        for word in _clean_text(metadata.get("title")).split()
        if len(_key_fragment(word)) >= 4
    ]
    fallback = f"{_key_fragment(first_author)}{year}{''.join(title_words[:1])}"
    return fallback or "zotero_item"


def _bibtex_entry_type(metadata: dict[str, Any]) -> str:
    item_type = _clean_text(metadata.get("item_type")).lower()
    return ENTRY_TYPE_MAP.get(item_type, "misc")


def _bibtex_field_lines(metadata: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    title = _clean_text(metadata.get("title"))
    authors = metadata.get("authors") or []
    year = metadata.get("year")
    doi = _clean_text(metadata.get("doi"))
    venue = _clean_text(metadata.get("venue"))
    item_type = _clean_text(metadata.get("item_type")).lower()
    raw = metadata.get("raw_data") if isinstance(metadata.get("raw_data"), dict) else {}

    def add(field: str, value: str) -> None:
        value = _clean_text(value)
        if value:
            lines.append(f"  {field} = {{{_bibtex_escape(value)}}},")

    if authors:
        add("author", " and ".join(_clean_text(author) for author in authors if _clean_text(author)))
    if title:
        add("title", title)
    if year:
        add("year", str(year))
    if item_type in {"journalarticle", "article"}:
        add("journal", venue)
    elif item_type in {"booksection", "incollection", "conferencepaper", "conference", "inproceedings"}:
        add("booktitle", venue)
    elif item_type in {"book"}:
        add("publisher", venue)
    elif item_type in {"thesis"}:
        add("school", venue)
    elif item_type in {"report"}:
        add("institution", venue)
    elif venue:
        add("howpublished", venue)
    if raw.get("volume"):
        add("volume", raw.get("volume"))
    if raw.get("issue"):
        add("number", raw.get("issue"))
    elif raw.get("number"):
        add("number", raw.get("number"))
    if raw.get("pages"):
        add("pages", _bibtex_pages(raw.get("pages")))
    if doi:
        add("doi", doi)
    return lines


def _bibtex(metadata: dict[str, Any]) -> str:
    entry_type = _bibtex_entry_type(metadata)
    key = _bibtex_key(metadata)
    lines = [f"@{entry_type}{{{key},"]
    lines.extend(_bibtex_field_lines(metadata))
    present_fields = {
        line.split("=", 1)[0].strip()
        for line in lines[1:]
        if "=" in line
    }
    missing = {"author", "title", "year"} - present_fields
    if missing:
        missing_text = ", ".join(sorted(missing))
        lines.insert(
            0,
            f"% [UNCONFIRMED] BibTeX missing required field(s): {missing_text} — manual check required",
        )
        lines[1] = lines[1].replace(f"{{{key},", f"{{UNCONFIRMED_{key},", 1)
    if lines[-1].endswith(","):
        lines[-1] = lines[-1].rstrip(",")
    lines.append("}")
    return "\n".join(lines)


def _zotero_api(path: str, params: dict[str, Any] | None = None, api_base: str = "", timeout: float = DEFAULT_TIMEOUT) -> Any:
    base = (api_base or os.environ.get("ZOTERO_LOCAL_API") or DEFAULT_API_BASE).rstrip("/")
    query = f"?{urlencode(params or {}, doseq=True)}" if params else ""
    request = Request(f"{base}/{path.lstrip('/')}{query}", headers={"Zotero-API-Version": "3"})
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - local user-configured API endpoint
        payload = response.read()
    return json.loads(payload.decode("utf-8")) if payload else None


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    data = item.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    key = _clean_text(item.get("key") or data.get("key"))
    title = _clean_text(data.get("title") or data.get("shortTitle"))
    creators = _creators(data)
    abstract = _plain_note(data.get("abstractNote"))
    venue = _clean_text(
        data.get("publicationTitle")
        or data.get("conferenceName")
        or data.get("proceedingsTitle")
        or data.get("bookTitle")
        or data.get("publisher")
        or data.get("institution")
    )
    doi = _clean_text(data.get("DOI") or data.get("doi"))
    citation_key = _clean_text(data.get("citationKey") or data.get("citekey"))
    tags = [
        _clean_text(tag.get("tag"))
        for tag in data.get("tags") or []
        if isinstance(tag, dict) and _clean_text(tag.get("tag"))
    ]

    return {
        "item_key": key,
        "item_type": _clean_text(data.get("itemType")),
        "title": title,
        "short_title": _clean_text(data.get("shortTitle")),
        "doi": doi,
        "citekey": citation_key,
        "citation_key": citation_key,
        "year": _year_from_date(data.get("date")),
        "date": _clean_text(data.get("date")),
        "venue": venue,
        "creators": creators,
        "authors": [creator["name"] for creator in creators if creator.get("role") in {"author", "editor", "contributor"}],
        "abstract": abstract,
        "url": _clean_text(data.get("url")),
        "tags": tags,
        "language": _clean_text(data.get("language")),
        "rights": _clean_text(data.get("rights")),
        "extra": _clean_text(data.get("extra")),
        "zotero_select": f"zotero://select/library/items/{key}" if key else "",
        "external_ids": _external_ids(data, key),
        "raw_data": data,
    }


def fetch_item(item_key: str, api_base: str = "", timeout: float = DEFAULT_TIMEOUT, follow_parent: bool = True) -> dict[str, Any]:
    item = _zotero_api(f"users/0/items/{item_key}", {"format": "json"}, api_base, timeout)
    if not isinstance(item, dict):
        raise ValueError(f"unexpected Zotero API response for item {item_key!r}")
    metadata = normalize_item(item)
    parent_key = _clean_text(metadata.get("raw_data", {}).get("parentItem") if isinstance(metadata.get("raw_data"), dict) else "")
    if follow_parent and metadata.get("item_type") == "attachment" and parent_key:
        parent_item = _zotero_api(f"users/0/items/{parent_key}", {"format": "json"}, api_base, timeout)
        if not isinstance(parent_item, dict):
            raise ValueError(f"unexpected Zotero API response for parent item {parent_key!r}")
        parent_metadata = normalize_item(parent_item)
        parent_metadata["queried_item_key"] = item_key
        parent_metadata["resolved_from_attachment"] = True
        parent_metadata["attachment"] = metadata
        parent_metadata["bibtex"] = _bibtex(parent_metadata)
        return parent_metadata
    metadata["queried_item_key"] = item_key
    metadata["resolved_from_attachment"] = False
    metadata["bibtex"] = _bibtex(metadata)
    return metadata


def ping(api_base: str = "", timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any]:
    base = (api_base or os.environ.get("ZOTERO_LOCAL_API") or DEFAULT_API_BASE).rstrip("/")
    items = _zotero_api("users/0/items", {"limit": 1, "format": "json"}, base, timeout)
    return {"ok": True, "api_base": base, "sample_count": len(items or [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-key", default="", help="Zotero item key to fetch.")
    parser.add_argument("--api-base", default="", help=f"Zotero Local API base URL (default: {DEFAULT_API_BASE}, or ZOTERO_LOCAL_API).")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")
    parser.add_argument("--no-follow-parent", action="store_true", help="Return attachment metadata as-is instead of resolving attachment keys to their parent item.")
    parser.add_argument("--ping", action="store_true", help="Only check whether the Zotero Local API is reachable.")
    args = parser.parse_args()

    try:
        if args.ping:
            result = ping(args.api_base, args.timeout)
        else:
            if not args.item_key:
                parser.error("provide --item-key, or use --ping")
            result = {
                "status": "ok",
                "source": "zotero-local-api",
                "api_base": (args.api_base or os.environ.get("ZOTERO_LOCAL_API") or DEFAULT_API_BASE).rstrip("/"),
                "metadata": fetch_item(args.item_key, args.api_base, args.timeout, follow_parent=not args.no_follow_parent),
            }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "source": "zotero-local-api",
                    "message": str(exc),
                    "hint": "Open Zotero Desktop and enable local API access, or continue with SQLite/Crossref fallback.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()

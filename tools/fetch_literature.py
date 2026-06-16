#!/usr/bin/env python3
"""No-key literature lookup via Crossref and OpenAlex.

Usage:
    python3 tools/fetch_literature.py search "low rank adaptation"
    python3 tools/fetch_literature.py references 10.1145/3366423.3380287
    python3 tools/fetch_literature.py recommend "low rank adaptation" --limit 20

The wrapper intentionally avoids API-key-gated literature services. Crossref is
used for DOI metadata, title search, and reference lists when publishers have
deposited them. OpenAlex is used for broader works search.

Purpose:
    Provide best-effort public literature metadata for discovery and ingest
    enrichment without requiring API keys.

Inputs:
    Search queries, titles, DOIs, or anchor identifiers.

Writes:
    Nothing. Results are printed as JSON.

Limitations:
    Citation and reference coverage depends on what public indexes expose; a
    missing result is not evidence that a citation relationship does not exist.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
from typing import Any
from urllib.parse import quote

import _env  # noqa: F401 - load optional CROSSREF_MAILTO from user config

import os
import requests

from _cli_io import configure_utf8_stdio

CROSSREF_API_URL = "https://api.crossref.org/works"
OPENALEX_API_URL = "https://api.openalex.org/works"
USER_AGENT = "llm-wiki/0.1 (mailto:llm-wiki-local@example.invalid)"
REQUEST_TIMEOUT = 30


def _clean_text(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_doi(value: str) -> bool:
    value = str(value or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return bool(re.match(r"^10\.\d{4,9}/\S+$", value, flags=re.IGNORECASE))


def _normalize_doi(value: str) -> str:
    value = str(value or "").strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    return value


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    mailto = os.environ.get("CROSSREF_MAILTO", "").strip()
    query = dict(params or {})
    if mailto and "api.crossref.org" in url:
        query.setdefault("mailto", mailto)
    openalex_mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if openalex_mailto and "api.openalex.org" in url:
        query.setdefault("mailto", openalex_mailto)
    openalex_api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if openalex_api_key and "api.openalex.org" in url:
        query.setdefault("api_key", openalex_api_key)
    resp = requests.get(url, params=query, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _published_year(value: str) -> int | None:
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return int(match.group(0)) if match else None


def _date_parts_year(parts: list[list[int]] | None) -> int | None:
    if not parts or not parts[0]:
        return None
    year = parts[0][0]
    return int(year) if year else None


def _normalize_crossref_item(item: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text((item.get("title") or [""])[0])
    abstract = _clean_text(item.get("abstract") or "")
    doi = item.get("DOI") or ""
    authors: list[dict[str, str]] = []
    for author in item.get("author") or []:
        given = author.get("given") or ""
        family = author.get("family") or ""
        name = _clean_text(" ".join([given, family]) or author.get("name") or "")
        if name:
            authors.append({"name": name})
    venue = _clean_text((item.get("container-title") or [""])[0])
    year = (
        _date_parts_year((item.get("published-print") or {}).get("date-parts"))
        or _date_parts_year((item.get("published-online") or {}).get("date-parts"))
        or _date_parts_year((item.get("issued") or {}).get("date-parts"))
    )
    external_ids = {"DOI": doi} if doi else {}
    return {
        "paperId": doi or item.get("URL") or title,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "citationCount": item.get("is-referenced-by-count") or 0,
        "influentialCitationCount": 0,
        "venue": venue,
        "publicationTypes": [item.get("type") or "work"],
        "fieldsOfStudy": [],
        "externalIds": external_ids,
        "url": item.get("URL") or (f"https://doi.org/{doi}" if doi else ""),
        "_provider": "crossref",
        "_raw_reference": item.get("reference") or [],
    }


def _normalize_doi_url(value: str) -> str:
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", str(value or ""), flags=re.IGNORECASE)


def _abstract_from_openalex_index(index: dict[str, list[int]] | None) -> str:
    """Reconstruct OpenAlex's inverted-index abstract into plain text."""
    if not isinstance(index, dict):
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            if isinstance(pos, int):
                positioned.append((pos, word))
    positioned.sort(key=lambda item: item[0])
    return _clean_text(" ".join(word for _pos, word in positioned))


def _normalize_openalex_item(item: dict[str, Any]) -> dict[str, Any]:
    title = _clean_text(item.get("display_name") or "")
    doi = _normalize_doi_url(item.get("doi") or "")
    authors: list[dict[str, str]] = []
    for authorship in item.get("authorships") or []:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        name = _clean_text(author.get("display_name") or authorship.get("raw_author_name") or "")
        if name:
            authors.append({"name": name})
    source = ((item.get("primary_location") or {}).get("source") or {})
    venue = _clean_text(source.get("display_name") or "")
    openalex_id = item.get("id") or ""
    external_ids = {"OpenAlex": openalex_id} if openalex_id else {}
    if doi:
        external_ids["DOI"] = doi
    return {
        "paperId": openalex_id or doi or title,
        "title": title,
        "abstract": _abstract_from_openalex_index(item.get("abstract_inverted_index")),
        "authors": authors,
        "year": item.get("publication_year"),
        "citationCount": item.get("cited_by_count") or 0,
        "influentialCitationCount": 0,
        "venue": venue,
        "publicationTypes": [item.get("type")] if item.get("type") else [],
        "fieldsOfStudy": [],
        "externalIds": external_ids,
        "url": f"https://doi.org/{doi}" if doi else openalex_id,
        "_provider": "openalex",
    }


def _crossref_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    data = _get_json(CROSSREF_API_URL, {
        "query.bibliographic": query,
        "rows": max(1, limit),
        "select": "DOI,title,abstract,author,published-print,published-online,issued,is-referenced-by-count,container-title,type,URL,reference",
    })
    items = (data.get("message") or {}).get("items") or []
    return [_normalize_crossref_item(item) for item in items]


def _openalex_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    data = _get_json(OPENALEX_API_URL, {
        "search": query,
        "per-page": max(1, limit),
        "select": (
            "id,doi,display_name,abstract_inverted_index,authorships,"
            "publication_year,cited_by_count,primary_location,type"
        ),
    })
    return [_normalize_openalex_item(item) for item in data.get("results") or []]


def _crossref_paper(doi: str) -> dict[str, Any]:
    data = _get_json(f"{CROSSREF_API_URL}/{quote(_normalize_doi(doi), safe='')}")
    return _normalize_crossref_item((data.get("message") or {}))


def _candidate_key(item: dict[str, Any]) -> str:
    external = item.get("externalIds") or {}
    if external.get("DOI"):
        return f"doi:{str(external['DOI']).lower()}"
    if item.get("paperId"):
        return f"provider:{str(item['paperId']).lower()}"
    title = re.sub(r"\s+", " ", (item.get("title") or "").lower()).strip()
    return f"title:{title}" if title else ""


def _dedupe(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = _candidate_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search no-key literature providers."""
    items: list[dict[str, Any]] = []
    try:
        items.extend(_crossref_search(query, limit=limit))
    except Exception as exc:
        print(f"warn: Crossref search failed for {query!r}: {exc}", file=sys.stderr)
    try:
        items.extend(_openalex_search(query, limit=limit))
    except Exception as exc:
        print(f"warn: OpenAlex search failed for {query!r}: {exc}", file=sys.stderr)
    if not items:
        raise RuntimeError(f"all literature providers failed for query: {query}")
    return _dedupe(items, limit)


def paper(identifier: str) -> dict[str, Any]:
    """Get paper details by DOI or title query."""
    if _looks_like_doi(identifier):
        return _crossref_paper(identifier)
    results = search(identifier, limit=1)
    if results:
        return results[0]
    raise RuntimeError(f"paper not found: {identifier}")


def references(identifier: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return Crossref-deposited references when a DOI is available."""
    record = paper(identifier)
    doi = (record.get("externalIds") or {}).get("DOI") or ""
    if not doi:
        return []
    try:
        crossref_record = _crossref_paper(doi)
    except Exception:
        return []
    refs = crossref_record.get("_raw_reference") or []
    out: list[dict[str, Any]] = []
    for ref in refs[:limit]:
        ref_doi = ref.get("DOI") or ref.get("doi") or ""
        title = ref.get("article-title") or ref.get("unstructured") or ""
        if not ref_doi and not title:
            continue
        out.append({
            "paperId": ref_doi or _clean_text(title),
            "title": _clean_text(title),
            "abstract": "",
            "authors": [],
            "year": int(ref["year"]) if str(ref.get("year", "")).isdigit() else None,
            "citationCount": 0,
            "influentialCitationCount": 0,
            "venue": "",
            "publicationTypes": [],
            "fieldsOfStudy": [],
            "externalIds": {"DOI": ref_doi} if ref_doi else {},
            "url": f"https://doi.org/{ref_doi}" if ref_doi else "",
            "_provider": "crossref_reference",
        })
    return out


def citations(identifier: str, limit: int = 100) -> list[dict[str, Any]]:
    """No-key providers used here do not expose a reliable citing-works endpoint."""
    _ = identifier, limit
    return []


def _keywords_from_title(title: str, max_words: int = 8) -> str:
    stop = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into",
        "is", "of", "on", "or", "the", "to", "via", "with", "using", "towards",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", title.lower())
    chosen = [word for word in words if word not in stop]
    return " ".join(chosen[:max_words]) or title


def recommend(
    positive_ids: list[str],
    negative_ids: list[str] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Approximate related-paper discovery with title-keyword search."""
    negative_ids = negative_ids or []
    negative_keys = {_candidate_key(paper_id_to_stub(pid)) for pid in negative_ids}
    anchor_keys = {_candidate_key(paper_id_to_stub(pid)) for pid in positive_ids}
    results: list[dict[str, Any]] = []
    for anchor in positive_ids:
        try:
            anchor_record = paper(anchor)
        except Exception as exc:
            print(f"warn: anchor lookup failed for {anchor}: {exc}", file=sys.stderr)
            continue
        query = _keywords_from_title(anchor_record.get("title") or anchor)
        for item in search(query, limit=limit):
            key = _candidate_key(item)
            if key and key not in anchor_keys and key not in negative_keys:
                results.append(item)
    return _dedupe(results, limit)


def paper_id_to_stub(identifier: str) -> dict[str, Any]:
    if _looks_like_doi(identifier):
        return {"externalIds": {"DOI": _normalize_doi(identifier)}, "title": ""}
    return {"paperId": identifier, "title": identifier}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search papers")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("n", nargs="?", type=int, default=None, help="Number of results")
    p_search.add_argument("--limit", type=int, default=None, help="Number of results")

    p_paper = sub.add_parser("paper", help="Get paper details")
    p_paper.add_argument("identifier", help="DOI or title")

    p_cite = sub.add_parser("citations", help="Get citing papers when available")
    p_cite.add_argument("identifier", help="DOI or title")
    p_cite.add_argument("--limit", type=int, default=100)

    p_refs = sub.add_parser("references", help="Get references when available")
    p_refs.add_argument("identifier", help="DOI or title")
    p_refs.add_argument("--limit", type=int, default=100)

    p_rec = sub.add_parser("recommend", help="Find papers related to one or more anchors")
    p_rec.add_argument("positive_ids", nargs="+", help="One or more anchor paper IDs")
    p_rec.add_argument("--negative", action="append", default=[], metavar="ID")
    p_rec.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()
    if args.command == "search":
        result = search(args.query, args.limit or args.n or 10)
    elif args.command == "paper":
        result = paper(args.identifier)
    elif args.command == "citations":
        result = citations(args.identifier, args.limit)
    elif args.command == "references":
        result = references(args.identifier, args.limit)
    elif args.command == "recommend":
        result = recommend(args.positive_ids, args.negative, args.limit)
    else:
        result = {}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

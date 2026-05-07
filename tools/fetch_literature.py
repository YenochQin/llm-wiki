#!/usr/bin/env python3
"""No-key literature lookup via arXiv + Crossref.

Usage:
    python3 tools/fetch_literature.py search "low rank adaptation"
    python3 tools/fetch_literature.py paper 2106.09685
    python3 tools/fetch_literature.py paper 10.48550/arXiv.2106.09685
    python3 tools/fetch_literature.py references 10.1145/3366423.3380287
    python3 tools/fetch_literature.py recommend 2106.09685 --limit 20

The wrapper intentionally avoids API-key-gated literature services. arXiv is
used for preprint discovery; Crossref is used for broader DOI metadata and
reference lists when publishers have deposited them.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

import _env  # noqa: F401 - load optional CROSSREF_MAILTO from user config

import os
import requests

ARXIV_API_URL = "https://export.arxiv.org/api/query"
CROSSREF_API_URL = "https://api.crossref.org/works"
USER_AGENT = "llm-wiki/0.1 (mailto:llm-wiki-local@example.invalid)"
ARXIV_DELAY_SECONDS = 3.0
REQUEST_TIMEOUT = 30

_last_arxiv_request = 0.0


def _clean_text(text: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _bare_arxiv_id(raw_id: str) -> str:
    value = str(raw_id or "").strip()
    value = value.removeprefix("ARXIV:").removeprefix("arXiv:").removeprefix("arxiv:")
    value = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", value, flags=re.IGNORECASE)
    value = value.removesuffix(".pdf")
    return re.sub(r"v\d+$", "", value, flags=re.IGNORECASE)


def _looks_like_arxiv_id(value: str) -> bool:
    value = _bare_arxiv_id(value)
    return bool(re.match(r"^\d{4}\.\d{4,5}$", value) or re.match(r"^[a-z-]+(?:\.[A-Z]{2})?/\d{7}$", value))


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
    resp = requests.get(url, params=query, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _get_arxiv(params: dict[str, Any]) -> str:
    global _last_arxiv_request
    elapsed = time.monotonic() - _last_arxiv_request
    if elapsed < ARXIV_DELAY_SECONDS:
        time.sleep(ARXIV_DELAY_SECONDS - elapsed)
    resp = requests.get(ARXIV_API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    _last_arxiv_request = time.monotonic()
    resp.raise_for_status()
    return resp.text


def _published_year(value: str) -> int | None:
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value.replace("Z", "+00:00")).year
    except ValueError:
        match = re.search(r"\b(19|20)\d{2}\b", value)
        return int(match.group(0)) if match else None


def _arxiv_entry_id(entry: ET.Element, ns: dict[str, str]) -> str:
    raw = entry.findtext("atom:id", default="", namespaces=ns)
    return _bare_arxiv_id(raw)


def _normalize_arxiv_entry(entry: ET.Element) -> dict[str, Any]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    arxiv_id = _arxiv_entry_id(entry, ns)
    title = _clean_text(entry.findtext("atom:title", default="", namespaces=ns))
    abstract = _clean_text(entry.findtext("atom:summary", default="", namespaces=ns))
    published = entry.findtext("atom:published", default="", namespaces=ns)
    doi = entry.findtext("arxiv:doi", default="", namespaces=ns)
    categories = [cat.attrib.get("term", "") for cat in entry.findall("atom:category", ns)]
    authors = [
        {"name": _clean_text(author.findtext("atom:name", default="", namespaces=ns))}
        for author in entry.findall("atom:author", ns)
    ]
    authors = [a for a in authors if a.get("name")]
    url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else entry.findtext("atom:id", default="", namespaces=ns)
    external_ids = {"ArXiv": arxiv_id}
    if doi:
        external_ids["DOI"] = doi
    return {
        "paperId": arxiv_id,
        "arxiv_id": arxiv_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": _published_year(published),
        "citationCount": 0,
        "influentialCitationCount": 0,
        "venue": "arXiv",
        "publicationTypes": ["preprint"],
        "fieldsOfStudy": categories,
        "externalIds": external_ids,
        "url": url,
        "_provider": "arxiv",
    }


def _arxiv_query(*, search_query: str = "", id_list: list[str] | None = None, limit: int = 10) -> list[dict[str, Any]]:
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max(1, limit),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    if id_list:
        params["id_list"] = ",".join(_bare_arxiv_id(item) for item in id_list)
        params["search_query"] = ""
    xml_text = _get_arxiv(params)
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    return [_normalize_arxiv_entry(entry) for entry in root.findall("atom:entry", ns)]


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
        "arxiv_id": "",
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


def _crossref_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    data = _get_json(CROSSREF_API_URL, {
        "query.bibliographic": query,
        "rows": max(1, limit),
        "select": "DOI,title,abstract,author,published-print,published-online,issued,is-referenced-by-count,container-title,type,URL,reference",
    })
    items = (data.get("message") or {}).get("items") or []
    return [_normalize_crossref_item(item) for item in items]


def _crossref_paper(doi: str) -> dict[str, Any]:
    data = _get_json(f"{CROSSREF_API_URL}/{quote(_normalize_doi(doi), safe='')}")
    return _normalize_crossref_item((data.get("message") or {}))


def _candidate_key(item: dict[str, Any]) -> str:
    external = item.get("externalIds") or {}
    if external.get("ArXiv"):
        return f"arxiv:{external['ArXiv']}"
    if external.get("DOI"):
        return f"doi:{str(external['DOI']).lower()}"
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
    """Search arXiv and Crossref without API keys."""
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for label, fn in (
        ("arXiv", lambda: _arxiv_query(search_query=f"all:{query}", limit=limit)),
        ("Crossref", lambda: _crossref_search(query, limit=limit)),
    ):
        try:
            results.extend(fn())
        except Exception as exc:
            errors.append(f"{label} search failed: {exc}")
    for error in errors:
        print(f"warn: {error}", file=sys.stderr)
    return _dedupe(results, limit)


def paper(identifier: str) -> dict[str, Any]:
    """Get paper details by arXiv ID, DOI, or title query."""
    if _looks_like_arxiv_id(identifier):
        results = _arxiv_query(id_list=[identifier], limit=1)
        if results:
            return results[0]
        raise RuntimeError(f"arXiv paper not found: {identifier}")
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
    if _looks_like_arxiv_id(identifier):
        return {"externalIds": {"ArXiv": _bare_arxiv_id(identifier)}, "title": ""}
    if _looks_like_doi(identifier):
        return {"externalIds": {"DOI": _normalize_doi(identifier)}, "title": ""}
    return {"paperId": identifier, "title": identifier}


def main() -> None:
    parser = argparse.ArgumentParser(description="No-key arXiv/Crossref literature lookup")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="Search papers")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("n", nargs="?", type=int, default=None, help="Number of results")
    p_search.add_argument("--limit", type=int, default=None, help="Number of results")

    p_paper = sub.add_parser("paper", help="Get paper details")
    p_paper.add_argument("identifier", help="arXiv ID, DOI, or title")

    p_cite = sub.add_parser("citations", help="Get citing papers when available")
    p_cite.add_argument("identifier", help="arXiv ID or DOI")
    p_cite.add_argument("--limit", type=int, default=100)

    p_refs = sub.add_parser("references", help="Get references when available")
    p_refs.add_argument("identifier", help="arXiv ID or DOI")
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
    main()

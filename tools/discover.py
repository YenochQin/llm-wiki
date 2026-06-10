#!/usr/bin/env python3
"""Discovery tool — assemble a ranked shortlist of candidate papers.

This is the deterministic core behind the /discover skill. It produces a
recommendation shortlist from one of three seed modes:

    from-anchors  — given one or more anchor paper IDs or titles
    from-topic    — given a topic/query string (lighter alternative to /init)
    from-wiki     — derive anchors from the wiki's most recent papers

Output is a JSON shortlist on stdout (and optionally a checkpoint file).
Dedupes against papers already in wiki/. Ranking is *not* the same as
init_discovery.py — discovery does not favor surveys; it weights related-paper
matches, citation counts when available, and freshness.

Usage:
    python3 tools/discover.py from-anchors --id "A paper title or DOI" \\
        [--negative "another paper title or DOI"] [--wiki-root wiki/] [--limit 10]
    python3 tools/discover.py from-topic "diffusion model fine-tuning" \\
        [--wiki-root wiki/] [--limit 10]
    python3 tools/discover.py from-wiki --wiki-root wiki/ [--limit 10]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import _env  # noqa: F401 — load .env files

import fetch_literature
import find_zotero_pdf
from _cli_io import configure_utf8_stdio
from _paths import load_paths, resolve_runtime_path


# ---------- candidate normalization ----------------------------------------

def _normalize_candidate(raw: dict[str, Any], *, source: str, anchor: str = "") -> dict[str, Any]:
    """Flatten a literature provider record into the discover shortlist schema."""
    if not raw:
        return {}
    authors = raw.get("authors") or []
    external_ids = raw.get("externalIds") or {}
    h_indexes = [a.get("hIndex") for a in authors if isinstance(a, dict) and a.get("hIndex")]
    tldr = raw.get("tldr")
    tldr_text = tldr.get("text") if isinstance(tldr, dict) else (tldr or "")
    return {
        "paperId": raw.get("paperId") or "",
        "externalIds": external_ids,
        "title": raw.get("title") or "",
        "abstract": raw.get("abstract") or "",
        "tldr": tldr_text,
        "year": raw.get("year"),
        "venue": raw.get("venue") or "",
        "authors": [a.get("name", "") for a in authors if isinstance(a, dict)],
        "max_h_index": max(h_indexes) if h_indexes else 0,
        "citation_count": raw.get("citationCount") or 0,
        "influential_citation_count": raw.get("influentialCitationCount") or 0,
        "fields_of_study": raw.get("fieldsOfStudy") or [],
        "publication_types": raw.get("publicationTypes") or [],
        "url": raw.get("url") or "",
        # True when a provider exposes a per-edge influential-citation flag.
        "is_influential_edge": bool(raw.get("_is_influential_edge")),
        "_sources": [source],
        "_anchors": [anchor] if anchor else [],
    }


def _candidate_key(c: dict[str, Any]) -> str:
    """Stable dedup key — prefer provider/DOI IDs, then title."""
    external_ids = c.get("externalIds") or {}
    doi = external_ids.get("DOI") or external_ids.get("doi")
    if doi:
        return f"doi:{str(doi).lower()}"
    if c.get("paperId"):
        paper_id = str(c["paperId"]).strip()
        if re.match(r"^10\.\d{4,9}/\S+$", paper_id, flags=re.IGNORECASE):
            return f"doi:{paper_id.lower()}"
        return f"provider:{str(c['paperId']).lower()}"
    title = re.sub(r"\s+", " ", (c.get("title") or "").strip().lower())
    return f"title:{title}" if title else ""


def _candidate_doi(c: dict[str, Any]) -> str:
    external_ids = c.get("externalIds") or {}
    doi = external_ids.get("DOI") or external_ids.get("doi") or ""
    if not doi and c.get("paperId"):
        paper_id = str(c.get("paperId") or "").strip()
        if re.match(r"^10\.\d{4,9}/\S+$", paper_id, flags=re.IGNORECASE):
            doi = paper_id
    doi = str(doi or "").strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi


def _merge_candidate(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    """Union sources/anchors; keep richer field values from either side."""
    for src in incoming.get("_sources", []):
        if src not in existing["_sources"]:
            existing["_sources"].append(src)
    for anchor in incoming.get("_anchors", []):
        if anchor and anchor not in existing["_anchors"]:
            existing["_anchors"].append(anchor)
    for key in ("abstract", "tldr", "venue", "url"):
        if not existing.get(key) and incoming.get(key):
            existing[key] = incoming[key]
    if not existing.get("authors") and incoming.get("authors"):
        existing["authors"] = incoming["authors"]
    if not existing.get("fields_of_study") and incoming.get("fields_of_study"):
        existing["fields_of_study"] = incoming["fields_of_study"]
    # Numeric fields: prefer the larger reading.
    for key in ("max_h_index", "citation_count", "influential_citation_count"):
        existing[key] = max(existing.get(key) or 0, incoming.get(key) or 0)
    # Influential-edge is a union: if any anchor↔candidate edge was flagged influential,
    # the candidate keeps the flag even when other channels surfaced it without the flag.
    existing["is_influential_edge"] = bool(existing.get("is_influential_edge") or incoming.get("is_influential_edge"))
    if not existing.get("year") and incoming.get("year"):
        existing["year"] = incoming["year"]


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for c in candidates:
        key = _candidate_key(c)
        if not key:
            continue
        if key in out:
            _merge_candidate(out[key], c)
        else:
            out[key] = c
    return list(out.values())


# ---------- wiki dedup -----------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_DOI_RE = re.compile(
    r"^external_ids:\s*\n(?:[ \t]+[A-Za-z0-9_-]+:\s*[\"']?[^\"'\n]*[\"']?\s*\n)*"
    r"[ \t]+(?:DOI|doi):\s*[\"']?([^\"'\n]+)[\"']?\s*$",
    re.MULTILINE,
)
_TITLE_RE = re.compile(r"^title:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)


def _extract_wiki_paper_key(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return ""
    fm = m.group(1)
    doi_match = _DOI_RE.search(fm)
    if doi_match:
        return f"doi:{doi_match.group(1).strip().lower()}"
    title_match = _TITLE_RE.search(fm)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1).strip().lower())
        if title:
            return f"title:{title}"
    return ""


def _wiki_known_paper_keys(wiki_root: Path | None) -> set[str]:
    """Scan wiki/papers/*.md for DOI/title identity keys."""
    if not wiki_root or not wiki_root.exists():
        return set()
    papers_dir = wiki_root / "papers"
    if not papers_dir.exists():
        return set()
    seen: set[str] = set()
    for path in papers_dir.glob("*.md"):
        key = _extract_wiki_paper_key(path)
        if key:
            seen.add(key)
    return seen


def _filter_against_wiki(candidates: list[dict[str, Any]], known: set[str]) -> list[dict[str, Any]]:
    if not known:
        return candidates
    return [c for c in candidates if _candidate_key(c) not in known]


# ---------- Zotero collection status ---------------------------------------

def _title_norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _zotero_match_for_candidate(c: dict[str, Any], zotero_root: Path | None) -> dict[str, Any]:
    """Return a confident Zotero match for a candidate, if the local library has it."""
    doi = _candidate_doi(c)
    title = str(c.get("title") or "").strip()
    if not (doi or title):
        return {}
    try:
        result = find_zotero_pdf.find(zotero_root, title, doi, "", 5)
    except Exception:
        return {}
    if result.get("status") != "ok":
        return {}

    title_key = _title_norm(title)
    doi_key = doi.lower()
    for item in result.get("candidates") or []:
        item_doi = str(item.get("doi") or "").strip().lower()
        item_title = _title_norm(str(item.get("title") or ""))
        if doi_key and item_doi == doi_key:
            return item
        if title_key and item_title == title_key:
            return item
    return {}


def _annotate_zotero_status(candidates: list[dict[str, Any]]) -> None:
    """Add _zotero_status: collected / not collected / unknown to each candidate."""
    try:
        zotero_root, _notes = find_zotero_pdf._discover_zotero_root(find_zotero_pdf.DEFAULT_CONFIG_PATH)
    except Exception:
        zotero_root = None
    if zotero_root is None:
        for c in candidates:
            c["_zotero_status"] = "unknown"
            c["_zotero_match"] = {}
        return

    for c in candidates:
        match = _zotero_match_for_candidate(c, zotero_root)
        c["_zotero_status"] = "collected" if match else "not collected"
        c["_zotero_match"] = match


def _provider_authors_to_names(authors: list[Any]) -> list[str]:
    names: list[str] = []
    for author in authors:
        if isinstance(author, dict):
            name = str(author.get("name") or "").strip()
        else:
            name = str(author or "").strip()
        if name:
            names.append(name)
    return names


def _enrich_candidate_metadata(candidates: list[dict[str, Any]]) -> None:
    """Fill missing title/author/venue/year fields from DOI or title metadata."""
    for c in candidates:
        identifier = _candidate_doi(c) or str(c.get("title") or "").strip()
        if not identifier:
            continue
        needs_enrichment = not c.get("title") or not c.get("authors") or not c.get("venue") or not c.get("year")
        if not needs_enrichment:
            continue
        try:
            record = fetch_literature.paper(identifier)
        except Exception:
            continue
        if not c.get("title") and record.get("title"):
            c["title"] = record["title"]
        if not c.get("authors"):
            c["authors"] = _provider_authors_to_names(record.get("authors") or [])
        if not c.get("venue") and record.get("venue"):
            c["venue"] = record["venue"]
        if not c.get("year") and record.get("year"):
            c["year"] = record["year"]
        if not _candidate_doi(c) and (record.get("externalIds") or {}).get("DOI"):
            c.setdefault("externalIds", {})["DOI"] = (record.get("externalIds") or {})["DOI"]


# ---------- ranking --------------------------------------------------------

def _influence_score(infl: int, total: int) -> float:
    """Reward influential citations more than raw count.

    Uses log scaling to keep mega-cited papers from saturating.
    """
    infl = max(0, int(infl or 0))
    total = max(0, int(total or 0))
    return 0.7 * math.log1p(infl) / math.log1p(50) + 0.3 * math.log1p(total) / math.log1p(1000)


def _hindex_score(h: int) -> float:
    """Mild bonus from author credibility — cap so it can't dominate."""
    h = max(0, int(h or 0))
    return min(1.0, h / 60.0)


def _freshness_score(year: int | None) -> float:
    if not year:
        return 0.4
    now = _dt.date.today().year
    age = max(0, now - int(year))
    if age <= 1:
        return 1.0
    if age <= 3:
        return 0.85
    if age <= 6:
        return 0.6
    if age <= 10:
        return 0.4
    return 0.25


def _anchor_overlap_score(c: dict[str, Any]) -> float:
    """How many anchors surfaced this candidate (more anchors = stronger signal)."""
    n = len(c.get("_anchors") or [])
    if n == 0:
        return 0.0
    return min(1.0, 0.5 + 0.25 * (n - 1))


def _channel_diversity_score(c: dict[str, Any]) -> float:
    """Bonus when the same candidate was surfaced by multiple channels.

    A paper appearing from recommend + references + citations is a
    stronger signal than one appearing only from recommend — it means
    the paper is semantically similar AND part of the citation graph.
    """
    return min(1.0, 0.4 * len(set(c.get("_sources") or [])))


def _anchor_influence_edge_score(c: dict[str, Any]) -> float:
    """Provider-specific per-edge importance signal, when available."""
    return 1.0 if c.get("is_influential_edge") else 0.0


def _is_heavily_related(c: dict[str, Any]) -> bool:
    """Gate anchor/wiki recommendations to papers with strong relation evidence."""
    sources = set(c.get("_sources") or [])
    anchors = set(a for a in (c.get("_anchors") or []) if a)
    if c.get("is_influential_edge"):
        return True
    if len(anchors) >= 2:
        return True
    if len(sources) >= 2:
        return True
    return bool(sources & {"literature_reference", "literature_citation"})


def _filter_heavily_related(candidates: list[dict[str, Any]], *, anchor_mode: bool) -> list[dict[str, Any]]:
    """Keep only strong follow-up reads for anchor/wiki discovery.

    Topic mode remains exploratory; this gate is only for recommendations tied
    to existing wiki anchors, especially post-/ingest suggestions.
    """
    if not anchor_mode:
        return candidates
    return [c for c in candidates if _is_heavily_related(c)]


def _score(c: dict[str, Any], *, anchor_mode: bool) -> float:
    influence = _influence_score(c.get("influential_citation_count", 0), c.get("citation_count", 0))
    h = _hindex_score(c.get("max_h_index", 0))
    fresh = _freshness_score(c.get("year"))
    diversity = _channel_diversity_score(c)
    if anchor_mode:
        # With related-paper search plus optional citation/reference channels:
        #   - influence: aggregate prestige (candidate's general importance)
        #   - anchor_influence_edge: specific anchor↔candidate significance (sharp, often 0)
        #   - anchor overlap: how many anchors surfaced the candidate
        #   - channel diversity: how many channels surfaced the candidate
        #   - freshness + h-index: supporting signals
        anchor = _anchor_overlap_score(c)
        edge = _anchor_influence_edge_score(c)
        return (
            0.25 * influence
            + 0.20 * edge
            + 0.15 * anchor
            + 0.15 * diversity
            + 0.15 * fresh
            + 0.10 * h
        )
    # Topic / wiki mode: no anchor signal — lean harder on influence and freshness.
    # `is_influential_edge` is always False here (no anchor edge exists), so skip it.
    return 0.45 * influence + 0.25 * fresh + 0.15 * h + 0.15 * diversity


def _rationale(c: dict[str, Any], *, anchor_mode: bool) -> str:
    bits: list[str] = []
    if anchor_mode and c.get("is_influential_edge"):
        # Lead with this — it is the sharpest signal we have.
        bits.append("influential edge with anchor")
    if anchor_mode and c.get("_anchors"):
        bits.append(f"from {len(c['_anchors'])} anchor(s)")
    if c.get("influential_citation_count"):
        bits.append(f"{c['influential_citation_count']} influential citations")
    elif c.get("citation_count"):
        bits.append(f"{c['citation_count']} citations")
    if c.get("max_h_index"):
        bits.append(f"top author h-index {c['max_h_index']}")
    if c.get("year"):
        bits.append(str(c["year"]))
    return "; ".join(bits) if bits else "candidate"


# ---------- candidate gathering --------------------------------------------

def _gather_from_anchors(
    positive: list[str],
    negative: list[str],
    per_anchor_limit: int,
    *,
    citation_expand: bool = True,
    citation_limit: int = 30,
) -> list[dict[str, Any]]:
    """Anchor gather: no-key related search plus optional citation/reference channels."""
    candidates: list[dict[str, Any]] = []
    # One call-set per anchor preserves which anchor surfaced which candidate;
    # this matters for the anchor-overlap signal in ranking.
    for anchor in positive:
        # Channel 1: related-paper lookup
        try:
            recs = fetch_literature.recommend([anchor], negative_ids=negative, limit=per_anchor_limit)
        except Exception as exc:
            print(f"warn: related-paper lookup failed for {anchor}: {exc}", file=sys.stderr)
            recs = []
        for raw in recs:
            norm = _normalize_candidate(raw, source="literature_recommend", anchor=anchor)
            if norm:
                candidates.append(norm)

        if not citation_expand:
            continue

        # Channel 2: what the anchor cites (older canonical work)
        try:
            refs = fetch_literature.references(anchor, limit=citation_limit)
        except Exception as exc:
            print(f"warn: reference lookup failed for {anchor}: {exc}", file=sys.stderr)
            refs = []
        for raw in refs:
            norm = _normalize_candidate(raw, source="literature_reference", anchor=anchor)
            if norm:
                candidates.append(norm)

        # Channel 3: what cites the anchor, when a no-key provider supports it.
        try:
            cits = fetch_literature.citations(anchor, limit=citation_limit)
        except Exception as exc:
            print(f"warn: citation lookup failed for {anchor}: {exc}", file=sys.stderr)
            cits = []
        for raw in cits:
            norm = _normalize_candidate(raw, source="literature_citation", anchor=anchor)
            if norm:
                candidates.append(norm)
    return candidates


def _gather_from_topic(topic: str, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    try:
        literature_results = fetch_literature.search(topic, limit=limit)
    except Exception as exc:
        print(f"warn: literature search failed for {topic!r}: {exc}", file=sys.stderr)
        literature_results = []
    for raw in literature_results:
        norm = _normalize_candidate(raw, source="literature_search")
        if norm:
            candidates.append(norm)

    return candidates


def _wiki_recent_anchors(wiki_root: Path, k: int) -> list[str]:
    """Pick the K most recently modified paper pages and return DOI/title anchors."""
    papers_dir = wiki_root / "papers"
    if not papers_dir.exists():
        return []
    paths = sorted(papers_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    anchors: list[str] = []
    for path in paths:
        key = _extract_wiki_paper_key(path)
        if key:
            anchors.append(key.split(":", 1)[1])
            if len(anchors) >= k:
                break
    return anchors


# ---------- shortlist assembly ---------------------------------------------

def build_shortlist(
    *,
    mode: str,
    positive_ids: list[str] | None = None,
    negative_ids: list[str] | None = None,
    topic: str = "",
    wiki_root: Path | None = None,
    limit: int = 10,
    per_anchor_limit: int = 50,
    citation_expand: bool = True,
    citation_limit: int = 30,
) -> dict[str, Any]:
    """Run the discovery pipeline and return a structured shortlist payload."""
    positive_ids = positive_ids or []
    negative_ids = negative_ids or []
    anchor_mode = mode in ("anchors", "wiki")

    if mode == "anchors":
        if not positive_ids:
            raise ValueError("from-anchors requires at least one --id")
        candidates = _gather_from_anchors(
            positive_ids,
            negative_ids,
            per_anchor_limit,
            citation_expand=citation_expand,
            citation_limit=citation_limit,
        )
        seed_summary = {
            "mode": "anchors",
            "positive_ids": positive_ids,
            "negative_ids": negative_ids,
            "citation_expand": citation_expand,
        }
    elif mode == "topic":
        if not topic:
            raise ValueError("from-topic requires a query string")
        candidates = _gather_from_topic(topic, max(20, limit * 4))
        seed_summary = {"mode": "topic", "topic": topic}
    elif mode == "wiki":
        if not wiki_root:
            raise ValueError("from-wiki requires --wiki-root")
        derived = _wiki_recent_anchors(wiki_root, k=3)
        if not derived:
            raise ValueError("from-wiki found no anchorable papers under wiki/papers/")
        candidates = _gather_from_anchors(
            derived,
            negative_ids,
            per_anchor_limit,
            citation_expand=citation_expand,
            citation_limit=citation_limit,
        )
        seed_summary = {
            "mode": "wiki",
            "derived_anchors": derived,
            "citation_expand": citation_expand,
        }
    else:
        raise ValueError(f"unknown mode: {mode}")

    candidates = _dedupe(candidates)
    known = _wiki_known_paper_keys(wiki_root) if wiki_root else set()
    candidates = _filter_against_wiki(candidates, known)

    for c in candidates:
        c["_score"] = round(_score(c, anchor_mode=anchor_mode), 4)
        c["_rationale"] = _rationale(c, anchor_mode=anchor_mode)

    candidates = _filter_heavily_related(candidates, anchor_mode=anchor_mode)
    candidates.sort(key=lambda c: c["_score"], reverse=True)
    shortlist = candidates[:limit]
    _enrich_candidate_metadata(shortlist)
    _annotate_zotero_status(shortlist)

    return {
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "seed": seed_summary,
        "wiki_dedup_count": len(known),
        "candidates_total": len(candidates),
        "shortlist_count": len(shortlist),
        "shortlist": shortlist,
    }


# ---------- output formatting ---------------------------------------------

def _format_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    seed = payload.get("seed") or {}
    mode = seed.get("mode", "?")
    if mode == "anchors":
        seed_desc = f"anchors: {', '.join(seed.get('positive_ids', []))}"
        if seed.get("negative_ids"):
            seed_desc += f" | negatives: {', '.join(seed['negative_ids'])}"
    elif mode == "topic":
        seed_desc = f'topic: "{seed.get("topic", "")}"'
    elif mode == "wiki":
        seed_desc = f"derived from wiki anchors: {', '.join(seed.get('derived_anchors', []))}"
    else:
        seed_desc = mode

    lines.append(f"# Discover shortlist ({mode})")
    lines.append(f"_Seed_: {seed_desc}")
    lines.append(
        f"_Stats_: {payload.get('shortlist_count', 0)} shown / "
        f"{payload.get('candidates_total', 0)} candidates / "
        f"{payload.get('wiki_dedup_count', 0)} already in wiki"
    )
    lines.append("")
    for i, c in enumerate(payload.get("shortlist") or [], start=1):
        title = c.get("title") or "(untitled)"
        rationale = c.get("_rationale") or ""
        score = c.get("_score", 0)
        authors = ", ".join(c.get("authors") or []) or "unknown"
        doi = _candidate_doi(c) or "unavailable"
        zotero_status = c.get("_zotero_status") or "unknown"
        lines.append(f"{i}. **{title}**  ")
        lines.append(f"   Authors: {authors}  ")
        lines.append(f"   DOI: {doi}  ")
        lines.append(f"   Zotero: {zotero_status}  ")
        lines.append(f"   Score: {score} — {rationale}")
        if c.get("tldr"):
            lines.append(f"   > {c['tldr']}")
        lines.append("")
    return "\n".join(lines)


# ---------- CLI ------------------------------------------------------------

def _slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text[:48] or "discover"


def _resolve_output_checkpoint_path(raw_path: str | Path, seed_slug: str) -> Path:
    """Resolve --output-checkpoint as either a file path or directory target."""
    raw_text = str(raw_path)
    out_path = Path(raw_text)
    if out_path.is_dir() or raw_text.endswith(("/", "\\")):
        today = _dt.date.today().isoformat()
        return out_path / f"discover-{seed_slug}-{today}.json"
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="llm-wiki discovery shortlist builder")
    sub = parser.add_subparsers(dest="command", required=True)

    common_args: list[tuple[str, dict[str, Any]]] = [
        ("--wiki-root", {"default": None, "help": "Wiki root for dedup against existing papers. Accepts @configured"}),
        ("--limit", {"type": int, "default": 10, "help": "Max shortlist size (default 10)"}),
        ("--per-anchor-limit", {"type": int, "default": 50, "help": "Recs requested per anchor (default 50)"}),
        ("--output-checkpoint", {"default": None, "help": "Also write JSON to this file or directory path"}),
        ("--markdown", {"action": "store_true", "help": "Print human-readable markdown instead of JSON"}),
    ]

    # Citation-expansion flags apply only to anchor and wiki modes.
    anchor_expand_args: list[tuple[str, dict[str, Any]]] = [
        ("--no-citation-expand", {"dest": "citation_expand", "action": "store_false", "help": "Skip references/citations fan-out (recommend channel only; faster but narrower)"}),
        ("--citation-limit", {"type": int, "default": 30, "help": "Per-anchor cap for references and citations channels (default 30 each)"}),
    ]

    p_anchors = sub.add_parser("from-anchors", help="Recommend from one or more anchor papers")
    p_anchors.add_argument("--id", dest="positive_ids", action="append", default=[], required=True, help="Anchor paper ID (repeatable)")
    p_anchors.add_argument("--negative", dest="negative_ids", action="append", default=[], help="Push recommendations away from this ID (repeatable)")
    for flag, kwargs in common_args:
        p_anchors.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_expand_args:
        p_anchors.add_argument(flag, **kwargs)

    p_topic = sub.add_parser("from-topic", help="Recommend from a topic / query string")
    p_topic.add_argument("topic", help="Topic or query string")
    for flag, kwargs in common_args:
        p_topic.add_argument(flag, **kwargs)

    p_wiki = sub.add_parser("from-wiki", help="Derive seeds from the wiki's recent papers")
    for flag, kwargs in common_args:
        p_wiki.add_argument(flag, **kwargs)
    for flag, kwargs in anchor_expand_args:
        p_wiki.add_argument(flag, **kwargs)

    args = parser.parse_args()
    if getattr(args, "wiki_root", None):
        paths = load_paths()
        args.wiki_root = resolve_runtime_path(args.wiki_root, paths, role="--wiki-root")

    if args.command == "from-anchors":
        payload = build_shortlist(
            mode="anchors",
            positive_ids=args.positive_ids,
            negative_ids=args.negative_ids,
            wiki_root=args.wiki_root,
            limit=args.limit,
            per_anchor_limit=args.per_anchor_limit,
            citation_expand=args.citation_expand,
            citation_limit=args.citation_limit,
        )
        seed_slug = _slugify("-".join(args.positive_ids[:2]))
    elif args.command == "from-topic":
        payload = build_shortlist(
            mode="topic",
            topic=args.topic,
            wiki_root=args.wiki_root,
            limit=args.limit,
            per_anchor_limit=args.per_anchor_limit,
        )
        seed_slug = _slugify(args.topic)
    elif args.command == "from-wiki":
        if not args.wiki_root:
            parser.error("from-wiki requires --wiki-root")
        payload = build_shortlist(
            mode="wiki",
            wiki_root=args.wiki_root,
            limit=args.limit,
            per_anchor_limit=args.per_anchor_limit,
            citation_expand=args.citation_expand,
            citation_limit=args.citation_limit,
        )
        seed_slug = "wiki"
    else:
        parser.error(f"unknown command: {args.command}")
        return

    if args.output_checkpoint:
        out_path = _resolve_output_checkpoint_path(args.output_checkpoint, seed_slug)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"checkpoint written: {out_path}", file=sys.stderr)

    if args.markdown:
        print(_format_markdown(payload))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

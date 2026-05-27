#!/usr/bin/env python3
"""Source preparation + manifest builder for /init.

Local-papers-only pipeline: prepares raw PDFs into wiki/sources/ and
copies notes/web sources from raw/ into wiki/sources/ for vault browsing.
External discovery and remote source fetching have been removed; /init now
operates purely over the user's local raw/papers/ inputs.

Usage:
    python3 tools/init_discovery.py prepare \\
        --raw-root raw \\
        --wiki-root wiki \\
        --sources-output-dir wiki/sources \\
        --cache-root .checkpoints/mineru-cache \\
        --pdf-titles-json .checkpoints/init-pdf-titles.json \\
        --output-manifest .checkpoints/init-prepare.json
    python3 tools/init_discovery.py manifest \\
        --raw-root raw \\
        --prepared-manifest .checkpoints/init-prepare.json \\
        --output-sources .checkpoints/init-sources.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import _env  # noqa: F401 — load .env files for child tools
import enrich_local_pdf_bibtex
import prepare_paper_source as paper_source
from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, display_path, load_paths, resolve_runtime_path
from research_wiki import slugify

TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm"}


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _reject_repo_wiki_output(parser: argparse.ArgumentParser, output_dir: Path, paths) -> None:
    repo_wiki = (paths.project_root / "wiki").resolve()
    configured_wiki = paths.wiki_root.resolve()
    if configured_wiki != repo_wiki and _is_relative_to(output_dir, repo_wiki):
        parser.error(
            "--sources-output-dir resolved inside the code repository's wiki/ directory, "
            "but config/paths.json points at an external wiki root. "
            "Pass @configured-sources or the external wiki/sources path."
        )


def _paper_entry_match_key(entry: dict[str, Any]) -> tuple[str, str]:
    return ("", _normalize_text(str(entry.get("title") or "")))


def _paper_entry_source_key(entry: dict[str, Any]) -> str:
    source_path = Path(str(entry.get("source_path") or ""))
    name = source_path.name.lower()
    if name.endswith(".tar.gz"):
        base = source_path.name[:-7]
    else:
        base = source_path.stem
    return _normalize_text(base.replace("_", " ").replace("-", " "))


def _paper_entry_preference(entry: dict[str, Any]) -> tuple[int, int, int]:
    original_format = str(entry.get("original_format") or "")
    ingest_format = str(entry.get("ingest_format") or "")
    abstract_len = len(str(entry.get("abstract_excerpt") or ""))

    if original_format == "tex" and ingest_format == "tex":
        rank = 4
    elif original_format in {"archive", "directory"} and ingest_format in {"tex", "directory"}:
        rank = 3
    elif original_format == "pdf" and ingest_format == "tex":
        rank = 2
    elif ingest_format == "pdf":
        rank = 1
    elif ingest_format in {"mineru-md", "directory"}:
        rank = 3
    else:
        rank = 0
    return (rank, abstract_len)


def _project_root(raw_root: Path) -> Path:
    return raw_root.resolve().parent


def _relative_to_project(path: Path, raw_root: Path, project_root: Path | None = None) -> str:
    if project_root is not None:
        return display_path(path, project_root)
    return str(path.resolve().relative_to(_project_root(raw_root)))


def _normalize_prepare_source_path(raw_root: Path, source_path: str) -> str:
    raw_source = str(source_path or "").strip()
    if not raw_source:
        return ""

    candidate = Path(raw_source)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        project_root = _project_root(raw_root)
        resolved = (project_root / raw_source).resolve()
        parts = candidate.parts
        if not resolved.exists() and parts and parts[0] == "raw":
            resolved = (raw_root / Path(*parts[1:])).resolve()
        if not resolved.exists() and not raw_source.startswith("raw/"):
            resolved = (raw_root / raw_source).resolve()

    try:
        return _relative_to_project(resolved, raw_root)
    except ValueError:
        return ""


def _normalize_pdf_titles_map(
    raw_root: Path,
    pdf_titles: dict[str, Any] | None,
    warning_sink: list[str] | None = None,
) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    normalized_payloads: dict[str, dict[str, str]] = {}
    original_keys: dict[str, str] = {}
    for raw_key, raw_title in (pdf_titles or {}).items():
        key = _normalize_prepare_source_path(raw_root, str(raw_key))
        if isinstance(raw_title, dict):
            title = " ".join(str(raw_title.get("title") or "").split())
        else:
            title = " ".join(str(raw_title or "").split())
        if not key:
            if warning_sink is not None:
                warning_sink.append(f"ignored invalid PDF title mapping: {raw_key}")
            continue
        if not title:
            continue
        normalized_payloads[key] = {"title": title}
        original_keys[key] = str(raw_key)
    return normalized_payloads, original_keys


def _load_pdf_titles_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("expected a JSON object mapping source paths to titles or {title} records")
    return payload


def _read_text(path: Path, limit: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def _normalize_text(text: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff\s.+/_-]", " ", text.lower())
    return " ".join(text.split())


_NON_TITLE_PATTERNS = (
    "published as a",
    "proceedings of",
    "conference",
    "copyright",
    "all rights reserved",
    "https://",
    "http://",
    "doi:",
    "ieee",
    "acm",
    "springer",
    "elsevier",
)


def _is_likely_title(line: str) -> bool:
    lower = line.lower()
    if lower in {"abstract", "introduction", "contents", "references"}:
        return False
    for pat in _NON_TITLE_PATTERNS:
        if pat in lower:
            return False
    if re.search(r"\b20\d{2}\b", line) and len(line) < 50:
        return False
    return True


def _guess_title_from_text(text: str, fallback: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("#").strip()
        if len(line) < 8:
            continue
        if not _is_likely_title(line):
            continue
        return re.sub(r"\s+", " ", line)[:200]
    return fallback


def _extract_abstract_excerpt(text: str, limit: int = 1200) -> str:
    if not text.strip():
        return ""
    match = re.search(
        r"(?is)(?:^|\n)\s*(?:abstract|摘要)\s*[:：]?\s*(.+?)(?:\n\s*(?:1\.?|i\.?|introduction|引言|keywords?|关键词)\b|\Z)",
        text,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()[:limit]
    first_paragraphs = re.split(r"\n\s*\n", text.strip())
    for paragraph in first_paragraphs:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if len(paragraph) >= 40:
            return paragraph[:limit]
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _path_slug(path: Path) -> str:
    return slugify("-".join(path.parts)) or "item"


def _ingest_format_from_path(path_str: str) -> str:
    path = Path(path_str)
    if path.suffix.lower() == ".tex":
        return "tex"
    if path.suffix.lower() == ".pdf":
        return "pdf"
    if path.suffix.lower() == ".md":
        return "mineru-md"
    return "directory"


def _prepare_text_entry(
    path: Path,
    raw_root: Path,
    kind: str,
    sources_output_dir: Path,
    project_root: Path,
) -> dict[str, Any] | None:
    text = _read_text(path, limit=120000)
    if not text.strip():
        return None
    source_rel = _relative_to_project(path, raw_root, project_root=project_root)
    relative_name = path.relative_to(raw_root / kind)
    prepared_path = sources_output_dir / kind / relative_name
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, prepared_path)
    prepared_rel = _relative_to_project(prepared_path, raw_root, project_root=project_root)
    title = _guess_title_from_text(text, path.stem)
    return {
        "entry_id": f"{kind}:{_path_slug(path.relative_to(raw_root))}",
        "source_kind": kind,
        "source_path": source_rel,
        "prepared_path": prepared_rel,
        "canonical_ingest_path": prepared_rel,
        "canonical_read_path": prepared_rel,
        "original_format": path.suffix.lower().lstrip(".") or "text",
        "title": title,
        "abstract_excerpt": _extract_abstract_excerpt(text, limit=400),
        "warnings": [],
        "usable": True,
    }


def _prepare_paper_entry(
    path: Path,
    raw_root: Path,
    wiki_root: Path,
    project_root: Path,
    sources_output_dir: Path,
    cache_root: Path,
    title: str = "",
) -> dict[str, Any]:
    enrichment: dict[str, Any] = {}
    try:
        enrichment = enrich_local_pdf_bibtex.enrich(path, title=title)
    except Exception:
        enrichment = {}
    metadata = enrichment.get("metadata") if enrichment.get("status") == "ok" else {}
    authors = metadata.get("authors") if isinstance(metadata, dict) else []
    return paper_source.prepare_paper_source(
        path,
        raw_root,
        wiki_root=wiki_root,
        output_dir=sources_output_dir / "papers",
        cache_root=cache_root,
        project_root=project_root,
        title=title,
        bibtex=str(enrichment.get("bibtex") or ""),
        citation_key=str(enrichment.get("citation_key") or ""),
        authors=", ".join(str(author) for author in authors) if isinstance(authors, list) else str(authors or ""),
        year=str(enrichment.get("year") or ""),
    )


def prepare_inputs(
    raw_root: Path,
    wiki_root: Path,
    project_root: Path | None = None,
    sources_output_dir: Path | None = None,
    cache_root: Path | None = None,
    pdf_titles: dict[str, Any] | None = None,
    warning_sink: list[str] | None = None,
) -> dict[str, Any]:
    raw_root = raw_root.resolve()
    project_root = (project_root or _project_root(raw_root)).resolve()
    wiki_root = wiki_root.resolve()
    if sources_output_dir is None:
        raise ValueError("prepare_inputs requires an explicit sources_output_dir")
    sources_output_dir = sources_output_dir.resolve()
    if cache_root is None:
        raise ValueError("prepare_inputs requires an explicit cache_root")
    cache_root = cache_root.resolve()
    source_root = sources_output_dir
    (source_root / "papers").mkdir(parents=True, exist_ok=True)
    (source_root / "notes").mkdir(parents=True, exist_ok=True)
    (source_root / "web").mkdir(parents=True, exist_ok=True)
    paper_entries: list[dict[str, Any]] = []
    other_entries: list[dict[str, Any]] = []
    normalized_handoffs, original_title_keys = _normalize_pdf_titles_map(raw_root, pdf_titles, warning_sink=warning_sink)
    seen_title_keys: set[str] = set()

    papers_root = raw_root / "papers"
    if papers_root.exists():
        for entry in sorted(papers_root.iterdir()):
            if entry.name == ".gitkeep":
                continue
            source_rel = _relative_to_project(entry, raw_root, project_root=project_root)
            raw_relative_source_rel = _relative_to_project(entry, raw_root)
            recovered = normalized_handoffs.get(source_rel) or normalized_handoffs.get(raw_relative_source_rel, {})
            recovered_title = recovered.get("title", "")
            if recovered_title:
                seen_title_keys.add(source_rel)
                seen_title_keys.add(raw_relative_source_rel)
            paper_entries.append(
                _prepare_paper_entry(entry, raw_root, wiki_root, project_root, sources_output_dir, cache_root, title=recovered_title)
            )

    deduped_papers: dict[str, dict[str, Any]] = {}
    for entry in paper_entries:
        key = entry["candidate_id"]

        existing = deduped_papers.get(key)
        if existing is None:
            deduped_papers[key] = entry
            continue

        if _paper_entry_preference(entry) > _paper_entry_preference(existing):
            kept, dropped = entry, existing
            deduped_papers[key] = entry
        else:
            kept, dropped = existing, entry
        kept["warnings"] = list(dict.fromkeys(
            list(kept.get("warnings", []))
            + list(dropped.get("warnings", []))
            + [f"duplicate local source skipped in favor of preferred source: {kept['source_path']}"]
        ))

    if warning_sink is not None:
        for source_rel, original_key in sorted(original_title_keys.items()):
            if source_rel not in seen_title_keys:
                warning_sink.append(f"ignored unknown PDF title mapping: {original_key}")

    for kind in ("notes", "web"):
        base = raw_root / kind
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.name == ".gitkeep" or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            record = _prepare_text_entry(path, raw_root, kind, sources_output_dir, project_root)
            if record:
                other_entries.append(record)

    return {
        "raw_root": _relative_to_project(raw_root, raw_root, project_root=project_root),
        "prepared_root": _relative_to_project(source_root, raw_root, project_root=project_root),
        "entries": list(deduped_papers.values()) + other_entries,
    }


def _load_prepare_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _prepared_paper_entries(prepared_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not prepared_manifest:
        return []
    return [
        entry
        for entry in prepared_manifest.get("entries", [])
        if entry.get("source_kind") == "paper" and entry.get("usable", True)
    ]


def build_source_manifest(prepared_manifest: dict[str, Any]) -> dict[str, Any]:
    """Build .checkpoints/init-sources.json from a prepared manifest.

    Only emits user_local entries — external discovery is no longer supported.
    """
    sources: list[dict[str, Any]] = []
    for index, entry in enumerate(_prepared_paper_entries(prepared_manifest)):
        canonical = entry["canonical_ingest_path"]
        sources.append({
            "candidate_id": entry["candidate_id"],
            "origin": "user_local",
            "canonical_ingest_path": canonical,
            "prepared_path": entry.get("prepared_path"),
            "discovered_path": None,
            "source_path": entry.get("source_path"),
            "ingest_format": entry.get("ingest_format") or _ingest_format_from_path(canonical),
            "shortlist_rank": index + 1,
        })
    return {"status": "ok", "sources": sources}


def _print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Prepare local raw paper inputs into wiki/sources/ and emit a manifest")
    p_prepare.add_argument("--raw-root", default=None)
    p_prepare.add_argument("--wiki-root", required=True,
                           help="Explicit wiki vault root for path display and graph/wiki context.")
    p_prepare.add_argument("--sources-output-dir", required=True,
                           help="Explicit output directory for generated source copies, e.g. @configured-sources.")
    p_prepare.add_argument("--cache-root", required=True,
                           help="Explicit MinerU cache root for OCR intermediate outputs. Accepts @mineru-cache.")
    p_prepare.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path)
    p_prepare.add_argument("--pdf-titles-json")
    p_prepare.add_argument("--output-manifest", required=True)

    p_manifest = sub.add_parser(
        "manifest",
        help="Build .checkpoints/init-sources.json from a prepared manifest (local papers only)",
    )
    p_manifest.add_argument("--raw-root", default=None)
    p_manifest.add_argument("--wiki-root", default=None)
    p_manifest.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path)
    p_manifest.add_argument("--prepared-manifest", required=True)
    p_manifest.add_argument("--output-sources", required=True)

    args = parser.parse_args()

    if args.command == "prepare":
        pdf_titles = None
        if args.pdf_titles_json:
            try:
                pdf_titles = _load_pdf_titles_json(Path(args.pdf_titles_json))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                parser.error(f"--pdf-titles-json: {exc}")
        warnings: list[str] = []
        base_paths = load_paths(config_path=args.paths_config)
        raw_root = resolve_runtime_path(args.raw_root, base_paths, role="--raw-root") if args.raw_root else base_paths.raw_root
        wiki_root = resolve_runtime_path(args.wiki_root, base_paths, role="--wiki-root")
        paths = load_paths(config_path=args.paths_config, wiki_root=wiki_root, raw_root=raw_root)
        sources_output_dir = resolve_runtime_path(args.sources_output_dir, paths, role="--sources-output-dir")
        cache_root = resolve_runtime_path(args.cache_root, paths, role="--cache-root")
        if sources_output_dir == Path("/sources") or str(sources_output_dir).startswith("/sources/"):
            p_prepare.error("--sources-output-dir resolved under /sources; pass @configured-sources or an absolute wiki path.")
        _reject_repo_wiki_output(p_prepare, sources_output_dir, paths)
        legacy_cache = (paths.project_root / ".mineru-cache").resolve()
        if cache_root == legacy_cache:
            p_prepare.error("--cache-root resolved to legacy .mineru-cache; pass @mineru-cache so cache files go under .checkpoints/mineru-cache.")
        manifest = prepare_inputs(
            paths.raw_root,
            wiki_root=paths.wiki_root,
            project_root=paths.project_root,
            sources_output_dir=sources_output_dir,
            cache_root=cache_root,
            pdf_titles=pdf_titles,
            warning_sink=warnings,
        )
        output_path = Path(args.output_manifest)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        _print_json(manifest)
        return

    if args.command == "manifest":
        base_paths = load_paths(config_path=args.paths_config)
        raw_root = resolve_runtime_path(args.raw_root, base_paths, role="--raw-root") if args.raw_root else base_paths.raw_root
        wiki_root = resolve_runtime_path(args.wiki_root, base_paths, role="--wiki-root") if args.wiki_root else base_paths.wiki_root
        paths = load_paths(config_path=args.paths_config, wiki_root=wiki_root, raw_root=raw_root)
        prepared = _load_prepare_manifest(Path(args.prepared_manifest))
        if not prepared:
            parser.error(f"missing or unreadable prepared manifest: {args.prepared_manifest}")
        source_manifest = build_source_manifest(prepared)
        out = Path(args.output_sources)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(source_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        _print_json(source_manifest)
        return


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

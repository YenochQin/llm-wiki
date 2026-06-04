"""Normalize MinerU prepared source markdown frontmatter.

This maintenance helper rewrites ``wiki/sources/papers/*.md`` frontmatter into
the canonical prepared-source field order and normalizes Zotero attachment paths
to ``${Zotero data directory}/storage/...`` so the files remain portable across
machines.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

from _cli_io import configure_utf8_stdio
import find_zotero_pdf
from prepare_paper_source import _render_yaml


FIELD_ORDER = [
    "title",
    "source",
    "sourceSlug",
    "ingestedAt",
    "sourceType",
    "pipeline",
    "totalPages",
    "totalChars",
    "citationKey",
    "paperSlug",
    "latexRepairReplacements",
    "latexRepairConvertedDelimiters",
    "latexRepairMathSpans",
    "skippedSectionHeadings",
    "droppedHeadings",
    "sections",
    "figures",
]

ZOTERO_STORAGE_RE = re.compile(
    r"(?:^|[\\/])(?:Zotero(?:[\\/](?:data))?|data)[\\/]storage[\\/](?P<rest>.+)$",
    re.IGNORECASE,
)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _normalize_source(value: Any) -> tuple[Any, bool]:
    if not isinstance(value, str):
        return value, False
    raw = value.strip().strip('"').strip("'")
    if raw.startswith("${Zotero data directory}/storage/"):
        return raw.replace("\\", "/"), raw != value

    normalized = raw.replace("\\", "/")
    marker = "/storage/"
    if marker in normalized:
        rest = normalized.split(marker, 1)[1]
        return f"${{Zotero data directory}}/storage/{rest}", True

    match = ZOTERO_STORAGE_RE.search(raw)
    if match:
        rest = match.group("rest").replace("\\", "/")
        return f"${{Zotero data directory}}/storage/{rest}", True

    return value, False


def _portable_zotero_storage_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    marker = "/storage/"
    if marker not in normalized:
        return ""
    rest = normalized.split(marker, 1)[1]
    return f"${{Zotero data directory}}/storage/{rest}"


def _best_zotero_attachment(metadata: dict[str, Any], zotero_root: Path | None) -> str:
    if zotero_root is None:
        return ""
    queries = []
    citation_key = str(metadata.get("citationKey") or "").strip()
    title = str(metadata.get("title") or "").strip()
    if citation_key:
        queries.append(citation_key)
    if title:
        queries.append(title)

    for query in queries:
        result = find_zotero_pdf.find(
            zotero_root=zotero_root,
            query=query,
            doi="",
            item_key="",
            limit=3,
            config_path=find_zotero_pdf.DEFAULT_CONFIG_PATH,
        )
        for candidate in result.get("candidates") or []:
            if citation_key and candidate.get("citation_key") == citation_key:
                attachments = candidate.get("attachments") or []
            elif float(candidate.get("score") or 0) >= 0.88:
                attachments = candidate.get("attachments") or []
            else:
                continue
            for attachment in attachments:
                path = str(attachment.get("path") or "")
                portable = _portable_zotero_storage_path(path)
                if portable:
                    return portable
    return ""


def _ordered_metadata(metadata: dict[str, Any], fallback_slug: str) -> OrderedDict[str, Any]:
    normalized = dict(metadata)
    if not normalized.get("sourceSlug"):
        normalized["sourceSlug"] = fallback_slug
    if not normalized.get("sourceType"):
        normalized["sourceType"] = "pdf"
    if not normalized.get("pipeline"):
        normalized["pipeline"] = "mineru"
    if normalized.get("citationKey") and not normalized.get("paperSlug"):
        normalized["paperSlug"] = normalized["citationKey"]

    ordered: OrderedDict[str, Any] = OrderedDict()
    for key in FIELD_ORDER:
        if key in normalized:
            ordered[key] = normalized.pop(key)
    for key in sorted(normalized):
        ordered[key] = normalized[key]
    return ordered


def _safe_print(text: str) -> None:
    print(text.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace").decode(sys.stdout.encoding or "utf-8"))


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text

    header = "".join(lines[1:end_index])
    body = "".join(lines[end_index + 1 :])
    metadata = yaml.safe_load(CONTROL_RE.sub("", header)) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, body.lstrip("\r\n")


def normalize_file(path: Path, zotero_root: Path | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    metadata, content = _split_frontmatter(text)

    old_source = metadata.get("source")
    new_source, source_changed = _normalize_source(old_source)
    if source_changed:
        metadata["source"] = new_source
    elif isinstance(old_source, str) and not old_source.startswith("${Zotero data directory}/storage/"):
        zotero_source = _best_zotero_attachment(metadata, zotero_root)
        if zotero_source:
            metadata["source"] = zotero_source
            source_changed = True

    ordered = _ordered_metadata(metadata, path.stem)
    new_text = _render_yaml(ordered) + "\n\n" + content.rstrip() + "\n"

    return {
        "path": path,
        "changed": new_text != text,
        "source_changed": source_changed,
        "old_source": old_source,
        "new_source": metadata.get("source"),
        "text": new_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources_dir", type=Path)
    parser.add_argument("--write", action="store_true", help="Write changes instead of reporting only.")
    parser.add_argument("--zotero-root", type=Path, default=None, help="Zotero data directory for matching non-storage source paths.")
    args = parser.parse_args()

    paths = sorted(p for p in args.sources_dir.glob("*.md") if p.is_file())
    changed = []
    source_changed = []
    non_portable_sources = []
    errors = []

    for path in paths:
        try:
            result = normalize_file(path, args.zotero_root)
        except Exception as exc:  # noqa: BLE001 - report all malformed files.
            errors.append((path, exc))
            continue
        if result["changed"]:
            changed.append(result)
        if result["source_changed"]:
            source_changed.append(result)
        source = result["new_source"]
        if source and not str(source).startswith("${Zotero data directory}/storage/"):
            non_portable_sources.append((path.name, source))

    if args.write:
        for result in changed:
            result["path"].write_text(result["text"], encoding="utf-8")

    print(f"scanned={len(paths)}")
    print(f"changed={len(changed)}")
    print(f"source_normalized={len(source_changed)}")
    print(f"non_portable_sources={len(non_portable_sources)}")
    print(f"errors={len(errors)}")
    if source_changed:
        print("source_normalized_files:")
        for result in source_changed[:40]:
            _safe_print(f"- {result['path'].name}: {result['new_source']}")
        if len(source_changed) > 40:
            print(f"- ... {len(source_changed) - 40} more")
    if errors:
        print("errors:")
        for path, exc in errors:
            _safe_print(f"- {path}: {exc}")
        return 1
    if non_portable_sources:
        print("non_portable_source_files:")
        for name, source in non_portable_sources[:40]:
            _safe_print(f"- {name}: {source}")
        if len(non_portable_sources) > 40:
            print(f"- ... {len(non_portable_sources) - 40} more")
    return 0


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())

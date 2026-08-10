#!/usr/bin/env python3
"""Prepare one Zotero paper through a single, manifest-producing interface.

The CLI deliberately accepts a Zotero item key only at this orchestration seam.
It resolves the PDF, fetches normalized metadata, writes a checkpoint bundle,
and invokes ``prepare_paper_source`` with the resolved PDF and metadata.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fetch_zotero_metadata
import find_zotero_pdf
import prepare_paper_source
from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path


def select_pdf(candidate: dict[str, Any]) -> Path:
    paths = [Path(path) for path in candidate.get("pdf_paths") or [] if path]
    if len(paths) != 1:
        raise ValueError(
            "Zotero candidate must have exactly one existing PDF attachment; "
            f"found {len(paths)}"
        )
    return paths[0]


def build_manifest(
    *,
    candidate: dict[str, Any],
    metadata_result: dict[str, Any],
    prepared_result: dict[str, Any],
    metadata_path: Path,
) -> dict[str, Any]:
    metadata = metadata_result.get("metadata") or {}
    return {
        "status": "ok" if prepared_result.get("usable") else "unusable",
        "item_key": candidate.get("item_key") or metadata.get("item_key", ""),
        "source_pdf": str(select_pdf(candidate)),
        "metadata_path": metadata_path.as_posix(),
        "metadata": metadata,
        "prepared": prepared_result,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    paths = load_paths(config_path=args.paths_config)
    zotero_result = find_zotero_pdf.find(
        args.zotero_root,
        query="",
        doi="",
        item_key=args.item_key,
        limit=2,
        config_path=args.paths_config,
    )
    if zotero_result.get("status") != "ok":
        raise RuntimeError(zotero_result.get("message", "Zotero PDF lookup failed"))
    candidates = zotero_result.get("candidates") or []
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one Zotero candidate, found {len(candidates)}")
    candidate = candidates[0]
    pdf_path = select_pdf(candidate)

    metadata_path = Path(args.metadata_output)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        metadata_result = {
            "status": "ok",
            "source": "zotero-local-api",
            "metadata": fetch_zotero_metadata.fetch_item(args.item_key, args.api_base, args.timeout),
        }
    except (OSError, ValueError, TimeoutError) as exc:
        metadata_result = {
            "status": "error",
            "source": "zotero-local-api",
            "message": str(exc),
        }
    metadata_result["source_pdf"] = str(pdf_path)
    metadata_result["candidate"] = {
        "item_key": candidate.get("item_key", ""),
        "match_reason": candidate.get("match_reason", ""),
        "score": candidate.get("score"),
    }
    metadata_path.write_text(json.dumps(metadata_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if metadata_result.get("status") != "ok":
        raise RuntimeError("Zotero metadata status is not ok")
    metadata = metadata_result["metadata"]

    output_dir = resolve_runtime_path(args.output_dir, paths, role="--output-dir")
    cache_root = resolve_runtime_path(args.cache_root, paths, role="--cache-root")
    prepared_result = prepare_paper_source.prepare_paper_source(
        pdf_path,
        paths.raw_root,
        title=metadata.get("title", ""),
        bibtex=metadata.get("bibtex", ""),
        citation_key=metadata.get("citation_key", ""),
        authors="; ".join(metadata.get("authors") or []),
        year=str(metadata.get("year") or ""),
        overwrite=args.overwrite,
        wiki_root=paths.wiki_root,
        output_dir=output_dir,
        cache_root=cache_root,
        project_root=paths.project_root,
    )
    manifest = build_manifest(
        candidate=candidate,
        metadata_result=metadata_result,
        prepared_result=prepared_result,
        metadata_path=metadata_path,
    )
    manifest_path = metadata_path.with_name("manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-key", required=True)
    parser.add_argument("--zotero-root", type=Path)
    parser.add_argument("--api-base", default="")
    parser.add_argument("--timeout", type=float, default=fetch_zotero_metadata.DEFAULT_TIMEOUT)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument(
        "--metadata-output",
        default="",
        help="Checkpoint metadata path (default: .checkpoints/ingest/<item-key>/metadata.json).",
    )
    parser.add_argument("--paths-config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not args.metadata_output:
        args.metadata_output = str(Path(".checkpoints") / "ingest" / args.item_key / "metadata.json")
    try:
        print(json.dumps(run(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), flush=True)
        raise SystemExit(2)


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

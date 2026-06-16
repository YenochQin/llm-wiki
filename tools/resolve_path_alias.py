#!/usr/bin/env python3
"""Resolve llm-wiki runtime path aliases.

This is the supported CLI for checking aliases such as ``@configured`` and
``@configured-sources-papers``. Do not import path helpers from ``_env``;
environment loading and runtime path resolution are separate concerns.

Purpose:
    Turn llm-wiki runtime aliases into absolute paths before using normal shell
    commands that do not understand aliases.

Inputs:
    Aliases or paths. With no positional arguments, common aliases are printed.

Writes:
    Nothing. Results are printed as tab-separated text or JSON.

Usage:
    uv run python -X utf8 tools/resolve_path_alias.py
    uv run python -X utf8 tools/resolve_path_alias.py @configured @raw-root
    uv run python -X utf8 tools/resolve_path_alias.py --json @configured-sources-papers
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path

DEFAULT_ALIASES = [
    "@project-root",
    "@configured",
    "@raw-root",
    "@configured-sources",
    "@configured-sources-papers",
    "@mineru-cache",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Aliases or paths to resolve. Defaults to common llm-wiki aliases.",
    )
    parser.add_argument(
        "--paths-config",
        default=DEFAULT_CONFIG_PATH,
        type=Path,
        help="Path config JSON (default: config/paths.json).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        runtime_paths = load_paths(config_path=args.paths_config)
        requested = args.paths or DEFAULT_ALIASES
        resolved = {
            value: str(resolve_runtime_path(value, runtime_paths, role="path-alias"))
            for value in requested
        }
    except Exception as exc:
        if args.json:
            print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    if args.json:
        payload = {
            "status": "ok",
            "config_path": str(runtime_paths.config_path),
            "profile": runtime_paths.profile,
            "used_config": runtime_paths.used_config,
            "paths": resolved,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for key, value in resolved.items():
        print(f"{key}\t{value}")


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

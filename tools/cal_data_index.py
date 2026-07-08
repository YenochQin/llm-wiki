#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path

DEFAULT_DATA_DIR: Final = "temp/cal_data"
DEFAULT_REPORT_DIR: Final = "experiments/cal_reports"
CLI_DESCRIPTION: Final = "Generate Obsidian-browsable reports for wiki-local calculation data."
MAX_CELL_CHARS: Final = 80
TEXT_EXTENSIONS: Final = {".txt", ".log", ".md", ".yaml", ".yml", ".json", ".toml"}
IMAGE_EXTENSIONS: Final = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


@dataclass(frozen=True, slots=True)
class IndexRequest:
    wiki_root: Path
    data_dir: str = DEFAULT_DATA_DIR
    report_dir: str = DEFAULT_REPORT_DIR
    table_rows: int = 8
    text_lines: int = 20


@dataclass(frozen=True, slots=True)
class IndexResult:
    wiki_root: Path
    data_root: Path
    report_root: Path
    run_count: int
    report_count: int


@dataclass(frozen=True, slots=True)
class RunSource:
    name: str
    slug: str
    path: Path
    files: tuple[Path, ...]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "cal-data"


def _wiki_path(path: Path) -> str:
    return path.as_posix()


def _relative_link(from_dir: Path, target: Path) -> str:
    return Path(os.path.relpath(target, from_dir)).as_posix()


def _file_size(path: Path) -> str:
    size = path.stat().st_size
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} B"
        value /= 1024
    return f"{size} B"


def _truncate_cell(value: str) -> str:
    cleaned = value.replace("\n", " ").replace("|", "\\|").strip()
    if len(cleaned) <= MAX_CELL_CHARS:
        return cleaned
    return cleaned[: MAX_CELL_CHARS - 1].rstrip() + "..."


def _markdown_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = [_truncate_cell(cell) or f"column-{index + 1}" for index, cell in enumerate(normalized[0])]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _column in header) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(_truncate_cell(cell) for cell in row) + " |")
    return "\n".join(lines)


def _read_delimited_preview(path: Path, limit: int) -> tuple[int, str]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    rows: list[list[str]] = []
    row_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            if row_count <= limit:
                rows.append(row)
            row_count += 1
    data_rows = max(row_count - 1, 0)
    return data_rows, _markdown_table(rows)


def _read_line_preview(path: Path, limit: int) -> tuple[int, str]:
    lines: list[str] = []
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            if count < limit:
                lines.append(raw_line.rstrip("\n"))
            count += 1
    return count, "\n".join(lines)


def _kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return suffix.lstrip(".")
    if suffix == ".jsonl":
        return "jsonl"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return suffix.lstrip(".") or "text"
    return "file"


def _discover_runs(data_root: Path) -> tuple[RunSource, ...]:
    if not data_root.exists():
        return ()
    runs: list[RunSource] = []
    direct_files = tuple(sorted(path for path in data_root.iterdir() if path.is_file()))
    if direct_files:
        runs.append(
            RunSource(
                name="cal_data root files",
                slug="cal-data-root",
                path=data_root,
                files=direct_files,
            )
        )
    for child in sorted(path for path in data_root.iterdir() if path.is_dir()):
        files = tuple(sorted(path for path in child.rglob("*") if path.is_file()))
        runs.append(RunSource(name=child.name, slug=_slugify(child.name), path=child, files=files))
    return tuple(runs)


def _file_table(run: RunSource, report_dir: Path) -> str:
    lines = ["| file | type | size | rows/items | link |", "|---|---:|---:|---:|---|"]
    for path in run.files:
        kind = _kind_for(path)
        item_count = ""
        if kind in {"csv", "tsv", "jsonl"}:
            item_count = str(_read_delimited_preview(path, 0)[0] if kind in {"csv", "tsv"} else _read_line_preview(path, 0)[0])
        run_relative = _wiki_path(path.relative_to(run.path))
        link = _relative_link(report_dir, path)
        lines.append(
            f"| `{run_relative}` | {kind} | {_file_size(path)} | {item_count} | [{path.name}]({link}) |"
        )
    return "\n".join(lines)


def _preview_sections(run: RunSource, report_dir: Path, request: IndexRequest) -> str:
    sections: list[str] = []
    for path in run.files:
        kind = _kind_for(path)
        link = _relative_link(report_dir, path)
        run_relative = _wiki_path(path.relative_to(run.path))
        if kind in {"csv", "tsv"}:
            row_count, table = _read_delimited_preview(path, request.table_rows)
            sections.append(f"### {run_relative}\n\nRows: {row_count}\n\n{table}".rstrip())
        elif kind == "jsonl":
            count, preview = _read_line_preview(path, request.text_lines)
            sections.append(f"### {run_relative}\n\nItems: {count}\n\n```jsonl\n{preview}\n```")
        elif kind == "image":
            sections.append(f"### {run_relative}\n\n![{path.name}]({link})")
        elif path.suffix.lower() in TEXT_EXTENSIONS:
            _count, preview = _read_line_preview(path, request.text_lines)
            fence = path.suffix.lower().lstrip(".") or "text"
            sections.append(f"### {run_relative}\n\n```{fence}\n{preview}\n```")
    return "\n\n".join(sections)


def _report_content(run: RunSource, report_dir: Path, request: IndexRequest) -> str:
    generated = datetime.now(timezone.utc).date().isoformat()
    source_link = _relative_link(report_dir, run.path)
    preview = _preview_sections(run, report_dir, request)
    preview_section = preview if preview else "No previewable files found."
    return (
        f"# {run.name}\n\n"
        "## Summary\n\n"
        f"- source_dir: [{_wiki_path(run.path.relative_to(request.wiki_root))}]({source_link})\n"
        f"- generated_at: {generated}\n"
        f"- file_count: {len(run.files)}\n"
        "- related: \n\n"
        "## Files\n\n"
        f"{_file_table(run, report_dir)}\n\n"
        "## Previews\n\n"
        f"{preview_section}\n\n"
        "## Notes\n\n"
        "- \n"
    )


def _index_content(runs: tuple[RunSource, ...], request: IndexRequest) -> str:
    generated = datetime.now(timezone.utc).date().isoformat()
    lines = [
        "# Calculation reports",
        "",
        "## Summary",
        "",
        f"- data_dir: `{request.data_dir}`",
        f"- generated_at: {generated}",
        f"- run_count: {len(runs)}",
        "",
        "## Runs",
        "",
    ]
    if not runs:
        lines.append("No calculation data found.")
    for run in runs:
        lines.append(f"- [[{run.slug}]] — `{_wiki_path(run.path.relative_to(request.wiki_root))}`")
    return "\n".join(lines) + "\n"


def build_reports(request: IndexRequest) -> IndexResult:
    data_root = (request.wiki_root / request.data_dir).resolve()
    report_root = (request.wiki_root / request.report_dir).resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    runs = _discover_runs(data_root)
    for run in runs:
        (report_root / f"{run.slug}.md").write_text(
            _report_content(run, report_root, request),
            encoding="utf-8",
        )
    (report_root / "index.md").write_text(_index_content(runs, request), encoding="utf-8")
    return IndexResult(
        wiki_root=request.wiki_root,
        data_root=data_root,
        report_root=report_root,
        run_count=len(runs),
        report_count=len(runs) + 1,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=CLI_DESCRIPTION)
    parser.add_argument("wiki_root", nargs="?", default="@configured")
    parser.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--table-rows", default=8, type=int)
    parser.add_argument("--text-lines", default=20, type=int)
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    base_paths = load_paths(config_path=args.paths_config)
    wiki_root = resolve_runtime_path(args.wiki_root, base_paths, role="wiki_root")
    if wiki_root is None:
        print("wiki_root could not be resolved", file=sys.stderr)
        return 2
    result = build_reports(
        IndexRequest(
            wiki_root=wiki_root,
            data_dir=args.data_dir,
            report_dir=args.report_dir,
            table_rows=max(args.table_rows, 0),
            text_lines=max(args.text_lines, 0),
        )
    )
    print(
        f"generated {result.report_count} report file(s) for {result.run_count} run(s) "
        f"under {result.report_root}"
    )
    return 0


def main() -> None:
    configure_utf8_stdio()
    raise SystemExit(_main())


if __name__ == "__main__":
    main()

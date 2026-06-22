#!/usr/bin/env python3
"""Migrate legacy wiki/log.md entries into weekly wiki/log/*.md files.

Default mode is a dry run. Pass --yes to write migrated entries. The old
log.md file is never deleted or modified.

Purpose:
    Convert the legacy single log file into the current weekly log layout.

Inputs:
    Legacy wiki/log.md, or old weekly filenames when --rename-old-weekly is set.

Writes:
    Weekly wiki/log/yyyy-mm-wN.md files only when --yes is provided. The legacy
    log.md file is preserved.

Usage:
    uv run python -X utf8 tools/migrate_log.py --wiki-root @configured
    uv run python -X utf8 tools/migrate_log.py --wiki-root @configured --yes
    uv run python -X utf8 tools/migrate_log.py --wiki-root @configured --rename-old-weekly --yes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import load_paths
from research_wiki import LOG_DIR, LOG_HEADER, _log_period_filename, _parse_log_message

LEGACY_ENTRY_RE = re.compile(r"^##\s+\[(\d{4}-\d{2}-\d{2})\]\s+(.+?)\s*$")
CONFLICT_MARKER_RE = re.compile(r"^(?:<{7}|={7}|>{7})")
OLD_WEEKLY_LOG_RE = re.compile(r"^(\d{4}-\d{2})-(\d{2})\.md$")
WRONG_EXTENSION_LOG_RE = re.compile(r"^(\d{4}-\d{2}-w[1-5])\.log$")


@dataclass
class LegacyLogEntry:
    date: str
    skill: str
    lines: list[str]

    @property
    def target_filename(self) -> str:
        return _log_period_filename(datetime.strptime(self.date, "%Y-%m-%d"))


def _resolve_wiki_root(value: str) -> Path:
    if value in {"@configured", "@wiki"}:
        return load_paths().wiki_root.resolve()
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def _normalize_body(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    return out


def parse_legacy_log(content: str) -> tuple[list[LegacyLogEntry], list[str]]:
    """Parse old `## [YYYY-MM-DD] skill | details` log headings."""
    entries: list[LegacyLogEntry] = []
    warnings: list[str] = []
    current_date = ""
    current_message = ""
    current_body: list[str] = []
    seen_first_entry = False

    def flush() -> None:
        nonlocal current_date, current_message, current_body
        if not current_date:
            return
        skill, details = _parse_log_message(current_message)
        lines = [f"[{current_date}] {details}"]
        lines.extend(_normalize_body(current_body))
        entries.append(LegacyLogEntry(current_date, skill, lines))
        current_date = ""
        current_message = ""
        current_body = []

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        match = LEGACY_ENTRY_RE.match(raw_line)
        if match:
            flush()
            current_date = match.group(1)
            current_message = match.group(2)
            seen_first_entry = True
            continue

        if raw_line.strip() in {"# LLMWiki Log", "# log"}:
            continue
        if CONFLICT_MARKER_RE.match(raw_line):
            warnings.append(f"conflict marker line {line_no}: {raw_line[:80]}")

        if current_date:
            current_body.append(raw_line)
        elif raw_line.strip() and seen_first_entry:
            warnings.append(f"unattached non-empty line {line_no}: {raw_line[:80]}")

    flush()
    return entries, warnings


def _section_bounds(content: str, skill: str) -> tuple[int, int] | None:
    heading_re = re.compile(rf"(?m)^##\s+{re.escape(skill)}\s*$")
    match = heading_re.search(content)
    if not match:
        return None
    body_start = match.end()
    next_heading = re.search(r"(?m)^##\s+", content[body_start:])
    section_end = body_start + (
        next_heading.start() if next_heading else len(content[body_start:])
    )
    return body_start, section_end


def _append_block_to_section(
    log_path: Path, skill: str, lines: list[str], *, dry_run: bool
) -> bool:
    """Append a multiline entry block under `## skill`.

    Returns True when the block would be/w was added, False when it already
    exists in that skill section.
    """
    block = "\n".join(lines).rstrip()
    if not block:
        return False

    if log_path.exists():
        content = log_path.read_text(encoding="utf-8")
        if not content.strip():
            content = LOG_HEADER
    else:
        content = LOG_HEADER

    if not content.startswith("# "):
        content = LOG_HEADER + content.lstrip()

    bounds = _section_bounds(content, skill)
    if bounds is None:
        new_content = content.rstrip() + f"\n\n## {skill}\n{block}\n"
    else:
        _body_start, section_end = bounds
        section_text = content[bounds[0] : bounds[1]]
        if block in section_text:
            return False
        before = content[:section_end].rstrip()
        after = content[section_end:].lstrip("\n")
        if after:
            new_content = f"{before}\n{block}\n\n{after}"
        else:
            new_content = f"{before}\n{block}\n"

    if not dry_run:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(new_content, encoding="utf-8")
    return True


def migrate_log(
    wiki_root: Path, *, source: Path | None = None, dry_run: bool = True
) -> dict:
    source_path = source or (wiki_root / "log.md")
    output_dir = wiki_root / LOG_DIR
    if not source_path.exists():
        return {
            "status": "error",
            "message": f"legacy log file not found: {source_path}",
            "source": str(source_path),
            "output_dir": str(output_dir),
        }

    entries, warnings = parse_legacy_log(
        source_path.read_text(encoding="utf-8", errors="ignore")
    )
    file_summary: dict[str, dict] = {}
    added = 0
    skipped = 0

    for entry in entries:
        rel_path = f"{LOG_DIR}/{entry.target_filename}"
        target = wiki_root / rel_path
        summary = file_summary.setdefault(
            rel_path, {"entries_added": 0, "entries_skipped": 0, "skills": {}}
        )
        if _append_block_to_section(target, entry.skill, entry.lines, dry_run=dry_run):
            added += 1
            summary["entries_added"] += 1
            summary["skills"][entry.skill] = summary["skills"].get(entry.skill, 0) + 1
        else:
            skipped += 1
            summary["entries_skipped"] += 1

    return {
        "status": "dry_run" if dry_run else "ok",
        "changed": bool(added) and not dry_run,
        "source": str(source_path),
        "output_dir": str(output_dir),
        "entries_found": len(entries),
        "entries_to_add": added,
        "entries_skipped_existing": skipped,
        "files": [
            {"path": path, **summary} for path, summary in sorted(file_summary.items())
        ],
        "warnings": warnings,
    }


def _new_weekly_name_from_old(path: Path) -> str:
    old_weekly = OLD_WEEKLY_LOG_RE.match(path.name)
    if old_weekly:
        week = int(old_weekly.group(2))
        if week < 1 or week > 5:
            return ""
        return f"{old_weekly.group(1)}-w{week}.md"

    wrong_extension = WRONG_EXTENSION_LOG_RE.match(path.name)
    if wrong_extension:
        return f"{wrong_extension.group(1)}.md"

    return ""


def rename_old_weekly_logs(wiki_root: Path, *, dry_run: bool = True) -> dict:
    """Rename old weekly log names to Obsidian-visible yyyy-mm-wN.md files."""
    log_dir = wiki_root / LOG_DIR
    planned: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    if not log_dir.exists():
        return {
            "status": "dry_run" if dry_run else "ok",
            "changed": False,
            "renamed": [],
            "conflicts": [],
            "message": f"log directory not found: {log_dir}",
        }

    for old_path in sorted(log_dir.iterdir()):
        if not old_path.is_file():
            continue
        new_name = _new_weekly_name_from_old(old_path)
        if not new_name:
            continue
        new_path = old_path.with_name(new_name)
        item = {"from": str(old_path), "to": str(new_path)}
        if new_path.exists():
            conflicts.append(item)
            continue
        planned.append(item)
        if not dry_run:
            old_path.rename(new_path)

    return {
        "status": "dry_run" if dry_run else "ok",
        "changed": bool(planned) and not dry_run,
        "renamed": planned,
        "conflicts": conflicts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--wiki-root", default="@configured", help="Wiki root, default: @configured"
    )
    parser.add_argument(
        "--source", default="", help="Legacy log file path, default: <wiki-root>/log.md"
    )
    parser.add_argument(
        "--rename-old-weekly",
        action="store_true",
        help="Rename old weekly yyyy-mm-NN.md or yyyy-mm-wN.log files to yyyy-mm-wN.md",
    )
    parser.add_argument("--yes", action="store_true", help="Write migrated entries")
    args = parser.parse_args()

    wiki_root = _resolve_wiki_root(args.wiki_root)
    if args.rename_old_weekly:
        result = rename_old_weekly_logs(wiki_root, dry_run=not args.yes)
    else:
        source = Path(args.source).expanduser().resolve() if args.source else None
        result = migrate_log(wiki_root, source=source, dry_run=not args.yes)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

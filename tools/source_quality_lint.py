#!/usr/bin/env python3
"""Read-only screening of prepared source Markdown before evidence extraction.

Usage:
    uv run python -X utf8 tools/source_quality_lint.py <source.md> --json
    uv run python -X utf8 tools/source_quality_lint.py @configured-sources-papers

Defaults to @configured-sources-papers. Inputs may be files or directories.
Prints Markdown, or JSON with --json; never writes files or calls a model/API.
Optional --wiki-dir adds direct prepared-source references from existing pages.
Exit 0: no red findings (warnings still require review); 1: red findings;
2: invalid invocation/input. No-findings does NOT establish PDF fidelity.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import frontmatter

from _cli_io import configure_utf8_stdio
from _paths import DEFAULT_CONFIG_PATH, load_paths, resolve_runtime_path
from _source_markdown import abstract_text, mask_noncontent, section_heading


RULESET_VERSION = "1"
LIMITATIONS = [
    "Rule findings are review candidates, not confirmed OCR errors or a measured error rate.",
    "PDF pages, MinerU cache blocks and scientific correctness have not been checked.",
    "Plausible wrong digits/signs, reading order, lost content and semantic contradictions may escape these rules.",
    "No findings means only that these rules did not match. Selected evidence still needs agent review.",
    "Direct referencing pages are an impact shortlist, not proof that a damaged fragment was used; claims reached through papers are not expanded.",
]


class _TableParser(HTMLParser):
    """Widths of simple HTML rows; rowspan tables are left to manual review."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.width = 0
        self.rowspan = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.width = 0
        if tag in {"td", "th"}:
            attrs = dict(attrs)
            self.rowspan |= attrs.get("rowspan", "1") != "1"
            try:
                self.width += max(1, int(attrs.get("colspan", "1")))
            except (TypeError, ValueError):
                self.rowspan = True  # Complex/malformed markup needs visual review.

    def handle_endtag(self, tag):
        if tag == "tr":
            self.rows.append((self.getpos()[0], self.width))


def _pipe_cells(line: str) -> list[str]:
    # Literal pipes inside math and escaped Markdown pipes are not separators.
    line = re.sub(r"(?<!\\)\$[^$\n]*?(?<!\\)\$", "MATH", line)
    return re.split(r"(?<!\\)\|", line.strip().strip("|"))


def scan_text(text: str, *, path: Path | None = None) -> dict:
    """Screen one string; all line/column coordinates refer to its original text."""
    issues = []
    offsets = [0] + [m.end() for m in re.finditer("\n", text)]

    def add(rule, severity, offset, message, *, end=None, scope="fragment"):
        offset = max(0, min(offset, len(text)))
        line_idx = bisect.bisect_right(offsets, offset) - 1
        end = offset + 1 if end is None else end
        line_end = text.find("\n", offset)
        line_end = len(text) if line_end < 0 else line_end
        excerpt_start = max(offsets[line_idx], offset - 75)
        excerpt_end = min(line_end, max(offset + 120, end))
        issues.append({
            "rule": rule, "severity": severity, "scope": scope,
            "line": line_idx + 1, "column": offset - offsets[line_idx] + 1,
            "end_line": bisect.bisect_right(offsets, max(offset, end - 1)),
            "excerpt": text[excerpt_start:excerpt_end][:300], "message": message,
        })

    metadata = {}
    if re.match(r"\A\ufeff?---[^\S\n]*(?:\n|$)", text):
        if not re.search(r"\n(?:---|\.\.\.)[^\S\n]*(?:\n|$)", text):
            add("frontmatter-invalid", "red", 0, "Unclosed YAML frontmatter.", scope="document")
        else:
            try:
                metadata = frontmatter.loads(text.lstrip("\ufeff")).metadata
            except Exception as exc:
                add("frontmatter-invalid", "red", 0, f"Cannot parse YAML: {type(exc).__name__}.", scope="document")

    visible = mask_noncontent(text)
    lines = visible.split("\n")
    original_lines = text.split("\n")
    chars = len(re.sub(r"\s", "", visible))
    if not visible.strip():
        add("empty-source", "red", 0, "No body content outside metadata/code.", scope="document")

    for match in re.finditer(r"\?{2,}|\ufffd", visible):
        add("missing-character", "red", match.start(),
            "Possible lost symbols/characters. Withhold this fragment as evidence until verified.", end=match.end())
    for match in re.finditer(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", visible):
        add("control-character", "red", match.start(),
            f"Unexpected control character U+{ord(match.group()):04X} in source text; verify the original glyph.")
    for match in re.finditer(r"\b[a-z][A-Za-z]{11,}\b", visible):
        word = match.group()
        changes = sum(a.isupper() != b.isupper() for a, b in zip(word, word[1:]))
        if changes >= 4:
            add("suspicious-word", "warn", match.start(),
                "Unusual internal capitalization; inspect for OCR garbage or a legitimate identifier.", end=match.end())

    headings = [(i, section_heading(line)) for i, line in enumerate(lines)]
    abstracts = [(i, name) for i, name in headings if name in {"abstract", "摘要"}]
    if not abstracts:
        add("abstract-not-located", "info", 0,
            "No explicit abstract label found; a letter, chapter or unlabeled abstract may be valid.", scope="document")
    for i, _ in abstracts:
        original = original_lines[i].strip()
        if not re.fullmatch(r"#{1,6}\s+(?:abstract|摘要)\s*", original, re.I):
            add("abstract-heading-variant", "info", offsets[i],
                "Abstract uses a plain/bold/letter-spaced label. The shared reader recognizes it; check its boundaries.")
    if abstracts and not abstract_text(text):
        add("empty-abstract", "warn", offsets[abstracts[0][0]], "Explicit abstract has no text before the next section.")

    pages = metadata.get("totalPages")
    if isinstance(pages, (int, float)) and not isinstance(pages, bool) and pages >= 3 and chars / pages < 200:
        add("low-text-per-page", "warn", 0,
            f"{chars} non-whitespace body characters across {pages} recorded pages (<200/page); inspect for missing content or image-heavy pages.", scope="document")
    skipped = metadata.get("skippedSectionHeadings", [])
    if isinstance(skipped, list):
        for heading in skipped:
            if re.search(r"appendix|supplement|supporting", str(heading), re.I):
                at = text.find(str(heading))
                add("excluded-source-section", "warn", max(0, at),
                    f"Adapter recorded an omitted section: {heading}. Verify whether planned evidence needs it; omission may be intentional.", scope="document")

    seen = {}
    paragraph_text = "".join(
        re.sub(r"[^\n]", " ", line) if section_heading(line) else line
        for line in visible.splitlines(keepends=True)
    )
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", paragraph_text):
        paragraph = re.sub(r"\s+", " ", match.group()).strip()
        if len(paragraph) < 180 or any(c in paragraph for c in ("$", "|", "<", "#")):
            continue
        if paragraph in seen:
            add("repeated-paragraph", "warn", match.start(),
                f"Exact long paragraph also appears at line {seen[paragraph]}; possible duplicated extraction.")
        else:
            seen[paragraph] = bisect.bisect_right(offsets, match.start())

    # Keep delimiters and formulas outside code; resume after malformed inline
    # spans at paragraph boundaries so a single lost delimiter doesn't eat a file.
    tokens = list(re.finditer(r"(?<!\\)(?:\$\$|\$|\\[()\[\]])", visible))
    opener = None
    closing = {"$": "$", "$$": "$$", r"\(": r"\)", r"\[": r"\]"}
    for token in tokens:
        value = token.group()
        if opener is not None:
            between = visible[opener.end():token.start()]
            cell_or_section = re.search(r"</(?:td|th)\s*>|^#{1,6}\s+", between, re.I | re.M)
            paragraph = opener.group() in {"$", r"\("} and re.search(r"\n[ \t\r]*\n", between)
            if cell_or_section or paragraph:
                add("math-delimiter", "warn", opener.start(),
                    "Math has no closing delimiter before a paragraph, table cell or section boundary.")
                opener = None
        if opener is None:
            if value in closing:
                opener = token
            else:
                add("math-delimiter", "warn", token.start(), "Math closing delimiter has no opener.")
            continue
        if value != closing[opener.group()]:
            add("math-delimiter", "warn", opener.start(), "Math opener interrupted by a different delimiter; inspect formula boundaries.")
            opener = token if value in closing else None
            continue
        formula = visible[opener.end():token.start()]
        depth = 0
        unbalanced = False
        for brace in re.finditer(r"(?<!\\)[{}]", formula):
            depth += 1 if brace.group() == "{" else -1
            unbalanced |= depth < 0
        if unbalanced or depth:
            add("math-braces", "warn", opener.start(), "Unbalanced unescaped braces inside math.", end=token.end())
        environments = []
        bad_environment = False
        for env in re.finditer(r"\\(begin|end)\s*\{([^}]+)\}", formula):
            if env.group(1) == "begin":
                environments.append(env.group(2))
            elif not environments or environments.pop() != env.group(2):
                bad_environment = True
        if environments or bad_environment:
            add("math-environment", "warn", opener.start(), "Unmatched or mismatched LaTeX environments.", end=token.end())
        opener = None
    if opener is not None:
        add("math-delimiter", "warn", opener.start(), "Math delimiter remains unclosed at end of source.")

    for i in range(1, len(lines)):
        cells = _pipe_cells(lines[i])
        if "|" not in lines[i] or not all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells):
            continue
        width = len(cells)
        for j in [i - 1, *range(i + 1, len(lines))]:
            if "|" not in lines[j] or not lines[j].strip():
                break
            actual = len(_pipe_cells(lines[j]))
            if actual != width:
                add("table-columns", "warn", offsets[j], f"Markdown table has {actual} cells; separator defines {width}.")
    for table in re.finditer(r"<table\b[^>]*>.*?</table\s*>", visible, re.I | re.S):
        parser = _TableParser()
        parser.feed(table.group())
        if not parser.rowspan and len({width for _, width in parser.rows}) > 1:
            add("table-columns", "warn", table.start(),
                f"HTML row widths differ after colspan expansion: {sorted(set(w for _, w in parser.rows))}; inspect merged cells and alignment.")

    if path:
        for image in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
            target = image.group(1).strip().strip("<>")
            if ":" not in target and not (path.parent / unquote(target.split("#")[0])).is_file():
                add("missing-image", "warn", image.start(), "Local image target does not exist; figure evidence may be unavailable.")

    issues.sort(key=lambda item: (item["line"], item["column"], item["rule"]))
    blocked = any(i["scope"] == "document" and i["severity"] == "red" for i in issues)
    return {
        "path": str(path.resolve()) if path else None,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "status": "blocked" if blocked else "review_required" if issues else "no_findings",
        "body_characters": chars, "issues": issues,
    }


def reference_index(wiki: Path) -> dict[str, list[str]]:
    """Index actual direct Markdown links, not source/page filename guesses."""
    refs = {}
    for kind in ("papers", "concepts", "claims"):
        for page in sorted((wiki / kind).glob("*.md")):
            text = page.read_text(encoding="utf-8")
            for match in re.finditer(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)", text):
                target = unquote(match.group(1).split("#")[0].strip().strip("<>"))
                if "://" in target:
                    continue
                source = (page.parent / target).resolve()
                if source.is_relative_to((wiki / "sources/papers").resolve()):
                    refs.setdefault(str(source), set()).add(str(page.resolve()))
    return {key: sorted(value) for key, value in refs.items()}


def scan_paths(paths: list[Path], *, wiki: Path | None = None) -> dict:
    files = set()
    for path in paths:
        if path.is_dir():
            candidates = [p.resolve() for p in path.rglob("*.md") if p.is_file()]
            if not candidates:
                raise ValueError(f"No Markdown sources found in {path}")
            files.update(candidates)
        elif path.is_file() and path.suffix.lower() == ".md":
            files.add(path.resolve())
        else:
            raise ValueError(f"Source path missing or not Markdown: {path}")
    refs = reference_index(wiki) if wiki else {}
    reports = []
    for path in sorted(files):
        try:
            data = path.read_bytes()
            report = scan_text(data.decode("utf-8"), path=path)
        except UnicodeDecodeError:
            report = {
                "path": str(path), "sha256": hashlib.sha256(data).hexdigest(),
                "status": "blocked", "body_characters": None,
                "issues": [{"rule": "invalid-utf8", "severity": "red", "scope": "document",
                            "line": 1, "column": 1, "end_line": 1, "excerpt": "",
                            "message": "Source is not valid UTF-8; bytes were not silently discarded."}],
            }
        report["referencing_pages"] = refs.get(str(path), [])
        reports.append(report)
    issues = [issue for report in reports for issue in report["issues"]]
    return {
        "ruleset_version": RULESET_VERSION, "mode": "read-only-rule-screen",
        "limitations": LIMITATIONS,
        "summary": {
            "files_scanned": len(reports), "files_with_findings": sum(bool(r["issues"]) for r in reports),
            "files_with_red": sum(any(i["severity"] == "red" for i in r["issues"]) for r in reports),
            "files_blocked": sum(r["status"] == "blocked" for r in reports),
            "issue_counts": dict(sorted(Counter(i["severity"] for i in issues).items())),
            "rule_counts": dict(sorted(Counter(i["rule"] for i in issues).items())),
        },
        "files": reports,
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    out = ["# Source quality screening report", "", f"Ruleset: {report['ruleset_version']}; mode: read-only.", "",
           f"Scanned **{summary['files_scanned']}** sources; **{summary['files_with_red']}** with red findings; "
           f"**{summary['files_blocked']}** unreadable/empty/invalid sources blocked as whole documents.", "",
           "Red fragment findings restrict those fragments, not automatically the whole paper. "
           "Warnings and information require contextual review. No scientific/PDF fidelity audit was performed.", "",
           "## Coverage limits", "", *[f"- {item}" for item in report["limitations"]], "",
           "## Rule counts", "", "| Rule | Matches |", "| --- | ---: |"]
    out.extend(f"| {rule} | {count} |" for rule, count in summary["rule_counts"].items())
    out.extend(["", "## Findings by source", ""])
    ranked = sorted(report["files"], key=lambda r: (
        -sum(i["severity"] == "red" for i in r["issues"]),
        -sum(i["severity"] == "warn" for i in r["issues"]), r["path"]))
    for file in ranked:
        if not file["issues"]:
            continue
        out.extend([f"### {Path(file['path']).name}", "", f"Source: [open](<{file['path']}>). "
                    f"Status: `{file['status']}`. SHA-256: `{file['sha256']}`.", ""])
        if file["referencing_pages"]:
            out.extend(["Direct referencing pages (impact candidates only): " + ", ".join(
                f"[{Path(p).stem}](<{p}>)" for p in file["referencing_pages"]), ""])
        for issue in file["issues"]:
            out.extend([f"- **{issue['severity']} · {issue['rule']}** — "
                        f"[L{issue['line']}:{issue['column']}](<{file['path']}:{issue['line']}>) "
                        f"({issue['scope']}): {issue['message']}"])
            if issue["excerpt"]:
                # Keep source characters exact; a code fence avoids broken source math rendering.
                excerpt = issue["excerpt"]
                fence = "`" * max(3, max((len(m.group()) + 1 for m in re.finditer(r"`+", excerpt)), default=3))
                out.extend(["", "  " + fence + "text", *["  " + line for line in excerpt.splitlines()], "  " + fence, ""])
        out.append("")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="Prepared Markdown files/directories; supports aliases.")
    parser.add_argument("--json", action="store_true", help="Print full machine-readable report.")
    parser.add_argument("--wiki-dir", help="Optional wiki root for direct source-reference mapping.")
    parser.add_argument("--paths-config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args(argv)
    try:
        runtime = load_paths(config_path=args.paths_config)
        paths = [resolve_runtime_path(p, runtime, role="source", require_external=True)
                 for p in args.paths or ["@configured-sources-papers"]]
        wiki = resolve_runtime_path(args.wiki_dir, runtime, role="wiki-dir", require_external=True) if args.wiki_dir else None
        if wiki and not wiki.is_dir():
            raise ValueError(f"Wiki directory does not exist: {wiki}")
        report = scan_paths(paths, wiki=wiki)
    except (OSError, ValueError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_markdown(report), end="\n")
    return 1 if report["summary"]["files_with_red"] else 0


if __name__ == "__main__":
    configure_utf8_stdio()
    raise SystemExit(main())

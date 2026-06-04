#!/usr/bin/env python3
"""Conservatively repair OCR-spaced LaTeX math in Markdown.

The repair pass only edits math spans and display math blocks. Markdown code
fences and inline code are copied through untouched so BibTeX and examples do
not get rewritten accidentally.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from _cli_io import configure_utf8_stdio
from _paths import load_paths, resolve_runtime_path


@dataclass(frozen=True)
class LatexRepairReport:
    replacements: int
    converted_delimiters: int
    math_spans: int

    @property
    def changed(self) -> bool:
        return self.replacements > 0 or self.converted_delimiters > 0

    def as_dict(self) -> dict[str, int | bool]:
        return {
            "changed": self.changed,
            "replacements": self.replacements,
            "converted_delimiters": self.converted_delimiters,
            "math_spans": self.math_spans,
        }


TEXT_LIKE_COMMANDS = {"text", "mbox", "textrm", "textit", "textbf", "emph"}
ORBITAL_LETTERS = "spdfghiklm"
TERM_SYMBOL_LETTERS = "SPDFGHIKLMNOQ"
ORBITAL_TOKEN_PATTERN = rf"(?:[{ORBITAL_LETTERS}]|\\mathrm\{{[{ORBITAL_LETTERS}]\}})"

BRACED_COMMANDS = {
    "frac",
    "dfrac",
    "tfrac",
    "sqrt",
    "mathrm",
    "mathbf",
    "mathit",
    "mathsf",
    "mathtt",
    "mathcal",
    "mathbb",
    "mathfrak",
    "boldsymbol",
    "operatorname",
    "overline",
    "underline",
    "widehat",
    "widetilde",
    "bar",
    "hat",
    "tilde",
    "vec",
    "dot",
    "ddot",
    "begin",
    "end",
}

SPACED_COMMANDS = BRACED_COMMANDS | {
    "alpha",
    "beta",
    "gamma",
    "delta",
    "epsilon",
    "varepsilon",
    "zeta",
    "eta",
    "theta",
    "vartheta",
    "iota",
    "kappa",
    "lambda",
    "mu",
    "nu",
    "xi",
    "pi",
    "varpi",
    "rho",
    "varrho",
    "sigma",
    "varsigma",
    "tau",
    "upsilon",
    "phi",
    "varphi",
    "chi",
    "psi",
    "omega",
    "Gamma",
    "Delta",
    "Theta",
    "Lambda",
    "Xi",
    "Pi",
    "Sigma",
    "Upsilon",
    "Phi",
    "Psi",
    "Omega",
    "le",
    "leq",
    "ge",
    "geq",
    "neq",
    "approx",
    "sim",
    "simeq",
    "times",
    "cdot",
    "pm",
    "mp",
    "to",
    "rightarrow",
    "leftarrow",
    "leftrightarrow",
    "infty",
    "partial",
    "nabla",
    "ell",
    "hbar",
    "quad",
    "qquad",
    "vert",
    "Vert",
    "langle",
    "rangle",
    "lbrace",
    "rbrace",
}


def _is_escaped(text: str, index: int) -> bool:
    count = 0
    pos = index - 1
    while pos >= 0 and text[pos] == "\\":
        count += 1
        pos -= 1
    return count % 2 == 1


def _find_unescaped(text: str, needle: str, start: int) -> int:
    pos = start
    while True:
        pos = text.find(needle, pos)
        if pos == -1:
            return -1
        if not _is_escaped(text, pos):
            return pos
        pos += len(needle)


def _apply(pattern: str, repl: str, text: str, flags: int = 0) -> tuple[str, int]:
    updated, count = re.subn(pattern, repl, text, flags=flags)
    if updated == text:
        return text, 0
    return updated, count


def _repair_math_body_once(body: str) -> tuple[str, int]:
    replacements = 0
    repaired = body

    # OCR can insert a space after known control-word backslashes:
    # "\ alpha" -> "\alpha". Do not rewrite "\ J"; "\ " is a LaTeX space.
    spaced_commands = "|".join(sorted(SPACED_COMMANDS, key=len, reverse=True))
    repaired, count = _apply(rf"(?<!\\)\\\s+({spaced_commands})(?![A-Za-z])", r"\\\1", repaired)
    replacements += count

    # Keep command names attached to their braced argument.
    braced = "|".join(sorted(BRACED_COMMANDS))
    repaired, count = _apply(rf"\\({braced})\s+\{{", r"\\\1{", repaired)
    replacements += count

    # Subscripts/superscripts must not be separated from their argument.
    repaired, count = _apply(r"(?<=[A-Za-z0-9)\]\}])\s+([_^])", r"\1", repaired)
    replacements += count
    repaired, count = _apply(r"([_^])\s+\{", r"\1{", repaired)
    replacements += count
    repaired, count = _apply(r"([_^])\s+([A-Za-z0-9\\])", r"\1\2", repaired)
    replacements += count
    repaired, count = _apply(r"([_^])\{\s*([^{}\s]+)\s*\}", r"\1{\2}", repaired)
    replacements += count

    # Atomic configuration + term symbols need a left superscript on the term.
    # Obsidian/MathJax renders this reliably when a LaTeX space command anchors
    # the left superscript: "1 s ^ { 2 } ^ { 1 } S _ { 0 }"
    # becomes "1s^{2} \ ^{1}S_{0}". MinerU may emit orbital letters either
    # bare ("4f") or wrapped in \mathrm ("4\mathrm{f}").
    repaired, count = _apply(rf"\b([1-9]\d*)\s+([{ORBITAL_LETTERS}])(?=\s*[_^])", r"\1\2", repaired)
    replacements += count
    repaired, count = _apply(
        rf"\b([1-9]\d*)\s*({ORBITAL_TOKEN_PATTERN})(_\{{[^{{}}\s]+\}})?\^\{{([0-9]+)\}}\^\{{([0-9]+)\}}\s*([{TERM_SYMBOL_LETTERS}])",
        r"\1\2\3^{\4} \\ ^{\5}\6",
        repaired,
    )
    replacements += count
    repaired, count = _apply(
        rf"\\\s*\^\s*\{{\s*([0-9]+)\s*\}}\s*([{TERM_SYMBOL_LETTERS}])",
        r"\\ ^{\1}\2",
        repaired,
    )
    replacements += count

    # Delimiter commands are parsed more reliably without OCR-inserted gaps.
    repaired, count = _apply(
        r"\\(left|right)\s+((?:\\[{}])|[()\[\]{}|.])",
        r"\\\1\2",
        repaired,
    )
    replacements += count

    # Environments sometimes become "\begin {matrix}" in PDF OCR output.
    repaired, count = _apply(r"\\(begin|end)\s+\{", r"\\\1{", repaired)
    replacements += count

    # Adjacent braced arguments in math macros should stay adjacent:
    # "\frac{ a } { b }" -> "\frac{ a }{ b }".
    repaired, count = _apply(r"(?<=})[ \t]+(?=\{)", "", repaired)
    replacements += count
    repaired, count = _apply(
        r"\\(frac|dfrac|tfrac)\{\s*([^{}\n]*\S)\s*\}\{\s*([^{}\n]*\S)\s*\}",
        r"\\\1{\2}{\3}",
        repaired,
    )
    replacements += count

    # Remove padding inside non-text command arguments when the argument is a
    # simple token. Avoid \text{...}, where spaces may be intentional prose.
    for command in sorted(BRACED_COMMANDS - TEXT_LIKE_COMMANDS):
        repaired, count = _apply(
            rf"\\{command}\{{\s*([^{{}}\n]*\S)\s*\}}",
            rf"\\{command}" + r"{\1}",
            repaired,
        )
        replacements += count

    return repaired, replacements


def _repair_math_body(body: str) -> tuple[str, int]:
    total_replacements = 0
    repaired = body
    for _ in range(8):
        repaired, replacements = _repair_math_body_once(repaired)
        total_replacements += replacements
        if replacements == 0:
            break
    return repaired, total_replacements


def _repair_unprotected_segment(text: str) -> tuple[str, LatexRepairReport]:
    out: list[str] = []
    replacements = 0
    converted_delimiters = 0
    math_spans = 0
    i = 0

    while i < len(text):
        if text.startswith("$$", i) and not _is_escaped(text, i):
            end = _find_unescaped(text, "$$", i + 2)
            if end == -1:
                out.append(text[i:])
                break
            body, count = _repair_math_body(text[i + 2:end])
            out.append("$$" + body + "$$")
            replacements += count
            math_spans += 1
            i = end + 2
            continue

        if text.startswith(r"\[", i):
            end = text.find(r"\]", i + 2)
            if end == -1:
                out.append(text[i:])
                break
            body, count = _repair_math_body(text[i + 2:end])
            out.append("$$" + body + "$$")
            replacements += count
            converted_delimiters += 1
            math_spans += 1
            i = end + 2
            continue

        if text.startswith(r"\(", i):
            end = text.find(r"\)", i + 2)
            if end == -1:
                out.append(text[i:])
                break
            body, count = _repair_math_body(text[i + 2:end])
            out.append("$" + body + "$")
            replacements += count
            converted_delimiters += 1
            math_spans += 1
            i = end + 2
            continue

        if text[i] == "$" and not _is_escaped(text, i):
            if i + 1 < len(text) and text[i + 1] == "$":
                out.append(text[i])
                i += 1
                continue
            end = _find_unescaped(text, "$", i + 1)
            if end == -1:
                out.append(text[i])
                i += 1
                continue
            if end + 1 < len(text) and text[end + 1] == "$":
                out.append(text[i])
                i += 1
                continue
            body, count = _repair_math_body(text[i + 1:end])
            out.append("$" + body + "$")
            replacements += count
            math_spans += 1
            i = end + 1
            continue

        out.append(text[i])
        i += 1

    return "".join(out), LatexRepairReport(
        replacements=replacements,
        converted_delimiters=converted_delimiters,
        math_spans=math_spans,
    )


def _split_protected_markdown(text: str) -> list[tuple[str, bool]]:
    """Return (segment, protected) pairs for fenced and inline code."""
    segments: list[tuple[str, bool]] = []
    i = 0
    while i < len(text):
        fence = re.search(r"(?m)^[ \t]*(```+|~~~+)", text[i:])
        inline = text.find("`", i)
        candidates = []
        if fence:
            candidates.append((i + fence.start(), "fence", fence.group(1)))
        if inline != -1:
            candidates.append((inline, "inline", "`"))
        if not candidates:
            segments.append((text[i:], False))
            break

        start, kind, marker = min(candidates, key=lambda item: item[0])
        if start > i:
            segments.append((text[i:start], False))

        if kind == "fence":
            line_end = text.find("\n", start)
            if line_end == -1:
                segments.append((text[start:], True))
                break
            close_re = re.compile(rf"(?m)^[ \t]*{re.escape(marker)}[ \t]*$")
            close = close_re.search(text, line_end + 1)
            if not close:
                segments.append((text[start:], True))
                break
            end = close.end()
            if end < len(text) and text[end] == "\n":
                end += 1
            segments.append((text[start:end], True))
            i = end
            continue

        end = text.find("`", start + 1)
        if end == -1:
            segments.append((text[start:], False))
            break
        segments.append((text[start:end + 1], True))
        i = end + 1

    return segments


def repair_latex_math(text: str) -> tuple[str, LatexRepairReport]:
    """Repair LaTeX math in Markdown text and return the updated text/report."""
    out: list[str] = []
    total = LatexRepairReport(replacements=0, converted_delimiters=0, math_spans=0)

    for segment, protected in _split_protected_markdown(text):
        if protected:
            out.append(segment)
            continue
        repaired, report = _repair_unprotected_segment(segment)
        out.append(repaired)
        total = LatexRepairReport(
            replacements=total.replacements + report.replacements,
            converted_delimiters=total.converted_delimiters + report.converted_delimiters,
            math_spans=total.math_spans + report.math_spans,
        )

    return "".join(out), total


def _iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if p.is_file()))
        elif path.is_file():
            files.append(path)
    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair OCR-spaced LaTeX math in Markdown files.",
    )
    parser.add_argument("paths", nargs="+", help="Markdown files or directories. Supports configured-path aliases.")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files.")
    args = parser.parse_args()

    runtime_paths = load_paths()
    resolved_paths = [resolve_runtime_path(path, runtime_paths, role="path") for path in args.paths]
    for path in _iter_markdown_files([p for p in resolved_paths if p is not None]):
        original = path.read_text(encoding="utf-8", errors="ignore")
        repaired, report = repair_latex_math(original)
        if report.changed and not args.dry_run:
            path.write_text(repaired, encoding="utf-8")
        print(json.dumps({"path": str(path), **report.as_dict()}, ensure_ascii=False))


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

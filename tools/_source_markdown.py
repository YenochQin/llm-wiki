"""Small, shared readers for prepared Markdown; never rewrite source text."""

from __future__ import annotations

import re


SECTION_NAMES = (
    "abstract", "摘要", "keywords", "article info", "introduction", "background",
    "methods", "method", "materials and methods", "theory", "results",
    "results and discussion", "discussion", "conclusion", "conclusions",
    "summary", "references", "bibliography", "literature cited",
    "acknowledgments", "acknowledgements", "funding", "data availability",
    "appendix", "supplementary material", "supplementary information",
)
_COMPACT_NAMES = {re.sub(r"\s+", "", name): name for name in SECTION_NAMES}


def normalize_section_name(text: str) -> str:
    """Normalize known letter-spaced labels, without joining arbitrary words."""
    text = re.sub(r"\s+", " ", text).strip().rstrip(":：").lower()
    return _COMPACT_NAMES.get(text.replace(" ", ""), text)


def section_heading(line: str) -> str | None:
    """Recognize ATX, whole-line bold, and known plain section labels."""
    value = line.strip()
    atx = re.fullmatch(r"#{1,6}\s+(.+?)(?:\s+#+)?", value)
    bold = re.fullmatch(r"(?:\*\*(.+)\*\*|__(.+)__)", value)
    if atx:
        return normalize_section_name(atx.group(1).strip("*"))
    if bold:
        value = bold.group(1) or bold.group(2)
        # Author bylines are also bold in MinerU output.
        if re.match(r"\d+(?:\.\d+)*\.?\s+\S", value):
            return normalize_section_name(value)
    name = normalize_section_name(value)
    return name if name in SECTION_NAMES else None


def mask_noncontent(text: str) -> str:
    """Mask YAML, code, comments and link destinations, preserving offsets."""
    def blank(match: re.Match) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"\A\ufeff?---[^\S\n]*\n.*?\n(?:---|\.\.\.)[^\S\n]*(?:\n|$)",
                  blank, text, count=1, flags=re.S)
    lines = text.splitlines(keepends=True)
    fence = None
    for i, line in enumerate(lines):
        marker = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if fence is None and marker:
            fence = marker.group(1)
        elif fence and re.fullmatch(r"[ \t]{0,3}" + re.escape(fence[0]) +
                                   "{" + str(len(fence)) + r",}[ \t]*\n?", line):
            lines[i] = re.sub(r"[^\n]", " ", line)
            fence = None
            continue
        if fence:
            lines[i] = re.sub(r"[^\n]", " ", line)
    text = "".join(lines)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    text = re.sub(r"(`+)([^`\n]*?)\1", blank, text)
    # Keep visible link labels, but don't flag URL query syntax as missing text.
    text = re.sub(r"(?<=\]\()[^\n)]*(?=\))", blank, text)
    return re.sub(r"https?://[^\s<>]+", blank, text)


def abstract_text(body: str) -> str | None:
    """Return an explicit abstract, or None; no guessing from cover text."""
    lines = body.splitlines(keepends=True)
    visible = mask_noncontent(body).splitlines(keepends=True)
    start = None
    for i, line in enumerate(visible):
        heading = section_heading(line)
        if heading in {"abstract", "摘要"}:
            start = i + 1
        elif start is not None and heading is not None:
            return "".join(lines[start:i]).strip()
    return "".join(lines[start:]).strip() if start is not None else None

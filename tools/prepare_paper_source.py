#!/usr/bin/env python3
"""Prepare one local paper source for `/ingest`.

Drop-in replacement for OmegaWiki's tex-fetching prep step. This version routes
every local PDF through the MinerU pipeline (lifted from `pdf-source-scripts/`)
and emits a structured markdown file that `/ingest` consumes directly.

Pipeline:

    PDF
      -> _mineru.extract(...)                    # cache by sha16(PDF)
      -> _normalize_cache(...)                   # synthesize Zotero-style manifest
      -> _convert_to_markdown(...)               # adapter: cleans cover/headings/figures
      -> repair_latex_math(...)                  # conservative math delimiter/spacing fixes
      -> wiki/sources/papers/<source-slug>.md         # canonical_ingest_path
      -> wiki/sources/papers/assets/<source-slug>/*.jpg  # extracted figure crops

Cache layout (kept across runs for cheap re-prep):

    <explicit-cache-root>/<sha16>/
        <stem>.md               raw MinerU markdown
        <stem>.json             MinerU content_list block list
        full.md                 adapter-canonical copy of <stem>.md
        manifest.json           synthesized from the block list
        images/                 figure/table crops referenced by the .md

CLI (preserves OmegaWiki's contract — `/ingest` invocations are unchanged):

    python3 tools/prepare_paper_source.py \\
        --raw-root raw \\
        --output-dir wiki/sources/papers \\
        --cache-root .checkpoints/mineru-cache \\
        --source raw/papers/example.pdf \\
        [--title "Recovered Paper Title"]

stdout: a single JSON object (one line) with the manifest shape `/ingest`
expects. `canonical_ingest_path` is the file `/ingest` should read; for this
build it is always a `.md` produced by MinerU + adapter (`ingest_format = "mineru-md"`).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
from _cli_io import configure_utf8_stdio
import _mineru
from _paths import DEFAULT_CONFIG_PATH, display_path, load_paths, resolve_runtime_path
from repair_latex_math import repair_latex_math

PREPARED_SUBDIR = "prepared"
LEGACY_PREPARED_SUBDIR = "tmp"

# ---------------------------------------------------------------------------
# Adapter constants (lifted verbatim from pdf-source-scripts/pdf_to_source_mineru.py)
# ---------------------------------------------------------------------------

REFERENCE_HEADING_PATTERNS = [
    r"^\s*(?:literature\s*cited|references?|bibliography)\s*$",
]

SKIP_SECTION_PATTERNS = [
    r"^\s*acknowledg(?:e?ments?)\s*$",
    r"^\s*disclosure\s*statement\s*$",
    r"^\s*supplementary\s*(?:material|information)\s*$",
    r"^\s*supporting\s*information\s*$",
    r"^\s*appendix(?:\s+\w+)?\s*$",
    r"^\s*funding\s*$",
    r"^\s*author\s*contributions?\s*$",
    r"^\s*competing\s*interests?\s*$",
    r"^\s*data\s*availability\s*$",
    r"^\s*additional\s*information\s*$",
]

JUNK_PATTERNS = [
    r"^\s*www\..*$",
    r"^\s*https?://.*$",
    r"^\s*downloaded\s+from.*$",
    r"^\s*ANWENS\s*CONNECT\s*$",
    r"^\s*contents\s*$",
    r"^\s*table\s*of\s*contents\s*$",
]

JOURNAL_NAME_HINTS = (
    "annual review",
    "journal of",
    "proceedings of",
    "nature ",
    "science ",
    "physical review",
    "monthly notices",
    "astrophysical journal",
    "astronomy and astrophysics",
)

KEEP_UNNUMBERED = {
    "abstract", "keywords", "summary", "introduction",
    "background", "main", "methods", "method", "materials and methods",
    "results", "results and discussion", "discussion",
    "conclusion", "conclusions", "highlights",
    "references", "reference", "bibliography", "literature cited",
}

_ROMAN_RE = r"(?:M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))"
NUMBERED_HEADING_RE = re.compile(r"^\s*((?:\d+(?:\.\d+)*)|(?:" + _ROMAN_RE + r"))\.?\s+[A-Za-z]")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(images/([^)]+)\)")
FIGURE_LABEL_RE = re.compile(r"\b(Figure|Fig\.?|Table)\s*\d+\b", re.IGNORECASE)
AUTHOR_INITIAL_RE = re.compile(r"\b[A-Z]\.\s*[A-Z]")
BIBTEX_SECTION_RE = re.compile(
    r"\n*## BibTeX\s*\n+```bibtex\n.*?\n```\s*",
    re.DOTALL,
)
BIBTEX_ENTRY_RE = re.compile(r"@\s*[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
BIBTEX_FIELD_RE = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*=\s*[{'\"](?P<value>.*?)[}'\"]\s*,?\s*$",
    re.MULTILINE,
)
TITLE_STOP_WORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "using", "via", "with",
}


# ---------------------------------------------------------------------------
# YAML rendering for the markdown frontmatter
# ---------------------------------------------------------------------------

def _yaml_scalar(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_block_scalar(key: str, value: str) -> list[str]:
    lines = [f"{key}: |"]
    text = value.rstrip("\n")
    if not text:
        lines.append("  ")
        return lines
    for line in text.splitlines():
        lines.append(f"  {line}")
    return lines


def _render_yaml(items: dict) -> str:
    lines = ["---"]
    for key, value in items.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key}: {value}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            elif all(isinstance(x, str) for x in value):
                lines.append(f"{key}:")
                for x in value:
                    lines.append(f"  - {_yaml_scalar(x)}")
            else:
                lines.append(f"{key}:")
                for x in value:
                    first = True
                    for k2, v2 in x.items():
                        prefix = "  - " if first else "    "
                        first = False
                        if isinstance(v2, int):
                            lines.append(f"{prefix}{k2}: {v2}")
                        else:
                            lines.append(f"{prefix}{k2}: {_yaml_scalar(str(v2))}")
        else:
            if "\n" in str(value):
                lines.extend(_yaml_block_scalar(str(key), str(value)))
            else:
                lines.append(f"{key}: {_yaml_scalar(str(value))}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Heading classifiers
# ---------------------------------------------------------------------------

def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.match(p, text, re.IGNORECASE) for p in patterns)


def _heading_is_cutoff(text: str) -> bool:
    return _matches_any(text.strip(), SKIP_SECTION_PATTERNS)


def _heading_is_reference(text: str) -> bool:
    return _matches_any(text.strip(), REFERENCE_HEADING_PATTERNS)


def _heading_is_junk(text: str) -> bool:
    h = text.strip()
    if _matches_any(h, JUNK_PATTERNS):
        return True
    if h.endswith(":") and not NUMBERED_HEADING_RE.match(h):
        return True
    return False


def _is_journal_name(text: str) -> bool:
    h = text.strip().lower()
    return any(h.startswith(prefix) for prefix in JOURNAL_NAME_HINTS)


def _is_numbered(text: str) -> bool:
    return bool(NUMBERED_HEADING_RE.match(text.strip()))


def _heading_depth(text: str) -> int:
    m = NUMBERED_HEADING_RE.match(text.strip())
    if not m:
        return 1
    return m.group(1).count(".") + 1


def _is_allowed_unnumbered(text: str) -> bool:
    return text.strip().lower().rstrip(":") in KEEP_UNNUMBERED


def _looks_like_author(text: str) -> bool:
    return bool(AUTHOR_INITIAL_RE.search(text))


def _looks_like_furniture(text: str) -> bool:
    words = [w for w in text.split() if any(c.isalpha() for c in w)]
    if not words or len(words) > 4:
        return False
    return all(w == w.upper() for w in words)


def _is_real_heading(text: str) -> bool:
    return bool(
        NUMBERED_HEADING_RE.match(text)
        or _is_allowed_unnumbered(text)
        or _heading_is_junk(text)
        or _heading_is_cutoff(text)
    )


def _normalize_heading_text(heading: str) -> str:
    return re.sub(r"^(\d+(?:\.\d+)*\.)([A-Za-z])", r"\1 \2", heading.strip())


def _plain_title_key(text: str) -> str:
    text = re.sub(r"\\circ\b", " o ", text)
    text = re.sub(r"\\[A-Za-z]+\s*(?:\{([^{}]*)\})?", r" \1 ", text)
    text = re.sub(r"[$^_{}\\]", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _same_title_heading(heading: str, title: str) -> bool:
    if not heading or not title:
        return False
    heading_key = _plain_title_key(heading)
    title_key = _plain_title_key(title)
    if not heading_key or not title_key:
        return False
    return heading_key == title_key


def _cover_title_heading_matches(heading: str, title: str) -> bool:
    if _same_title_heading(heading, title):
        return True
    if not heading or not title or _is_numbered(heading):
        return False
    heading_key = _plain_title_key(heading)
    title_key = _plain_title_key(title)
    if not heading_key or not title_key:
        return False
    # Fuzzy fallback only while still parsing cover/title material. MinerU can
    # prepend labels like "PAPER" or "OPEN ACCESS", or truncate a long title.
    if len(heading_key) >= 20 and len(title_key) >= 20:
        ratio = difflib.SequenceMatcher(None, heading_key, title_key).ratio()
        if ratio >= 0.88:
            return True
    prefix_len = 0
    for a, b in zip(heading_key, title_key):
        if a != b:
            break
        prefix_len += 1
    if prefix_len >= 60:
        return True
    return False


# ---------------------------------------------------------------------------
# Manifest synthesis (from MinerU content_list block list)
# ---------------------------------------------------------------------------

def _normalize_cover_blocks(blocks: list[dict]) -> list[dict]:
    out: list[dict] = []
    i = 0
    n = len(blocks)
    title_emitted = False

    while i < n:
        b = blocks[i]
        is_cover_l1 = b.get("text_level") == 1 and (b.get("page_idx") or 0) == 0
        if not is_cover_l1:
            out.append(b)
            i += 1
            continue

        text = (b.get("text") or "").strip()

        if _is_journal_name(text):
            out.append(b)
            i += 1
            continue

        if _is_real_heading(text):
            out.append(b)
            i += 1
            continue

        if not title_emitted:
            fragments = [text]
            j = i + 1
            while j < n:
                bj = blocks[j]
                if not (bj.get("text_level") == 1 and (bj.get("page_idx") or 0) == 0):
                    break
                tj = (bj.get("text") or "").strip()
                if (_is_journal_name(tj)
                        or _is_real_heading(tj)
                        or _looks_like_author(tj)
                        or _looks_like_furniture(tj)):
                    break
                fragments.append(tj)
                j += 1
            merged = dict(b)
            merged["text"] = " ".join(fragments)
            out.append(merged)
            title_emitted = True
            i = j
            continue

        i += 1

    return out


def _synthesize_manifest(md_path: Path, json_path: Path) -> dict:
    raw_blocks = json.loads(json_path.read_text(encoding="utf-8"))
    full_md = md_path.read_text(encoding="utf-8")
    blocks = _normalize_cover_blocks(raw_blocks)

    total_pages = (max((b.get("page_idx", 0) or 0) for b in blocks) + 1) if blocks else 0

    sections: list[dict] = []
    all_figures: list[dict] = []
    cur_section_heading = ""

    auto_fig_n = 0
    for block in blocks:
        if block.get("text_level") == 1:
            heading = (block.get("text") or "").strip()
            if not heading:
                continue
            cur_section_heading = heading
            sections.append({
                "heading": heading,
                "page": int(block.get("page_idx", 0) or 0),
                "figures": [],
                "tables": [],
            })
        elif block.get("type") == "image":
            img_path = block.get("img_path") or ""
            if not img_path:
                continue
            cap_list = block.get("img_caption") or block.get("image_caption") or []
            caption = " ".join(cap_list).strip() if isinstance(cap_list, list) else str(cap_list)
            m = FIGURE_LABEL_RE.search(caption)
            if m:
                label = m.group(0)
            else:
                auto_fig_n += 1
                label = f"Image {auto_fig_n}"
            page = int(block.get("page_idx", 0) or 0)
            entry = {
                "label": label,
                "path": img_path,
                "caption": caption,
                "page": page,
                "section": cur_section_heading,
            }
            all_figures.append(entry)
            if sections:
                sections[-1]["figures"].append({
                    "label": label,
                    "path": img_path,
                    "caption": caption,
                    "page": page,
                })

    return {
        "sections": sections,
        "allFigures": all_figures,
        "allTables": [],
        "totalPages": total_pages,
        "totalChars": len(full_md),
    }


def _normalize_cache(cache_dir: Path, md_path: Path, json_path: Path) -> None:
    full_md = cache_dir / "full.md"
    manifest = cache_dir / "manifest.json"

    if not full_md.exists() or full_md.stat().st_mtime < md_path.stat().st_mtime:
        full_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    if not manifest.exists() or manifest.stat().st_mtime < json_path.stat().st_mtime:
        data = _synthesize_manifest(md_path, json_path)
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=None), encoding="utf-8")


# ---------------------------------------------------------------------------
# Markdown adapter: full.md + manifest -> structured wiki source
# ---------------------------------------------------------------------------

def _detect_title(manifest: dict) -> str:
    for sec in manifest.get("sections", [])[:8]:
        h = (sec.get("heading", "") or "").strip()
        if not h:
            continue
        if _heading_is_junk(h) or _heading_is_cutoff(h) or _is_journal_name(h):
            continue
        if h.lower() in KEEP_UNNUMBERED:
            continue
        if _is_numbered(h):
            continue
        if len(h.split()) < 2:
            continue
        return h
    return ""


def _transform_markdown(
    full_md: str,
    slug: str,
    detected_title: str,
) -> tuple[str, list[str], list[str], dict[str, int | bool]]:
    out: list[str] = []
    dropped: list[str] = []
    skipped_sections: list[str] = []
    skip_body = False
    title_norm = detected_title.strip().lower()
    image_root = f"assets/{slug}"
    in_cover = True
    title_emitted = False

    for raw in full_md.splitlines():
        if raw.lstrip().startswith("#"):
            heading_text = _normalize_heading_text(raw.lstrip("#").strip())

            if _heading_is_cutoff(heading_text):
                skipped_sections.append(heading_text)
                dropped.append(heading_text)
                skip_body = True
                continue

            if _heading_is_junk(heading_text) or _is_journal_name(heading_text):
                dropped.append(heading_text)
                skip_body = True
                continue

            # Title heading in papers without explicit section headings (e.g. PRL)
            if in_cover and title_norm and _cover_title_heading_matches(heading_text, detected_title):
                in_cover = False
                if not title_emitted:
                    out.append(f"# {heading_text}")
                    out.append("")
                    title_emitted = True
                skip_body = False
                continue

            is_content = _is_numbered(heading_text) or _is_allowed_unnumbered(heading_text)

            if in_cover and not is_content:
                skip_body = True
                continue

            if in_cover and is_content:
                in_cover = False
                if detected_title and not title_emitted:
                    out.append(f"# {detected_title}")
                    out.append("")
                    title_emitted = True

            if title_norm and _same_title_heading(heading_text, detected_title):
                if not title_emitted:
                    out.append(f"# {heading_text}")
                    title_emitted = True
                skip_body = True
                continue

            if not _is_numbered(heading_text) and not _is_allowed_unnumbered(heading_text):
                out.append("")
                out.append(f"**{heading_text}**")
                out.append("")
                skip_body = False
                continue

            depth = max(1, min(_heading_depth(heading_text), 4))
            out.append(f"{'#' * depth} {heading_text}")
            skip_body = False
            continue

        if in_cover or skip_body:
            continue

        rewritten = IMG_RE.sub(
            lambda m: f"![{m.group(1)}]({image_root}/{m.group(2)})",
            raw,
        )
        out.append(rewritten)

    body = "\n".join(out).strip() + "\n"
    body = re.sub(r"\n{3,}", "\n\n", body)
    body, latex_report = repair_latex_math(body)
    return body, dropped, skipped_sections, latex_report.as_dict()


def _collect_used_images(body: str, slug: str) -> set[str]:
    rx = re.compile(rf"!\[[^\]]*\]\(assets/{re.escape(slug)}/([^)]+)\)")
    return set(rx.findall(body))


def _build_section_index(manifest: dict) -> list[dict]:
    out: list[dict] = []
    for sec in manifest.get("sections", []) or []:
        h = (sec.get("heading", "") or "").strip()
        if not h or _heading_is_junk(h) or _heading_is_cutoff(h) or _is_journal_name(h):
            continue
        out.append({
            "heading": _normalize_heading_text(h),
            "page": int(sec.get("page", 0) or 0),
            "figures": len(sec.get("figures", []) or []),
        })
    return out


def _build_figures_index(manifest: dict, used_images: set[str], slug: str) -> list[dict]:
    figures: list[dict] = []
    for fig in manifest.get("allFigures", []) or []:
        path = fig.get("path", "") or ""
        name = path.rsplit("/", 1)[-1] if path else ""
        if not name or name not in used_images:
            continue
        caption = re.sub(r"\s+", " ", (fig.get("caption", "") or "").strip())
        figures.append({
            "label": fig.get("label", ""),
            "page": int(fig.get("page", 0) or 0),
            "section": fig.get("section", ""),
            "path": f"assets/{slug}/{name}",
            "caption": caption[:500],
        })
    return figures


def _build_abstract_excerpt(body: str, limit: int = 800) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
    text = re.sub(r"^#.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _same_source(existing_source: str, pdf: Path) -> bool:
    if not existing_source:
        return False
    existing = Path(existing_source).expanduser()
    current = pdf.expanduser()
    try:
        return existing.resolve() == current.resolve()
    except OSError:
        return str(existing) == str(current)


def _read_existing_frontmatter(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        metadata = frontmatter.loads(text).metadata
        return {str(k): str(v) for k, v in metadata.items()}
    except Exception:
        pass
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields


def _strip_frontmatter(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*", "", text, count=1, flags=re.DOTALL)


def _format_bibtex_section(bibtex: str) -> str:
    bibtex = bibtex.rstrip("\n")
    if not bibtex:
        return ""
    return f"\n\n## BibTeX\n\n```bibtex\n{bibtex}\n```\n"


def _upsert_bibtex_body(text: str, bibtex: str = "") -> str:
    """Move BibTeX out of frontmatter and into a body fenced code block."""
    try:
        post = frontmatter.loads(text)
    except Exception:
        body_bibtex = bibtex.strip()
        return text if not body_bibtex else BIBTEX_SECTION_RE.sub("", text).rstrip() + _format_bibtex_section(body_bibtex)

    metadata = dict(post.metadata)
    fm_bibtex = str(metadata.pop("bibtex", "") or "").strip()
    body_bibtex = bibtex.strip() or fm_bibtex
    body = BIBTEX_SECTION_RE.sub("", post.content).rstrip()
    if body_bibtex:
        body += _format_bibtex_section(body_bibtex)
    return frontmatter.dumps(frontmatter.Post(body, **metadata)).rstrip() + "\n"


def _repair_prepared_text(text: str) -> tuple[str, dict[str, int | bool]]:
    """Repair math in an existing prepared markdown document."""
    try:
        post = frontmatter.loads(text)
    except Exception:
        repaired, report = repair_latex_math(text)
        return repaired, report.as_dict()

    repaired_body, report = repair_latex_math(post.content)
    if not report.changed:
        return text, report.as_dict()
    metadata = dict(post.metadata)
    metadata["latexRepairReplacements"] = int(report.replacements)
    metadata["latexRepairConvertedDelimiters"] = int(report.converted_delimiters)
    metadata["latexRepairMathSpans"] = int(report.math_spans)
    return frontmatter.dumps(frontmatter.Post(repaired_body, **metadata)).rstrip() + "\n", report.as_dict()


def _latex_warning(report: dict[str, int | bool]) -> str:
    return (
        "latex math repaired: "
        f"{report.get('replacements', 0)} spacing replacements, "
        f"{report.get('converted_delimiters', 0)} delimiter conversions"
    )


def _safe_source_slug_part(value: str, *, separator: str = "-") -> str:
    """Return a filesystem-safe source slug component."""
    text = unicodedata.normalize("NFKD", value.strip().lower()).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = text.replace("$", " ")
    text = re.sub(r"[{}\\^]", " ", text)
    text = re.sub(r"[^a-z0-9]+", separator, text)
    text = re.sub(rf"{re.escape(separator)}+", separator, text)
    return text.strip(separator)


def _safe_citation_key(value: str) -> str:
    """Normalize a Zotero/Better BibTeX citation key for use as a file stem."""
    text = unicodedata.normalize("NFKD", value.strip()).encode("ascii", "ignore").decode("ascii")
    if not text:
        return ""
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    text = text.replace("$", "")
    text = re.sub(r"[{}\\^]", "", text)
    text = re.sub(r"[^A-Za-z0-9_.+-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-._")
    return text


def _bibtex_entry_key(bibtex: str) -> str:
    match = BIBTEX_ENTRY_RE.search(bibtex or "")
    return _safe_citation_key(match.group(1)) if match else ""


def _bibtex_field(bibtex: str, field_name: str) -> str:
    for match in BIBTEX_FIELD_RE.finditer(bibtex or ""):
        if match.group(1).lower() == field_name.lower():
            return " ".join(match.group("value").split())
    return ""


def _first_author_from_bibtex(bibtex: str) -> str:
    authors = _bibtex_field(bibtex, "author")
    if not authors:
        return ""
    return authors.split(" and ", 1)[0].strip()


def _author_token(authors: str, bibtex: str) -> str:
    first_author = (authors or "").split(",", 1)[0].strip() or _first_author_from_bibtex(bibtex)
    if not first_author:
        return "unknown"
    if "," in first_author:
        surname = first_author.split(",", 1)[0]
    else:
        parts = first_author.split()
        surname = parts[-1] if parts else first_author
    return _safe_source_slug_part(surname, separator="-") or "unknown"


def _year_token(year: str, bibtex: str) -> str:
    match = re.search(r"\d{4}", str(year or "")) or re.search(r"\d{4}", _bibtex_field(bibtex, "year"))
    return match.group(0) if match else "nodate"


def _very_short_title(title: str, bibtex: str, max_words: int = 3) -> str:
    title_text = title.strip() or _bibtex_field(bibtex, "title")
    title_text = unicodedata.normalize("NFKD", title_text).encode("ascii", "ignore").decode("ascii")
    tokens = [
        token
        for token in re.split(r"[^A-Za-z0-9]+", re.sub(r"\\[a-zA-Z]+\*?", " ", title_text).lower())
        if len(token) >= 2 and token not in TITLE_STOP_WORDS
    ]
    return "-".join(tokens[:max_words]) or "untitled"


def _source_slug(
    *,
    title: str,
    citation_key: str = "",
    authors: str = "",
    year: str = "",
    bibtex: str = "",
) -> str:
    """Prepared-source file stem: citationKey first, then author_year_veryshorttitle."""
    key = _safe_citation_key(citation_key) or _bibtex_entry_key(bibtex)
    if key:
        return key
    author = _author_token(authors, bibtex)
    year_part = _year_token(year, bibtex)
    short_title = _very_short_title(title, bibtex)
    return f"{author}_{year_part}_{short_title}"


# ---------------------------------------------------------------------------
# Top-level pipeline
# ---------------------------------------------------------------------------

def _sha16_of_file(path: Path, max_bytes: int = 4 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(max_bytes))
    return h.hexdigest()[:16]


def _project_root(raw_root: Path) -> Path:
    return raw_root.resolve().parent


def _source_output_dir(
    raw_root: Path,
    wiki_root: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    if output_dir is not None:
        return output_dir.resolve()
    if wiki_root is not None:
        return wiki_root.resolve() / "sources" / "papers"
    raise ValueError("prepare_paper_source requires an explicit output_dir")


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
            "--output-dir resolved inside the code repository's wiki/ directory, "
            "but config/paths.json points at an external wiki root. "
            "Pass @configured-sources-papers or the external wiki/sources/papers path."
        )


def prepare(
    pdf: Path,
    raw_root: Path,
    title_override: str = "",
    bibtex_override: str = "",
    citation_key: str = "",
    authors: str = "",
    year: str = "",
    cache_root: Path | None = None,
    language: str = "en",
    backend: str = "api",
    overwrite: bool = False,
    wiki_root: Path | None = None,
    output_dir: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    """Run MinerU on a PDF and write a structured markdown source to wiki/sources/papers/.

    Returns the manifest `/ingest` consumes.
    """
    warnings: list[str] = []
    output_dir = _source_output_dir(raw_root, wiki_root=wiki_root, output_dir=output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    display_root = project_root or _project_root(raw_root)

    if not pdf.exists():
        return {
            "canonical_ingest_path": display_path(pdf, display_root),
            "prepared_path": None,
            "ingest_format": "pdf",
            "title": title_override,
            "abstract_excerpt": "",
            "warnings": [f"PDF not found: {pdf}"],
            "usable": False,
        }

    if cache_root is None:
        raise ValueError("prepare_paper_source requires an explicit cache_root")
    cache_root = cache_root.resolve()
    cache_dir = cache_root / _sha16_of_file(pdf)

    try:
        md_path, json_path = _mineru.extract(pdf, cache_dir, language, backend)
    except Exception as exc:
        return {
            "canonical_ingest_path": display_path(pdf, display_root),
            "prepared_path": None,
            "ingest_format": "pdf",
            "title": title_override,
            "abstract_excerpt": "",
            "warnings": [f"mineru extraction failed: {exc}"],
            "usable": False,
        }

    _normalize_cache(cache_dir, md_path, json_path)

    full_md = (cache_dir / "full.md").read_text(encoding="utf-8")
    manifest = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))

    title = (
        title_override.strip()
        or _detect_title(manifest)
        or pdf.stem.replace("-", " ").replace("_", " ")
        or "Untitled"
    )
    slug = _source_slug(
        title=title,
        citation_key=citation_key,
        authors=authors,
        year=year,
        bibtex=bibtex_override,
    )
    out_path = output_dir / f"{slug}.md"
    if out_path.exists() and not overwrite:
        existing_front = _read_existing_frontmatter(out_path)
        existing_source = existing_front.get("source", "")
        existing_text = out_path.read_text(encoding="utf-8", errors="ignore")
        if _same_source(existing_source, pdf):
            migrated_text = _upsert_bibtex_body(existing_text, bibtex_override)
            if migrated_text != existing_text:
                existing_text = migrated_text
                out_path.write_text(existing_text, encoding="utf-8")
            repaired_text, latex_report = _repair_prepared_text(existing_text)
            latex_warnings = []
            if latex_report.get("changed"):
                existing_text = repaired_text
                out_path.write_text(existing_text, encoding="utf-8")
                latex_warnings.append(_latex_warning(latex_report))
            return {
                "canonical_ingest_path": display_path(out_path, display_root),
                "prepared_path": display_path(out_path, display_root),
                "ingest_format": "mineru-md",
                "title": existing_front.get("title") or title,
                "abstract_excerpt": _build_abstract_excerpt(_strip_frontmatter(existing_text)),
                "warnings": [f"prepared source already exists; reusing: {out_path}"] + latex_warnings,
                "usable": True,
            }
        return {
            "canonical_ingest_path": display_path(out_path, display_root),
            "prepared_path": display_path(out_path, display_root),
            "ingest_format": "mineru-md",
            "title": title,
            "abstract_excerpt": _build_abstract_excerpt(_strip_frontmatter(existing_text)),
            "warnings": [
                f"prepared source collision: another source already uses this title/slug: {display_path(out_path, display_root)}",
                "Rerun with --overwrite only after confirming replacement with the user.",
            ],
            "usable": False,
        }

    body, dropped, skipped_sections, latex_report = _transform_markdown(full_md, slug, title)
    if latex_report.get("changed"):
        warnings.append(_latex_warning(latex_report))

    if not body.strip():
        return {
            "canonical_ingest_path": display_path(output_dir / f"{slug}.md", display_root),
            "prepared_path": None,
            "ingest_format": "mineru-md",
            "title": title,
            "abstract_excerpt": "",
            "warnings": ["MinerU produced an empty body after filtering"],
            "usable": False,
        }

    used_images = _collect_used_images(body, slug)
    if used_images:
        images_dir = cache_dir / "images"
        if images_dir.exists():
            assets_dir = output_dir / "assets" / slug
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in used_images:
                src = images_dir / name
                if src.exists():
                    shutil.copy2(src, assets_dir / name)

    front: dict = {
        "title": title,
        "source": _portable_pdf_source(pdf),
        "sourceSlug": slug,
        "ingestedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceType": "pdf",
        "pipeline": "mineru",
        "totalPages": int(manifest.get("totalPages", 0) or 0),
        "totalChars": int(manifest.get("totalChars", 0) or 0),
    }
    key = _safe_citation_key(citation_key) or _bibtex_entry_key(bibtex_override)
    if key:
        front["citationKey"] = key
        front["paperSlug"] = key
    if latex_report.get("changed"):
        front["latexRepairReplacements"] = int(latex_report.get("replacements", 0) or 0)
        front["latexRepairConvertedDelimiters"] = int(latex_report.get("converted_delimiters", 0) or 0)
        front["latexRepairMathSpans"] = int(latex_report.get("math_spans", 0) or 0)
    if skipped_sections:
        front["skippedSectionHeadings"] = skipped_sections
    if dropped:
        front["droppedHeadings"] = dropped
    sections = _build_section_index(manifest)
    if sections:
        front["sections"] = sections
    figures = _build_figures_index(manifest, used_images, slug)
    if figures:
        front["figures"] = figures

    document = _render_yaml(front) + "\n\n" + body.rstrip() + _format_bibtex_section(bibtex_override)
    out_path.write_text(document, encoding="utf-8")

    print(
        f"prepare_paper_source: wrote {out_path} "
        f"(sections={len(sections)}, figures={len(figures)}, "
        f"droppedHeadings={len(dropped)}, skippedSections={len(skipped_sections)})",
        file=sys.stderr,
    )

    return {
        "canonical_ingest_path": display_path(out_path, display_root),
        "prepared_path": display_path(out_path, display_root),
        "ingest_format": "mineru-md",
        "title": title,
        "abstract_excerpt": _build_abstract_excerpt(body),
        "warnings": warnings,
        "usable": True,
    }


def prepare_paper_source(
    path: Path,
    raw_root: Path,
    title: str = "",
    bibtex: str = "",
    citation_key: str = "",
    authors: str = "",
    year: str = "",
    overwrite: bool = False,
    wiki_root: Path | None = None,
    output_dir: Path | None = None,
    cache_root: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    """Compatibility wrapper used by init_discovery.py."""
    result = prepare(
        pdf=path,
        raw_root=raw_root,
        title_override=title,
        bibtex_override=bibtex,
        citation_key=citation_key,
        authors=authors,
        year=year,
        cache_root=cache_root,
        overwrite=overwrite,
        wiki_root=wiki_root,
        output_dir=output_dir,
        project_root=project_root,
    )
    result.setdefault("candidate_id", _local_candidate_id(path, raw_root))
    result.setdefault("source_kind", "paper")
    result.setdefault("source_path", _project_relative(path, raw_root, project_root=project_root))
    result.setdefault("resolved_source_path", _project_relative(path, raw_root, project_root=project_root))
    result.setdefault("canonical_read_path", result.get("canonical_ingest_path", ""))
    result.setdefault("original_format", path.suffix.lower().lstrip(".") or "file")
    return result


def _local_candidate_id(path: Path, raw_root: Path) -> str:
    try:
        rel = path.resolve().relative_to(raw_root.resolve())
    except ValueError:
        rel = path
    slug = re.sub(r"[^a-z0-9]+", "-", str(rel).lower()).strip("-")
    return f"local:{slug or path.stem.lower()}"


def _project_relative(path: Path, raw_root: Path, project_root: Path | None = None) -> str:
    if project_root is not None:
        return display_path(path, project_root)
    try:
        return str(path.resolve().relative_to(raw_root.resolve().parent))
    except ValueError:
        return str(path)


def _portable_pdf_source(path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    marker = "/storage/"
    if marker in normalized:
        rest = normalized.split(marker, 1)[1]
        return f"${{Zotero data directory}}/storage/{rest}"
    return str(path)


def _resolve_source_path(source: Path, raw_root: Path, project_root: Path) -> Path:
    if source.is_absolute():
        resolved = source.resolve()
        if resolved.exists():
            return resolved
        parent = resolved.parent
        if parent.name and parent.parent.name == "storage" and parent.exists():
            pdfs = sorted(parent.glob("*.pdf"))
            if len(pdfs) == 1:
                return pdfs[0].resolve()
        return resolved
    candidates = [(project_root / source).resolve(), (raw_root / source).resolve()]
    parts = source.parts
    if parts and parts[0] == "raw":
        candidates.append((raw_root / Path(*parts[1:])).resolve())
    candidates.append((raw_root / "papers" / source.name).resolve())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a local PDF for /ingest via the MinerU pipeline.",
    )
    parser.add_argument("--raw-root", default=None,
                        help="Raw source root used for source resolution. Accepts @raw-root. Defaults to config/paths.json or ./raw.")
    parser.add_argument("--wiki-root", default=None,
                        help="Optional wiki vault root for path display/config resolution. Accepts @wiki-root; does not replace --output-dir.")
    parser.add_argument("--output-dir", required=True,
                        help="Explicit directory for prepared paper markdown output, e.g. @configured-sources-papers.")
    parser.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path,
                        help="Path config JSON (default: config/paths.json).")
    parser.add_argument("--source", required=True, type=Path,
                        help="Path to a local PDF to prepare.")
    parser.add_argument("--title", default="",
                        help="Confident agent-recovered title. Used verbatim when set.")
    parser.add_argument("--bibtex", default="",
                        help="Derived Zotero BibTeX string to persist in the prepared source body under ## BibTeX.")
    parser.add_argument("--citation-key", default="",
                        help="Preferred Zotero/Better BibTeX citation key for the prepared source filename.")
    parser.add_argument("--authors", default="",
                        help="Author string used for fallback source filename author_year_veryshorttitle.")
    parser.add_argument("--year", default="",
                        help="Publication year used for fallback source filename author_year_veryshorttitle.")
    parser.add_argument("--cache-root", required=True,
                        help="Explicit MinerU cache root for OCR intermediate outputs. Accepts @mineru-cache.")
    parser.add_argument("--language", default="en", help="Document language for MinerU.")
    parser.add_argument("--backend", default="api", choices=("api", "local"),
                        help="MinerU backend: 'api' (cloud) or 'local' (mineru[all]).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace an existing wiki/sources/papers/<source-slug>.md after user confirmation.")
    raw_args = sys.argv[1:]
    if any(arg == "--item-key" or arg.startswith("--item-key=") for arg in raw_args):
        parser.error(
            "prepare_paper_source.py does not accept --item-key. "
            "Use tools/fetch_zotero_metadata.py --item-key only for metadata, "
            "and pass the selected PDF path to this tool with --source."
        )
    args = parser.parse_args()

    base_paths = load_paths(config_path=args.paths_config)
    raw_root = resolve_runtime_path(args.raw_root, base_paths, role="--raw-root") if args.raw_root else base_paths.raw_root
    wiki_root = resolve_runtime_path(args.wiki_root, base_paths, role="--wiki-root") if args.wiki_root else base_paths.wiki_root
    paths = load_paths(config_path=args.paths_config, wiki_root=wiki_root, raw_root=raw_root)
    output_dir = resolve_runtime_path(args.output_dir, paths, role="--output-dir")
    cache_root = resolve_runtime_path(args.cache_root, paths, role="--cache-root")
    if output_dir == Path("/sources/papers") or str(output_dir).startswith("/sources/"):
        parser.error("--output-dir resolved under /sources; pass @configured-sources-papers or an absolute wiki path.")
    _reject_repo_wiki_output(parser, output_dir, paths)
    legacy_cache = (paths.project_root / ".mineru-cache").resolve()
    if cache_root == legacy_cache:
        parser.error("--cache-root resolved to legacy .mineru-cache; pass @mineru-cache so cache files go under .checkpoints/mineru-cache.")
    source = _resolve_source_path(args.source, paths.raw_root, paths.project_root)
    result = prepare(
        pdf=source,
        raw_root=paths.raw_root,
        title_override=args.title,
        bibtex_override=args.bibtex,
        citation_key=args.citation_key,
        authors=args.authors,
        year=args.year,
        cache_root=cache_root,
        language=args.language,
        backend=args.backend,
        overwrite=args.overwrite,
        wiki_root=paths.wiki_root,
        output_dir=output_dir,
        project_root=paths.project_root,
    )
    print(json.dumps(result, ensure_ascii=False))
    if not result.get("usable"):
        raise SystemExit(2)


if __name__ == "__main__":
    configure_utf8_stdio()
    main()

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
      -> wiki/sources/papers/<slug>.md                # canonical_ingest_path
      -> wiki/sources/papers/assets/<slug>/*.jpg      # extracted figure crops

Cache layout (kept across runs for cheap re-prep):

    .mineru-cache/<sha16>/
        <stem>.md               raw MinerU markdown
        <stem>.json             MinerU content_list block list
        full.md                 adapter-canonical copy of <stem>.md
        manifest.json           synthesized from the block list
        images/                 figure/table crops referenced by the .md

CLI (preserves OmegaWiki's contract — `/ingest` invocations are unchanged):

    python3 tools/prepare_paper_source.py \\
        --raw-root raw \\
        --source raw/papers/example.pdf \\
        [--title "Recovered Paper Title"]

stdout: a single JSON object (one line) with the manifest shape `/ingest`
expects. `canonical_ingest_path` is the file `/ingest` should read; for this
build it is always a `.md` produced by MinerU + adapter (`ingest_format = "mineru-md"`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import frontmatter
import _mineru
from _paths import DEFAULT_CONFIG_PATH, display_path, load_paths
from research_wiki import slugify

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

NUMBERED_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\.?\s*[A-Za-z]")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(images/([^)]+)\)")
FIGURE_LABEL_RE = re.compile(r"\b(Figure|Fig\.?|Table)\s*\d+\b", re.IGNORECASE)
AUTHOR_INITIAL_RE = re.compile(r"\b[A-Z]\.\s*[A-Z]")
BIBTEX_SECTION_RE = re.compile(
    r"\n*## BibTeX\s*\n+```bibtex\n.*?\n```\s*",
    re.DOTALL,
)


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
) -> tuple[str, list[str], list[str]]:
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

            if title_norm and heading_text.lower() == title_norm:
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
    return body, dropped, skipped_sections


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


def _source_output_dir(raw_root: Path, wiki_root: Path | None = None) -> Path:
    if wiki_root is not None:
        return wiki_root.resolve() / "sources" / "papers"
    return _project_root(raw_root) / "wiki" / "sources" / "papers"


def prepare(
    pdf: Path,
    raw_root: Path,
    title_override: str = "",
    bibtex_override: str = "",
    cache_root: Path | None = None,
    language: str = "en",
    backend: str = "api",
    overwrite: bool = False,
    wiki_root: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    """Run MinerU on a PDF and write a structured markdown source to wiki/sources/papers/.

    Returns the manifest `/ingest` consumes.
    """
    warnings: list[str] = []
    output_dir = _source_output_dir(raw_root, wiki_root=wiki_root)
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

    cache_root = cache_root or Path(".mineru-cache")
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
    slug = slugify(title)
    out_path = output_dir / f"{slug}.md"
    legacy_prepared_path = raw_root / PREPARED_SUBDIR / "papers" / f"{slug}.md"
    legacy_out_path = raw_root / LEGACY_PREPARED_SUBDIR / "papers" / f"{slug}.md"
    if not out_path.exists() and legacy_prepared_path.exists() and not overwrite:
        existing_front = _read_existing_frontmatter(legacy_prepared_path)
        existing_source = existing_front.get("source", "")
        if _same_source(existing_source, pdf):
            existing_text = legacy_prepared_path.read_text(encoding="utf-8", errors="ignore")
            migrated_text = _upsert_bibtex_body(existing_text, bibtex_override)
            if migrated_text != existing_text:
                existing_text = migrated_text
                legacy_prepared_path.write_text(existing_text, encoding="utf-8")
            return {
                "canonical_ingest_path": display_path(legacy_prepared_path, display_root),
                "prepared_path": display_path(legacy_prepared_path, display_root),
                "ingest_format": "mineru-md",
                "title": existing_front.get("title") or title,
                "abstract_excerpt": _build_abstract_excerpt(_strip_frontmatter(existing_text)),
                "warnings": [
                    f"legacy prepared source reused: {display_path(legacy_prepared_path, display_root)}",
                    f"new prepared sources are written under {display_path(output_dir, display_root)}",
                ],
                "usable": True,
            }
    if not out_path.exists() and legacy_out_path.exists() and not overwrite:
        existing_front = _read_existing_frontmatter(legacy_out_path)
        existing_source = existing_front.get("source", "")
        if _same_source(existing_source, pdf):
            existing_text = legacy_out_path.read_text(encoding="utf-8", errors="ignore")
            migrated_text = _upsert_bibtex_body(existing_text, bibtex_override)
            if migrated_text != existing_text:
                existing_text = migrated_text
                legacy_out_path.write_text(existing_text, encoding="utf-8")
            return {
                "canonical_ingest_path": display_path(legacy_out_path, display_root),
                "prepared_path": display_path(legacy_out_path, display_root),
                "ingest_format": "mineru-md",
                "title": existing_front.get("title") or title,
                "abstract_excerpt": _build_abstract_excerpt(_strip_frontmatter(existing_text)),
                "warnings": [
                    f"legacy prepared source reused: {display_path(legacy_out_path, display_root)}",
                    f"new prepared sources are written under {display_path(output_dir, display_root)}",
                ],
                "usable": True,
            }
    if out_path.exists() and not overwrite:
        existing_front = _read_existing_frontmatter(out_path)
        existing_source = existing_front.get("source", "")
        existing_text = out_path.read_text(encoding="utf-8", errors="ignore")
        if _same_source(existing_source, pdf):
            migrated_text = _upsert_bibtex_body(existing_text, bibtex_override)
            if migrated_text != existing_text:
                existing_text = migrated_text
                out_path.write_text(existing_text, encoding="utf-8")
            return {
                "canonical_ingest_path": display_path(out_path, display_root),
                "prepared_path": display_path(out_path, display_root),
                "ingest_format": "mineru-md",
                "title": existing_front.get("title") or title,
                "abstract_excerpt": _build_abstract_excerpt(_strip_frontmatter(existing_text)),
                "warnings": [f"prepared source already exists; reusing: {out_path}"],
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

    body, dropped, skipped_sections = _transform_markdown(full_md, slug, title)

    if not body.strip():
        return {
            "canonical_ingest_path": display_path(_source_output_dir(raw_root, wiki_root=wiki_root) / f"{slug}.md", display_root),
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
        "source": str(pdf),
        "ingestedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourceType": "pdf",
        "pipeline": "mineru",
        "totalPages": int(manifest.get("totalPages", 0) or 0),
        "totalChars": int(manifest.get("totalChars", 0) or 0),
    }
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
    overwrite: bool = False,
    wiki_root: Path | None = None,
    project_root: Path | None = None,
) -> dict:
    """Compatibility wrapper used by init_discovery.py."""
    result = prepare(
        pdf=path,
        raw_root=raw_root,
        title_override=title,
        bibtex_override=bibtex,
        overwrite=overwrite,
        wiki_root=wiki_root,
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


def _resolve_source_path(source: Path, raw_root: Path, project_root: Path) -> Path:
    if source.is_absolute():
        return source.resolve()
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
    parser.add_argument("--raw-root", default=None, type=Path,
                        help="Raw source root. Defaults to config/paths.json or ./raw.")
    parser.add_argument("--wiki-root", default=None, type=Path,
                        help="Wiki vault root. Defaults to config/paths.json or ./wiki.")
    parser.add_argument("--paths-config", default=DEFAULT_CONFIG_PATH, type=Path,
                        help="Path config JSON (default: config/paths.json).")
    parser.add_argument("--source", required=True, type=Path,
                        help="Path to a local PDF to prepare.")
    parser.add_argument("--title", default="",
                        help="Confident agent-recovered title. Used verbatim when set.")
    parser.add_argument("--bibtex", default="",
                        help="Derived Zotero BibTeX string to persist in the prepared source body under ## BibTeX.")
    parser.add_argument("--cache-root", default=None, type=Path,
                        help="MinerU cache root (default: .mineru-cache at CWD).")
    parser.add_argument("--language", default="en", help="Document language for MinerU.")
    parser.add_argument("--backend", default="api", choices=("api", "local"),
                        help="MinerU backend: 'api' (cloud) or 'local' (mineru[all]).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace an existing wiki/sources/papers/<slug>.md after user confirmation.")
    args = parser.parse_args()

    paths = load_paths(config_path=args.paths_config, wiki_root=args.wiki_root, raw_root=args.raw_root)
    source = _resolve_source_path(args.source, paths.raw_root, paths.project_root)
    result = prepare(
        pdf=source,
        raw_root=paths.raw_root,
        title_override=args.title,
        bibtex_override=args.bibtex,
        cache_root=args.cache_root,
        language=args.language,
        backend=args.backend,
        overwrite=args.overwrite,
        wiki_root=paths.wiki_root,
        project_root=paths.project_root,
    )
    print(json.dumps(result, ensure_ascii=False))
    if not result.get("usable"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

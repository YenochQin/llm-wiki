---
description: Ingest local PDF files or PDF directories into the wiki by preprocessing them into prepared MinerU markdown, then handing the prepared sources to /ingest.
argument-hint: "(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]"
---

# /ingest-local-pdf

Use this skill when the source lives outside Zotero: a local PDF, a directory of PDFs, or another raw local file that needs MinerU preprocessing before it can enter the wiki. The skill normalizes the source into `wiki/sources/papers/*.md`, then hands the prepared path to `/ingest` so the normal paper/concept/claim workflow stays in one place.

Use this local reference on demand:

- `references/pdf-preprocessing.md` -- local PDF normalization, title recovery, directory batching, and handoff to `/ingest`

## Workflow

1. Resolve the input path.
   - If the input is a single PDF, inspect the first page and recover a confident title only when the title is clear.
   - If the input is a directory, enumerate readable PDFs in deterministic order and process each file separately.
2. Preprocess each PDF with `tools/prepare_paper_source.py` into `wiki/sources/papers/<slug>.md`.
3. If `prepare_paper_source.py` reports `usable: false`, surface the warnings and skip that file.
4. Hand each prepared `wiki/sources/papers/<slug>.md` to `/ingest` for the paper-page workflow.
5. If the source is already a prepared `wiki/sources/papers/*.md`, skip preprocessing and pass it straight to `/ingest`.

## Constraints

- Do not look up Zotero PDFs here; that belongs to `/ingest`.
- Do not write directly to `wiki/papers/`, `wiki/concepts/`, `wiki/claims/`, or `wiki/people/` from this skill.
- Keep raw PDFs in their original location; only the prepared markdown and extracted assets belong under `wiki/sources/`.
- If the directory contains mixed file types, ignore non-PDF files unless the user explicitly points at a prepared markdown file.

## Dependencies

### Tools (via Bash)

- `uv run python tools/prepare_paper_source.py --raw-root "$RAW_ROOT" --source <local-path> [--title "<recovered-title>"]`

### Skills

- `/ingest` -- consumes the prepared `wiki/sources/papers/*.md` path and writes the wiki pages

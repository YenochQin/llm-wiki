# /ingest PDF Preprocessing

Open this reference when `/ingest` has selected a Zotero PDF attachment and needs to convert it into structured markdown before ingest can proceed.

## Why preprocessing exists

A PDF attachment is a poor ingest source by itself: text extraction varies, equations and captions are easy to miss, and figure regions are not addressable. The MinerU pipeline turns the Zotero-selected PDF into a structured markdown file with a YAML frontmatter that already lists `sections`, `figures`, and a clean body where heading depth tracks dotted section numbers. The rest of `/ingest` then works from one uniform input shape.

## Pipeline

```text
PDF -> tools/_mineru.extract            (cloud API by default; local backend opt-in)
    -> <explicit-cache-root>/<sha16>/  (per-PDF cache: <stem>.md, <stem>.json, manifest.json, images/)
    -> tools/prepare_paper_source       (adapter: cover normalization, heading hierarchy, cutoffs, image relocation, LaTeX math repair)
    -> <explicit-output-dir>/<source-slug>.md       + <explicit-output-dir>/assets/<source-slug>/<hash>.jpg
```

For full details (cache layout, adapter passes, troubleshooting) open `docs/mineru-pipeline.md`.

## Recovery order

Follow this exact order before invoking the prep tool. Stop at the first step that produces a confident result.

1. **Agent inspection of the PDF itself.**
   Before invoking any tool, open the PDF and record:
   - a confident paper title from the first-page title when Zotero metadata is unavailable or incomplete
   Zotero Local API metadata remains preferred for title/DOI/authors when available.
2. **Zotero metadata.**
   After `/ingest` has selected a DOI/title-matched Zotero candidate, prefer `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>` for identity fields and the derived `bibtex` entry. This is an internal enrichment call only; do not expose `--item-key` as a user-facing `/ingest` selector.

## Invocation

Once you have the title (possibly empty), run:

```shell
uv run python tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source '<zotero-pdf-path>' [--citation-key '<zotero-citation-key>'] [--authors '<author-list>'] [--year <year>] [--bibtex "$BIBTEX"] [--title '<zotero-or-agent-recovered-title>']
```

- Pass `--title` when Zotero metadata or first-page inspection gives a confident title. Do not pass a title derived from PDF metadata or from the filename — those poison the literature enrichment lookup.
- Pass `--citation-key` when Zotero/Better BibTeX provides one; it is the preferred prepared-source filename stem. If no citation key is available, pass `--authors`, `--year`, and `--title` so the helper names the source as `author_year_veryshorttitle`.
- Omit the flag when no title is confident. The helper falls back cleanly.
- The helper automatically runs `tools/repair_latex_math.py` on the prepared body before writing. This conservative pass only edits math spans/blocks, skips code fences and inline code, converts `\(...\)` / `\[...\]` to Obsidian-compatible `$...$` / `$$...$$`, and removes common OCR-inserted spaces such as `\ alpha`, `_ {i}`, `^ {2}`, and `\left (`. It also repairs atomic term-symbol OCR such as `1 s ^ { 2 } ^ { 1 } S _ { 0 }` into `1s^{2} \ ^{1}S_{0}` so the second superscript is rendered as the left superscript of the term symbol. If repairs were applied, the JSON `warnings` array includes a `latex math repaired: ...` summary and the prepared frontmatter records the repair counts.
- The prepared markdown frontmatter `source` must be portable. For Zotero attachments, it must be written as `${Zotero data directory}/storage/<attachment-key>/<file>.pdf`, never as a machine-specific absolute path such as `E:\...`, `/Users/...`, or `/home/...`.

The helper writes the prepared entry under the explicit `--output-dir` (normally `@configured-sources/papers`) and prints a JSON record with:

| Field | Meaning |
|-------|---------|
| `canonical_ingest_path` | the prepared `.md` `/ingest` should consume |
| `prepared_path` | same path; kept for parity with the OmegaWiki contract |
| `ingest_format` | always `mineru-md` for this pipeline |
| `title` | best title (agent-supplied > MinerU-detected > filename stem) |
| `abstract_excerpt` | first ~400 chars after the abstract heading |
| `warnings` | non-fatal anomalies (no abstract found, no figures detected, LaTeX math repair counts, etc.) |
| `usable` | boolean — `false` blocks ingest |

Use `canonical_ingest_path` as the source for the rest of `/ingest`.

## Title authority

When Zotero supplied a title, treat that title as authoritative for the paper page's `title` field. Titles detected by MinerU's cover-page heuristics are fallback display strings only; do not let them overwrite Zotero metadata.

## Reading the prepared output

The prepared `.md` looks like:

```markdown
---
title: "..."
source: "${Zotero data directory}/storage/<attachment-key>/<file>.pdf"
ingestedAt: "2026-05-06T..."
totalPages: 24
totalChars: 87412
sections:
  - {level: 1, title: "Introduction", line: 12}
  - {level: 2, title: "Related work", line: 84}
  - ...
figures:
  - {id: "fig-1", path: "assets/<source-slug>/abc123.jpg", caption: "..."}
  - ...
skippedSectionHeadings: ["Acknowledgments", "Disclosure Statement"]  # optional
droppedHeadings: ["URL stub", "Contents"]
---

# Introduction
...

# References
...
```

Use the frontmatter as your structural anchor when extracting concepts, claims, and figure references. Do not re-derive section structure from the body; the adapter already did it. The bibliography is intentionally retained: use it to resolve inline `(Author, year)` references and to expand citation/discovery paths.

Prepared math should already use `$...$` and `$$...$$`. If you still see visibly broken formulas in the prepared markdown, run a dry report first:

```shell
uv run python tools/repair_latex_math.py --dry-run '@configured-sources-papers/<source-slug>.md'
```

Only rewrite existing prepared sources after confirming the report is limited to math-span repairs.

## Output

A successful preprocessing pass produces:

- `wiki/sources/papers/<source-slug>.md` — frontmatter + cleaned body. `<source-slug>` is the sanitized Zotero citation key when available; otherwise it is `author_year_veryshorttitle`.
- `wiki/sources/papers/assets/<source-slug>/<hash>.jpg` — only the figures that survived the cut

From this point on, treat the prepared `.md` as the canonical source for the rest of `/ingest`. Do not re-copy the PDF into `raw/papers/`; the original Zotero attachment remains the user-owned artifact.

Prepared markdown generated from Zotero attachments must be written under `wiki/sources/papers/`.

## Failure modes

- **`MINERU_API_TOKEN is not set`**: surface this clearly to the user. Either ask them to add the token to `~/.config/llm-wiki/.env`, or fall back to the local MinerU backend if installed (`uv sync --extra local`).
- **MinerU API outage / rate limit**: same fallback — try the local backend if available, otherwise hand off to the user with a clear message.
- **Manifest reports `usable: false`**: do not proceed. Surface the `warnings` array to the user; common causes are scanned PDFs without OCR, encrypted PDFs, or pages-only image dumps.
- **No figures extracted on a paper that clearly has them**: not blocking. Note in the report; the user may want to switch to the local backend for that paper.

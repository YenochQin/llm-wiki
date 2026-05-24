# /ingest-local-pdf PDF Preprocessing

Open this reference when `/ingest-local-pdf` receives a local `.pdf` or a directory of PDFs and needs to convert the files into structured markdown before handoff to `/ingest`.

## Why preprocessing exists

A raw PDF is a poor ingest source: text extraction varies, equations and captions are easy to miss, and figure regions are not addressable. The MinerU pipeline turns each PDF into a structured markdown file with YAML frontmatter that already lists `sections`, `figures`, and a clean body where heading depth tracks dotted section numbers. `/ingest` then works from one uniform prepared input shape.

For directory inputs, process each PDF independently in deterministic order. Do not try to merge multiple PDFs into one prepared source.

## Pipeline

```text
PDF -> tools/_mineru.extract            (cloud API by default; local backend opt-in)
    -> <explicit-cache-root>/<sha16>/  (per-PDF cache: <stem>.md, <stem>.json, manifest.json, images/)
    -> tools/enrich_local_pdf_bibtex    (optional metadata-only Zotero BibTeX enrichment)
    -> tools/prepare_paper_source       (adapter: cover normalization, heading hierarchy, cutoffs, image relocation, LaTeX math repair)
    -> <explicit-output-dir>/<source-slug>.md       + <explicit-output-dir>/assets/<source-slug>/<hash>.jpg
```

For full details (cache layout, adapter passes, troubleshooting) open `docs/mineru-pipeline.md`.

## Recovery order

Follow this exact order before invoking the prep tool. Stop at the first step that produces a confident result.

1. **Agent inspection of the PDF itself.**
   Before invoking any tool, open the PDF and record:
   - a confident paper title from the first page, not from PDF metadata
   The title may be empty. Do not guess.
2. **Directory batches.**
   When the user points at a directory, inspect each PDF separately and recover a title per file only when it is clear.

## Invocation

Once you have the title (possibly empty), first try metadata-only Zotero enrichment:

```shell
uv run python tools/enrich_local_pdf_bibtex.py --source <pdf-path> [--title "<agent-recovered-title>"]
```

- Use this only to enrich metadata/BibTeX for the same local PDF. Do not switch the content source to Zotero's PDF from this skill.
- If the helper returns `status: ok`, use the returned `.bibtex` verbatim and pass `.citation_key`, `.authors`, and `.year` to the prep tool when present.
- If the helper returns `not_found` or `metadata_error`, continue without BibTeX and report the reason. The user can open Zotero Desktop / enable Local API access and rerun if needed.

Then run:

```shell
uv run python tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source <pdf-path> [--title "<agent-recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]
```

- Pass `--title` only when the title is confident. Do not pass a title derived from PDF metadata or the filename.
- Omit the flag when no title is confident. The helper falls back cleanly.
- Pass `--bibtex` only with a BibTeX string returned by `tools/enrich_local_pdf_bibtex.py` or other authoritative metadata flow. The helper writes it into the prepared markdown body under `## BibTeX`; it must not appear in YAML frontmatter.
- Pass `--citation-key` when Zotero/Better BibTeX provides one; it is the preferred prepared-source filename stem. If no citation key is available, pass `--authors`, `--year`, and `--title` so the helper names the source as `author_year_veryshorttitle`.
- The helper automatically runs `tools/repair_latex_math.py` on the prepared body before writing. This conservative pass only edits math spans/blocks, skips code fences and inline code, converts `\(...\)` / `\[...\]` to Obsidian-compatible `$...$` / `$$...$$`, and removes common OCR-inserted spaces such as `\ alpha`, `_ {i}`, `^ {2}`, and `\left (`. It also repairs atomic term-symbol OCR such as `1 s ^ { 2 } ^ { 1 } S _ { 0 }` into `1s^{2} \ ^{1}S_{0}` so the second superscript renders as the left superscript of the term symbol. If repairs were applied, the JSON `warnings` array includes a `latex math repaired: ...` summary and the prepared frontmatter records the repair counts.

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

Use `canonical_ingest_path` as the source for `/ingest`. When the prepared markdown contains a `## BibTeX` block, `/ingest` should carry that block into the generated paper page unless a later Zotero metadata lookup produces a clearly better authoritative BibTeX entry.

## Title authority

When the agent supplied a confident title, treat that title as authoritative for the paper page's `title` field. Titles detected by MinerU's cover-page heuristics are fallback display strings only; do not let them overwrite the agent title.

## Output

A successful preprocessing pass produces:

- `wiki/sources/papers/<source-slug>.md` — frontmatter + cleaned body. `<source-slug>` is the sanitized Zotero citation key when available; otherwise it is `author_year_veryshorttitle`.
- `wiki/sources/papers/assets/<source-slug>/<hash>.jpg` — only the figures that survived the cut

From this point on, treat the prepared `.md` as the canonical source for `/ingest`. Do not re-copy the PDF into `raw/papers/`; the original path remains the user-owned artifact.

Prepared math should already use `$...$` and `$$...$$`. If you need to repair an existing prepared source, inspect first:

```shell
uv run python tools/repair_latex_math.py --dry-run '@configured-sources-papers/<source-slug>.md'
```

Only run without `--dry-run` after confirming the report is limited to math-span repairs.

## Failure modes

- **`MINERU_API_TOKEN is not set`**: surface this clearly to the user. Either ask them to add the token to `~/.config/llm-wiki/.env`, or fall back to the local MinerU backend if installed (`uv sync --extra local`).
- **MinerU API outage / rate limit**: same fallback — try the local backend if available, otherwise hand off to the user with a clear message.
- **Manifest reports `usable: false`**: do not proceed. Surface the `warnings` array to the user; common causes are scanned PDFs without OCR, encrypted PDFs, or pages-only image dumps.
- **No figures extracted on a paper that clearly has them**: not blocking. Note in the report; the user may want to switch to the local backend for that paper.
- **Zotero enrichment not found**: not blocking. Continue ingest and report that no matching Zotero item was found.
- **Zotero Local API unavailable**: not blocking. SQLite matching may find an item, but full BibTeX extraction needs Zotero Desktop Local API; tell the user to open Zotero and rerun if they want the richer BibTeX.

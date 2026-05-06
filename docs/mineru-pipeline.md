# MinerU Pipeline — PDF to llm-wiki Source Markdown

End-to-end pipeline for converting raw PDFs into the structured markdown that `/ingest` consumes. MinerU is a vision-language PDF parser; we use it instead of the OmegaWiki tex-priority chain because it preserves section structure and figure crops on PDF-only sources.

## Pipeline

```text
raw/papers/<file>.pdf
    -> tools/_mineru.extract           (cloud API or local backend)
    -> .mineru-cache/<sha16>/          (per-PDF cache: <stem>.md, <stem>.json, manifest.json, images/)
    -> tools/prepare_paper_source     (adapter: heading hierarchy, cover normalization, cutoffs, image relocation)
    -> raw/tmp/papers/<slug>.md        + raw/tmp/papers/assets/<slug>/<hash>.jpg
    -> /ingest reads canonical_ingest_path = raw/tmp/papers/<slug>.md
```

`prepare_paper_source.py` returns a JSON manifest with:

| Field | Meaning |
|-------|---------|
| `canonical_ingest_path` | the markdown file `/ingest` should read (always under `raw/tmp/papers/`) |
| `prepared_path` | same as above; kept for parity with the OmegaWiki contract |
| `ingest_format` | `"mineru-md"` — flag to skills that this is structured MinerU output, not raw PDF or `.tex` |
| `title` | best-effort title detected from the cover or the first non-junk heading |
| `abstract_excerpt` | first ~400 chars after the abstract heading, for skill prompts |
| `arxiv_id` | recovered from the PDF text if present, else null |
| `warnings` | non-fatal anomalies (missing abstract, no figures, etc.) |
| `usable` | boolean — `false` blocks downstream ingest |

## Components

- **`tools/_mineru.py`** — MinerU client. Two interchangeable backends (`api` cloud and `local` library) that both normalize their output into the cache layout below. Lifted verbatim from `pdf-source-scripts/mineru_backend.py`.
- **`tools/prepare_paper_source.py`** — orchestrator + adapter. Hashes the PDF for a per-document cache, calls `_mineru.extract`, synthesizes a manifest from MinerU's block list, runs the adapter, and writes the OmegaWiki-style JSON manifest.

## Prerequisites

- Python 3.10+ (managed by uv via `.venv`).
- For `api` backend (default): `MINERU_API_TOKEN` set in project-root `.env` or in `~/.config/MinerU/mineru.env`. Optional override: `MINERU_API_BASE` (default `https://mineru.net/api/v4`).
- For `local` backend: `uv pip install -e ".[local]"`. First run downloads several GB of model weights; afterward extraction runs offline. No token needed.

## Single-PDF usage (CLI)

```bash
uv run python tools/prepare_paper_source.py \
  --raw-root raw \
  --source raw/papers/<file>.pdf \
  [--title "Optional override"] \
  [--arxiv-id 2401.12345]
```

Output is a JSON manifest on stdout (consumed by `/ingest`). Side effects:

- Populates `.mineru-cache/<sha16>/` (reused on subsequent runs).
- Writes `raw/tmp/papers/<slug>.md` + `raw/tmp/papers/assets/<slug>/`.

## Cache layout

```
.mineru-cache/<sha16>/
    <stem>.md                  # raw MinerU markdown (untouched)
    <stem>.json                # MinerU content_list block list
    full.md                    # adapter-canonical copy of the .md
    manifest.json              # synthesized from the block list
    images/                    # extracted figure / table crops
```

`<sha16>` is the first 16 hex chars of `sha256(first 4 MiB of pdf)`. Re-running on the same PDF reuses the cache and only re-runs the cheap adapter step. To force a fresh extraction, delete the per-PDF cache directory.

## Output layout

```
raw/tmp/papers/
    <slug>.md                        # frontmatter + body (this is canonical_ingest_path)
    assets/<slug>/<hash>.jpg         # only images that survive the adapter cut
```

Frontmatter on `<slug>.md` includes `title`, `source`, `ingestedAt`, `totalPages`, `totalChars`, optional `arxivId`, `cutoffHeading`, `droppedHeadings`, plus structured `sections` and `figures` arrays. `/ingest` mines this for paper-level metadata, concept candidates, and figure cross-references.

## What the adapter cleans up

MinerU's raw markdown is flat and noisy. The adapter applies seven passes (mirrors `pdf-source-scripts/pdf_to_source_mineru.py`):

1. **Title detection.** Picks the first non-junk, non-numbered, non-journal heading from the manifest's `sections`. Falls back to the PDF stem.
2. **Cover-page normalization.** MinerU emits each visual line on the cover as a separate level-1 block. The adapter merges title fragments and drops author bylines / journal furniture, then emits a single synthetic `# <title>` before the first real section.
3. **Heading hierarchy.** Counts dot-separated section numbers (`1.` → `#`, `2.1.` → `##`, `2.1.1.` → `###`). Inserts a missing space between the number and the title when MinerU OCR-glued them.
4. **Junk filtering.** Drops URL-like headings, "Contents", margin glossaries ending in `:`, and journal-name covers. Unnumbered headings are demoted to bold unless they are in the `KEEP_UNNUMBERED` allowlist (Abstract, Keywords, Introduction, Methods, Results, Discussion, Conclusion, …).
5. **Truncation.** Stops at the first `CUTOFF_PATTERNS` match — References, Bibliography, Acknowledgments, Disclosure Statement, Supplementary Information, Appendix, Funding, Author Contributions, Competing Interests, Data Availability.
6. **Image relocation.** Rewrites `images/<hash>` references to `assets/<slug>/<hash>` and copies only the images that survive the cut.
7. **Frontmatter emission.** Writes the YAML described above.

## arXiv URL flow

`/ingest <arxiv-url>` first calls `tools/init_discovery.py download` to fetch the PDF into `raw/discovered/`, then routes through this same MinerU pipeline. No special-case logic — the prep tool just sees a PDF.

## Troubleshooting

- **`MINERU_API_TOKEN is not set`**: the `api` backend couldn't find a token. Add `MINERU_API_TOKEN=…` to `.env`, or export it in the shell, or write it to `~/.config/MinerU/mineru.env`.
- **`401`/`403` from the cloud API**: token invalid or expired. Regenerate at <https://mineru.net/apiManage/account/api>.
- **`backend='local' requires the mineru library`**: install with `uv pip install -e ".[local]"`. First run downloads several GB of model weights.
- **MinerU API down / rate-limited**: switch to local backend by installing the `local` extra and re-running. The CLI accepts the same flags.
- **Title is split or missing**: cover-block sequence broke normalization. Inspect `.mineru-cache/<sha16>/<stem>.json`, look at the leading `text_level: 1` blocks on `page_idx: 0`, and adjust the cover-normalization helpers in `prepare_paper_source.py`.
- **Reference dump leaks into body**: the cutoff heading didn't match any `CUTOFF_PATTERNS`. Add a pattern (use `\s*`, not `\s+`, to tolerate OCR-glued forms like `DISCLOSURESTATEMENT`).
- **Stale output after editing the adapter**: delete only `manifest.json` inside the per-PDF cache (or the whole `<sha16>/` directory) and re-run; the cached `<stem>.md` / `<stem>.json` from MinerU are reused.

## Why MinerU instead of the OmegaWiki tex-priority chain?

OmegaWiki's original `prepare_paper_source.py` preferred arXiv `.tex` source when recoverable, falling back to a synthetic `.tex` from PDF text. That works well when most sources are arXiv preprints. For a more general workflow (Zotero PDFs, books, conference papers, scanned reports), MinerU's vision-language extraction gives consistently better section/figure structure than text-only PDF parsing. The trade-off: MinerU is a network dependency (the API) or a heavy local install, and it does not recover paper identity (no automatic arXiv ID lookup) — the adapter only extracts an arXiv ID if it appears verbatim in the PDF text.

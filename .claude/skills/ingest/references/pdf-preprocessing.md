# /ingest PDF Preprocessing

Open this reference when `/ingest` receives a local `.pdf` and needs to convert it into structured markdown before ingest can proceed. Skip it in INIT MODE — `/init` already ran an equivalent batch preprocessing pass and handed off a canonical path.

## Why preprocessing exists

A raw PDF is a poor ingest source: text extraction varies, equations and captions are easy to miss, and figure regions are not addressable. The MinerU pipeline turns the PDF into a structured markdown file with a YAML frontmatter that already lists `sections`, `figures`, optional `arxivId`, and a clean body where heading depth tracks dotted section numbers. The rest of `/ingest` then works from one uniform input shape.

This mirrors the pipeline `tools/init_discovery.py prepare` runs internally when `/init` batch-processes local PDFs. You are doing the same thing for a single paper, inline.

## Pipeline

```text
PDF -> tools/_mineru.extract            (cloud API by default; local backend opt-in)
    -> .mineru-cache/<sha16>/           (per-PDF cache: <stem>.md, <stem>.json, manifest.json, images/)
    -> tools/prepare_paper_source       (adapter: cover normalization, heading hierarchy, cutoffs, image relocation)
    -> raw/tmp/papers/<slug>.md         + raw/tmp/papers/assets/<slug>/<hash>.jpg
```

For full details (cache layout, adapter passes, troubleshooting) open `docs/mineru-pipeline.md`.

## Recovery order

Follow this exact order before invoking the prep tool. Stop at the first step that produces a confident result.

1. **Agent inspection of the PDF itself.**
   Before invoking any tool, open the PDF and record:
   - a confident paper title (from the first-page title, not from PDF metadata — metadata is often wrong)
   - a confident arXiv ID if one is visibly printed on the first page or in a header
   Either or both may be empty. Do not guess.
2. **Filename / path arXiv ID extraction.**
   `prepare_paper_source.py` regex-matches an arXiv ID embedded in the filename or containing folder; you do not need to do this yourself.
3. **Title-based Semantic Scholar lookup.**
   Only runs when the agent supplied a confident `--title`. The helper handles it internally.

The MinerU pipeline itself does not require an arXiv ID — it processes any PDF. The arXiv ID is only used to enrich downstream metadata (`venue`, `year`, citation counts) once `/ingest` Step 2 runs.

## Invocation

Once you have the title and/or arXiv ID (possibly both empty), run:

```bash
"$PYTHON_BIN" tools/prepare_paper_source.py \
  --raw-root raw \
  --source <pdf-path> \
  [--title "<agent-recovered-title>"] \
  [--arxiv-id "<agent-recovered-arxiv-id>"]
```

- Pass `--title` only when the agent is confident. Do not pass a title derived from PDF metadata or from the filename — those poison the S2 enrichment lookup.
- Pass `--arxiv-id` only when the agent read it off the page. Filename-embedded IDs are picked up automatically.
- Omit both flags when neither is confident. The helper falls back cleanly.

The helper writes the prepared entry under `raw/tmp/papers/` and prints a JSON record with:

| Field | Meaning |
|-------|---------|
| `canonical_ingest_path` | the prepared `.md` `/ingest` should consume |
| `prepared_path` | same path; kept for parity with the OmegaWiki contract |
| `ingest_format` | always `mineru-md` for this pipeline |
| `title` | best title (agent-supplied > MinerU-detected > filename stem) |
| `abstract_excerpt` | first ~400 chars after the abstract heading |
| `arxiv_id` | recovered from PDF text or supplied by the agent; may be null |
| `warnings` | non-fatal anomalies (no abstract found, no figures detected, etc.) |
| `usable` | boolean — `false` blocks ingest |

Use `canonical_ingest_path` as the source for the rest of `/ingest`.

## Title authority

When the agent supplied a confident title, treat that title as authoritative for the paper page's `title` field. Titles detected by MinerU's cover-page heuristics are fallback display strings only; do not let them overwrite the agent title. The agent-recovered title is what drove the successful S2 lookup; letting a parsed cover title overwrite it creates subtle identity drift.

## Reading the prepared output

The prepared `.md` looks like:

```markdown
---
title: "..."
source: "raw/papers/<file>.pdf"
ingestedAt: "2026-05-06T..."
arxivId: "2401.12345"           # optional
totalPages: 24
totalChars: 87412
sections:
  - {level: 1, title: "Introduction", line: 12}
  - {level: 2, title: "Related work", line: 84}
  - ...
figures:
  - {id: "fig-1", path: "assets/<slug>/abc123.jpg", caption: "..."}
  - ...
cutoffHeading: "References"     # body truncated here
droppedHeadings: ["URL stub", "Contents"]
---

# Introduction
...
```

Use the frontmatter as your structural anchor when extracting concepts, claims, and figure references. Do not re-derive section structure from the body; the adapter already did it.

## Output

A successful preprocessing pass produces:

- `raw/tmp/papers/<slug>.md` — frontmatter + cleaned body
- `raw/tmp/papers/assets/<slug>/<hash>.jpg` — only the figures that survived the cut

From this point on, treat the prepared `.md` as the canonical source for the rest of `/ingest`. Do not re-copy the PDF into `raw/papers/`; the original path remains the user-owned artifact.

## Failure modes

- **`MINERU_API_TOKEN is not set`**: surface this clearly to the user. Either ask them to add the token to `.env`, or fall back to the local MinerU backend if installed (`uv pip install -e ".[local]"`).
- **MinerU API outage / rate limit**: same fallback — try the local backend if available, otherwise hand off to the user with a clear message.
- **Manifest reports `usable: false`**: do not proceed. Surface the `warnings` array to the user; common causes are scanned PDFs without OCR, encrypted PDFs, or pages-only image dumps.
- **No figures extracted on a paper that clearly has them**: not blocking. Note in the report; the user may want to switch to the local backend for that paper.

# /ingest PDF Preprocessing

Open this reference when `/ingest` receives a local `.pdf` and needs to convert it into structured markdown before ingest can proceed. Skip it in INIT MODE — `/init` already ran an equivalent batch preprocessing pass and handed off a canonical path.

## Why preprocessing exists

A raw PDF is a poor ingest source: text extraction varies, equations and captions are easy to miss, and figure regions are not addressable. The MinerU pipeline turns the PDF into a structured markdown file with a YAML frontmatter that already lists `sections`, `figures`, and a clean body where heading depth tracks dotted section numbers. The rest of `/ingest` then works from one uniform input shape.

This mirrors the pipeline `tools/init_discovery.py prepare` runs internally when `/init` batch-processes local PDFs. You are doing the same thing for a single paper, inline.

## Pipeline

```text
PDF -> tools/_mineru.extract            (cloud API by default; local backend opt-in)
    -> .mineru-cache/<sha16>/           (per-PDF cache: <stem>.md, <stem>.json, manifest.json, images/)
    -> tools/prepare_paper_source       (adapter: cover normalization, heading hierarchy, cutoffs, image relocation)
    -> wiki/sources/papers/<slug>.md         + wiki/sources/papers/assets/<slug>/<hash>.jpg
```

For full details (cache layout, adapter passes, troubleshooting) open `docs/mineru-pipeline.md`.

## Recovery order

Follow this exact order before invoking the prep tool. Stop at the first step that produces a confident result.

1. **Agent inspection of the PDF itself.**
   Before invoking any tool, open the PDF and record:
   - a confident paper title (from the first-page title, not from PDF metadata — metadata is often wrong)
   The title may be empty. Do not guess.
2. **Title-based no-key literature lookup.**
   Only runs later when the agent supplied a confident `--title`; `/ingest` may use it for Crossref metadata enrichment.

## Invocation

Once you have the title (possibly empty), run:

```bash
"$PYTHON_BIN" tools/prepare_paper_source.py \
  --raw-root raw \
  --source <pdf-path> \
  [--title "<agent-recovered-title>"]
```

- Pass `--title` only when the agent is confident. Do not pass a title derived from PDF metadata or from the filename — those poison the literature enrichment lookup.
- Omit the flag when no title is confident. The helper falls back cleanly.

The helper writes the prepared entry under `wiki/sources/papers/` and prints a JSON record with:

| Field | Meaning |
|-------|---------|
| `canonical_ingest_path` | the prepared `.md` `/ingest` should consume |
| `prepared_path` | same path; kept for parity with the OmegaWiki contract |
| `ingest_format` | always `mineru-md` for this pipeline |
| `title` | best title (agent-supplied > MinerU-detected > filename stem) |
| `abstract_excerpt` | first ~400 chars after the abstract heading |
| `warnings` | non-fatal anomalies (no abstract found, no figures detected, etc.) |
| `usable` | boolean — `false` blocks ingest |

Use `canonical_ingest_path` as the source for the rest of `/ingest`.

## Title authority

When the agent supplied a confident title, treat that title as authoritative for the paper page's `title` field. Titles detected by MinerU's cover-page heuristics are fallback display strings only; do not let them overwrite the agent title. The agent-recovered title is what drove the successful literature lookup; letting a parsed cover title overwrite it creates subtle identity drift.

## Reading the prepared output

The prepared `.md` looks like:

```markdown
---
title: "..."
source: "raw/papers/<file>.pdf"
ingestedAt: "2026-05-06T..."
totalPages: 24
totalChars: 87412
sections:
  - {level: 1, title: "Introduction", line: 12}
  - {level: 2, title: "Related work", line: 84}
  - ...
figures:
  - {id: "fig-1", path: "assets/<slug>/abc123.jpg", caption: "..."}
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

## Output

A successful preprocessing pass produces:

- `wiki/sources/papers/<slug>.md` — frontmatter + cleaned body
- `wiki/sources/papers/assets/<slug>/<hash>.jpg` — only the figures that survived the cut

From this point on, treat the prepared `.md` as the canonical source for the rest of `/ingest`. Do not re-copy the PDF into `raw/papers/`; the original path remains the user-owned artifact.

Legacy compatibility: older worktrees may still reference `raw/tmp/papers/*.md`. Treat those files as readable prepared sources, but all newly generated prepared markdown must be written under `wiki/sources/papers/`.

## Failure modes

- **`MINERU_API_TOKEN is not set`**: surface this clearly to the user. Either ask them to add the token to `~/.config/llm-wiki/.env`, or fall back to the local MinerU backend if installed (`uv sync --extra local`).
- **MinerU API outage / rate limit**: same fallback — try the local backend if available, otherwise hand off to the user with a clear message.
- **Manifest reports `usable: false`**: do not proceed. Surface the `warnings` array to the user; common causes are scanned PDFs without OCR, encrypted PDFs, or pages-only image dumps.
- **No figures extracted on a paper that clearly has them**: not blocking. Note in the report; the user may want to switch to the local backend for that paper.

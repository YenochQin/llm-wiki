---
name: ingest-light
description: Lightly ingest background or dissertation-introduction papers into the wiki without expanding the full concept/claim/people graph. Use when the user wants many papers added for thesis introduction, related-work background, bibliography scaffolding, or narrative context rather than deep knowledge-graph extraction.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>| <prepared-source-path>) [--role background|method-foundation|benchmark|application|gap-evidence|review-context] [--depth light|paper-only] [--target-summary thesis-introduction-literature]"
---

# /ingest-light

Light ingest is for papers whose main purpose is dissertation-introduction or background narrative support. It creates a useful paper page and connects it to a writing-purpose Summary page, but it does **not** default to creating concepts, claims, people pages, or semantic graph edges.

Use `/ingest` instead when the paper is core evidence for reusable concepts/claims or should become part of the main research graph.

## References

- `references/light-paper-page.md` — required paper-page shape and tags for light ingest.
- `references/role-selection.md` — choose the primary introduction role when the user did not specify one or when the role is ambiguous.
- `references/summary-update.md` — how to update `wiki/Summary/<target-summary>.md`.
- `/ingest` references may be consulted for Zotero PDF preprocessing and BibTeX rules, especially `../ingest/references/pdf-preprocessing.md`.

Open `docs/runtime-page-templates.en.md` before writing the paper page frontmatter.

## Inputs

- Zotero-backed lookup by `--doi <doi>` or `--title <str>`, optionally with `--zotero-root <dir>`.
- Prepared source path only when handed off from `/ingest-local-pdf`, `/init`, or explicitly provided by the user.
- `--role` controls why the paper is in the introduction corpus:
  - `background`: broad motivation or domain context.
  - `method-foundation`: method/theory/platform foundation.
  - `benchmark`: experimental or reference-data comparison.
  - `application`: astrophysics, plasma, laser spectroscopy, clocks, nuclear-structure, databases.
  - `gap-evidence`: missing data, disagreement, incomplete assignments, or data-quality need.
  - `review-context`: survey/review/book/chapter used for framing.
- `--depth light` is the default: create/update a light paper page and target Summary.
- `--depth paper-only` creates/updates the paper page but does not add the paper to the target Summary.
- `--target-summary` defaults to `thesis-introduction-literature`.

Do not accept `--item-key` as a user-facing selector. Internal Zotero metadata enrichment may call `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>` only after DOI/title lookup selected an unambiguous candidate.

Never pass DOI or title directly to `tools/fetch_zotero_metadata.py`; that helper only accepts `--item-key` (or `--ping`). For DOI/title-based Zotero lookup, first run `tools/find_zotero_pdf.py --doi <doi>` or `--title "<title>"`, select an unambiguous candidate, then call `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>`.

If the user omits `--role`, read `references/role-selection.md`, infer one primary role from the paper metadata/source, and state the role choice and one-sentence rationale in the final report. If the role cannot be inferred from available information, ask the user instead of guessing.

## Outputs

For Python tools, pass aliases such as `@configured` and `@configured-sources-papers` directly. For direct file reads/writes through editor tools, first resolve the alias with `tools/resolve_path_alias.py` and then use the absolute path. Never create literal directories named `@configured` or `@raw-root`.

- `<resolved-wiki-root>/papers/{slug}.md` — CREATE or UPDATE as a light paper page.
- `<resolved-wiki-root>/sources/papers/{source-slug}.md` — created when a Zotero PDF must be prepared through `tools/prepare_paper_source.py`.
- `<resolved-wiki-root>/Summary/{target-summary}.md` — UPDATE unless `--depth paper-only`.
- `<resolved-wiki-root>/index.md` — rebuild or append through `tools/research_wiki.py rebuild-index`.
- `<resolved-wiki-root>/log/` — append via `tools/research_wiki.py log`.

No default writes to:

- `<resolved-wiki-root>/concepts/`
- `<resolved-wiki-root>/claims/`
- `<resolved-wiki-root>/people/`
- `<resolved-wiki-root>/graph/edges.jsonl`
- `<resolved-wiki-root>/graph/citations.jsonl`

## Workflow

**Pre-condition**: run from the repository root and use runtime path aliases. Do not hard-code `wiki/`, `raw/`, or external vault paths.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@configured-sources-papers'
```

If path diagnosis is needed, use `uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@raw-root' '@configured-sources-papers' '@mineru-cache'`. Do not import path helpers from `tools._env`; runtime path aliases are resolved by `tools/_paths.py` through this CLI.

Never pass literal relative output paths such as `wiki/sources` or `wiki/sources/papers`; these resolve inside the code repository when the wiki is split into an external vault. Use `@configured`, `@configured-sources`, and `@configured-sources-papers`.
Never pass `@configured/...` or `@raw-root/...` to direct file editing tools or plain shell commands such as `cat`, `cp`, `mkdir`, or redirection. They do not resolve aliases and will create literal directories in the code repository.

### Step 1: Resolve and prepare source

1. If the input is a prepared `@configured-sources-papers/*.md`, read it directly.
2. If the input is DOI/title, follow the Zotero lookup/preparation flow from `/ingest` Step 1:
   - call `tools/find_zotero_pdf.py` with `--doi` or `--title`;
   - select only an unambiguous candidate with exactly one existing PDF attachment;
   - set `<selected-pdf-path>` to the candidate's `best_attachment.path` when present, otherwise its single `pdf_paths[0]`;
   - fetch Zotero metadata with internal `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>` when available; do not call `tools/fetch_zotero_metadata.py --doi` or `--title`, which are not supported CLI options;
   - run `tools/prepare_paper_source.py` with explicit `--source <selected-pdf-path>`, `--output-dir '@configured-sources-papers'`, and `--cache-root '@mineru-cache'`.
3. Preserve Zotero `metadata.paper_slug` or prepared frontmatter `paperSlug` as the paper slug. Use `tools/research_wiki.py paper-slug` only when no citation key is available.
4. Stop if preparation reports `usable: false`. Do not read `full.md`, MinerU cache files, or other intermediate cache artifacts as a substitute canonical source. A non-empty MinerU cache with `usable: false` means the adapter/filtering layer needs to be fixed or the failure must be reported to the user.

Correct preparation command shape:

```shell
uv run python -X utf8 tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source '<selected-pdf-path>' [--title '<zotero-title>'] [--citation-key '<zotero-citation-key>'] [--authors '<author-list>'] [--year "<year>"] [--bibtex "$BIBTEX"]
```

Use single quotes around Zotero-derived PDF paths and metadata values in shell commands. Some Zotero filenames contain `$` or TeX math such as `$$^{143-147}$$`; double quotes allow Bash to expand `$$` into the process id and corrupt the path.

Never pass Zotero `item_key` to `tools/prepare_paper_source.py`. `item_key` is only for `tools/fetch_zotero_metadata.py`; MinerU preparation requires a real local PDF path via `--source`. Never pass `.mineru-cache` as `--cache-root`; use `@mineru-cache`, which resolves to `.checkpoints/mineru-cache`.

### Step 2: Create or update the light paper page

Follow `references/light-paper-page.md`.
If `--role` was omitted or ambiguous, follow `references/role-selection.md` before writing.

Requirements:

- Frontmatter includes normal paper fields plus tags containing `thesis-introduction`, the selected role, and `light-ingest`.
- `paper_type`, `research_modes`, and `research_object_tags` should be filled conservatively when clear; otherwise use `other` / `[]` / `[]` rather than inventing.
- Body sections stay light: Problem, Key idea, Research classification, Introduction use, Evidence notes, Limitations, BibTeX, Related.
- `## Introduction use` must include the selected primary role and the reason this paper belongs in that role. Mention secondary roles there only when useful.
- `## Related` must include `[[{target-summary}]]` unless `--depth paper-only`.
- Do not create new concept/claim/people pages. Link existing pages only when clearly useful.

If `<resolved-wiki-root>/papers/{slug}.md` already exists, update only light-ingest metadata/sections that are missing or stale. Do not overwrite a full `/ingest` page with a lighter page.

### Step 3: Update the target Summary

Skip this step for `--depth paper-only`.

Follow `references/summary-update.md`.

Add the paper under a role-based subsection in `<resolved-wiki-root>/Summary/{target-summary}.md`, preserving existing prose. If the target Summary does not exist, create it using the Summary template with a concise scope and the required sections.

### Step 4: Navigation and log

Run:

```shell
uv run python -X utf8 tools/research_wiki.py rebuild-index '@configured'
uv run python -X utf8 tools/research_wiki.py log '@configured' "ingest-light | added papers/<slug> | role=<role> | target=Summary/<target-summary>"
```

### Step 5: Scoped verification

Run scoped lint only on touched files:

```shell
uv run python -X utf8 tools/lint.py --wiki-dir '@configured' --only "papers/{slug}.md" --only "Summary/{target-summary}.md"
```

Do not report unrelated full-wiki lint debt.

## Upgrade path

If a light-ingested paper later becomes core evidence, run `/ingest` or `/reingest` on the same paper slug and explicitly upgrade it to full graph participation. Preserve `thesis-introduction` tags and the Summary link unless the user asks to remove them.

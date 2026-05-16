---
description: Lightly ingest background or dissertation-introduction papers into the wiki without expanding the full concept/claim/people graph. Use when the user wants many papers added for thesis introduction, related-work background, bibliography scaffolding, or narrative context rather than deep knowledge-graph extraction.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>| <prepared-source-path>) [--role background|method-foundation|benchmark|application|gap-evidence|review-context] [--depth light|paper-only] [--target-summary thesis-introduction-literature]"
---

# /ingest-light

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key 和 wikilink 语法保持原样。

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

If the user omits `--role`, read `references/role-selection.md`, infer one primary role from the paper metadata/source, and state the role choice and one-sentence rationale in the final report. If the role cannot be inferred from available information, ask the user instead of guessing.

## Outputs

- `@configured/papers/{slug}.md` — CREATE or UPDATE as a light paper page.
- `@configured/sources/papers/{source-slug}.md` — created when a Zotero PDF must be prepared.
- `@configured/Summary/{target-summary}.md` — UPDATE unless `--depth paper-only`.
- `@configured/index.md` — rebuild or append through `tools/research_wiki.py rebuild-index`.
- `@configured/log.md` — append via `tools/research_wiki.py log`.

No default writes to:

- `@configured/concepts/`
- `@configured/claims/`
- `@configured/people/`
- `@configured/graph/edges.jsonl`
- `@configured/graph/citations.jsonl`

## Workflow

**Pre-condition**: run from the repository root and use runtime path aliases. Do not hard-code `wiki/`, `raw/`, or external vault paths.

```bash
uv run python tools/research_wiki.py stats @configured --json >/dev/null
```

### Step 1: Resolve and prepare source

1. If the input is a prepared `@configured-sources-papers/*.md`, read it directly.
2. If the input is DOI/title, follow the Zotero lookup/preparation flow from `/ingest` Step 1:
   - call `tools/find_zotero_pdf.py` with `--doi` or `--title`;
   - select only an unambiguous candidate with exactly one existing PDF attachment;
   - fetch Zotero metadata with internal `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>` when available;
   - run `tools/prepare_paper_source.py` with explicit `--output-dir @configured-sources-papers` and `--cache-root @mineru-cache`.
3. Preserve Zotero `metadata.paper_slug` or prepared frontmatter `paperSlug` as the paper slug. Use `tools/research_wiki.py paper-slug` only when no citation key is available.
4. Stop if preparation reports `usable: false`.

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

If `@configured/papers/{slug}.md` already exists, update only light-ingest metadata/sections that are missing or stale. Do not overwrite a full `/ingest` page with a lighter page.

### Step 3: Update the target Summary

Skip this step for `--depth paper-only`.

Follow `references/summary-update.md`.

Add the paper under a role-based subsection in `@configured/Summary/{target-summary}.md`, preserving existing prose. If the target Summary does not exist, create it using the Summary template with a concise scope and the required sections.

### Step 4: Navigation and log

Run:

```bash
uv run python tools/research_wiki.py rebuild-index @configured
uv run python tools/research_wiki.py log @configured "ingest-light | added papers/<slug> | role=<role> | target=Summary/<target-summary>"
```

### Step 5: Scoped verification

Run scoped lint only on touched files:

```bash
uv run python tools/lint.py --wiki-dir @configured --only "papers/{slug}.md" --only "Summary/{target-summary}.md"
```

Do not report unrelated full-wiki lint debt.

## Upgrade path

If a light-ingested paper later becomes core evidence, run `/ingest` or `/reingest` on the same paper slug and explicitly upgrade it to full graph participation. Preserve `thesis-introduction` tags and the Summary link unless the user asks to remove them.

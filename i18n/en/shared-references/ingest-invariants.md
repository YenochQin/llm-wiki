# Ingest Invariants (single source of truth)

> Cross-cutting micro-rules shared by every ingest-family skill (`/ingest`, `/reingest`, `/ingest-light`, `/ingest-local-pdf`, `/init`). Each rule is defined **once, here**. Skills and phase files point to this file instead of restating these rules. If a rule changes, it changes here only.

These invariants always hold, in every phase, in every ingest-family skill. A phase Gate may re-check an invariant, but never redefines it.

## 1. Path and environment discipline

- Run all commands from the repository root. Run Python tools through `uv run python -X utf8 tools/<name>.py …`.
- Never hard-code `wiki/` or `raw/`. Use runtime path aliases: `@configured`, `@raw-root`, `@configured-sources`, `@configured-sources-papers`, `@mineru-cache`.
- Path aliases are resolved **only** by Python tools that support `tools/_paths.py`. For direct file edits / `cat` / `cp` / `mkdir` / shell redirection, first run `uv run python -X utf8 tools/resolve_path_alias.py '<alias>'` and use the absolute path. Never create a literal directory named `@configured` or `@raw-root`.
- `@configured` must resolve to the wiki vault root, not the code repository root. `tools/research_wiki.py` rejects the code repo root.
- Diagnose paths with `uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@raw-root' '@configured-sources-papers' '@mineru-cache'`. Do not import path helpers from `tools._env`.
- In PowerShell, quote aliases that start with `@` (e.g. `'@configured'`); a bare `@configured` is parsed as splatting.

## 2. Zotero discipline

- `--item-key` is **internal only**. Never expose or accept it as a user-facing paper selector in any ingest-family skill.
- DOI/title lookup flow: `tools/find_zotero_pdf.py --doi <doi>` or `--title "<title>"` → select an **unambiguous** candidate (exactly one existing PDF attachment, match reason `doi` / `exact-title` / clearly unambiguous title / filename-like match) → only then call `tools/fetch_zotero_metadata.py --item-key <candidate.item_key>` for enrichment.
- Never pass DOI or title to `tools/fetch_zotero_metadata.py`; it accepts only `--item-key` (or `--ping`).
- Metadata alone is **not** a content source. With no PDF / prepared markdown / notes / web content, do not create a paper page.
- When `--zotero-root` is omitted, read the active profile's `zotero_roots` in `config/paths.json`.

## 3. Slug derivation

- **Paper pages**: use `metadata.paper_slug` from `tools/fetch_zotero_metadata.py` when non-empty; else the prepared source frontmatter `paperSlug`/`sourceSlug` when non-empty. Only when neither exists, fall back to `tools/research_wiki.py paper-slug "<title>" --citation-key "<key-or-empty>" --authors "<authors>" --year "<year>" --bibtex "<bibtex-or-empty>"` (which yields `author_year_veryshorttitle`).
- **Non-paper pages** (concepts, claims, people, topics, ideas, experiments, outputs): `tools/research_wiki.py slug "<title>"`.
- Never hand-craft a slug.
- Collisions: see `.claude/skills/ingest/references/error-handling.md`. A paper slug colliding with a *different* paper → stop and report. A concept/claim slug colliding with a different existing page within one ingest → numeric suffix via the tool's built-in handling.

## 4. LaTeX

- Inline math `$...$`; display math `$$...$$`. This is the Obsidian rendering standard.
- Never use code fences for equations and never use `\(...\)` / `\[...\]`.
- PDF-derived prepared sources already passed `tools/repair_latex_math.py`. If a copied formula is still visibly broken, repair the math span itself; do not carry OCR-spaced commands (`\ alpha`, `_ {i}`, `^ {2}`, `\left (`) onto the page, and do not replace formal notation with vague prose or ASCII pseudocode.
- When copying equations or formal statements from a prepared source into Evidence Pack cards, copy the complete meaning-preserving unit. Do not truncate long display equations, multi-line `aligned` / `split` / `cases` blocks, definitions, theorem statements, algorithm steps, or derivation lines and then use the partial quote as evidence. If a full formula is too long for a card, cite the equation label/section and keep the card descriptive rather than using a shortened formula as formal support.
- A leading `>` in an Evidence Pack quote is Markdown blockquote syntax, not part of the LaTeX. Keep quote markers outside math content: for a `$$...$$` display-math block, only the opening `$$` line may carry the quote marker; formula continuation lines and the closing `$$` line must not start with `>` after list indentation, because some renderers treat that marker as formula content. If an equation is inline within an already quoted sentence, do not add an extra `>` immediately before the formula.

## 5. Wikilinks and source links

- Internal links are **slug-only**: `[[slug]]`. Never directory-prefixed: no `[[wiki/...]]`, `[[topics/slug]]`, `[[wiki_glm/...]]`, etc.
- Only wikilink paper slugs that already exist under `@configured/papers/` or are created in the same run. An un-ingested bibliography paper stays plain text with title/DOI/year and `not yet ingested`; never a dangling `[[paper-slug]]`.
- Prepared source excerpts use ordinary relative markdown links: `[prepared markdown](../sources/papers/<source-slug>.md)`.

## 6. BibTeX

- BibTeX lives in the paper body under `## BibTeX` as a fenced ```bibtex code block. **Never** in YAML frontmatter. Never route ingest through `.bib` sidecars.
- Citation-core fields only: entry type, citekey, `author`, `title`, `year`, one venue field (`journal`/`booktitle`/`publisher`/`school`/`institution`/`howpublished`), `volume`, `number`, `pages`, `doi`. No URL, tags/keywords, abstract, language, or rights.

## 7. Page shape and Evidence Pack are template-defined

- The Evidence Pack card shape, its citation syntax `[[#^E1]]`, the forbidden-variant list, the per-page frontmatter/body structure, the `## Source excerpts` shape, and the claim YAML provenance shape are all defined **once** in `docs/runtime-page-templates.en.md`. Emit per that template; do **not** restate the ASCII shapes in skill or phase prose.
- Evidence Pack `short_label` fields carry the refined meaning of the source block. Evidence Pack `excerpt` fields are compact exact anchors for locating the original evidence, not whole-paragraph or whole-subsection copies. Preserve complete formal units only when the formal unit itself is the necessary anchor; otherwise anchor long formulas/tables by a short source sentence plus label/section and keep the full source in prepared markdown.
- claim YAML provenance is structured data: `source_papers` and `evidence[].source` are paper slugs only; `evidence[].source_anchor` is the Evidence Pack id only (`E1`). Never put `[[...]]`, `#`, `^`, or `[[#^E1]]` in claim YAML.

## 8. Paper `## Related` section

- Every generated or regenerated `papers/{slug}.md` page must end with exactly one `## Related` section.
- `## Related` contains wikilinks only to pages that already exist or are created in the same run. Never link not-yet-ingested bibliography items, follow-up candidates, external URLs, DOIs, raw notes, prepared sources, or graph files here.
- Use only these bullet labels, in this order, omitting empty labels: `Concepts`, `Claims`, `Foundations`, `Papers`, `Topics`, `People`, `Summary`.
- Bullet shape is fixed: `- <Label>: [[slug-a]], [[slug-b]]`. Do not add prose explanations, evidence text, citation anchors, parentheticals, confidence notes, or nested bullets.
- Sort slugs alphabetically within each label. Do not duplicate a slug across labels.
- Put paper-paper related work only under `Papers`, and only when the linked paper page exists or is created in the same run. Queue not-yet-ingested related work in `outputs/ingest-candidates.md` instead.
- `/ingest-light` may include the target Summary link under `Summary` unless `--depth paper-only`; it must still follow the same bullet shape.

## 9. Graph edge invocation contract

- Always: `uv run python -X utf8 tools/research_wiki.py add-edge '@configured' --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`.
- The first argument after `add-edge` **must** be `'@configured'`. Never start with `add-edge --from`.
- Use named flags only; no positional `<paper> <type> <concept>`.
- paper-concept and paper-paper **semantic** edges require both `--evidence` (short, source-grounded) and `--confidence`. Symmetric paper-paper types are canonicalized and stored once with `symmetric: true`.
- Bibliographic citations go to `citations.jsonl` via `add-citation`, separate from semantic edges; not every citation becomes a semantic edge.

## 10. Scope boundary with `/check`

- Ingest-family skills emit well-shaped entities and correct forward/reverse links at write time, and run a narrow **shape check** (required keys, enum ranges, YAML parses) plus a **scoped** `grounding_lint.py --only` / `lint.py --only` on touched files.
- Backlink symmetry across the whole wiki, dangling-node detection, cross-entity consistency, edge dedup, and full-wiki lint counts belong to `/check`. Never run or report a full-wiki audit inside an ingest.

---
description: Ingest a Zotero-backed paper into the wiki — creates pages (papers + concepts + people + claims) and builds all cross-references and graph edges. Trigger whenever the user says "ingest", "add this paper", or asks to fold a Zotero-backed paper into the knowledge base.
argument-hint: "[--zotero-root <dir>] (--title <str>|--doi <doi>|--item-key <key>) [--discover]"
---

# /ingest

Turn one paper into a fully wired set of wiki pages. Emit well-formed entities and correct cross-references; leave semantic audits (backlink symmetry, dangling nodes, field-value policing) for `/check`.

Use these local references on demand:

- `references/pdf-preprocessing.md` — MinerU pipeline + prepare-paper handoff for Zotero-selected PDFs; describes the `mineru-md` output format the rest of `/ingest` consumes
- `references/dedup-policy.md` — merge-vs-create decision rule for concepts and claims, and the line that separates `/ingest` shape checks from `/check` semantic audits
- `references/cross-references.md` — forward/reverse link matrix and paper-to-paper edge-type selection
- `references/init-mode.md` — manifest-driven handoff from `/init` and parallel-safety conventions
- `references/error-handling.md` — source parse, API, and slug-collision fallbacks

Open `docs/runtime-page-templates.en.md` before drafting any wiki page frontmatter or body sections, and `docs/runtime-support-files.en.md` for `index.md`, `log.md`, and `graph/` formats.

## Inputs

- `source`: Zotero lookup arguments. Prepared `@configured-sources-papers/*.md` and `canonical_ingest_path` values are internal handoffs from `/ingest-local-pdf` or `/init` only (see `references/init-mode.md`). The prepared format is `mineru-md` — structured markdown with `sections`/`figures` frontmatter.
- Existing MinerU Markdown may be consumed only when handed off by `/ingest-local-pdf` or `/init`; do not expose prepared markdown as a normal `/ingest` user-facing input.
- Optional reference metadata usually comes directly from Zotero Local API when the source is a Zotero item; this includes Zotero/Better BibTeX fields such as `citationKey` and a derived `bibtex` entry that is compatible with the three `bibbst/` styles in this repo. Use that Zotero-derived `bibtex` string directly in the paper body under `## BibTeX`; never store BibTeX in YAML frontmatter and do not route `/ingest` through `.bib` or reference-metadata sidecars.
- Zotero lookup form: one or more of `--title <str>`, `--doi <doi>`, or `--item-key <key>`, optionally plus `--zotero-root <dir>`. If `--zotero-root` is omitted, read the selected profile's `zotero_roots` in `config/paths.json` and scan the listed Zotero data/profile directory candidates. A root may be the Zotero data directory containing `zotero.sqlite` and `storage/`, or a Zotero profile directory whose `prefs.js` points to the data directory.
- Zotero metadata enrichment is optional: after a Zotero lookup selects an `item_key`, try `tools/fetch_zotero_metadata.py --item-key <key>` to read richer metadata from Zotero Desktop's local API. If Zotero Desktop is closed or local API access is disabled, continue with the existing SQLite/Crossref path.
- Zotero metadata by itself is not a grounded source. If the user only provides metadata with no PDF, prepared Markdown, source note, or web/notes content, do not create a paper page; ask for a content source or record the metadata as a future ingest aid only when explicitly requested.
- `--discover` (optional, default **off**): after the final report, invoke `/discover --anchor <this-paper's-doi-or-title>` and append the shortlist to the report as "Related papers you may want to ingest next". Never auto-ingests the suggestions. Skipped automatically in INIT MODE. Treat this as a user-owned flag: do not set it based on repo state.

## Outputs

- One fully-wired paper page plus linked entities (concepts, claims, people)
- Graph edges and citations appended via `tools/research_wiki.py`
- Terminal summary with page counts and suggested follow-up ingests

## Wiki Interaction

### Reads

- `@configured/index.md` for existing slugs and tags
- `@configured/papers/*.md` to detect an already-ingested paper
- `@configured/concepts/*.md` and `@configured/foundations/*.md` for dedup matches
- `@configured/claims/*.md` for dedup matches
- `@configured/people/*.md` for existing authors
- `@configured/topics/*.md` to place the paper under existing topics
- `@configured/graph/open_questions.md` to notice when the paper addresses a known gap

### Writes

- `@configured/papers/{slug}.md` — CREATE
- `@configured/concepts/{slug}.md` — CREATE (new) or EDIT (append `key_papers`, aliases, variants)
- `@configured/claims/{slug}.md` — CREATE (new) or EDIT (append `evidence` entry)
- `@configured/people/{slug}.md` — CREATE (importance ≥ 4 only) or EDIT (append `Key papers`)
- `@configured/topics/{slug}.md` — EDIT only (no CREATE from `/ingest`)
- `@configured/graph/edges.jsonl` — APPEND via tool
- `@configured/graph/citations.jsonl` — APPEND via tool
- `@configured/graph/context_brief.md` — REBUILD (skipped in INIT MODE)
- `@configured/graph/open_questions.md` — REBUILD (skipped in INIT MODE)
- `@configured/index.md` — APPEND
- `@configured/log.md` — APPEND via tool

### Graph edges created

- `paper → concept`: `introduces_concept` / `uses_concept` / `extends_concept` / `critiques_concept` with `confidence`
- `paper → foundation`: `derived_from` (foundation is terminal; no reverse link)
- `paper → claim`: `supports` / `contradicts`
- `paper → paper`: `same_problem_as` / `similar_method_to` / `complementary_to` / `builds_on` / `compares_against` / `improves_on` / `challenges` / `surveys` with `confidence`
- bibliographic `paper → paper`: `cites` in `graph/citations.jsonl`

`tools/research_wiki.py add-edge` rejects missing confidence/evidence for
paper-paper and paper-concept semantic edges, and rejects legacy
paper-to-concept or paper-to-paper types on new writes.

## Workflow

**Pre-condition**: working directory is the project root containing `tools/`, `pyproject.toml`, and `config/paths.json`. Run Python tools through `uv run python`, matching `README.md`. Do not hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, `@raw-root`, `@configured-sources-papers`, and `@mineru-cache`. By default, `tools/_paths.py` loads `config/paths.json` and the documented `LLM_WIKI_*` overrides; only override these roots when the user explicitly requests it.

```bash
# Run all commands from the repository root; runtime paths are resolved by tool aliases.
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi
if [ -z "$PROJECT_ROOT" ]; then
  PROJECT_ROOT=$(pwd)
fi
cd "$PROJECT_ROOT"

uv run python tools/research_wiki.py stats @configured --json >/dev/null
```

`@configured` must resolve to the actual wiki vault root, not the code repository root. `tools/research_wiki.py` rejects the code repository root to prevent accidental creation of root-level `graph/`, `index.md`, or `log.md`.

### Step 1: Resolve the source

1. If `/init` passed a `canonical_ingest_path`, enter **INIT MODE** and consume that path verbatim. Do not rescan `@raw-root`. See `references/init-mode.md`.
2. If the source is a prepared `@configured-sources-papers/*.md`, use it directly.
3. If the user supplied Zotero lookup arguments, run:

   ```bash
   uv run python tools/find_zotero_pdf.py \
     [--zotero-root <dir>] \
     [--title "<title>"] [--doi <doi>] [--item-key <key>]
   ```

   If `--zotero-root` is omitted, the helper scans `config/paths.json`; use `--zotero-config <path>` only when the user explicitly names an alternate config. Pick the top candidate only when it has exactly one existing PDF attachment and the match reason is `item-key`, `doi`, `exact-title`, a clearly unambiguous title match, or a filename-like attachment match. Otherwise report the candidates and ask the user to choose. For chapter-split books, prefer the attachment whose path or filename matches the chapter PDF name. Keep the selected candidate's `citation_key`, `creators`, `year`, and PDF path for preprocessing. Do not copy it into `@raw-root/papers/`.
4. If the selected Zotero candidate has an `item_key`, try:

   ```bash
   uv run python tools/fetch_zotero_metadata.py --item-key <key>
   ```

   Treat a successful response as authoritative bibliographic metadata from the user's local library. Use it to prefer `title`, `doi`, `year`, `venue`, `creators`/authors, `abstract`, `tags`, `url`, `zotero_select`, `citationKey`/`citekey`, `external_ids.zotero_key`, and the returned `bibtex` string. If the command fails, note the fallback only if it affects the report; do not block ingest.
5. Preprocess Zotero PDFs with `tools/prepare_paper_source.py` using the selected candidate's SQLite `citation_key` when present; otherwise pass Zotero Local API `citationKey`/`citekey`, authors, year, title, and BibTeX metadata so the prepared source filename can fall back to `author_year_veryshorttitle`. This preprocessing includes the conservative LaTeX math repair pass and may report `latex math repaired: ...` in its warnings. Carry the Zotero-derived `bibtex` string into the body of both the prepared source markdown and `@configured/papers/{slug}.md` under a `## BibTeX` fenced `bibtex` code block. Do not put `bibtex` in frontmatter. Keep it as plain BibTeX so the three `bibbst/` styles (`gbt7714-numerical.bst`, `apsrev4-2.bst`, `elsarticle-num.bst`) can consume it directly. The derived BibTeX entry must stay citation-core only: entry type, citekey, `author`, `title`, `year`, one venue field (`journal`/`booktitle`/`publisher`/`school`/`institution`/`howpublished`), `volume`, `number`, `pages`, and `doi`; do not include URL, tags/keywords, abstract, language, or rights in the BibTeX block. Do not route `/ingest` through `.bib` or reference-metadata sidecars.

Raw persistence rule: never copy or duplicate a file already under `@configured-sources/` or `@raw-root/papers/` into a different raw subtree.

### Step 2: Paper identity and enrichment

1. Generate the paper slug:

   ```bash
   uv run python tools/research_wiki.py slug "<paper-title>"
   ```

2. Stop-if-exists: if `@configured/papers/{slug}.md` already exists and the title or DOI matches, report and exit. If they differ, resolve the collision per `references/error-handling.md`.
3. When Zotero Local API metadata is available, prefer it for identity fields (`title`, `doi`, `year`, `venue`, authors/creators, abstract, tags, URL, `citationKey`/`citekey`, and `external_ids`) and use the derived `bibtex` string only for the body `## BibTeX` block.
4. When a DOI or confident title is available, query the no-key literature lookup:

   ```bash
   uv run python tools/fetch_literature.py paper <doi-or-title>
   ```

   Use the result for `venue`, `year`, `external_ids`, citation count when available, and the evidence behind the `importance` score (1-5). If citation counts are unavailable, default `importance` to 3 and mark it provisional.
5. Merge bibliographic metadata conservatively: Zotero wins for user-curated identity fields; Crossref may fill missing `external_ids`, venue/year gaps, and citation-derived importance evidence; MinerU remains the source of record for paper content and section structure.
6. Use the `mineru-md` frontmatter (`sections`, `figures`, `abstract_excerpt`) as your structural anchor when summarizing. The frontmatter already gives you a clean section list and figure inventory; do not re-parse the body to recover them.
7. Before drafting the paper page, classify the source form:
   - `paper_type`: choose one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`. Use `review` for review/survey articles, but do not put `review` in `research_modes`.

### Step 3: Write the paper page

Open `docs/runtime-page-templates.en.md` for the paper template. Fill every required frontmatter field; leave `cited_by` empty for now (step 5 backfills it).

Before writing, run a **shape check** on the frontmatter you are about to emit — no more than this:

- every required key is present and non-empty, including `paper_type`
- `importance` ∈ {1,2,3,4,5}; `status` on claims ∈ the documented set; `maturity` on concepts ∈ the documented set; claim `confidence` ∈ [0,1]
- `paper_type` is one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`
- YAML parses

The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job, not this skill's.

Body sections to populate: Problem, Key idea, Method, Results, Limitations, Open questions, My take, Related.

For mathematical or technical papers, keep important equations in LaTeX. Use `$...$` for inline math and `$$...$$` for display math. PDF-derived prepared sources should already have passed `tools/repair_latex_math.py`; if a copied formula is still visibly broken, repair the math span itself instead of carrying OCR-spaced commands such as `\ alpha`, `_ {i}`, `^ {2}`, or `\left (` into the page. Do not use code fences for equations or `\(` `\)` notation.

Wikilinks must be vault-local slug links: write `[[slug]]`, never `[[wiki/...]]`, `[[wiki_glm/...]]`, `[[wiki_back.../...]]`, `[[topics/slug]]`, or any other directory-prefixed wikilink. Use ordinary relative markdown links only for prepared source excerpts, e.g. `[prepared markdown](../sources/papers/<source-slug>.md)`.

### Step 4: Concepts, claims, people

Follow `references/dedup-policy.md`. In short:

**Research-direction anchor (optional but preferred)**: before drafting any concept's `## My understanding` section, check whether `@configured/Summary/research-direction.md` exists. If it does, read it and use the listed direction(s) as the anchoring context for the synthesis. Treat the file as guidance, not as a license to fabricate a connection the source paper cannot support. If the file is absent, write a generic maintainer-voice synthesis and note that the anchor file was not found.

1. For each candidate concept or claim, call the matching `find-similar-*` tool first.
2. Prefer merging into the top result. Create a new page only when the tool returns no acceptable candidate and the paper's importance justifies it.
3. For each entity you write or edit, write the reverse link in the same turn. The obligation matrix lives in `references/cross-references.md`.
4. Create a `@configured/people/{slug}.md` only for papers with importance ≥ 4. Otherwise append to existing author pages only.
5. For every paper with importance ≥ 4, create or update at least one claim. A missing `claims/` layer for a high-importance paper is a failed ingest unless the source is purely bibliographic, editorial, or otherwise has no defensible claim; record that exception in the log and final report.
6. For every concept page created or materially edited, add or refresh `## Source excerpts`: one short exact original-language blockquote per grounding paper, each linked to that paper's actual prepared MinerU markdown (`../sources/papers/<source-slug>.md`, derived from `canonical_ingest_path` or prepared frontmatter `sourceSlug`). If the prepared markdown is missing, record `prepared markdown: missing` and the fallback source used.
7. For every concept page created or materially edited, `## My understanding` must include **at least one concrete connection sentence** tying the concept to the user's active research direction(s) declared in `@configured/Summary/research-direction.md` — e.g. how the concept appears in that direction, what role it plays (descriptor feature, computational bottleneck, validation benchmark, …). Only omit the connection if the source paper genuinely cannot defend one; in that case write a one-line scoped reason instead of forcing a generic tie-in. If the anchor file is absent, add `_no research-direction anchor file found_` on its own line.

### Step 5: Paper-to-paper edges and `cited_by`

Skip this whole step in INIT MODE — the parent `/init` handles it at fan-in.

```bash
uv run python tools/fetch_literature.py references <doi-or-title>
uv run python tools/fetch_literature.py citations <doi-or-title>
```

- For each reference whose DOI or title resolves to an existing `@configured/papers/{slug}.md`, add a bibliographic `cites` row to `graph/citations.jsonl`.
- Add a semantic paper-to-paper edge in `graph/edges.jsonl` only when the source text gives a clear cue. Edge-type selection is in `references/cross-references.md`. If no semantic relation cleanly fits, keep only the `cites` row.
- For each citation already in the wiki, append the citer's slug to this paper's `cited_by`.
- Surface unmatched high-citation references in the final report so the user can decide whether to follow up with another `/ingest`.

### Step 6: Topics and index

1. Match the paper's domain and tags against existing `@configured/topics/*.md`. For each match:
   - importance ≥ 4 → append to the topic's `## Seminal works`
   - importance < 4 → append under `## SOTA tracker` or `## Recent work` by year
   - if the paper directly addresses a listed open problem, annotate that line on the topic page
   - record the matched topic count `N` for the Step 8 report
2. Do not create new topic pages from `/ingest` — topic creation belongs to `/init` and `/edit`. If `N=0`, surface this in the Step 8 report with a one-line suggestion to run `/edit` and create a topic page for the paper's domain. Do not silently leave `topics/` empty.
3. Match the paper against existing `@configured/Summary/*.md`. If a Summary page's `scope`, `key_topics`, or overview clearly covers the paper, append the paper under `## Key References` or `## Related` and record the matched Summary count `S`. Do not create Summary pages from `/ingest`; if `S=0`, surface it in the report with the topic-placement note.
4. Append new or edited page entries to `@configured/index.md` under their category headings. See `docs/runtime-support-files.en.md` for the exact format.

### Step 7: Log and rebuild

```bash
uv run python tools/research_wiki.py log @configured "ingest | added papers/<slug> | updated: <list>"
```

Unless in INIT MODE:

```bash
uv run python tools/research_wiki.py rebuild-context-brief @configured
uv run python tools/research_wiki.py rebuild-open-questions @configured
```

### Step 8: Report

Emit one compact summary covering: pages created, pages updated, graph edges added, topic/Summary placement (`Topic placement: matched N topics; Summary placement: matched S summaries` — if `N=0`, append a one-line suggestion to run `/edit` and create a topic page for the paper's domain; if `S=0`, suggest adding or updating a Summary page), contradictions surfaced (if any), and high-citation references not yet in the wiki (suggested follow-up ingests). Close with:

```
Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges
```

**Self-check** (run before finalizing the report):
1. `@configured/papers/{slug}.md` exists and frontmatter YAML parses.
2. At least one concept page was created or materially updated; each new/edited concept page has `## Source excerpts` and `## My understanding`.
3. At least one claim exists for importance ≥ 4 papers, or the report names the exception.
4. `@configured/graph/edges.jsonl` has at least one edge involving the new paper.
5. `@configured/log.md` has a new `## [today]` entry.
6. `@configured/index.md` includes the new paper and all new entities.
7. LaTeX in all written pages uses `$`/`$$` exclusively — no code-fence equations, no `\(` `\)`.
8. Every `[prepared markdown](../sources/papers/<source-slug>.md)` link written by this ingest resolves to an existing file with size > 0 bytes. If any target is missing or empty, the prepared MinerU markdown got wiped after preparation — surface the missing source slugs in the report and stop instead of shipping dead links. (If a concept page truly has no source backing, it must use the documented `prepared markdown: missing` fallback wording, not a live link to an empty file.)
9. For every concept page created or materially updated, `## My understanding` either contains the research-direction connection sentence required in Step 4 item 7, or contains a one-line scoped reason for omission, or notes that `@configured/Summary/research-direction.md` was not found.
10. No written page contains directory-prefixed wikilinks such as `[[wiki/...]]`, `[[wiki_glm/...]]`, `[[wiki_back.../...]]`, or `[[topics/slug]]`. If Obsidian later rewrites links for disambiguation, report that as an external post-ingest change; `/ingest` itself must emit slug-only wikilinks.

If any check fails, fix it before emitting the report.

### Step 9: Optional discovery (only if `--discover` is set)

Skip this step unless the user explicitly passed `--discover`. Also skip it in INIT MODE — `/init`'s parent process decides whether to run discovery at fan-in, not individual subagents.

When active, invoke `/discover` with the just-ingested paper as the single anchor:

```bash
uv run python tools/discover.py from-anchors \
  --id <doi-or-title-of-this-paper> \
  --wiki-root @configured \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

Append the markdown output to the report under a heading like "Related papers you may want to ingest next". Do not auto-ingest anything from the shortlist — the user picks. If discovery fails (provider outage, all channels empty), note the failure in one line and continue — a failed `/discover` must not fail an otherwise successful `/ingest`.

## Constraints

- `@raw-root/papers/`, `@raw-root/notes/`, `@raw-root/web/` are user-owned and read-only. `/ingest` does not accept direct local PDF inputs; `/ingest-local-pdf` prepares local sidecars under `@configured-sources/`. INIT MODE treats all of `raw/` as read-only.
- `@configured/graph/` is tool-owned. Edit only through `tools/research_wiki.py`.
- Slugs always come from `tools/research_wiki.py slug`. Never hand-craft.
- Every forward link writes its reverse link in the same turn — the wiki's bidirectional-link invariant. The only exception is links to `@configured/foundations/`, which are terminal.
- In INIT MODE, do not write reverse links into pages that already exist (created by a sibling worktree or scaffold). Record the relationship via `tools/research_wiki.py add-edge` only; the parent `/init` backfills reverse links during fan-in.
- Source format: `mineru-md` is the canonical prepared format. `/ingest` consumes prepared markdown in `@configured-sources-papers/` or the INIT MODE handoff path; Zotero-selected PDFs are preprocessed through `tools/prepare_paper_source.py`, including its LaTeX math repair pass. Raw local PDFs are handled by `/ingest-local-pdf`. If preparation fails (unusable manifest with `usable: false`), surface the warnings to the user rather than proceeding.
- Metadata-only sources (Zotero metadata without an attachment/content source) cannot create a paper page. They may enrich a real content ingest, or be saved only when the user explicitly asks `/edit` to add a metadata note/source.
- Ingest is conservative about new entities:
  - importance < 4: at most **1** new concept and **1** new claim per paper
  - importance ≥ 4: at most **3** new concepts and **2** new claims per paper
  - Any further candidates must be merged into their nearest `find-similar-*` result, or left out for `/check` to flag. Rationale and matching rules: `references/dedup-policy.md`.
- `/ingest` runs a shape check on its own output (required keys, enum ranges, YAML parses) and stops there. Backlink symmetry, dangling nodes, and full semantic audits belong to `/check`. Do not re-implement them here.
- Assume another `/ingest` may run concurrently in a sibling worktree. All shared-file writes (`graph/edges.jsonl`, `graph/citations.jsonl`, `index.md`, `log.md`) must go through `tools/research_wiki.py` or use append-only semantics. See `references/init-mode.md`.
- In INIT MODE, skip `fetch_literature.py citations`, `fetch_literature.py references`, and the `rebuild-*` commands — the parent `/init` runs them once after fan-in.

## Error Handling

See `references/error-handling.md`. Highlights: MinerU API failures fall back to the local backend if installed, otherwise hand off to the user; an unusable manifest (`usable: false`) blocks ingest with a clear warning surface; literature lookup outages default `importance` to 3 and skip citation backfill; slug collisions append a numeric suffix.

## Dependencies

### Tools (via Bash)

- `uv run python tools/research_wiki.py slug "<title>"`
- `uv run python tools/research_wiki.py find-similar-concept @configured "<title>" --aliases "<a,b,c>"`
- `uv run python tools/research_wiki.py find-similar-claim @configured "<title>" --tags "<a,b,c>"`
- `uv run python tools/research_wiki.py add-edge @configured --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`
  - `--confidence high|medium|low` is required for paper-paper and paper-concept semantic edges.
- `uv run python tools/research_wiki.py add-citation @configured --from papers/<citing> --to papers/<cited> --source literature_api`
- `uv run python tools/research_wiki.py log @configured "<message>"`
- `uv run python tools/research_wiki.py rebuild-context-brief @configured`
- `uv run python tools/research_wiki.py rebuild-open-questions @configured`
- `uv run python tools/prepare_paper_source.py --raw-root @raw-root --output-dir @configured-sources-papers --cache-root @mineru-cache --source <zotero-pdf-path> [--title "<zotero-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]`
- `uv run python tools/fetch_zotero_metadata.py --item-key <key>` — optional after Zotero PDF lookup succeeds and only if Zotero Desktop Local API is reachable; returns Zotero metadata plus a derived `bibtex` entry
- `uv run python tools/fetch_literature.py paper|citations|references <doi-or-title>` — only when a DOI or confident title is available
- `uv run python tools/discover.py from-anchors --id <doi-or-title> --wiki-root @configured --limit 10 --output-checkpoint .checkpoints/ --markdown` — only when `--discover` is set

### Shared References

- `.claude/skills/shared-references/citation-verification.md`

### Skills

- `/init` — calls `/ingest-local-pdf` in parallel subagents for local prepared sources
- `/ingest-local-pdf` — prepares direct local PDFs and hands prepared sources back to `/ingest`
- `/check` — audits wiki state after `/ingest` completes; owns every semantic check `/ingest` intentionally does not perform
- `/discover` — optional follow-up when `--discover` is set; produces a shortlist of related papers the user may want to ingest next

### External APIs

- Crossref (via `tools/fetch_literature.py`) — no-key metadata, search, and best-effort reference lookup
- Zotero Desktop Local API (via `tools/fetch_zotero_metadata.py`) — optional local metadata enrichment when Zotero is running at `http://127.0.0.1:23119/api` or `ZOTERO_LOCAL_API`
- MinerU (via `tools/_mineru.py` + `tools/prepare_paper_source.py`; cloud API by default, local backend opt-in)

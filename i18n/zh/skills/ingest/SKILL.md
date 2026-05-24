---
description: Ingest a Zotero-backed paper into the wiki — creates pages (papers + concepts + people + claims) and builds all cross-references and graph edges. Trigger whenever the user says "ingest", "add this paper", or asks to fold a Zotero-backed paper into the knowledge base.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>) [--discover]"
---

# /ingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

Turn one paper into a fully wired set of wiki pages. Emit well-formed entities and correct cross-references; leave semantic audits (backlink symmetry, dangling nodes, field-value policing) for `/check`.

Use these local references on demand:

- `references/pdf-preprocessing.md` — MinerU pipeline + prepare-paper handoff for Zotero-selected PDFs; describes the `mineru-md` output format the rest of `/ingest` consumes
- `references/dedup-policy.md` — merge-vs-create decision rule for concepts and claims, and the line that separates `/ingest` shape checks from `/check` semantic audits
- `references/cross-references.md` — forward/reverse link matrix and paper-to-paper edge-type selection
- `references/init-mode.md` — manifest-driven handoff from `/init` and parallel-safety conventions
- `references/error-handling.md` — source parse, API, and slug-collision fallbacks
- `references/content-quality-gate.md` — report-derived quality floor for paper/concept/claim pages; open before drafting Step 3/4 outputs

Open `docs/runtime-page-templates.en.md` before drafting any wiki page frontmatter or body sections, and `docs/runtime-support-files.en.md` for `index.md`, `log.md`, and `graph/` formats.

## Inputs

- `source`: Zotero lookup arguments. Prepared `@configured-sources-papers/*.md` and `canonical_ingest_path` values are internal handoffs from `/ingest-local-pdf` or `/init` only (see `references/init-mode.md`). The prepared format is `mineru-md` — structured markdown with `sections`/`figures` frontmatter.
- Existing MinerU Markdown may be consumed only when handed off by `/ingest-local-pdf` or `/init`; do not expose prepared markdown as a normal `/ingest` user-facing input.
- Optional reference metadata usually comes directly from Zotero Local API when the source is a Zotero item; this includes Zotero/Better BibTeX fields such as `citationKey` and a derived `bibtex` entry that is compatible with the three `bibbst/` styles in this repo. Use that Zotero-derived `bibtex` string directly in the paper body under `## BibTeX`; never store BibTeX in YAML frontmatter and do not route `/ingest` through `.bib` or reference-metadata sidecars.
- Zotero lookup form: one or more of `--title <str>` or `--doi <doi>`, optionally plus `--zotero-root <dir>`. Do not expose or accept `--item-key` as a user-facing `/ingest` selector; Zotero item keys are internal identifiers and can point at attachments or parent items in ways that poison paper slug selection. If `--zotero-root` is omitted, read the selected profile's `zotero_roots` in `config/paths.json` and scan the listed Zotero data/profile directory candidates. A root may be the Zotero data directory containing `zotero.sqlite` and `storage/`, or a Zotero profile directory whose `prefs.js` points to the data directory.
- Zotero metadata enrichment is optional: after a DOI/title Zotero lookup selects an unambiguous candidate, use that candidate's internal `item_key` with `tools/fetch_zotero_metadata.py --item-key <key>` to read richer metadata from Zotero Desktop's local API. This internal metadata call is allowed; a user-supplied `--item-key` lookup path is not. If Zotero Desktop is closed or local API access is disabled, continue with the existing SQLite/Crossref path.
- Zotero metadata by itself is not a grounded source. If the user only provides metadata with no PDF, prepared Markdown, source note, or web/notes content, do not create a paper page; ask for a content source or record the metadata as a future ingest aid only when explicitly requested.
- `--discover` (optional, default **off**): after the final report, invoke `/discover --anchor <this-paper's-doi-or-title>` and append the shortlist to the report as "Related papers you may want to ingest next". Never auto-ingests the suggestions. Skipped automatically in INIT MODE. Treat this as a user-owned flag: do not set it based on repo state.

## Outputs

- One fully-wired paper page plus linked entities (concepts, claims, people)
- Graph edges and citations appended via `tools/research_wiki.py`
- Terminal summary with page counts and suggested follow-up ingests
- A minimum viable ingest normally touches the paper page, at least one concept or existing concept update, at least one claim or existing claim update, author/person handling, `index.md`, `log.md`, and graph/context files. If the source genuinely cannot support a claim or concept, say why in the log and final report.

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

- `paper → concept`: `introduces_concept` / `uses_concept` / `extends_concept` / `critiques_concept` with `confidence` and source-grounded `evidence`
- `paper → foundation`: `derived_from` (foundation is terminal; no reverse link)
- `paper → claim`: `supports` / `contradicts`
- `paper → paper`: `same_problem_as` / `similar_method_to` / `complementary_to` / `builds_on` / `compares_against` / `improves_on` / `challenges` / `surveys` with `confidence`
- bibliographic `paper → paper`: `cites` in `graph/citations.jsonl`

`tools/research_wiki.py add-edge` rejects missing confidence/evidence for
paper-paper and paper-concept semantic edges, and rejects legacy
paper-to-concept or paper-to-paper types on new writes.
Always call it with named flags: `--from`, `--to`, `--type`, and `--evidence`.

## Workflow

**Pre-condition**: working directory is the project root containing `tools/`, `pyproject.toml`, and `config/paths.json`. Run Python tools through `uv run python`, matching `README.md`. Do not hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, `@raw-root`, `@configured-sources-papers`, and `@mineru-cache`. By default, `tools/_paths.py` loads `config/paths.json` and the documented `LLM_WIKI_*` overrides; only override these roots when the user explicitly requests it.

Run commands from the repository root.

```shell
uv run python tools/research_wiki.py stats '@configured' --json
```

`@configured` must resolve to the actual wiki vault root, not the code repository root. `tools/research_wiki.py` rejects the code repository root to prevent accidental creation of root-level `graph/`, `index.md`, or `log.md`.
If path diagnosis is needed, use `uv run python tools/resolve_path_alias.py '@configured' '@raw-root' '@configured-sources-papers' '@mineru-cache'`. Do not import path helpers from `tools._env`; runtime path aliases are resolved by `tools/_paths.py` through this CLI.

### Step 1: Resolve the source

1. If `/init` passed a `canonical_ingest_path`, enter **INIT MODE** and consume that path verbatim. Do not rescan `@raw-root`. See `references/init-mode.md`.
2. If the source is a prepared `@configured-sources-papers/*.md`, use it directly.
3. If the user supplied Zotero lookup arguments, run:

   ```shell
   uv run python tools/find_zotero_pdf.py [--zotero-root <dir>] [--title "<title>"] [--doi <doi>]
   ```

   If `--zotero-root` is omitted, the helper scans `config/paths.json`; use `--zotero-config <path>` only when the user explicitly names an alternate config. Pick the top candidate only when it has exactly one existing PDF attachment and the match reason is `doi`, `exact-title`, a clearly unambiguous title match, or a filename-like attachment match. Otherwise report the candidates and ask the user to choose. For chapter-split books, prefer the attachment whose path or filename matches the chapter PDF name. Keep the selected candidate's internal `item_key`, `citation_key`, `creators`, `year`, and PDF path for preprocessing. Do not copy it into `@raw-root/papers/`.
4. If the selected Zotero candidate has an internal `item_key`, try:

   ```shell
   uv run python tools/fetch_zotero_metadata.py --item-key <key>
   ```

   Treat a successful response as authoritative bibliographic metadata from the user's local library. Use it to prefer `title`, `doi`, `year`, `venue`, `creators`/authors, `abstract`, `tags`, `url`, `zotero_select`, `citationKey`/`citekey`, `paper_slug`, `external_ids.zotero_key`, and the returned `bibtex` string. `metadata.paper_slug` is the Zotero/Better BibTeX citation key normalized for a wiki filename; if it is non-empty, use it directly as the paper page slug. If the command fails, note the fallback only if it affects the report; do not block ingest.
5. Preprocess Zotero PDFs with `tools/prepare_paper_source.py` using the Zotero Local API `citationKey`/`citekey` when available; otherwise use the selected candidate's SQLite `citation_key`; otherwise pass authors, year, title, and BibTeX metadata so the prepared source filename can fall back to `author_year_veryshorttitle`. This preprocessing includes the conservative LaTeX math repair pass and may report `latex math repaired: ...` in its warnings. Carry the Zotero-derived `bibtex` string into the body of both the prepared source markdown and `@configured/papers/{slug}.md` under a `## BibTeX` fenced `bibtex` code block. Do not put `bibtex` in frontmatter. Keep it as plain BibTeX so the three `bibbst/` styles (`gbt7714-numerical.bst`, `apsrev4-2.bst`, `elsarticle-num.bst`) can consume it directly. The derived BibTeX entry must stay citation-core only: entry type, citekey, `author`, `title`, `year`, one venue field (`journal`/`booktitle`/`publisher`/`school`/`institution`/`howpublished`), `volume`, `number`, `pages`, and `doi`; do not include URL, tags/keywords, abstract, language, or rights in the BibTeX block. Do not route `/ingest` through `.bib` or reference-metadata sidecars.

Raw persistence rule: never copy or duplicate a file already under `@configured-sources/` or `@raw-root/papers/` into a different raw subtree.

### Step 2: Paper identity and enrichment

1. Determine the paper slug from the Zotero metadata already fetched in Step 1. If `tools/fetch_zotero_metadata.py` returned a non-empty `metadata.paper_slug`, or the prepared source frontmatter contains non-empty `paperSlug`, use that value directly for `@configured/papers/{slug}.md`; do not rederive it from the title. If Zotero metadata is unavailable or has no citation key, fall back to the same paper identity metadata used for preprocessing:

   ```shell
   uv run python tools/research_wiki.py paper-slug "<paper-title>" --citation-key "<zotero-citation-key-or-empty>" --authors "<author-list>" --year "<year>" --bibtex "<zotero-derived-bibtex-or-empty>"
   ```

   This paper-page slug should normally match the prepared source `sourceSlug`, unless a deliberate source-level disambiguation suffix was needed for split chapters.
2. Stop-if-exists: if `@configured/papers/{slug}.md` already exists and the title or DOI matches, report and exit. If they differ, resolve the collision per `references/error-handling.md`.
3. When Zotero Local API metadata is available, prefer it for identity fields (`title`, `doi`, `year`, `venue`, authors/creators, abstract, tags, URL, `citationKey`/`citekey`, and `external_ids`) and use the derived `bibtex` string only for the body `## BibTeX` block.
4. When a DOI or confident title is available, query the no-key literature lookup:

   ```shell
   uv run python tools/fetch_literature.py paper <doi-or-title>
   ```

   Use the result for `venue`, `year`, `external_ids`, citation count when available, and the evidence behind the `importance` score (1-5). If citation counts are unavailable, default `importance` to 3 and mark it provisional.
5. Merge bibliographic metadata conservatively: Zotero wins for user-curated identity fields; Crossref may fill missing `external_ids`, venue/year gaps, and citation-derived importance evidence; MinerU remains the source of record for paper content and section structure.
6. Use the `mineru-md` frontmatter (`sections`, `figures`, `abstract_excerpt`) as your structural anchor when summarizing. The frontmatter already gives you a clean section list and figure inventory; do not re-parse the body to recover them.
7. Before drafting the paper page, classify the source form, research direction, and object:
   - `paper_type`: choose one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`. Use `review` for review/survey articles, but do not put `review` in `research_modes`.
   - `research_modes`: choose one or more of `theory`, `computation`, `experiment`. For review papers, classify by the evidence types being synthesized, not by `review`.
   - `theory_tags`: concrete theory/model/mechanism/framework names used, compared, or tested.
   - `computation_tags`: concrete calculation, simulation, statistical, ML, or data-analysis schemes used; `[]` if none.
   - `experiment_tags`: concrete observation, laboratory, sample-analysis, instrument, mission, protocol, or field process; `[]` if none.
   - `research_object_tags`: non-empty list of research objects (materials, celestial bodies, systems, samples, datasets, populations, model objects).
   If the source is unclear, write `unclear` in the relevant tag list or prose rather than inventing details.

### Step 3: Write the paper page

Open `docs/runtime-page-templates.en.md` for the paper template and `references/content-quality-gate.md` for the content floor. Fill every required frontmatter field; leave `cited_by` empty for now (step 5 backfills it).

Before writing, run a **shape check** on the frontmatter you are about to emit — no more than this:

- every required key is present and non-empty, including `paper_type`, `research_modes`, and `research_object_tags`; `bibtex` is absent from frontmatter
- `importance` ∈ {1,2,3,4,5}; `status` on claims ∈ the documented set; `maturity` on concepts ∈ the documented set; claim `confidence` ∈ [0,1]
- `paper_type` is one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`
- every value in `research_modes` is one of `theory`, `computation`, `experiment`; for each mode present, the corresponding `theory_tags` / `computation_tags` / `experiment_tags` is non-empty
- YAML parses

The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job, not this skill's.

Body sections to populate: Problem, Key idea, Research classification, Method, Results, Limitations, Open questions, My take, BibTeX, Related.

Paper page content must be both structured and source-faithful:

- Preserve the paper's own section logic. Use the `sections` frontmatter as the outline anchor; when useful, name source sections, figures, tables, algorithms, equations, or examples in bullets.
- For mathematical or technical papers, keep important equations in LaTeX. Use `$...$` for inline math and `$$...$$` for display math — this is the Obsidian rendering standard. Do not use code fences for equations or `\(` `\)` notation. PDF-derived prepared sources should already have passed `tools/repair_latex_math.py`; if a copied formula is still visibly broken, repair the math span itself instead of carrying OCR-spaced commands such as `\ alpha`, `_ {i}`, `^ {2}`, or `\left (` into the page. Do not replace formulas with vague prose or ASCII pseudocode when the source gives formal notation.
- `## Method` and `## Results` must contain concrete mechanisms, procedures, empirical findings, theoretical results, or chapter-level takeaways. Avoid generic summaries that could fit any paper in the field.
- `## Related` must list the concepts, claims, foundations, topics, and people linked during this ingest, so the paper is navigable even before graph files are rebuilt.
- Wikilinks must be vault-local slug links: write `[[slug]]`, never `[[wiki/...]]`, `[[wiki_glm/...]]`, `[[wiki_back.../...]]`, `[[topics/slug]]`, or any other directory-prefixed wikilink. Use ordinary relative markdown links only for prepared source excerpts, e.g. `[prepared markdown](../sources/papers/<source-slug>.md)`.

`## Research classification` must explicitly describe:

- **Theory**: which theory/model/framework is used or evaluated, if any.
- **Computation**: which numerical, simulation, statistical, ML, or data-analysis scheme is used, if any.
- **Experiment**: which observational, laboratory, sample-analysis, instrument, mission, or protocol process is used, if any.
- **Research objects**: what materials/systems/samples/datasets/celestial bodies/populations are studied.

### Step 4: Concepts, claims, people

Follow `references/dedup-policy.md`. In short:

**Research-direction anchor (optional but preferred)**: before drafting any concept's `## My understanding` section, check whether `@configured/Summary/research-direction.md` exists. If it does, read it and use the listed direction(s) as the anchoring context for the synthesis — see item 7 below. If the file is absent, fall back to a generic maintainer-voice synthesis and note that the anchor file was not found. Treat the file as guidance, not as a license to fabricate a connection the source paper cannot support.

1. For each candidate concept or claim, call the matching `find-similar-*` tool first.
2. Prefer merging into the top result. Create a new page only when the tool returns no acceptable candidate and the paper's importance justifies it.
3. For each entity you write or edit, write the reverse link in the same turn. The obligation matrix lives in `references/cross-references.md`.
4. Create a `@configured/people/{slug}.md` only for papers with importance ≥ 4. Otherwise append to existing author pages only.
5. For every paper with importance ≥ 4, create or update at least one claim. A missing `claims/` layer for a high-importance paper is a failed ingest unless the source is purely bibliographic, editorial, or otherwise has no defensible claim; record that exception in the log and final report. The "at most N" entity limits in the Constraints section are upper bounds, not targets — zero claims for an importance ≥ 4 paper violates this floor.
6. For every concept page created or materially edited, add or refresh `## Source excerpts` with at least **two substantively different excerpts** per concept page when the source covers the concept in multiple passages. Each excerpt must be an exact original-language blockquote linked to that paper's actual prepared MinerU markdown (`../sources/papers/<source-slug>.md`, derived from `canonical_ingest_path` or prepared frontmatter `sourceSlug`). If the source contains formulas or precise definitions for the concept, include a short formula/definition excerpt rather than only paraphrase. Do not cherry-pick a generic opening sentence — the excerpts should collectively demonstrate the concept's formal structure. If the prepared markdown is missing, record `prepared markdown: missing` and the fallback source used.
7. For concept pages, fill the reusable-knowledge sections, not just a definition: `## Intuition`, `## Formal notation`, `## Variants`, `## Comparison`, `## When to use`, `## Known limitations`, `## Open problems`, `## Key papers`, and `## My understanding`. **All listed sections are mandatory** — omit none silently. If a section truly does not apply, write a one-line scoped reason. `## Comparison` must include a compact table when two or more variants, neighboring concepts, or methods are worth contrasting. `## When to use` must give concrete applicability conditions (quantitative thresholds, physical regimes, specific task types), not purely qualitative "use when working with [topic]" formulations. `## Formal notation` must use `$`/`$$` LaTeX notation, never code fences or `\(` `\)`. `## My understanding` must include **at least one concrete connection sentence** tying the concept to the user's active research direction(s) declared in `@configured/Summary/research-direction.md` — e.g. how the concept appears in that direction, what role it plays (descriptor feature, computational bottleneck, validation benchmark, …). Only omit the connection if the source paper genuinely cannot defend one; in that case write a one-line scoped reason instead of forcing a generic tie-in. If the anchor file is absent, write a synthesis in the maintainer's voice and add `_no research-direction anchor file found_` on its own line.
8. For claim pages, include `## Statement`, `## Evidence summary`, `## Conditions and scope`, `## Counter-evidence`, `## Linked ideas`, and `## Open questions`. Keep confidence conservative: reserve ≥0.85 for claims with direct, strong evidence and clear scope; avoid wording like "necessary and sufficient" unless the paper proves exactly that.

### Step 5: Paper-to-paper edges and `cited_by`

Skip this whole step in INIT MODE — the parent `/init` handles it at fan-in.

```shell
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
4. Rebuild or append new/edited page entries to `@configured/index.md` using the repository-supported format. The index must remain useful to both humans and tools: keep `# Wiki Index`, entity category headings, slugs, titles when available, and key metadata such as importance/status/confidence/tags/research modes. A pure opaque dump or a malformed half-YAML index is not acceptable. See `docs/runtime-support-files.en.md` and prefer:

   ```shell
   uv run python tools/research_wiki.py rebuild-index '@configured'
   ```

### Step 7: Log and rebuild

Verify `@configured/graph/` exists before writing to it; create the directory if missing.

```shell
uv run python tools/research_wiki.py log '@configured' "ingest | added papers/<slug> | updated: <list>"
```

Unless in INIT MODE:

```shell
uv run python tools/research_wiki.py rebuild-index '@configured'
uv run python tools/research_wiki.py rebuild-context-brief '@configured'
uv run python tools/research_wiki.py rebuild-open-questions '@configured'
```

### Step 8: Report

Emit one compact summary covering: pages created, pages updated, graph edges added, topic/Summary placement (`Topic placement: matched N topics; Summary placement: matched S summaries` — if `N=0`, append a one-line suggestion to run `/edit` and create a topic page for the paper's domain; if `S=0`, suggest adding or updating a Summary page), contradictions surfaced (if any), and high-citation references not yet in the wiki (suggested follow-up ingests). Close with:

```
Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges
```

If the ingest falls below the normal minimum viable output (paper + concept/update + claim/update + index + log + graph), include a one-line reason rather than silently shipping a thin wiki.

**Self-check** (run before finalizing the report):
1. `@configured/papers/{slug}.md` exists and frontmatter YAML parses.
2. At least one concept page created or materially updated with all mandatory body sections.
3. At least one claim exists for importance ≥ 4 papers, or the report names the exception.
4. `@configured/graph/edges.jsonl` has at least one edge involving the new paper.
5. `@configured/log.md` has a new `## [today]` entry.
6. `@configured/index.md` includes the new paper and all new entities.
7. LaTeX in all written pages uses `$`/`$$` exclusively — no code-fence equations, no `\(` `\)`.
8. Every `[prepared markdown](../sources/papers/<source-slug>.md)` link written by this ingest resolves to an existing file with size > 0 bytes. If any target is missing or empty, the prepared MinerU markdown got wiped after preparation — surface the missing source slugs in the report and stop instead of shipping dead links. (If the user truly intends to keep concept pages without a source backing, the concept page must use the documented `prepared markdown: missing` fallback wording, not a live link to an empty file.)
9. For every concept page created or materially updated, `## My understanding` either contains the research-direction connection sentence required in Step 4 item 7, or contains a one-line scoped reason for omission, or notes that the anchor file `@configured/Summary/research-direction.md` was not found.
10. No written page contains directory-prefixed wikilinks such as `[[wiki/...]]`, `[[wiki_glm/...]]`, `[[wiki_back.../...]]`, or `[[topics/slug]]`. If Obsidian later rewrites links for disambiguation, report that as an external post-ingest change; `/ingest` itself must emit slug-only wikilinks.

If any check fails, fix it before emitting the report.

Do not run or report an unrestricted full-wiki `tools/lint.py` audit during `/ingest`. Historical lint debt belongs to `/check` and should not be mixed into the success report for a newly ingested paper. If you need a lint-backed verification, restrict it to the files created or materially edited in this ingest, for example:

```shell
uv run python tools/lint.py --wiki-dir '@configured' --only "papers/{slug}.md" --only "concepts/{new-or-edited}.md"
```

Report only the scoped results. Do not summarize unrelated pre-existing 🔴/🟡/🔵 counts in the `/ingest` final answer.

### Step 9: Optional discovery (only if `--discover` is set)

Skip this step unless the user explicitly passed `--discover`. Also skip it in INIT MODE — `/init`'s parent process decides whether to run discovery at fan-in, not individual subagents.

When active, invoke `/discover` with the just-ingested paper as the single anchor:

```shell
uv run python tools/discover.py from-anchors --id <doi-or-title-of-this-paper> --wiki-root '@configured' --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Append the markdown output to the report under a heading like "Related papers you may want to ingest next". Do not auto-ingest anything from the shortlist — the user picks. If discovery fails (provider outage, all channels empty), note the failure in one line and continue — a failed `/discover` must not fail an otherwise successful `/ingest`.

## Constraints

- `@raw-root/papers/`, `@raw-root/notes/`, `@raw-root/web/` are user-owned and read-only. `/ingest` does not accept direct local PDF inputs; `/ingest-local-pdf` prepares local sidecars under `@configured-sources/`. INIT MODE treats all of `raw/` as read-only.
- `@configured/graph/` is tool-owned. Edit only through `tools/research_wiki.py`.
- Paper slugs come first from Zotero metadata: use `metadata.paper_slug` returned by `tools/fetch_zotero_metadata.py` whenever it is non-empty. Use `tools/research_wiki.py paper-slug` only as the fallback when Zotero metadata or citation keys are unavailable. Use `tools/research_wiki.py slug` for concepts, claims, people, topics, ideas, experiments, outputs, and other non-paper pages. Never hand-craft.
- Every forward link writes its reverse link in the same turn — the wiki's bidirectional-link invariant. The only exception is links to `@configured/foundations/`, which are terminal.
- In INIT MODE, do not write reverse links into pages that already exist (created by a sibling worktree or scaffold). Record the relationship via `tools/research_wiki.py add-edge` only; the parent `/init` backfills reverse links during fan-in.
- Source format: `mineru-md` is the canonical prepared format. `/ingest` consumes prepared markdown in `@configured-sources-papers/` or the INIT MODE handoff path; Zotero-selected PDFs are preprocessed through `tools/prepare_paper_source.py`. Raw local PDFs are handled by `/ingest-local-pdf`. If preparation fails (unusable manifest with `usable: false`), surface the warnings to the user rather than proceeding.
- Metadata-only sources (Zotero metadata without an attachment/content source) cannot create a paper page. They may enrich a real content ingest, or be saved only when the user explicitly asks `/edit` to add a metadata note/source.
- Ingest is conservative about new entities:
  - importance < 4: at most **1** new concept and **1** new claim per paper
  - importance ≥ 4: **at least 1** and at most **3** new concepts; **at least 1** and at most **2** new claims per paper
  - Any further candidates must be merged into their nearest `find-similar-*` result, or left out for `/check` to flag. Rationale and matching rules: `references/dedup-policy.md`.
- LaTeX notation: use `$...$` for inline math and `$$...$$` for display math in all wiki pages. Code fences for equations and `\(` `\)` notation are not Obsidian-compatible and must not appear. PDF-derived formulas pass through `tools/repair_latex_math.py` during preprocessing; if you manually copy formulas, keep the same repaired style.
- `/ingest` runs a shape check on its own output (required keys, enum ranges, YAML parses) and stops there. Backlink symmetry, dangling nodes, and full semantic audits belong to `/check`. Do not re-implement them here.
- `/ingest` must not surface full-wiki lint counts from pre-existing pages. Use `tools/lint.py --only <touched-file>` only for scoped verification when needed, and leave whole-wiki lint reporting to `/check`.
- Assume another `/ingest` may run concurrently in a sibling worktree. All shared-file writes (`graph/edges.jsonl`, `graph/citations.jsonl`, `index.md`, `log.md`) must go through `tools/research_wiki.py` or use append-only semantics. See `references/init-mode.md`.
- In INIT MODE, skip `fetch_literature.py citations`, `fetch_literature.py references`, and the `rebuild-*` commands — the parent `/init` runs them once after fan-in.

## Error Handling

See `references/error-handling.md`. Highlights: MinerU API failures fall back to the local backend if installed, otherwise hand off to the user; an unusable manifest (`usable: false`) blocks ingest with a clear warning surface; literature lookup outages default `importance` to 3 and skip citation backfill; slug collisions append a numeric suffix.

## Dependencies

### Tools

- `uv run python tools/research_wiki.py paper-slug "<paper-title>" --citation-key "<key>" --authors "<authors>" --year "<year>" --bibtex "<bibtex>"` — fallback paper page slug generation when Zotero metadata did not return `metadata.paper_slug`
- `uv run python tools/research_wiki.py slug "<title>"` — non-paper slug generation
- `uv run python tools/research_wiki.py find-similar-concept '@configured' "<title>" --aliases "<a,b,c>"`
- `uv run python tools/research_wiki.py find-similar-claim '@configured' "<title>" --tags "<a,b,c>"`
- `uv run python tools/research_wiki.py add-edge '@configured' --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`
  - Use named flags only; do not use positional edge arguments like `<paper> <type> <concept>`.
  - `--evidence "<text>"` is required for paper-concept and paper-paper semantic edges. Use a short source-grounded phrase, not an empty placeholder.
  - `--confidence high|medium|low` is required for paper-paper and paper-concept semantic edges.
  - Paper-concept example: `uv run python tools/research_wiki.py add-edge '@configured' --from papers/<paper-slug> --to concepts/<concept-slug> --type uses_concept --evidence "<source-grounded reason>" --confidence high`
- `uv run python tools/research_wiki.py add-citation '@configured' --from papers/<citing> --to papers/<cited> --source literature_api`
- `uv run python tools/research_wiki.py log '@configured' "<message>"`
- `uv run python tools/research_wiki.py rebuild-index '@configured'`
- `uv run python tools/research_wiki.py rebuild-context-brief '@configured'`
- `uv run python tools/research_wiki.py rebuild-open-questions '@configured'`
- `uv run python tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source '<zotero-pdf-path>' [--title '<zotero-title>'] [--citation-key '<zotero-citation-key>'] [--authors '<author-list>'] [--year <year>] [--bibtex "$BIBTEX"]` — use single quotes for Zotero-derived paths/metadata because filenames may contain `$` or TeX math such as `$$^{143-147}$$`
- `uv run python tools/fetch_zotero_metadata.py --item-key <key>` — internal metadata enrichment only after DOI/title Zotero PDF lookup selects an unambiguous candidate; returns Zotero metadata, `metadata.paper_slug`, and a derived `bibtex` entry
- `uv run python tools/fetch_literature.py paper|citations|references <doi-or-title>` — only when a DOI or confident title is available
- `uv run python tools/discover.py from-anchors --id <doi-or-title> --wiki-root '@configured' --limit 10 --output-checkpoint .checkpoints/ --markdown` — only when `--discover` is set

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

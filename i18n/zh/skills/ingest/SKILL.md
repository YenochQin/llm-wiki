---
description: Ingest a paper into the wiki — creates pages (papers + concepts + people + claims) and builds all cross-references and graph edges. Trigger whenever the user says "ingest", "add this paper", drops a `.pdf` or `.md` source, or asks to fold a paper into the knowledge base.
argument-hint: "(<local-path> | [--zotero-root <dir>] (--title <str>|--doi <doi>|--item-key <key>)) [--discover]"
---

# /ingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

Turn one paper into a fully wired set of wiki pages. Emit well-formed entities and correct cross-references; leave semantic audits (backlink symmetry, dangling nodes, field-value policing) for `/check`.

Use these local references on demand:

- `references/pdf-preprocessing.md` — MinerU pipeline + prepare-paper handoff for direct PDF drops; describes the `mineru-md` output format the rest of `/ingest` consumes
- `references/dedup-policy.md` — merge-vs-create decision rule for concepts and claims, and the line that separates `/ingest` shape checks from `/check` semantic audits
- `references/cross-references.md` — forward/reverse link matrix and paper-to-paper edge-type selection
- `references/init-mode.md` — manifest-driven handoff from `/init` and parallel-safety conventions
- `references/error-handling.md` — source parse, API, and slug-collision fallbacks
- `references/content-quality-gate.md` — report-derived quality floor for paper/concept/claim pages; open before drafting Step 3/4 outputs

Open `docs/runtime-page-templates.en.md` before drafting any wiki page frontmatter or body sections, and `docs/runtime-support-files.en.md` for `index.md`, `log.md`, and `graph/` formats.

## Inputs

- `source`: one of — local `.pdf`, local `.md` (already-prepared MinerU output or hand-curated source), Zotero lookup arguments, or a `canonical_ingest_path` handed off by `/init` via `.checkpoints/init-sources.json` (see `references/init-mode.md`). The default prepared format produced by `tools/prepare_paper_source.py` is `mineru-md` — structured markdown with `sections`/`figures` frontmatter.
- Zotero lookup form: one or more of `--title <str>`, `--doi <doi>`, or `--item-key <key>`, optionally plus `--zotero-root <dir>`. If `--zotero-root` is omitted, read `config/zotero-roots.json` and scan the listed Zotero data/profile directory candidates. A root may be the Zotero data directory containing `zotero.sqlite` and `storage/`, or a Zotero profile directory whose `prefs.js` points to the data directory.
- If the user passes a chapter-like filename such as `978-0-387-35069-1_6.pdf`, treat it as a Zotero attachment hint first: resolve the parent Zotero item, then pick the matching attachment by filename/path if the helper returns one. Only fall back to the local `raw/papers/` or other local path branches when Zotero lookup fails or the user explicitly provides a local file path.
- `--discover` (optional, default **off**): after the final report, invoke `/discover --anchor <this-paper's-doi-or-title>` and append the shortlist to the report as "Related papers you may want to ingest next". Never auto-ingests the suggestions. Skipped automatically in INIT MODE. Treat this as a user-owned flag: do not set it based on repo state.

## Outputs

- One fully-wired paper page plus linked entities (concepts, claims, people)
- Graph edges and citations appended via `tools/research_wiki.py`
- Terminal summary with page counts and suggested follow-up ingests
- A minimum viable ingest normally touches the paper page, at least one concept or existing concept update, at least one claim or existing claim update, author/person handling, `index.md`, `log.md`, and graph/context files. If the source genuinely cannot support a claim or concept, say why in the log and final report.

## Wiki Interaction

### Reads

- `wiki/index.md` for existing slugs and tags
- `wiki/papers/*.md` to detect an already-ingested paper
- `wiki/concepts/*.md` and `wiki/foundations/*.md` for dedup matches
- `wiki/claims/*.md` for dedup matches
- `wiki/people/*.md` for existing authors
- `wiki/topics/*.md` to place the paper under existing topics
- `wiki/graph/open_questions.md` to notice when the paper addresses a known gap

### Writes

- `wiki/papers/{slug}.md` — CREATE
- `wiki/concepts/{slug}.md` — CREATE (new) or EDIT (append `key_papers`, aliases, variants)
- `wiki/claims/{slug}.md` — CREATE (new) or EDIT (append `evidence` entry)
- `wiki/people/{slug}.md` — CREATE (importance ≥ 4 only) or EDIT (append `Key papers`)
- `wiki/topics/{slug}.md` — EDIT only (no CREATE from `/ingest`)
- `wiki/graph/edges.jsonl` — APPEND via tool
- `wiki/graph/citations.jsonl` — APPEND via tool
- `wiki/graph/context_brief.md` — REBUILD (skipped in INIT MODE)
- `wiki/graph/open_questions.md` — REBUILD (skipped in INIT MODE)
- `wiki/index.md` — APPEND
- `wiki/log.md` — APPEND via tool

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

**Pre-condition**: working directory contains `wiki/`, `raw/`, and `tools/`. Resolve the Python interpreter once and reuse it:

```bash
# Find the project root via git so worktree subagents can still locate .venv.
# .venv is gitignored, so a subagent whose cwd is ../.worktrees/<branch>/
# doesn't have one — without this lookup it falls back to system python3 and
# misses the .env-loaded API keys plus the installed deps (requests for MinerU, etc.).
# git rev-parse --git-common-dir returns the main repo's .git regardless of
# which worktree the shell is in; its parent is the project root.
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null || true)
PROJECT_ROOT=""
if [ -n "$GIT_COMMON_DIR" ]; then
  PROJECT_ROOT=$(cd "$(dirname "$GIT_COMMON_DIR")" 2>/dev/null && pwd)
fi

if   [ -x "$PROJECT_ROOT/.venv/bin/python" ];         then PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
elif [ -x "$PROJECT_ROOT/.venv/Scripts/python.exe" ]; then PYTHON_BIN="$PROJECT_ROOT/.venv/Scripts/python.exe"
elif [ -x .venv/bin/python ];                         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ];                 then PYTHON_BIN=.venv/Scripts/python.exe
else                                                       PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: Resolve the source

1. If `/init` passed a `canonical_ingest_path`, enter **INIT MODE** and consume that path verbatim. Do not rescan `raw/`. See `references/init-mode.md`.
2. If the user supplied Zotero lookup arguments, run:

   ```bash
   "$PYTHON_BIN" tools/find_zotero_pdf.py \
     [--zotero-root <dir>] \
     [--title "<title>"] [--doi <doi>] [--item-key <key>]
   ```

   If `--zotero-root` is omitted, the helper scans `config/zotero-roots.json`; use `--zotero-config <path>` only when the user explicitly names an alternate config. Pick the top candidate only when it has exactly one existing PDF attachment and the match reason is `item-key`, `doi`, `exact-title`, a clearly unambiguous title match, or a filename-like attachment match. Otherwise report the candidates and ask the user to choose. For chapter-split books, prefer the attachment whose path or filename matches the chapter PDF name. Feed the selected PDF path into the normal PDF preprocessing step; do not copy it into `raw/papers/`.
3. If the source is a local `.md` already under `wiki/sources/papers/` (or otherwise marked as prepared `mineru-md`), use it directly. Legacy `raw/tmp/papers/*.md` inputs may still be read but new prepared outputs must use `wiki/sources/papers/`.
4. If the source is a local `.pdf` (or a `.md` that has not been prepared), run the preprocessing pipeline in `references/pdf-preprocessing.md` to produce a prepared MinerU markdown file under `wiki/sources/papers/` before continuing. The prep tool returns a JSON manifest whose `canonical_ingest_path` is the prepared `.md` and whose `ingest_format` is `mineru-md`.

Raw persistence rule: never copy or duplicate a file already under `wiki/sources/` or `raw/papers/` into a different raw subtree.

### Step 2: Paper identity and enrichment

1. Generate the paper slug:

   ```bash
   "$PYTHON_BIN" tools/research_wiki.py slug "<paper-title>"
   ```

2. Stop-if-exists: if `wiki/papers/{slug}.md` already exists and the title or DOI matches, report and exit. If they differ, resolve the collision per `references/error-handling.md`.
3. When a DOI or confident title is available, query the no-key literature lookup:

   ```bash
   "$PYTHON_BIN" tools/fetch_literature.py paper <doi-or-title>
   ```

   Use the result for `venue`, `year`, `external_ids`, citation count when available, and the evidence behind the `importance` score (1-5). If citation counts are unavailable, default `importance` to 3 and mark it provisional.
4. Use the `mineru-md` frontmatter (`sections`, `figures`, `abstract_excerpt`) as your structural anchor when summarizing. The frontmatter already gives you a clean section list and figure inventory; do not re-parse the body to recover them.
5. Before drafting the paper page, classify the source form, research direction, and object:
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

- every required key is present and non-empty, including `paper_type`, `research_modes`, and `research_object_tags`
- `importance` ∈ {1,2,3,4,5}; `status` on claims ∈ the documented set; `maturity` on concepts ∈ the documented set; claim `confidence` ∈ [0,1]
- `paper_type` is one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`
- every value in `research_modes` is one of `theory`, `computation`, `experiment`; for each mode present, the corresponding `theory_tags` / `computation_tags` / `experiment_tags` is non-empty
- YAML parses

The shape check is intentionally narrow. Backlink symmetry, dangling-node detection, and cross-entity consistency are `/check`'s job, not this skill's.

Body sections to populate: Problem, Key idea, Research classification, Method, Results, Limitations, Open questions, My take, Related.

Paper page content must be both structured and source-faithful:

- Preserve the paper's own section logic. Use the `sections` frontmatter as the outline anchor; when useful, name source sections, figures, tables, algorithms, equations, or examples in bullets.
- For mathematical or technical papers, keep important equations in LaTeX. Do not replace formulas with vague prose or ASCII pseudocode when the source gives formal notation.
- `## Method` and `## Results` must contain concrete mechanisms, procedures, empirical findings, theoretical results, or chapter-level takeaways. Avoid generic summaries that could fit any paper in the field.
- `## Related` must list the concepts, claims, foundations, topics, and people linked during this ingest, so the paper is navigable even before graph files are rebuilt.

`## Research classification` must explicitly describe:

- **Theory**: which theory/model/framework is used or evaluated, if any.
- **Computation**: which numerical, simulation, statistical, ML, or data-analysis scheme is used, if any.
- **Experiment**: which observational, laboratory, sample-analysis, instrument, mission, or protocol process is used, if any.
- **Research objects**: what materials/systems/samples/datasets/celestial bodies/populations are studied.

### Step 4: Concepts, claims, people

Follow `references/dedup-policy.md`. In short:

1. For each candidate concept or claim, call the matching `find-similar-*` tool first.
2. Prefer merging into the top result. Create a new page only when the tool returns no acceptable candidate and the paper's importance justifies it.
3. For each entity you write or edit, write the reverse link in the same turn. The obligation matrix lives in `references/cross-references.md`.
4. Create a `wiki/people/{slug}.md` only for papers with importance ≥ 4. Otherwise append to existing author pages only.
5. For every ingest whose source supports an arguable proposition, create or update at least one claim. A missing `claims/` layer is a failed ingest unless the source is purely bibliographic, editorial, or otherwise has no defensible claim; record that exception in the log and final report.
6. For every concept page created or materially edited, add or refresh `## Source excerpts`: one short exact original-language blockquote per grounding paper, each linked to that paper's prepared MinerU markdown (`../sources/papers/<paper-slug>.md`). If the source contains formulas or precise definitions for the concept, include a short formula/definition excerpt rather than only paraphrase. If the prepared markdown is missing, record `prepared markdown: missing` and the fallback source used.
7. For concept pages, fill the reusable-knowledge sections, not just a definition: `## Intuition`, `## Formal notation`, `## Variants`, `## Comparison`, `## When to use`, `## Known limitations`, `## Open problems`, `## Key papers`, and `## My understanding`. If a section truly does not apply, write a one-line scoped reason.
8. For claim pages, include `## Statement`, `## Evidence summary`, `## Conditions and scope`, `## Counter-evidence`, `## Linked ideas`, and `## Open questions`. Keep confidence conservative: reserve ≥0.85 for claims with direct, strong evidence and clear scope; avoid wording like "necessary and sufficient" unless the paper proves exactly that.

### Step 5: Paper-to-paper edges and `cited_by`

Skip this whole step in INIT MODE — the parent `/init` handles it at fan-in.

```bash
"$PYTHON_BIN" tools/fetch_literature.py references <doi-or-title>
"$PYTHON_BIN" tools/fetch_literature.py citations <doi-or-title>
```

- For each reference whose DOI or title resolves to an existing `wiki/papers/{slug}.md`, add a bibliographic `cites` row to `graph/citations.jsonl`.
- Add a semantic paper-to-paper edge in `graph/edges.jsonl` only when the source text gives a clear cue. Edge-type selection is in `references/cross-references.md`. If no semantic relation cleanly fits, keep only the `cites` row.
- For each citation already in the wiki, append the citer's slug to this paper's `cited_by`.
- Surface unmatched high-citation references in the final report so the user can decide whether to follow up with another `/ingest`.

### Step 6: Topics and index

1. Match the paper's domain and tags against existing `wiki/topics/*.md`. For each match:
   - importance ≥ 4 → append to the topic's `## Seminal works`
   - importance < 4 → append under `## SOTA tracker` or `## Recent work` by year
   - if the paper directly addresses a listed open problem, annotate that line on the topic page
2. Do not create new topic pages from `/ingest` — topic creation belongs to `/init` and `/edit`.
3. Rebuild or append new/edited page entries to `wiki/index.md` using the repository-supported format. The index must remain useful to both humans and tools: keep `# Wiki Index`, entity category headings, slugs, titles when available, and key metadata such as importance/status/confidence/tags/research modes. A pure opaque dump or a malformed half-YAML index is not acceptable. See `docs/runtime-support-files.en.md` and prefer:

   ```bash
   "$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
   ```

### Step 7: Log and rebuild

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki/ "ingest | added papers/<slug> | updated: <list>"
```

Unless in INIT MODE:

```bash
"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
```

### Step 8: Report

Emit one compact summary covering: pages created, pages updated, graph edges added, contradictions surfaced (if any), and high-citation references not yet in the wiki (suggested follow-up ingests). Close with:

```
Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges
```

If the ingest falls below the normal minimum viable output (paper + concept/update + claim/update + index + log + graph), include a one-line reason rather than silently shipping a thin wiki.

### Step 9: Optional discovery (only if `--discover` is set)

Skip this step unless the user explicitly passed `--discover`. Also skip it in INIT MODE — `/init`'s parent process decides whether to run discovery at fan-in, not individual subagents.

When active, invoke `/discover` with the just-ingested paper as the single anchor:

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <doi-or-title-of-this-paper> \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

Append the markdown output to the report under a heading like "Related papers you may want to ingest next". Do not auto-ingest anything from the shortlist — the user picks. If discovery fails (provider outage, all channels empty), note the failure in one line and continue — a failed `/discover` must not fail an otherwise successful `/ingest`.

## Constraints

- `raw/papers/`, `raw/notes/`, `raw/web/` are user-owned and read-only. Direct local `/ingest` may add prepared sidecars under `wiki/sources/`. INIT MODE treats all of `raw/` as read-only.
- `wiki/graph/` is tool-owned. Edit only through `tools/research_wiki.py`.
- Slugs always come from `tools/research_wiki.py slug`. Never hand-craft.
- Every forward link writes its reverse link in the same turn — the wiki's bidirectional-link invariant. The only exception is links to `wiki/foundations/`, which are terminal.
- In INIT MODE, do not write reverse links into pages that already exist (created by a sibling worktree or scaffold). Record the relationship via `tools/research_wiki.py add-edge` only; the parent `/init` backfills reverse links during fan-in.
- Source format: `mineru-md` is the canonical prepared format. Never ingest from a raw PDF — always go through `tools/prepare_paper_source.py` first so downstream extraction sees structured markdown with frontmatter (`sections`, `figures`). If preparation fails (unusable manifest with `usable: false`), surface the warnings to the user rather than ingesting from the raw PDF text.
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

- `"$PYTHON_BIN" tools/research_wiki.py slug "<title>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-concept wiki/ "<title>" --aliases "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py find-similar-claim wiki/ "<title>" --tags "<a,b,c>"`
- `"$PYTHON_BIN" tools/research_wiki.py add-edge wiki/ --from <id> --to <id> --type <type> --evidence "<text>" [--confidence high|medium|low]`
  - `--confidence high|medium|low` is required for paper-paper and paper-concept semantic edges.
- `"$PYTHON_BIN" tools/research_wiki.py add-citation wiki/ --from papers/<citing> --to papers/<cited> --source literature_api`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-index wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/`
- `"$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/`
- `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"]`
- `"$PYTHON_BIN" tools/fetch_literature.py paper|citations|references <doi-or-title>` — only when a DOI or confident title is available
- `"$PYTHON_BIN" tools/discover.py from-anchors --id <doi-or-title> --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown` — only when `--discover` is set

### Shared References

- `.claude/skills/shared-references/citation-verification.md`

### Skills

- `/init` — calls `/ingest` in parallel subagents via INIT MODE
- `/check` — audits wiki state after `/ingest` completes; owns every semantic check `/ingest` intentionally does not perform
- `/discover` — optional follow-up when `--discover` is set; produces a shortlist of related papers the user may want to ingest next

### External APIs

- Crossref (via `tools/fetch_literature.py`) — no-key metadata, search, and best-effort reference lookup
- MinerU (via `tools/_mineru.py` + `tools/prepare_paper_source.py`; cloud API by default, local backend opt-in)

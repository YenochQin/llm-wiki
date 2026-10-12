---
name: paper-plan
description: Use when planning a theoretical, computational, experimental, or mixed research paper from wiki claims and recorded evidence. Produces a PAPER_PLAN with the narrative, sections, figures, citations, and evidence gaps for a chosen journal or conference, or a provisional outline when the venue is undecided.
argument-hint: "<claim-slugs...> [--venue <journal-or-conference>] [--title <working-title>]"
---

# /paper-plan

> Compile a paper outline from the wiki's claim graph.
> Input target claims and, optionally, a target journal or conference;
> compile an evidence map from the wiki → determine narrative structure → generate a section outline + figure plan + citation plan.
> Agent-local review is a mandatory step, using criteria appropriate to the paper's research modes.
> Output PAPER_PLAN.md to wiki/outputs/.
>
> Key distinction: the outline is claim-graph-driven — each section exists because it supports a claim,
> not because paper convention requires that section.

## Inputs

- `claims`: list of existing target claim slugs (space-separated). Preserve recorded status/confidence. Proposed, challenged, or otherwise weakly evidenced claims may appear in a draft outline, with their gaps explicit; do not upgrade them while planning.
- `--venue` (optional): any user-specified journal or conference, preserving its name. When omitted, record `unspecified` and use a provisional structure/budget; do not choose a venue on the user's behalf. Verify applicable article-type/submission rules from user-supplied requirements or current official author instructions before asserting format compliance.
- `--title` (optional): working title; if omitted, generated from target claims

## Outputs

- `wiki/outputs/paper-plan-{slug}-{date}.md` — complete paper plan (PAPER_PLAN.md)
- `wiki/graph/edges.jsonl` — new derived_from edges (plan → source claims/papers)
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/log/` — appended log entry
- **PAPER_PLAN_REPORT** (printed to terminal) — plan summary
- The plan records research modes, actual evidence coverage, unresolved gaps, and whether venue/budget requirements are verified or provisional. Delivery of a draft outline does not establish evidence or submission readiness.

## Wiki Interaction

### Reads
- `wiki/claims/*.md` — status, confidence, evidence list, conditions of target claims
- `wiki/experiments/*.md` — supporting experiments for claims (results, metrics, key_result)
- User-identified proof/derivation notes, calculation reports, datasets, and observation records — additional evidence with actual path/section provenance; reading them does not authorize ingestion or changes to those sources
- `wiki/papers/*.md` — evidence source papers (Method, Results, Related)
- `wiki/concepts/*.md` — technical concepts involved (supports Method section writing)
- `wiki/topics/*.md` — research direction context (supports Introduction positioning)
- `wiki/ideas/*.md` — motivation and hypothesis of original ideas
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps (annotate paper limitations)
- `wiki/graph/edges.jsonl` — relationship graph (build narrative logic chain)
- `skills/shared-references/academic-writing.md` — writing principles
- `skills/shared-references/citation-verification.md` — citation discipline

### Writes
- `wiki/outputs/paper-plan-{slug}-{date}.md` — paper plan file
- `wiki/graph/edges.jsonl` — derived_from edges
- `wiki/graph/context_brief.md` — rebuilt
- `wiki/log/` — appended operation log

### Graph edges created
- `derived_from`: paper-plan → claims (which claims the plan is derived from)
- `derived_from`: paper-plan → papers (which papers the plan cites)

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`, matching `README.md`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

### Step 1: Load Claim Graph

1. Read `wiki/claims/{slug}.md` for all target claims
2. For each claim, collect its evidence list:
   - each evidence item's recorded source and source anchor, plus linked research records
   - evidence type (supports / contradicts / tested_by / invalidates)
   - evidence strength (weak / moderate / strong)
3. For each evidence source, read the corresponding wiki page:
   - `wiki/experiments/{source}.md` → key_result, metrics, outcome
   - `wiki/papers/{source}.md` → Evidence Pack, Method, Results, and cited prepared-source locations
   - user-identified evidence files → the actual proof, derivation, calculation, or observation and its conditions; retain normal Markdown file links rather than inventing wiki pages
4. Load relevant edges from `wiki/graph/edges.jsonl` to build relationships between claims
5. Read `wiki/graph/context_brief.md` for global context
6. Read `wiki/graph/open_questions.md` to annotate known limitations

**Validation**:
- Determine applicable `theory`, `computation`, and/or `experiment` modes from the claims, research object, and actual sources; these are internal classifications, not new user flags. Explain ambiguous choices.
- Match evidence to what each claim asserts: proof/derivation and assumptions for theoretical claims; recorded numerical results with applicable convergence/error/validation checks for computational claims; observations/measurements with applicable controls and uncertainty for experimental claims. Mixed claims require support for each component. Numerical agreement alone does not prove a general theorem.
- No experimental result is required solely because the artifact is a paper plan. Low confidence, missing checks, and proposed/challenged claims become explicit evidence gaps, not automatic demands for experiments or a reason to withhold the outline.

### Step 2: Compile Evidence Map from Wiki

Read [references/evidence-map.md](references/evidence-map.md) when compiling the claim → evidence → section matrix. Preserve evidence status/strength, record precise source locations and applicable checks, and map every target claim to the argument; missing support remains an explicit gap.

### Steps 3–4: Narrative and Section Outline

Read [references/narrative-and-outline.md](references/narrative-and-outline.md) when choosing the storyline, section structure, and venue budget. Select sections from the research modes and argument; do not require an Experiments section, ML baselines, ablations, or an architecture figure. Use verified venue limits where available; otherwise label budget estimates provisional.

### Step 5: Figure Plan

Read [references/figure-plan.md](references/figure-plan.md) when planning figures/tables. Record each item's type, source evidence, visual encoding, and size; do not assume results that are not recorded.

### Step 6: Citation Plan

Following `shared-references/citation-verification.md`:

1. List all wiki papers referenced via `[[slug]]` in the outline
2. For each paper, pre-fetch BibTeX:
   - DBLP first, then CrossRef, then `tools/fetch_literature.py` CrossRef wrapper
   - Success: record BibTeX key + source
   - Failure: mark `[UNCONFIRMED]`
3. Generate citation coverage report:
   ```
   Citations: 15 total, 12 verified (DBLP: 8, CrossRef: 3, literature API: 1), 3 [UNCONFIRMED]
   ```
4. For [UNCONFIRMED] entries, provide suggested URLs for manual verification

### Step 7: Agent Review (mandatory)

Perform `/llm-review` in the current agent with `--difficulty hard --focus completeness`. Read and follow `skills/llm-review/SKILL.md` and `shared-references/review-protocol.md`.

Pass the selected research modes and evidence requirements with the plan. Review the complete outline, evidence map, figure/table plan, citation coverage, and venue constraints using domain-appropriate criteria; absence of ML baselines/ablations is not a flaw unless the actual claims require them:

1. Is the narrative arc (gap → solution → evidence → impact) convincing, with a clear purpose for every section?
2. Are claims supported by the right evidence type? Which assumptions, proof steps, numerical checks, measurements, or controls are missing for the selected modes?
3. Is related work grouped appropriately, and are important directions missing from the recorded coverage?
4. Is the budget feasible under verified venue rules, and are unknown requirements labeled provisional?
5. Do the figures and tables adequately support the argument?

Record the 1–10 score, verdict, specific findings, review mode, and revision record. Revise supported findings and re-check affected parts of the final plan; a pre-edit score cannot certify later edits. If the current agent created the outline, label the review `self-review`. No additional service configuration is needed to complete this gate.

### Step 8: Write to Wiki

Read [references/recording.md](references/recording.md) before saving the plan. Include metadata, evidence map, revised outline, figure/table plan, citation coverage, and actual review findings/provenance. Add derived edges through the tool, rebuild context, log actual writes, and return the plan report with unresolved evidence/review/citation gaps.

## Source grounding

This skill generates durable content, so it follows the shared **Source Grounding Discipline** — see `skills/shared-references/source-grounding.md`.

- Every substantive planned assertion must map to a target/contextual claim and retrievable evidence, or be explicitly marked as an unresolved assumption/evidence gap. Every planned literature citation must resolve to an existing `wiki/papers/` page; supplemental user files retain their actual provenance.
- Do not present missing proofs, calculations, or experimental results as completed. An outline may identify a section that needs evidence, with the gap clearly marked.
- Pre-fetch BibTeX per `citation-verification.md` and flag `[UNCONFIRMED]` entries early. Manual grounding self-check on the plan.

## Constraints

- **Evidence follows the claim**: accept theory/computation/experiment as applicable; no universal experimental-result, seed-count, percentage, or ablation quota. Do not create experiment pages simply to make a theoretical/computational paper eligible.
- **Venue rules need provenance**: accept any journal/conference; retain verified rules and their source/date/article type, or record them as unverified. No hard-coded ML venue/page-limit whitelist.
- **Budget must be honest**: fit verified page/word/figure limits where applicable; provisional budgets are estimates, not confirmed compliance.
- **Agent review is mandatory**: complete Step 7 in the current agent and record findings; additional model configuration is not a prerequisite
- **All citations from wiki**: every paper in the citation plan must exist in wiki/papers/
- **claim → section mapping must be complete**: every target claim must appear in at least one section
- **Every section must serve the argument**: map it to target/contextual claims or an explicit supporting role such as notation or proof dependencies; remove filler without inventing contribution claims
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl
- **Resolving citations**: wiki entities/literature use existing `[[slug]]` links; supplemental evidence files use normal Markdown links with actual locations
- **Planning scope**: do not execute new calculations/experiments, invent a missing proof, modify claim status/confidence, or compile LaTeX. Those actions require a separate user request.

## Error Handling

- **Incomplete evidence, including all-proposed claims**: deliver a draft outline with claim-specific gaps and suggested proof, numerical-validation, or observational work as applicable. Mark evidence readiness incomplete; do not automatically run that work.
- **Limited literature coverage**: identify missing comparisons relevant to the actual claims; do not use a fixed citation count as a quality gate.
- **Venue omitted or rules unavailable**: deliver a provisional outline and state unknown format/budget constraints. Ask only if a missing rule prevents a user-requested exact-format deliverable.
- **Verified budget exceeded**: compress or move supporting detail to an appendix only when the verified rules allow it; keep essential argument/evidence in the main text and report remaining conflicts.
- **Review evidence incomplete**: list missing evidence and unresolved findings in the plan; do not mark the review passed
- **BibTeX fetch failed**: mark [UNCONFIRMED]; summarize in the citation plan report
- **Slug conflict**: append date suffix
- **Target claim not found**: error; list candidates in wiki/claims/

## Dependencies

### Tools
- `uv run python -X utf8 tools/research_wiki.py slug "<title>"` — generate slug
- `uv run python -X utf8 tools/research_wiki.py add-edge '@configured' ...` — add graph edge
- `uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'` — rebuild query_pack
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"` — append log
- `uv run python -X utf8 tools/fetch_literature.py search "<title>"` — no-key literature search (citation plan fallback)

### Skills
- `/llm-review` — current-agent critique; reads its rubric and returns findings without editing the artifact

### Host capabilities
- Read/search local files for wiki context.
- Fetch bibliographic metadata through available web tools or `tools/fetch_literature.py`; label unavailable verification rather than assuming a particular host tool.

### Shared References
- `skills/shared-references/review-protocol.md` — current-agent review and provenance
- `skills/shared-references/academic-writing.md` — narrative structure and section design principles
- `skills/shared-references/citation-verification.md` — citation fetch and verification rules

### Called by
- Manual user invocation

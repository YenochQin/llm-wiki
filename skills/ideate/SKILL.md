---
name: ideate
description: Use when the user wants to generate new research ideas or directions grounded in the wiki and external literature — for example asking what to work on next or for ideas around a given topic.
argument-hint: "[research-direction-or-topic] [--max-ideas N] [--skip-validation] [--auto]"
---

# /ideate

> Generates high-quality research ideas through a 5-phase pipeline, grounded in the wiki knowledge base and external search.
> Phase 1 scans the research landscape (wiki + web search + no-key literature search), Phase 2 generates ideas and challenges alternatives in the current agent,
> Phase 3 applies a first-pass filter (feasibility + quick novelty check), Phase 4 performs deep validation (calls /novelty + /llm-review),
> Phase 5 writes selected ideas within the total page budget, including selected eliminated ideas as anti-repetition memory; the report lists candidates that were not saved.

## Inputs

- `direction` (optional): research direction, keywords, or specific problem description. If omitted, select from relevant open questions, then from a clear topic in the current conversation. If neither exists, ask only for the missing research direction; do not invent one or require ingestion first.
- `--max-ideas N` (optional, default 3): total maximum number of new `ideas/` pages in this run, counting proposed and failed pages together. Require a positive integer; never silently exceed or change it.
- `--skip-validation`: skip Phase 4 deep validation (fast mode: Phase 1–3 + Phase 5 only)
- `--auto`: fully automatic mode, no pause for user confirmation

## Outputs

- `wiki/ideas/{slug}.md` — selected proposed or failed ideas, at most `--max-ideas` new pages in total; remaining candidates are reported without creating pages
- `wiki/graph/edges.jsonl` — new idea → claim/gap relationship edges
- `wiki/graph/context_brief.md` — rebuilt compressed context
- `wiki/graph/open_questions.md` — rebuilt knowledge gap map
- **IDEA_REPORT** (printed to terminal) — pipeline execution summary, ranked results, novelty scores

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — knowledge gaps, drives idea direction
- `wiki/ideas/*.md` — existing ideas, especially status=failed ideas and their failure_reason (banlist)
- `wiki/claims/*.md` — current claims status, identifies weakly_supported and challenged claims
- `wiki/papers/*.md` — existing paper methods and results
- `wiki/concepts/*.md` — technical concepts, find cross-domain combination opportunities
- `wiki/topics/*.md` — research direction maps, SOTA and open problems
- `@experiment-root/*.md` — existing experiment results, avoid duplication

### Writes
- `wiki/ideas/{slug}.md` — create new idea pages
- `wiki/graph/edges.jsonl` — add idea → claim/gap relationship edges (addresses_gap, inspired_by)
- `wiki/graph/context_brief.md` — rebuild
- `wiki/graph/open_questions.md` — rebuild
- `wiki/log/` — append operation log

### Graph edges created
- `addresses_gap`: idea → claim/topic (knowledge gap the idea targets)
- `inspired_by`: idea → paper/concept (source of inspiration for the idea)

## Workflow

Resolve `@experiment-root` or `@output-root` with `tools/resolve_path_alias.py` before accessing that root; resolve only roots used by the selected mode. Use returned absolute paths for ordinary file operations.

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`, matching `README.md`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

**Additional pre-condition steps**:
1. **Check wiki maturity**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py maturity '@configured' --json
   ```
   Adjust subsequent behavior based on maturity level:
   - **cold**: expand Phase 1 external search (web-search queries from 5 to 8, literature-search limit from 20 to 30),
     read any existing relevant pages and failed-idea records, and annotate "cold-start mode: heavier external search". Cold means sparse, not necessarily empty; missing navigation files do not require initialization or ingestion.
   - **warm**: standard behavior (current default)
   - **hot**: reduce Phase 1 external search (web-search queries from 5 to 2, literature-search limit from 20 to 10),
     raise Phase 3 gap_alignment_bonus from +2 to +3, prioritize resolving weak claims already in the wiki
2. **Snapshot wiki state** (for the Growth Report at the end):
   Save the JSON returned by maturity to memory variable `maturity_before`

### Phase 1: Landscape Scan

Goal: build a comprehensive view of the target domain, including existing work, knowledge gaps, and recent advances.

Read [references/landscape-scan.md](references/landscape-scan.md) when retrieving wiki context and external literature. Read available failed-idea records; empty banlists/gap lists and missing navigation files are valid. Use available search capabilities and the maturity settings above without requiring ingestion.

Keep a source ledger for the facts and prior work used in candidates:

- Existing wiki sources use resolving `[[slug]]` links.
- External sources use ordinary Markdown links and bibliographic identity: title, authors, year, DOI when available, retrieved location/date, and the supporting passage or result. Mark them `external — not ingested`; do not fabricate a DOI or wiki page.
- Record explicit user assumptions separately from retrieved evidence. A metadata-only result supports bibliographic facts, not an unread method or numerical result.
- A cold-start idea may be grounded entirely in traceable external sources and explicit user input. Label its proposed hypothesis as speculative; leave `origin_gaps` empty when no relevant claim page exists. Do not auto-ingest sources or create placeholder papers/claims just to satisfy links.

### Phases 2–3: Generate, Challenge, and Filter Candidates

Read [references/candidate-generation.md](references/candidate-generation.md) for the brainstorming passes and first-pass screening. Deduplicate against active and failed ideas, distinguish same-agent challenge from independent review, and rank only supported candidates. Fewer candidates than the example counts is valid.

### Phase 4: Deep Validation

(Skip if `--skip-validation` is set; proceed directly to Phase 5.)

Apply deep validation to up to 3 surviving ideas from Phase 3. Record validation per candidate; candidates not checked are `not validated`, not passed.

1. **Call /novelty** (one at a time):
   ```
   For each top idea:
   Review skill: /novelty (read and follow skills/novelty/SKILL.md)
   Args: "<idea-title-and-hypothesis>"
   ```
   Record novelty score (1–5) and recommendations

2. **Call /llm-review** (for up to 2 surviving ideas):
   ```
   Review skill: /llm-review (read and follow skills/llm-review/SKILL.md)
   Args: "<idea-full-description>" --difficulty hard --focus method
   ```
   Record review score (1–10) and weaknesses

3. **Composite ranking**:
   - Use the composite `novelty_score × 2 + review_score + gap_alignment_bonus` only when both component scores exist. Otherwise report the missing assessment and rank provisionally from the available findings; never fill an unrun review with zero or an invented score.
   - gap_alignment_bonus: +2 if the idea directly targets a gap_map entry
   - If novelty_score <= 2 → downgrade to "modify needed"
   - If review_score <= 4 → downgrade to "major issues"

4. Display the ranked candidates, validation gaps, and proposed write selection. Apply the same selection/write check in Phase 5 even when deep validation was skipped.

### Phase 5: Write to Wiki

Select what can be saved before creating any pages:

- Build a deduplicated `write_selection` with at most `N = --max-ideas` new idea pages across all statuses. Prioritize ranked proposed ideas, then use remaining slots for eliminated ideas with specific, source-backed rejection reasons. Fewer than N is valid.
- List every unselected candidate and its reason in the report as `report-only`; do not claim it was added to persistent failure memory. If all candidates were eliminated, select at most N failed pages. Do not overwrite an existing idea or evade the cap through another writer.
- With `--auto` or an existing user instruction authorizing this selection, proceed without asking again. Otherwise show the concrete selection for confirmation/adjustment before writing; report `awaiting-selection` while it is pending. Skipping validation does not bypass this check.
- Before drafting page structure, open `docs/runtime-page-templates.en.md` (§ideas). Preserve the canonical fields and body sections. If no supported candidates or no authorized selection is available, return the report without page writes, rebuilds, or a write log.

For an authorized, nonempty `write_selection`, read [references/recording.md](references/recording.md) before writing selected proposed/failed pages, computing priority, adding valid graph edges, rebuilding derived files, or logging. The total cap and selection check above apply to every write; external sources remain ordinary links and absent validation scores remain unset.

Return an IDEA_REPORT using [references/report-format.md](references/report-format.md), including when no pages were saved. Distinguish saved proposed/failed pages from report-only candidates, actual scores from absent checks, and recorded/partial/awaiting-selection/missing-input outcomes. Report actual paths and counts, never assumed persistence.

## Source grounding

This skill generates durable content, so it follows the shared **Source Grounding Discipline** — see `skills/shared-references/source-grounding.md`.

- Every idea, gap, and cited prior work must trace to a wiki page or a captured search/literature result — do not invent papers, methods, or benchmark numbers.
- Mark speculative leaps explicitly; check the failed-idea banlist (`failure_reason`) before proposing so dead ends are not re-explored.
- `grounding_lint.py` does not cover `ideas/`; run a manual grounding self-check before writing.

## Constraints

- **Auto-switch to cold-start mode when wiki is cold**: expand external search (8 web-search queries, literature-search limit 30), do not block execution
- **Traceable grounding, including cold starts**: substantiate prior-work facts with existing wiki sources, captured external sources, or explicit user input. No minimum wiki-page count; do not create fake links or treat un-ingested sources as wiki pages.
- **Banlist must be loaded**: Phase 1 must read failed ideas' failure_reason; Phase 2/3 must check for overlap
- **Review provenance**: follow review-protocol.md; challenge passes are not independent generators or reviewers
- **Total page cap**: proposed and failed pages share `--max-ideas`; only selected failed pages are persisted with `failure_reason`. Report all remaining candidates without claiming persistence.
- **No fabrication**: all ideas must be derived from existing wiki knowledge or external search results; do not invent non-existent papers or methods
- **Slug uniqueness**: check whether the same slug already exists in wiki/ideas/ before creating
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl

## Error Handling

- **Wiki is empty**: use Phase 1 external search and the supplied direction; do not require ingestion first. Ask for a topic only if neither the request nor available context provides one.
- **Web search unavailable**: use available structured literature search and wiki sources. If neither provides sufficient grounding, return `source-unavailable` with the missing evidence and save no unsupported idea pages.
- **Literature API unavailable**: skip structured literature search, use available web search for compensation
- **/novelty fails**: if novelty fails for a single idea in Phase 4, mark "novelty unverified" and continue
- **/llm-review fails**: if review fails in Phase 4, mark "unreviewed" and continue; recommend user manually runs /llm-review
- **Slug conflict**: if the same slug already exists in wiki/ideas/, append a numeric suffix (e.g. `sparse-lora-v2`)
- **All ideas eliminated**: save only selected failed pages within the total cap; report the rest, their rejection reasons, and possible search adjustments. An empty proposed shortlist is a valid outcome.
- **A write or graph/rebuild fails**: report a partial outcome with the actual saved paths/counts and failed operation; do not label the full selection recorded or exceed the cap during recovery.

## Dependencies

### Tools
- `uv run python -X utf8 tools/research_wiki.py maturity '@configured' --json` — check wiki maturity + Growth Report
- `uv run python -X utf8 tools/research_wiki.py slug "<title>"` — generate slug
- `uv run python -X utf8 tools/research_wiki.py add-edge '@configured' ...` — add graph edge
- `uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'` — rebuild query_pack
- `uv run python -X utf8 tools/research_wiki.py rebuild-open-questions '@configured'` — rebuild gap_map
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"` — append log
- `uv run python -X utf8 tools/fetch_literature.py search "<query>" --limit 20` — no-key literature search

### Skills
- `/novelty` — Phase 4 deep novelty validation
- `/llm-review` — Phase 4 agent-local critique

### Host capabilities
- Use available web search for Phase 1 retrieval and Phase 3 screening, with the documented literature-search fallback.
- Read the called skill instructions and execute them in the current agent; a host-specific Skill tool is not required.

### Shared References
- `skills/shared-references/review-protocol.md` — brainstorming and review provenance

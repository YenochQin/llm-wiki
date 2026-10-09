---
name: novelty
description: Use when checking whether a research idea or method is genuinely novel — when the user asks if something has been done before, whether an idea is new, or wants a novelty score and recommendations before committing.
argument-hint: "<idea-description-or-slug-or-paper-title> [--quick] [--verbose]"
---

# /novelty

> Assess the novelty of a research idea or method using multiple sources. Searches web search,
> no-key literature search, existing wiki work, and recent web/literature results, then challenges the retrieved evidence in the current agent.
> Outputs a novelty score (1-5) when assessable, closest prior work, differentiation points, and next-step recommendations.
> Can be used standalone or called by /ideate Phase 4.

## Inputs

- `target`: one of the following:
  - free-text description of the idea (a paragraph or a few sentences)
  - slug of an ideas/ page in the wiki (e.g. `sparse-lora-for-edge-devices`)
  - paper title (check novelty of that paper's method)
- `--quick`: skip the agent-local novelty check (Step 3), search only; retain the search-coverage and uncertainty requirements
- `--verbose`: output full search results, not just summaries

## Outputs

- **Novelty Report** (output to terminal, not written to wiki):
  - Novelty Score (1-5), provisional where needed, or not assessed when comparisons cannot be verified
  - List of closest prior work (top 3-5)
  - Differentiation points versus each prior work
  - Agent-local novelty assessment (unless --quick)
  - Recommended action: proceed / modify / abandon
- This skill is a **read-only query** — it does not modify any wiki content

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — search existing papers for similar methods
- `wiki/concepts/*.md` — check concept overlap
- `wiki/ideas/*.md` — check for duplication with existing ideas (especially `failure_reason` of failed ideas)
- `wiki/claims/*.md` — check the current status of claims the idea depends on
- `wiki/graph/context_brief.md` — global context to assist search

### Writes
- **None**. Novelty check is a pure query operation; it does not modify the wiki.

### Graph edges created
- **None**.

## Workflow

**Precondition**: run from the llm-wiki repository root. Resolve the configured external wiki root with `uv run python -X utf8 tools/resolve_path_alias.py '@configured'` and use the returned absolute path for direct reads. `wiki/` below denotes that configured root; do not require or create repository-local content directories.

### Step 1: Extract Method Signature

1. **If target is a slug**: read `wiki/ideas/{slug}.md`, extract title, Hypothesis, Approach sketch
2. **If target is free text**: use directly
3. **If target is a paper title**: query `tools/fetch_literature.py search "<title>" --limit 5` to recover the abstract; if no provider has a match, ask the user for a description
4. Extract the "method signature" from the target — the core elements of the method:
   - **What**: what it does (task / goal)
   - **How**: the method used (technical approach)
   - **Why novel**: claimed innovation
5. Generate 3-5 core keywords for subsequent searches

### Step 2: Multi-Source Search

Record the actual search date and derive the current year `Y` at runtime. Use a rolling recent window from `Y-2` through the search date, alongside searches with no date restriction for older prior art. Apply real date filters when supported; otherwise generate year terms from that window and disclose the filtering limitation. Never reuse literal years from an old example.

Use the available web/literature tools and local file search. Batch independent queries when supported; no additional agent or host-specific Agent tool is required. Cover the following search directions, adapting queries to the method and following gaps rather than treating a query count as sufficient coverage.

**Source A — Web Search:**
1. Direct match: `"<method-name>" "<task>"`, plus aliases and equivalent terminology without a date restriction.
2. Components: `<component-1> <component-2> <domain>` to find earlier combinations.
3. Surveys and foundational work: `("survey" OR "review") <task-area>`; follow relevant older references.
4. Alternatives: `<alternative-approach> <same-task>` to test functional overlap under different method names.
5. Recent work: `<method-keywords>` within the rolling window, including preprints where relevant.

**Source B — no-key literature search:**
```shell
uv run python -X utf8 tools/fetch_literature.py search "<method-keywords>" --limit 20
```
- Inspect the most relevant matches, not merely the most cited or newest ones. Fetch enough primary-source detail to compare the method, task, and claimed contribution:
```shell
uv run python -X utf8 tools/fetch_literature.py paper <doi-or-title>
```

**Source C — Wiki Internal Search:**
1. Scan Key idea and Method sections of all pages in `wiki/papers/`
2. Scan Definition and Variants sections of `wiki/concepts/`
3. Scan all content in `wiki/ideas/`, with special attention to:
   - ideas with status = failed and their failure_reason (anti-repetition)
   - ideas with status = proposed/in_progress (avoid internal duplication)
4. Read `wiki/graph/context_brief.md` for global perspective

**Source D — Recent venues (web search):**
- Select journals, conferences, and preprint sources relevant to the target domain. Search `<method-keywords>` within the same runtime-derived recent window to surface work structured search may miss.

**Coverage and stopping:**
- Keep a compact record of actual queries, sources, date restrictions, verified closest matches, and unresolved gaps. Check a paper's abstract or relevant method text from a primary source before asserting substantive overlap; metadata alone is insufficient.
- After the initial coverage pass, run focused follow-ups for material terminology, component, or citation gaps. Stop when these checks resolve the important comparisons and further targeted searches yield no materially closer work, or when access/tool limits prevent further verification. In the latter case, report limited coverage and the remaining gaps.
- A finished search is bounded evidence, not proof that no prior work exists. With no verifiable comparison, mark novelty unassessed rather than assigning a high score from empty results.

### Step 3: Agent-Local Novelty Check

(Skip if `--quick`.)

Follow `shared-references/review-protocol.md`. In the current agent, challenge the method signature against the closest prior work retrieved in Step 2:

1. Is the method a minor variation or recombination of known techniques? Identify the overlapping components and actual differences.
2. What is the closest existing work? Cite the retrieved source for each material comparison.
3. Give a novelty score of 1–5 with justification when comparisons can be verified; otherwise mark it not assessed. Reserve high scores for a supported new insight or formulation; unsuccessful searches do not prove novelty.
4. If the score is <= 2, suggest concrete changes that could increase differentiation.

Use one evidence-based assessment. Record `agent-local` or `self-review` as appropriate; this pass is not an independent second opinion. If a separate reviewer report is supplied by the user, compare its findings against the sources and preserve unresolved disagreements.

### Step 4: Generate Novelty Report

Synthesize Step 2 search results and Step 3 agent-local assessment into a structured report:

Use `## Score: Not assessed` instead of a numeric score when comparisons cannot be verified. Keep the coverage record concise by default; with `--verbose`, include the full retrieved-result list, actual queries, and verification status.

```markdown
# Novelty Report: {idea title}

## Score: {1-5}/5 — {label}

| Score | Label | Meaning |
|-------|-------|---------|
| 1 | Published | Highly similar published work exists |
| 2 | Very Similar | Very similar method exists, only minor differences |
| 3 | Incremental | Clear incremental contribution over existing work |
| 4 | Novel Combination | Creatively combines existing techniques, producing new insight |
| 5 | Fundamentally New | Proposes an entirely new paradigm or formulation |

## Search Coverage
- Search date: {actual date}; recent window: {runtime-derived range}
- Sources and search directions checked: {compact coverage record}
- Remaining gaps: {unverified matches, inaccessible sources, terminology or date-filter limits}
- Conclusion scope: {bounded by the sources inspected; provisional where needed}

## Closest Prior Work

1. **{title}** ({year}) — {one-sentence description of the similarity}
   - Difference: {key distinction between this method and the prior work}
   - Source: {verified DOI or primary-source link}
   - Wiki link: [[slug]] (if it exists)
2. ...

## Novelty Assessment
{evidence-based assessment; with --quick, mark Step 3 not run}
- Review mode: {agent-local / self-review / quick search only}

## Anti-repetition Check
- Failed ideas in wiki: {list relevant failed ideas with failure_reason}
- In-progress ideas in wiki: {list potentially overlapping ideas}

## Recommendation
- **{proceed / modify / abandon}**
- Rationale: {one paragraph}
- If modify: suggested differentiation directions: {specific suggestions}
```

**Scoring rules (composite judgment):**
- Base any final score on verified comparisons and their limitations; mark it provisional where coverage is limited, or not assessed when no comparison can be verified. Do not manufacture a second score or treat repeated passes as independent corroboration.
- If wiki contains a failed idea whose failure_reason overlaps with this idea → lower score by 1 (keep within 1–5)
- If wiki contains a highly overlapping in_progress idea → mark as abandon (internal duplication)

## Constraints

- **Do not modify the wiki**: novelty check is a pure query; all results are output to terminal only
- **Conservative scoring**: underestimate novelty rather than overestimate to avoid wasting effort on known work
- **Must check failed ideas**: ideas with status=failed in wiki/ideas/ are important anti-repetition signals
- **Search coverage**: cover direct/alias matches, components, surveys/older work, alternative approaches, and recent work across available web, literature, and wiki sources. Report unavailable channels and unresolved gaps; a fixed query count does not establish completeness.
- **Review provenance**: follow review-protocol.md; distinguish the current assessment from any separate report supplied by the user
- **Cite real sources**: all prior work listed in the report must be real (returned by web search/literature search); do not fabricate

## Error Handling

- **web search unavailable**: skip Sources A and D, rely only on literature + wiki search; note limited coverage in report
- **Literature API unavailable**: skip structured literature search, rely on web search + wiki search; note limited coverage in report
- **Prior-work evidence incomplete**: identify which comparisons could not be verified and limit the novelty conclusion accordingly
- **Wiki empty**: proceed with external searches normally; annotate wiki internal search section with "wiki empty"
- **idea slug not found**: prompt user to check the slug, list available slugs in wiki/ideas/

## Dependencies

### Tools
- `uv run python -X utf8 tools/resolve_path_alias.py '@configured'` — resolve the external wiki root
- `uv run python -X utf8 tools/fetch_literature.py search "<query>" --limit 20` — no-key literature search
- `uv run python -X utf8 tools/fetch_literature.py paper <doi-or-title>` — fetch paper details

### Host capabilities
- Use available web search and page retrieval for prior-work discovery and source details, with the documented structured-literature fallback.

### Shared References
- `skills/shared-references/source-grounding.md` — anti-hallucination source-grounding discipline (general)
- `skills/shared-references/review-protocol.md` — agent-local assessment and review provenance

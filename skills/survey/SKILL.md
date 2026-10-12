---
name: survey
description: Use when writing a thematic Related Work section from existing wiki literature for a research question, claim set, or PAPER_PLAN. Returns LaTeX or Markdown prose with verified citations; use /discover when the task is to find additional papers.
argument-hint: "<research-question-or-claim-slugs-or-paper-plan-path> [--format latex|markdown] [--max-papers N]"
---

# /survey

> Generate a Related Work section ready for direct use in a paper, based on existing wiki knowledge.
> Draw material from wiki/papers/, concepts/, topics/; group by research direction (not paper-by-paper listing).
> End each group with a statement of how it differs from this work. Citations follow citation-verification.md;
> writing follows academic-writing.md Related Work rules.
> Supports LaTeX and Markdown output formats.

## Inputs

- `query`: one of:
  - research question description (free text, e.g. "parameter-efficient fine-tuning for LLMs")
  - list of claim slugs (from wiki/claims/, used to organize related work around specific claims)
  - path to PAPER_PLAN.md (extract Related Work section definition from it)
- `--format` (optional, default `latex`): output format
  - `latex`: `\cite{key}` citations, embeddable directly in a paper
  - `markdown`: `[[slug]]` wikilink citations, for wiki archiving
- `--max-papers` (optional, default 30): maximum number of papers to cite

## Outputs

- `wiki/outputs/related-work-{slug}-{date}.md` — Related Work text (archived)
- `wiki/graph/edges.jsonl` — derived_from edges (if a new output is created)
- `wiki/log/` — appended log entry
- **Terminal output** — Related Work body text (for direct copy-paste)

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — Problem, Key idea, Results, Related, My take
- `wiki/concepts/*.md` — Definition, Variants, Comparison, Known limitations
- `wiki/topics/*.md` — Overview, Timeline, Open problems, Seminal works
- `wiki/claims/*.md` — Statement, source_papers (if input is claim slugs)
- `wiki/ideas/*.md` — Motivation (understand this paper's positioning)
- `wiki/index.md` — content catalog, filtered by importance
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/edges.jsonl` — inter-paper semantic relationships (same_problem_as, similar_method_to, complementary_to, builds_on, compares_against, improves_on, challenges, surveys)
- `skills/shared-references/academic-writing.md` — Related Work writing rules
- `skills/shared-references/citation-verification.md` — citation discipline

### Writes
- `wiki/outputs/related-work-{slug}-{date}.md` — archived file
- `wiki/graph/edges.jsonl` — derived_from edges
- `wiki/log/` — appended operation log

### Graph edges created
- `derived_from`: related-work output → source papers

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

### Step 1: Locate Relevant Knowledge

1. **Parse input**:
   - If free text: extract keywords; match against tags and titles in wiki/index.md
   - If claim slugs: read each claim's source_papers; collect related papers
   - If PAPER_PLAN path: read the Related Work section's groupings and citations
2. **Read wiki/graph/context_brief.md** for global context
3. **Read wiki/graph/edges.jsonl**: extract inter-paper semantic relationships (same_problem_as, similar_method_to, complementary_to, builds_on, compares_against, improves_on, challenges, surveys)
4. **Build candidate paper list**:
   - Sort by importance descending from index.md
   - Rank by tags and domain match
   - Cap at `--max-papers` papers
5. **If candidate papers < 5**: warn "insufficient related papers; consider /ingest of more papers first"

### Step 2: Deep-Read Related Pages

For each paper in the candidate list:

1. Read `wiki/papers/{slug}.md`: focus on Problem, Key idea, Results, My take
2. Read linked `wiki/concepts/*.md`: focus on Definition, Variants, Comparison
3. Read related `wiki/topics/*.md`: focus on Timeline, Open problems

Record for each paper:
- core contribution (one sentence)
- method category (which research direction it belongs to)
- relationship to this work (same problem / similar method / complementary / builds on / compares against / improves on / challenges / surveys)
- limitations (extracted from Limitations or My take)

### Steps 3–4: Group and Write

Read [references/thematic-writing.md](references/thematic-writing.md) when organizing and drafting the Related Work text. Group by direction, explain each group's relationship to this work, honor `--format`, and apply the shared writing/polish rules. Use only source-backed characterizations of selected wiki papers.

### Step 5: BibTeX Preparation (--format latex only)

If output format is LaTeX, following `shared-references/citation-verification.md`:

1. Collect all `\cite{key}` citations
2. For each key, attempt to fetch BibTeX: DBLP → CrossRef → `tools/fetch_literature.py` CrossRef wrapper
3. Verified: record BibTeX
4. Unverified: mark `[UNCONFIRMED]`
5. Output list of BibTeX entries (can be appended to the selected manuscript version's references.bib under `<paper_root>/<paper-id>/<draft-id>/`)
6. Report citation coverage

### Step 6: Archive

Read [references/archiving.md](references/archiving.md) when saving the completed text and citation coverage. Archive under the configured external outputs root, add derived edges through the tool, log actual writes, and return the full text; do not modify source wiki entities.

## Source grounding

This skill generates durable content, so it follows the shared **Source Grounding Discipline** — see `skills/shared-references/source-grounding.md`.

- Only cite papers already in the wiki; every characterization of a paper must trace to its wiki page or prepared source.
- Do not invent results, comparisons, or contributions to make the narrative flow — underclaim rather than overclaim.
- BibTeX follows `citation-verification.md` (never from memory). Run a manual grounding self-check: no number or comparison without a source.

## Constraints

- **Only cite papers already in the wiki**: do not fabricate citations; every `\cite{}` or `[[slug]]` must correspond to a page in wiki/papers/
- **Group by theme, not as a flat list**: each paragraph covers a research direction, not "Paper A did X. Paper B did Y."
- **Every group must have a positioning sentence**: state the relationship to this work (at the end — difference or inheritance)
- **Warn when candidate papers < 5**: prompt user to /ingest more papers first
- **BibTeX follows citation-verification.md**: do not generate from LLM memory (--format latex only)
- **De-AI polish is mandatory**: a polish pass must be applied after generation
- **Archive to outputs/**: do not directly modify wiki papers/concepts/topics pages
- **Graph edges via tools/research_wiki.py**: do not manually edit edges.jsonl

## Error Handling

- **Fewer than 3 wiki papers**: error; suggest /ingest of enough papers first
- **No matching papers**: broaden search scope (relax tag matching); if still none, error
- **All BibTeX fetches failed** (latex format): use [UNCONFIRMED] placeholders; report count
- **PAPER_PLAN format mismatch**: ignore plan's grouping suggestions; use automatic grouping
- **Slug conflict**: append date suffix

## Dependencies

### Tools
- `uv run python -X utf8 tools/research_wiki.py slug "<title>"` — generate slug
- `uv run python -X utf8 tools/research_wiki.py add-edge '@configured' ...` — add graph edge
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"` — append log
- `uv run python -X utf8 tools/fetch_literature.py search "<title>"` — BibTeX fallback (no-key literature search)

### MCP Servers
- None (use /llm-review --focus writing for agent-local review if requested)

### Host capabilities
- Read/search local wiki pages.
- For LaTeX output, fetch bibliographic metadata through available web tools or `tools/fetch_literature.py`; keep unavailable citations `[UNCONFIRMED]`.

### Shared References
- `skills/shared-references/academic-writing.md` — Related Work writing rules + de-AI polish
- `skills/shared-references/citation-verification.md` — BibTeX fetch and [UNCONFIRMED] protocol

### Called by
- `/paper-draft` Step 3 (Related Work section can be delegated to this skill)
- Manual user invocation

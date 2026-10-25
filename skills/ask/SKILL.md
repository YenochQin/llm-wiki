---
name: ask
description: Answer questions from the wiki's accumulated knowledge by retrieving and synthesizing existing pages with citations. Read-only; saving answers or changing wiki content belongs to /edit.
argument-hint: "<question> [--format markdown|table|timeline|bullets]"
---

# /ask

> Answer questions from existing wiki knowledge with citations and explicit uncertainty. This skill reads and answers only; `/edit` handles requested saves and modifications.

## Inputs

- `question`: natural-language question (e.g. "What is the core difference between LoRA and Adapter?").
- `--format` (optional, default `markdown`): `markdown` / `table` / `timeline` / `bullets`.

## Outputs

- Answer in the conversation, with `[[slug]]` citations to existing wiki pages.
- Retrieved-page references, relevant claim confidence/status, and any evidence gaps or limitations.

## Wiki Interaction

### Reads

- `wiki/graph/context_brief.md` and `wiki/graph/open_questions.md`, when present.
- `wiki/index.md`, when present, and `wiki/graph/edges.jsonl` for relevant relationships.
- Experiment records under `@experiment-root/` remain eligible evidence. Resolve that alias when the question needs experiments; resolve `@output-root` only when retrieving saved reports.
- Relevant pages under `papers/`, `concepts/`, `topics/`, `people/`, `ideas/`, `claims/`, `Summary/`, and `foundations/`.

### Writes

- None. Do not create, modify, or delete wiki content, raw inputs, repository files, or configuration. This includes reports, logs, index updates, derived-graph rebuilds, and initialization.

### Graph edges created

- None.

## Workflow

**Precondition**: run from the llm-wiki repository root. Resolve the configured external wiki root with the read-only path resolver, then use its absolute path for file reads. `wiki/` below denotes that configured root.

```shell
uv run python -X utf8 tools/resolve_path_alias.py '@configured'
```

### Step 1: Load Available Context

1. Read `graph/context_brief.md` and `graph/open_questions.md` if they exist.
2. Read `index.md` if it exists. Missing index or derived files are navigation limitations, not a reason to write: locate relevant pages directly under the page-type directories.
3. If the context appears stale, verify it against the current pages. Do not repair or regenerate it during the query.

### Step 2: Retrieve Relevant Pages

1. Match question keywords and entities against the available catalog, context, page filenames, titles, and content.
2. Rank relevant pages and read at most 15 full pages. Search additional page text selectively when needed.
3. For relationship questions, read relevant existing graph edges and page links. If graph files are absent, use the page links and disclose coverage limits.

### Step 3: Synthesize the Answer

1. Answer from the retrieved content using the requested `--format`.
2. Cite each key assertion with an existing `[[slug]]`; distinguish recorded findings from your synthesis or inference.
3. When citing a claim, include its recorded confidence and status. Report disagreements and insufficient evidence without inventing a resolution.
4. Identify relevant known gaps. When the wiki cannot answer, state the limitation and suggest useful search or ingest directions without running a write workflow.

### Step 4: Return the Answer

Return the answer, the retrieved-page references, and material gaps. End the query without logging or changing files.

If the user explicitly requests saving this answer or modifying a page, handle that as a separate `/edit` operation under `skills/edit/SKILL.md`, preserving the original question, citations, and uncertainty. Existing authorization for that operation remains valid; do not request it again. Do not start `/edit` merely because an answer seems worth saving.

## Constraints

- **Strictly read-only**: no content writes, report files, logs, graph maintenance, index repair, or initialization. No automatic save or write-back mode.
- **Source-grounded answers**: use actual wiki content; do not fill evidence gaps from model memory or external search.
- **Existing citations only**: every `[[slug]]` citation must resolve to an existing wiki page.
- **Preserve uncertainty**: keep source scope, qualifications, claim confidence/status, and unresolved gaps visible.
- **No automatic handoff**: answering does not authorize edits; use `/edit` only for a user-requested save or modification.

## Error Handling

- **Missing index or derived files**: read relevant pages directly and note the navigation limitation; continue without creating files.
- **Wiki empty or no matching pages**: state that the wiki has no supporting content; suggest `/init`, `/ingest`, or search directions as appropriate, without invoking them.
- **Configured wiki root missing or invalid**: report the configuration issue and available read-only limitations; do not initialize a replacement wiki or modify configuration.

## Dependencies

### Tools

- `uv run python -X utf8 tools/resolve_path_alias.py '@configured'` — read-only path resolution.
- Native file reads and text searches — retrieve existing wiki content.

### Shared References

- `.claude/skills/shared-references/source-grounding.md` — source-grounded answers and uncertainty.

### Related Skills

- `/edit` — user-requested answer archiving or wiki modifications.
- `/ingest` — referenced when recommending additional source-backed knowledge.

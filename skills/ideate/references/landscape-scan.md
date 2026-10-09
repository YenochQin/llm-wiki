# Landscape Retrieval for Ideation

Read this reference during Phase 1 retrieval, before constructing candidate ideas. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

1. **Load available wiki internal context**:
   - Read `wiki/graph/context_brief.md` and `wiki/graph/open_questions.md` when present; otherwise find relevant pages directly.
   - Empty directories contribute empty lists. An empty banlist or gap list is valid; record it rather than waiting for wiki population.
   - Read all `wiki/ideas/*.md`, extract:
     - status=failed ideas → **banlist** (with failure_reason)
     - status=proposed/in_progress ideas → **active list** (avoid duplication)
   - Read `wiki/claims/*.md`, find claims with status=weakly_supported or challenged → **weak claims list**
   - If `direction` is specified, filter to the relevant subset

2. **External search** (use available search tools):
   - **Web search**: derive a rolling six-month window from the actual search date and search for papers and advances in the target direction (3–5 initial queries). Also search without a date restriction for foundational work; record unresolved coverage gaps.
   - **No-key literature search**:
     ```shell
     uv run python -X utf8 tools/fetch_literature.py search "<direction-keywords>" --limit 20
     ```
     Fetch details for the top 5 highly-cited papers
   - **Web search (recent venues)**: select venues relevant to the direction and search `<direction-keywords>` using the same runtime-derived recent window. Prefer supported date filters; otherwise generate year terms from the window and note that limitation. Query counts guide effort, not claims of complete coverage.

3. **Compile landscape report** (internal use, not written to wiki):
   - Current SOTA methods and performance
   - Known open problems / unresolved challenges
   - Recent trends and hot topics
   - Knowledge gaps in the wiki (from gap_map)
   - Prohibited directions (from banlist)

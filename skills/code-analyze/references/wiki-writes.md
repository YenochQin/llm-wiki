# Optional Code Analysis Writes

Read this reference only when `--write` or `--crystallize` authorizes wiki writes. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

### Step 7: Archive (`--write` only)

1. Generate the slug:

   ```bash
   uv run python -X utf8 tools/research_wiki.py slug "code process analysis {target-name}"
   ```

2. Resolve the configured wiki root before direct edits:

   ```bash
   uv run python -X utf8 tools/resolve_path_alias.py @configured
   ```

3. Create `outputs/code-analysis-{slug}-{date}.md` with `artifact_type: code_analysis`, the
   objective, target, date, cited wiki pages, and repository path/branch/commit/dirty metadata.
4. Update `index.md` only if the current index lists outputs.
5. Append the log through the tool:

   ```bash
   uv run python -X utf8 tools/research_wiki.py log @configured "code-analyze | {target} | objective: {objective} | output: outputs/{slug}.md"
   ```

6. Add useful `derived_from` edges for cited wiki pages through `research_wiki.py add-edge`.

### Step 8: Crystallize (`--crystallize` only)

Crystallize only durable research knowledge, such as an implemented algorithmic mechanism, a
verifiable claim embodied by the computation, a runnable evaluation, or a research gap revealed
by the processing design.

Before creating or editing pages, open `docs/runtime-page-templates.en.md`. Keep forward and
reverse links synchronized. Explain code provenance explicitly and do not fabricate paper
citations for code-grounded concepts.

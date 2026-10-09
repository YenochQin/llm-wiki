# Related Work Archiving

Read this reference when archiving the completed Related Work text and reporting citation coverage. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

1. **Generate slug**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py slug "<query-keywords>"
   ```

2. **Write archive file**:
   Create `wiki/outputs/related-work-{slug}-{date}.md`:
   ```yaml
   ---
   title: "Related Work: {topic}"
   type: related-work
   format: {latex|markdown}
   paper_count: {N}
   date_generated: YYYY-MM-DD
   ---
   ```
   Body is the complete Related Work text.
   If latex format: append BibTeX entries as an appendix.

3. **Add graph edges**:
   ```shell
   # output → each cited paper
   uv run python -X utf8 tools/research_wiki.py add-edge '@configured' --from "outputs/related-work-{slug}-{date}" --to "papers/{paper-slug}" --type derived_from --evidence "Cited in related work section"
   ```

4. **Append log**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py log '@configured' "survey | {topic} | {N} papers, {G} groups, format: {format}"
   ```

5. **Terminal output**: complete Related Work body text + citation coverage statistics

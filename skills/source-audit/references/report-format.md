# Source Audit Batch Report

Read this reference when formatting the batch findings and next-batch continuation. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Use this structure for every batch:

```markdown
# Source-Grounded Audit — YYYY-MM-DD

## Batch
- **Type**: papers
- **Range**: {first slug} … {last slug}
- **Linked expansion**: off | on, linked pages: N
- **Mode**: report-only | fix | dry-run
- **Source root**: `{configured wiki root}/sources`

## Source Resolution
- `papers/{paper-slug}.md` → `sources/papers/{source-slug}.md` (page link | source metadata | manifest | legacy lookup); list every resolved source when there are several.
- Broken links / unresolved mappings: none | exact targets and the reason resolution failed.

## Summary
- Critical: N
- Major: N
- Minor: N
- Source blockers: N
- Grounding gate red issues: N
- Pages checked: N

## Grounding Gate
- Command: `uv run python -X utf8 tools/grounding_lint.py ... --json`
- Result: passed | red issues found
- Red issues:
  - `{file}` `[category]`: message, mapped to `[severity][issue-class]`.

## Findings

### [[slug]]

1. **[Major][CLASSIFICATION_ERROR] Short title**
   - **Source location**: `{source file}` heading/table/figure/line if available.
   - **Source text**: short exact quote from the prepared source.
   - **Wiki location**: `wiki/papers/{slug}.md` field/section/paragraph/table row, or `missing`.
   - **Wiki text / missing coverage**: exact wiki text, or the source-backed point absent from the wiki.
   - **Mismatch type**: contradiction | fabricated or unsupported addition | omitted source fact | overgeneralization | wrong number/unit | excerpt mismatch | classification mismatch | metadata mismatch | grounding-gate failure.
   - **Why this is a problem**: explain the non-correspondence between the quoted source and the wiki.
   - **Required correction**: precise replacement, deletion, or addition.

## Proposed Edits
- `wiki/papers/{slug}.md`: exact field/section edits, or `none`.
- Linked pages: exact `concepts/{slug}.md` / `claims/{slug}.md` edits, or `none`.

## Next Batch
- Continue with: `/source-audit --type papers --batch-size 5 --start-after {last slug}`
```

If no issues are found for a page, include:

```markdown
### [[slug]]
- No source-grounding issues found after source-to-wiki alignment in the audited scope.
```

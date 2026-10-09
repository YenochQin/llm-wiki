# Code Process Report Format

Read this reference when assembling a code process analysis report. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Use this structure unless the user requests another shape:

```markdown
# Code Process Analysis: {target}

## Scope and Objective

## Entry Point and End-to-End Summary

## Global Processing Model

## Stage-by-Stage Analysis

### Stage 1: {name}
- Code:
- Input:
- Processing:
- Output:
- Formula:
- Formula-to-code correspondence:

## Branches, Iteration, and State

## Final Output Construction

## Uncertainties and Unresolved Paths

## Research Wiki Mapping
```

For every stage, place the implementation explanation beside its formula so the correspondence is
auditable. After the stage analysis, include the composed end-to-end formula and explain which
code component implements each operator. Use `$...$` for inline math and `$$...$$` for display
math in both wiki files and user-facing output.

Keep quotations short. Prefer precise paraphrases with line-specific file references. Do not add
generic risk or test-gap sections outside the user's chosen direction.

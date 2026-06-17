# Light Paper Page

Use this shape for `/ingest-light` paper pages. The goal is citation utility and introduction-writing retrieval, not full graph extraction.

## Frontmatter

Use the normal `papers/{slug}.md` schema and keep fields parseable:

```yaml
---
title: ""
slug: ""
paper_type: paper
venue: ""
year:
tags: [thesis-introduction, light-ingest, background]
research_modes: []
theory_tags: []
computation_tags: []
experiment_tags: []
research_object_tags: []
importance: 2
date_added: YYYY-MM-DD
source_type: pdf
external_ids: {}
keywords: []
domain: "atomic-structure"
code_url: ""
cited_by: []
---
```

Role tags:

- `background`
- `method-foundation`
- `benchmark`
- `application`
- `gap-evidence`
- `review-context`

If the paper already has a full `/ingest` page, do not degrade it. Add missing `thesis-introduction`, `light-ingest`, and role tags only when appropriate, then append/update `## Introduction use`.

## Body

Required sections:

```markdown
# Title

## Evidence Pack

- `E1` <UseLabel> — <short label> ([prepared markdown](../sources/papers/<source-slug>.md), <source section>): ^E1
  > exact source fragment

## Problem

One short paragraph on what the paper is about.

## Key idea

One short paragraph on the main contribution or framing.

## Research classification

- paper_type: ...
- research_modes: ...
- research_object: ...
- introduction role: ...
- role rationale: ...

## Introduction use

How this paper should be used in the dissertation introduction. Be concrete:
- background motivation
- method lineage
- benchmark data
- application context
- gap evidence

Start this section with:

```markdown
Primary role: `<role>` — <one sentence explaining why this paper has that role in the introduction>.
```

If the paper has secondary uses, add them after the primary role sentence, but do not duplicate the paper across many Summary subsections unless the user requests that.

## Evidence notes

Short notes on facts or claims useful for the introduction. These are not wiki `claims/` unless the user later upgrades the paper.

## Limitations

Known limitations, scope limits, or reasons this paper is background-only.

## BibTeX

```bibtex
...
```

## Related

- [[thesis-introduction-literature]] — <role> citation for dissertation introduction
```

## Rules

- Keep it compact: one to three paragraphs per prose section.
- Do not invent details absent from metadata/prepared source.
- `## Evidence Pack` is mandatory and must use the exact card shape shown above. Replace placeholders only. The readable id stays at the start as `` `E1` ``; the Obsidian block id goes at the end as `^E1`; prose cites cards with the literal Obsidian block-link string `[[#^E1]]`. The outer double brackets `[[...]]`, leading `#`, and one literal space before the citation are mandatory. Write `... finding [[#^E1]]`, never `... finding[[#^E1]]`. Never use invalid citation forms such as `[#^E1]`, `[[^E1]]`, `#^E1`, `^E1`, or legacy `[!E1]`; never start a card with `^E1`, and never replace `` `E1` `` with `^E1`.
- Prefer Zotero BibTeX. Never put BibTeX in YAML frontmatter.
- Use Obsidian wikilinks for internal pages and ordinary markdown links for prepared source files.
- Do not create concept, claim, or people pages from a light ingest.

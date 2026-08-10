# Phase C — Paper page

> 中文运行提示：执行本 phase 时请用中文向用户汇报；命令、路径、字段名、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。


> Shared ingest phase. Frontmatter fields and body sections are defined in `docs/runtime-page-templates.en.md` §papers. Quality floor: `.claude/skills/ingest/references/content-quality-gate.md`. Obeys `.claude/skills/shared-references/ingest-invariants.md`.

## Purpose

Write the paper page from the Evidence Pack cards — structured, source-faithful, and reconstructable later without reopening the source.

## Steps

1. **Emit frontmatter per the template.** Fill every required key; leave `cited_by` empty (Phase D/E backfills). `bibtex` is never in frontmatter (invariants §6).
2. **Populate body sections** (template §papers): `## Evidence Pack` (from Phase B) / `## Problem` / `## Key idea` / `## Research classification` / `## Method` / `## Results` / `## Limitations` / `## Open questions` / `## My take` / `## BibTeX` / `## Related`.
3. **Anchor structure to the prepared frontmatter** (`sections`, `figures`, `abstract_excerpt`). Name source sections, figures, tables, algorithms, equations in `## Method` / `## Results`; avoid generic summaries that fit any paper.
4. **`## Research classification`** must explicitly state, per active direction: which theory/model/framework (theory), which numerical/simulation/statistical/ML/data-analysis scheme (computation), which observational/lab/sample/instrument/protocol process (experiment), and the research object(s). `unclear` where the source does not say.
5. **`## BibTeX`** carries the Zotero/Crossref-derived entry as a fenced ```bibtex block, citation-core only (invariants §6).
6. **`## Related`** follows the fixed label order and bullet shape in invariants §8, listing only touched concepts/claims/foundations/topics/people and existing-or-same-run paper slugs.
7. Math uses `$`/`$$` only (invariants §4).

## Gate C — output this block before Phase D; if any line is ✗, stop and fix

```text
[Gate C] paper page  papers/{slug}.md
- frontmatter YAML parses: ✓/✗
- required keys present & non-empty (incl. paper_type, research_modes, research_object_tags): ✓/✗
- bibtex absent from frontmatter: ✓/✗
- importance ∈ {1..5}: ✓/✗
- all body sections present (Evidence Pack…Related): ✓/✗
- Research classification names theory/computation/experiment + objects (or unclear): ✓/✗
- LaTeX uses $/$$ only (no code-fence eqns, no \( \)): ✓/✗
- wikilinks slug-only; no directory prefixes; no dangling paper links: ✓/✗
- BibTeX is citation-core only: ✓/✗
```

Run the scoped grounding gate on the paper page; fix any `level: red` before continuing (do not downgrade to warning):

```shell
uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only "papers/{slug}.md" --json
```

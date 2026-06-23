---
name: reingest-force
description: Use when an existing paper page or its paper-derived entities are so wrong that normal /reingest would be contaminated by bad wiki state, and the paper must be rebuilt from source with the existing page identity reused but old content ignored.
argument-hint: "<local-pdf-or-wiki/sources/papers/*.md> [--paper-only] [--discover]"
---

# /reingest-force

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> 内容语言提醒：写入正式 wiki 页面时遵守 `AGENTS.md` 的正式页面语言规范；除非用户明确要求中文，页面正文默认使用英文，source excerpts 保持原语言。

Rebuild an existing `wiki/papers/{slug}.md` in **clean-room mode**. Use this when the current paper page is badly wrong and you do **not** want old `papers/`, `concepts/`, `claims/`, or `people` content derived from that paper to steer the new ingest.

`/reingest-force` reuses the **same phase pipeline as `/ingest`**, but keeps `/reingest`'s existing-page match requirement: the page must already exist, and the regenerated result is written back to that page path. `--paper-only` skips entity rebuilding. `--discover` behaves the same as `/reingest`.

## Always-on references

- `i18n/en/shared-references/ingest-invariants.md`
- `i18n/en/shared-references/source-grounding.md`
- `docs/runtime-page-templates.en.md`
- `i18n/en/shared-references/ingest-phases/phase-a-source-identity.md`
- `i18n/en/shared-references/ingest-phases/phase-b-evidence-pack.md`
- `i18n/en/shared-references/ingest-phases/phase-c-paper-page.md`
- `i18n/en/shared-references/ingest-phases/phase-d-knowledge-graph.md`
- `i18n/en/shared-references/ingest-phases/phase-e-navigation-finalize.md`

## What Force Means

- Match the existing paper page by prepared `paperSlug`/`sourceSlug`, DOI, title, or page path. If no existing page matches, stop and tell the user to use `/ingest`.
- Refresh the canonical prepared source first. If the input is a PDF, overwrite `wiki/sources/papers/<source-slug>.md` via `tools/prepare_paper_source.py --overwrite`.
- Treat the refreshed source as the **only factual authority** for this run.
- Do **not** preserve old paper body sections, custom sections, prior analysis text, or old paper-derived summaries.
- Do **not** use the old paper page or connected entities as evidence sources. They are migration targets and dedup targets only.
- Keep repository-wide safety rules: never edit `raw/`; never manually edit `graph/`; never silently delete concept/claim/people pages or old evidence entries.

## Workflow

### Phase A — refresh source + resolve existing page

Follow ingest Phase A for source refresh and identity checks, then resolve the existing page:

```shell
uv run python -X utf8 tools/research_wiki.py find '@configured' papers --slug "<slug>"
```

If the page does not exist, stop and suggest `/ingest`.

### Phase B + Phase C — full paper rewrite

Run ingest Phases B and C from the refreshed source. Ignore the old `papers/<slug>.md` body completely.

- Re-extract the Evidence Pack from the refreshed source.
- Rewrite the paper page to the current paper template as if this were a first ingest.
- Reuse only stable page identity that is still valid and independently supported, such as the matched page path and durable metadata recoverable from source or bibliography.
- Do not carry forward old custom sections, old `## Related`, or previous inline claims just because they already exist.

### Phase D — entity rebuild on current source only

Skip this phase when `--paper-only` is set.

Run ingest Phase D with one extra rule: existing connected entities are **not** trusted knowledge inputs.

- Re-extract concepts, claims, and people from the refreshed source first.
- Use existing pages only for identity matching, dedup, backlink repair, and schema migration.
- If an existing concept/claim/people page conflicts with the refreshed source, overwrite the paper-derived parts from source and mark unsupported old paper-derived material stale or report it for review.
- Never let old evidence anchors, old paraphrases, or old `## Related` structure decide the new result.

### Phase E — finalize exactly like ingest-family refresh

Run index/context/open-question rebuilds, scoped lint, scoped grounding lint, and log the run. `--discover` follows the same optional follow-up rule as `/reingest`: append only gated candidates to `@configured/outputs/ingest-candidates.md`.

## Report

State all of the following:

- refreshed source path
- matched paper page
- whether `--paper-only` was used
- that this was a **force clean-room rebuild**
- entity rebuild summary
- stale/ambiguous old pages or links that still need review
- lint and grounding-lint result

Close with:

```text
Wiki: reingested-force papers/<slug> | updated: <list> | lint: <summary>
```

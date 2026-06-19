---
name: reingest
description: Regenerate an already-ingested paper page from its raw PDF or prepared MinerU markdown, refreshing paper analysis and migrating affected concept/claim/people pages when the new source changes the wiki's knowledge.
argument-hint: "<local-pdf-or-wiki/sources/papers/*.md> [--paper-only] [--update-entities] [--refresh-metadata] [--discover]"
---

# /reingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> 内容语言提醒：写入正式 wiki 页面时遵守 `AGENTS.md` 的正式页面语言规范；除非用户明确要求中文，页面正文默认使用英文，source excerpts 保持原语言。

Regenerate an existing `wiki/papers/{slug}.md` from a raw PDF or prepared `mineru-md` source. Use this when the PDF→markdown adapter changed, the paper template changed, or the previous ingest was incomplete. `/reingest` runs the **same phase pipeline as `/ingest`** with the deltas below, and **after each phase prints that phase's Gate block**. Entity migration (`--update-entities`) is the default; `--paper-only` disables it.

## Phases (run in order; print each Gate, applying the reingest deltas)

- Phase A — `.claude/skills/shared-references/ingest-phases/phase-a-source-identity.md`
- Phase B — `.claude/skills/shared-references/ingest-phases/phase-b-evidence-pack.md`
- Phase C — `.claude/skills/shared-references/ingest-phases/phase-c-paper-page.md`
- Phase D — `.claude/skills/shared-references/ingest-phases/phase-d-knowledge-graph.md` (run as **entity migration**)
- Phase E — `.claude/skills/shared-references/ingest-phases/phase-e-navigation-finalize.md`

Phase B re-extracts cards from the refreshed source and prints Gate B before Phase C rewrites `## Evidence Pack` as the first body section.

## Always-on references

- `.claude/skills/shared-references/ingest-invariants.md` — path / Zotero / slug / LaTeX / wikilink / BibTeX / edge rules
- `docs/runtime-page-templates.en.md` — page shape + Evidence Pack card shape (single source of truth)
- `.claude/skills/shared-references/source-grounding.md` — anti-hallucination discipline

## Scope

`/reingest` updates the paper page, its canonical prepared source, and affected knowledge entities. It is **not a reset**:

- `raw/papers|notes|web` remain read-only.
- `wiki/sources/papers/<source-slug>.md` may be overwritten via `tools/prepare_paper_source.py --overwrite`. When overwriting, preserve portable Zotero provenance: a PDF under a Zotero `storage/` must yield frontmatter `source` = `${Zotero data directory}/storage/<attachment-key>/<file>.pdf`, never the generating machine's absolute path.
- Entity migration is enabled by default; `--paper-only` disables it for this run.
- Never delete concept/claim/people pages. Append/qualify/supersede; mark obsolete entities stale where the schema supports it and report them. Never delete old evidence entries.
- Preserve user-created custom sections unless the user asks for a full rewrite.
- `--item-key` is not a user-facing paper selector (invariants §2). Match the existing paper from prepared `paperSlug`/`sourceSlug`, DOI, title, or page path.

## Phase deltas

### Phase A delta — refresh source + match existing page
- If input is a PDF, prepare with `--overwrite` (carry `--citation-key`/`--authors`/`--year`; `--title` only when confidently recovered). If input is a prepared `*.md`, use it directly. For DOI/title-only Zotero refresh, follow invariants §2.
- Resolve the **existing** paper page (slug per invariants §3). Look it up:
  ```shell
  uv run python -X utf8 tools/research_wiki.py find '@configured' papers --slug "<slug>"
  ```
  (`find`'s second positional arg is an entity directory like `papers`; do not pass `papers/<slug>`.) If the page does **not** exist, stop and suggest `/ingest`; never silently create a new page.
- Read the existing page and preserve `cited_by`, stable identity not in the new source (`external_ids`, `code_url`, curated `importance` rationale), existing `## Related` links still valid, and any non-template custom section.

### Phase C delta — write to the existing page
Regenerate analysis into the existing page (do not create a new one), regenerating `## Evidence Pack` first. Use the retained bibliography to resolve inline references; do not cite references absent from bibliography/metadata.

### Phase D delta — entity migration + template migration (skip if `--paper-only`)
Review entities connected to the old or regenerated page: pages in old/new `## Related`; concepts whose `key_papers` include this paper; claims whose `source_papers`/`evidence[].source` include it; linked people; graph neighbors (`tools/research_wiki.py neighbors '@configured' papers/<slug>`). For each, compare old statement vs regenerated source **and** audit current page shape against `docs/runtime-page-templates.en.md`. A source-faithful entity is not automatically skippable: if its frontmatter, provenance shape, required sections, or source anchors are stale, migrate it to the current template even when the prose meaning is already correct.
- **Concepts**: update Definition, Source excerpts (exact excerpts linked to refreshed prepared markdown), Variants, Known limitations, Open problems, aliases, related_concepts, `date_updated`; keep `key_papers`.
- **Claims**: always audit every connected claim against the current claim template before deciding it needs no edit. Required checks: frontmatter has all current keys (`status`, `confidence`, `tags`, `domain`, `source_papers`, `evidence`, `conditions`, dates); `source_papers` and `evidence[].source` are slug-only; each evidence item has `source_anchor`, `type`, `strength`, `source_section`, and `detail`; `source_anchor` is an Evidence Pack id only (`E1`, not `^E1` or `[[#^E1]]`); body has `## Statement`, `## Evidence summary`, `## Conditions and scope`, `## Counter-evidence`, `## Linked ideas`, and `## Open questions`. If any check fails, edit the claim even if the claim statement is already supported by the paper. Update Statement/Evidence/Conditions/Counter-evidence/`confidence`/`status`/`date_updated` when needed; **append** new evidence/counter-evidence, do not delete old. Provenance YAML stays structured (invariants §7).
- **People**: refresh affiliation/areas/recent work/collaborators/key papers.
- New concept/claim → `find-similar-*` first; prefer migrating over creating duplicates. Ensure reverse links/evidence for every regenerated link. Add semantic edges with `add-edge` (invariants §8). Do not auto-remove old edges; report ones the regenerated page no longer supports as "possibly stale".

### Phase E delta — rebuild + validate
Run `rebuild-index`, `rebuild-context-brief`, `rebuild-open-questions`, then scoped `lint.py` and `grounding_lint.py --only` on touched `papers/`/`concepts/`/`claims/`, then `log "reingest | refreshed papers/<slug> | updated: <list>"`. Fix any `grounding_lint` `level: red` before reporting; fix deterministic `lint` issues unless that would delete user-authored content. The final report must state how many connected claims were template-audited and how many were migrated for template/schema reasons even when their source-grounded content was already acceptable.

## Report

Summarize: refreshed source path + warnings; paper page updated; entity migration summary (reviewed/updated/created/marked-stale); edges/citations added; stale or ambiguous old links needing review; lint + grounding_lint result. Close with:

```text
Wiki: reingested papers/<slug> | updated: <list> | lint: <summary>
```

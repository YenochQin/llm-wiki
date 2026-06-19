# Phase D — Knowledge graph

> 中文运行提示：执行本 phase 时请用中文向用户汇报；命令、路径、字段名、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。


> Shared ingest phase. Dedup rules: `.claude/skills/ingest/references/dedup-policy.md`. Cross-reference matrix and edge-type selection: `.claude/skills/ingest/references/cross-references.md`. Page floors: `.claude/skills/ingest/references/content-quality-gate.md`. Obeys `.claude/skills/shared-references/ingest-invariants.md`.

> **INIT MODE**: skip reverse-link edits to pre-existing pages and skip `fetch_literature.py citations/references`; record relationships via `add-edge` only — the parent `/init` backfills at fan-in. See `.claude/skills/ingest/references/init-mode.md`.
>
> **`/ingest-light`**: skip this phase's claims, people, and semantic edges by default.
>
> **`/reingest`**: run this phase as *entity migration* and *template migration* — append/qualify/supersede, never delete a page or an old evidence entry; mark obsolete entities stale where the schema allows. Do not skip an entity merely because its prose is source-faithful; first audit whether it matches the current template/schema.

## Purpose

Connect the paper into the reusable knowledge graph: concepts, claims, people, paper-to-paper edges, and citations — with every forward link's reverse written in the same turn.

## Steps

1. **Dedup before create.** For each candidate concept/claim, call `find-similar-concept` / `find-similar-claim` first and apply the decision rule in `dedup-policy.md` (default = merge; create only with a clear distinction, within the per-paper limit).
2. **Concepts**: fill all mandatory sections (template §concepts + quality floor), including `## Source excerpts` (≥2 substantively different exact excerpts when the source covers the concept in multiple passages) and a research-direction connection sentence in `## My understanding` (or a one-line scoped reason / `_no research-direction anchor file found_`).
3. **Claims**: structured provenance YAML only (invariants §7 / template §claims); fill all mandatory sections; keep `confidence` conservative. In `/reingest`, every connected claim must be audited against the current claim template before it can be marked "no edit": required frontmatter keys, slug-only `source_papers` / `evidence[].source`, complete evidence fields (`source_anchor`, `type`, `strength`, `source_section`, `detail`), Evidence Pack id-only anchors, and all required body sections. Template/schema drift is sufficient reason to edit, even when the claim statement is already supported by the refreshed paper.
4. **People**: create only for importance ≥ 4; otherwise append to existing author pages.
5. **Reverse links**: every forward link writes its reverse in the same turn, per the cross-reference matrix. Foundations are terminal (no reverse).
6. **Paper-to-paper edges + citations** (skip in INIT MODE): `fetch_literature.py references|citations`; add a `cites` row for each reference resolving to an existing paper; add a semantic edge only on a clear source cue (type per `cross-references.md`, with `--confidence` + `--evidence`); backfill `cited_by`.
7. **Floor**: importance ≥ 4 papers create/update ≥1 claim, or the report names the exception (purely bibliographic/editorial sources).

## Gate D — output this block before Phase E; if any line is ✗, stop and fix

```text
[Gate D] knowledge graph
- find-similar-* called for every new concept/claim: ✓/✗
- concepts touched: <n> (all mandatory sections + ≥2 source excerpts where warranted): ✓/✗
- claims touched: <n> (structured provenance YAML; conservative confidence): ✓/✗
- /reingest only: every connected claim template-audited; stale claim templates migrated or listed with blocker: ✓/✗ / n.a.
- importance≥4 ⇒ ≥1 claim, else exception named: ✓/✗ / n.a.
- people created only if importance≥4: ✓/✗
- every forward link has its reverse this turn (INIT MODE: edges only): ✓/✗
- semantic edges carry --confidence + --evidence: ✓/✗
- per-paper creation limit respected: ✓/✗
```

Run the scoped grounding gate on touched concept/claim pages; fix any `level: red` before continuing:

```shell
uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only "concepts/{touched}.md" --only "claims/{touched}.md" --json
```

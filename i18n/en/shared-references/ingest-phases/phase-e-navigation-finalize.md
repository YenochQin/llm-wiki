# Phase E — Navigation and finalize

> Shared ingest phase. Index/log/graph formats: `docs/runtime-support-files.en.md`. Obeys `.claude/skills/shared-references/ingest-invariants.md`. This phase owns the **single** final self-check for the whole ingest — there is no second copy elsewhere.

> **INIT MODE**: skip topic writes, `rebuild-context-brief`, and `rebuild-open-questions` (the parent `/init` runs them at fan-in); still write the log and commit inside the worktree on success. See `.claude/skills/ingest/references/init-mode.md`.

## Purpose

Place the paper in topics/Summary, refresh navigation, log the run, and run the consolidated final self-check before reporting.

## Steps

1. **Topic placement**: match domain/tags against `@configured/topics/*.md`. importance ≥ 4 → `## Seminal works`; importance < 4 → `## SOTA tracker` / `## Recent work` by year; annotate any addressed open problem. Record matched count `N`. Do **not** create topic pages (that is `/edit` / `/init`); if `N=0`, suggest `/edit` in the report.
2. **Summary placement**: if a `@configured/Summary/*.md` scope covers the paper, append under `## Key references` / `## Related`. Record `S`. Do not create Summary pages; if `S=0`, surface it.
3. **Index**: `uv run python -X utf8 tools/research_wiki.py rebuild-index '@configured'`.
4. **Log** (always): `uv run python -X utf8 tools/research_wiki.py log '@configured' "ingest | added papers/<slug> | updated: <list>"`.
5. **Rebuild** (skip in INIT MODE): `rebuild-context-brief` and `rebuild-open-questions`.
6. **Report**: pages created/updated, edges added, `Topic placement: matched N; Summary placement: matched S`, contradictions, and follow-up candidates only if they pass the structured candidate gate (title + authors + year + DOI + Zotero status + relation evidence; otherwise omit). Close with `Wiki: +1 paper, +{N} claims, +{M} concepts, +{K} edges`.

## Gate E — consolidated final self-check; output this block; if any line is ✗, fix before reporting

```text
[Gate E] final
1. papers/{slug}.md exists & frontmatter YAML parses: ✓/✗
2. Evidence Pack meets coverage floor (per populated section + per concept + per claim): ✓/✗
3. grounding_lint --only (paper + touched concepts/claims) has no red: ✓/✗
4. ≥1 concept created/updated with all mandatory sections: ✓/✗
5. importance≥4 ⇒ ≥1 claim, else exception named in report: ✓/✗ / n.a.
6. graph/edges.jsonl has ≥1 edge involving the new paper: ✓/✗
7. current weekly log has a [today] entry under ## ingest: ✓/✗
8. index.md includes the new paper and all new entities: ✓/✗
9. all pages use $/$$ LaTeX only: ✓/✗
10. every [prepared markdown](...) link resolves to a file > 0B: ✓/✗
11. every concept ## My understanding has the research-direction sentence / scoped reason / anchor-absent note: ✓/✗
12. no directory-prefixed wikilinks; no dangling paper-slug wikilinks: ✓/✗
13. Topic placement N and Summary placement S recorded in report: ✓/✗
```

Run the grounding gate across all touched pages (red blocks the report):

```shell
uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only "papers/{slug}.md" --only "concepts/{touched}.md" --only "claims/{touched}.md" --json
```

Do **not** run or report a full-wiki `tools/lint.py` audit here. For lint-backed verification, restrict to touched files: `tools/lint.py --wiki-dir '@configured' --only "papers/{slug}.md"`. Whole-wiki 🔴/🟡/🔵 counts belong to `/check`.

---
name: ingest-light
description: Lightly ingest background or dissertation-introduction papers into the wiki without expanding the full concept/claim/people graph. Use when the user wants many papers added for thesis introduction, related-work background, bibliography scaffolding, or narrative context rather than deep knowledge-graph extraction.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>| <prepared-source-path>) [--role background|method-foundation|benchmark|application|gap-evidence|review-context] [--depth light|paper-only] [--target-summary thesis-introduction-literature]"
---

# /ingest-light

Light ingest is for papers whose main purpose is dissertation-introduction or background narrative support. It creates a useful paper page and connects it to a writing-purpose Summary page, but does **not** default to creating concepts, claims, people pages, or semantic graph edges. Use `/ingest` instead when the paper is core evidence for reusable concepts/claims.

It reuses the shared ingest pipeline but runs a reduced subset, **printing each phase's Gate block** as it goes:

- **Phase A** — `.claude/skills/shared-references/ingest-phases/phase-a-source-identity.md` (resolve + prepare + identity)
- **Phase B** — `.claude/skills/shared-references/ingest-phases/phase-b-evidence-pack.md` (light Evidence Pack; concepts/claims counts are 0 unless this run explicitly touches them)
- **Light paper page** — this skill's own light variant (below + `references/light-paper-page.md`); Evidence Pack still required per `docs/runtime-page-templates.en.md`
- **Summary update** — `references/summary-update.md`
- **Finalize** — index + log + scoped lint (Phase E, reduced)

Phase D (concepts/claims/people/semantic edges) is **skipped by default**.

## References

- `references/light-paper-page.md` — required light paper-page shape and tags.
- `references/role-selection.md` — choose the primary introduction role when unspecified/ambiguous.
- `references/summary-update.md` — how to update `wiki/Summary/<target-summary>.md`.
- `.claude/skills/shared-references/ingest-invariants.md` — path / Zotero / slug / LaTeX / wikilink / BibTeX rules.
- `.claude/skills/ingest/references/pdf-preprocessing.md` — Zotero PDF preprocessing (Phase A).

## Inputs

- Zotero lookup by `--doi`/`--title` (optionally `--zotero-root`), or a prepared source path handed off from `/ingest-local-pdf`, `/init`, or the user. Zotero discipline (incl. `--item-key` internal-only) is in invariants §2.
- `--role` ∈ `background | method-foundation | benchmark | application | gap-evidence | review-context`. If omitted/ambiguous, infer one primary role per `references/role-selection.md` and state the choice + one-sentence rationale in the report; if it cannot be inferred, ask the user.
- `--depth light` (default): create/update the light paper page **and** the target Summary. `--depth paper-only`: paper page only.
- `--target-summary` (default `thesis-introduction-literature`).

## Outputs

- `<wiki-root>/papers/{slug}.md` — light paper page (CREATE/UPDATE).
- `<wiki-root>/sources/papers/{source-slug}.md` — when a Zotero PDF must be prepared.
- `<wiki-root>/Summary/{target-summary}.md` — UPDATE unless `--depth paper-only`.
- `<wiki-root>/index.md` (rebuild/append) and `<wiki-root>/log/` (append).
- **No default writes** to `concepts/`, `claims/`, `people/`, `graph/edges.jsonl`, `graph/citations.jsonl`.

## Workflow

**Pre-condition**: run from repo root; path/environment discipline in invariants §1.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

1. **Phase A** — resolve + prepare the source and settle identity, per the phase file. Stop if `usable: false`; do not read MinerU cache intermediates as a substitute. Print Gate A.
2. **Phase B** — extract the light Evidence Pack from the prepared source and print Gate B. Use the shared phase, with the light page's populated interpretive sections as the coverage target; concept/claim counts are `0` unless this run explicitly updates existing concept/claim pages.
3. **Light paper page** — follow `references/light-paper-page.md`:
   - Frontmatter = normal paper fields + tags containing `thesis-introduction`, the selected role, and `light-ingest`. Fill `paper_type`/`research_modes`/`research_object_tags` conservatively, else `other`/`[]`/`[]`.
   - Light body sections: `## Evidence Pack` (first, per template), `## Problem`, `## Key idea`, `## Research classification`, `## Introduction use`, `## Evidence notes`, `## Limitations`, `## BibTeX`, `## Related`.
   - `## Introduction use` states the primary role and why this paper belongs in it.
   - `## Related` follows the fixed paper Related format in ingest invariants §8; include `[[{target-summary}]]` under `Summary` unless `--depth paper-only`.
   - Do not create concept/claim/people pages; link existing pages only when clearly useful. If the page already exists, update only missing/stale light metadata — never overwrite a full `/ingest` page with a lighter one.
   - Print Gate C (template shape check + scoped `grounding_lint --only` on the paper page; fix red).
4. **Summary update** (skip for `--depth paper-only`) — follow `references/summary-update.md`: add the paper under a role-based subsection in `Summary/{target-summary}.md`, preserving prose; create the Summary from template if absent.
5. **Finalize** —
   ```shell
   uv run python -X utf8 tools/research_wiki.py rebuild-index '@configured'
   uv run python -X utf8 tools/research_wiki.py log '@configured' "ingest-light | added papers/<slug> | role=<role> | target=Summary/<target-summary>"
   uv run python -X utf8 tools/lint.py --wiki-dir '@configured' --only "papers/{slug}.md" --only "Summary/{target-summary}.md"
   ```
   Print this reduced Gate E before reporting:
   ```text
   [Gate E-light] final
   1. papers/{slug}.md exists & frontmatter YAML parses: ✓/✗
   2. Evidence Pack meets light coverage floor (populated sections; concepts/claims n.a. unless touched): ✓/✗
   3. scoped grounding_lint/lint has no blocking issue on touched files: ✓/✗
   4. Summary/{target-summary}.md updated or --depth paper-only: ✓/✗ / n.a.
   5. current weekly log has a [today] entry under ## ingest-light: ✓/✗
   6. index.md includes the light paper: ✓/✗
   7. all pages use $/$$ LaTeX only and slug-only wikilinks: ✓/✗
   ```
   Report scoped results only; do not surface full-wiki lint debt.

## Upgrade path

If a light-ingested paper later becomes core evidence, run `/ingest`, `/reingest`, or `/reingest-force` on the same slug to upgrade it to full graph participation. Use `/reingest-force` when the existing paper page is badly wrong and old wiki state should not steer the rebuild. Preserve `thesis-introduction` tags and the Summary link unless the user asks to remove them. See `/promote-light-ingest` to find candidates.

---
description: Scan light-ingested thesis/background paper pages and rank which ones should be promoted to full `/ingest` or `/reingest` with concepts, claims, people, and graph links. Use when the user asks which `/ingest-light` papers deserve deeper processing, wants to upgrade light pages, or wants a promotion shortlist.
argument-hint: "[--limit N] [--min-score N] [--apply <paper-slug>]"
---

# /promote-light-ingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。

This skill audits paper pages created by `/ingest-light` and proposes which ones should be promoted to the full research graph. It is a proposal gate by default: it ranks candidates, explains why they matter, and gives exact `/reingest` commands. It does **not** batch-upgrade papers unless the user explicitly names a slug with `--apply`.

## Inputs

- `--limit N` optional, default 20: maximum candidates to show.
- `--min-score N` optional, default 0: hide low-scoring candidates.
- `--apply <paper-slug>` optional: after showing the rationale, run `/reingest @configured-sources-papers/<source-slug>.md --update-entities` for one explicitly selected light-ingest paper whose prepared source exists.

## Outputs

- Promotion shortlist grouped as `high` / `medium` / `low` priority.
- Suggested command per paper, usually:
  - `/reingest @configured-sources-papers/<source-slug>.md --update-entities`
- Optional report file under `.checkpoints/` if useful for a long shortlist.
- `<resolved-wiki-root>/log.md` append line via `tools/research_wiki.py log`.

## Selection Signals

Promote light-ingested papers when they are likely to generate reusable wiki structure:

- `role=method-foundation`, `gap-evidence`, or `benchmark`.
- `research_modes` includes `theory` or `computation`, especially MCDHF/RCI/GRASP/RIS4/isotope-shift/hyperfine work.
- The paper contains benchmark data, uncertainty discussion, discrepancy/gap evidence, or a reusable method.
- The prepared source exists under `@configured-sources-papers`.
- The page already has more than light sections, such as `## Method`, `## Results`, `## Open questions`, or non-Summary wikilinks.

Do not prioritize pure `background` or broad `review-context` pages unless they are foundational for the thesis narrative or method chapter.

## Workflow

**Pre-condition**: run from the repository root. Use runtime path aliases; do not hard-code `wiki/` or external vault paths.

```shell
uv run python tools/research_wiki.py stats '@configured' --json
uv run python tools/resolve_path_alias.py '@configured' '@configured-sources-papers'
```

### Step 1: Scan Light Pages

Run:

```shell
uv run python tools/promote_light_ingest.py --wiki-dir '@configured' --limit 20
```

For machine-readable output:

```shell
uv run python tools/promote_light_ingest.py --wiki-dir '@configured' --limit 20 --json
```

For a persistent report:

```shell
uv run python tools/promote_light_ingest.py --wiki-dir '@configured' --limit 30 --output .checkpoints/promote-light-ingest.md
```

### Step 2: Explain the Ranking

Present the shortlist to the user. For each high/medium candidate, include:

- `[[slug]]`
- role and score
- one-sentence reason for promotion
- whether the prepared source exists
- exact suggested command

Do not claim a page is ready for promotion if its prepared source is missing. In that case, suggest re-running `/ingest-light` or locating the prepared source first.

### Step 3: Optional Apply

Only when the user explicitly supplies `--apply <paper-slug>` or separately says to upgrade a named candidate:

1. Confirm the candidate is tagged `light-ingest`.
2. Prefer:
   ```text
   /reingest @configured-sources-papers/<source-slug>.md --update-entities
   ```
3. Use the candidate's `source_slug` from the scanner output, not the paper page slug if they differ. `/reingest` accepts a prepared source path or PDF; `papers/<slug>` is only the existing page identity checked during matching.
4. Preserve `thesis-introduction`, role tags, and `[[thesis-introduction-literature]]` links during the full reingest. Promotion adds graph/deep-analysis structure; it should not erase the writing-purpose context.

Never auto-apply the whole shortlist.

### Step 4: Log

```shell
uv run python tools/research_wiki.py log '@configured' "promote-light-ingest | scanned light papers | candidates=<N>"
```

If `--apply` was used, log:

```shell
uv run python tools/research_wiki.py log '@configured' "promote-light-ingest | promoted papers/<slug>"
```

## Constraints

- Proposal-first: by default this skill only ranks and reports.
- Do not create concepts, claims, people, or graph edges directly. Promotion is delegated to `/reingest` or `/ingest`.
- Do not delete `light-ingest`, `thesis-introduction`, role tags, or Summary links.
- Do not use literal `wiki/` paths for output or diagnostics; use `@configured` and `tools/resolve_path_alias.py`.

## Dependencies

### Tools

- `uv run python tools/promote_light_ingest.py --wiki-dir '@configured' [--limit N] [--min-score N] [--json] [--output <path>]`
- `uv run python tools/research_wiki.py log '@configured' "<message>"`
- `uv run python tools/resolve_path_alias.py '@configured' '@configured-sources-papers'`

### Skills

- `/ingest-light` — creates the light pages being audited.
- `/reingest` — preferred promotion action for an existing paper page.
- `/ingest` — use only when there is a prepared source but no existing paper page.

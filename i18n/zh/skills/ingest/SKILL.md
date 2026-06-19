---
name: ingest
description: Ingest a Zotero-backed paper into the wiki — creates pages (papers + concepts + people + claims) and builds all cross-references and graph edges. Trigger whenever the user says "ingest", "add this paper", or asks to fold a Zotero-backed paper into the knowledge base.
argument-hint: "[--zotero-root <dir>] (--title <str>| --doi <doi>) [--discover]"
---

# /ingest

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> 内容语言提醒：写入正式 wiki 页面时遵守 `AGENTS.md` 的正式页面语言规范；除非用户明确要求中文，页面正文默认使用英文，source excerpts 保持原语言。

Turn one paper into a fully wired set of wiki pages. `/ingest` is a **phase runner**: it executes Phases A–E in order, and **after each phase it must print that phase's Gate block** before starting the next. The Gate blocks are the anti-laziness mechanism — never skip a phase or its Gate. Emit well-formed entities and correct cross-references; leave semantic audits (backlink symmetry, dangling nodes, field-value policing) for `/check`.

## Phases (run in order; print each Gate)

- Phase A — `.claude/skills/shared-references/ingest-phases/phase-a-source-identity.md`
- Phase B — `.claude/skills/shared-references/ingest-phases/phase-b-evidence-pack.md`
- Phase C — `.claude/skills/shared-references/ingest-phases/phase-c-paper-page.md`
- Phase D — `.claude/skills/shared-references/ingest-phases/phase-d-knowledge-graph.md`
- Phase E — `.claude/skills/shared-references/ingest-phases/phase-e-navigation-finalize.md`

## Always-on references

- `.claude/skills/shared-references/ingest-invariants.md` — path / Zotero / slug / LaTeX / wikilink / BibTeX / edge rules (single source of truth; obeyed by every phase)
- `docs/runtime-page-templates.en.md` — page frontmatter, body sections, Evidence Pack card shape, claim YAML (single source of truth for page shape)
- `.claude/skills/shared-references/source-grounding.md` — anti-hallucination discipline (general)

## On-demand detail references

- `.claude/skills/ingest/references/pdf-preprocessing.md` — MinerU prepare for Zotero PDFs (Phase A)
- `.claude/skills/ingest/references/dedup-policy.md` — merge-vs-create rule (Phase D)
- `.claude/skills/ingest/references/cross-references.md` — forward/reverse matrix + edge-type selection (Phase D)
- `.claude/skills/ingest/references/init-mode.md` — `/init` handoff + parallel safety (all phases)
- `.claude/skills/ingest/references/error-handling.md` — source parse / API / slug-collision fallbacks
- `.claude/skills/ingest/references/content-quality-gate.md` — per-page quality floor (Phases C/D)

## Inputs

- `source`: Zotero lookup arguments — `--title <str>` and/or `--doi <doi>`, optionally `--zotero-root <dir>`. Zotero discipline (including why `--item-key` is internal-only) is in invariants §2. Prepared `@configured-sources-papers/*.md` and `canonical_ingest_path` values are internal handoffs from `/ingest-local-pdf` or `/init` only; do not expose prepared markdown as a user-facing input.
- Zotero metadata alone is not a grounded source: with no PDF / prepared markdown / notes / web content, do not create a paper page.
- `--discover` (optional, default **off**): after the final report, run `/discover` anchored on this paper and append the gated shortlist as "Related papers you may want to ingest next". User-owned flag — do not set it from repo state. Skipped in INIT MODE.

## Outputs

- One fully-wired paper page plus linked entities (concepts, claims, people)
- Graph edges and citations appended via `tools/research_wiki.py`
- Terminal summary with page counts and optional structured follow-up candidates
- Minimum viable ingest: paper page + ≥1 concept (new or updated) + ≥1 claim (new or updated; mandatory for importance ≥ 4) + author handling + `index.md` + `log/` + graph/context. If the source cannot support a claim or concept, say why in the log and report.

## Wiki Interaction

- **Reads**: `index.md`; `papers/*` (already-ingested check); `concepts/*` + `foundations/*` and `claims/*` (dedup); `people/*`; `topics/*`; `graph/open_questions.md`.
- **Writes**: `papers/{slug}.md` (CREATE); `concepts/{slug}.md` (CREATE/EDIT); `claims/{slug}.md` (CREATE/EDIT); `people/{slug}.md` (CREATE if importance ≥ 4, else EDIT); `topics/{slug}.md` (EDIT only); `graph/edges.jsonl` + `graph/citations.jsonl` (APPEND via tool); `graph/context_brief.md` + `graph/open_questions.md` (REBUILD, skipped in INIT MODE); `index.md` (APPEND); `log/` (APPEND via tool).
- **Graph edges**: `paper→concept` (`introduces_/uses_/extends_/critiques_concept`); `paper→foundation` (`derived_from`, terminal); `paper→claim` (`supports`/`contradicts`); `paper→paper` semantic types; bibliographic `cites` in `citations.jsonl`. Edge invocation contract is in invariants §8; type selection in `cross-references.md`.

## Workflow

**Pre-condition**: working directory is the project root (`tools/`, `pyproject.toml`, `config/paths.json`). Path/environment discipline is in invariants §1.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

Then run Phases A → B → C → D → E from the files above, printing each Gate block as you complete the phase. Do not start a phase while the previous phase's Gate has a ✗.

### After Phase E: optional discovery (only if `--discover`)

Skip unless the user passed `--discover`; also skip in INIT MODE. When active:

```shell
uv run python -X utf8 tools/discover.py from-anchors --id <doi-or-title-of-this-paper> --wiki-root '@configured' --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Append only gated candidates (Phase E candidate gate: title + authors + year + DOI + Zotero status + relation evidence). Never auto-ingest. A failed or empty `/discover` must not fail an otherwise successful `/ingest` — note it in one line.

## Constraints

- `@raw-root/papers|notes|web` are user-owned and read-only; `/ingest` takes no direct local PDF input (that is `/ingest-local-pdf`). INIT MODE treats all of `raw/` as read-only.
- `@configured/graph/` is tool-owned; edit only through `tools/research_wiki.py`.
- Every forward link writes its reverse in the same turn (foundations excepted; INIT MODE defers reverse links to fan-in). See `cross-references.md` and `init-mode.md`.
- `mineru-md` is the canonical prepared format; preparation failure (`usable: false`) blocks ingest with the warnings surfaced.
- New-entity caps (dedup-policy.md): importance < 4 → ≤1 new concept, ≤1 new claim; importance ≥ 4 → ≥1 and ≤3 concepts, ≥1 and ≤2 claims. Caps are upper bounds, not targets.
- `/ingest` runs only a narrow shape check + scoped `grounding_lint`/`lint --only` on touched files. Backlink symmetry, dangling nodes, full semantic audits, and whole-wiki lint counts belong to `/check`.
- All other cross-cutting rules: invariants §1–§9.

## Error Handling

See `.claude/skills/ingest/references/error-handling.md`. Highlights: MinerU API failure → local backend if installed, else hand off; `usable: false` blocks ingest; literature outage → `importance` 3 and skip citation backfill; paper slug collision with a different paper → stop and report.

## Dependencies

### Tools
- `tools/research_wiki.py` — `stats`, `paper-slug`, `slug`, `find-similar-concept`, `find-similar-claim`, `add-edge`, `add-citation`, `log`, `rebuild-index`, `rebuild-context-brief`, `rebuild-open-questions` (invocation contracts in invariants §3/§8)
- `tools/find_zotero_pdf.py`, `tools/fetch_zotero_metadata.py --item-key <key>` — Zotero lookup + internal enrichment (invariants §2)
- `tools/prepare_paper_source.py …` — MinerU prepare (pdf-preprocessing.md)
- `tools/fetch_literature.py paper|citations|references <doi-or-title>` — when a DOI/confident title is available
- `tools/grounding_lint.py --wiki-dir '@configured' --only "<touched-file>" --json` — mandatory scoped gate (Phases C/D/E)
- `tools/discover.py from-anchors …` — only when `--discover`

### Skills
- `/init` — calls `/ingest-local-pdf` in parallel subagents
- `/ingest-local-pdf` — prepares local PDFs and hands prepared sources back to `/ingest`
- `/check` — owns every semantic audit `/ingest` intentionally skips
- `/discover` — optional follow-up when `--discover` is set

### External APIs
- Crossref (`fetch_literature.py`); Zotero Desktop Local API (`fetch_zotero_metadata.py`); MinerU (`prepare_paper_source.py`)

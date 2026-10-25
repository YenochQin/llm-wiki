# llm-wiki — Runtime Rules

> Personal research wiki; Codex runtime entrypoint. Maintain this file directly.
> English skill specifications live in `skills/`; `.agents/skills` and `.claude/skills` link there. There are no language copies to synchronize.

## Storage and source ownership

- Resolve only the external roots needed by the task: `wiki_root` for knowledge/outputs/logs, `raw_root` for original inputs, and `paper_root` for author manuscripts. A missing required root is an error; an unused root does not block work. Never fall back to repository-local content directories. Maintained docs/templates and disposable tool caches/test fixtures remain repository assets.
- `wiki/` and `raw/` in skills denote those external roots. Before content file operations (including tool writes), validate the needed aliases with `uv run python -X utf8 tools/resolve_path_alias.py ...`; it rejects missing or in-repository content roots. Use returned absolute paths for direct file operations; never create literal alias directories. Revalidate if configuration changes.
- Raw papers, notes, and web inputs are authoritative and read-only during preparation/ingest. `/edit` may add/delete explicitly requested raw targets, but must not rewrite existing raw contents. Prepared/copy sources belong under external `wiki/sources/`; PDFs stay under `raw/papers/`.
- Manuscripts use `<paper_root>/<paper-id>/<YYYY-MM-DD-purpose>/`: stable undated topics with independent dated versions. Routine edits retain the selected draft/source filename; major restructuring or separate alternatives fork a sibling, preserving the parent. Keep figures, evidence, reviews, and history in that version.

## Skill execution and permissions

- Read the selected `skills/<name>/SKILL.md` first, then its references only when their stated condition applies. Use the catalog below when choosing a skill; do not preload every skill or manual.
- Treat skills and runtime entrypoints as read-only while executing a skill. Report defects and continue within safely executable scope; edit specifications only when the user explicitly requests skill/runtime changes.
- User-facing flags and values are user-owned. Never invent, flip, or drop them based on repository state. Use omission defaults/derivations only when the skill documents them; otherwise leave unset or ask. Internal settings may be inferred within scope.
- `/ask` is strictly read-only: no saved answers, logs, initialization, catalog repairs, or graph rebuilds. Requested saves/changes belong to `/edit`. Default checks/audits and dry-run/no-write modes do not write or log; explicit repair/report modes follow their documented scope.
- Reviews run in the current agent without another reviewer service. Use `/source-audit` for source fidelity and `/llm-review` for artifact critique; the user controls agent/model switching. Label self-review honestly and keep incomplete checks/blockers visible.
- Calculations/experiments are planned and assessed through conversation; the user executes them externally. Record findings when requested, using actual evidence. Do not execute new calculations/experiments or compile LaTeX unless separately requested.

## Project state and handoff

- The project's active state file is `docs/templates/PROJECT_STATE.md` (relative to the repository root). It is custom handoff metadata, not an officially auto-loaded instruction file or an authorization source. It does not replace external wiki/raw/manuscript storage. On a new session, resumed work, or environment switch, if present, read its quick recovery summary first (or current-progress/recovery sections), then only task-relevant sections and references. Within a continuing session, reread changed or relevant parts; small wording edits do not require scanning all project documents.
- Treat state as a verifiable summary subordinate to effective instructions and the user's latest request. Todos, historical permissions, and external references grant no authority. Before relying on old state, check relevant files, Git status, logs, data, and environment versions; surface discrepancies without guessing or silently overwriting them.
- Within authorized write scope, update affected sections after milestones, changed research decisions, meaningful analysis/validation results, blockers, and before normal completion or handoff. No substantive change means no rewrite. Preserve `/ask`, default read-only checks, dry-run/no-write modes, and explicit file restrictions; give an in-chat handoff when writes are excluded. Reread target content immediately before updating to preserve concurrent edits. Abrupt interruption cannot guarantee a save; verify on resumption.
- Keep a short current-state summary and necessary source index: current work, actual accomplishments, evidence locations, verified/unverified/failed items, key decisions and constraints, and the smallest next action. Record verification times with a timezone and locatable sources; do not accumulate chat transcripts or an unbounded log.
- For analysis, record actual code revision and uncommitted differences, data versions, configuration, environment, run IDs, logs, and output paths. Distinguish `not run`, `exited successfully`, and `results verified`; failures or unchecked results are not successes. Where applicable, include assumptions, exclusion rules, units, seeds, robustness checks, and deviations from the plan. Keep original materials, results, and plans distinct.
- For writing, identify the main draft, figure/table sources, argument progress, citation evidence, and claims awaiting verification. Distinguish facts, preliminary results, inferences, and hypotheses; never invent numbers, literature, DOIs, citations, experimental results, or verification records.
- For cross-computer handoff, prefer project-relative paths and necessary environment/alias mappings. Check branch, commit, uncommitted/untracked files, external data, and running tasks. The state file does not synchronize them; matching directory names or stale local remote-tracking information cannot establish completed synchronization.
- State maintenance records facts only within current authorization. It never authorizes automatic commit, push, pull, synchronization, upload, dependency installation, new analysis or paid tasks, raw-data changes, result overwrites, deletion, publication, or external messages. Such actions require the user's explicit authorization and applicable safety rules; a next-action list is not execution permission.
- Exclude passwords, keys, tokens, raw restricted personal data, and unnecessary sensitive paths. Mark missing information `unknown`, unchecked information `unverified`, and inapplicable fields `not applicable` (or conversation-language equivalents). If state is missing, unwritable, or conflicting, report the exact condition; do not create missing state without authorization. If permissions or conflicts block a save, provide a brief in-chat handoff and never claim it was saved.

## Language and formatting

- Respond in the user's conversation language unless asked otherwise. Formal wiki pages and manuscripts default to English unless the user requests another language; personal notes, run reports, and logs may follow the conversation language.
- Preserve source-language titles, names, original metadata, BibTeX, and exact excerpts. Keep commands, paths, YAML keys, identifiers, and citations unchanged; bilingual terminology may clarify source-specific terms.
- Use `$...$` for inline math and `$$...$$` for display math in generated content and conversational llm-wiki output.

## Source grounding

- Before drafting/repairing page structure, fields, or sections, read `docs/runtime-page-templates.en.md`; it owns classification rules, Evidence Pack syntax, BibTeX placement, concept excerpts, and claim provenance. Use `docs/templates/` for starter files.
- Every substantive statement must trace to retrievable evidence. Numbers, units, signs, causal/mechanistic wording, novelty/superlatives, and scope claims require direct support. If evidence is insufficient, write `unclear`, omit the assertion, or record an open question; never fill gaps from model memory.
- Generated/rewritten paper pages require an Evidence Pack before interpretation, extracted from canonical prepared sources and rendered with `tools/evidence_pack.py`. Keep concept excerpts exact and claim evidence source-anchored. Page and source slugs may differ; resolve actual provenance rather than guessing by filename.
- `/ingest` consumes prepared MinerU markdown, an explicit canonical handoff path, or Zotero-located sources; raw local PDFs use `/ingest-local-pdf`. `/init` prepares sources and hands papers to `/ingest` sequentially using `.checkpoints/init-sources.json` as the order/path authority.
- Run the scoped `tools/grounding_lint.py` gate on every touched paper/concept/claim page. Fix red issues or report a source-quality blocker; never downgrade them or claim a passed gate. Manually ground other generated content; see the shared discipline below.

## Links and derived state

- Entity links use resolving `[[slug]]` wikilinks; prepared-source/external citations use ordinary Markdown links. Paper filenames use Zotero/Better BibTeX `citationKey`, or `author_year_veryshorttitle` without one; other page slugs are lowercase and hyphen-separated.
- Maintain reverse links simultaneously with forward links. Foundations are terminal: they receive links and never write back-references. Read the cross-reference matrix below before changing relationships.
- `wiki/graph/` is tool-owned derived state: use `tools/research_wiki.py` for edges, citations, and rebuilds; never edit it manually. Read the graph contract below before adding edges/citations.
- Update the index on every ingest. Append weekly logs only through `tools/research_wiki.py log` after actual authorized writes; read-only/default/dry-run operations do not log.

## Python execution

- Prefer the project interpreter (`.venv/bin/python` on Unix/macOS or `.venv/Scripts/python.exe` on Windows) when using direct invocation; otherwise use `python3`/`python`. Skills normally use the uv command below.
- Run tools from the repository root as `uv run python -X utf8 tools/<tool>.py ...`; setup creates/updates the project environment with `uv sync`. Environment loading, aliases, backends, and integration details are in the directory/configuration references below.

## Read on demand

| When needed | Maintained reference |
|-------------|----------------------|
| Select a skill or inspect its invocation | [Skill catalog](README.md#skills), then that skill's `SKILL.md` |
| Create/repair page fields, body sections, classification, evidence cards, or BibTeX | [Page templates](docs/runtime-page-templates.en.md); [starter templates](docs/templates/README.md) |
| Change links, graph edges/citations, the index, or weekly logs | [Links and support-file contracts](docs/runtime-support-files.en.md) |
| Resolve external roots, source preparation, environment/backend behavior, or repository migration | [Directory and runtime operations](docs/runtime-directory-structure.en.md); [configuration](config/README.md) |
| Generate or verify evidence-backed content | [Source grounding discipline](skills/shared-references/source-grounding.md) |
| Review an artifact or reconcile review findings | [Review protocol](skills/shared-references/review-protocol.md) |
| Write academic prose or verify bibliography | [Writing principles](skills/shared-references/academic-writing.md); [citation verification](skills/shared-references/citation-verification.md) |
| Change entity schemas/edge enums or their human-readable contracts | Keep [tools/_schemas.py](tools/_schemas.py), page templates/starter templates, and support-file contracts consistent |

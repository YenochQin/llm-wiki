# llm-wiki — Runtime Schema

> Personal LLM-maintained research wiki. Powered by Claude Code.
> This file is the wiki's runtime entry point: defines page structure, link conventions, and workflow constraints.
> Adapted from OmegaWiki's workflow with the PDF preprocessing layer swapped to MinerU.

> **Maintenance note**: Managed under `i18n/`. Edit `i18n/en/CLAUDE.md` (not the active copy at the root). Run `./setup.sh --lang <current>` to sync.

---

## Repository Layout

Open `docs/runtime-directory-structure.en.md` only when you need the full repo tree.

Keep this mental map in immediate context:

### `wiki/` is the main product surface

- `wiki/index.md` is the catalog of all wiki pages
- `wiki/log/` stores weekly activity logs maintained by `tools/research_wiki.py log`
- `wiki/papers/` holds paper summaries
- `wiki/concepts/`, `wiki/topics/`, and `wiki/foundations/` hold reusable knowledge structure
- `wiki/people/`, `wiki/ideas/`, `wiki/experiments/`, and `wiki/claims/` hold research actors, hypotheses, tests, and assertions
- `wiki/Summary/` holds area-level syntheses
- `wiki/outputs/` holds generated artifacts
- `wiki/graph/` is derived state; do not edit it manually

### Formatting guardrail

- Open `docs/runtime-page-templates.en.md` before drafting or repairing wiki page structure, YAML, or body sections
- For copyable page starter templates, use `docs/templates/`; do not keep a root-level template library
- Open `docs/runtime-support-files.en.md` when you need graph-derived file details or `index.md` / `log/` format
- `SKILL.md` is the immediate entrypoint for a skill; some larger skills may also provide local on-demand reference files under their skill directory
- `/init` is the first concrete example of this pattern: read `skills/init/SKILL.md` first, then open `skills/init/references/*` only when needed
- `skills/` is a symlink created by `setup.sh`, pointing to `i18n/{lang}/skills/`; edit skill content in `i18n/`, not the symlink target

### `raw/` and `config/`

- `raw/papers/`, `raw/notes/`, and `raw/web/` are user-owned inputs
- `wiki/sources/papers/` stores MinerU-converted paper markdown; source PDFs stay in `raw/papers/`
- `wiki/sources/notes/` and `wiki/sources/web/` store vault-visible copies of notes and web markdown/text
- `config/` holds environment templates (`.env.example`, `settings.local.json.example`, `paths.json.example`)
- `config/paths.json` may use `profiles.macos/windows/linux` to connect this code repository to OS-specific external wiki vault and raw source directories; it is machine-local and not committed

---

## 9 Page Types

`papers`, `concepts`, `topics`, `people`, `ideas`, `experiments`, `claims`, `Summary`, `foundations`.

Open `docs/runtime-page-templates.en.md` for page templates and `docs/runtime-support-files.en.md` for graph/index/log references.

### Paper Analysis Classification

Every `papers/{slug}.md` must first classify the source form, research direction, and research object:

- `paper_type`: classify the source form as one of `paper`, `review`, `book`, `degree_thesis`, `preprint`, `report`, `chapter`, `dataset`, or `other`. This is separate from `research_modes`: review articles should use `paper_type: review`, while `research_modes` still reflects the evidence types being analyzed or synthesized.
- `research_modes`: choose one or more of `theory`, `computation`, `experiment`. For review papers, classify by the evidence types being analyzed/synthesized; do not use `review` as a mode.
- `theory_tags`: list the concrete theories, models, mechanisms, or analytical frameworks used, compared, or tested.
- `computation_tags`: list the computational/simulation/statistical/ML/data-analysis schemes used; empty list if none.
- `experiment_tags`: list observations, experiments, sample analyses, instruments, missions, or protocols; empty list if none.
- `research_object_tags`: list the research objects, such as materials, celestial bodies, systems, samples, populations, model objects, or datasets.

The body must include `## Research classification`, explaining which of theory/computation/experiment apply, what specific theory/computational scheme/experimental process was used, and what objects were studied. If the source does not make something clear, write `unclear` rather than inventing it.

### Concept Source Grounding

Every `concepts/{slug}.md` page must include `## Source excerpts` immediately after `## Definition`.

- Add one short original-language excerpt for each paper that materially grounds the concept.
- Each excerpt must link to the prepared MinerU markdown, usually `wiki/sources/papers/{paper-slug}.md`, using a normal markdown link.
- Keep the excerpt exact and brief; do not paraphrase inside the blockquote.
- If the prepared markdown is missing, write `prepared markdown: missing` and state which fallback source was used.

Example:

```markdown
- [[paper-slug]] ([prepared markdown](../sources/papers/paper-slug.md)):
  > short exact source fragment
```

---

## Link Syntax

All internal links use Obsidian wikilinks:

```markdown
[[slug]]                    ← link to any page in this wiki
[[lora-low-rank-adaptation]] ← links to papers/lora-low-rank-adaptation.md
[[flash-attention]]          ← links to concepts/flash-attention.md
```

**Naming convention**: all lowercase, hyphen-separated, no spaces.

---

## Cross-Reference Rules

When writing a forward link, **always write the reverse link simultaneously**:

| Forward action | Required reverse action |
|----------------|------------------------|
| papers/A writes `Related: [[concept-B]]` | concepts/B appends A to `key_papers` |
| papers/A writes `[[researcher-C]]` | people/C appends A to `Key papers` |
| papers/A writes `supports: [[claim-D]]` | claims/D appends `{source: A, type: supports}` to `evidence` |
| topics/T writes `key_people: [[person-D]]` | people/D appends T to `Research areas` |
| concepts/K writes `key_papers: [[paper-E]]` | papers/E appends K to `Related` |
| concepts/K writes part_of `[[topic-F]]` | topics/F appends K to overview paragraph |
| ideas/I writes `origin_gaps: [[claim-C]]` | claims/C appends I to `## Linked ideas` |
| experiments/E writes `target_claim: [[claim-C]]` | claims/C appends `{source: E, type: tested_by}` to `evidence` |
| claims/C writes `source_papers: [[paper-P]]` | papers/P appends C to `## Related` |
| any page links to `[[foundation-X]]` | **no reverse link** — foundations are terminal: they receive inward links from papers/concepts/etc. but never write `key_papers` or any back-reference field |

---

## Graph Rules

- `graph/` is auto-generated; do not edit it manually
- core derived files are `edges.jsonl`, `citations.jsonl`, `context_brief.md`, and `open_questions.md`
- semantic edge types include paper-paper (`same_problem_as`, `similar_method_to`, `complementary_to`, `builds_on`, `compares_against`, `improves_on`, `challenges`, `surveys`), paper-concept (`introduces_concept`, `uses_concept`, `extends_concept`, `critiques_concept`), and existing claim/experiment/provenance types (`supports`, `contradicts`, `tested_by`, `invalidates`, `addresses_gap`, `derived_from`, `inspired_by`)
- `/ingest` paper-paper and paper-concept semantic edges must include `confidence: high|medium|low`
- symmetric paper-paper edges are stored once with sorted endpoints and `symmetric: true`
- bibliographic citations live in `citations.jsonl` as `type: cites`
- use `tools/research_wiki.py add-edge`, `add-citation`, `rebuild-context-brief`, and `rebuild-open-questions`

## log/ Format

Logs are written to `wiki/log/{yyyy-mm-wN}.md`, where `wN` is the week-of-month bucket: days 1–7 are `w1`, days 8–14 are `w2`, and so on.

Each weekly log file uses `# log` as the top-level heading and skill names as second-level headings. Standard format:

```markdown
# log

## ingest-light
[YYYY-MM-DD] added something

## ingest
[YYYY-MM-DD] added something
```

Append log entries only through the tool:

```shell
uv run python -X utf8 tools/research_wiki.py log '@configured' "ingest-light | added something"
```

---

## Python Environment

- this project is **uv-managed**: `setup.sh` creates/updates `.venv` from `pyproject.toml` via `uv sync`
- prefer `.venv/bin/python` (Unix/macOS) or `.venv/Scripts/python.exe` (Windows) when `.venv/` exists
- otherwise fall back to `python3` (Unix/macOS) or `python` (Windows)
- skills run tools as `uv run python -X utf8 tools/<name>.py …` (uv automatically resolves `.venv` from `pyproject.toml`); the equivalent direct invocation is `.venv/bin/python tools/<name>.py …` when `.venv/` exists
- Python tools auto-load API keys from process env first, then `~/.config/llm-wiki/.env` (or `$XDG_CONFIG_HOME/llm-wiki/.env`) via `tools/_env.py`; project-root `.env` and `~/.env` are legacy fallbacks only
- Path configuration uses `config/paths.json` (or `LLM_WIKI_WIKI_ROOT`, `LLM_WIKI_RAW_ROOT`) to set external `wiki_root` / `raw_root`; `active_profile: auto` chooses `macos`, `windows`, or `linux` from the current OS, and `LLM_WIKI_PATH_PROFILE` can override it temporarily; without config, tools fall back to in-repo `wiki/` and `raw/`
- the optional MinerU local backend is opt-in: `uv sync --extra local` (downloads several GB of model weights)
- no test suite exists (no `tests/` directory, no `test_*.py` files) and no Python code lint/format is configured (no ruff, black, mypy); `tools/lint.py` is a wiki-content linter, not a Python code linter

---

## Constraints

- **`raw/papers/`, `raw/notes/`, `raw/web/` are user-owned**: treat them as authoritative inputs. `/init` and `/ingest-local-pdf` may add vault-visible source copies under `wiki/sources/`: PDFs must be converted to `wiki/sources/papers/*.md` and never copied into `wiki/`; notes/web may be copied to `wiki/sources/notes/` and `wiki/sources/web/`. `/edit` may add raw sources only when the user explicitly asked for it. `/init` subagents running `/ingest` in INIT MODE still treat `raw/` as strictly read-only and must consume the handed-off canonical path directly.
- **User-facing skill parameters are user-owned**: flags and values shown in a skill's `argument-hint` belong to the user's command, not to agent strategy. Do not invent, flip, or drop those parameters from repository state alone. If the user omitted a parameter, only use a default or derived value when that skill explicitly documents omission behavior; otherwise leave it unset or ask the user. Internal derived settings that are not user-facing parameters may still be inferred by the skill.
- **INIT MODE handoff is manifest-driven**: when `/init` writes `.checkpoints/init-sources.json`, that manifest becomes the single source of truth for ingest order and canonical source paths. Prepared local inputs should point to `wiki/sources/papers/<slug>.md` (MinerU output).
- **graph/ is auto-generated**: never manually edit files in `graph/` — only via `tools/research_wiki.py`.
- **Bidirectional links**: always write the reverse link when writing a forward link.
- **mineru-md is the canonical ingest format**: PDFs are preprocessed by MinerU (`tools/_mineru.py`) into structured markdown with frontmatter (`sections`, `figures`). `/ingest-local-pdf` and `/init` produce/consume the prepared `wiki/sources/papers/<slug>.md`; `/ingest` only consumes already prepared `wiki/sources/papers/<slug>.md`, the INIT MODE handoff path, or Zotero-located paper sources — never the raw PDF directly.
- **index.md updated on every ingest**; log entries go through the weekly `log/` files.
- **lint default is report-only**: `--fix` auto-fixes deterministic issues (xref backlinks, missing field defaults); `--suggest` outputs suggestions for non-deterministic issues; `--fix --dry-run` previews fixes.
- **Slug generation rule**: paper title keywords, hyphen-joined, all lowercase.
- **Importance scoring**: 1 = niche, 2 = useful, 3 = field-standard, 4 = influential, 5 = seminal.
- **Failed ideas must record reason**: `failure_reason` is anti-repetition memory — prevents re-exploring known dead ends.
- **Claim confidence range**: 0.0-1.0; re-evaluate every time evidence changes.
- **Experiments must link to a claim**: every experiment requires `target_claim`; results are written back to the claim's evidence after the user runs the experiment externally and reports results to `/exp-eval`.
- **MinerU API token**: `MINERU_API_TOKEN` env variable powers the default cloud backend. Without it, PDF ingest fails; install the local backend (`uv sync --extra local`) for offline operation.
- **Literature lookup**: `tools/fetch_literature.py` uses no-key Crossref search and metadata. Citation graph coverage is best-effort because public sources expose fewer citation edges than key-gated services.
- **Repository and wiki can be separated**: use `tools/separate_wiki_repository.py` to copy/move `wiki/` and `raw/` to external absolute paths and write `config/paths.json`; use `tools/clean_wiki_repository.py` to remove leftover in-repo `wiki/` and `raw/`. Cleanup is dry-run by default and deletes only with `--yes`.
- **Zotero integration**: `tools/find_zotero_pdf.py`, `tools/fetch_zotero_metadata.py`, and `tools/_zotero_snapshot.py` look up PDFs and parent-item metadata in local Zotero databases by `--title`, `--doi`, or `--item-key`; Zotero roots are configured via the selected profile's `zotero_roots` in `config/paths.json` or `--zotero-root`. `/ingest` can use this to auto-locate Zotero attachments and derive plain BibTeX from Zotero metadata; BibTeX is written to the body `## BibTeX` fenced code block, not YAML frontmatter. Raw local PDFs belong to `/ingest-local-pdf`.
- **`tools/_schemas.py` bidirectional sync**: this module is the machine-consumable copy of entity schemas (directories, edge types, required fields, enums). Changes here must be synced to the human-readable spec in `i18n/*/CLAUDE.md`, and vice versa.

---

## Skills

| Skill | File | Trigger |
|-------|------|---------|
| `/setup` | `skills/setup/SKILL.md` | manual (first-time config) |
| `/reset` | `skills/reset/SKILL.md` | manual (`--scope wiki\|raw\|log\|checkpoints\|all`) |
| `/init` | `skills/init/SKILL.md` | manual |
| `/prefill` | `skills/prefill/SKILL.md` | manual (`[domain] [--add concept]`) |
| `/ingest` | `skills/ingest/SKILL.md` | manual |
| `/ingest-light` | `skills/ingest-light/SKILL.md` | manual (lightly ingest dissertation-introduction/background papers) |
| `/promote-light-ingest` | `skills/promote-light-ingest/SKILL.md` | manual (rank light-ingested papers for promotion to full ingest) |
| `/zotero-collection-list` | `skills/zotero-collection-list/SKILL.md` | manual (list citationKey, title, and DOI by Zotero collection/subcollection) |
| `/ingest-local-pdf` | `skills/ingest-local-pdf/SKILL.md` | manual |
| `/reingest` | `skills/reingest/SKILL.md` | manual (re-ingest an existing paper page) |
| `/discover` | `skills/discover/SKILL.md` | manual / internal (called by `/ingest --discover`) |
| `/ask` | `skills/ask/SKILL.md` | manual |
| `/edit` | `skills/edit/SKILL.md` | manual |
| `/check` | `skills/check/SKILL.md` | biweekly/manual |
| `/source-audit` | `skills/source-audit/SKILL.md` | manual (audit wiki interpretations against original source text) |
| `/novelty` | `skills/novelty/SKILL.md` | manual |
| `/review` | `skills/review/SKILL.md` | manual |
| `/ideate` | `skills/ideate/SKILL.md` | manual |
| `/exp-design` | `skills/exp-design/SKILL.md` | manual |
| `/exp-eval` | `skills/exp-eval/SKILL.md` | manual |
| `/refine` | `skills/refine/SKILL.md` | manual |
| `/paper-plan` | `skills/paper-plan/SKILL.md` | manual |
| `/paper-draft` | `skills/paper-draft/SKILL.md` | manual |
| `/survey` | `skills/survey/SKILL.md` | manual |
| `/research` | `skills/research/SKILL.md` | manual (design-only orchestrator) |
| `/rebuttal` | `skills/rebuttal/SKILL.md` | manual |

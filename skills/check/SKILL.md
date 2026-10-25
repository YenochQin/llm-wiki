---
name: check
description: Use when checking wiki health across page structure, fields, backlinks, and graph consistency, or requesting deterministic repairs. Reports findings without writing by default; use /source-audit for fidelity to original sources.
argument-hint: "[wiki-dir] [--json] [--fix [--dry-run]] [--suggest]"
---

# /check

> Scans the full wiki to detect structural, link, field, and graph health issues, and generates a tiered fix-recommendation report.
> Covers all 9 entity types, including claims confidence plausibility, idea failure-reason completeness,
> experiment-claim link validity, and graph edge consistency.

## Inputs

- `wiki-dir` (optional): wiki root to inspect; when omitted, resolve the configured external root (`@configured`). Never infer a repository-local `wiki/` fallback.
- Optional: `--json` flag (output JSON format via tools/lint.py)
- Optional: `--fix` flag (auto-fix deterministic issues)
- Optional: `--fix --dry-run` (preview fixes without applying them)
- Optional: `--suggest` flag (show recommendations for issues that cannot be auto-fixed)

## Outputs

- Lint report (reported directly to the user)
- Optional file write, only if explicitly requested and not in preview/no-write mode: `@output-root/lint-report-{date}.md`

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — paper page fields and links
- `wiki/concepts/*.md` — concept page fields and links
- `wiki/topics/*.md` — topic page fields and links
- `wiki/people/*.md` — people page fields and links
- `wiki/ideas/*.md` — idea status, failure_reason, origin_gaps
- `@experiment-root/*.md` — experiment status, target_claim, outcome
- `wiki/claims/*.md` — claim confidence, status, evidence, source_papers
- `wiki/Summary/*.md` — survey page fields
- `wiki/graph/edges.jsonl` — semantic graph edge consistency check
- `wiki/graph/citations.jsonl` — bibliographic citation consistency check
- `wiki/index.md` — cross-check page completeness

### Writes
- Default and suggestion-only checks without an explicit report-save request: no writes, including reports, logs, catalog, or derived files.
- Dry-run/no-write mode: no writes, even when report archiving is requested.
- With `--fix` and no dry-run/no-write request: `tools/lint.py` may apply deterministic repairs.
- An explicitly requested report archive may be saved outside preview/no-write mode.
- `wiki/log/` records actual repairs or an explicitly requested report archive; a read-only check does not log.

## Workflow

Resolve `@experiment-root` or `@output-root` with `tools/resolve_path_alias.py` before accessing that root; resolve only roots used by the selected mode. Use returned absolute paths for ordinary file operations.

**Pre-conditions**: run from the configured llm-wiki repository root. Resolve the user-supplied `wiki-dir`, or `@configured` when omitted, through `tools/resolve_path_alias.py`. In every command below, replace `<wiki-dir>` with that resolved absolute directory; `wiki/` in prose denotes the same selected root. Report invalid or missing configuration instead of creating a fallback.

```shell
uv run python -X utf8 tools/research_wiki.py stats '<wiki-dir>' --json
```

For the default root, use `uv run python -X utf8 tools/resolve_path_alias.py '@configured'`; for an explicit directory, pass that supplied path instead. Do not import path helpers from `tools._env`.

### Step 1: Run the Automated Lint Tool

**Default mode (report only)**:
```shell
uv run python -X utf8 tools/lint.py --wiki-dir '<wiki-dir>' --json
```

**Auto-fix mode** (when user specifies `--fix`):
```shell
uv run python -X utf8 tools/lint.py --wiki-dir '<wiki-dir>' --fix --json
```
Auto-fixes deterministic issues (xref reverse-link completion, missing fields filled with default values) and outputs a fix report.

**Preview mode** (when user specifies `--fix --dry-run`):
```shell
uv run python -X utf8 tools/lint.py --wiki-dir '<wiki-dir>' --fix --dry-run --json
```
Previews what would be fixed without applying any changes.

Append `--suggest` to the selected lint command only when supplied. The tool's `--json` above is for parsing findings internally; the user's `--json` selects JSON as the returned report format. Preserve the requested fix/preview/suggestion mode.

Parse the JSON output to obtain all automatically detected issues (and fix results).

### Step 1b: Run the Source-Grounding Gate

Run the mechanical grounding checker after the structural lint. This catches generated paper/concept/claim pages that lack source anchors or quote excerpts that do not occur in the prepared markdown:

```shell
uv run python -X utf8 tools/grounding_lint.py --wiki-dir '<wiki-dir>' --json
```

Treat every `red` grounding issue as 🔴 Fix Immediately. The grounding gate is report-only; do not auto-fix unsupported content. If the user asks for `--fix`, structural deterministic fixes may still be applied by `tools/lint.py`, but source-grounding failures require source review, `/source-audit`, or manual correction.

### Steps 2–5: Interpret Automated Coverage

When interpreting or investigating structural, field, backlink, or graph findings, read [references/automated-coverage.md](references/automated-coverage.md). It describes the checks covered by the automated tools; source-grounding red issues still require the treatment in Step 1b.

### Step 6: Content Quality (LLM-assisted)

Items detectable by the automated tool:
1. Papers with importance=5 have no concept page referencing them
2. Concepts with maturity=stable have only 1 key_paper
3. Topics have empty Open problems sections

Additional LLM judgments (requires reading content):
1. **Concept near-duplicate detection**: scan all concept page titles + aliases and assess whether any pairs are semantically identical or highly similar (e.g. "attention mechanism" and "self-attention"). Output merge recommendations for suspected duplicates.
2. Contradictory statement detection (inconsistent descriptions of the same fact across different pages)
3. SOTA records not updated in over 6 months
4. people Recent work not updated in over 6 months
5. Claim confidence inconsistent with evidence quantity/strength
6. High-priority idea stuck in proposed status for a long time

### Step 7: Generate Report

Read [references/report-format.md](references/report-format.md) when formatting the report. Sort findings by severity, distinguish automated results from content judgments, and include every red grounding issue.

When the user supplies `--json`, return a JSON report preserving the tool findings and labeling additional content judgments separately; otherwise return the Markdown report.

Save `@output-root/lint-report-{date}.md` only when the user explicitly requested an archive and this is not a dry-run/no-write operation. After actual repairs or a requested report write, append a log:

```shell
uv run python -X utf8 tools/research_wiki.py log '<wiki-dir>' "check | {repairs/report archive}: N 🔴, M 🟡, K 🔵"
```

Default checks, suggestion-only runs, previews, and fix runs that made no changes and saved no report do not write logs or maintenance files.

## Constraints

- **Read-only by default**: without `--fix` or an explicit report-save request, return the report only; do not write logs or any other files. `--fix --dry-run` and explicit no-write requests prohibit all writes, including report archives.
- **`--fix` only repairs deterministic issues**: xref reverse-link completion, missing fields filled with safe default values. Non-deterministic issues output recommendations (`--suggest`) for user approval
- **raw/ is read-only**: do not modify files under `raw/`
- **graph/ is read-only**: lint does not modify graph files, checks consistency only
- **LLM judgments labeled by source**: automated checks and LLM judgments are clearly distinguished in the report
- **Idempotent**: running multiple times produces the same result (unless wiki content changes)

## Error Handling

- **wiki/ does not exist**: report error and suggest running `/init`
- **graph files do not exist**: skip the missing graph-file checks, note in report
- **Partial directory missing**: skip checks for missing directories, list missing directories in report

## Dependencies

### Tools
- `uv run python -X utf8 tools/lint.py --wiki-dir '<wiki-dir>' [--json] [--fix] [--dry-run] [--suggest]` — automated structural check + fix (core dependency)
- `uv run python -X utf8 tools/grounding_lint.py --wiki-dir '<wiki-dir>' [--json] [--only <path>]` — report-only source-grounding gate for papers, concepts, and claims
- `uv run python -X utf8 tools/research_wiki.py log '<wiki-dir>' "<message>"` — append log
- `uv run python -X utf8 tools/research_wiki.py stats '<wiki-dir>'` — get statistics (optional, for the report)

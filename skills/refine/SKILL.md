---
name: refine
description: Use when the user wants to iteratively improve a research artifact until it reaches a target quality — repeatedly reviewing, applying fixes, and re-checking rather than doing a single pass.
argument-hint: <artifact-slug-or-path> [--max-rounds N] [--target-score N] [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /refine

> General-purpose multi-round iterative improvement loop for any research artifact
> (idea, proposal, experiment plan, paper draft).
> Each round reviews the artifact, applies source-backed fixes, verifies the changes, and reviews the resulting version.
> Completion requires a verified final version, the requested score, and no unresolved blocking issues.
> Outputs the best verified artifact, improvement history, and an explicit run status even when the work is incomplete.

For manuscript files, preserve the selected topic, draft version, and source filename under configured `paper_root`. Routine revisions stay in that draft; requested structural alternatives or independent evaluations fork a new sibling draft under the same undated topic, recording the parent and revision purpose. Store manuscript-specific review notes and backups in that workspace's `reviews/` and `history/`; do not generate replacement manuscripts or content artifacts inside the code repository.

## Inputs

- `artifact`: the artifact to improve, one of:
  - slug of a wiki page (searched in ideas/experiments/claims/outputs/)
  - file path (e.g. `wiki/outputs/paper-draft-v1.md`)
- `--max-rounds N` (optional, default 4): maximum improvement rounds (positive integer). A final review of a changed version verifies that round; it is not another edit round. Reuse an unchanged current review, so at most N+1 successful state reviews are needed; a failed review may be retried once.
- `--target-score N` (optional, default 8): requested review-score threshold (1-10), used together with the completion gate below; a high score alone does not establish completion.
- `--difficulty` (optional, default `hard`): difficulty level passed to /llm-review
- `--focus` (optional): review focus passed to /llm-review

## Outputs

- **Improved artifact** (wiki page or file, updated in place)
- **Wiki entity updates** (if review finds claims needing strengthening or identifies gaps)
- **REFINE_REPORT** (output to terminal):
  - Score trajectory across all rounds
  - Cumulative list of fixed issues
  - Final-version review score/verdict, or `unverified` if the current version could not be reviewed
  - Run status, stop reason, required verification, and every unresolved issue

## Wiki Interaction

### Reads
- `wiki/ideas/*.md` — if artifact is an idea
- `wiki/experiments/*.md` — if artifact is an experiment plan
- `wiki/claims/*.md` — claims referenced by the review
- `wiki/papers/*.md` — papers referenced by the review
- `wiki/outputs/*.md` — if artifact is a wiki output
- `<paper_root>/<paper-id>/<draft-id>/` — if artifact is a manuscript (selected source and supporting files)
- `wiki/graph/context_brief.md` — global context passed to /llm-review
- `wiki/graph/open_questions.md` — check whether new gaps need recording

### Writes
- `wiki/ideas/{slug}.md` — if artifact is an idea, fix issues found by review
- `wiki/experiments/{slug}.md` — if artifact is an experiment plan
- `wiki/claims/{slug}.md` — if review finds a claim needing update (confidence adjustment, evidence note)
- `wiki/outputs/*.md` — if artifact is a wiki output
- `<paper_root>/<paper-id>/<draft-id>/` — if artifact is a manuscript (selected source and supporting files)
- `wiki/graph/edges.jsonl` — if new relationships are discovered during fixes
- `wiki/graph/context_brief.md` — rebuild after each round if wiki changes were made
- `wiki/graph/open_questions.md` — rebuild after each round if wiki changes were made
- `wiki/log/` — append operation log

### Graph edges created
- Depends on fix content; may add: `supports`, `addresses_gap`, `inspired_by`, etc.

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`, matching `README.md`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

### Step 1: Initialize

1. **Locate artifact**:
   - If slug: search sequentially in `wiki/ideas/`, `wiki/experiments/`, `wiki/claims/`, `wiki/outputs/`, `wiki/papers/` for `{slug}.md`
   - If file path: read directly
   - Record artifact type and path
2. **Read current content**: load full artifact text
3. Initialize round/review histories, a stable issue registry, substantive-progress tracking, and the last verified state using [references/tracking.md](references/tracking.md). Validate explicit round/score values unchanged and keep review verdicts separate from run status; do not roll back over user edits.

### Step 2: Iteration Loop

Repeat the following steps until the termination condition is met:

**Review the current state, then attempt improvement round N only if needed (N = 1, ..., max-rounds).** The initial review may complete the task with zero improvement rounds.

#### 2a. Review the Current Version

Use the latest review only if it covers the current artifact and supporting context unchanged. Otherwise call `/llm-review` and record the reviewed version and provenance:

```
Review skill: /llm-review (read and follow skills/llm-review/SKILL.md)
Args: "<artifact-path-or-content>" --difficulty {difficulty} --focus {focus}
```

Parse the review output and extract:
- `score` (1-10)
- `verdict` (ready / needs-work / major-revision / rethink)
- `weaknesses` (by severity: critical / major / minor)
- `actionable_items` (ranked list)
- `wiki_entity_mapping` (claims needing support, gaps identified)

Append each new review to `review_history` and `score_history` before evaluating it. Reconcile findings into `issue_registry`; preserve unresolved prior issues until a concrete source check or verification closes them. An issue disappearing from a later review is not, by itself, proof of a fix.

#### 2b. Evaluate the Completion Gate

Set `run_status = complete` only when all conditions hold:

- The latest successful review covers the current artifact and supporting context.
- `score >= target-score` and the review verdict is `ready`.
- No unresolved critical issue or major issue blocking the requested use remains; required source/grounding checks have passed.
- No missing evidence, author decision, or unperformed verification required for this request remains.

A `ready` verdict or high score cannot override a blocking issue. Minor residual limitations may remain only when they do not block the requested use and are disclosed. If the gate passes, finish without unnecessary further edits.

If the gate fails, continue safe, source-backed local fixes within the remaining rounds. When no such fixes remain, use `needs-evidence` for required external data/decisions/checks or `needs-revision` for unresolved design/content issues. A first-pass `rethink` is a recommendation, not an automatic halt: perform bounded useful fixes, but leave a fundamental redesign outside the request as unresolved.

#### 2c. Classify Actionable Items and Apply Fixes

Start an improvement round only when attempting safe changes; increment `round` once. Never run a new experiment, launch a calculation, compile LaTeX, or expand into a redesign to manufacture completion. The user performs external execution and compilation unless separately requested.

Read [references/fix-categories.md](references/fix-categories.md) when classifying actionable findings. Apply only supported in-scope artifact/wiki fixes; record missing evidence, new experiments, and out-of-scope decisions as unresolved with concrete handoffs. Review feedback alone does not establish source truth.

#### 2d. Verify Changes and Update Tracking

1. Re-read every changed artifact/page and check each attempted fix against its source, proof, or other appropriate evidence. Review feedback points to a possible defect; it is not substitute source evidence.
2. Run scoped `grounding_lint.py` on touched paper/concept/claim pages and any other checks required for this request. Keep red issues and failed/unperformed required checks open. Do not assume a missing external calculation or compilation passed.
3. Record actual changes in `wiki_changes`. Move an issue to `fixed_issues` only after the relevant verification succeeds; derive `unresolved_issues` from the remaining open registry instead of accumulating duplicate/stale findings.
4. After changes to the artifact or relevant support, review that final state through `/llm-review` and record it as in 2a. Reopen recurring findings and refresh the fixed/unresolved lists from the reconciled registry. This verification review is required even in the last allowed improvement round. If review fails twice, keep the current state `unverified` and stop with `review-unavailable`; never present the pre-edit score as a final-version score.
5. Record whether this round made verified substantive progress (a material issue was resolved or required evidence/check became available). If yes, reset `no_progress_rounds = 0`; otherwise increment it. Equal scores do not negate verified progress.

#### 2e. Maintain Derived Data and Decide Whether to Continue

Rebuild derived context/open-question files through `tools/research_wiki.py` after actual wiki changes, including changes to a wiki artifact. Record any failed write/rebuild as an open verification issue.

Evaluate 2b on the verified final state first. If it still fails, stop with an explicit incomplete status when appropriate:

| Run status | Stop condition |
|------------|----------------|
| `needs-evidence` | No further safe local fix; required user data, decision, calculation, or verification is unavailable |
| `needs-revision` | No remaining safe in-scope fix, or two consecutive completed improvement rounds have made no verified substantive progress |
| `round-limit` | The allowed improvement rounds are exhausted while the completion gate still fails |
| `review-unavailable` | Review retry failed; final-state quality is unverified |
| `write-error` | A required write or consistency update failed; report actual changed paths and unresolved state |

Use the most specific stopping reason when several apply; never label these outcomes complete or converged. Otherwise continue with the current verified review. Score plateaus alone do not stop the loop. Return the current artifact with its actual verification status, the last verified state when available, and any unverified later changes; do not call an unverified current file the best verified version.

### Step 3: Final Report

After stopping, use [references/report-format.md](references/report-format.md) to return the artifact, reviewed version/context, actual score or `unverified`, round/review history, fixed and open issues, checks, external handoffs, and explicit run status. An incomplete run still delivers the available artifact and findings.

Append a log only after actual artifact/wiki changes or an explicitly authorized report archive:
```shell
uv run python -X utf8 tools/research_wiki.py log '@configured' "refine | {artifact-slug} | {N} rounds | final-version score {score-or-unverified} | status: {run_status} | {stop_reason}"
```

A zero-edit evaluation without a saved report returns its findings without writing logs or maintenance files. A failed run with actual changes still logs those changes and the incomplete outcome.

## Source grounding

This skill generates durable content, so it follows the shared **Source Grounding Discipline** — see `skills/shared-references/source-grounding.md`.

- Apply only fixes grounded in the `/llm-review` feedback; do not introduce new claims, numbers, or citations the review did not support.
- List unresolved gaps explicitly rather than papering over them with invented content.
- If a refinement touches `papers/`, `concepts/`, or `claims/`, re-run `grounding_lint.py` on those pages before finishing.

## Constraints

- **Evidence determines completion**: high scores and `ready` never override critical/major blockers, missing evidence, or failed required checks. Assess the actual final version.
- **Progress is substantive**: stop after two consecutive improvement rounds with no verified substantive progress; a repeated score alone is not a stop rule.
- **External execution remains with the user**: do not run new calculations/experiments or compile LaTeX unless separately requested; report required handoffs honestly.
- **Wiki modifications limited to review suggestions**: refine only modifies wiki entities explicitly recommended by the review; do not expand scope proactively
- **Unresolved issues must be listed**: do not silently skip issues that cannot be resolved in the loop
- **Preserve improvement history**: score_history and fixed_issues are recorded in full; do not discard intermediate state
- **Pass review parameters through**: --difficulty and --focus are passed through to /llm-review; maintain consistent review standards
- **Artifact updated in place**: fixes modify the original file directly; do not create copies

## Error Handling

- **Artifact not found**: prompt user to check slug or path, list likely candidate pages
- **/llm-review call fails**: retry once; if still failing, return `review-unavailable`, the artifact/history, and any last verified-version score clearly distinguished from the unverified current version.
- **Wiki write/rebuild fails**: report `write-error`, actual changes and failed paths; do not hide the failure behind a high review score or overwrite uncertain user edits.
- **Initial score already meets target**: finish with zero improvement rounds only if the full completion gate passes; otherwise address the blocking findings.
- **Only external/out-of-scope issues remain**: return `needs-evidence` or `needs-revision` with concrete missing inputs and the best verified artifact; do not wait silently or claim success.

## Dependencies

### Tools
- `uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'` — rebuild query_pack
- `uv run python -X utf8 tools/research_wiki.py rebuild-open-questions '@configured'` — rebuild gap_map
- `uv run python -X utf8 tools/research_wiki.py add-edge '@configured' ...` — add graph edge (if needed)
- `uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only <touched-path> --json` — scoped source-grounding check
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"` — append log entry

### Skills
- `/llm-review` — each round's review (core dependency)

### Host capabilities
- Read/search the artifact and relevant support; edit only the authorized artifact/wiki scope.
- Execute `/llm-review` by reading its skill instructions in the current agent; a host-specific Skill tool is not required.

### Shared References
- `skills/shared-references/review-protocol.md` — agent-local review via /llm-review

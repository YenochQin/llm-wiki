---
name: rebuttal
description: Use when responding to peer-review comments on a paper — turning reviewer concerns into a point-by-point rebuttal backed by wiki claims and recorded experiment evidence.
argument-hint: "<review-paths-or-text> [--paper-slug <slug>] [--venue <venue>] [--stress-test | --no-stress-test] [--format formal|rich]"
---

# /rebuttal

> Parse review comments, atomize each concern (Rvx-Cy numbering) and map it to a wiki claim,
> check whether evidence is sufficient (tracing back to wiki experiments),
> simulate reviewer follow-up questions in the current agent (stress-test, scored 1-5), and generate
> a formal plain-text rebuttal and a rich-text rebuttal.
> Deliver an honest draft even when evidence or review scores are weak. Report submission readiness separately from draft delivery; unresolved evidence and author decisions remain visible.

## Inputs

- `review`: source of review comments, one of:
  - file path (e.g. `raw/reviews/reviewer1.txt`, `raw/reviews/meta-review.md`)
  - multiple file paths (comma-separated: `raw/reviews/R1.txt,raw/reviews/R2.txt,raw/reviews/R3.txt`)
  - directly pasted review text
- `--paper-slug` (optional): slug of the associated paper in wiki/outputs/, used to locate PAPER_PLAN
- `--venue` (optional): target conference/journal (ICLR / NeurIPS / ICML / ACL / CVPR); affects rebuttal format and word limits
- `--stress-test` (optional, enabled by default): the current agent simulates reviewer follow-up; disable with `--no-stress-test`
- `--format` (optional, default `formal`): output format
  - `formal`: plain-text draft in submission style (resolve readiness gaps before pasting into a submission system)
  - `rich`: rich-text version (with wiki [[links]], detailed analysis, improvement plan)

## Outputs

- **wiki/outputs/rebuttal-{slug}.md** — rich-text rebuttal (with [[wikilinks]], evidence tracing, analysis tables)
- **wiki/outputs/rebuttal-{slug}.txt** — plain-text draft; paste into a submission system only after resolving marked gaps and author decisions
- **wiki/claims/*.md** — if a concern exposes an evidence gap, append a suggestion to `## Open questions`
- **wiki/log/** — append log entry

## Wiki Interaction

### Reads
- User-supplied manuscript passages, calculation/experiment records, and supporting files — usable evidence even before wiki ingestion; retain their actual provenance
- `wiki/claims/*.md` — map concerns to claims, check evidence sufficiency
- `wiki/experiments/*.md` — find experiment results supporting claims
- `wiki/papers/*.md` — find citation context for referenced papers
- `wiki/concepts/*.md` — understand the conceptual background of method-related concerns
- `wiki/ideas/*.md` — find the motivation and pilot results for ideas
- `wiki/outputs/PAPER_PLAN.md` — understand paper structure (from /paper-plan, if --paper-slug provided)
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/edges.jsonl` — claim-experiment-paper relationships
- `skills/shared-references/review-protocol.md` — agent-local stress-test and provenance

### Writes
- `wiki/outputs/rebuttal-{slug}.md` — rich-text version
- `wiki/outputs/rebuttal-{slug}.txt` — formal plain-text version
- `wiki/claims/*.md` — append reviewer-identified gaps to `## Open questions` (do not directly modify confidence/status; add suggestions only)
- `wiki/log/` — append log entry

### Graph edges created
- None (rebuttal is a query operation; does not modify the knowledge graph)

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

Additional steps:
1. Read `review-protocol.md` to confirm review mode and evidence requirements
2. Generate slug: `uv run python -X utf8 tools/research_wiki.py slug "{paper-slug}-rebuttal"`

### Steps 1–3: Parse, Atomize, and Map Concerns

Read [references/concern-analysis.md](references/concern-analysis.md) when processing the review comments. Preserve reviewer provenance, assign `Rvx-Cy` IDs, classify severity/type, and map each concern to available claim/evidence records. Unmapped concerns still receive a response; missing wiki evidence may be supported by identified user-provided files or remain an explicit gap.

### Step 4: Draft Rebuttal Responses

Read [references/response-strategies.md](references/response-strategies.md) when choosing a response strategy and drafting each concern's answer. Cite the actual supporting source or acknowledge the gap; never fabricate wiki records, data, or completed work.

Only user-confirmed scope/resources/dates become commitments. Otherwise retain `[AUTHOR INPUT NEEDED: confirm scope/resources/date]` as needed and deliver the draft without waiting for those details. The user performs external calculations/experiments unless separately requested.

### Step 5: Agent Stress-Test

If `--stress-test` is enabled (default), follow `shared-references/review-protocol.md` and assess each response in the current agent from a skeptical reviewer's perspective. Use the original atomic concerns (Rvx-Cy IDs), rebuttal text, and supporting evidence. Check whether the response addresses the concern, its evidence is traceable, and any commitments are specific, feasible, and actually confirmed by the user.

Score each response from 1–5:

- 1: unconvincing; deflection or unsupported assertions.
- 2: weak; vague or lacking concrete evidence.
- 3: acceptable; addresses the concern but could be stronger.
- 4: strong; concrete evidence and clear reasoning.
- 5: fully convincing; compelling evidence and a thorough response.

For scores <= 3, provide a follow-up question and concrete improvement. Keep responses scoring 4–5, strengthen those scoring 3, and rewrite those scoring 1–2 (consider acknowledging insufficient evidence rather than defending an unsupported assertion).

If any response scores <= 2, re-assess the revised responses once, for a maximum of two rounds. Record scores, revisions, unresolved questions, and the review mode. Multiple rounds by the same agent remain `self-review` when it drafted the responses. With `--no-stress-test`, record `not run` and leave scores unset; do not report a passing review. After the two-round limit, continue to Step 6 even if scores remain low. Preserve honest acknowledgments, unresolved concerns, and proposed improvements; a low score never withholds the draft.

### Step 6: Format Output + Safety Check

Read [references/output-formats.md](references/output-formats.md) when formatting both the plain-text and rich-text drafts. Keep readiness, blocking concern IDs, source gaps, unconfirmed proposals, and actual stress-test/check status visible; display the user-selected format while saving both drafts as described in 6d.

**6c. Verify coverage and assess provisional readiness**:
- Give every parsed concern a response or an explicit evidence/author-input placeholder. A missing comment or unresolved issue blocks readiness, not delivery of the available draft.
- Trace cited facts to existing wiki records or actual user-provided sources. Where evidence is unavailable, omit unsupported numbers/claims and state the limitation.
- Check every promised action, resource, and date against explicit user confirmation. Label unconfirmed proposals; never turn feasibility estimates into commitments.
- Assess readiness from substantive concerns and required checks, not average stress-test score. Open critical/major blockers, low-score unresolved responses, missing evidence, or author-input placeholders must remain listed and prevent a ready-for-author-review assessment.
- With a skipped/failed stress-test, report that verification as `not run`/`incomplete`; do not claim a passed review. Only use `ready-for-author-review` when the requested checks are complete and no substantive blocker remains; author review is still required before submission.
- Finalize readiness and save/deliver the drafts after the claim checks in 6d; these later checks must not leave an earlier ready label on a draft with unresolved failures.
- Do not run calculations/experiments, compile LaTeX, or submit/send the rebuttal unless separately requested.

**6d. Update wiki**:
- For existing claims with evidence gaps: append source-grounded suggestions to `## Open questions`; preserve confidence/status. Do not create placeholder claims in an empty wiki. Run scoped `grounding_lint.py` on changed claims and report any red issues as unresolved.
- Recompute readiness using these actual verification results before writing the final draft files. A required failed check prevents a ready label. Write both files under the configured external outputs directory and report their actual paths, displaying the requested format. If saving fails, still deliver the available draft in the conversation with the failed path and partial-delivery status.
- After actual writes, append a log with delivery/readiness and actual stress-test state (use `not run` or `incomplete` rather than an invented score):
  ```shell
  uv run python -X utf8 tools/research_wiki.py log '@configured' "rebuttal | {N} concerns addressed | {M} evidence gaps | readiness: {readiness} | stress-test: {score-or-not-run-or-incomplete}"
  ```

## Constraints

- **No fabrication**: every cited number/result must trace to an identified wiki or user-provided source; absent evidence remains explicit, never filled from memory.
- **Author-confirmed commitments only**: proposals are not promises. Use confirmed scope/resources/dates only; unknowns remain visible placeholders. Do not claim unperformed work is done.
- **Full draft delivery**: every concern has a response or an explicit gap marker. Unresolved concerns and low scores block readiness, never the available draft output.
- **Evidence traceability**: use a resolving wiki link or an identified user-provided source; do not fabricate wiki pages for un-ingested evidence.
- **Do not directly modify wiki claims**: rebuttal only appends suggestions to claims' Open questions; do not modify confidence/status
- **Review provenance**: during stress-test, follow review-protocol.md; a skeptical role or second pass does not establish independence
- **Concern ID format**: strictly use Rvx-Cy format (Rv1-C1, Rv1-C2, Rv2-C1) to ensure traceability
- **Specific proposals, explicit unknowns**: tie proposed revisions/validation to the concern and actual workflow; unconfirmed details are unknown, not mandatory invented dates or metrics. External execution and LaTeX compilation remain with the user unless separately requested.
- **Output to wiki/outputs/**: rebuttal files are stored uniformly in the wiki/outputs/ directory

## Error Handling

- **Review file not found**: report error, list available files under raw/reviews/
- **Review format cannot be parsed**: fall back to plain-text processing; use LLM to extract concerns; annotate in report
- **Concern cannot be mapped to a claim (unmapped)**: annotate as "unmapped"; still respond (based on paper content rather than wiki claim)
- **Stress-test evidence incomplete**: identify the affected responses and missing evidence; mark the pass incomplete rather than inventing support
- **Evidence severely insufficient**: deliver a conservative draft and concern-by-concern evidence-gap table; mark `needs-evidence` and suggest what would support each response without claiming completed validation.
- **Wiki empty**: use available user-provided manuscript/evidence and mark mappings `unmapped`; otherwise deliver explicit evidence-gap responses. Ingestion may be suggested but is not a precondition for drafting.
- **Responses still score 1-2 after stress-test**: deliver the revised draft with `needs-revision` or `needs-evidence`, unresolved concern IDs, and suggested fixes. Do not keep looping or suppress output.

## Dependencies

### Tools
- `uv run python -X utf8 tools/research_wiki.py slug "{title}"` — generate rebuttal slug
- `uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only <changed-claim-path> --json` — verify touched claims
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"` — append log entry

### Host capabilities
- Read/search local comments, wiki pages, and user-provided evidence.
- Write both rebuttal formats under the configured external outputs root; if saving fails, deliver the available draft in the conversation.

### Shared References
- `skills/shared-references/source-grounding.md` — anti-hallucination source-grounding discipline (general)
- `skills/shared-references/review-protocol.md` — agent-local stress-test and provenance

### Suggested follow-up skills
- `/paper-draft` — prepare revised paper (based on Paper Edits checklist)

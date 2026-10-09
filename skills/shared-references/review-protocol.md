# Agent Review Protocol

> Referenced by: `/llm-review`, `/novelty`, `/ideate`, `/paper-plan`, `/paper-draft`, `/rebuttal`, `/refine`

## Execution

The current agent performs the requested review using the artifact, source evidence, relevant context, and the caller's criteria. Review requires no additional model API, MCP reviewer, or service configuration. Continue the documented review step without asking the user to configure a second model.

Agent and model selection belongs to the user. Do not automatically spawn another reviewer, create a session, switch models, or send artifacts elsewhere. A user may run the same skill in another agent/session and provide that report for comparison.

## Choose the Review Task

- `/source-audit`: check whether ingested paper, concept, and claim pages faithfully represent canonical prepared sources. Trace quotations, numbers, units, signs, classifications, and omissions to the actual source. A general quality score cannot substitute for this audit.
- `/llm-review`: critique research artifacts for method, evidence sufficiency, writing, or completeness. It produces suggestions; the caller controls any edits.
- `/novelty`: assess differentiation against retrieved prior work; model opinion cannot establish that prior work does not exist.
- `/ideate`: generate and challenge alternatives in the current agent; multiple passes do not constitute multiple independent generators.

## Describe the Review Honestly

Record the reviewer as `current agent` and the mode as `agent-local` or `self-review` as applicable. Include an agent/model identifier only when known; otherwise leave it unknown. A different agent does not by itself establish a different model.

If the current agent authored or revised the artifact in the available context, label the pass `self-review`. A role change or additional pass does not establish independence. If a separate reviewer report is supplied, record its provenance and distinguish it from the current assessment. Do not claim an independent or blind review when prior judgments were already visible or the review history is unknown.

For a fresh review in another agent/session, provide the artifact, original evidence, relevant context, and criteria. Keep prior scores, recommendations, and proposed conclusions out of the initial review material when an independent first assessment is intended. Compare reports after that assessment.

## Evidence and Disagreements

- Tie each finding to a passage, source, recorded result, or explicit assumption; distinguish confirmed errors from uncertainty.
- Missing sources or experiment data remain evidence gaps. Additional review passes do not supply missing evidence.
- When comparing supplied reports, retain their findings and scores with provenance. Resolve disagreements against evidence; do not manufacture a second score or average scores into claim confidence.
- Agreement alone does not justify higher confidence. Never average away a critical finding; investigate it and preserve unresolved limitations in the report.
- Preserve each caller's review switches and write permissions. Report an incomplete review with the concrete missing evidence; do not mark it passed or silently skip a required gate.

## Readiness and Incomplete Outcomes

Scores and `ready` verdicts are supporting judgments, not proof of completion. The caller checks the actual final artifact, unresolved critical/major blockers, source evidence, and required verification. A pre-edit review cannot certify a later version. Keep delivery, review verdict, and completion/readiness separate; round limits, stalled substantive progress, unavailable evidence/review, and failed writes remain explicit incomplete outcomes. Return the available artifact and findings instead of withholding them for a higher score.

User-performed calculations, experiments, and LaTeX compilation remain external handoffs unless separately requested. Do not invent results, confirmed resources, deadlines, or passed checks to close a finding; proposed actions remain proposals until the user confirms them.

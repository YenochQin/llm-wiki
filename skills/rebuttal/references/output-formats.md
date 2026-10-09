# Rebuttal Output Formats

Read this reference when preparing the plain-text and rich-text draft layouts before final verification. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

**6a. Format rebuttal-{slug}.txt** (plain text). Mark incomplete drafts clearly at the top and retain visible author-input placeholders; do not label them ready for submission:

```
Draft readiness: {needs-evidence / needs-revision / needs-author-input / ready-for-author-review}
Unresolved inputs: {concern IDs and needed evidence/decisions, or none}

We thank the reviewers for their constructive feedback. We address each concern below.

Reviewer 1:

[Rv1-C1] {concern summary}
{response}

[Rv1-C2] {concern summary}
{response}

Reviewer 2:
...

Summary of Revisions:
- {bulleted list of planned changes}

Confirmed Additional Work (if applicable):
- {only user-confirmed scope/resources/date, or none}

Author Inputs Needed (omit when none):
- {unconfirmed proposal or missing evidence, tied to concern ID; do not present as a promise}
```

**6b. Format rich-text rebuttal-{slug}.md**:

```markdown
# Rebuttal Analysis: {paper title}

- Draft delivery: {complete / partial with exact missing comments or failed writes}
- Submission readiness: {needs-evidence / needs-revision / needs-author-input / ready-for-author-review}
- Blocking issues: {concern IDs, evidence gaps, unconfirmed commitments, required checks}

## Coverage Summary
| Concern ID | Type | Severity | Claim | Evidence Status | Stress-Test Score | Strategy |
|------------|------|----------|-------|-----------------|------------|----------|
| Rv1-C1 | method | critical | [[claim-slug]] | sufficient | 4/5 | A |
| Rv1-C2 | missing | major | [[claim-slug]] | insufficient | 3/5 | B |

## Responses
### Reviewer 1
**[Rv1-C1]** ...
**[Rv1-C2]** ...

## Evidence Gap Analysis
| Claim | Confidence | Gap | Needed |
|-------|-----------|-----|--------|
| [[claim-slug]] | 0.5 | No ablation on dataset X | Run ablation experiment |

## Action Items

### Paper Edits
| Section | Change | Reason |
|---------|--------|--------|
| Section 3.2 | Clarify notation | Rv1-C3 clarity concern |

### Wiki Updates
| Page | Update | Reason |
|------|--------|--------|
| claims/{slug} | Add open question | Rv2-C1 evidence gap |

### Suggested Experiments
| Experiment | Target Claim | Suggested by |
|-----------|-------------|--------------|
| ablation-dataset-x | [[claim-slug]] | Rv1-C2 |

→ Discuss supplementary calculations/experiments and required manual steps with the user. The user carries out any agreed calculations/experiments externally.

## Agent Stress-Test Summary
- Mode: {agent-local / self-review / not run}
- Average score: {N}/5
- Scores 4-5: {N}/{total}
- Scores 1-3: {N}/{total} (record revisions and any unresolved questions)
- With --no-stress-test: scores unset; omit numerical summary

## Verification
- Evidence traceability: {verified / open}, with actual source records
- Commitments: {confirmed / author input needed / none}
- Concern coverage: {answered count}/{total}; missing or unresolved IDs: {list or none}
- Challenged claims: {handling and remaining limitations}
- Required checks: {passed / failed / pending / not in scope}; do not pre-check unfinished items
```

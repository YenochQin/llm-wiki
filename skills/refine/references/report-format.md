# Refinement Delivery Report

Read this reference when delivering a completed or explicitly incomplete refinement run. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

After iteration ends, generate the REFINE_REPORT:

```markdown
# Refine Loop Report: {artifact title}

## Summary
- **Artifact**: {slug or path}
- **Improvement rounds**: {N} / {max-rounds}; verification reviews: {count}
- **Score trajectory**: {score_history, e.g., 5 → 6 → 7 → 8}
- **Final-version score/verdict**: {score/10 and verdict, or unverified}; reviewed version/context: {identifier}
- **Run status**: {complete / round-limit / needs-evidence / needs-revision / review-unavailable / write-error}
- **Stop reason**: {concrete reason, separate from review verdict}
- **Completion gate**: {passed / not passed}; open critical/major issues: {counts}
- **Required checks and external handoffs**: {verified results, failures, pending user calculation/compilation/decision; no assumed pass}

## Issues Fixed ({count})

| Round | Issue | Severity | Fix applied |
|-------|-------|----------|-------------|
| 1 | Method description too vague | major | Added specific algorithm steps |
| 1 | Claim confidence too high | major | Lowered [[claim-slug]] confidence 0.8→0.6 |
| 2 | Missing ablation design | minor | Added ablation plan |

## Wiki Changes Made

| Page | Change | Round |
|------|--------|-------|
| `wiki/claims/{slug}.md` | confidence 0.8 → 0.6 | 1 |
| `wiki/graph/edges.jsonl` | +1 edge (addresses_gap) | 2 |

## Unresolved Issues ({count})

| Issue | Severity | Suggested action |
|-------|----------|------------------|
| Missing experimental validation | critical | Discuss required validation and manual steps with the user; assess actual results once provided |
| Missing comparison paper | major | Run `/ingest` for {paper-title} |

## Next Steps
- {based on verdict and unresolved issues}
```

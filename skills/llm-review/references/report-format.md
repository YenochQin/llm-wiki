# Agent-Local Review Report Format

Read this reference when formatting the completed review, after the requested review passes. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Synthesize Step 2 + Step 3 results into a structured Review Report:

```markdown
# Review Report: {artifact title}

## Meta
- **Artifact type**: {idea / experiment / claim / paper-draft / proposal}
- **Difficulty**: {standard / hard / adversarial}
- **Focus**: {method / evidence / writing / completeness / comprehensive}
- **Reviewer**: current agent
- **Review mode**: {agent-local / self-review}; separate reports only when actually supplied
- **Passes**: {1 for standard, 2 for hard/adversarial}

## Score: {final score}/10 — {verdict}

| Verdict | Meaning |
|---------|---------|
| ready | Ready to use or submit directly |
| needs-work | Clear improvement points; usable after fixes |
| major-revision | Core sections need significant revision |
| rethink | Fundamental direction may be flawed; reconsider |

## Strengths
1. {strength 1}
2. {strength 2}
...

## Weaknesses (by severity)

### Critical
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Major
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Minor
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

## Questions
1. {question}
...

## Wiki Entity Mapping

### Claims needing stronger support
| Claim | Current confidence | Issue | Suggested action |
|-------|-------------------|-------|------------------|
| [[claim-slug]] | 0.6 | Evidence is indirect | Run targeted experiment |

### Knowledge gaps identified
| Gap | Related to | Suggested action |
|-----|-----------|------------------|
| {description} | [[slug]] | /ingest, /ask, or discuss a feasible calculation/experiment with the user |

### Suggested wiki updates
- `wiki/claims/{slug}.md`: update confidence, add evidence note
- `wiki/ideas/{slug}.md`: add risk factor from review
- `wiki/graph/open_questions.md`: will be updated on next rebuild

## Self-Challenge History (hard/adversarial only)

### Initial Review
{summary of initial assessment}

### Self-Challenge
{confirmed weaknesses / uncertain risks / rejected objections}
...

## Actionable Items (ranked)
1. [CRITICAL] {action item}
2. [MAJOR] {action item}
3. [MINOR] {action item}
```

# Rebuttal Response Strategies

Read this reference when drafting a response according to its evidence, clarity, scope, or novelty concern. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Draft a response for each concern according to its strategy:

**Strategy A — Evidence sufficient (respond directly):**
- Cite specific experiment results and data (annotate source, ensure traceability to wiki/experiments/)
- If supporting evidence was provided directly rather than ingested, cite its actual file/table/passage and retain that provenance; do not invent a wiki record.
- Point to evidence in the wiki (convert to paper citations)
- If the concern is based on a misunderstanding: politely clarify, point to the relevant Section in the paper

**Strategy B — Evidence insufficient (acknowledge + proposed next step):**
- Acknowledge the exact evidence gap and its implications; narrow the claim or state the limitation when that is the honest response.
- Suggest a supplementary calculation/experiment for discussion, taking account of the user's workflow and manual steps. Keep suggestions separate from author commitments.
- Include an experiment, resource allocation, or completion date as a commitment only when the user has explicitly confirmed it in the available context. Otherwise use `[AUTHOR INPUT NEEDED: confirm scope/resources/date]` where needed; never invent a timeline or wait to deliver the draft for it.
- Do not claim that planned calculations, experiments, manuscript edits, or compilation have already been performed without actual confirmation/evidence. The user executes external work unless separately requested.

**Strategy C — Clarity issue (commit to revision):**
- Acknowledge the unclear expression
- Provide the improved description (show the revised text directly in the rebuttal)
- List specific Paper Edit plans

**Strategy D — Scope/Novelty challenge (argue):**
- Highlight essential differences from existing work
- Cite novelty-check results (if available)
- Point out differences the reviewer may have overlooked

**Format for each response**:
```markdown
**[Rvx-Cy]** {concern summary}

{response text, 2-5 sentences, annotated sources for traceability}
```

**Safety checks (per response)**:
- [ ] No fabrication: do not fabricate data or experiment results
- [ ] No overpromise: each commitment/date/resource is user-confirmed; unconfirmed proposals and author-input placeholders are visible
- [ ] Every cited datum traces to a wiki record or an identified user-provided source; absent evidence remains a gap
- [ ] If claim is challenged/deprecated, do not pretend it is supported

# Refinement Fix Categories

Read this reference when deciding which reviewed findings can be fixed within the current improvement round. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Classify and handle each actionable item:

**Category A — Method/content issues (current agent fixes):**
- Method description too vague → add details
- Missing comparative analysis → add comparison against baseline
- Incomplete argumentative logic → add reasoning steps
- Unclear expression → rewrite relevant paragraphs
- → Edit the artifact file directly

**Category B — Wiki knowledge gaps (suggest external operations):**
- Insufficient claim evidence → identify whether more source evidence (`/ingest`) or a user-planned calculation/experiment is needed; discuss the latter with the user
- Missing related work citations → suggest running `/ingest` to add papers
- Requires experimental validation → suggest running the experiment externally, then discussing the actual results and remaining uncertainties with the user
- → Record in `unresolved_issues`, list suggested operations in the report
- → If claim confidence needs adjustment, update `wiki/claims/{slug}.md` directly

**Category C — Claim status updates (current agent fixes wiki):**
- Review says a claim's confidence should be lowered → update claim page
- Review discovers a new gap → record to gap_map (via rebuild)
- Review discovers a new relationship → add graph edge
- → Update relevant wiki pages, record in `wiki_changes`

**Category D — Out of scope (skip):**
- Requires new experimental data → cannot resolve in refine loop
- Requires domain expert judgment → mark as unresolved
- → Record in `unresolved_issues`

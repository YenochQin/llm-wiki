# Paper Plan Persistence and Report

Read this reference after the mandatory review, when saving the plan and returning PAPER_PLAN_REPORT. Paths are relative to the llm-wiki repository root unless an external root is explicitly named.

1. **Generate slug**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py slug "<working-title>"
   ```

2. **Write the plan** to the resolved external `wiki/outputs/paper-plan-{slug}-{date}.md`, containing:
   - Metadata: title, date, target claims, research object/modes, supplied venue or `unspecified`
   - Venue/format requirements: confirmed source and date checked, or explicit unknowns; mark budget estimates provisional where needed
   - Evidence Map: actual source locations, support/scope, counter-evidence, and gaps
   - Complete selected section outline, with review revisions and source-backed figure/table plan (which may contain zero items)
   - Citation Plan and verification coverage
   - Agent Review Summary: actual findings, score if assessed, mode, revision record, and checks of the final version
   - Remaining evidence, citation, review, and format gaps

   Deliver the available outline even when evidence is incomplete. Label it a draft with unresolved dependencies; do not call it evidence-ready or format-compliant while the corresponding gaps remain. Review scores alone do not establish readiness. Keep this operation within plan/output/derived-state writes; do not create experiment pages, edit claim confidence/status, or run missing research work.

3. **Add graph edges** only for existing target claims and cited wiki papers:
   ```shell
   # plan → target claim
   uv run python -X utf8 tools/research_wiki.py add-edge '@configured' --from "outputs/paper-plan-{slug}-{date}" --to "claims/{primary-claim}" --type derived_from --evidence "Paper plan built from this claim"

   # plan → key paper
   uv run python -X utf8 tools/research_wiki.py add-edge '@configured' --from "outputs/paper-plan-{slug}-{date}" --to "papers/{paper-slug}" --type derived_from --evidence "Paper plan cites this paper"
   ```
   Supplemental source-file links remain in the plan; do not fabricate graph nodes or treat the plan as new evidence for its own claims.

4. **Rebuild derived data**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py rebuild-context-brief '@configured'
   ```

5. **Append log after actual writes**:
   ```shell
   uv run python -X utf8 tools/research_wiki.py log '@configured' "paper-plan | {venue-or-unspecified} outline for [[{slug}]] | modes: {modes} | claims: {claim-list} | citations: {verified}/{total} | gaps: {gap-summary}"
   ```

6. **Return PAPER_PLAN_REPORT** using actual values and selected section titles:
   ```markdown
   # Paper Plan Report

   ## Meta
   - Title: {working title}
   - Research object/modes: {actual classification}
   - Venue: {supplied venue or unspecified}
   - Format/budget: {verified rules with source/date, or provisional/unknown}
   - Date: {date}
   - Saved plan: {actual absolute path}
   - Delivery/readiness: {draft delivered; remaining evidence/format/review gaps or checked scope}

   ## Claims → Evidence → Sections
   | Claim | Recorded status/confidence | Evidence and scope | Open gaps | Selected section |
   |-------|----------------------------|--------------------|-----------|------------------|
   | {existing claim link} | {actual values} | {actual source and support} | {gap or none} | {selected title} |

   ## Budget
   | Selected section | Allocation/unit | Verified or provisional | Argument served |
   |------------------|-----------------|-------------------------|-----------------|
   | {actual title} | {estimate in applicable units} | {basis} | {claim/purpose} |

   ## Figures/Tables: {actual count; zero is valid}
   ## Citations: {verified}/{total} verified, {unconfirmed_count} [UNCONFIRMED]
   ## Agent Review: {actual score or not assessed}, verdict: {actual verdict}, mode: {agent-local / self-review}

   ## Remaining Gaps and Next Steps
   - {claim-specific proof, computational, observational, citation, or format dependencies}
   - {draftable scope and dependencies for /paper-draft; do not invent missing results}
   ```

If a write or derived-data operation fails, report the actual saved paths and incomplete operations rather than claiming persistence succeeded. Return the available plan in the conversation if it could not be saved. User-performed research work and LaTeX compilation remain separate from this planning workflow.

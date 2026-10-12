# Idea Generation Report Format

Read this reference when returning ranked ideas, write status, and validation gaps, including no-write outcomes. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

6. **Print IDEA_REPORT to terminal**:
   ```markdown
   # Idea Generation Report

   ## Pipeline Summary
   - Direction: {direction}
   - Phase 1: Scanned {N} external papers, {M} wiki gaps identified
   - Phase 2: Generated {X} candidates (initial pass: {a}, alternatives: {b}; current agent)
   - Phase 3: {Y} survived initial filter (from {X})
   - Phase 4: Deep validation on top {Z}; review mode: {agent-local / self-review / not run}
   - Outcome: {recorded / partial / awaiting-selection / needs-topic / source-unavailable / no-supported-candidates}
   - Phase 5: {P} proposed + {F} failed = {K} pages actually saved / {max-ideas} cap; {R} report-only candidates
   - Source/validation gaps: {exact missing evidence or assessments; never label missing checks passed}

   ## Top Ideas (ranked)

   Use wikilinks only for saved/existing pages; unsaved candidates use plain titles. Scores are actual assessments or explicit `not run`/`unverified` labels.

   | Rank | Idea | Novelty | Review | Gap Align | Status | Persistence |
   |------|------|---------|--------|-----------|--------|-------------|
   | 1 | [[saved-slug]] | 4/5 | 7/10 | +2 | proposed | saved |
   | 2 | <unselected title> | 3/5 | unverified | +0 | candidate | report-only |

   ## Filtered Out
   | Idea | Reason | Persistence |
   |------|--------|-------------|
   | [[saved-failed-slug]] | Similar published work exists: <linked source> | saved: failed |
   | <unselected title, plain text> | <specific reason> | report-only |

   ## Suggested Next Steps
   - Discuss a feasible calculation/experiment for the top idea with the user, including manual preparation and execution steps
   - Run `/novelty` on any idea before investing time

   ## Wiki Growth
   | Metric | Before | After | Delta |
   |--------|--------|-------|-------|
   | Papers | {before} | {after} | +{delta} |
   | Claims | {before} | {after} | +{delta} |
   | Ideas | {before} | {after} | +{delta} |
   | Edges | {before} | {after} | +{delta} |
   | Maturity | {before_level} | {after_level} | {unchanged/upgraded} |
   (Only rows with delta != 0 are shown. Data is computed by comparing `maturity_before` from the pre-condition step against a fresh `maturity --json` call here.)
   ```

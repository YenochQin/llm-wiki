# Refinement State Tracking

Read this reference when initializing a refinement run or reconstructing its existing tracked state. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

3. **Initialize tracking variables**:
   - `round = 0`
   - `score_history = []`
   - `fixed_issues = []`
   - `unresolved_issues = []`
   - `wiki_changes = []`
   - `issue_registry = {}` (stable issue id, severity, status, required evidence/check, verification)
   - `review_history = []` (version/context identifier, score, verdict, review mode)
   - `no_progress_rounds = 0`
   - `run_status = None`
   - Retain the last verified artifact content in memory (and the existing manuscript history when applicable), so a later failed verification cannot erase which state was actually checked. Do not roll back over user edits automatically.
   Validate explicit round/score values without changing them. Keep review verdicts separate from the run status.

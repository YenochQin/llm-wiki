# Section-by-Section Manuscript Writing

Read this reference when collecting material, writing, polishing, or optionally reviewing a selected section. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

For each section (in the outline order from PAPER_PLAN); if `--sections` is specified, write only those sections:

**3a. Collect Material**

From the section definition in PAPER_PLAN, extract:
- the claims this section supports
- the list of corresponding wiki pages and identified supplemental evidence files
- planned figures/tables
- citation list

Read the relevant portions of the mapped evidence; these are examples, not required sections:
- Introduction → wiki/ideas/{idea}.md#Motivation + wiki/topics/{topic}.md#Overview
- Related Work → wiki/papers/*.md#Related + wiki/concepts/*.md#Comparison
- Method → wiki/concepts/*.md#Formal_notation + wiki/claims/{claim}.md#Statement
- Theory/Derivation → source-anchored assumptions, proof/derivation notes, and limits identified in the plan
- Computational Method/Results → identified calculation reports/data, actual settings, convergence and numerical-error records
- Experiments → @experiment-root/*.md#Results + @experiment-root/*.md#Analysis
- Conclusion → wiki/graph/open_questions.md + wiki/claims/*.md#Open_questions

**3b. Write LaTeX**

Following `shared-references/academic-writing.md`:
- Write according to the paragraph plan for that section
- Insert `\cite{key}` citations (keys mapped from citation plan)
- Insert `\ref{fig:name}` / `\ref{tab:name}` references to figures/tables
- Use symbols defined in `math_commands.tex`
- Begin each paragraph with a topic sentence
- Evidence sections: explain how the proof, calculation, or observation supports the claim under its recorded conditions; do not substitute planned work for completed evidence

**3c. De-AI Polish**

Apply de-AI polish to each written section (per academic-writing.md):
1. Scan and replace AI-signature vocabulary (delve, leverage, utilize, comprehensive...)
2. Remove excessive hedging
3. Vary sentence openings (avoid consecutive identical sentence structures)
4. Remove filler sentences (sentences that add no information)
5. Ensure active voice predominates
6. Check notation consistency

**3d. Optional Agent Review (--review)**

If `--review` is enabled, review each section in the current agent using `/llm-review --difficulty standard --focus writing`. Read and follow `skills/llm-review/SKILL.md` and `shared-references/review-protocol.md`.

Use the section's LaTeX, target claims, evidence, and shared notation. Check clarity, logical flow, claim-evidence alignment, notation consistency, missing content, and remaining AI-style language. Record specific findings and the review mode; a review of a section just written by the current agent is `self-review`.

Apply targeted edits to address the findings without rewriting the entire section. Keep unsupported claims marked as gaps rather than inventing evidence.

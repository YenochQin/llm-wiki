# /ingest Content Quality Gate

Open this reference before drafting or revising Step 3/4 outputs. It turns the comparison reports' failures into a concrete quality floor.

## Failure modes to prevent

- Good content but no runtime trail: missing `log.md`, missing graph rebuilds, or `index.md` not updated.
- Good scaffolding but thin pages: empty `claims/`, concept pages with only definitions, or paper pages that summarize without reusable claims/concepts.
- Source drift: losing the paper's original section structure, equations, tables, figures, or precise terminology.
- Overclaiming: high confidence or "necessary/sufficient" language without direct proof and clear scope.

## Paper page floor

A paper page should let a later agent reconstruct what the source contributed without reopening the source immediately.

- Use the prepared MinerU frontmatter (`sections`, `figures`, `abstract_excerpt`) as the outline anchor.
- Map `## Method` and `## Results` to source sections when the source has clear sections. For chapters, preserve chapter subsection structure; for empirical papers, name datasets, instruments, protocols, tables, figures, and main metrics; for theory papers, name definitions, assumptions, propositions, equations, and derivation steps.
- Preserve key equations in LaTeX when the source contains formulas. Prefer one or two central equations over a long dump.
- `## Limitations` and `## Open questions` should be source-grounded when possible, then clearly label any agent inference as "Inferred".
- `## Related` must expose all new/updated concepts, claims, foundations, and people touched by the ingest.

## Concept page floor

A concept page is reusable knowledge, not a glossary stub.

- `## Definition`: one precise definition, scoped to the field.
- `## Source excerpts`: at least one exact original-language excerpt per grounding paper, linked to the prepared markdown. If the source has a formal definition or equation, use that as one excerpt.
- `## Intuition`: explain why the concept exists and what problem it solves.
- `## Formal notation`: include notation/equations/algorithmic form when available; write "No formal notation in the source" only when true.
- `## Variants`: list variants, special cases, gauges, approximations, baselines, or closely related formulations when the source distinguishes them.
- `## Comparison`: use a compact table when there are two or more variants, neighboring concepts, methods, or assumptions worth contrasting.
- `## When to use`: give concrete applicability conditions, thresholds, regimes, or examples when the source supports them.
- `## Known limitations` and `## Open problems`: include at least one grounded limitation/question, or state why the source does not provide one.
- `## My understanding`: add a concise synthesis in the maintainer's voice; do not duplicate the definition.

## Claim page floor

Claims are the wiki's memory of evidence and disagreement.

- Create or update at least one claim for every substantive paper/chapter/review. Skip only for sources that genuinely do not make a defensible proposition, and record the reason.
- `## Statement`: make the claim narrow enough to be testable or evidence-bearing.
- `## Evidence summary`: cite concrete paper details, not just "the paper argues".
- `## Conditions and scope`: state where the claim applies; avoid universal wording unless the source proves it.
- `## Counter-evidence`: include explicit counter-evidence, limitations, alternative explanations, or "No direct counter-evidence in this source; possible risk is ...".
- `## Open questions`: include what would change the confidence.
- Confidence guidance: `0.2-0.4` speculative/weak, `0.5-0.7` plausible with limited evidence, `0.7-0.85` well supported in scope, `>0.85` reserved for direct strong evidence with narrow conditions.

## Runtime completeness floor

Normal ingest output should include:

- paper page created
- at least one concept created or existing concept materially updated
- at least one claim created or existing claim materially updated
- people handling: created only if importance >= 4, otherwise update existing pages if present
- `index.md` updated or rebuilt
- `log.md` appended in `## [YYYY-MM-DD] ingest | ...` form
- graph edges/citations written through `tools/research_wiki.py`
- `context_brief.md` and `open_questions.md` rebuilt outside INIT MODE

If any item is absent, the final report should name the exception. Do not hide a thin ingest behind a successful page count.

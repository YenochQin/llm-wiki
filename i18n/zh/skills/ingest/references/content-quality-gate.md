# /ingest Content Quality Gate

Open this reference before drafting or revising Step 3/4 outputs. It turns the comparison reports' failures into a concrete quality floor.

## Failure modes to prevent

- Good content but no runtime trail: missing `log.md`, missing graph rebuilds, or `index.md` not updated.
- Good scaffolding but thin pages: empty `claims/`, concept pages with only definitions, or paper pages that summarize without reusable claims/concepts.
- Source drift: losing the paper's original section structure, equations, tables, figures, or precise terminology.
- Overclaiming: high confidence or "necessary/sufficient" language without direct proof and clear scope.
- Equation format mismatch: using code fences or `\(` `\)` notation instead of Obsidian-compatible `$`/`$$` math.
- Vacuous guidance: "When to use" or "Known limitations" sections that could apply to any concept in the field.

## Paper page floor

A paper page should let a later agent reconstruct what the source contributed without reopening the source immediately.

- Use the prepared MinerU frontmatter (`sections`, `figures`, `abstract_excerpt`) as the outline anchor.
- Map `## Method` and `## Results` to source sections when the source has clear sections. For chapters, preserve chapter subsection structure and reference section numbers (e.g. "Sec 6.3"); for empirical papers, name datasets, instruments, protocols, tables, figures, and main metrics; for theory papers, name definitions, assumptions, propositions, equations, and derivation steps.
- Preserve key equations in LaTeX when the source contains formulas. Prefer one or two central equations over a long dump.
- `## Limitations` and `## Open questions` should be source-grounded when possible, then clearly label any agent inference as "Inferred".
- `## Related` must expose all new/updated concepts, claims, foundations, and people touched by the ingest.

## Concept page floor

A concept page is reusable knowledge, not a glossary stub.

- `## Definition`: one precise definition, scoped to the field.
- `## Source excerpts`: at least **two substantively different excerpts** per concept page when the source paper covers the concept in multiple passages. Each excerpt must be an exact original-language blockquote linked to the prepared markdown. If the source has a formal definition or equation, use that as one excerpt. Do not cherry-pick a generic opening sentence — the excerpts should collectively demonstrate the concept's formal structure.
- `## Intuition`: explain why the concept exists and what problem it solves.
- `## Formal notation`: include notation/equations/algorithmic form when available. Use `$...$` for inline math and `$$...$$` for display math — this is the Obsidian rendering standard. Do not use code fences for equations or `\(` `\)` notation. Write "No formal notation in the source" only when true.
- `## Variants`: list variants, special cases, gauges, approximations, baselines, or closely related formulations when the source distinguishes them.
- `## Comparison`: **required** when there are two or more variants, neighboring concepts, methods, or assumptions worth contrasting. Use a compact markdown table. Do not omit this section — if only one variant exists, compare against the nearest non-variant alternative.
- `## When to use`: give concrete applicability conditions — quantitative thresholds (e.g. "$Z \gtrsim 30$", "system size > 1000"), physical regimes, or specific task types. Avoid purely qualitative "use when reasoning about [topic]" formulations that could apply to any concept in the domain.
- `## Known limitations` and `## Open problems`: include at least one grounded limitation/question, or state why the source does not provide one.
- `## Key papers`: list all papers that materially ground this concept.
- `## My understanding`: add a concise synthesis in the maintainer's voice; do not duplicate the definition.

**All listed body sections are mandatory.** If a section truly has no content after good-faith effort, write a one-line scoped reason (e.g. "No comparison table warranted: only one formulation exists in this source and the nearest alternative [X] is already covered under [[related-concept]]."). Never omit a section silently.

## Claim page floor

Claims are the wiki's memory of evidence and disagreement.

- **Create or update at least one claim for every paper with importance ≥ 4.** A missing claims layer for a high-importance paper is a failed ingest. Skip claims only for sources that genuinely make no defensible proposition (purely bibliographic compilations, editorial prefaces, data appendices), and record the reason in the log and report.
- `## Statement`: make the claim narrow enough to be testable or evidence-bearing.
- `## Evidence summary`: cite concrete paper details (specific equations, tables, figures, experimental results), not just "the paper argues".
- `## Conditions and scope`: state where the claim applies; avoid universal wording unless the source proves it.
- `## Counter-evidence`: include explicit counter-evidence, limitations, alternative explanations, or "No direct counter-evidence in this source; possible risk is ...". Never leave this section blank or omit it.
- `## Open questions`: include what would change the confidence.
- Confidence guidance: `0.2–0.4` speculative/weak, `0.5–0.7` plausible with limited evidence, `0.7–0.85` well supported in scope, `>0.85` reserved for direct strong evidence with narrow conditions. Do not assign `>0.85` to claims whose scope extends beyond what the source directly demonstrates.

## Graph and runtime completeness floor

Before writing any graph files, verify `wiki/graph/` exists. Create it if missing.

Normal ingest output should include:

- paper page created
- at least one concept created or existing concept materially updated
- at least one claim created or existing claim materially updated (mandatory for importance ≥ 4)
- people handling: created only if importance ≥ 4, otherwise update existing pages if present
- `index.md` updated or rebuilt
- `log.md` appended in `## [YYYY-MM-DD] ingest | ...` form
- `wiki/graph/edges.jsonl` with at least one edge
- `wiki/graph/citations.jsonl` created (may be empty)
- `wiki/graph/context_brief.md` rebuilt outside INIT MODE
- `wiki/graph/open_questions.md` rebuilt outside INIT MODE

If any item is absent, the final report should name the exception. Do not hide a thin ingest behind a successful page count.

## Post-ingest verification checklist

After Step 8 (report), run this self-check before considering the ingest complete:

1. `wiki/papers/{slug}.md` exists and frontmatter YAML parses.
2. At least one concept page was created or materially updated with all mandatory sections.
3. Claims: at least one claim page exists (importance ≥ 4) or the report names the exception.
4. `wiki/graph/edges.jsonl` contains at least one edge involving the new paper.
5. `wiki/log.md` has a new `## [today]` entry.
6. `wiki/index.md` includes the new paper and all new entities.
7. LaTeX in all written pages uses `$`/`$$` notation exclusively — no code-fence equations, no `\(` `\)`.

If any check fails, fix it before emitting the final report.

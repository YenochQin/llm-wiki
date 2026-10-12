# Paper Plan Evidence Map

Read this reference when mapping selected claims to their evidence and planned sections. Paths are relative to the llm-wiki repository root unless an external root is explicitly named.

## Match evidence to the claim

Use the applicable modes, including combinations, rather than requiring every paper to contain experiments:

| Mode | Possible evidence | Checks to record when relevant to the claim |
|------|-------------------|--------------------------------------------|
| theory | Definitions, assumptions, complete proofs, analytical derivations, limiting cases | Logical dependencies, scope of the theorem/approximation, missing steps, boundary cases |
| computation | User-reported numerical calculations, simulations, numerical analysis, data-analysis outputs | Method/settings, inputs and units, convergence, truncation/discretization error, consistency or reference comparisons |
| experiment | Measurements, observations, sample analyses, instrument/protocol records | Conditions, calibration, controls, sample scope, uncertainty and applicable statistical reasoning |

A check is selected because the claim depends on it. Do not impose ML training seeds, baseline percentages, ablations, error bars, or fixed validation quotas on unrelated work. A deterministic calculation needs an appropriate numerical-error assessment, not invented sampling uncertainty. Numerical agreement alone cannot establish a general proof.

## Build the matrix

Read the original evidence, not only a claim's confidence score. Preserve recorded status/confidence and opposing evidence; do not edit claim pages during planning.

```markdown
| Claim | Recorded status/confidence | Mode | Actual source and location | Support and scope | Missing checks/evidence | Planned section |
|-------|----------------------------|------|----------------------------|-------------------|-------------------------|-----------------|
| [[claim-slug]] | {recorded values} | {applicable modes} | {existing paper + Evidence Pack anchor, or actual evidence-file link + location} | {what it supports and under which conditions} | {specific gap or none} | {selected section} |
```

- Paper evidence: follow its Evidence Pack/prepared-source anchors to the relevant proof, equation, table, or passage. Preserve paper/source identity differences.
- Linked research records: inspect actual reported results and supporting source files. Existing `experiments/` pages may be used, but their existence is not a requirement for theory or computation.
- User-identified derivation/calculation/observation files: keep their actual path and section/table/equation provenance as normal Markdown links. Do not invent a wiki page, source anchor, result, or graph node for them. This skill does not automatically ingest those files or change the claim schema.
- Inaccessible or incomplete evidence: label it unverified/partial/missing, explain the effect on the claim, and retain the gap in the plan. A proposed proof or future calculation is not completed evidence.
- Mixed claims: separate their theoretical, computational, and experimental components so support for one cannot conceal a gap in another.

Map primary claims to the contribution and core argument; map supporting claims to the relevant derivation, calculation, observation, comparison, or discussion. Contextual claims support motivation and related work. Use an ablation subsection only when a claim specifically concerns component contributions.

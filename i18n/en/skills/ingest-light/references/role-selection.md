# Role Selection

Use this guide before writing a light-ingest paper page. The role answers one question:

> What does this paper mainly help the dissertation introduction convince the reader of?

Pick one primary role unless the user explicitly requests otherwise. If multiple roles seem plausible, choose the role tied to the sentence where the paper will most likely be cited in the introduction. Mention secondary uses in `## Introduction use`, but keep the frontmatter role tag focused.

## Decision table

| If the paper mainly helps say... | Use role |
|---|---|
| this research direction matters | `background` |
| this method/theory/program is mature and appropriate | `method-foundation` |
| the thesis results can be compared against these data/results | `benchmark` |
| these atomic data are used in a real application area | `application` |
| existing data/calculations are missing, inconsistent, or insufficient | `gap-evidence` |
| this paper/book/chapter gives the broad review frame | `review-context` |

## Role meanings

### background

Use when the paper answers: **why is this research direction important?**

Typical evidence:

- medium/high-Z spectra matter for science or technology;
- atomic data are important to spectroscopy, databases, astrophysics, plasma, or nuclear studies;
- the paper gives domain motivation but is not mainly a method source or benchmark dataset.

### method-foundation

Use when the paper answers: **why is this theory or computational method reasonable?**

Typical evidence:

- MCDHF, RCI, MCHF, CI, GRASP, GRASP2K, GRASP2018, angular algebra, active-space, correlation model;
- handbook/textbook or code paper used to justify the method chapter or introduction method paragraph.

### benchmark

Use when the paper answers: **what can the thesis compare results with?**

Typical evidence:

- measured energies, wavelengths, lifetimes, branching fractions, oscillator strengths, isotope shifts, or hyperfine constants;
- high-quality prior calculations used as comparison tables;
- reference datasets or database evaluations.

### application

Use when the paper answers: **where will these atomic parameters be used?**

Typical evidence:

- abundance analysis, kilonova opacity, plasma diagnostics, laser spectroscopy, atomic clocks, nuclear-structure extraction, database construction.

### gap-evidence

Use when the paper answers: **what is missing or unresolved?**

Typical evidence:

- missing NIST/database values;
- incomplete level assignments;
- disagreement between experiment and theory;
- limited configuration coverage;
- uncertainty too large for the intended application.

### review-context

Use when the paper answers: **how should the broad literature be framed?**

Typical evidence:

- review article, handbook chapter, textbook chapter, broad survey;
- useful for organizing the introduction rather than supporting one narrow fact.

## Fallback question

If still unsure, ask:

> When citing this paper in the introduction, what do I most want the reader to believe?

- Direction is important -> `background`
- Method is appropriate -> `method-foundation`
- Results are comparable/verifiable -> `benchmark`
- Application is real -> `application`
- Gap remains -> `gap-evidence`
- Literature frame is broad -> `review-context`

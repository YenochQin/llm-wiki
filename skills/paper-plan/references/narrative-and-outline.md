# Paper Plan Narrative, Outline, and Venue Budget

Read this reference when selecting the storyline, sections, and format budget. Paths are relative to the llm-wiki repository root unless an external root is explicitly named.

## Determine the argument

1. Identify the problem/gap, target contribution, actual evidence, and conclusions within their supported scope. Do not infer impact solely from a confidence score.
2. Select the research object, audience, and applicable theory/computation/experiment modes from the claims and sources.
3. Compare against the closest relevant recorded prior work. Use the available comparisons and state missing coverage instead of requiring a fixed number of competitors.
4. Map each substantive section to target or contextual claims. Supporting sections such as notation or technical preliminaries serve the argument without inventing a new contribution claim.

## Select sections by research mode

These are alternatives to adapt, not mandatory section inventories:

| Paper direction | Possible core sections | What justifies them |
|-----------------|------------------------|--------------------|
| theory | Assumptions and formulation; theorem/derivation; proof and limiting cases; implications | The logical chain needed for the stated result |
| computation | Physical/mathematical model; computational method and settings; results; convergence/error assessment; interpretation | Recorded calculations and checks supporting the numerical claims |
| experiment | Research object and protocol; observations/results; uncertainty/controls; interpretation | Actual measurements and the validity of the inference |
| mixed | An integrated sequence of derivation, computation, and/or observation | Dependencies between the components of the argument |

Include introduction, relevant prior work, discussion/limitations, and conclusions in the form appropriate to the paper and venue. Related work may be a separate section or integrated into the introduction. Use neutral headings such as Theory, Computational Method, Results, or Discussion when they fit; do not add Experiments, training/inference, ML baselines, ablations, scaling studies, or a system architecture diagram without a claim-specific reason.

## Record each section

Repeat this starter for the sections actually selected. Replace placeholders with real existing claims, source locations, and planned content:

```markdown
## {section number}. {argument-specific title}

### Purpose and claims
- {role in the argument and existing target/contextual claims}

### Paragraph/subsection plan
- {logical progression for this section}

### Evidence and citations
- {existing wiki paper/claim links and precise evidence locations}
- {actual supplemental evidence-file links, when used}

### Figures/tables
- {needed items, or none with a brief reason}

### Open gaps
- {missing proof steps, numerical checks, observations, or citations; never assumed complete}

### Budget
- {estimated pages/words or relative allocation; verified limit or provisional estimate}
```

Results previews must use recorded findings; an unsupported headline stays a gap. An outline can reserve space for missing evidence, clearly marked as a draft dependency, without inventing the result.

## Verify venue rules and budget

- Preserve the user-supplied `--venue` name; accept any journal or conference. When omitted, record `unspecified` and proceed with a provisional, domain-appropriate outline. Do not choose a target on the user's behalf.
- For a specified venue, use user-supplied requirements or current official author instructions for the relevant article type/submission category. Record the source/link, date checked, and applicable version/year where relevant.
- Extract only confirmed constraints: page or word limit, counting of references/appendices, column/template requirements, figure/table limits, and anonymity policy where applicable. An absent statement is unknown, not an unlimited allowance.
- If rules cannot be verified, label them unverified and retain a provisional budget. Do not reuse a remembered venue table or require format lookup to block delivery of an otherwise useful draft outline.
- Allocate space to the actual argument. Check totals against verified limits in their specified units; never assume a universal page count or convert words to pages without a layout basis.
- If over budget, compress or move supporting detail only where the applicable rules allow it. Keep essential assumptions, argument, and evidence accessible; report unresolved format conflicts.

# Runtime Page Templates

> On-demand reference for full wiki page templates only. See `docs/runtime-support-files.en.md` for graph-derived files plus `index.md` and `log/`.

## 9 Page Types

### papers/{slug}.md

```yaml
---
title: ""
slug: ""
paper_type: paper       # paper | review | book | degree_thesis | preprint | report | chapter | dataset | other
venue: ""
year:
tags: []
research_modes: []      # theory | computation | experiment; choose all that apply
theory_tags: []         # named theories/frameworks/models used or evaluated
computation_tags: []    # simulation / numerical / statistical / ML / data-analysis schemes
experiment_tags: []     # observation / lab / field / sample-return / instrument / protocol tags
research_object_tags: [] # material/system/object under study
importance: 3           # 1-5
date_added: YYYY-MM-DD
source_type: tex         # tex | pdf
external_ids: {}
keywords: []
domain: ""               # NLP / CV / ML Systems / Robotics
code_url: ""
cited_by: []
---
```

Body sections: `## Evidence Pack` / `## Problem` / `## Key idea` / `## Research classification` / `## Method` / `## Results` / `## Limitations` / `## Open questions` / `## My take` / `## BibTeX` / `## Related`

`## Evidence Pack` is mandatory for generated paper pages. It must appear before interpretive sections and contain short source-grounding cards copied from the prepared MinerU markdown:

```markdown
## Evidence Pack

- `E1` <UseLabel> — <short label> ([prepared markdown](../sources/papers/<source-slug>.md), <source section>): ^E1
  > exact source fragment
```

This is the only valid Evidence Pack card header shape. Keep both markers: the readable evidence id stays at the start as `` `E1` ``, and the Obsidian block id goes at the very end of the same bullet header as `^E1`. Never start a card with `^E1`, and never replace `` `E1` `` with `^E1`. Subsequent prose cites the card with the literal Obsidian block-link string `[[#^E1]]`; the outer double brackets `[[...]]`, the leading `#`, and one literal space before the citation are mandatory. Write `... finding [[#^E1]]`, never `... finding[[#^E1]]`. Invalid citation forms include `[#^E1]`, `[[^E1]]`, `#^E1`, `^E1`, and `[!E1]`.

Every card must link to an existing `wiki/sources/papers/{source-slug}.md` prepared source and include an exact blockquote that occurs in that source. Subsequent `## Method`, `## Results`, `## Limitations`, and claim-generating statements may only use facts supported by these cards. If the source does not support a detail, write `unclear` or move it to `## Open questions`; do not fill gaps from model memory.

**Coverage floor.** The pack is not satisfied by a single card or by a fixed round number (a uniform three-card pack across substantive papers is a laziness smell). Provide at least one card per interpretive section you actually populate (`Problem`, `Method`, `Results`, `Limitations`), plus one card per generated concept page and per generated claim. The card count scales with the paper's substance; a section the source cannot support takes `unclear` instead of a card.

BibTeX must not be stored in YAML frontmatter. When Zotero/Crossref metadata provides a BibTeX entry, write it in the paper body under `## BibTeX` as a fenced code block:

````markdown
## BibTeX

```bibtex
@article{key,
  author = {...},
  title = {...},
  year = {...}
}
```
````

The BibTeX entry must be citation-core only: entry type, citekey, `author`, `title`, `year`, one venue field (`journal`/`booktitle`/`publisher`/`school`/`institution`/`howpublished`), `volume`, `number`, `pages`, and `doi`. Do not include URL, tags/keywords, abstract, language, rights, or other note-like fields in the BibTeX block.

`## Research classification` should first classify the paper into theory, computation, and/or experiment. For each active direction, name the specific theory, computational scheme, or experimental/observational process used. Always include the research object(s) being studied.

### concepts/{concept-name}.md

```yaml
---
title: ""
aliases: []
tags: []
maturity: active         # stable | active | emerging | deprecated
key_papers: []
first_introduced: ""
date_updated: YYYY-MM-DD
related_concepts: []
---
```

Body sections: `## Definition` / `## Source excerpts` / `## Intuition` / `## Formal notation` / `## Variants` / `## Comparison` / `## When to use` / `## Known limitations` / `## Open problems` / `## Key papers` / `## My understanding`

`## Source excerpts` is required for every concept page. Add one short original-language excerpt for each paper that materially grounds the concept, and link the excerpt back to the prepared MinerU markdown:

```markdown
- [[paper-slug]] ([prepared markdown](../sources/papers/paper-slug.md)):
  > short exact source fragment
```

Keep excerpts brief and use the source language exactly. If the relevant prepared markdown is unavailable, write `prepared markdown: missing` and explain the fallback source.

### topics/{topic-name}.md

```yaml
---
title: ""
tags: []
my_involvement: none     # none | reading | side-project | main-focus
sota_updated: YYYY-MM-DD
key_venues: []
related_topics: []
key_people: []
---
```

Body sections: `## Overview` / `## Timeline` / `## Seminal works` / `## SOTA tracker` / `## Open problems` / `## My position` / `## Research gaps` / `## Key people`

### people/{firstname-lastname}.md

```yaml
---
name: ""
affiliation: ""
tags: []
homepage: ""
scholar: ""
date_updated: YYYY-MM-DD
---
```

Body sections: `## Research areas` / `## Key papers` / `## Recent work` / `## Collaborators` / `## My notes`

### Summary/{area-name}.md

```yaml
---
title: ""
scope: ""
key_topics: []
paper_count:
date_updated: YYYY-MM-DD
---
```

Body sections: `## Overview` / `## Core areas` / `## Evolution` / `## Current frontiers` / `## Key references` / `## Related`

### foundations/{slug}.md

```yaml
---
title: ""
slug: ""
domain: ""
status: mainstream       # mainstream | historical
aliases: []
first_introduced: ""
date_updated: YYYY-MM-DD
source_url: ""
---
```

Body sections: `## Definition` / `## Intuition` / `## Formal notation` / `## Key variants` / `## Known limitations` / `## Open problems` / `## Relevance to active research`

Foundations have **no outward link fields**. Other pages may link to a foundation; foundations write no reverse link.

### ideas/{idea-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | in_progress | tested | validated | failed
origin: ""
origin_gaps: []
tags: []
domain: ""
priority: 3               # 1-5
pilot_result: ""
failure_reason: ""
linked_experiments: []
date_proposed: YYYY-MM-DD
date_resolved: ""
---
```

Body sections: `## Motivation` / `## Hypothesis` / `## Approach sketch` / `## Expected outcome` / `## Risks` / `## Pilot results` / `## Lessons learned`

### experiments/{experiment-slug}.md

```yaml
---
title: ""
slug: ""
status: planned           # planned | running | completed | abandoned
target_claim: ""
hypothesis: ""
tags: []
domain: ""
setup:
  model: ""
  dataset: ""
  hardware: ""
  framework: ""
metrics: []
baseline: ""
outcome: ""               # succeeded | failed | inconclusive
key_result: ""
linked_idea: ""
date_planned: YYYY-MM-DD
date_completed: ""
run_log: ""
started: ""
estimated_hours: 0
remote:
  server: ""
  gpu: ""
  session: ""
  started: ""
  completed: ""
---
```

Body sections: `## Objective` / `## Setup` / `## Procedure` / `## Results` / `## Analysis` / `## Claim updates` / `## Follow-up`

### claims/{claim-slug}.md

```yaml
---
title: ""
slug: ""
status: proposed          # proposed | weakly_supported | supported | challenged | deprecated
confidence: 0.5           # 0.0-1.0
tags: []
domain: ""
source_papers:
  - paper-slug            # slug only; no [[...]], no #^anchor
evidence:
  - source: paper-slug    # slug only; no [[...]], no #^anchor
    source_anchor: E1     # Evidence Pack id only: E1, E2, ...
    type: supports        # supports | contradicts | tested_by | invalidates
    strength: moderate    # weak | moderate | strong
    source_section: ""    # source section / figure / table label when useful
    detail: ""
conditions: ""
date_proposed: YYYY-MM-DD
date_updated: YYYY-MM-DD
---
```

Body sections: `## Statement` / `## Evidence summary` / `## Conditions and scope` / `## Counter-evidence` / `## Linked ideas` / `## Open questions`

Claim YAML provenance is data, not Obsidian display syntax. `source_papers` and `evidence[].source` must contain paper slugs only. `evidence[].source_anchor` must contain the Evidence Pack id only (`E1`, not `^E1`, `[[#^E1]]`, or `[[paper#^E1]]`). Put rendered links, if needed, in body prose only.

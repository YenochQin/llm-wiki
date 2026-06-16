# Source Grounding Discipline

> Shared anti-hallucination reference for every skill that **generates** durable
> content (wiki pages, LaTeX drafts, experiment designs, reports).
> Referenced by: `/ingest`, `/reingest`, `/source-audit`, `/exp-design`,
> `/ideate`, `/prefill`, `/survey`, `/paper-plan`, `/paper-draft`, `/refine`,
> `/ask`, `/rebuttal`, `/novelty`.
>
> `/ingest` is the canonical implementation of this discipline (its **Evidence
> Pack** + `grounding_lint.py` gate). This file generalizes that pattern so
> other generative skills do not each reinvent — or silently weaken — it.

---

## Core Rule

**Every substantive statement in generated content must trace to a retrievable
source, never to model memory.**

Acceptable sources, in priority order:

1. **Prepared MinerU markdown** of the paper (`wiki/sources/papers/<slug>.md`) — exact text.
2. **Existing wiki pages** that are themselves source-grounded (`papers/`, `concepts/`, `claims/`, `foundations/`).
3. **Fetched literature / web search results** captured during this run (Crossref, Wikipedia, WebSearch) — cite the query and result.
4. **The user's own input** in this session (an explicit hypothesis, a pasted result).

Model memory ("I recall this paper reports 92%") is **not** an acceptable source.

---

## Evidence-First Protocol

Before drafting any interpretive prose, build a short evidence set, then draft
**only** from it. This is the generalized form of `/ingest`'s Evidence Pack.

1. Extract short evidence cards from the canonical source. Each card carries:
   - an id (`E1`, `E2`, …)
   - a link to the source (prepared markdown link, wiki `[[slug]]`, or fetched URL)
   - the section/table/figure/equation label when available
   - **one short exact quote** in the original language — not a paraphrase
2. Draft methods, results, definitions, claim evidence, and comparisons **only**
   from these cards.
3. If no card supports a detail, you have three honest options — pick one, never
   invent: write `unclear`, omit the detail, or move it under an
   `## Open questions` / "needs verification" heading.
4. Do not replace exact quotes with an LLM summary "for brevity." The quote is
   the anti-hallucination anchor.

If the source is too poor to extract evidence cards, **stop and report a
source-quality blocker** instead of generating from memory.

---

## High-Risk Statements (require direct card support)

Treat these as hard-blocked unless an evidence card backs them verbatim:

- numbers, units, signs, error bars, sample sizes, seeds
- dataset / benchmark / model / venue names
- comparisons and rankings ("outperforms", "2× faster", "SOTA")
- causal or mechanistic claims ("because", "causes", "is driven by")
- superlatives and exclusivity ("first", "best", "only", "necessary and sufficient")
- broad generalizations beyond the studied scope

When unsure, downgrade the wording (qualitative instead of quantitative) or mark
`unclear`. Underclaim rather than overclaim.

---

## Provenance Marking

Generated pages must let a future reader tell source-derived content from
synthesis:

- Tag LLM-synthesized sections that have no source backing, e.g. `(LLM analysis)`.
- Keep `## Source excerpts` / `## Evidence Pack` excerpts exact and linked.
- A claim's `evidence` entry must name a `source_anchor` (Evidence Pack id or
  prepared-source location).
- If the prepared markdown is missing, record `prepared markdown: missing` plus
  the fallback source used — do not link a live path to an empty file.

---

## Citations Must Exist and Be Verifiable

- Every `[[slug]]` wikilink must resolve to a page that already exists (or is
  created in the same run). Never emit placeholder `[[paper-slug]]` links for
  papers not in the wiki — write them as plain text marked `not yet ingested`.
- BibTeX and external citations follow `citation-verification.md`: fetched from
  authoritative sources, never generated from memory; unverifiable entries carry
  the `[UNCONFIRMED]` marker until checked.

---

## Closing Gate (run before finalizing)

### Wiki pages (`papers/` · `concepts/` · `claims/`)

Run the mechanical source-grounding gate on every touched page and fix every red
issue before reporting — do not downgrade it to a warning:

```shell
uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' \
  --only "papers/<slug>.md" --only "concepts/<slug>.md" --only "claims/<slug>.md" --json
```

`grounding_lint.py` only covers `papers/`, `concepts/`, and `claims/`; it does
not check `experiments/`, `ideas/`, `foundations/`, `outputs/`, or LaTeX.

### Other generated content (experiments · ideas · foundations · reports · LaTeX)

`grounding_lint.py` does not see these, so run a manual grounding self-check:

1. Every high-risk statement has an evidence card or an explicit `unclear` / `(LLM analysis)` marker.
2. Every cited wiki page and external reference actually exists.
3. No number, dataset name, or comparison was introduced without a source.
4. Synthesis is marked as synthesis, not presented as a source finding.

---

## What NOT To Do

- **Never** fill a gap with model memory — write `unclear` instead.
- **Never** invent a paper, dataset, metric value, DOI, or external id.
- **Never** paraphrase a number or comparison into the text without a backing quote.
- **Never** present LLM synthesis as a source-reported finding.
- **Never** silently drop an `unclear` / `[UNCONFIRMED]` / `(LLM analysis)` marker to make output look more complete.
- **Never** emit a wikilink to a page that does not exist.

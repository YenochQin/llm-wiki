# Phase B — Evidence Pack

> Shared ingest phase. The card shape and citation syntax are defined **only** in `docs/runtime-page-templates.en.md` §papers — emit per that template, never restate the ASCII here. Obeys `.claude/skills/shared-references/ingest-invariants.md`.

## Purpose

Build the source Evidence Pack from the prepared MinerU markdown **before** any interpretive prose. This is a hard anti-hallucination gate, not optional context: every downstream interpretive statement must trace to a card. See the shared discipline in `.claude/skills/shared-references/source-grounding.md`.

## Steps

1. **Extract short evidence cards** from the canonical prepared source (`wiki/sources/papers/<source-slug>.md` or the INIT MODE handoff path). Each card carries: an id (`E1`, `E2`, …), the prepared-source markdown link, the source section/table/figure/equation/heading label when available, one short **exact original-language** blockquote, and an intended use (`Problem` / `Research classification` / `Method` / `Results` / `Limitations` / `Concept` / `Claim`).
2. **Cards are exact-source first.** Do not replace a card with an LLM summary of the source.
3. **Draft only from cards.** Paper `## Method` / `## Results` / `## Limitations`, concept definitions, and claim evidence may use only facts a card supports. If no card supports a detail, write `unclear`, omit it, or move it to `## Open questions` — never fill the gap from model memory.
4. **High-risk statements require direct card support**: numbers, units, signs, sample sizes, dataset/benchmark names, comparisons, causality, mechanism, and "first/best/SOTA/necessary/sufficient" wording.
5. **Copy formal material as complete units.** If a card quotes a displayed equation, inline equation that defines a symbol, theorem, definition, algorithm step, table result, or derivation line used as evidence, the quoted fragment must include the complete source unit needed to preserve meaning. For display math, copy from the opening delimiter through the closing delimiter, including every line of `aligned` / `split` / `cases` / multi-line equations. Do not quote only the first line, first term, or visually convenient prefix of a long formula. If the complete formula is too long for a card, quote the surrounding source sentence plus equation label/section, write that the full equation remains in the prepared source, and do not use the shortened card as support for a formal notation, concept definition, or claim that depends on the omitted terms.
6. **Preserve quote syntax without injecting it into math.** The leading `>` on evidence lines is Markdown blockquote syntax required by the page template; it is not part of the quoted LaTeX. For display math, `$$...$$` is one indivisible LaTeX block: only the opening `$$` line may carry the Evidence Pack quote marker. Do **not** prefix formula continuation lines or the closing `$$` line with `>` after the list indentation. If an equation stays inline within an already quoted sentence, do not add an extra `>` immediately before the formula. Before passing Gate B, scan every Evidence Pack display-math block and remove any `>` marker between the opening `$$` and closing `$$`.
7. **Meet the coverage floor** (defined in template §papers): one card per interpretive section you actually populate (`Problem`, `Method`, `Results`, `Limitations`), plus one `Concept` card per concept page this ingest creates or materially edits, plus one `Claim` card per claim it generates. The count scales with the paper's substance — a uniform three-card pack on a substantive paper is a laziness smell, not a target.
8. **Place the pack as the first body section** of the paper page, per the template card shape.

If the prepared source is too poor to extract cards, stop and report a source-quality blocker instead of generating from memory.

## Gate B — output this block before Phase C; if any line is ✗, stop and fix

```text
[Gate B] evidence pack
- cards extracted: <n>
- populated interpretive sections: <list>  → each has ≥1 card: ✓/✗
- concepts this ingest will touch: <n> → each has a Concept card: ✓/✗
- claims this ingest will generate: <n> → each has a Claim card: ✓/✗
- every card links to an existing prepared source file (size > 0B): ✓/✗
- every blockquote is an exact original-language fragment (not paraphrase): ✓/✗
- equations/formal statements copied as complete meaning-preserving units, not partial spans: ✓/✗
- display-math Evidence Pack blocks have no `>` markers on formula continuation or closing `$$` lines: ✓/✗
- coverage scales with substance (not a fixed round number): ✓/✗
```

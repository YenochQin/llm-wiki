# Phase B — Evidence Pack

> Shared ingest phase. The card shape and citation syntax are defined **only** in `docs/runtime-page-templates.en.md` §papers — emit per that template, never restate the ASCII here. Obeys `.claude/skills/shared-references/ingest-invariants.md`.

## Purpose

Build the source Evidence Pack from the prepared MinerU markdown **before** any interpretive prose. This is a hard anti-hallucination gate, not optional context: every downstream interpretive statement must trace to a card. See the shared discipline in `.claude/skills/shared-references/source-grounding.md`.

## Steps

1. **Extract short evidence cards** from the canonical prepared source (`wiki/sources/papers/<source-slug>.md` or the INIT MODE handoff path). Each card carries: an id (`E1`, `E2`, …), the prepared-source markdown link, the source section/table/figure/equation/heading label when available, one short **exact original-language** blockquote, and an intended use (`Problem` / `Research classification` / `Method` / `Results` / `Limitations` / `Concept` / `Claim`).
2. **Cards are exact-source first.** Do not replace a card with an LLM summary of the source.
3. **Draft only from cards.** Paper `## Method` / `## Results` / `## Limitations`, concept definitions, and claim evidence may use only facts a card supports. If no card supports a detail, write `unclear`, omit it, or move it to `## Open questions` — never fill the gap from model memory.
4. **High-risk statements require direct card support**: numbers, units, signs, sample sizes, dataset/benchmark names, comparisons, causality, mechanism, and "first/best/SOTA/necessary/sufficient" wording.
5. **Meet the coverage floor** (defined in template §papers): one card per interpretive section you actually populate (`Problem`, `Method`, `Results`, `Limitations`), plus one `Concept` card per concept page this ingest creates or materially edits, plus one `Claim` card per claim it generates. The count scales with the paper's substance — a uniform three-card pack on a substantive paper is a laziness smell, not a target.
6. **Place the pack as the first body section** of the paper page, per the template card shape.

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
- coverage scales with substance (not a fixed round number): ✓/✗
```

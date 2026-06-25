# Phase B — Evidence Pack

> Shared ingest phase. The card shape and citation syntax are defined **only** in `docs/runtime-page-templates.en.md` §papers. Do not hand-write Evidence Pack Markdown during ingest; render it with `tools/evidence_pack.py` from structured card parameters. Obeys `.claude/skills/shared-references/ingest-invariants.md`.

## Purpose

Build the source Evidence Pack from the prepared MinerU markdown **before** any interpretive prose. This is a hard anti-hallucination gate, not optional context: every downstream interpretive statement must trace to a card. See the shared discipline in `.claude/skills/shared-references/source-grounding.md`.

## Steps

1. **Extract short evidence card parameters** from the canonical prepared source (`wiki/sources/papers/<source-slug>.md` or the INIT MODE handoff path). Each card parameter object carries: `id` (`E1`, `E2`, …), `use_label` (`Problem` / `Research classification` / `Method` / `Results` / `Limitations` / `Concept` / `Claim`), `short_label`, `source_slug`, `source_section`, and `excerpt`.
   - `short_label` is the refined title of the source block: summarize the source's contribution in a few precise words, such as the mechanism, dataset/result, definition, limitation, or formal object.
   - `excerpt` is a locator anchor, not a copied source block. Use the shortest exact original-language sentence, phrase, table row, or formula that lets a reader find and verify the evidence in the prepared source.
2. **Cards are source-anchor first.** Do not replace the `excerpt` with an LLM summary, and do not paste whole paragraphs or subsections as a substitute for choosing a precise anchor. The condensation belongs in `short_label` and downstream prose; the blockquote stays exact and compact.
3. **Draft only from cards.** Paper `## Method` / `## Results` / `## Limitations`, concept definitions, and claim evidence may use only facts a card supports. If no card supports a detail, write `unclear`, omit it, or move it to `## Open questions` — never fill the gap from model memory.
4. **High-risk statements require direct card support**: numbers, units, signs, sample sizes, dataset/benchmark names, comparisons, causality, mechanism, and "first/best/SOTA/necessary/sufficient" wording.
5. **Copy formal material as complete units when the formula itself is the anchor.** If a card quotes a displayed equation, inline equation that defines a symbol, theorem, definition, algorithm step, table result, or derivation line used as evidence, the quoted fragment must include the complete source unit needed to preserve meaning. For display math, copy from the opening delimiter through the closing delimiter, including every line of `aligned` / `split` / `cases` / multi-line equations. Do not quote only the first line, first term, or visually convenient prefix of a long formula. If the complete formula is too long for a compact card, use the surrounding source sentence plus equation/table/algorithm label or section as the anchor, write that the full formal unit remains in the prepared source, and do not use the shortened card as support for a formal notation, concept definition, or claim that depends on omitted terms.
6. **Render with the deterministic helper.** Write the card parameters to a temporary JSON file:

   ```json
   {
     "cards": [
       {
         "id": "E1",
         "use_label": "Method",
         "short_label": "rate expression",
         "source_slug": "paper-slug",
         "source_section": "Eq. 2",
         "excerpt": "$$\nA = x\n+ y\n$$"
       }
     ]
   }
   ```

   Then run:

   ```shell
   uv run python -X utf8 tools/evidence_pack.py --input <cards.json>
   ```

   Paste the generated Markdown into the paper page as the first body section. Do not manually add `>` markers, `^E1` anchors, prepared markdown links, or the `## Evidence Pack` heading; the helper owns that formatting.
7. **Meet the coverage floor** (defined in template §papers): one card per interpretive section you actually populate (`Problem`, `Method`, `Results`, `Limitations`), plus one `Concept` card per concept page this ingest creates or materially edits, plus one `Claim` card per claim it generates. The count scales with the paper's substance — a uniform three-card pack on a substantive paper is a laziness smell, not a target.
8. **Place the pack as the first body section** of the paper page using the helper output.

If the prepared source is too poor to extract cards, stop and report a source-quality blocker instead of generating from memory.

## Gate B — output this block before Phase C; if any line is ✗, stop and fix

```text
[Gate B] evidence pack
- cards extracted: <n>
- populated interpretive sections: <list>  → each has ≥1 card: ✓/✗
- concepts this ingest will touch: <n> → each has a Concept card: ✓/✗
- claims this ingest will generate: <n> → each has a Claim card: ✓/✗
- every card links to an existing prepared source file (size > 0B): ✓/✗
- every `short_label` is a refined source-block title rather than a copied heading: ✓/✗
- every blockquote is an exact original-language fragment (not paraphrase): ✓/✗
- every excerpt is a compact locator anchor, not a whole paragraph/subsection paste: ✓/✗
- equations/formal statements copied as complete meaning-preserving units when used as anchors, not partial spans: ✓/✗
- Evidence Pack Markdown generated by `tools/evidence_pack.py` from structured parameters, not hand-written: ✓/✗
- display-math Evidence Pack blocks have no `>` markers on formula continuation or closing `$$` lines: ✓/✗
- coverage scales with substance (not a fixed round number): ✓/✗
```

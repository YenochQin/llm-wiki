# Source-to-Wiki Evidence Alignment

Read this reference during source-to-wiki comparison for every selected or explicitly linked target. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

For each target page:

1. Read the wiki page.
2. Read the canonical source markdown or the linked prepared source excerpts.
3. Extract audit-relevant source anchors before judging the wiki. Use exact source passages, headings, tables, figure captions, or line-like locations when available. Do not replace this with a model-generated summary of the source.
4. Prioritize these source anchors:
   - title, authors, venue/year, DOI, BibTeX fields.
   - research classification: `paper_type`, `research_modes`, theory/computation/experiment tags, research objects.
   - methods, datasets/samples, instruments, experimental setup, equations/models.
   - numerical claims: values, ranges, signs, units, percentages, uncertainties, sample sizes.
   - results/conclusions, limitations, scope conditions, negative findings.
   - claims of novelty, first/best/SOTA, causality, generality, or mechanism.
   - concept definitions and quoted `## Source excerpts`.
5. For each source anchor, find the corresponding wiki field, sentence, paragraph, table row, or section:
   - If the wiki says something materially different, record a mismatch.
   - If the wiki omits a source-backed fact needed for faithful interpretation, record `OMISSION`.
   - If the wiki adds a material statement, search the source for its key terms, numbers, entities, and synonyms. If no corresponding source passage is found, record `UNSUPPORTED` and state the targeted searches performed.
6. Run an explicit hallucination pass over high-risk wiki statements: numbers, units, signs, sample sizes, dataset names, benchmark names, algorithm names, causality/mechanism wording, "first", "best", "SOTA", necessary/sufficient claims, and broad generalizations. For each high-risk statement, search the prepared source for distinctive terms and plausible synonyms. If the source has no corresponding passage, record `UNSUPPORTED` and label the mismatch type as `fabricated or unsupported addition`.
7. Every finding must be anchored in one or more exact source excerpts. Keep quotes short, but include enough original wording to let the user see the mismatch directly.
8. Use a source-level summary only as navigation. Do not report a finding from a summary alone unless the source OCR is too poor; label that as `SOURCE_QUALITY_BLOCKER`.

When `--include-linked` added a concept or claim page, audit it as a first-class target:

- Concepts: verify definitions, `## Source excerpts`, and claims made in concept prose against all linked prepared sources, especially the originating paper(s) from the current batch.
- Claims: verify `## Statement`, evidence summary, conditions/scope, confidence/status rationale, and YAML evidence against the cited `source_papers` and `evidence[].source` papers. If the claim cites multiple papers, do not treat one paper as supporting the whole claim unless the claim's scope says so.
- Report linked-page findings under their own page headings, and label the page as `linked from [[paper-slug]]` in the report.

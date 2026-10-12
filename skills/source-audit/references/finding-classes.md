# Source Audit Finding Classes

Read this reference when classifying observed source/wiki discrepancies and source blockers. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Use these issue classes:

- `MISREADING`: wiki states the opposite or a materially different meaning from the source.
- `UNSUPPORTED`: wiki adds a claim not grounded in the source. Use this for likely LLM hallucinations/fabrications when targeted source searches find no support.
- `OVERGENERALIZATION`: source claim is narrower than wiki wording.
- `OMISSION`: source contains a key result, limitation, method detail, scope condition, caveat, or negative finding that the wiki does not represent, and the absence makes the wiki interpretation incomplete or misleading.
- `NUMBER_UNIT_ERROR`: wrong number, range, sign, unit, uncertainty, date, sample count, isotope/mass, or percentage.
- `SOURCE_EXCERPT_MISMATCH`: quoted source excerpt is missing, paraphrased as if quoted, linked to the wrong source, or does not support the surrounding definition.
- `SOURCE_MISSING`: no prepared source can be identified and found after provenance resolution; list the attempted paths. A paper/source filename difference is not an issue.
- `CLASSIFICATION_ERROR`: `paper_type`, `research_modes`, tags, or research object classification contradicts the source.
- `BIBTEX_ERROR`: BibTeX/title/venue/year/DOI metadata is wrong or contains non-core fields.
- `SOURCE_QUALITY_BLOCKER`: OCR/MinerU conversion is too poor to verify; distinguish this from a wiki error.

Severity:

- `Critical`: reverses or corrupts a central claim/result, wrong core number/unit/sign, fabricated finding, or source contradiction.
- `Major`: unsupported or overbroad interpretation that changes scope, missing central limitation, wrong classification affecting downstream retrieval.
- `Minor`: metadata/title/BibTeX cleanup, wording precision, small omission that does not alter the main interpretation.

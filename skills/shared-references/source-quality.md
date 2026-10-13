# Prepared-source quality gate

Run this gate before extracting evidence from canonical prepared Markdown,
including direct handoffs, cached sources, light ingest and reingest. A
preparation manifest's `usable: true` confirms preparation, not scientific
readability or fidelity to the PDF.

## Scan the selected sources

Resolve the required external roots as usual, then run the read-only scanner
on **every actual canonical source path** used by this ingest:

```shell
uv run python -X utf8 tools/source_quality_lint.py '<absolute-canonical-source.md>' --json
```

Pass multiple paths when the paper has multiple prepared sources. Do not infer
source filenames from paper slugs. Use the current source contents even when
preparation reused a cache. Repeat the scan if a source changes after inspection.

The tool prints findings and SHA-256 fingerprints; it does not edit sources,
save reports, call a model, open PDFs, or write logs. Exit 2 is an incomplete
scan and must be resolved before extracting evidence. Exit 1 means red findings
need disposition; exit 0 can still contain warnings or informational findings.

## Review before extracting cards

Read the flagged fragments with their surrounding paragraphs, equations or
table headers. Record the disposition in the run's report, with source path,
line/rule, and one of: `excluded`, `verified-with-anchor`, `benign-with-reason`,
or `unresolved`. Keep exact source text unchanged.

- **Red, document scope**: unreadable/invalid/empty source. Stop this paper's
  ingest with `SOURCE_QUALITY_BLOCKER`.
- **Red, fragment scope**: possible missing characters or symbols. Withhold
  the affected content from evidence until verified. A localized problem does
  not invalidate unrelated readable content. A reference proving the same fact
  elsewhere must itself be an unambiguous source anchor; plausible restoration
  from domain knowledge is not verification.
- **Warn**: inspect the reported boundary, equation, table, duplicate paragraph,
  suspicious word, missing image or extraction-coverage anomaly. Exclude or mark
  unresolved evidence if the concern cannot be settled from accessible sources.
- **Info**: label variants or an absent explicit abstract are not by themselves
  evidence of OCR failure. Confirm boundaries/document type and proceed when
  the source supports the planned content.

The current agent then reviews each prospective evidence unit for readable
variables, signs, units, complete formal statements and table row/column
alignment, and checks relevant prose/table consistency and missing context.
This is agent review, not an automated scientific validation or a separate
reviewer/model service. The Python scanner has no model API dependency.

If fidelity remains uncertain, retain a blocker for that evidence; compare
against the original PDF/page image when source access and the task authorize
it. Report what was actually checked. Neither an exact quote match nor an empty
scanner report establishes PDF fidelity. Proceed to evidence extraction only
when the intended scope has enough unambiguous source evidence. If exclusions
prevent the required Evidence Pack coverage, stop the paper and report the gap.

## Existing-source batch screening

Outside a single ingest, scan the directory; optionally index direct source
links from existing paper/concept/claim pages:

```shell
uv run python -X utf8 tools/source_quality_lint.py '@configured-sources-papers' --wiki-dir '@configured' --json
```

Without `--json`, stdout is a Markdown report sorted by red/warning counts.
Every match has its original file position, an exact nearby excerpt, rule and
scope. Direct referencing pages are impact candidates, not confirmed propagated
errors; the scanner does not expand indirect claim dependencies. Authorize and
scope any subsequent wiki audit separately.

Rules cover visible missing characters, selected malformed math and table
structures, repeated prose, abstract labels, missing image assets and metadata
indicators of omitted/low-text content. The low-text heuristic uses fewer than
200 non-whitespace body characters per recorded page for sources of at least
three pages; image-heavy documents can legitimately match. Word capitalization
and table checks are heuristics, not OCR diagnoses. Rowspan HTML tables require
manual inspection. Plausible wrong digits/signs, dropped passages, reading order
and scientific contradictions can escape all rules.

Save output only when the user requests a report archive. After an authorized
archive, append its log through `tools/research_wiki.py log`; default stdout
screening writes neither reports nor logs. Keep automated screening findings
distinct from any later agent/PDF review.

---
name: source-audit
description: Use when verifying that wiki pages faithfully represent their original sources — surfacing misreadings, unsupported claims, omissions, wrong numbers, units or signs, overgeneralizations, source-excerpt mismatches, and classification errors against the prepared source markdown.
argument-hint: "[slug|path|--all] [--type papers|concepts|claims|all] [--include-linked] [--batch-size N] [--start-after slug] [--fix] [--dry-run] [--write-report] [--adversarial]"
---

# /source-audit

> Audit whether wiki pages are faithful to their canonical source documents. This is a source-grounded content audit, not a general wiki lint. It lists exact source-to-wiki mismatches: what the source says, what the wiki says or omits, why they do not correspond, and the required correction.

## Inputs

- Target selector:
  - `slug` or `path`: audit one wiki page.
  - `--all`: audit all matching pages in batches.
  - default when no target is specified: `--type papers --batch-size 5`, sorted by filename.
- `--type`:
  - `papers`: compare `wiki/papers/{slug}.md` with `wiki/sources/papers/{slug}.md`.
  - `concepts`: compare concept definitions/excerpts against linked prepared sources.
  - `claims`: compare claim text/evidence against cited source papers.
  - `all`: audit papers, then concepts, then claims.
- `--include-linked`: when the selected batch includes paper pages, also audit directly linked concept and claim pages supported by those papers. This is opt-in; default paper audits remain paper-only.
- `--batch-size N`: number of pages per batch; default `5`.
- `--start-after slug`: for batch continuation; skip sorted targets through this slug.
- `--fix`: apply conservative wiki corrections after reporting findings.
- `--dry-run`: show proposed edits without writing files; meaningful with `--fix`.
- `--write-report`: write `wiki/outputs/source-audit-{date}.md`.
- `--adversarial`: use stricter reading; actively look for plausible but unsupported wiki wording.

## Outputs

- Source-grounded audit report in the conversation.
- Optional report file: `wiki/outputs/source-audit-{date}.md`.
- Optional wiki edits only when the user explicitly passes `--fix`.
- Optional log entry in `wiki/log/` after a completed batch.

## Wiki Interaction

### Reads

- `wiki/papers/*.md` - paper summaries, classification, results, limitations, BibTeX.
- `wiki/sources/papers/*.md` - MinerU prepared markdown, the canonical source for paper audits.
- `wiki/concepts/*.md` - definitions, `## Source excerpts`, `key_papers`.
- `wiki/claims/*.md` - claim text, confidence, evidence, source papers.
- `wiki/index.md` - locate pages when needed.
- `config/paths.json` or runtime aliases - resolve the configured wiki root.

### Writes

- Default: no writes.
- With `--fix`: edit only wiki interpretation pages (`papers/`, `concepts/`, `claims/`) and only for issues that are directly supported by the source.
- With `--write-report`: write `wiki/outputs/source-audit-{date}.md`.
- Append `wiki/log/` via `tools/research_wiki.py log` after a completed audit batch.

### Never writes

- Do not modify `raw/`.
- Do not manually modify `wiki/graph/`.
- Do not alter prepared source markdown under `wiki/sources/` unless the user explicitly asks to repair source conversion artifacts.

## Workflow

**Precondition**: run from the llm-wiki repository root. Resolve the configured wiki root; do not hard-code repository-local `wiki/` if `config/paths.json` points elsewhere.

```shell
uv run python -X utf8 tools/resolve_path_alias.py '@configured'
```

Use the resolved absolute path for direct file reads/edits. If `uv` is unavailable but `.venv` exists, use the project Python described in `AGENTS.md`.

### Step 1: Build the audit batch

1. Resolve the target selector:
   - explicit file path: audit that file.
   - explicit slug: find it under the selected type directories.
   - `--all` or no target: list sorted pages for the selected type.
2. Apply `--start-after slug` and `--batch-size N`.
3. If `--include-linked` is set and the selected batch contains paper pages, expand the audit target set with directly linked concepts and claims:
   - concepts linked from the paper page's `## Related` or whose `key_papers` contains the paper slug.
   - claims linked from the paper page's `## Related`, or whose `source_papers` / `evidence[].source` contains the paper slug.
   - Do not include people, topics, Summary pages, foundations, graph files, or cited-but-not-ingested papers.
   - Deduplicate pages. `--batch-size` applies only to the primary selected pages; linked pages are additional and must be reported as `linked`.
4. For paper pages, require a matching prepared source at `wiki/sources/papers/{slug}.md`.
5. If a prepared source is missing, report it as `SOURCE_MISSING`; do not infer from memory.

Default batch behavior:

```text
type=papers
batch-size=5
order=sorted filename ascending
mode=report-only
```

### Step 2: Build source-to-wiki alignment evidence

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
6. Every finding must be anchored in one or more exact source excerpts. Keep quotes short, but include enough original wording to let the user see the mismatch directly.
7. Use a source-level summary only as navigation. Do not report a finding from a summary alone unless the source OCR is too poor; label that as `SOURCE_QUALITY_BLOCKER`.

When `--include-linked` added a concept or claim page, audit it as a first-class target:

- Concepts: verify definitions, `## Source excerpts`, and claims made in concept prose against all linked prepared sources, especially the originating paper(s) from the current batch.
- Claims: verify `## Statement`, evidence summary, conditions/scope, confidence/status rationale, and YAML evidence against the cited `source_papers` and `evidence[].source` papers. If the claim cites multiple papers, do not treat one paper as supporting the whole claim unless the claim's scope says so.
- Report linked-page findings under their own page headings, and label the page as `linked from [[paper-slug]]` in the report.

### Step 3: Classify findings

Use these issue classes:

- `MISREADING`: wiki states the opposite or a materially different meaning from the source.
- `UNSUPPORTED`: wiki adds a claim not grounded in the source.
- `OVERGENERALIZATION`: source claim is narrower than wiki wording.
- `OMISSION`: source contains a key result, limitation, method detail, scope condition, caveat, or negative finding that the wiki does not represent, and the absence makes the wiki interpretation incomplete or misleading.
- `NUMBER_UNIT_ERROR`: wrong number, range, sign, unit, uncertainty, date, sample count, isotope/mass, or percentage.
- `SOURCE_EXCERPT_MISMATCH`: quoted source excerpt is missing, paraphrased as if quoted, linked to the wrong source, or does not support the surrounding definition.
- `CLASSIFICATION_ERROR`: `paper_type`, `research_modes`, tags, or research object classification contradicts the source.
- `BIBTEX_ERROR`: BibTeX/title/venue/year/DOI metadata is wrong or contains non-core fields.
- `SOURCE_QUALITY_BLOCKER`: OCR/MinerU conversion is too poor to verify; distinguish this from a wiki error.

Severity:

- `Critical`: reverses or corrupts a central claim/result, wrong core number/unit/sign, fabricated finding, or source contradiction.
- `Major`: unsupported or overbroad interpretation that changes scope, missing central limitation, wrong classification affecting downstream retrieval.
- `Minor`: metadata/title/BibTeX cleanup, wording precision, small omission that does not alter the main interpretation.

### Step 4: Produce the report

Use this structure for every batch:

```markdown
# Source-Grounded Audit - YYYY-MM-DD

## Batch
- **Type**: papers
- **Range**: {first slug} ... {last slug}
- **Linked expansion**: off | on, linked pages: N
- **Mode**: report-only | fix | dry-run
- **Source root**: `{configured wiki root}/sources`

## Summary
- Critical: N
- Major: N
- Minor: N
- Source blockers: N
- Pages checked: N

## Findings

### [[slug]]

1. **[Major][CLASSIFICATION_ERROR] Short title**
   - **Source location**: `{source file}` heading/table/figure/line if available.
   - **Source text**: short exact quote from the prepared source.
   - **Wiki location**: `wiki/papers/{slug}.md` field/section/paragraph/table row, or `missing`.
   - **Wiki text / missing coverage**: exact wiki text, or the source-backed point absent from the wiki.
   - **Mismatch type**: contradiction | unsupported addition | omitted source fact | overgeneralization | wrong number/unit | excerpt mismatch | classification mismatch | metadata mismatch.
   - **Why this is a problem**: explain the non-correspondence between the quoted source and the wiki.
   - **Required correction**: precise replacement, deletion, or addition.

## Proposed Edits
- `wiki/papers/{slug}.md`: exact field/section edits, or `none`.
- Linked pages: exact `concepts/{slug}.md` / `claims/{slug}.md` edits, or `none`.

## Next Batch
- Continue with: `/source-audit --type papers --batch-size 5 --start-after {last slug}`
```

If no issues are found for a page, include:

```markdown
### [[slug]]
- No source-grounding issues found after source-to-wiki alignment in the audited scope.
```

### Step 5: Apply fixes only when requested

Without `--fix`, stop after the report.

With `--fix`:

1. Apply only conservative edits with direct source support.
2. Prefer tightening wording over adding broad new claims.
3. Preserve YAML style, section order, wikilinks, and existing backlinks.
4. Do not invent missing metadata. Use `unclear` when the source does not support a field.
5. If editing creates or removes wikilinks, maintain required bidirectional links.
6. If `--dry-run` is present, show the proposed patch summary but do not write.

After edits, re-read changed files and confirm the correction is present.

### Step 6: Log completion

Append a concise log line after a completed batch:

```shell
uv run python -X utf8 tools/research_wiki.py log '@configured' "source-audit | type=papers batch={first}..{last} findings={critical}/{major}/{minor} mode=report-only"
```

Skip logging only if the user asks for a no-write audit.

## Constraints

- **Source-first**: every finding must cite the source file and a specific fragment, heading, table, figure caption, or clearly identified location when available.
- **Mismatch-first output**: list concrete source-to-wiki non-correspondences. Do not substitute a paper/source summary for the mismatch list.
- **Exact excerpts required**: every error or omission finding must include one or more short exact source excerpts. For omissions, quote the source passage and name where the wiki should cover it.
- **Unsupported requires search evidence**: when marking a wiki statement as unsupported, quote the nearest relevant source passage or state `no corresponding source passage found` after targeted searches for the claim's key terms, numbers, entities, and synonyms.
- **No summary-only findings**: do not report a finding from a source-level summary alone. Source summaries may guide navigation but cannot replace exact source evidence.
- **No memory-only judgments**: if the source does not contain enough evidence, report uncertainty instead of relying on model knowledge.
- **Prepared markdown is canonical**: for paper audits, use `wiki/sources/papers/*.md`; raw PDFs are fallback only when the user explicitly asks.
- **Read-only by default**: no wiki edits unless `--fix` is explicit.
- **Linked expansion is explicit**: do not audit linked concepts/claims during a paper audit unless `--include-linked` is set. When it is set, linked concepts/claims are full audit targets, not casual context reads.
- **Batch strictly**: when the user asks for batches of 5, audit exactly 5 available targets unless fewer remain.
- **Separate source error from wiki error**: OCR loss, broken tables, missing figures, or incomplete MinerU conversion are `SOURCE_QUALITY_BLOCKER`.
- **Keep quotes short**: use brief exact fragments only where needed to ground the finding.
- **Formula formatting**: any LaTeX written into reports or wiki pages must use `$...$` inline and `$$...$$` for display math.

## Error Handling

- **Configured wiki root missing**: report the resolved path and suggest running `/setup`.
- **No matching pages**: report selector/type and show likely available slugs.
- **Source missing**: emit `SOURCE_MISSING`, skip source-grounding judgments for that page.
- **Source too long**: read title/abstract/introduction/conclusion plus relevant sections first; search within the source for numbers, methods, terms, and claimed results from the wiki page.
- **Ambiguous evidence**: classify as uncertainty; do not mark as an error unless source support is clearly absent or contradictory.
- **Fix conflict with user edits**: stop and report the affected file rather than overwriting uncertain changes.

## Relationship to other skills

- Use `/check` for structural health, broken links, required fields, and graph consistency.
- Use `/review` for independent quality review of a research artifact.
- Use `/source-audit` when the core question is whether wiki interpretation faithfully reflects original source documents.

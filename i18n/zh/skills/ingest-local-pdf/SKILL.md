---
description: Ingest local PDF files or PDF directories into the wiki by preprocessing them into prepared MinerU markdown, then handing the prepared sources to /ingest.
argument-hint: "(<local-pdf-or-dir> | <wiki/sources/papers/*.md>) [--title <str>] [--discover]"
---

# /ingest-local-pdf

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

Use this skill when the content source is a local PDF, a directory of PDFs, or another raw local file that needs MinerU preprocessing before it can enter the wiki. The skill normalizes the source into `wiki/sources/papers/*.md`, enriches bibliographic metadata from Zotero when the same PDF/item is already in Zotero, then hands the prepared path to `/ingest` so the normal paper/concept/claim workflow stays in one place.

Use this local reference on demand:

- `references/pdf-preprocessing.md` — local PDF normalization, title recovery, directory batching, and handoff to `/ingest`

## Workflow

**Pre-condition**: run from the repository root. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, `@raw-root`, `@configured-sources-papers`, and `@mineru-cache`:

Run commands from the repository root.

```shell
uv run python tools/research_wiki.py stats '@configured' --json
```

If path diagnosis is needed, use `uv run python tools/resolve_path_alias.py '@configured' '@raw-root' '@configured-sources-papers' '@mineru-cache'`. Do not import path helpers from `tools._env`; runtime path aliases are resolved by `tools/_paths.py` through this CLI.

1. Resolve the input path.
   - If the input is a single PDF, inspect the first page and recover a confident title only when the title is clear.
   - If the input is a directory, enumerate readable PDFs in deterministic order and process each file separately.
2. Before preprocessing each PDF, try Zotero metadata enrichment:
   ```shell
   uv run python tools/enrich_local_pdf_bibtex.py --source '<local-path>' [--title '<agent-recovered-title>']
   ```
   If it returns `status: ok`, capture `.bibtex` exactly and pass it to `prepare_paper_source.py` with `--bibtex`; also pass `.citation_key`, `.authors`, and `.year` when present so the prepared source filename can use the Zotero citation key or fall back to `author_year_veryshorttitle`. Preserve `.paper_slug` for the downstream `/ingest` paper page slug when present. If it returns `not_found` or `metadata_error`, continue without BibTeX and mention the reason in the report; do not block PDF ingest.
3. Preprocess each PDF with `tools/prepare_paper_source.py --output-dir '@configured-sources-papers' --cache-root '@mineru-cache'` into the configured wiki source directory. This step includes the conservative LaTeX math repair pass documented in `references/pdf-preprocessing.md`; report any `latex math repaired: ...` warning in the final summary.
4. If `prepare_paper_source.py` reports `usable: false`, surface the warnings and skip that file.
5. Hand each prepared `wiki/sources/papers/<source-slug>.md` to `/ingest` for the paper-page workflow, preserving the prepared source's `## BibTeX` block as the preferred BibTeX when present.
6. If the source is already a prepared `wiki/sources/papers/*.md`, skip preprocessing and pass it straight to `/ingest`.

## Constraints

- Do not use Zotero as the content source here; selected content must still be the user-provided local PDF/prepared markdown. Zotero lookup in this skill is metadata-only, for BibTeX enrichment of the local PDF.
- Do not write directly to `wiki/papers/`, `wiki/concepts/`, `wiki/claims/`, or `wiki/people/` from this skill.
- Keep raw PDFs in their original location; only the prepared markdown and extracted assets belong under the configured wiki source directory.
- Never pass literal relative output paths such as `wiki/sources` or `wiki/sources/papers`; these resolve inside the code repository when the wiki is split into an external vault. Use `@configured-sources-papers`.
- If the directory contains mixed file types, ignore non-PDF files unless the user explicitly points at a prepared markdown file.

## Dependencies

### Tools

- `uv run python tools/enrich_local_pdf_bibtex.py --source '<local-path>' [--title '<recovered-title>']` — optional metadata-only Zotero enrichment; returns `.bibtex` when confident
- `uv run python tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source '<local-path>' [--title '<recovered-title>'] [--citation-key '<zotero-citation-key>'] [--authors '<author-list>'] [--year <year>] [--bibtex "$BIBTEX"]`
- `uv run python tools/repair_latex_math.py --dry-run '@configured-sources-papers/<source-slug>.md'` — optional inspection command for existing prepared markdown; `prepare_paper_source.py` already runs this repair during new PDF preprocessing

### Skills

- `/ingest` — consumes the prepared `wiki/sources/papers/*.md` path and writes the wiki pages

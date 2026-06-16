# llm-wiki tools

This directory contains the command-line programs used by llm-wiki skills.
Most commands are intended to be run through `uv run python -X utf8` from the
repository root so dependencies, UTF-8 output, and local path configuration are
loaded consistently.

## General usage

```shell
uv run python -X utf8 tools/<tool>.py --help
uv run python -X utf8 tools/<tool>.py <command> --help
```

Runtime path aliases such as `@configured`, `@raw-root`,
`@configured-sources`, `@configured-sources-papers`, and `@mineru-cache` are
resolved only by tools that import `tools/_paths.py`. For ordinary shell
commands, resolve aliases first:

```shell
uv run python -X utf8 tools/resolve_path_alias.py @configured @configured-sources-papers
```

## Safety model

Tools that can rewrite, delete, migrate, or reset files default to a dry run
where practical. Use `--yes`, `--write`, or omit `--dry-run` only after reading
the plan. The `raw/` tree is user-owned input; ingestion helpers copy or prepare
vault-visible files under `wiki/sources/` instead of modifying the original raw
sources.

`wiki/graph/` is derived state. Prefer `tools/research_wiki.py` commands such as
`add-edge`, `add-citation`, `dedup-edges`, `rebuild-index`, and
`rebuild-context-brief` rather than editing graph files directly.

## Shell-facing tools

| Tool | Use when | Typical command |
| --- | --- | --- |
| `research_wiki.py` | Append logs, update metadata, manage graph edges, rebuild derived wiki files, query wiki state. | `uv run python -X utf8 tools/research_wiki.py log @configured "ingest \| added paper"` |
| `lint.py` | Check wiki structure, links, required fields, graph consistency, and deterministic fixes. | `uv run python -X utf8 tools/lint.py --wiki-dir @configured --suggest` |
| `grounding_lint.py` | Gate generated paper/concept/claim pages for source anchors and exact prepared-source quotes. | `uv run python -X utf8 tools/grounding_lint.py --wiki-dir @configured --only papers/foo.md` |
| `prepare_paper_source.py` | Convert one local PDF into canonical MinerU markdown for `/ingest`. | `uv run python -X utf8 tools/prepare_paper_source.py --source raw/papers/a.pdf --output-dir @configured-sources-papers --cache-root @mineru-cache` |
| `init_discovery.py` | Prepare all local `/init` sources and build the handoff manifest. | `uv run python -X utf8 tools/init_discovery.py prepare --wiki-root @configured --sources-output-dir @configured-sources --cache-root @mineru-cache --output-manifest .checkpoints/init-prepare.json` |
| `discover.py` | Build a candidate-paper shortlist from anchors, a topic, or recent wiki papers. | `uv run python -X utf8 tools/discover.py from-topic "isotope shift theory" --wiki-root @configured --markdown` |
| `fetch_literature.py` | Query no-key public literature metadata via Crossref/OpenAlex. | `uv run python -X utf8 tools/fetch_literature.py search "MCDHF isotope shift" --limit 10` |
| `fetch_wikipedia.py` | Fetch Wikipedia summaries or sections for `/prefill`. | `uv run python -X utf8 tools/fetch_wikipedia.py summary "Configuration interaction"` |
| `find_zotero_pdf.py` | Find matching local Zotero PDF attachments without modifying Zotero. | `uv run python -X utf8 tools/find_zotero_pdf.py --title "Paper title"` |
| `fetch_zotero_metadata.py` | Read Zotero Desktop local API metadata and BibTeX for one item. | `uv run python -X utf8 tools/fetch_zotero_metadata.py --item-key ABC123` |
| `list_zotero_collection.py` | List Zotero citation keys, titles, and DOIs under a collection path. | `uv run python -X utf8 tools/list_zotero_collection.py "2026/202605/0507" --output-md papers.md` |
| `enrich_local_pdf_bibtex.py` | Derive BibTeX for a local PDF from matching Zotero metadata. | `uv run python -X utf8 tools/enrich_local_pdf_bibtex.py --source raw/papers/a.pdf --title "Paper title"` |
| `backfill_bibtex_from_zotero.py` | Update existing paper pages and prepared sources with Zotero-derived BibTeX. | `uv run python -X utf8 tools/backfill_bibtex_from_zotero.py --slug foo --dry-run` |
| `promote_light_ingest.py` | Rank light-ingested papers for promotion to full `/ingest`. | `uv run python -X utf8 tools/promote_light_ingest.py --wiki-dir @configured --output .checkpoints/promote.md` |
| `repair_latex_math.py` | Repair OCR-spaced LaTeX math in Markdown files. | `uv run python -X utf8 tools/repair_latex_math.py @configured-sources-papers --dry-run` |
| `resolve_path_alias.py` | Resolve runtime path aliases before using normal shell commands. | `uv run python -X utf8 tools/resolve_path_alias.py --json @configured @raw-root` |

## Maintenance and migration tools

These tools are for repository migration or schema maintenance. Read `--help`
and run the default dry-run/plan mode first.

| Tool | Use when |
| --- | --- |
| `separate_wiki_repository.py` | Copy or move in-repo `wiki/` and `raw/` to external absolute vault paths and write `config/paths.json`. |
| `clean_wiki_repository.py` | Remove in-repo `wiki/` and/or `raw/` after external paths are configured. |
| `reset_wiki.py` | Reset selected wiki/raw/log/checkpoint scopes to a clean scaffold. |
| `migrate_log.py` | Move legacy `wiki/log.md` entries into weekly `wiki/log/*.md` files. |
| `migrate_source_slugs.py` | Rename prepared sources to citation-key based slugs and update links. |
| `migrate_paper_slugs.py` | Rename paper pages to citation-key based slugs and update links/graph/log references. |
| `migrate_bibtex_frontmatter.py` | Move paper BibTeX from YAML frontmatter into `## BibTeX` fenced blocks. |
| `normalize_prepared_source_frontmatter.py` | Normalize prepared-source frontmatter order and Zotero storage paths. |

## Internal helper modules

Files beginning with `_` are imported by the CLI tools and are not primary shell
entrypoints: `_cli_io.py`, `_env.py`, `_mineru.py`, `_paths.py`, `_schemas.py`,
and `_zotero_snapshot.py`.

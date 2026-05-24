---
description: List papers from a Zotero collection or subcollection by reading the local Zotero SQLite database snapshot; returns citationKey, title, and DOI, with optional Markdown export. Use when the user names a Zotero collection path/category and asks to list or export its literature items.
argument-hint: "<collection-path> [--zotero-root <dir>] [--no-recursive] [--output-md <path>]"
---

# /zotero-collection-list

List `citationKey`, `title`, and `doi` for bibliographic items under a Zotero collection path by querying a read-only snapshot of `zotero.sqlite`.

Use this when the user says things like:

- “list citationKey, title, and DOI under Zotero collection `2026/202605/0507`”
- “export a Zotero category/subcategory literature list to Markdown”
- “check which collection items lack citationKey/DOI”

## Inputs

- `<collection-path>`: collection hierarchy, accepted separators: `/`, `>`, or `::`.
  - Example: `2026/202605/0507`
  - Example: `2026 > 202605 > 0507`
- `--zotero-root <dir>` optional: Zotero data directory or profile directory. If omitted, scan the selected profile's `zotero_roots` in `config/paths.json`.
- `--no-recursive` optional: list only direct items in the collection, not items in nested subcollections.
- `--output-md <path>` optional: write a Markdown table with `citationKey | title | doi`.

Do not use Zotero item keys as user-facing selectors for this skill. This skill selects by collection path only.

## Workflow

Run from the repository root.

```shell
uv run python tools/list_zotero_collection.py "2026/202605/0507"
```

Optional variants:

```shell
uv run python tools/list_zotero_collection.py "2026/202605/0507" --no-recursive
uv run python tools/list_zotero_collection.py "2026/202605/0507" --output-md .checkpoints/zotero-0507.md
uv run python tools/list_zotero_collection.py "2026/202605/0507" --zotero-root "$HOME/Zotero"
```

The tool:

1. Resolves Zotero root through `config/paths.json` unless `--zotero-root` is provided.
2. Creates/reuses a read-only snapshot under `config/zotero-cache/`.
3. Resolves the exact collection path.
4. Lists non-attachment bibliographic parent items.
5. Returns JSON with `citationKey`, `title`, and `doi`.
6. If `--output-md` is provided, writes a Markdown table to that path.

## Reporting

For normal user-facing output, summarize:

- resolved collection path
- total item count
- missing citationKey count
- missing DOI count
- the requested table/list or Markdown output path

If the user asks for a simple list, output only the requested columns.

If the collection path is ambiguous, report the candidate full paths and ask the user to choose a more specific path.

If the collection path is missing, say it was not found and suggest checking the exact Zotero collection hierarchy.

## Constraints

- This skill is read-only for Zotero.
- Do not write wiki pages, graph files, `index.md`, or `log.md`.
- Do not run MinerU or prepare PDFs.
- Do not mutate `raw/` or Zotero storage.
- Do not expose internal SQLite row IDs unless needed for debugging; prefer Zotero `zotero_key`.

# /init Prepare

Use this reference when `/init` is preparing local inputs and writing `.checkpoints/init-sources.json`.

## Prepare Flow

- Run `uv run python tools/init_discovery.py prepare --raw-root '@raw-root' --wiki-root '@configured' --sources-output-dir '@configured-sources' --cache-root '@mineru-cache' --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`.
- Before preparing local PDFs, recover confident titles when possible and write `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }` or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title" } }`.
- `tools/init_discovery.py prepare` must pass recovered titles into `uv run python tools/prepare_paper_source.py --raw-root '@raw-root' --output-dir '@configured-sources-papers' --cache-root '@mineru-cache' --source <local-path> [--title "<recovered-title>"] [--citation-key "<zotero-citation-key>"] [--authors "<author-list>"] [--year <year>] [--bibtex "$BIBTEX"]`.
- `tools/init_discovery.py prepare` must delegate local paper normalization to the same helper and reuse pre-staged `wiki/sources/` artifacts when they already exist.
- For local PDFs, use this recovery order only: agent-recovered title from the first page -> MinerU produces structured markdown.
- When the agent supplied a confident PDF title, that title is authoritative for the prepared manifest. MinerU cover-page detected titles are fallback display strings only and must not overwrite the agent title.
- If no confident PDF title is available, omit `--title`. The MinerU pipeline still runs cleanly with the flag absent. Metadata or filename titles remain display-only.

## Source Preference Rules

- The canonical prepared format is `mineru-md`: `wiki/sources/papers/<source-slug>.md` plus `wiki/sources/papers/assets/<source-slug>/<hash>.jpg` for figures.
- Keep notes/web on their original source paths. `/init` reads them directly during scaffolding.
- If the handed-off source already lives under `wiki/sources/`, treat that path as canonical and do not duplicate it into `raw/papers/`.
- Set each local paper's `canonical_ingest_path` to the prepared `wiki/sources/papers/<source-slug>.md` path. If MinerU prep failed (manifest `usable: false`), record the warning and skip that paper rather than substituting the raw PDF.

## Source Manifest Contract

- Run `uv run python tools/init_discovery.py manifest --raw-root '@raw-root' --wiki-root '@configured' --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json` after `prepare` succeeds.
- `.checkpoints/init-sources.json` is the single source of truth for Step 5 ingest order.
- All entries are `origin=user_local` with the canonical prepared path. `/init` does not download external papers, so no `origin=introduced` entries are produced.
- Step 5 must consume the handed-off `canonical_ingest_path` exactly as written.

- Zotero metadata enrichment is attempted for local PDFs when possible. If it finds a citation key, that key is used as the prepared source filename stem; if not, the prep tool falls back to `author_year_veryshorttitle`. Enrichment failures do not block `/init`.
- Prepared source frontmatter must keep Zotero attachment paths portable: when a PDF lives under a Zotero data directory `storage/`, `source` must be `${Zotero data directory}/storage/<attachment-key>/<file>.pdf`, never the absolute path from the machine that generated the markdown.

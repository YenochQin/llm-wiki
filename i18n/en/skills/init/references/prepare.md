# /init Prepare

Use this reference when `/init` is preparing local inputs and writing `.checkpoints/init-sources.json`.

## Prepare Flow

- Run `"$PYTHON_BIN" tools/init_discovery.py prepare --raw-root raw --pdf-titles-json .checkpoints/init-pdf-titles.json --output-manifest .checkpoints/init-prepare.json`.
- Before preparing local PDFs, recover confident titles when possible and write `.checkpoints/init-pdf-titles.json` as either `{ "raw/papers/foo.pdf": "Recovered Paper Title" }` or `{ "raw/papers/foo.pdf": { "title": "Recovered Paper Title", "arxiv_id": "2401.00001" } }` when a confident arXiv ID is already known.
- `tools/init_discovery.py prepare` must pass those recovered titles and IDs into `"$PYTHON_BIN" tools/prepare_paper_source.py --raw-root raw --source <local-path> [--title "<recovered-title>"] [--arxiv-id "<recovered-arxiv-id>"]`.
- `tools/init_discovery.py prepare` must delegate local paper normalization to the same helper and reuse pre-staged `raw/tmp/` artifacts when they already exist.
- For local PDFs, use this recovery order only: handed-off arXiv ID or filename/path arXiv ID -> title-based no-key literature lookup when a confident title was supplied -> MinerU produces structured markdown.
- When the agent supplied a confident PDF title, that title is authoritative for the prepared manifest. MinerU cover-page detected titles are fallback display strings only and must not overwrite the agent title.
- Do not use PDF metadata or PDF body text as arXiv-ID hints during prepare.
- The arXiv ID, when recovered, is used only for downstream metadata enrichment (venue, year, citation counts) once `/ingest` runs. The prepared `.md` file itself is always MinerU output.
- If no confident PDF title is available, omit `--title`; if no confident arXiv ID is available, omit `--arxiv-id`. The MinerU pipeline still runs cleanly with both flags absent. Metadata or filename titles remain display-only.

## Source Preference Rules

- The canonical prepared format is `mineru-md`: `raw/tmp/papers/<slug>.md` plus `raw/tmp/papers/assets/<slug>/<hash>.jpg` for figures.
- Keep notes/web on their original source paths. `/init` reads them directly during scaffolding.
- If the handed-off source already lives under `raw/tmp/`, treat that path as canonical and do not duplicate it into `raw/papers/`.
- Set each local paper's `canonical_ingest_path` to the prepared `raw/tmp/papers/<slug>.md` path. If MinerU prep failed (manifest `usable: false`), record the warning and skip that paper rather than substituting the raw PDF.

## Source Manifest Contract

- Run `"$PYTHON_BIN" tools/init_discovery.py manifest --raw-root raw --prepared-manifest .checkpoints/init-prepare.json --output-sources .checkpoints/init-sources.json` after `prepare` succeeds.
- `.checkpoints/init-sources.json` is the single source of truth for Step 5 ingest order.
- All entries are `origin=user_local` with the canonical prepared path. `/init` does not download external papers, so no `origin=introduced` entries are produced.
- Step 5 must consume the handed-off `canonical_ingest_path` exactly as written.

# /ingest Error Handling

Open this reference when a step fails. `/ingest` prefers to degrade gracefully except at the explicit hard-stop gates below: record what happened, continue only where this reference permits it, and surface the gap in the final report.

## Source parsing

- **MinerU API call fails (network, 4xx/5xx)**: if the local MinerU backend is installed (`uv sync --extra local`), retry once with `--backend local`. Otherwise stop and surface a clear message asking the user to either set `MINERU_API_TOKEN`, fix connectivity, or install the local backend.
- **MinerU returns an unusable manifest** (`usable: false` from `prepare_paper_source.py`): stop and report the `warnings` array verbatim. Common causes: scanned PDF without OCR, encrypted PDF, image-only pages. Do not paper over the failure by ingesting the raw PDF text — `mineru-md` is the contract.
- **No readable source at all**: stop and report. Do not create a paper page from a title alone — a paper page without grounded content is noise.
- **INIT MODE input unreadable**: do not attempt to re-prepare the source (INIT MODE is read-only on `raw/`). Stop, record the failure, and let the parent `/init` retry or skip the paper at fan-in.

## External APIs

- **Zotero Local API unavailable** (`fetch_zotero_metadata.py` times out, refuses the connection, or returns any `status` other than `ok` during Zotero lookup mode): stop immediately. Do not follow a SQLite/Crossref fallback hint, do not run `prepare_paper_source.py`, and do not continue with incomplete Zotero metadata. Tell the user: `Open Zotero Desktop, ensure local API access is enabled, then rerun /ingest from the beginning.`
- **Literature lookup unavailable** (`fetch_literature.py paper` errors): skip external enrichment, default `importance` to 3, and note in the report that the paper's importance is provisional. Skip the citation backfill step entirely for this ingest.

## Slug collisions

- **Generated slug matches an existing page with a different DOI or title**: stop and report. Do not append a numeric suffix silently — a collision between two different papers at the same slug is a signal the wiki has a naming problem that the user should resolve.
- **Generated slug matches an existing page with the same paper**: the paper is already ingested. Report and exit.
- **Within a single ingest, a generated concept or claim slug collides with a different existing page**: append a numeric suffix (`-2`, `-3`, ...) via the tool's built-in collision handling. This is the one case where suffixing is correct — it happens when two genuinely different ideas produce the same slug under the deterministic rule.

## Wiki not initialized

If `` is missing or empty, run:

```shell
uv run python -X utf8 tools/research_wiki.py init '@configured'
```

Then retry `/ingest`. Do not attempt to create pages in a non-initialized wiki; `index.md` and `graph/` scaffolding must exist first.

## Partial failure mid-ingest

If an ingest fails after some writes have landed (paper page written, but concept dedup or graph edge fails):

- do not roll back the writes that succeeded
- append a log entry via `tools/research_wiki.py log` describing which steps completed and which are incomplete
- surface the incomplete steps in the user report so the user can run `/edit` or `/check --fix` to finish the job
- in INIT MODE, if the ingest completed successfully, commit inside the worktree before exiting (see `references/init-mode.md`). If the ingest partially failed, do **not** commit the incomplete state; let the parent `/init` handle the failed worktree at fan-in

## When to stop vs. continue

Stop outright when:

- no source can be read at all
- Zotero Local API metadata lookup fails in Zotero lookup mode
- the paper is already ingested (slug + DOI/title match an existing page)
- a slug collision would silently overwrite a different existing paper

Continue with a warning when:

- the literature enrichment call is down (paper page still works, just plainer)
- the reference list cannot be parsed (skip step 5; paper ingest still works)
- a single concept or claim dedup call fails transiently (retry once; if it still fails, skip that candidate and note it)

The guiding principle: a partial ingest that preserves a well-shaped paper page is more useful than a clean abort that leaves the wiki unchanged. Partial state is recoverable via `/check` and `/edit`. Lost partial state is not.

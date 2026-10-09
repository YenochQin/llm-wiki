# Prepared-source handoff from /init

Read this reference only when `/init` invokes `/ingest` with a source from `.checkpoints/init-sources.json`.

- `/init` processes the manifest in `shortlist_rank` order, one paper at a time.
- Consume the selected entry's `canonical_ingest_path` exactly as handed off. Resolve runtime aliases before direct file reads; preserve the manifest's source identity and path.
- The source is usable MinerU markdown already prepared under the configured `sources/papers/` directory. Do not rescan `raw/`, repeat preprocessing, or substitute another source.
- Keep all user-owned raw inputs read-only. If the prepared file is missing or unusable, report the blocked entry so `/init` can record it and continue with other papers.
- Run the same Phases A–E as every prepared-source ingest, including deduplication, reverse links, citation handling, topic placement, navigation, logs, and scoped grounding checks.
- Use the shared invariants for identity and slug allocation. The canonical source filename and the resulting paper-page slug may differ.
- Return the completed, skipped, or incomplete outcome and affected page paths to `/init`. Apply the recovery rules below before treating an existing paper as a skip.

## Interrupted entries

Use `research_wiki.py checkpoint-load '@configured' init-session` to load recovery metadata. Store each entry under `paper:<canonical_ingest_path>` with `checkpoint-set-meta`; its value is a JSON string containing `status`, `paper_path`, `source_sha256`, `created_in_session`, `completed_phases`, and `written_files` (absolute content-file paths mapped to their last written SHA-256). Pass JSON as one correctly quoted argument.

- Before the first content write, record `status: incomplete`, source identity/hash, intended paper path, and whether that paper was absent before this session (`created_in_session`). Update file hashes after writes and completed phases after their Gates pass. Shared append-only logs/graph files need operation records, not whole-file hashes; other papers may legitimately update them.
- A completed record is reusable only for the same source with its expected paper present. A matching paper that predates this session is skipped without rewriting. Never infer completion merely from the paper file or a historical completed/failed list; the per-entry record is authoritative.
- For an incomplete entry created by this session, confirm the canonical source/identity and recorded content-file hashes. Then bypass Phase A's ordinary stop-if-exists check for that paper only, reuse verified completed outputs, and continue from the first unfinished phase. Recover upstream evidence from the source or existing Evidence Pack as needed. Finish missing entities, backlinks, citations, and navigation; deduplicate existing relationships and avoid duplicating already-recorded log operations.
- A changed source, conflicting edits, missing recovery provenance, or an unverified partial write leaves the entry incomplete with a recovery blocker. Preserve existing files and continue other entries; do not skip it as completed or overwrite uncertain work.
- Mark `status: completed` only after the final Gate passes. On failure, retain `incomplete`, actual written paths, and remaining steps. These are internal recovery records, not new user-facing flags or permission to regenerate unrelated existing papers.

The normal ingest evidence and Gate requirements remain authoritative during recovery.

---
name: edit
description: Apply user-requested wiki changes, save answers with source provenance, or explicitly add/delete raw sources. Use for writes rather than /ask.
argument-hint: "[request]"
---

# /edit

> Apply the user's requested changes to wiki content, including saving a prior `/ask` answer. Raw-source additions and deletions require a request naming the intended material; existing raw content is not rewritten.

## Inputs

User request, for example:

- "Save the previous answer in wiki/outputs/."
- "Update the SOTA tracker in topics/efficient-llm-adaptation."
- "Add a new variant to concepts/lora."
- "Add this local source to raw/notes/."
- "Delete raw/papers/xxx.pdf."

## Outputs

- Requested page or raw-source changes.
- Necessary backlinks, catalog entries, derived graph updates, and an `edit` log entry after actual changes.
- A report of changed paths and unresolved evidence gaps.

## Workflow

**Precondition**: run from the repository root. Resolve the configured external wiki root before direct file operations. Resolve `@raw-root` with the same tool only when a raw-source operation needs it; never create literal alias directories or repository-local research content.

```shell
uv run python -X utf8 tools/resolve_path_alias.py '@configured'
```

### Step 1: Identify the Requested Change

1. Identify the target, requested changes, and source material from the current conversation. Read existing target pages before changing them.
2. For a prior answer, retain the original question, source-page citations, qualifications, and unresolved gaps. If essential answer/source context is unavailable, request that missing information rather than recreating it from memory.
3. Use existing authorization for the specified change. Clarify only an ambiguous target or missing scope; a prior `/ask` query alone does not authorize a save.
4. Open `docs/runtime-page-templates.en.md` before creating or changing page structure, frontmatter, or body sections. Follow `AGENTS.md` and the source-grounding reference for evidence requirements.

### Step 2: Apply the Changes

**Wiki content**:

- Modify only requested pages and the related files needed to maintain their consistency.
- To save an answer without a specified entity type, use `wiki/outputs/{query-slug}.md`. Preserve the answer's citations and uncertainty; include `title`, `slug`, `query`, `source_pages`, and `date_created` in frontmatter. Check for an existing destination before creating or replacing it.
- Create or materially update concept/claim pages only when the user's request includes that knowledge change. Re-read the actual supporting sources; a synthesized answer alone is not source evidence. Preserve canonical prepared-source links, exact excerpts, Evidence Pack anchors, and required backlinks.
- Maintain forward and reverse links together. Use `tools/research_wiki.py add-edge` or `add-citation` for warranted graph relationships, following the endpoint/type rules; never edit `wiki/graph/` manually.
- After changing paper/concept/claim pages, run `uv run python -X utf8 tools/grounding_lint.py --wiki-dir '@configured' --only <touched-relative-path> --json` for the touched files. Fix red issues from source evidence or report the source-quality blocker; do not claim a passed grounding check when red issues remain.

**Raw sources**:

- Add a source only when the user explicitly requests it. Copy the named local source or save the requested web content under the appropriate configured raw directory. Do not overwrite an existing raw file.
- Delete only the explicitly requested, resolved raw-source target. If the target is ambiguous or the request does not authorize deletion, clarify it first. Do not expand a file deletion into a directory or batch deletion.
- Do not modify the contents of existing raw files. Adding or deleting a named source is the user-authorized exception to raw read-only ownership.
- Paper ingestion remains a separate source-preparation/ingest operation; a raw-source change alone does not authorize ingestion or removal of derived wiki pages.

### Step 3: Maintain Consistency

1. Update `index.md` when affected wiki entries change; raw-only changes do not require a catalog edit.
2. Rebuild relevant derived context/open-question files through `tools/research_wiki.py` when affected wiki content or graph relationships change, or when the user explicitly requests that maintenance.
3. After actual changes, append a log entry through the tool:

   ```shell
   uv run python -X utf8 tools/research_wiki.py log '@configured' "edit | {description}"
   ```

4. If the request produces no change or is only a preview, report that result without writing a log or maintenance files.

### Step 4: Report

List the actual changed paths, what changed, relevant verification, and any unresolved evidence gaps.

## Constraints

- **User-directed writes**: `/edit` is the write operation for saved answers and requested wiki changes. Do not turn an unrequested finding into additional content edits.
- **Raw ownership**: only explicitly requested additions/deletions are allowed; existing raw contents remain read-only.
- **Evidence and templates**: preserve page structure, formal page language, source provenance, exact excerpts, and uncertainty. Do not promote an inference into a source-backed claim merely by saving it.
- **Graph and links**: maintain backlinks; use graph tools for changes and rebuilds.
- **Preview/no-write requests**: show proposed changes without modifying pages, raw files, logs, catalog, or derived files.

## Dependencies

- `tools/resolve_path_alias.py` — resolve external content roots.
- `tools/research_wiki.py` — slug generation, graph operations, derived rebuilds, and logging when needed.
- `tools/grounding_lint.py` — scoped grounding checks after paper/concept/claim edits.
- `docs/runtime-page-templates.en.md` — page structure and metadata.
- `.claude/skills/shared-references/source-grounding.md` — evidence discipline.

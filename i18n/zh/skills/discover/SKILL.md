---
description: Build a ranked shortlist of candidate papers (anchor-driven, topic-driven, or derived from current wiki state) that the user — or an upstream skill — may decide to feed into `/ingest`. Use whenever the user asks "what should I read next", "find papers similar to this one", "recommend related work", "what's around this topic", or whenever `/ingest` is invoked with `--discover`. Does not ingest; only proposes.
argument-hint: "(--anchor <id> [--anchor <id>] [--negative <id>] | --topic <str> | --from-wiki) [--limit N]"
---

# /discover

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> Produce a ranked shortlist of paper candidates from one of three seed modes. Surface them to the user (or to the calling skill) with rationales. Never auto-ingest — `/discover` is a proposal stage, `/ingest` is the action stage.

Use these local references on demand:

- `references/seed-modes.md` — when to pick anchor / topic / wiki mode and how to translate the user's phrasing into one
- `references/ranking-signals.md` — what `tools/discover.py` scores on and why discovery does **not** share `/init`'s survey preference
- `references/wiki-dedup.md` — how candidates are filtered against `wiki/papers/` and what to do with matches

## Inputs

- `--anchor <id>` (repeatable): one or more anchor paper identifiers or titles (DOIs preferred when available). Drives the **anchor mode** — the primary use case, including the post-`/ingest` "what to read next" flow.
- `--negative <id>` (repeatable, optional): IDs to exclude from recommendations. Only meaningful with `--anchor`.
- `--topic "<str>"`: a topic / query string. Drives the **topic mode** — lighter alternative to `/init`'s planner.
- `--from-wiki`: derive seeds automatically from the wiki's most recently modified papers. Drives the **wiki mode**.
- `--limit N` (optional, default 10): max shortlist size.

Exactly one of `--anchor`, `--topic`, `--from-wiki` must be given.

## Outputs

- `.checkpoints/discover-{seed-slug}-{YYYY-MM-DD}.json` — full shortlist payload, machine-readable; the seed slug is derived from the first anchor or the topic
- a human-readable markdown summary printed to the user with rationale per candidate
- `wiki/log.md` — one append line via `tools/research_wiki.py log`

`/discover` does not write anywhere else in `wiki/` and does not touch `raw/`. Whether to actually pull a candidate into the wiki is the caller's decision (a follow-up `/ingest`).

## Wiki Interaction

### Reads

- `wiki/papers/*.md` — frontmatter `external_ids.DOI` and title for dedup against already-ingested papers
- `wiki/papers/*.md` modification times — for `--from-wiki` anchor selection

### Writes

- `wiki/log.md` — APPEND via `tools/research_wiki.py log`

### Graph edges created

- none. Graph mutations belong to `/ingest`, not `/discover`.

## Workflow

**Pre-condition**: working directory contains `wiki/`, `raw/`, and `tools/`. Resolve the Python interpreter once and reuse it:

```bash
if [ -x .venv/bin/python ]; then
  PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then
  PYTHON_BIN=.venv/Scripts/python.exe
else
  PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 1: Pick the seed mode

Translate the user's request into exactly one of `from-anchors`, `from-topic`, or `from-wiki`. The decision rule lives in `references/seed-modes.md`; the short version:

- the user named one or more specific papers, or this is a post-`/ingest` `--discover` follow-up → **anchors**
- the user gave a topic / direction / keywords → **topic**
- the user asked open-ended "what should I read next" with no anchor and no topic → **wiki**

If the user supplied negatives ("not these"), include them via `--negative` in anchor mode only.

### Step 2: Run the discovery tool

```bash
"$PYTHON_BIN" tools/discover.py from-anchors \
  --id <doi-or-title> [--id <doi-or-title>...] [--negative <id-or-title>...] \
  --wiki-root wiki \
  --limit 10 \
  --output-checkpoint .checkpoints/ \
  --markdown
```

Or for topic / wiki modes:

```bash
"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Anchor (and wiki) mode run no-key related search plus best-effort `references` + `citations` channels per anchor. References surface older canonical work when Crossref has deposited reference lists; citations may be empty because the no-key provider used here does not expose a full citing-works graph.

The tool handles candidate gathering, wiki dedup, ranking, and writes the checkpoint. Always pass `--wiki-root wiki` so already-ingested papers are filtered out — surfacing duplicates wastes the user's review time.

If Crossref is unavailable in topic mode, abort with a clear message rather than emitting an empty shortlist as if it were a real recommendation.

### Step 3: Present the shortlist

Show the markdown output to the user. For each candidate, the user needs enough to decide whether to ingest:

- title and DOI or provider identifier, when available
- one-line rationale (already produced by the tool: anchor count, citation count when available, year)
- abstract excerpt if the tool surfaced one

Append a short "next step" hint:

```
To ingest a candidate from configured Zotero libraries: run /ingest --title "<candidate title>" (or --doi <doi>). If the PDF is outside Zotero, pass the local PDF path directly to /ingest.
```

Do not ingest anything yourself. The user picks.

### Step 4: Log

```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki "discover | mode=<anchors|topic|wiki> | seed=<short-desc> | shortlist=<N>"
```

## Internal Callers

`/discover` is designed to be invoked both by users (manually) and by other skills (as a subroutine).

### From `/ingest --discover`

When `/ingest` is invoked with the optional `--discover` flag (default off), it calls `/discover` after the final report, using the just-ingested paper's DOI when available, otherwise its title. The shortlist is appended to `/ingest`'s report under a "Related papers you may want to ingest next" heading. `/ingest` never auto-ingests anything from this list.

### From `/init`

`/init` does not call `/discover`. `/init` ingests only local user-owned papers from `raw/papers/`; it does not propose or download external candidates. `/discover` is the right tool for follow-up reading suggestions after `/init` finishes.

## Constraints

- **Never auto-ingest**: `/discover` returns a shortlist and stops. Even when called by `/ingest --discover`, the caller surfaces results and the user decides what to ingest.
- **No writes to `wiki/` other than `log.md`**: paper pages, concepts, claims, graph edges all belong to `/ingest`.
- **No writes to `raw/`**: `/discover` does not download papers. For Zotero-managed PDFs, the user can run `/ingest --title "<candidate title>"` or `/ingest --doi <doi>` and let `/ingest` scan `config/zotero-roots.json`; for non-Zotero PDFs, they can pass the local PDF path directly to `/ingest`.
- **Always dedupe against the wiki**: pass `--wiki-root wiki` so the shortlist contains only papers not yet in the wiki. Surfacing duplicates is the most common low-quality failure mode.
- **Ranking is discovery-specific**: do not import or duplicate `tools/init_discovery.py`'s scoring helpers. The two skills have different objectives — `/init` wants broad foundational coverage; `/discover` wants relevant *next reads*. See `references/ranking-signals.md`.
- **No-key provider coverage**: anchor mode uses Crossref title/DOI lookup plus reference lookup when available. This is less complete than key-gated citation graphs, but it works without account setup.

## Error Handling

- **All seed channels fail**: report the failure, write no shortlist, and do not log a successful run.
- **No provider returns recommendations for an anchor**: keep going with the remaining anchors; if all anchors return zero, treat as total failure.
- **`--from-wiki` finds no anchorable papers** (`wiki/papers/` empty or paper pages are missing both title and DOI): tell the user the wiki is too sparse for wiki-mode discovery and suggest topic mode.
- **Anchor ID is malformed or unknown**: surface the bad ID in the report and continue with any remaining anchors.

## Dependencies

### Tools (via Bash)

- `"$PYTHON_BIN" tools/discover.py from-anchors --id <id> [--id <id>...] [--negative <id>...] --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-topic "<query>" --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/discover.py from-wiki --wiki-root wiki --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `"$PYTHON_BIN" tools/research_wiki.py log wiki "<message>"`

### Skills

- `/ingest` — caller via `--discover` flag; also the action the user takes on a chosen candidate
- `/init` — independent planner; does not call `/discover`

### External APIs

- Crossref — no-key search, paper metadata, and best-effort reference lookup via `tools/fetch_literature.py`

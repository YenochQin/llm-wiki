---
name: discover
description: Use when the user asks what to read next, wants papers similar to a given one, related-work recommendations, or what surrounds a topic — proposes a ranked shortlist of candidate papers to feed into /ingest, without ingesting them.
argument-hint: "(--anchor <id> [--anchor <id>] [--negative <id>] | --topic <str> [--since-year YYYY] | --from-wiki) [--limit N]"
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
- `--topic "<str>"`: a topic / query string. Drives the **topic mode** — recent-first, relevance-gated exploration and a lighter alternative to `/init`'s planner.
- `--since-year YYYY` (topic mode only, optional): earliest publication year. When omitted, use the current year minus 10.
- `--from-wiki`: derive seeds automatically from the wiki's most recently modified papers. Drives the **wiki mode**.
- `--limit N` (optional, default 12): max shortlist size.

Exactly one of `--anchor`, `--topic`, `--from-wiki` must be given.

## Outputs

- `.checkpoints/discover-{seed-slug}-{YYYY-MM-DD}.json` — full shortlist payload, machine-readable; the seed slug is derived from the first anchor or the topic
- a human-readable markdown summary printed to the user with rationale per candidate
- `wiki/outputs/ingest-candidates.md` — append structured queue rows when `/discover` is called from `/ingest --discover` or `/reingest --discover`
- `wiki/log/` — one append line via `tools/research_wiki.py log`

Manual `/discover` does not write anywhere else in `wiki/` and does not touch `raw/` unless the user explicitly asks to save the shortlist. Internal ingest-family callers save their gated candidates to `outputs/ingest-candidates.md`. Whether to actually pull a candidate into the wiki is the user's decision (a follow-up `/ingest`).

## Wiki Interaction

### Reads

- `wiki/papers/*.md` — frontmatter `external_ids.DOI` and title for dedup against already-ingested papers
- `wiki/papers/*.md` modification times — for `--from-wiki` anchor selection

### Writes

- `wiki/log/` — APPEND via `tools/research_wiki.py log`
- `wiki/outputs/ingest-candidates.md` — APPEND only for `/ingest --discover` or `/reingest --discover` callers, or when the user explicitly asks manual `/discover` to save candidates

### Graph edges created

- none. Graph mutations belong to `/ingest`, not `/discover`.

## Workflow

**Pre-condition**: a configured llm-wiki repo (see `/setup`). Run Python tools through `uv run python -X utf8`. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured` and `@raw-root`:

Run commands from the repository root.

```shell
uv run python -X utf8 tools/research_wiki.py stats '@configured' --json
```

### Step 1: Pick the seed mode

Translate the user's request into exactly one of `from-anchors`, `from-topic`, or `from-wiki`. The decision rule lives in `references/seed-modes.md`; the short version:

- the user named one or more specific papers, or this is a post-`/ingest` `--discover` follow-up → **anchors**
- the user gave a topic / direction / keywords → **topic**
- the user asked open-ended "what should I read next" with no anchor and no topic → **wiki**

If the user supplied negatives ("not these"), include them via `--negative` in anchor mode only.

### Step 2: Run the discovery tool

```shell
uv run python -X utf8 tools/discover.py from-anchors --id <doi-or-title> [--id <doi-or-title>...] [--negative <id-or-title>...] --wiki-root '@configured' --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Or for topic / wiki modes:

```shell
uv run python -X utf8 tools/discover.py from-topic "<canonical-query>" \
  [--query-variant "<equivalent-query>"...] \
  [--required-term-group "<term-a|synonym-a>"...] \
  [--required-title-term-group "<term-a|synonym-a>"...] \
  [--since-year <YYYY>] \
  --wiki-root '@configured' --limit 12 --output-checkpoint .checkpoints/ --markdown
uv run python -X utf8 tools/discover.py from-wiki --wiki-root '@configured' --limit 10 --output-checkpoint .checkpoints/ --markdown
```

Topic search uses OpenAlex as the primary works pool plus a small Crossref supplement before unified filtering. Crossref also acts as the no-key fallback when OpenAlex is sparse or unavailable. Anchor (and wiki) mode additionally uses Crossref DOI metadata and deposited references; citations may be empty because the current no-key paths do not expose a reliable full citing-works graph.

For topic mode, convert non-English phrasing to one canonical scholarly English query without changing scope. For a narrow or terminology-sensitive topic, derive 2–4 equivalent English search variants and pass them with repeatable `--query-variant`. For a named entity family whose members are indexed separately, derive up to 12 member-specific variants instead of placing every member in one long query. These variants are internal retrieval expansions, not user-owned parameters: preserve the user's concepts, entities, and exclusions, and do not broaden into adjacent applications. Example: an atomic-structure topic may expand observable names such as `energy levels`, `transition probabilities`, and `oscillator strengths`, but must retain `neutral atoms` and the requested element family or member in every variant.

When the topic contains two or more hard qualifiers that commonly occur separately in off-topic fields, derive repeatable `--required-term-group` constraints. Each group is a pipe-separated set of literal alternatives; every visible candidate must match at least one alternative from every group in its title, abstract, TLDR, or venue. Treat these as internal scope constraints, not user-owned parameters. For example, a neutral-transition-atom calculation query should require separate groups for neutral atomic species, the requested element family, and atomic-structure observables. Keep alternatives concise and inspectable.

Use `--required-title-term-group` for the research object or task when an abstract may cite or consume the requested data without the paper itself studying that topic. Title groups use the same AND-of-ORs syntax but match the title only. Prefer this gate for charge states, named entities, methods, and observables that must define the paper's main subject.

Topic mode defaults to papers from the current year minus 10 and targets 12 visible candidates. The tool gathers a much larger provider pool, deduplicates it, applies lexical topic coverage over title/abstract/venue, and ranks primarily by topic match and freshness. Citation count is only a tie-breaker. If fewer than 8 structured candidates survive, try the remaining equivalent variants once; never relax the topic gate merely to fill the list.

The tool handles candidate gathering, wiki dedup, heavy-relation filtering, ranking, Zotero collection-status annotation, and writes the checkpoint. Always pass `--wiki-root '@configured'` so already-ingested papers are filtered out — surfacing duplicates wastes the user's review time.

Before ranking and shortlist display, `tools/discover.py` applies a hard age/citation gate: if a candidate was published before 1990, recommend it only when `citation_count > 100`. Pre-1990 candidates with 100 or fewer citations must be dropped, even if they otherwise match the topic or anchor.

For anchor and wiki modes, `tools/discover.py` only keeps candidates with strong relation evidence: direct reference/citation channel, multiple discovery channels, multiple anchors, or an explicit influential-edge signal. A single `recommend`/title-search hit is not enough, even if it has many citations. Topic mode instead applies its own lexical relevance gate.

Use OpenAlex as the primary topic pool. Add only a small Crossref supplement to recover exact DOI/title records that OpenAlex ranks below its broad result window; send both pools through the same recency and relevance gates, and expose the source on every candidate. If OpenAlex fails or is sparse, let Crossref fill the deficit. If all topic-search providers fail, abort with a clear message rather than emitting an empty shortlist as if it were a real recommendation.

### Step 3: Present the shortlist

Show the markdown output to the user. For each candidate, the user needs enough to decide whether to ingest:

- title
- authors
- year
- DOI, or `unavailable` when the provider exposes none in manual `/discover` runs
- Zotero collection status: `collected`, `not collected`, or `unknown`
- provider source: `OpenAlex`, `Crossref`, or both
- one-line rationale / relation evidence (already produced by the tool: anchor count, relation channel, citation count when available, year)
- abstract excerpt if the tool surfaced one

Do not rewrite incomplete bibliographic hints into prose recommendations. A visible candidate must have at least a title and authors. If title or authors are missing, drop it from the user-facing shortlist and report only the number dropped. Do not output author-year-only, venue-only, DOI-only, citation-key-only, or "important paper" prose bullets.

Append a short "next step" hint:

```
To ingest a candidate from configured Zotero libraries: run /ingest --title "<candidate title>" (or --doi <doi>). If the PDF is outside Zotero, pass the local PDF path directly to /ingest.
```

Do not ingest anything yourself. The user picks.

### Step 4: Log

```shell
uv run python -X utf8 tools/research_wiki.py log '@configured' "discover | mode=<anchors|topic|wiki> | seed=<short-desc> | shortlist=<N>"
```

## Internal Callers

`/discover` is designed to be invoked both by users (manually) and by other skills (as a subroutine).

### From `/ingest --discover`

When `/ingest` or `/reingest` is invoked with the optional `--discover` flag (default off), it calls `/discover` after Phase E, using the just-ingested/refreshed paper's DOI when available, otherwise its title. The gated shortlist is appended to `@configured/outputs/ingest-candidates.md`, not to the paper page and not as a long final-report section. Because this is a post-ingest follow-up, surface only the heavy-relation shortlist produced by the tool, and keep each candidate's title, authors, DOI, and Zotero collection status visible in the queue row. `/ingest` and `/reingest` never auto-ingest anything from this list.

For this caller, apply a stricter candidate gate before anything reaches `outputs/ingest-candidates.md`. Each candidate must include exact title, authors, year, DOI, Zotero collection status, and one-line relation evidence. `DOI: unavailable` is allowed in manual `/discover` output, but not in ingest-family `--discover` queue rows. Drop candidates that fail the gate; if all are dropped, report `No structured follow-up candidates passed the gate` instead of naming unresolved references.

### From `/init`

`/init` does not call `/discover`. `/init` ingests only local user-owned papers from `raw/papers/`; it does not propose or download external candidates. `/discover` is the right tool for follow-up reading suggestions after `/init` finishes.

## Constraints

- **Never auto-ingest**: `/discover` returns a shortlist and stops. Even when called by `/ingest --discover`, the caller surfaces results and the user decides what to ingest.
- **No paper-page writes**: `/discover` never writes candidate recommendations into `papers/{slug}.md`. Ingest-family `--discover` callers write recommendations only to `outputs/ingest-candidates.md`; paper pages, concepts, claims, and graph edges all belong to `/ingest`.
- **No writes to `raw/`**: `/discover` does not download papers. For Zotero-managed PDFs, the user can run `/ingest --title "<candidate title>"` or `/ingest --doi <doi>` and let `/ingest` scan the selected profile's `zotero_roots` in `config/paths.json`; for non-Zotero PDFs, they can pass the local PDF path directly to `/ingest`.
- **Always dedupe against the wiki**: pass `--wiki-root '@configured'` so the shortlist contains only papers not yet in the wiki. Surfacing duplicates is the most common low-quality failure mode.
- **Pre-1990 citation gate**: candidates published before 1990 require `citation_count > 100`; otherwise drop them from every mode before ranking. This is a recommendation quality gate, not a soft scoring preference.
- **Recent-first topic mode**: unless the user supplies `--since-year`, keep topic candidates from the current year minus 10 onward. Rank topic match and freshness above citation count; do not use high citation count to rescue an off-topic or out-of-window paper.
- **Topic expansion stays in scope**: derived `--query-variant` values may add scholarly synonyms and named observables, but every variant must retain the user's research object and central task. Do not broaden into materials, catalysis, biology, or other application domains unless the topic explicitly asks for them.
- **Hard qualifiers remain hard**: use `--required-term-group` when generic words can satisfy the query independently. Do not show a candidate that fails any required concept group, even when it is recent or highly cited.
- **Abstract mentions are not enough**: use `--required-title-term-group` when the paper must directly study the requested object/task. A downstream application that merely cites the requested data must not enter the shortlist.
- **Structured recommendations only**: Never invent or preserve partial citation strings as recommendations. If a provider returns only author/year, venue, pages, or an ambiguous title fragment, treat it as unresolved metadata, not as a paper candidate.
- **Ranking is discovery-specific**: do not import or duplicate `tools/init_discovery.py`'s scoring helpers. The two skills have different objectives — `/init` wants broad foundational coverage; `/discover` wants relevant *next reads*. See `references/ranking-signals.md`.
- **No-key provider coverage**: OpenAlex is primary for works search. Crossref supplies fallback search, DOI metadata, and deposited references. This is less complete than key-gated citation graphs, but it works without account setup.

## Error Handling

- **All seed channels fail**: report the failure, write no shortlist, and do not log a successful run.
- **No provider returns recommendations for an anchor**: keep going with the remaining anchors; if all anchors return zero, treat as total failure.
- **`--from-wiki` finds no anchorable papers** (`wiki/papers/` empty or paper pages are missing both title and DOI): tell the user the wiki is too sparse for wiki-mode discovery and suggest topic mode.
- **Anchor ID is malformed or unknown**: surface the bad ID in the report and continue with any remaining anchors.

## Dependencies

### Tools

- `uv run python -X utf8 tools/discover.py from-anchors --id <id> [--id <id>...] [--negative <id>...] --wiki-root '@configured' --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `uv run python -X utf8 tools/discover.py from-topic "<query>" [--query-variant "<equivalent-query>"...] [--required-term-group "<term-a|synonym-a>"...] [--required-title-term-group "<term-a|synonym-a>"...] [--since-year <YYYY>] --wiki-root '@configured' --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `uv run python -X utf8 tools/discover.py from-wiki --wiki-root '@configured' --limit <N> --output-checkpoint .checkpoints/ --markdown`
- `uv run python -X utf8 tools/research_wiki.py log '@configured' "<message>"`

### Skills

- `/ingest` — caller via `--discover` flag; also the action the user takes on a chosen candidate
- `/init` — independent planner; does not call `/discover`

### External APIs

- OpenAlex — primary no-key works search, abstracts, citation counts, and provider IDs via `tools/fetch_literature.py`
- Crossref — fallback no-key search, DOI metadata, and best-effort reference lookup via `tools/fetch_literature.py`

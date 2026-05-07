# /discover ranking signals

The deterministic ranking lives in `tools/discover.py` — this file documents what it weighs and **why it differs from `/init`**, so that future edits do not accidentally re-converge the two.

## Anchor-mode candidate channels

Anchor mode gathers from no-key arXiv/Crossref channels per anchor:

- **`recommend`** — approximates related papers by looking up the anchor, extracting title keywords, and searching arXiv/Crossref.
- **`references`** — surfaces older work when Crossref has deposited reference lists for the anchor DOI.
- **`citations`** — currently best-effort and often empty because the no-key providers used here do not expose a full citing-works graph.

Together they provide account-free discovery: topical neighbors plus references where available. Coverage is intentionally lighter than key-gated citation graph services.

## What discovery scores on

Anchor mode (rough weight order):

1. **Aggregate influential citation count** — log-scaled. Reflects the candidate's general prestige. Weighted heavier than raw `citationCount`.
2. **Anchor-influence edge** — provider-specific edge signal when available. The current no-key providers usually do not emit this, so the score mostly comes from overlap, channel diversity, citations, and freshness.
3. **Anchor overlap** — how many anchors surfaced this candidate. Two anchors pointing to the same paper means it sits at their intersection.
4. **Channel diversity** — bonus when the same candidate appears in multiple channels (e.g., both `recommend` and `references`). A paper present in all three is rare and usually central to the anchor's neighborhood.
5. **Freshness** — mild bonus for recent years. Recent ≠ better, so the curve is flat-ish (1.0 / 0.85 / 0.6 / 0.4 / 0.25 across age buckets).
6. **Author h-index** (max across authors) — capped tie-breaker. The list endpoints do not return `authors.hIndex`, so this signal mostly fires for topic-mode candidates that came via the richer single-paper graph API.

Topic / wiki mode: same signals minus anchor overlap and minus the anchor-influence edge (no anchor exists in topic mode; wiki-derived anchors do score the edge signal). Influence and freshness carry more weight to compensate.

### Why keep edge influence in the schema?

`is_influential_edge` stays in the normalized candidate schema so future no-key or user-configured providers can expose edge-specific importance without changing downstream ranking code. Today it is usually false.

## What discovery does **not** score on

This is where `/discover` deliberately differs from `/init`'s planner (`tools/init_discovery.py`):

- **No survey preference**. `/init` favors survey/review papers because a fresh wiki benefits from them as anchor coverage. `/discover` is invoked when a user already knows the area (anchor mode) or is exploring (topic mode); they rarely need yet another survey, and surfacing surveys above novel work would be noise.
- **No "older canonical anchor" bonus**. `/init`'s bootstrap mode promotes one older citation-heavy paper to broaden coverage. `/discover` users typically want forward-looking recommendations, not foundational re-anchoring.
- **No notes/web priority terms**. `/init` reads `raw/notes/` and `raw/web/` to extract the user's stated intent. `/discover` does not — its inputs are explicit (anchor, topic, or wiki state).

If a future ranking signal seems shared between `/init` and `/discover`, prefer keeping two implementations rather than extracting a shared scorer. The objectives genuinely differ; a shared scorer would force one skill to compromise.

## Provider limitations

`tools/fetch_literature.py` deliberately uses no-key providers:

- arXiv supplies preprint search and metadata, but not citation counts.
- Crossref supplies DOI metadata, citation counts when deposited, and references when publishers provide them.
- A full citing-works graph is not available from these no-key paths, so citation expansion is best-effort.

Do not reintroduce a required API key for discovery. If a richer provider is added later, make it optional and preserve the arXiv/Crossref fallback.

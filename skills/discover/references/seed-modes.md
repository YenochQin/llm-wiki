# /discover seed modes

Pick exactly one mode per invocation. The decision is based on what the user (or calling skill) actually said, not on what the wiki contains.

## Anchor mode (`from-anchors`)

Use when the user named one or more specific papers, or when this is a post-`/ingest` `--discover` follow-up.

Triggers:

- "find papers similar to LoRA"
- "what's related to this one I just ingested"
- one or more DOIs, paper titles, or wiki paper slugs in the request
- `/ingest --discover` invocation (anchor = the just-ingested paper's DOI when available, otherwise title)

Anchor mode is the strongest signal channel because the anchor title and identifiers constrain OpenAlex-first works search and Crossref metadata/reference lookup better than a broad topic string.

If the user supplies negatives ("not these", "different from X"), pass them via `--negative`; the tool excludes exact negative IDs when they appear in the candidate set.

## Topic mode (`from-topic`)

Use when the user gave a topic, direction, or set of keywords without naming specific papers.

Triggers:

- "find papers about diffusion model fine-tuning"
- "what's been written on retrieval augmented generation"
- a domain phrase with no anchors

Topic mode runs OpenAlex-first works search with Crossref fallback. It is recent-first by default: use the current year minus 10 as the lower publication bound unless the user supplies `--since-year`. Rank topical coverage and freshness above citation count.

Translate non-English topics into a canonical scholarly English query. For narrow topics whose literature uses several equivalent terms, derive 2–4 scoped variants and pass them through `--query-variant`. For entity families indexed member by member, use up to 12 member-specific variants. Keep the same research object and task in every variant; the variants are retrieval expansions, not permission to broaden into neighboring application areas.

When the topic combines hard qualifiers that are individually common in neighboring fields, derive `--required-term-group` constraints so every candidate must match the research object, requested entity family, and task/observable group separately.

Topic mode is useful for exploration when the user has a domain in mind but no specific paper in hand. `/init` is a different tool — it ingests local user-owned papers into a fresh wiki — so route topic-only requests to `/discover`, not `/init`.

## Wiki mode (`from-wiki`)

Use when the user asked open-ended "what should I read next" with no anchor and no topic.

Triggers:

- "give me the next batch of papers to read"
- "what's a good follow-up to my current wiki"
- explicit `--from-wiki` flag

Wiki mode picks the wiki's most recently modified paper pages, extracts their DOI when available, otherwise title, and uses those values as anchors. This implicitly biases discovery toward whatever the user has been working on lately — usually the desired behavior.

If `wiki/papers/` is empty or paper pages are missing both title and DOI, wiki mode cannot run. Tell the user the wiki is too sparse and suggest topic mode (or `/init`).

## What if the user gave both an anchor and a topic?

Prefer anchor mode. Anchors are a much stronger signal than a topic string. Mention the topic in the user-facing report so they know it was noted, but the discovery itself runs through `from-anchors`.

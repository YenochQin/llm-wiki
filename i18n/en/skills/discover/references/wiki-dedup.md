# /discover wiki dedup

`tools/discover.py` deduplicates candidates against the existing wiki when `--wiki-root @configured` is passed. This document explains what the dedup does and does not catch, so the user-facing report is accurate.

## What it catches

For each candidate, `tools/discover.py` builds an identity key from DOI/provider ID/title and checks whether any existing `wiki/papers/*.md` page has a matching DOI or title in frontmatter. Matches are dropped from the shortlist before scoring; the count is reported as `wiki_dedup_count`.

This catches the typical case: an already-ingested paper bubbles up as a recommendation again. Surfacing such a paper would waste the user's review attention; dropping it is correct.

## What it does not catch

- **No DOI and weak titles**: a paper without a DOI can only be matched by normalized title. If two records use substantially different titles, they may both appear.
- **Cross-source duplicates within the candidate set**: the dedup pass before wiki filtering uses `_candidate_key` (DOI → provider ID → title) which catches most cross-source duplicates. Fully missing IDs and titles are dropped silently.

## What to do with a "high dedup" report

If `wiki_dedup_count` is high relative to `candidates_total` (e.g., 30 / 50), the wiki is already well-covered for these anchors. Two interpretations:

1. The user is looking for breadth and should switch to a different seed (different anchor, broader topic, or `--from-wiki` to explore adjacent papers).
2. The recommendation channel is genuinely saturated — there is little new to recommend in this neighborhood.

The skill should mention high dedup in the user-facing report; do not hide it.

## What dedup does not do

`/discover` never modifies the wiki to "fix" a duplicate. If the candidate's metadata seems richer than what is currently in the wiki, that is a `/edit` or `/check` concern, not a `/discover` concern.

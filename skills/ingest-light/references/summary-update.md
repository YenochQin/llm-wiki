# Target Summary Update

`/ingest-light` uses a Summary page as a writing-purpose container. The default target is:

```text
wiki/Summary/thesis-introduction-literature.md
```

## Existing Summary

Preserve existing prose. Add the light-ingested paper to `## Key references` or to a role subsection.

Preferred role subsections under `## Key references`:

```markdown
### Background

- [[paper-slug]] — one sentence on how it supports the introduction.

### Method foundation

- [[paper-slug]] — one sentence on the method lineage.

### Benchmark

- [[paper-slug]] — one sentence on the benchmark observable/data.

### Application

- [[paper-slug]] — one sentence on the application motivation.

### Gap evidence

- [[paper-slug]] — one sentence on the missing-data or disagreement gap.

### Review context

- [[paper-slug]] — one sentence on the broad framing.
```

If `## Key references` has only bullets, append a new bullet at the end instead of reorganizing the whole section.

## New Summary

If the target Summary does not exist, create:

```yaml
---
title: "Thesis introduction literature map"
scope: "Writing-oriented literature map for dissertation introduction background and citation intake."
key_topics: []
paper_count: 0
date_updated: YYYY-MM-DD
---
```

Required sections:

```markdown
# Thesis introduction literature map

## Overview

## Core areas

## Evolution

## Current frontiers

## Key references

## Related
```

## Metadata

- Increment or recompute `paper_count` as the number of linked `[[paper-slug]]` entries under `## Key references` when practical.
- Update `date_updated`.
- Ensure `[[paper-slug]]` is present somewhere in the Summary unless `--depth paper-only`.

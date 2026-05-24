# Citation Discipline

> 中文运行提示：使用本参考时，请用中文向用户解释结论；技术术语、BibTeX、命令、路径和字段名保持原样。下面保留英文规范作为精确参考。

> Shared reference for all skills that generate citations: /paper-draft, /survey, /paper-plan.
> Every citation in a OmegaWiki output must be **verifiable** — never LLM-generated.

---

## Core Rule

**BibTeX entries must come from authoritative sources, not from LLM memory.**

LLMs hallucinate citation details (wrong year, wrong venue, wrong authors, non-existent papers).
The only acceptable sources for BibTeX are:

1. **DBLP** (`https://dblp.org/`) — primary source for CS venues
2. **CrossRef** (`https://api.crossref.org/`) — primary source for DOI-bearing publications
3. **CrossRef wrapper** (`tools/fetch_literature.py`) — fallback for DOI/title metadata
4. **The paper's own .bib file** — if available in `raw/papers/`

## The [UNCONFIRMED] Protocol

When a BibTeX entry **cannot** be fetched from any authoritative source:

1. Generate a best-effort entry from available information (title, authors, year from wiki page)
2. Prefix the BibTeX key with `UNCONFIRMED_`: `@article{UNCONFIRMED_smith2024attention, ...}`
3. Add a comment: `% [UNCONFIRMED] BibTeX not confirmed from DBLP/CrossRef — manual check required`
4. The `[UNCONFIRMED]` marker is a **hard blocker** for submission — /paper-compile must flag all remaining `[UNCONFIRMED]` entries

## Fetching BibTeX

### DBLP (preferred for CS)

```shell
# Search by title
WebFetch: https://dblp.org/search/publ/api?q={url-encoded-title}&format=json&h=3

# Parse response: .result.hits.hit[].info contains title, authors, venue, year, url
# Get BibTeX: WebFetch the .url field + ".bib" suffix
```

### CrossRef (preferred for DOI)

```shell
# Search by title
WebFetch: https://api.crossref.org/works?query.bibliographic={url-encoded-title}&rows=3

# Parse response: .message.items[] contains title, author, container-title, DOI
# Construct BibTeX from structured data
```

### CrossRef wrapper (fallback for DOI/title lookup)

```shell
# Uses no-key Crossref APIs
python3 tools/fetch_literature.py search "<title>"
# Returns paperId, title, authors, year, venue, externalIds
```

## Citation Key Convention

```
{first-author-lastname}{year}{first-keyword}
```

Examples:
- `hu2022lora` (Hu et al., 2022, "LoRA: Low-Rank Adaptation...")
- `vaswani2017attention` (Vaswani et al., 2017, "Attention Is All You Need")

## Rules for Skills

### /paper-draft
1. After drafting each section, collect all `\cite{}` references
2. For each citation: attempt DBLP → CrossRef → CrossRef wrapper in order
3. Only include entries that are actually cited (`\nocite{*}` is forbidden)
4. Write `references.bib` with fetched entries + [UNCONFIRMED] entries separated at bottom

### /survey
1. Use `[[slug]]` wikilinks during drafting (wiki-internal format)
2. When converting to LaTeX, resolve each `[[slug]]` to a `\cite{key}`
3. The citation key must match a verified BibTeX entry
4. If a wiki paper has no verifiable BibTeX, output `\cite{UNCONFIRMED_slug}` and flag

### /paper-plan
1. In the citation plan, list all wiki papers that will be cited
2. Pre-fetch BibTeX for each planned citation (fail-fast: identify [UNCONFIRMED] entries early)
3. Report citation coverage: how many are verified vs. [UNCONFIRMED]

## What NOT To Do

- **Never** generate BibTeX from memory (wrong venue/year is worse than [UNCONFIRMED])
- **Never** cite a paper not in the wiki (all citations trace back to wiki/papers/)
- **Never** use `\nocite{*}` (every entry must be explicitly cited)
- **Never** silently drop a [UNCONFIRMED] marker (it must survive until human verification or successful fetch)
- **Never** fabricate DOIs or other external IDs

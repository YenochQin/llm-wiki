---
name: api-review
description: Request a review of a wiki page, draft, or pasted research artifact from a configured model API, providing relevant wiki excerpts as evidence. Use when the user asks for an API-based or external model review.
---

# /api-review

Run from the repository root after resolving the wiki alias with
`uv run python -X utf8 tools/resolve_path_alias.py @configured`. Resolve any other
content alias that the user selects for the artifact before reading it.

1. Identify the user's artifact and review focus. Accept a wiki slug, a wiki-relative
   Markdown path, an explicit UTF-8 `.md`, `.txt`, or `.tex` file path, or pasted text.
   An explicit request for API review authorizes sending the artifact and relevant
   excerpts to the configured provider. For narrower sharing instructions, pass
   `--no-linked-context` and select only the authorized pages with `--context`.
2. The tool includes wiki pages linked from the artifact body. Add relevant wiki
   pages with `--context` when there is important unlinked evidence. Match the topic,
   cited papers, or claims against the wiki index and page content. Prefer primary
   evidence, relevant findings, and competing claims. Leave earlier review scores
   and conclusions out of the initial request. Each `--context` takes a wiki slug
   or wiki-relative Markdown path and can be repeated.
3. Pass the focus with `--focus` when the user specifies one. Use `-` as the target
   and pass pasted material on stdin. For a local preview of the input manifest,
   add `--dry-run`. A real call sends the full artifact and up to 24,000 context
   characters total, with up to 6,000 per page and explicit pages first. The result
   records truncated or omitted context and unresolved links. A plain HTTP provider
   must be on loopback. Provider setup is in [the setup guide](../../config/setup-guide.md#optional-api-review).
4. Return the external model's findings and provider/model provenance in the
   conversation. Check cited anchors against the actual review materials before
   presenting a finding as verified. Report missing context and API errors. The
   review writes no wiki pages, reports, or logs.

```bash
uv run python -X utf8 tools/api_review.py claims/example-claim --context papers/example-paper --focus evidence
```

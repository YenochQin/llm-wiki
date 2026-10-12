# Automated Check Coverage

Read this reference when interpreting automated findings or investigating check coverage. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

### Step 2: Structural Completeness (automated coverage)

The automated tool checks:

1. **Broken wikilinks**: `[[slug]]` target file does not exist
2. **Orphan pages**: pages with no incoming links
3. **Missing required fields** (all 9 entity types):
   - papers: title, slug, tags, importance
   - concepts: title, tags, maturity, key_papers
   - topics: title, tags
   - people: name, tags
   - Summary: title, scope, key_topics
   - ideas: title, slug, status, origin, tags, priority
   - experiments: title, slug, status, target_claim, hypothesis, tags
   - claims: title, slug, status, confidence, tags, source_papers, evidence
4. **Concept source grounding**: every concept page has `## Source excerpts`, prepared markdown links under `wiki/sources/papers/`, and at least one blockquoted original fragment
5. **Paper source grounding**: generated paper pages have `## Evidence Pack` entries linked to prepared markdown with exact source excerpts, and the pack meets the coverage floor (a card per populated interpretive section plus per generated concept/claim, not a thin fixed-three pack); `grounding_lint.py` flags thin packs as a `warn`-level `thin-evidence-pack`
6. **Claim source grounding**: claim evidence items include a `source_anchor` or explicit source-anchor marker

### Step 3: Field Value Validation (automated coverage)

1. **Enum value checks**:
   - papers.importance ∈ {1,2,3,4,5}
   - concepts.maturity ∈ {stable, active, emerging, deprecated}
   - ideas.status ∈ {proposed, in_progress, tested, validated, failed}
   - ideas.priority ∈ {1,2,3,4,5}
   - experiments.status ∈ {planned, running, completed, abandoned}
   - experiments.outcome ∈ {succeeded, failed, inconclusive}
   - claims.status ∈ {proposed, weakly_supported, supported, challenged, deprecated}
2. **Claim confidence** ∈ [0.0, 1.0]
3. **Idea failure_reason**: must be non-empty when status=failed (anti-repetition memory)
4. **Experiment target_claim**: the referenced claim must exist

### Step 4: Cross Reference Symmetry (automated coverage)

Check `docs/runtime-support-files.en.md` (§Cross-Reference Rules) for the full bidirectional-link contract:

| Forward link | Reverse link checked |
|----------|---------------|
| concepts.key_papers → papers | papers.Related contains concept link |
| papers → people (wikilink) | people.Key papers contains paper |
| claims.source_papers → papers | papers.Related contains claim link |
| ideas.origin_gaps → claims | claims.Linked ideas contains idea |
| experiments.target_claim → claims | claims.evidence contains experiment |

### Step 5: Graph Edge Consistency (automated coverage)

1. **JSON format validity**: every line is valid JSON
2. **Required fields**: each edge has from, to, type
3. **Edge type validity**: semantic edges use the current endpoint-aware type sets; legacy paper-paper / paper-concept types produce migration warnings
4. **Edge confidence**: `/ingest` paper-paper and paper-concept semantic edges use `confidence: high|medium|low`
5. **Citation layer**: `graph/citations.jsonl` rows use `type: cites`, valid source/date, paper endpoints, and no confidence field
6. **Dangling nodes**: wiki pages referenced by from/to must exist

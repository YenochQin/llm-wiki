# Candidate Generation and Screening

Read this reference when generating candidates or applying first-pass feasibility/novelty screening. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

### Phase 2: Brainstorm and Challenge Alternatives

Goal: generate concrete hypotheses from the landscape, then explore alternative explanations and methods in the current agent. Follow `shared-references/review-protocol.md`.

1. **Generate 6–10 ideas**:
   - Input: landscape report + wiki gaps + weak claims + banlist.
   - Strategies: cross-domain combinations, filling gaps, strengthening weak claims, challenging existing hypotheses, and addressing recorded limitations.
   - Each idea includes: title, hypothesis (1–2 sentences), approach sketch (3–5 sentences), target claims, and estimated feasibility (high/medium/low).

2. **Generate 4–6 alternatives in a challenge pass**:
   - Re-examine the same landscape, gaps, banlist, and active ideas.
   - Question the first pass's assumptions and consider different mechanisms, simpler baselines, and competing explanations.
   - Use the same idea fields and assess feasibility within the user's constraints (default planning horizon: 3–6 months).
   - Label this as another pass by the current agent, not an independent generator. A separate report supplied by the user may contribute additional candidates with its provenance recorded.

3. **Merge and deduplicate**:
   - Combine the initial and alternative candidates (normally 10–16 before deduplication).
   - Merge ideas with the same core method, keeping the more specific version.
   - Remove banlist overlaps and heavy duplication of active ideas.
   - Aim for 8–12 candidates when the landscape supports them; do not invent ideas to meet a quota.

### Phase 3: First-Pass Filter

Goal: quickly eliminate ideas that are clearly infeasible or insufficiently novel.

Apply the following checks to each candidate idea:

1. **Feasibility check**:
   - Are GPU/compute requirements within reasonable range? (reference experiment setups already in the wiki)
   - Data availability (public datasets vs. private data)
   - Implementation complexity (achievable within 3–6 months?)
   - Label as feasibility: high/medium/low

2. **Quick novelty screening** (2–3 web-search queries per idea):
   - `"<idea-core-method>" + "<task>"` exact-match search
   - `<component-1> + <component-2>` component-combination search
   - If a highly similar published work is found → eliminate or flag

3. **Wiki alignment check**:
   - Does the idea address a known gap in the gap_map? (+score)
   - Does the idea target a weakly_supported claim? (+score)
   - Does the idea build on existing wiki knowledge? (+score)

4. **Filter decision**:
   - Eliminate if: feasibility=low AND quick novelty screening found similar published work
   - Eliminate if: highly correlated with a failure_reason in the banlist
   - Retain if: feasibility >= medium AND not eliminated
   - Output: surviving ideas ranked by available evidence; do not invent candidates to meet a count.

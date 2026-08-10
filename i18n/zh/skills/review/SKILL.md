---
name: review
description: Use when the user wants an agent-local independent critique of a research artifact such as an idea, claim, experiment design, or paper draft, with structured scores, concrete fixes, and wiki entity mapping.
argument-hint: <artifact-path-or-slug> [--difficulty standard|hard|adversarial] [--focus method|evidence|writing|completeness]
---

# /review

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> Review any research artifact (idea, proposal, experiment plan, paper draft, claim) using the current agent as the reviewer.
> Outputs a structured score, actionable improvement suggestions, and a mapping to wiki entities
> (which claims need strengthening, which gaps are discovered).
> Supports three difficulty levels (standard / hard / adversarial) and four review focuses.
> To get cross-agent review, run this same skill in another agent/session and compare the reports.
> Can be used standalone or called by /ideate, /refine, /exp-design.

## Inputs

- `artifact`: the artifact to review, one of:
  - slug of a wiki page (e.g. `sparse-lora-for-edge-devices`, searched in ideas/experiments/claims/)
  - file path (e.g. `wiki/outputs/paper-draft-v1.md`)
  - free text (directly pasted proposal or idea description)
- `--difficulty` (optional, default `standard`):
  - `standard`: single-pass review with structured feedback
  - `hard`: two-pass review; after the first pass, re-check the artifact against the strongest likely objections and revise the score if warranted
  - `adversarial`: hard review plus an explicit fatal-flaw search, simulating a skeptical reviewer
- `--focus` (optional, default comprehensive review):
  - `method`: focus on technical correctness, novelty, and feasibility of method design
  - `evidence`: focus on sufficiency of evidence, experimental rigor, claim support
  - `writing`: focus on clarity, structural organization, and argumentative logic
  - `completeness`: focus on missing content (related work, ablations, baselines)

## Outputs

- **Review Report** (output to terminal):
  - Overall Score (1-10)
  - Strengths (list of positives)
  - Weaknesses (list of issues, ranked by severity)
  - Questions (reviewer questions)
  - Actionable Suggestions (improvement suggestions ranked by priority)
  - Wiki Entity Mapping (which claims need strengthening, which gaps were found)
  - Verdict: `ready` / `needs-work` / `major-revision` / `rethink`
- If `--difficulty >= hard`: additionally includes self-challenge history and final revised score
- This skill **does not directly modify the wiki**, but outputs a list of suggested wiki updates

## Wiki Interaction

### Reads
- `wiki/papers/*.md` — locate papers cited by the artifact, verify citation accuracy
- `wiki/concepts/*.md` — understand technical concepts involved in the artifact
- `wiki/claims/*.md` — check the current status and confidence of claims the artifact depends on
- `wiki/experiments/*.md` — find related experiment results
- `wiki/ideas/*.md` — if reviewing an idea, check its context
- `wiki/graph/context_brief.md` — global context
- `wiki/graph/open_questions.md` — check completeness against the gap map

### Writes
- **None**. Review is a read-only query operation.
  - Review results are output to terminal; the user or caller (e.g. /refine) decides whether to apply them.

### Graph edges created
- **None**.

## Workflow

**Precondition**: confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`).

### Step 1: Load Context

1. **Parse artifact**:
   - If slug: search sequentially in `wiki/ideas/`, `wiki/experiments/`, `wiki/claims/`, `wiki/papers/`, `wiki/outputs/` for `{slug}.md`
   - If file path: read directly
   - If free text: use directly
2. **Determine artifact type**: idea / experiment / claim / paper-draft / proposal / other
3. **Load relevant wiki context**:
   - Read `wiki/graph/context_brief.md` for global perspective
   - Read `wiki/graph/open_questions.md` for knowledge gap list
   - Load relevant wiki pages by artifact type:
     - idea → its origin_gaps claims, related papers
     - experiment → its target_claim, related experiments
     - claim → its evidence sources, related papers and experiments
     - paper-draft → all wiki pages it cites
4. **Adopt reviewer stance**:
   - Treat the artifact as if it came from another researcher.
   - Do not defend the artifact by default, even if the current agent helped create it earlier.
   - Separate evidence-backed critique from speculation.
   - Prefer specific, falsifiable criticism over vague taste judgments.
   - When evidence is missing from the wiki context, label it as uncertainty rather than inventing support.
5. **Build the review rubric** (based on --focus):

   **Base rubric (all focuses):**

   Be thorough, specific, and constructive. For every weakness, suggest a concrete fix.
   Score on a 1-10 scale where:

   - 1-3: Fundamental flaws, not salvageable in current form
   - 4-5: Significant issues but core idea may have merit
   - 6-7: Solid work with clear areas for improvement
   - 8-9: Strong work, minor issues only
   - 10: Exceptional, publication-ready

   **Focus-specific additions:**
   - `method`: additionally assess technical correctness, novelty of approach, feasibility, comparison to alternatives
   - `evidence`: additionally assess experimental rigor, statistical significance, claim-evidence alignment, missing controls
   - `writing`: additionally assess clarity, logical flow, notation consistency, figure quality, related work coverage
   - `completeness`: additionally assess missing baselines, missing ablations, missing datasets, missing related work, reproducibility

   **Adversarial addition (adversarial mode only):**
   Additionally: actively search for fatal flaws. A fatal flaw is anything that,
   if true, would make the entire contribution invalid (incorrect proof, data leakage,
   unfair comparison, published prior work). If you find one, flag it clearly.

### Step 2: Agent-Local Review

Perform the review directly in the current agent. Do not call Review LLM, MCP review tools, or any external reviewer.

Produce an initial assessment containing:

1. **Strengths** (3-5 bullet points)
2. **Weaknesses** (ranked by severity, each with a concrete suggestion to fix)
3. **Questions** (things that are unclear or need clarification)
4. **Score** (1-10 with one-sentence justification)
5. **Verdict**: ready / needs-work / major-revision / rethink
6. **Claim-level feedback**: For each claim referenced in the artifact, assess whether the evidence is sufficient. List any claims that need stronger support.
7. **Knowledge gaps identified**: Any open questions or missing knowledge that would strengthen this work.

### Step 3: Self-Challenge Pass (hard / adversarial mode)

Skip this step if `--difficulty` is `standard`.

For `hard` and `adversarial`, run one additional self-challenge pass:

1. Re-read the artifact and the initial weaknesses.
2. Ask what a skeptical reviewer would say was still under-argued, under-tested, unclear, or unsupported.
3. Classify each challenge:
   - **Confirmed weakness**: the critique is valid → keep it and strengthen the fix.
   - **Uncertain risk**: the critique may be valid but needs more evidence → add it as a question or knowledge gap.
   - **Rejected objection**: the critique is answered by the artifact or wiki context → mention briefly only if it affects the final score.
4. Revise the score only if the self-challenge materially changes the assessment.

For `adversarial`, add a fatal-flaw scan:

- Look for data leakage, unfair comparison, incorrect proof, missing baseline that invalidates the main claim, published prior work that removes novelty, impossible assumptions, or claim-evidence mismatch.
- If a fatal flaw is plausible but not proven from available context, label it as `potential fatal flaw` and state what evidence would decide it.
- If no fatal flaw is found, say so explicitly and list the highest residual risk.

### Step 4: Structured Output

Synthesize Step 2 + Step 3 results into a structured Review Report:

```markdown
# Review Report: {artifact title}

## Meta
- **Artifact type**: {idea / experiment / claim / paper-draft / proposal}
- **Difficulty**: {standard / hard / adversarial}
- **Focus**: {method / evidence / writing / completeness / comprehensive}
- **Reviewer**: current agent
- **Review mode**: agent-local; rerun in another agent/session for cross-agent comparison
- **Passes**: {1 for standard, 2 for hard/adversarial}

## Score: {final score}/10 — {verdict}

| Verdict | Meaning |
|---------|---------|
| ready | Ready to use or submit directly |
| needs-work | Clear improvement points; usable after fixes |
| major-revision | Core sections need significant revision |
| rethink | Fundamental direction may be flawed; reconsider |

## Strengths
1. {strength 1}
2. {strength 2}
...

## Weaknesses (by severity)

### Critical
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Major
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

### Minor
- {weakness}: {specific description} → **Fix**: {specific fix suggestion}

## Questions
1. {question}
...

## Wiki Entity Mapping

### Claims needing stronger support
| Claim | Current confidence | Issue | Suggested action |
|-------|-------------------|-------|------------------|
| [[claim-slug]] | 0.6 | Evidence is indirect | Run targeted experiment |

### Knowledge gaps identified
| Gap | Related to | Suggested action |
|-----|-----------|------------------|
| {description} | [[slug]] | /ingest, /exp-design (then run externally), or /ask |

### Suggested wiki updates
- `wiki/claims/{slug}.md`: update confidence, add evidence note
- `wiki/ideas/{slug}.md`: add risk factor from review
- `wiki/graph/open_questions.md`: will be updated on next rebuild

## Self-Challenge History (hard/adversarial only)

### Initial Review
{summary of initial assessment}

### Self-Challenge
{confirmed weaknesses / uncertain risks / rejected objections}

## Actionable Items (ranked)
1. [CRITICAL] {action item}
2. [MAJOR] {action item}
3. [MINOR] {action item}
```

## Constraints

- **Agent-local only**: do not call Review LLM, MCP review tools, web search, or external services unless the user explicitly asks for external verification.
- **Reviewer independence**: adopt an independent reviewer stance; do not defend prior work by default, and distinguish evidence-backed critique from uncertainty.
- **Do not modify wiki**: review only outputs suggestions; it does not directly modify any wiki pages. Wiki modifications are handled by the caller (e.g. /refine)
- **Scores must have justification**: scores without a rationale are not accepted
- **Weaknesses must have fixes**: every weakness must include a specific, actionable fix suggestion; vague criticism is not accepted
- **Claim-level mapping is required**: output must include the Wiki Entity Mapping section, mapping review findings to specific wiki entities
- **Adversarial mode must search for fatal flaws**: e.g. fully published identical work, incorrect proofs, data leakage
- **Cross-agent comparison is user-driven**: if the user wants multiple independent reviews, tell them to run `/review` in separate agents/sessions and compare reports; this skill itself performs only the current agent's review.
- **Use [[slug]] when referencing wiki pages**: all references to wiki pages use wikilink syntax

## Error Handling

- **Artifact not found**: prompt user to check slug or path, list likely candidate pages
- **Wiki empty**: proceed with review normally, but annotate Wiki Entity Mapping section with "wiki empty, no entity mapping available"
- **Artifact too long**: review section by section, then merge the section reviews into one final report.
- **Insufficient context**: list the missing wiki pages, source evidence, or experiment results as questions or knowledge gaps; do not invent support.
- **Current agent previously authored the artifact**: explicitly note this as a bias risk in `## Meta`, then continue with the independent reviewer stance.

## Dependencies

### Tools
- No direct tool calls (review does not require deterministic tools)

### MCP Servers
- None. This skill is intentionally agent-local.

### Native file tools
- Read files to load the artifact and relevant wiki pages.
- Search files to find the wiki page corresponding to the artifact.

### Called by
- `/ideate` Phase 4 (review top ideas)
- `/refine` each iteration round (review current version)
- `/exp-design --review` (review experiment plan)

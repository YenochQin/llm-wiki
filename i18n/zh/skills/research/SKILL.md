---
description: End-to-end research orchestrator (design-only) — idea discovery → experiment design → user runs experiments externally → /exp-eval on returned results → paper plan + draft. No experiment execution, no paper compilation.
argument-hint: <research-direction-or-brief> [--auto] [--start-from stage1|stage2|stage3-eval|stage4|stage5] [--skip-paper] [--venue ICLR|NeurIPS|ICML|ACL|CVPR]
---

# /research

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。下面保留英文规范作为精确操作说明。

> End-to-end research orchestrator that composes the design-side skills into a complete research workflow.
> **This wiki does not execute experiments**. After `/exp-design` produces a plan, the user runs the experiments externally (their own GPUs, notebooks, or mathematical analysis) and reports the results back; `/research` then resumes with `/exp-eval` to fold the results into claims, and (optionally) into a paper.
>
> **Stages**: 0 Bootstrap → 1 Idea Discovery → Gate 1 → 2 Experiment Design → **HUMAN RUN** → 3 Verdict (`--start-from stage3-eval`) → Gate 2 → 4 Paper Plan + Draft.
> Every Gate and Stage saves progress to `wiki/outputs/pipeline-progress.md`, supporting cross-session recovery.
>
> `--auto` mode skips manual confirmation (automatically selects the top-1 idea and continues past Gate 2). `--skip-paper` runs the workflow without writing a paper.

## Inputs

- `direction`: research direction description or path to a `RESEARCH_BRIEF.md` file
  - Text form: one-sentence description of the research direction (e.g. "sparse LoRA for edge devices")
  - File form: structured RESEARCH_BRIEF.md (containing domain, constraints, target venues)
- `--auto` (optional): non-interactive mode; Gate 1 auto-selects top-1 idea, Gate 2 auto-continues
- `--start-from <stage>` (optional): resume execution from the specified stage
  - Valid values: `stage1`, `stage2`, `stage3-eval`, `stage4`
  - `stage3-eval` is the resume point after the user has run experiments externally and is ready to feed the results in
  - Requires `wiki/outputs/pipeline-progress.md` to exist
- `--skip-paper` (optional): run only Stages 0–3 (skip Stage 4 paper writing). `/exp-eval` still runs in Stage 3.
- `--venue` (optional): target conference (ICLR / NeurIPS / ICML / ACL / CVPR), passed to `/paper-plan`

## Outputs

- **Wiki updates** (delegated to sub-skills): ideas/, experiments/, claims/, outputs/, graph/
- **wiki/outputs/pipeline-progress.md** — pipeline progress snapshot (for recovery)
- **wiki/outputs/PIPELINE_REPORT.md** — full pipeline report
- **paper/ directory** (if not `--skip-paper`) — paper plan + draft (`.tex` / `.md`); the user runs the LaTeX compile pipeline themselves
- **wiki/log.md** — log appended after each stage

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — global context (passed to sub-skills)
- `wiki/graph/open_questions.md` — knowledge gaps (passed to /ideate)
- `wiki/ideas/*.md` — Gate 1 selection, Stage 3 verdict
- `wiki/experiments/*.md` — Stage 2-3 experiment plan + results
- `wiki/claims/*.md` — Stage 3 verdict, Stage 4 paper planning
- `wiki/outputs/pipeline-progress.md` — `--start-from` state recovery
- `wiki/papers/*.md` — Stage 4 paper writing context

### Writes
- `wiki/outputs/pipeline-progress.md` — save progress at each Gate
- `wiki/outputs/PIPELINE_REPORT.md` — final report
- `wiki/log.md` — append log entries
- All other wiki entity writes are delegated to sub-skills

### Graph edges created
- None directly — all graph edges are delegated to sub-skills (`/ideate`, `/exp-design`, `/exp-eval`)

## Workflow

**Precondition**:
1. Confirm working directory is the wiki project root (containing `wiki/`, `raw/`, `tools/`)
2. If `--start-from` is specified, read `wiki/outputs/pipeline-progress.md` to restore state

Resolve the Python interpreter once (uv-based, falls back to system `python3` only if `.venv` is missing):

```bash
if   [ -x .venv/bin/python ];         then PYTHON_BIN=.venv/bin/python
elif [ -x .venv/Scripts/python.exe ]; then PYTHON_BIN=.venv/Scripts/python.exe
else                                       PYTHON_BIN=python3
fi
export PYTHON_BIN
```

### Step 0: Initialize

1. **Parse input**:
   - If file path: read RESEARCH_BRIEF.md, extract direction, domain, constraints, target_venue
   - If text: use as direction; leave domain/constraints blank
   - Generate slug: `"$PYTHON_BIN" tools/research_wiki.py slug "{direction}"`

2. **Auto-recovery detection** (when `--start-from` is not specified):
   - If `wiki/outputs/pipeline-progress.md` exists and `status == running`:
     - Read direction, current_stage, started, slug
     - Use AskUserQuestion to prompt the user:
       ```
       Unfinished pipeline detected:
       Direction: {direction}
       Current stage: {current_stage}
       Started: {started}

       [1] Resume from {current_stage} (recommended)
       [2] Start a new pipeline (will overwrite old progress)
       ```
     - If `--auto` or user selects [1]: auto-set `--start-from {current_stage}`, continue
     - If user selects [2]: continue creating a new pipeline (overwrite old progress)

3. **Check recovery** (when `--start-from` is specified):
   - If progress file exists: restore idea_slug, experiment_slugs, claim_slugs and jump to specified stage
   - If progress file missing: report error and exit

4. **Create progress file** `wiki/outputs/pipeline-progress.md`:
   ```yaml
   ---
   slug: "{pipeline-slug}"
   direction: "{research direction}"
   status: running
   current_stage: stage1
   started: YYYY-MM-DD
   mode: auto|interactive
   skip_paper: true|false
   venue: "{venue}"
   idea_slug: ""
   experiment_slugs: []
   claim_slugs: []
   iteration_count: 0
   ---
   ## Stage Log
   - Stage 0 (Bootstrap): skipped
   - Stage 1 (Idea Discovery): pending
   - Gate 1: pending
   - Stage 2 (Experiment Design): pending
   - **HUMAN RUN (external)**: pending
   - Stage 3 (Verdict): pending
   - Gate 2: pending
   - Stage 4 (Paper Plan + Draft): pending
   ```

5. **Append log**:
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py log wiki/ \
     "research | started | direction: {direction} | mode: {auto|interactive}"
   ```

6. **Snapshot wiki state** (for Growth Report in Step Final):
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py maturity wiki/ --json
   ```
   Save returned JSON as `maturity_before`.

### Stage 0: Bootstrap (auto-triggered when wiki is empty)

**Trigger condition**: run `"$PYTHON_BIN" tools/research_wiki.py maturity wiki/ --json`. If `level == "cold"` and `papers < 3`: enter Bootstrap. Otherwise skip and proceed to Stage 1.

1. **Initialize wiki** (if not yet initialized):
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py init wiki/
   ```

2. **Search for relevant papers**:
   - Literature lookup: `"$PYTHON_BIN" tools/fetch_literature.py search "{direction}" --limit 20`

3. **Merge, rank, and select top 5**:
   - Deduplicate by arxiv_id
   - Ranking priority: available citation count > recency > relevance score
   - Select top 5

4. **Auto-ingest each paper** via the `/ingest` skill (PDFs route through MinerU automatically).

5. **Rebuild derived data**:
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py rebuild-context-brief wiki/
   "$PYTHON_BIN" tools/research_wiki.py rebuild-open-questions wiki/
   ```

6. **Log + update progress**:
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py log wiki/ \
     "research | stage0-bootstrap | auto-ingested {N} papers | maturity: {level}"
   "$PYTHON_BIN" tools/research_wiki.py set-meta \
     wiki/outputs/pipeline-progress.md current_stage stage1
   ```

### Stage 1: Idea Discovery

Call `/ideate`:

```
Skill: ideate
Args: "{direction}" --domain {domain}
```

**After completion**:
1. Read the generated ideas, sorted by priority
2. Update pipeline-progress: Stage 1 → completed, record generated idea slugs
3. Append log

### Gate 1: Select Idea

**If `--auto` mode**: select the highest-priority idea automatically.

**If interactive mode**:
- List all generated ideas (slug, title, priority, novelty score)
- Use AskUserQuestion to prompt user to select one idea (or enter "stop")

**Save progress**:
- Update pipeline-progress: Gate 1 → passed, record `idea_slug`
- Update selected idea status: proposed → in_progress

### Stage 2: Experiment Design

Call `/exp-design`:

```
Skill: exp-design
Args: "{idea_slug}" --review
```

**After completion**:
1. Read generated experiment slugs (pages in `wiki/experiments/` where `linked_idea == idea_slug`)
2. Update pipeline-progress: Stage 2 → completed, record `experiment_slugs`
3. Set `current_stage: stage3-eval` (so the next session resumes at the verdict step)
4. Append log:
   ```bash
   "$PYTHON_BIN" tools/research_wiki.py log wiki/ \
     "research | stage2 | designed {N} experiments | pipeline: {slug}"
   ```

5. **End the session here.** Output the handoff message:

```
Stage 2 complete: {N} experiment plans written.

Each experiment page in wiki/experiments/{slug}.md describes:
  • Hypothesis and target claim
  • Methodology / setup
  • Success criteria + expected effect size
  • Required resources

NEXT STEP — RUN THE EXPERIMENTS YOURSELF:
  Read each experiment page, run the analysis or training as described,
  and record the results in your own notes.

WHEN YOU HAVE RESULTS:
  Resume by appending the results to each experiment's `## Results` section
  (or by passing them through chat in the next session), then run:

      /research --start-from stage3-eval

  /exp-eval will fold your results into the linked claims and produce a
  verdict. From there, /research continues into Stage 4 (paper plan + draft).

Progress saved to wiki/outputs/pipeline-progress.md.
```

This is the orchestrator's deliberate hand-off. **Do not invoke any execution-side tooling**; experiment runs happen outside the wiki entirely.

### Stage 3: Verdict (entry point: `--start-from stage3-eval`)

This stage assumes the user has already run the experiments and made the results available — either by editing the experiment pages directly, or by reporting them in chat for the orchestrator to record.

1. **Verify each experiment page has results** before invoking `/exp-eval`. For each `experiment_slug`:
   - read `wiki/experiments/{slug}.md`
   - confirm a `## Results` section is present and non-trivial
   - if missing, ask the user to provide results (do not fabricate or skip)

2. **Call `/exp-eval` per experiment**:
   ```
   Skill: exp-eval
   Args: "{experiment_slug}" --auto
   ```

3. **Evaluate whether claims are sufficient**:
   - **Claims sufficient** (primary claim confidence ≥ 0.7 and status is `supported` or `weakly_supported`) → proceed to Gate 2
   - **Claims insufficient** (confidence < 0.4 or status is `challenged`) → enter iteration

4. **Iteration path** (claims insufficient, up to 1 retry):
   - Analyze the cause
   - Call `/refine` to revise the experiment plan:
     ```
     Skill: refine
     Args: "{experiment_plan_slug}" --max-rounds 2 --focus evidence
     ```
   - Hand back to the user for another **HUMAN RUN** of the revised experiments
   - Maximum 2 iterations total

5. **After completion**:
   - Update pipeline-progress: Stage 3 → completed, record `claim_slugs`
   - Append log

### Gate 2: Confirm Paper Ready

**If `--skip-paper`**: skip Gate 2 and Stage 4; proceed directly to Step Final.

**If `--auto` mode**: continue automatically.

**If interactive mode**:
- Display claim status summary:
  ```
  Claim: {slug} | Status: {status} | Confidence: {confidence}
  Evidence: {count} sources ({strong}/{moderate}/{weak})
  ```
- Use AskUserQuestion: ready for paper / need more experiments / stop here
- "need more experiments" → return to Stage 2 for replanning (and another HUMAN RUN)
- "stop here" → save progress, generate final report (no paper)

### Stage 4: Paper Plan + Draft (no compile)

Call sub-skills in sequence: `/paper-plan` → `/paper-draft` → `/refine`. Compilation (LaTeX → PDF) is **not** part of this wiki — once the draft is written, the user takes the `paper/` directory and compiles it themselves with their own toolchain.

**4a. Call `/paper-plan`**:
```
Skill: paper-plan
Args: "{claim_slugs}" --venue {venue}
```

**4b. Call `/paper-draft`**:
```
Skill: paper-draft
Args: "wiki/outputs/PAPER_PLAN.md" --review
```

**4c. Call `/refine` on paper draft**:
```
Skill: refine
Args: "paper/main.tex" --max-rounds 3 --target-score 8 --focus writing
```

**After completion**:
- Update pipeline-progress: Stage 4 → completed, status: completed
- Print: "Paper draft ready at paper/. Compile with your own LaTeX toolchain."

### Step Final: Pipeline Report

Generate `wiki/outputs/PIPELINE_REPORT.md`:

```markdown
# Research Pipeline Report

## Stage Summary
| Stage | Status | Duration |
|-------|--------|----------|
| Stage 0: Bootstrap | completed/skipped | ... |
| Stage 1: Idea Discovery | completed | ... |
| Gate 1: Idea Selection | passed | ... |
| Stage 2: Experiment Design | completed | ... |
| HUMAN RUN: external execution | completed | ... |
| Stage 3: Verdict | completed | ... |
| Gate 2: Paper Ready | passed | ... |
| Stage 4: Paper Plan + Draft | completed | ... |

## Selected Idea
- **Idea**: [[{idea_slug}]] — {idea title}
- **Priority**: {N}
- **Novelty score**: {score}

## Claims Trail
| Claim | Initial Status | Final Status | Confidence (proposed → supported) |
|-------|---------------|-------------|-----------------------------------|
| [[{slug}]] | proposed | supported | 0.3 → 0.8 |

## Experiment Results (reported by user)
| Experiment | Outcome | Key Result |
|-----------|---------|------------|
| [[{slug}]] | succeeded | {result} |

## Iteration History
- Total iterations: {N}
- Reason for iteration: {claims insufficient / ...}

## Deliverables
- Ideas: +{N} created
- Experiments: +{N} planned, {N} evaluated
- Claims: {N} updated
- Graph edges: +{N}
- Paper draft: paper/main.tex (if applicable; user compiles externally)

## Wiki Growth (pipeline total)
| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Papers | {N} | {N} | +{N} |
| Claims | {N} | {N} | +{N} |
| Ideas | {N} | {N} | +{N} |
| Experiments | {N} | {N} | +{N} |
| Edges | {N} | {N} | +{N} |
| Maturity | {level} | {level} | {status} |
(Diff `maturity_before` from Step 0 against a fresh `maturity --json` here. Only show rows where delta ≠ 0.)

## Next Steps
- {recommendations based on remaining gaps or unresolved issues}
```

Append log:
```bash
"$PYTHON_BIN" tools/research_wiki.py log wiki/ \
  "research | completed | idea: {slug} | claims: {N} updated | paper: {yes/no}"
```

Update pipeline-progress: status: completed.

## Constraints

- **Design-only orchestrator**: this skill never executes experiments. After Stage 2 it hands off to the user; after the user reports results it resumes at Stage 3. Do not invoke any execution-side tooling — those skills are not present in this wiki.
- **No paper compilation**: Stage 4 stops at the draft. The user runs LaTeX externally.
- **Orchestrator does not directly modify wiki entities**: all wiki modifications are delegated to sub-skills (`/ingest`, `/ideate`, `/exp-design`, `/exp-eval`, `/refine`, `/paper-plan`, `/paper-draft`).
- **Gates and Stages must save progress**: every Gate and Stage saves `pipeline-progress.md` when completed.
- **Maximum 2 iterations** at Stage 3 to prevent infinite loops.
- **`--auto` does not skip computation**: it skips human confirmation, not analytical steps.
- **`--skip-paper` still runs Stage 3 `/exp-eval`**: claim updates must be completed even when not writing a paper.
- **Pass sub-skill parameters through**: correctly forward `domain`, `--venue`, etc. to sub-skills.
- **Log every Stage** in `log.md`.
- **Do not re-run completed stages**: `--start-from` skips already-completed stages.
- **Auto-recovery first**: if no `--start-from` is given and an unfinished pipeline exists, prompt the user to resume.
- **Hand-off after Stage 2 is mandatory**: do not invent results, do not auto-skip the user. Always end the session there and require an explicit `--start-from stage3-eval` to resume.

## Error Handling

- **pipeline-progress missing but `--start-from` specified**: report error; prompt user to run the full pipeline first.
- **pipeline-progress corrupted**: attempt to infer progress from current wiki state (read ideas/experiments/claims statuses), recover to the nearest Gate.
- **Sub-skill call fails**: record error to pipeline-progress, report the failed stage, suggest `--start-from` to resume.
- **All ideas generation fails**: terminate; suggest the user adjust the research direction.
- **Stage 2 produces no experiments**: terminate; ask `/exp-design` to retry with a tighter idea slug.
- **Stage 3 invoked but experiment pages have no `## Results`**: pause and ask the user to fill in results. Do not call `/exp-eval` against empty results.
- **Stage 3 verdict produces no claim updates**: surface the issue; suggest the user revise the experiment write-up.
- **Gate user selects stop**: save progress; generate partial report.
- **RESEARCH_BRIEF.md malformed**: fall back to plain-text direction; ignore structured fields.
- **Wiki empty (no papers/concepts)**: auto-trigger Stage 0 Bootstrap.
- **Claims still insufficient after iteration**: annotate report with "claims insufficient after max iterations"; let the user decide whether to continue.

## Dependencies

### Skills (via Skill tool)
- `/ingest` — Stage 0 Bootstrap auto-ingest (PDFs route through MinerU automatically)
- `/ideate` — Stage 1 idea discovery
- `/exp-design` — Stage 2 experiment design (terminal step in this wiki's planning side)
- `/exp-eval` — Stage 3 verdict on user-reported results
- `/refine` — Stage 3 iteration + Stage 4 paper improvement
- `/paper-plan` — Stage 4 paper planning
- `/paper-draft` — Stage 4 paper writing

### Tools (via Bash)
- `"$PYTHON_BIN" tools/research_wiki.py slug "{title}"` — generate pipeline slug
- `"$PYTHON_BIN" tools/research_wiki.py set-meta <path> <field> <value>` — update pipeline-progress fields
- `"$PYTHON_BIN" tools/research_wiki.py log wiki/ "<message>"` — append log entry
- `"$PYTHON_BIN" tools/research_wiki.py maturity wiki/ --json` — wiki maturity (Stage 0 trigger + Growth Report)
- `"$PYTHON_BIN" tools/research_wiki.py init wiki/` — initialize wiki structure (Stage 0)
- `"$PYTHON_BIN" tools/fetch_literature.py search "{query}" --limit 20` — no-key literature search (Stage 0)

### Claude Code Native
- `Read` — read pipeline-progress, wiki pages, RESEARCH_BRIEF
- `Write` — write pipeline-progress, PIPELINE_REPORT
- `Glob` — find experiments, ideas, claims
- `Skill` — call sub-skills (core capability)
- `AskUserQuestion` — user interaction at Gates and auto-recovery detection

---
name: code-analyze
description: Analyze public source-code repositories as executable processing systems. Use when the user wants to reconstruct how code runs, computes, transforms data, and produces outputs; explain an end-to-end execution or processing flow; formalize each processing stage with LaTeX; or comprehensively investigate a user-specified implementation direction. Do not perform general security, performance, maintainability, or test-coverage auditing unless the user explicitly requests that direction.
---

# /code-analyze

Analyze code to recover its actual execution and processing model. Treat the repository as a
pipeline of transformations rather than as a target for general code review. Read source code as
the primary evidence, trace the runnable path first, then explain every substantive processing
stage in both implementation language and LaTeX.

Keep the target code read-only. Do not patch it unless the user separately requests an
implementation change.

## Inputs

Accept a repository path, subdirectory, file, or natural-language question about code. If the
target is omitted, use the current repository.

- With no specific analysis direction, reconstruct the principal end-to-end run from external
  input to final output.
- With a specific direction, make that direction the analysis objective and investigate it
  comprehensively. Trace enough upstream and downstream context to explain it correctly, but do
  not broaden the report into unrelated audit categories.
- With `--write`, archive the report as
  `outputs/code-analysis-{slug}-{date}.md` under the configured wiki root.
- With `--crystallize`, first write the report, then create or update research entities only when
  the findings are durable research knowledge.

Do not infer omitted user-facing flags from repository state.

## Default Scope

Focus on:

- how execution is started;
- how inputs are parsed, represented, and routed;
- which functions, modules, stages, or kernels perform each transformation;
- how intermediate data, shapes, state, parameters, and units change;
- how branching, iteration, aggregation, persistence, and external calls affect the result;
- how outputs are constructed and returned or stored;
- how the complete process can be expressed mathematically.

Do not analyze security, privacy, performance, maintainability, style, or test coverage by
default. Discuss one of these only when the user explicitly makes it the analysis direction, and
then analyze that direction across the relevant execution flow rather than appending a generic
checklist.

## Wiki Interaction

### Reads

Read wiki material only when the user asks to connect the implementation to research knowledge:

- `wiki/graph/context_brief.md`
- `wiki/index.md`
- directly relevant pages under `papers/`, `concepts/`, `claims/`, `ideas/`, and `experiments/`

### Writes

- Write nothing by default.
- With `--write`, create one report under `outputs/`, update the index only if it indexes outputs,
  and append a log entry through `tools/research_wiki.py log`.
- With `--crystallize`, create or edit only grounded `concepts/`, `claims/`, `ideas/`, or
  `experiments/` pages and maintain required reverse links.
- Create graph edges only through `tools/research_wiki.py`; never edit `wiki/graph/` manually.

## Workflow

When writing to the wiki, run from the llm-wiki repository root and verify the configured wiki:

```bash
uv run python -X utf8 tools/research_wiki.py stats @configured --json >/dev/null
```

### Step 1: Fix the Analysis Objective

1. Resolve the target path and the user's requested direction.
2. State one concrete objective, such as “reconstruct the inference pipeline from input records to
   predictions” or “explain how the solver updates the state at each iteration.”
3. If the user supplied no direction, select the principal documented run path. If several runs
   are equally central, list them and analyze the one best supported by entrypoints and docs;
   explicitly note the scope choice.
4. Record the repository root, branch, short commit, and dirty status when Git metadata is
   available.
5. Skip `.env`, keys, tokens, credential stores, and private local databases.

### Step 2: Locate the Runnable Path

Use `rg --files` first. Exclude generated, vendored, dependency, cache, and build directories
unless they implement the requested processing stage.

Inspect only evidence needed to recover execution:

- README usage commands and examples;
- manifests and runtime configuration;
- CLI, server, application, notebook, or script entrypoints;
- argument/config parsers and object construction;
- core functions, modules, models, operators, and data structures reached from the entrypoint;
- output writers, serializers, callbacks, and persistence boundaries;
- tests or examples only when they clarify intended execution semantics.

Build a concrete call path from the external trigger to the result. Do not stop at a directory
map or import graph.

### Step 3: Reconstruct the Processing Stages

Partition the run into ordered stages $T_1, T_2, \ldots, T_n$. For every stage, record:

1. its entry and exit code locations;
2. input symbols, types, shapes, units, and relevant state;
3. the exact operation performed;
4. output symbols, types, shapes, units, and state changes;
5. conditions, branches, loops, randomness, persistence, or external calls;
6. the next consumer of the output.

Separate orchestration from substantive transformations. Follow indirect dispatch, registries,
factories, callbacks, or configuration-selected implementations far enough to identify the
concrete path. When runtime selection prevents a single answer, describe each supported branch
and the selection condition.

Ground every important conclusion in source files and line references. Mark facts inferred only
from names, docs, or incomplete paths as uncertain.

### Step 4: Formalize Every Stage with LaTeX

Define symbols before using them. Start with the global pipeline:

$$
x_0 \xrightarrow{T_1} x_1 \xrightarrow{T_2} \cdots
\xrightarrow{T_n} x_n,
\qquad
x_n = (T_n \circ T_{n-1} \circ \cdots \circ T_1)(x_0).
$$

Then give at least one meaningful LaTeX expression for every substantive processing stage. Match
the expression to the code semantics:

- transformation: $x_i = T_i(x_{i-1}; \theta_i)$;
- branch: $x_i = \begin{cases}T_i^{(a)}(x_{i-1}), & c(x_{i-1}) \\ T_i^{(b)}(x_{i-1}), & \text{otherwise}\end{cases}$;
- iteration: $s_{k+1} = F(s_k, u_k)$;
- aggregation: $z = \sum_{j=1}^{m} w_j h_j$ or the exact implemented reducer;
- normalization: write the implemented denominator, axes, constants, and epsilon explicitly;
- optimization: state the implemented objective and update rule separately;
- stochastic processing: state the distribution or sampling rule only when present in code;
- reshape, indexing, filtering, or concatenation: specify shape and index mappings;
- I/O or orchestration with no numerical computation: use a typed mapping or state transition,
  such as $(s_{k+1}, o_k) = T(s_k, i_k)$.

Do not invent an algorithm, objective, probability model, variable meaning, or equation that the
code does not support. If a stage cannot be reduced to a useful numeric formula, formalize its
mapping, predicate, or state transition and explain the limitation.

### Step 5: Check the Reconstructed Flow

Cross-check the proposed flow against at least two available evidence surfaces, such as:

- entrypoint and downstream implementation;
- README example and argument parser;
- producer and consumer of an intermediate value;
- implementation and a focused test or example;
- logged/output schema and the code that constructs it.

Run only safe, local, non-mutating commands when they materially resolve an ambiguity and existing
dependencies are already available. Do not install dependencies, download data, make network
calls, or execute an untrusted public repository merely to complete the analysis. If execution is
not safe or available, perform static tracing and state that limitation.

### Step 6: Produce the Report

Use this structure unless the user requests another shape:

```markdown
# Code Process Analysis: {target}

## Scope and Objective

## Entry Point and End-to-End Summary

## Global Processing Model

## Stage-by-Stage Analysis

### Stage 1: {name}
- Code:
- Input:
- Processing:
- Output:
- Formula:
- Formula-to-code correspondence:

## Branches, Iteration, and State

## Final Output Construction

## Uncertainties and Unresolved Paths

## Research Wiki Mapping
```

For every stage, place the implementation explanation beside its formula so the correspondence is
auditable. After the stage analysis, include the composed end-to-end formula and explain which
code component implements each operator. Use `$...$` for inline math and `$$...$$` for display
math in both wiki files and user-facing output.

Keep quotations short. Prefer precise paraphrases with line-specific file references. Do not add
generic risk or test-gap sections outside the user's chosen direction.

### Step 7: Archive (`--write` only)

1. Generate the slug:

   ```bash
   uv run python -X utf8 tools/research_wiki.py slug "code process analysis {target-name}"
   ```

2. Resolve the configured wiki root before direct edits:

   ```bash
   uv run python -X utf8 tools/resolve_path_alias.py @configured
   ```

3. Create `outputs/code-analysis-{slug}-{date}.md` with `artifact_type: code_analysis`, the
   objective, target, date, cited wiki pages, and repository path/branch/commit/dirty metadata.
4. Update `index.md` only if the current index lists outputs.
5. Append the log through the tool:

   ```bash
   uv run python -X utf8 tools/research_wiki.py log @configured "code-analyze | {target} | objective: {objective} | output: outputs/{slug}.md"
   ```

6. Add useful `derived_from` edges for cited wiki pages through `research_wiki.py add-edge`.

### Step 8: Crystallize (`--crystallize` only)

Crystallize only durable research knowledge, such as an implemented algorithmic mechanism, a
verifiable claim embodied by the computation, a runnable evaluation, or a research gap revealed
by the processing design.

Before creating or editing pages, open `docs/runtime-page-templates.en.md`. Keep forward and
reverse links synchronized. Explain code provenance explicitly and do not fabricate paper
citations for code-grounded concepts.

## Constraints

- Keep source repositories read-only by default.
- Analyze execution and processing rather than performing a general code audit.
- Follow the user's explicit analysis direction comprehensively and exclude unrelated categories.
- Make every important claim traceable to code, documentation, commands, or existing wiki pages.
- Provide a LaTeX model for every substantive stage and an end-to-end composition.
- Never manufacture equations to conceal missing implementation evidence.
- Respect dirty worktrees and never revert user changes.
- Do not expose secrets or install dependencies by default.
- Write to the wiki only with `--write` or `--crystallize`.

## Error Handling

- **Target not found**: report the missing path and list nearby candidates.
- **Target too large**: prioritize documented entrypoints, the selected run, and reachable core
  stages; report sampling boundaries.
- **Several valid run paths**: enumerate them, state which path was selected, and explain why.
- **Dynamic dispatch unresolved**: show the selection mechanism and candidate implementations;
  do not pretend one branch is certain.
- **Formula underdetermined**: give the strongest supported mapping or state transition and mark
  missing semantics explicitly.
- **Execution unavailable or unsafe**: use static tracing and report the verification limitation.
- **Wiki not initialized**: still return the analysis, skip archival, and recommend `/init`.
- **Path outside readable scope**: request an accessible path or permission.

## Dependencies

- `rg` / `rg --files` for source discovery
- `git` for repository snapshots
- `uv run python -X utf8 tools/research_wiki.py` for slug, log, and graph operations
- `uv run python -X utf8 tools/resolve_path_alias.py` before direct writes to configured paths

Optional follow-ups: use `/review` to critique an archived analysis, `/edit` for approved wiki
changes, and `/check` after crystallizing wiki entities.

---
description: Analyze a codebase and produce architecture, flow, risk, and research-wiki mapping reports; optionally archive the report to wiki/outputs
argument-hint: "<code-path-or-question> [--mode architecture|flow|risk|tests|onboarding|research] [--write] [--crystallize]"
---

# /code-analyze

> 中文运行提示：除非用户特别要求英文输出，执行本 skill 时请用中文向用户汇报；命令、路径、YAML 字段、slug、frontmatter key、工具参数和 wikilink 语法保持原样。代码标识符、文件路径和命令保持原样。

> Analyze source code as a knowledge object. This skill reads a repository or subdirectory,
> maps architecture and execution flows, identifies risks and test gaps, and connects findings
> to the research wiki when relevant. It is for understanding and knowledge capture, not for
> making code changes unless the user explicitly asks for a follow-up edit.

## Trigger

User manual: `/code-analyze <code-path-or-question> [...]`

Use this skill when the user asks to understand, audit, explain, map, or summarize a codebase,
especially when the result should become reusable wiki knowledge.

## Inputs

- `code-path-or-question`: one of:
  - a repository or subdirectory path
  - a file path
  - a natural-language question about code in the current workspace
- `--mode` optional:
  - `architecture`: module map, dependencies, boundaries, entrypoints
  - `flow`: execution path, data flow, state transitions
  - `risk`: bugs, security/privacy issues, operational hazards, maintainability risks
  - `tests`: coverage surface, missing tests, test strategy
  - `onboarding`: reader-friendly code tour and mental model
  - `research`: map code to methods, claims, experiments, datasets, or papers in the wiki
- `--write` optional: archive the analysis as `wiki/outputs/code-analysis-{slug}-{date}.md`
- `--crystallize` optional: after writing an output, also propose or create wiki entities only when the finding clearly belongs in `concepts/`, `claims/`, `ideas/`, or `experiments/`

If `--mode` is omitted, infer the primary mode from the user request and state the choice.
If the target path is omitted, analyze the current repository.

## Outputs

- **Always**: a concise analysis report to the user with file references and uncertainty notes
- **If `--write`**:
  - `wiki/outputs/code-analysis-{slug}-{date}.md` — archived analysis report
  - `wiki/index.md` — updated if outputs are indexed in the current wiki
  - `wiki/log/` — append-only entry via `tools/research_wiki.py log`
  - `wiki/graph/edges.jsonl` — only if the report cites existing wiki pages and `derived_from` edges are useful
- **If `--crystallize`**:
  - suggested or created `concepts/`, `claims/`, `ideas/`, or `experiments/` pages, with required reverse links

## Wiki Interaction

### Reads
- `wiki/graph/context_brief.md` — only for `research` mode or when mapping code findings to existing wiki knowledge
- `wiki/index.md` — locate relevant existing pages
- `wiki/papers/*.md`, `wiki/concepts/*.md`, `wiki/claims/*.md`, `wiki/ideas/*.md`, `wiki/experiments/*.md` — only pages directly relevant to the code finding

### Writes
- None by default
- With `--write`: create one report under `wiki/outputs/`
- With `--crystallize`: create or edit wiki pages only after the finding is grounded and the user requested crystallization

### Graph edges created
- `outputs/code-analysis-* -> cited wiki page`: `derived_from`
- Claim/idea/experiment edges only when `--crystallize` creates those entities, following the global cross-reference rules

## Workflow

**Pre-condition**: run from the llm-wiki repository root when writing to the wiki. Use `uv run python` for llm-wiki tools. Never hard-code `wiki/` or `raw/`; use runtime path aliases such as `@configured`, and resolve aliases before direct file editing.

```bash
uv run python tools/research_wiki.py stats @configured --json >/dev/null
```

### Step 1: Establish Scope

1. Resolve the target:
   - explicit path -> analyze that path
   - file path -> analyze the file plus its direct callers/callees when discoverable
   - question only -> infer target from current repository and the question
2. Record repository snapshot when available:
   - `git rev-parse --show-toplevel`
   - `git branch --show-current`
   - `git rev-parse --short HEAD`
   - `git status --short`
3. Treat target code as read-only unless the user explicitly requests implementation changes.
4. Do not read secrets or private credentials. Skip `.env`, key files, tokens, local databases, and credential stores unless the user explicitly asks and the content is necessary.

### Step 2: Inventory the Codebase

Prefer fast local inspection:

```bash
rg --files <target>
```

Exclude generated or vendor-heavy directories unless they are the target:
- `.git/`
- `node_modules/`
- `.venv/`, `venv/`
- `__pycache__/`
- `.next/`, `dist/`, `build/`
- `target/`
- coverage artifacts and lockfile caches

Read only the files needed for the selected mode:
- project docs: `README*`, `docs/`, `AGENTS.md`, `CLAUDE.md`
- manifests: `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `build.gradle`, `requirements*.txt`
- entrypoints: CLI files, server/app files, notebooks or scripts named by docs
- tests and CI: `tests/`, `test_*`, `*.test.*`, `.github/workflows/`, CI config
- core modules suggested by names, imports, route registration, config wiring, or user question

### Step 3: Analyze by Mode

For all modes, ground claims in actual files and line references when possible.

**architecture**
- Identify entrypoints, core modules, ownership boundaries, data models, external services, and dependency direction.
- Note places where boundaries are implicit or circular.

**flow**
- Trace the requested workflow from input to output.
- Include parsing, validation, state mutation, persistence, network calls, error paths, and side effects.

**risk**
- Prioritize correctness bugs, unsafe assumptions, security/privacy issues, data loss risks, concurrency hazards, and brittle operational behavior.
- Separate confirmed issues from hypotheses that need runtime verification.

**tests**
- Map existing tests to behavior.
- Identify missing unit, integration, regression, fixture, and end-to-end coverage.
- Prefer focused test proposals tied to concrete code paths.

**onboarding**
- Produce a compact mental model: what to read first, what each major directory does, where changes usually land, and what invariants matter.

**research**
- Map implementation choices to wiki entities:
  - algorithms or mechanisms -> `concepts/`
  - empirical assertions -> `claims/`
  - runnable evaluations -> `experiments/`
  - future directions or gaps -> `ideas/`
  - associated papers -> `papers/`
- Only cite existing wiki pages with valid `[[slug]]` wikilinks.

### Step 4: Produce the Report

Use this structure unless the user asked for a different shape:

```markdown
# Code Analysis: {target}

## Scope
- Target:
- Mode:
- Snapshot:
- Files inspected:

## Executive Summary

## Architecture / Flow / Findings

## Risks and Unknowns

## Test and Verification Gaps

## Wiki Mapping

## Recommended Next Actions
```

Rules:
- Keep code quotations short; prefer paraphrase plus file references.
- Mark uncertainty explicitly when a conclusion is inferred from naming or incomplete context.
- Use line-specific local file references in the user-facing answer when available.
- If the report includes formulas, use `$...$` for inline math and `$$...$$` for display math.

### Step 5: Archive to Wiki (`--write` only)

1. Generate a slug:

   ```bash
   uv run python tools/research_wiki.py slug "code analysis {target-name} {mode}"
   ```

2. Resolve the configured wiki root before direct file writes:

   ```bash
   uv run python tools/resolve_path_alias.py @configured
   ```

3. Create `outputs/code-analysis-{slug}-{date}.md` with frontmatter:

   ```yaml
   ---
   title: "Code Analysis: {target}"
   slug: "code-analysis-{slug}-{date}"
   artifact_type: code_analysis
   target: "{target}"
   mode: "{mode}"
   date_created: YYYY-MM-DD
   source_pages: []
   source_repositories:
     - path: "{repo-or-target-path}"
       branch: "{branch-or-unknown}"
       commit: "{commit-or-unknown}"
       dirty: true
   ---
   ```

4. Add `source_pages` for cited existing wiki pages.
5. If the current `index.md` lists outputs, add the new output entry there.
6. Append the log entry through the tool:

   ```bash
   uv run python tools/research_wiki.py log @configured "code-analyze | {target} | mode: {mode} | output: outputs/{slug}.md"
   ```

7. If wiki pages were cited, add `derived_from` edges through `tools/research_wiki.py add-edge`. Do not hand-edit `wiki/graph/`.

### Step 6: Crystallize (`--crystallize` only)

Only crystallize when the report contains durable research knowledge, not ordinary project notes.

Good crystallization candidates:
- a reusable implementation concept not already captured in `concepts/`
- a verifiable claim about performance, correctness, reliability, or method behavior
- an experiment implied by a test harness or benchmark script
- a failed or promising research idea discovered from code gaps

When creating or editing pages:
- Open `docs/runtime-page-templates.en.md` before writing structure or YAML.
- Keep forward and reverse links synchronized.
- Do not create new page types for code repositories unless the global runtime spec has been updated.
- For concepts grounded in code rather than papers, explain provenance clearly and avoid fake paper citations.

## Constraints

- **Read-only by default**: this skill analyzes code; it does not patch source code unless the user separately asks for implementation.
- **No secret exposure**: do not print secrets, tokens, private keys, or local credentials.
- **No dependency installation by default**: do not run package installs or network-dependent setup unless the user approves or explicitly asks.
- **No generated/vendor deep dives by default**: avoid spending context on generated, vendored, or dependency code.
- **Evidence-first**: every important finding should point to inspected files, commands, or existing wiki pages.
- **Respect dirty worktrees**: do not revert or overwrite user changes discovered during analysis.
- **Graph only via tools**: never manually edit `wiki/graph/`.
- **Wiki writes are opt-in**: without `--write` or `--crystallize`, report only.

## Error Handling

- **Target not found**: report the missing path and list nearby candidates from the current directory.
- **Target too large**: sample by manifest, entrypoints, imports, and tests; report sampling limits.
- **Language/tooling unknown**: fall back to file inventory, manifests, and textual dependency tracing.
- **Tests cannot run**: report why and provide manual verification steps.
- **Wiki not initialized**: still produce terminal analysis; skip `--write` and tell the user to run `/init`.
- **Path outside readable scope**: ask the user for an accessible path or permission path, rather than guessing.

## Dependencies

### Tools
- `rg` / `rg --files` — primary code discovery
- `git` — repository snapshot when available
- `uv run python tools/research_wiki.py` — slug, log, graph operations
- `uv run python tools/resolve_path_alias.py` — resolve `@configured` before direct file writes

### Optional Follow-ups
- `/review` — independently review a generated code-analysis report
- `/edit` — apply approved wiki edits after analysis
- `/check` — validate wiki health after crystallization

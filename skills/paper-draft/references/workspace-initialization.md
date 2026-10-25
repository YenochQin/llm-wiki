# Manuscript Workspace Initialization

Read this reference before any manuscript workspace selection or write, including revisions and forks. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

1. Read PAPER_PLAN.md; extract venue (which may be `unspecified`), title, research modes, actual section list, evidence dependencies, and verified/provisional format rules. Resolve the configured external roots:
   ```shell
   uv run python -X utf8 tools/resolve_path_alias.py '@configured' '@paper-root' --json
   ```
   `paper_root` is configured per platform in `config/paths.json`, with optional `LLM_WIKI_PAPER_ROOT` override. It must be outside the code repository and separate from `wiki_root` and `raw_root`. Missing or invalid configuration is an error; never fall back to repository-local `paper/`, `papers/`, or `artifacts/`.
2. Select the research topic and manuscript version:
   - `paper-id` is a stable, undated topic slug. Use the user-supplied id unchanged; otherwise reuse the topic of the selected manuscript or derive an undated lowercase ASCII slug from the research topic/title. For a plan filename, remove the `paper-plan-` prefix, extension, and date component before deriving a topic id. If the topic cannot be identified, ask for an id. Maximum length: 96 characters.
   - `draft-id` identifies one manuscript version. Its format is `YYYY-MM-DD-<purpose-slug>` with a valid calendar date and a lowercase ASCII slug (maximum 120 characters). Use the user-supplied id unchanged. For a new draft without an id, use the user's local calendar date plus a short name describing the draft; if it collides, add `-v2`, `-v3`, etc. rather than overwriting.
   - For routine revisions to a selected/open manuscript, retain its topic, draft directory, and source filename, including standalone `paper.tex`. Do not create a replacement `main.tex` merely to fit the example layout. A legacy one-level bundle is migrated into the two-level layout with filenames and historical evidence preserved.
   - For a requested major restructuring, alternative narrative, or separately evaluated version, create a sibling draft under the same topic. Use `tools/paper_workspace.py fork <paper-id> <source-draft-id> <new-draft-id>` to copy an existing bundle, or `create <paper-id> <draft-id>` for a fresh draft. Both refuse existing destinations. Preserve the source version and edit/evaluate only the new copy. The fork's `draft.json` records its parent; copied evidence remains inherited evidence, not a newly executed experiment.
   - Resolve a selected draft with `tools/paper_workspace.py resolve <paper-id> <draft-id>`; list all drafts or one topic with `list [<paper-id>]`. Use the returned absolute `draft_dir` as `PAPER_DIR`; `paper_dir` is the topic's parent directory. These are documentation names, not literal directory names.
3. Use the two-level layout:
   ```text
   <paper_root>/
   ├── rmcdhf-radial-research/            # stable research topic
   │   ├── 2026-10-06-rmcdhf-research/    # initial manuscript version
   │   │   ├── paper.tex
   │   │   ├── draft.json
   │   │   ├── figures/
   │   │   ├── evidence/
   │   │   ├── reviews/
   │   │   └── history/
   │   └── 2026-10-06-structure-v2/       # separate structural alternative
   │       ├── paper.tex
   │       └── reviews/
   └── another-research-topic/
       └── 2026-10-06-initial-draft/
   ```
   Each manuscript version owns its LaTeX, bibliography, figure sources, tables, evidence, supporting scripts, review notes, and build outputs. Minor edit backups stay in that version's `history/`; major revisions use a new sibling draft. Record the parent version, reason for restructuring, and evaluation scope in the new draft's `revision-notes.md`; save its evaluations under its own `reviews/`. Never generate these files in the code repository. Record the absolute original plan path in the bundle README; plans remain under `@output-root` and logs under the configured wiki root.
4. Use an existing explicitly identified venue template when available; a venue display name is not automatically a filesystem path. Otherwise use a generic article class and mark the format provisional. Do not fabricate page limits or anonymity rules for an unspecified/unverified venue.
5. For a new split-file manuscript, generate `math_commands.tex` (preserve the existing structure when revising):
   - Collect all Formal notation from wiki/concepts/
   - Unify symbol definitions (vectors, matrices, sets, common operators)
6. For a new split-file manuscript, generate a `main.tex` skeleton and section files from the actual PAPER_PLAN section list. Replace the section-list comment below with one `\input{sections/<section-id>}` per selected section in plan order; create only those files. Do not introduce an Experiments section for a theory/computation plan. Revisions edit the existing source in place instead:
   ```latex
   \documentclass{article} % replace with venue template
   \input{math_commands}
   % packages
   \usepackage{booktabs,graphicx,amsmath,hyperref}

   \title{<title>}
   \author{} % author placeholder; follow confirmed venue identity requirements

   \begin{document}
   \maketitle
   \begin{abstract}
   % generated in Step 3
   \end{abstract}
   % Insert the actual selected PAPER_PLAN section inputs here, in order.
   \bibliography{references}
   \bibliographystyle{plain} % replace with venue-required style
   % Include a planned appendix consistently with verified rules; mark placement provisional when rules are unknown.
   \end{document}
   ```

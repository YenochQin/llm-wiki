# Manuscript Draft Delivery Report

Read this reference when reporting the saved manuscript and its actual verification state. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

4. Print to terminal:
   ```markdown
   # Paper Write Complete

   ## Files
   - PAPER_DIR/main.tex (master file)
   - PAPER_DIR/sections/ ({N} section files)
   - PAPER_DIR/figures/ ({M} figure files)
   - PAPER_DIR/references.bib ({K} entries, {V_count} [UNCONFIRMED])
   - PAPER_DIR/math_commands.tex

   ## Status
   - Sections written: {list}
   - De-AI polish: applied
   - Per-section review: {enabled/disabled by --review}
   - Full-paper review: {score and verdict}; scope: {full draft / selected sections}; mode: {agent-local / self-review}
   - [UNCONFIRMED] citations: {count} (resolve before submission)

   ## Next Steps
   - Resolve [UNCONFIRMED] citations manually
   - Run `/refine <absolute-selected-source-path> --focus writing` for further polish
   - Compilation is separate from drafting. Respect a draft-only/no-compilation request; any later compilation outputs stay inside this manuscript workspace or OS temporary storage
   ```

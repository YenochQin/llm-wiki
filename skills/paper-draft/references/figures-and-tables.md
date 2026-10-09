# Manuscript Figures and Tables

Read this reference when generating a figure or table requested by the selected plan sections. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

For each entry in the Figure Plan from PAPER_PLAN:

1. **Diagram type** (architecture diagrams, etc.):
   - Use TikZ or pgfplots to generate native LaTeX figures
   - If too complex: generate a matplotlib Python script → output PDF
   - Save to `PAPER_DIR/figures/{figure-name}.pdf`

2. **Plot type** (recorded calculation or observation charts):
   - Use the actual data sources identified in the plan, including calculation reports/data files or `wiki/experiments/{slug}.md`; record provenance. Plot rendering does not authorize new research calculations/experiments or filling missing data.
   - Generate matplotlib script (following figure design standards in academic-writing):
     - Colorblind-safe palette
     - Font size >= 8pt
     - Error bars / confidence bands only when relevant actual estimates are supplied; never fabricate uncertainty for deterministic results
     - Clear legend
   - Execute script to generate PDF:
     ```shell
     uv run python -X utf8 "<absolute-paper-dir>/figures/plot_{name}.py"
     ```
   - Save to `PAPER_DIR/figures/{figure-name}.pdf`

3. **Table type**:
   - Use booktabs style (toprule, midrule, bottomrule)
   - Highlight best/second-best only for justified comparisons; preserve units, scope, and actual uncertainty
   - Embed directly in section .tex file (small tables) or standalone `PAPER_DIR/tables/{name}.tex` (large tables)

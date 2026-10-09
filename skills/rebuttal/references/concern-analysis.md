# Review Concern Analysis

Read this reference when parsing comments, assigning concern IDs, and mapping concerns to claims/evidence. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

### Step 1: Parse Review Comments

1. **Read review text**:
   - If file path(s): read all specified files
   - If direct text: use directly
   - Merge multiple reviewers' comments, annotated by source (Reviewer 1/2/3/Meta)

2. **Identify structure**:
   - Extract each reviewer's: overall score (Accept/Reject/Borderline), confidence, summary, Strengths, Weaknesses, questions
   - If the format is non-standard (plain text), use LLM to parse into structured format

3. **Output**: structured comments for each reviewer

### Step 2: Atomize Concerns

Split each weakness and question into independent atomic concerns:

1. **Splitting rules**:
   - A single weakness may be a compound sentence containing multiple independent concerns ("the method lacks ablation experiments and also does not compare with X" → split into 2 concerns)
   - Assign each atomic concern an ID in `Rvx-Cy` format (Rv1-C1 = Reviewer 1, Concern 1; Rv1-C2 = Reviewer 1, Concern 2)
   - Retain reviewer number to ensure traceability back to the original comment

2. **Classify each concern**:
   - **evidence**: factual questions about experimental data or result interpretation
   - **method**: methodological questions about method design or algorithmic correctness
   - **missing**: missing experiments/analysis/comparisons/citations
   - **clarity**: unclear expression, symbol confusion, figure issues
   - **scope**: insufficient contribution, applicability questions
   - **novelty**: overlap with existing work, insufficient innovation
   - **minor**: formatting, typos, and other small issues

3. **Assess severity**: critical / major / minor

4. **Output**: atomized concern list, each containing {id (Rvx-Cy), reviewer, type, severity, text}

### Step 3: Map Concerns to Wiki Claims

For each concern:

1. **Find associated claim**:
   - Extract keywords from concern text
   - Search `wiki/claims/*.md` for matching claims
   - Read `wiki/graph/edges.jsonl` to find claim-experiment relationships
   - If no direct match is found: annotate as "unmapped" (no direct claim correspondence)

2. **Check Evidence Status**:
   - Read the claim's evidence list
   - Count strong/moderate/weak evidence
   - Find results of associated experiments
   - **Judgment**:
     - Sufficient: strong >= 1 or moderate >= 2
     - Partial: evidence exists but insufficient strength
     - Insufficient: no evidence or only weak evidence
     - Contradicted: evidence of invalidates type exists

3. **Output**:

| Concern ID | Reviewer | Type | Severity | Claim mapped | Evidence Status | Strategy |
|------------|----------|------|----------|--------------|-----------------|----------|
| Rv1-C1 | R1 | method | critical | [[claim-slug]] | sufficient | A |
| Rv1-C2 | R1 | missing | major | [[claim-slug]] | insufficient | B |
| Rv2-C1 | R2 | novelty | major | unmapped | — | D |

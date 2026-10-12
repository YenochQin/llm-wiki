# Thematic Related Work Writing

Read this reference when grouping selected papers and drafting/polishing the thematic paragraphs. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

### Step 3: Thematic Grouping

Following the Related Work rules in `shared-references/academic-writing.md`:

1. **Group by research direction** (not paper-by-paper listing):
   - Extract natural groupings from wiki/topics/ and concepts/ classifications
   - 3–8 papers per group
   - Group headings describe research directions (e.g. "Parameter-Efficient Fine-Tuning"), not individual papers
2. **Determine group order**:
   - Broad to specific (major direction → sub-direction → most related methods)
   - Or chronological (foundational → development → recent)
3. **Determine within-group order**:
   - Ascending by year (show progression)
   - Important papers: 2–3 sentences; secondary papers: 1 sentence
4. **Annotate each group's relationship to this work**:
   - End each group with one sentence: "Unlike these approaches, our method..." or "We build upon X by..."

### Step 4: Generate Paragraphs

Following `shared-references/academic-writing.md`:

1. **One or two paragraphs per group**:
   - Opening: background and importance of the direction
   - Body: expand on each paper's contribution in within-group order
   - Closing: positioning relative to this work (required)

2. **Citation format**:
   - `--format latex`: `\cite{key}`, key generated from citation-verification.md naming rules
   - `--format markdown`: `[[slug]]`

3. **Writing standards**:
   - No flat lists ("X did Y. Z did W.")
   - Each paragraph has a topic sentence
   - Use contrastive connectives ("While X focuses on..., Y addresses...")
   - No AI-signature vocabulary (see de-AI list in academic-writing.md)

4. **De-AI polish**:
   - Scan and replace AI-signature vocabulary
   - Vary sentence openings
   - Remove filler sentences

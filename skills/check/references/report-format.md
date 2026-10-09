# Check Report Format

Read this reference when producing the user-facing lint report. Paths and commands below are relative to the llm-wiki repository root unless an external root is explicitly named.

Output sorted by priority:

```
## Lint Report — YYYY-MM-DD

**Summary**: N 🔴, M 🟡, K 🔵

### 🔴 Fix Immediately
1. [file] — {issue description}

### 🟡 Recommended Fixes
1. [file] — {issue description}

### 🔵 Optional Improvements
1. [file] — {issue description}
```

Classification:
- **🔴 Fix Immediately**: broken links, missing required fields, invalid enum values, failed idea without failure_reason, invalid JSON in edges, confidence out of range
- **🟡 Recommended Fixes**: xref asymmetry, dangling graph edges, broken claim references, unknown edge types
- **🔵 Optional Improvements**: orphan pages, quality suggestions, empty sections

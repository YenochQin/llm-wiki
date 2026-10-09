# Paper Plan Figures and Tables

Read this reference when specifying figures or tables that help the selected evidence-backed argument. A paper may legitimately need no figures or tables; do not add them to meet a quota.

Choose items by purpose, for example:

| Direction | Possible item | Evidence needed |
|-----------|---------------|-----------------|
| theory | Assumption/dependency schematic, geometrical illustration, limiting-case table | Actual formulation, derivation, or proved result; label a schematic as non-measurement |
| computation | Calculated observable table, parameter dependence, convergence or error plot | Identified calculation output, settings, units, and actual error estimates where applicable |
| experiment | Observation plot, measurement table, instrument/protocol schematic | Identified measurement records, conditions, calibration and actual uncertainty where applicable |
| mixed | Comparison linking predictions and observations | Both actual sources and matching definitions/conditions |

For each selected item, record:

```markdown
### {Figure/Table id}: {argument-specific title}
- Purpose/claim: {which point this item supports}
- Type: {diagram, plot, table, or other justified form}
- Source: {actual existing source links and section/table/equation or data-file location}
- Content: {quantities/relations; axes, units, rows/columns, or labels}
- Validity/uncertainty: {scope and actual error information, or not applicable with a reason}
- Missing inputs: {specific gap or none}
- Presentation: {encoding and approximate size, respecting verified venue rules}
```

Do not invent data, error bands, best-result rankings, or comparison baselines. Architecture diagrams, ablations, and scaling curves apply only to claims that need them. Missing data remains a planned item with an explicit dependency. Planning specifies the item; it does not run new calculations or experiments, generate purported results, or compile LaTeX.

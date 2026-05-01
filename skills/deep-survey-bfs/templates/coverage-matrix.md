# Coverage Matrix — <survey-id>

Generated: `<YYYY-MM-DDThh:mmZ>` after Round `<N>`.

## Cell Map

| Sub-question | theory | experiment | survey | critical-review | dataset |
|---|---|---|---|---|---|
| SQ1 | P001, P004 | P004 | — | — | — |
| SQ2 | — | P002, P003 | — | — | P010 |

> Cell content: comma-separated ★★★ paper IDs. Inactive cells shown as `—`.

## Status Per Cell

| Sub-question | Dimension | Cell state | Target | Search strategy |
|---|---|---|---|---|
| SQ1 | survey | gap | <what's missing> | <search strategy> |
| SQ2 | critical-review | weak | one paper, single lab | citation BFS from P002 |

## Bias Audit

| Bucket | Distribution (★★★ subset) | Threshold | Status |
|---|---|---|---|
| Institution | top: <name>=<count>/<total> | 60% | clean / triggered |
| Country | top: <name>=<count>/<total> | 60% | clean / triggered |
| Year | top: <year>=<count>/<total> | 60% | clean / triggered |
| Method route | top: <route>=<count>/<total> | 60% | clean / triggered |

## Round N Task List

For each `gap` and `weak` cell, and each bias trigger:

```
- [ ] R<N>: <target> via <search_strategy>
```

## Audit Decision

- [ ] All active cells `closed` or accepted-`weak`
- [ ] Bias audit clean or accepted with documented limitation
- [ ] Each cell's ★★★ papers come from ≥2 distinct labs

If all three checked → `audit-passed`. Else → `audit-needs-roundN`.

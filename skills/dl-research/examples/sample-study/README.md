# sample-study: Batch Size Noise (Reference Run)

**Skill version:** dl-research 1.0.0  
**Coverage:** ledger schema, H/E identity, research graph (JSON + Mermaid), validate_ledger.py gate

## Scope

Minimal two-experiment study (`sample-batch-noise`) investigating whether larger
batch sizes reduce gradient noise and improve convergence on CIFAR-10. Covers
phases `frame` through `evaluate`; synthesis deliberately omitted to show an
in-progress state.

## Artifacts

| File | Purpose |
|---|---|
| `runs.jsonl` | Two valid ledger rows (H1.E1 baseline, H1.E2 treatment). Both pass `validate_ledger.py`. |
| `research_graph.json` | Graph stub matching the JSON schema in `templates/research-graph.schema.json`. |
| `research_graph.mmd` | Mermaid rendering of the same graph; must stay consistent with the JSON. |

## Smoke Test

```bash
python3 scripts/validate_ledger.py examples/sample-study/runs.jsonl
# expected: ok: examples/sample-study/runs.jsonl
```

Run from the `skills/dl-research/` directory. Exit 0 confirms the ledger rows
satisfy all required fields, allowed enum values, and type constraints defined
in `validate_ledger.py`.

## Key Schema Points Illustrated

- `experiment_id` uses dotted H/E form (`H1.E1`, `H1.E2`) for a multi-route study.
- `track_id` (`H1`), `slug` (`H1E1-baseline`), and `parent_id` are populated for H/E rows.
- `verdict` and `decision` are set on completed rows; null is valid for in-flight rows.
- `metric_value` is a finite float; `design_deviation` is boolean.

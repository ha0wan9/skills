---
template_name: orchestration-contract
description: "Seed for a committed, reviewable orchestration contract: per-task model tier, parallelization, orchestrator effort, human checkpoints, review level, and a non-predictive budget hint. Signed ahead of a run, then emitted to the engine."
source_reference: references/orchestration-contract.md
intended_project_path: docs/plans/<milestone>-orchestration-contract.md
owner: shared-user-facing
review_policy: re-review when the build plan or any task tier/checkpoint/review-level changes
---

# Orchestration Contract Template

Use this seed when `/orchestrate` turns a chosen milestone into a run. Fill it, **deliver it for
operator review**, then **sign** it (all sign-off boxes) before any engine emission. Schema owner:
[`references/orchestration-contract.md`](../references/orchestration-contract.md) — bind to its fields,
do not redefine them. See [`examples/sample-orchestration-contract.md`](../examples/sample-orchestration-contract.md)
for a filled, signed instance.

## Instantiated-artifact frontmatter

```yaml
---
artifact_name: <milestone>-orchestration-contract
instantiated_from: orchestration/templates/orchestration-contract.md
source_reference: orchestration/references/orchestration-contract.md
project_scope: this repo only
owner: shared-user-facing
review_policy: re-review when the build plan or any task tier/checkpoint/review-level changes
last_reviewed: YYYY-MM-DD
status: draft            # draft | signed
orchestrates_plan: docs/plans/<milestone>-build-plan.md
---
```

## Body

```markdown
# Orchestration Contract — <milestone>

**Orchestrates:** `<build plan>` — milestone `<vX>`. Policy signed ahead of the run; the engine
([engine-handoff.md]) is the mechanism. AP-COORD-7.

## Per-task contract
One row per task in the build plan's build order. `budget_hint` = the tier:class:fanout line.

| Task (plan id) | model_tier | parallelization | orchestrator_effort | human_checkpoint | review_level | budget_hint |
|---|---|---|---|---|---|---|
| <task — ITEM> | sonnet | serial | medium | none | L1 | sonnet:edit:1 |
| <task — ITEM> | opus | serial | high | both | L2 | opus:plan:1 |
| <task — ITEM> | cli | serial | low | none | L0 | cli:lint:1 |

## Budget hint (non-predictive — "estimate, not a guarantee")
    python3 skills/orchestration/scripts/budget_hint.py --task sonnet:edit:1 --task opus:plan:1 --task cli:lint:1
- low: <n> · expected: <n> · high: <n> tokens — coarse heuristic, NOT a forecast, NOT the engine budget.

## Human checkpoints (🔴)
Every before/after/both checkpoint as an explicit stop-and-log point.

## Sign-off  (status: signed only when ALL hold)
- [ ] every build-order task has a row
- [ ] review levels set; escalations stated with reason
- [ ] human checkpoints enumerated
- [ ] budget hint computed + reviewed
- [ ] delivered for operator review
```

Emission to the engine happens **after** signing, **only** on the user's `orchestrate` invocation.

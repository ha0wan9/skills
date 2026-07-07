---
artifact_name: project-board-v0.3-orchestration-contract
instantiated_from: orchestration/templates/orchestration-contract.md
source_reference: orchestration/references/orchestration-contract.md
project_scope: this repo only
owner: shared-user-facing
review_policy: re-review when the build plan or any task tier/checkpoint/review-level changes
last_reviewed: 2026-06-06
status: signed
orchestrates_plan: docs/plans/project-board-v0.3-build-plan.md
---

# Orchestration Contract — Project Board v0.3 (example)

> A worked, **signed** example: how `/orchestrate` would run the v0.3 build plan's Wave 2 (the
> project-meta mirror + edit-back). Policy signed ahead of the run; the engine
> ([`engine-handoff.md`](../references/engine-handoff.md)) is the mechanism. AP-COORD-7. Schema owner:
> [`references/orchestration-contract.md`](../references/orchestration-contract.md).

**Orchestrates:** `docs/plans/project-board-v0.3-build-plan.md` — milestone `v0.3`, Wave 2.

## Per-task contract

| Task (plan id) | model_tier | parallelization | orchestrator_effort | human_checkpoint | review_level | budget_hint |
|---|---|---|---|---|---|---|
| DASH-03 Linear mirror reference + dry-run path | sonnet | serial | medium | none | L1 | sonnet:edit:1 |
| DASH-13 dashboard edit-back (FS Access API + fallback) | sonnet | serial | medium | none | L1 | sonnet:edit:1 |
| validator coverage + provenance | cli | serial | low | none | L0 | cli:lint:1 |
| fresh-context wave review (gate 3) | sonnet | parallel(3) | high | after | L2 | sonnet:review:3 |
| land: push + merge | opus | serial | high | both | L1 | opus:mechanical:1 |

## Budget hint (non-predictive — "estimate, not a guarantee")

```
python3 skills/orchestration/scripts/budget_hint.py \
  --task "sonnet:edit:1:DASH-03" --task "sonnet:edit:1:DASH-13" \
  --task "cli:lint:1:validators" --task "sonnet:review:3:wave-review" \
  --task "opus:mechanical:1:land"
```

→ low ≈ 11,300 · **expected ≈ 37,800** · high ≈ 113,200 output tokens.
*Coarse heuristic, NOT a forecast, NOT the engine `budget`.* Reading: Sonnet-dominated, modest
fan-out — no Opus-heaviness to trim. The one Opus task (`land`) is mechanical, so its 2.5× factor is
acceptable.

**tier-mix:** 90% fleet / 1×opus / 0×fable / 1×cli  ← pasted verbatim from `budget_hint.py`'s
output (fleet = haiku + sonnet expected tokens ≈ 34,000 of 37,800 total; ≥80% target met, no WARN)

## Human checkpoints (🔴)

- **`land` (before + after):** push + merge is a push checkpoint — stop, confirm the fresh review is
  CLEAN, then merge; confirm reload after.
- **DASH-03 live Linear push:** the contract above runs the **dry-run** path only; a real push to the
  live Linear backend is a separate operator-triggered 🔴, not in this contract.
- **Wave review (after):** a BLOCKER verdict halts forward dispatch — no `land` until resolved.

## Sign-off

- [x] every build-order task has a row
- [x] review levels set; escalations stated with reason (review wave → L2 because it gates the land)
- [x] human checkpoints enumerated
- [x] budget hint computed + reviewed
- [x] delivered for operator review

`status: signed`. Emission to the engine happens **after** signing, **only** on the user's
`orchestrate` invocation: on Claude Code the per-task table becomes a Workflow script
(`parallel(3)` for the review panel); with no scripted engine it degrades to the Agent/Task
subagent-loop floor (fresh worker → fresh reviewer per task, BLOCKER halts).

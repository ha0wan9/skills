---
artifact_name: loop-engineering-orchestration-contract
instantiated_from: orchestration/templates/orchestration-contract.md
source_reference: orchestration/references/orchestration-contract.md
project_scope: this repo only
owner: shared-user-facing
review_policy: re-review when the build plan or any task tier/checkpoint/review-level changes
last_reviewed: 2026-07-07
status: signed
orchestrates_plan: docs/plans/loop-engineering-build-plan.md
---

# Orchestration Contract — v0.10 "Loop engineering"

**Orchestrates:** `docs/plans/loop-engineering-build-plan.md` — milestone `v0.10`
(DASH-059/060/061/062/064). Policy signed ahead of the run; the engine
(see `orchestration/references/engine-handoff.md`) is the mechanism. AP-COORD-7.

## Run context

| Field | Value |
|---|---|
| operating_loop | foreground |
| harness_profile_snapshot | HARNESS_PROFILE=standard; bounds=disabled; effective=standard |
| artifact_review_surface | the PR diff on GitHub + `docs/dashboard.html` board status |
| state_writeback_target | board items DASH-059/060/061/062/064 (+ v0.10 milestone) via `board.py`; lessons via memory |
| verification_oracle | build-plan verification matrix: `validate_project_meta.py` + dl-research fixture triple (v1 pass / v2-bad fail / v2-good pass) + loop_state round-trip + T3 exit-code scenario + T4 gate demonstrations + `ship_plugin.sh validate` + fresh ship-review clean |

## Per-task contract

| Task (plan id) | model_tier | parallelization | orchestrator_effort | human_checkpoint | review_level | budget_hint |
|---|---|---|---|---|---|---|
| T1 Loop Contract + loop_state + ratchet adoption (DASH-059/060) | sonnet | serial (internal L1→L2 order) | high | none | L2 — canon reference + cross-skill surface; escalated from L1 floor for stakes | sonnet:edit:1 |
| T2 ratchet promote gate (DASH-061) | sonnet | serial | medium | none | L1 with adversarial lens — validator/store change (per `adversarial-lens-earns-keep`) | sonnet:edit:1 |
| T3 openclaw cycle circuit breaker (DASH-062) | sonnet | serial | medium | none | L1 | sonnet:edit:1 |
| T4 phase-lock gates (DASH-064) | sonnet | serial | low | none | L1 | sonnet:edit:1 |
| T1–T4 wave shape | — | parallel(4), disjoint touch-sets (ledger-verified) | — | — | — | sonnet:review:5 (4 task reviews + 1 ship review) |
| T5 lead: bumps, validators, ship, board writeback | fable (conductor, this session) + cli | serial | high | none — push/merge covered by the standing validated-edit → ship → reload workflow authorization in `AGENTS.md`; first BLOCKER halts | L1 fresh ship-review (gate 3) | cli:lint:1 |

## Budget hint (non-predictive — "estimate, not a guarantee")
    python3 skills/orchestration/scripts/budget_hint.py --task sonnet:edit:1 --task sonnet:edit:1 --task sonnet:edit:1 --task sonnet:edit:1 --task sonnet:review:5
- low: 18,600 · expected: 62,000 · high: 186,000 output tokens — coarse heuristic, NOT a forecast, NOT the engine budget.

**tier-mix:** 100% fleet / 0×opus / 0×fable-dispatched / 1×cli  (conductor runs on the session model; no dispatched Opus/Fable slots)

## Human checkpoints (🔴)

None scheduled. Push/PR/merge fall under the repo's standing "Validated Edit → Ship → Reload"
workflow (AGENTS.md), which authorizes autonomous shipping behind the three gates
(validate / version-bump / fresh-review-clean). Any reviewer BLOCKER **stops forward dispatch**
synchronously (AP-COORD-2); at most one fix round per task, then halt and surface.

## Sign-off  (status: signed only when ALL hold)
- [x] every build-order task has a row (T1–T5)
- [x] run context complete; foreground run with concrete oracle
- [x] review levels set; escalations stated with reason (T1→L2 stakes; T2 adversarial lens)
- [x] human checkpoints enumerated (none; standing workflow authorization cited)
- [x] budget hint computed + reviewed (100% fleet share ≥ 80% target)
- [x] delivered for operator review — operator pre-authorized this run with the explicit
      instruction "Orchestrate and run Loop Engineering 2026" (2026-07-07); contract committed
      with the run for post-hoc review per that instruction

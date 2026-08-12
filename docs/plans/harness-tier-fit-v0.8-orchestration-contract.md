---
artifact_name: harness-tier-fit-v0.8-orchestration-contract
instantiated_from: orchestration/templates/orchestration-contract.md
source_reference: orchestration/references/orchestration-contract.md
project_scope: this repo only
owner: shared-user-facing
review_policy: re-review when the build plan or any task tier/checkpoint/review-level changes
last_reviewed: 2026-08-12
status: signed
orchestrates_plan: docs/plans/harness-tier-fit-v0.8-build-plan.md
---

# Orchestration Contract — v0.8 Wave 1 "Harness tier-fit"

**Orchestrates:** `docs/plans/harness-tier-fit-v0.8-build-plan.md` — milestone `v0.8`, Wave 1
(DASH-081 / DASH-083 / DASH-080 / DASH-082; DASH-54 and DASH-55 stay in v0.8 outside this wave).
Policy signed ahead of the run; the engine (see `orchestration/references/engine-handoff.md`) is
the mechanism. AP-COORD-7.

## Run context

| Field | Value |
|---|---|
| operating_loop | foreground |
| harness_profile_snapshot | HARNESS_PROFILE=standard; bounds=disabled; effective=standard |
| artifact_review_surface | PR diffs on GitHub + `docs/dashboard.html` board status + `docs/plans/harness-tier-fit-ab-note.md` (evidence artifact) |
| state_writeback_target | board items DASH-080/081/082/083 (+ v0.8 decisions DEC-003/DEC-004) via `board.py`; durable lessons via `lesson_registry.py` |
| verification_oracle | build-plan §6 matrix: stale-string grep + Workflow-schema check (081) · A/B note with verdict line (083a) · standard-advisory / strict-deny / validator triple (083b) · roster == DEC-003 (080) · audit-detects-mismatch + A-6 resolved + scope == DEC-004 (082) · `ship_plugin.sh validate` exit 0 + fresh review CLEAN (wave) |

## Per-task contract

| Task (plan id) | model_tier | parallelization | orchestrator_effort | human_checkpoint | review_level | budget_hint |
|---|---|---|---|---|---|---|
| W1.1 engine-handoff refresh (DASH-081) | sonnet | parallel with W1.2 (disjoint touch-sets) | medium | none | L2 — `review_tier.py` floor (harness-hit); satisfied by the wave panel row | sonnet:edit:1 |
| W1.2 phase-lock A/B evidence note (DASH-083a) | sonnet | parallel with W1.1 | medium | **after** (🔴 evidence gate — operator reads the note before W1.3) | L1 | sonnet:plan:1 |
| W1.3 de-prescription edits (DASH-083b) | sonnet | serial (post-gate) | high | **before** (evidence gate must have cleared) | L3 — `review_tier.py` floor (harness-hit + MUST-rule: gate-authority change); adversarial row below | sonnet:edit:1 |
| W1.4 roster slimming (DASH-080) | cli | serial | low | **both** (before: DEC-003 resolution; after: restart + listing verify) | L1 — escalated from L0 floor: user-config mutation, verified post-restart | cli:mechanical:1 |
| W1.5 config-root reconcile (DASH-082) | sonnet | serial | medium | **before** (DEC-004 resolution for the scope leg) | L1 — escalated from L0 floor: config-root surface | sonnet:edit:1 |
| W1.6a wave review panel | sonnet | parallel(3) | high | after (BLOCKER halts) | L2 | sonnet:review:3 |
| W1.6b adversarial gate review (over W1.3) | opus | serial | high | after (BLOCKER halts) | L3 — the single sanctioned escalation slot: adversarial review where a miss (silent gate-authority weakening) is expensive | opus:review:1 |
| W1.7 land (ship validate → merge → reload) | sonnet | serial | medium | none — standing validated-edit → ship → reload authorization (AGENTS.md); first BLOCKER halts | L1 fresh ship-review (gate 3) | sonnet:mechanical:1 |

## Budget hint (non-predictive — "estimate, not a guarantee")

    python3 skills/orchestration/scripts/budget_hint.py \
      --task "sonnet:edit:1:DASH-081" --task "sonnet:plan:1:DASH-083a" \
      --task "sonnet:edit:1:DASH-083b" --task "cli:mechanical:1:DASH-080" \
      --task "sonnet:edit:1:DASH-082" --task "sonnet:review:3:wave-panel" \
      --task "opus:review:1:adversarial-083" --task "sonnet:mechanical:1:land"

- low: 22,000 · **expected: 73,500** · high: 220,500 output tokens — coarse heuristic, NOT a forecast, NOT the engine budget.

**tier-mix:** 79% fleet / 1×opus / 0×fable / 1×cli
`WARN: fleet token-share below 80% target (advisory — mistagged tiers are not detectable here; review the per-task model_tier column)`

*Deviation explained:* the share sits 0.4 pt under target (58,500 / 73,500 = 79.6%) solely because
of the single opus adversarial-review slot over W1.3 — the canon-sanctioned "adversarial/security
review where a miss is expensive" seat for a gate-authority change. Padding the sonnet panel to
game the ratio would add cost without adding quality (AP-COORD-4); the deviation is accepted as-is.

## Human checkpoints (🔴)

1. **Evidence gate (after W1.2):** operator reads `docs/plans/harness-tier-fit-ab-note.md` and
   green-lights or rejects the softening. Ambiguous/negative evidence → keep-hard default
   (plan §8) — DASH-083 then completes as "evidence rejected softening".
2. **DEC-003 (before W1.4):** persona-pack roster decision — `board.py decision-resolve`.
3. **DEC-004 (before W1.5):** plugin scope-normalization decision — `board.py decision-resolve`.

Push/PR/merge are covered by the standing "Validated Edit → Ship → Reload" workflow authorization
(AGENTS.md); a reviewer BLOCKER stops forward dispatch synchronously (AP-COORD-2) — at most one
fix round per task, then halt and surface.

## Sign-off  (status: signed only when ALL hold)

- [x] every build-order task has a row (W1.1–W1.7)
- [x] run context complete; foreground run with a concrete per-item oracle
- [x] review levels set; escalations stated with reason (W1.3 → L3 must-rule floor; W1.6b →
      single opus adversarial slot; W1.4/W1.5 → L1 escalated from L0 floor for config surfaces)
- [x] human checkpoints enumerated (three 🔴 above; land under standing authorization)
- [x] budget hint computed + reviewed (79% fleet — WARN carried verbatim + deviation explained)
- [x] delivered for operator review — operator pre-authorized with the explicit instruction
      "ORCHESTRATE 评审的大项建议" (2026-08-12); contract delivered in-chat and committed with
      the run for post-hoc review, per the v0.10 loop-engineering precedent

`status: signed`. Emission per `engine-handoff.md`: on this runtime the unblocked slice
(W1.1 ∥ W1.2) becomes a Workflow run; W1.3–W1.5 dispatch only as their checkpoints clear;
with no scripted engine the run degrades to the Agent/Task subagent-loop floor.

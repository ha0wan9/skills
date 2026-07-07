# Build Plan — v0.10 "Loop engineering" (L1–L4 + L6)

**Source:** `skills/project-meta/proposals/loop-engineering-2026.md` (L5 withdrawn, L7 deferred).
**Board:** DASH-059, DASH-060, DASH-061, DASH-062, DASH-064 (milestone v0.10).
**Critic panel (2026-07-07, pre-build, per `critic-before-build-canon`):** design critic (2 BLOCKER / 4 MAJOR / 3 MINOR) + scope critic (1 TRIM). All findings folded in below; the plan deltas vs the proposal are marked **[critic]**.

## Plan deltas from the critic panel

1. **[critic-BLOCKER]** L3 has no critic-row shape to detect today — the runs-ledger schema has no
   `row_type` discriminator and its REQUIRED set only fits experiment rows. T2 now specifies the
   row shape explicitly (below) before touching the validator.
2. **[critic-BLOCKER]** L1 citation = **dev-time same-repo relative pointer + ≤6-line inline floor**
   (the `orchestration` "Dependency & Canon" pattern), NOT the `shared-cli-delegation.md` runtime
   resolver — that pattern is for runtime CLIs, not prose references.
3. **[critic-MAJOR]** L1→L2 are sequentially coupled (both author `references/loop-contract.md`) →
   merged into one task, T1, built by one worker in order.
4. **[critic-MAJOR]** Lint precision: heuristic scoped to prose files (SKILL.md/recipes/modes/
   references), fires only on ≥2 distinct loop markers, ships with a known-non-matches fixture
   (openclaw `cycle` polling loops, meta-debug retry helpers, dispatch_ledger budget fields).
   project-meta's own audit-convergence loop **conforms** (self-citation; no exemption — the
   canon-writer follows its own canon).
5. **[critic-MAJOR]** loop_state schema: `phase` is **optional free-form**; the ratchet has no
   survey-style phases — it checkpoints at end-of-iteration (after the keep/discard record),
   which is its phase boundary.
6. **[critic-MAJOR]** L4 paused state exits with **distinct code 2** ("paused, operator needed"),
   never 0 — cron monitors keyed on exit codes must not go silent when the breaker trips.
   **[critic-MINOR]** streak increments only on `overall == FAIL` (WARN does not count).
7. **[critic-TRIM]** deep-survey-bfs adoption of `should-stop` is cut from v0.10 (its loop is
   already best-in-repo); it gets a **citation-only** conformance line. Optional follow-on later.
8. **[critic-MINOR]** L6 `review` gate reads the file-derived `.harness/last-turn-meta.json`
   (D5 precedent), not a ledger query; `brainstorm.sh` intentionally stays a stub (nothing
   mechanical to check). Phase-lock wiring verified: `.claude/hooks/verify-before-stop.sh`
   invokes `phase_lock_check.py` (no wiring gap).

## Build order

T1 ∥ T2 ∥ T3 ∥ T4 (touch-sets pairwise disjoint — verified below), then T5 (lead: bumps,
validators, ship). Each Tn gets a fresh reviewer before merge into the shared branch history.

### T1 — Loop Contract + loop_state primitive + ratchet adoption (DASH-059 + DASH-060)

**Touches:** `skills/project-meta/references/loop-contract.md` (new),
`skills/project-meta/scripts/loop_state.py` (new),
`skills/project-meta/scripts/skill_architecture_lint.py`,
`skills/project-meta/recipes/audit.md` (conformance block),
`skills/project-meta/SKILL.md` (reference row only, if references are indexed there),
`skills/dl-research/modes/ratchet-loop.md` (conformance block + checkpoint adoption),
`skills/deep-survey-bfs/references/loop-mode.md` (citation-only conformance line),
plus lint fixture files under `skills/project-meta/` if the lint uses fixtures today.

**Scope:**
- `loop-contract.md`: the six-field loop declaration — trigger, goal, budget
  (tokens/iterations/time), verification (grader separation; computational floor mandatory,
  inferential critics stack on top), state/checkpoint (file-based), stopping rule + escalation.
  Plus the canonical `loop_state.json` schema lifted from deep-survey-bfs
  (`iteration`, `current_task`, `blockers`, `completed_targets`, `next_targets`,
  `stop_conditions`, `budget_spent`; `phase` optional free-form). Citation mechanism per
  delta 2. Cite evidence sparsely (proposal ¶1–4), don't restate the literature.
- `loop_state.py` (stdlib-only): `init` / `checkpoint` / `read` / `should-stop` verbs over a
  `loop_state.json` path. `should-stop` evaluates the declared `stop_conditions` (budget
  exceeded, max iterations, explicit stop flag) and exits 0=continue / 1=stop with a reason
  line. No daemon, no timer — invoked at loop boundaries by the loop owner.
- Lint leg per delta 4: WARN (not FAIL) when a prose skill file declares a loop without citing
  `loop-contract.md`; known-non-matches fixture proves precision.
- `ratchet-loop.md`: adds a checkpoint step at end-of-iteration via `loop_state.py`
  (resolved project-meta install or repo path, same resolution note the skill already uses for
  shared CLIs), documents resume ("read loop_state.json + last ledger row; continue"), and adds
  the conformance block. No behavior change to the keep/discard rules.

**Acceptance (falsifiable):**
- `python3 scripts/validate_project_meta.py` green (26 checks + any lint-fixture additions).
- `loop_state.py` round-trip demo: `init` → 2× `checkpoint` → `should-stop` (continue) →
  checkpoint hitting an iteration cap → `should-stop` exits 1 with reason.
- Lint: a synthetic loop-declaring fixture WARNs; the known-non-matches list does not.
- `ratchet-loop.md` shows the checkpoint step + resume path; deep-survey file diff is
  citation-line only.

### T2 — Mechanize the ratchet promote gate (DASH-061)

**Touches:** `skills/dl-research/templates/runs-ledger.schema.json`,
`skills/dl-research/scripts/validate_ledger.py`,
`skills/dl-research/examples/sample-study/runs.jsonl` (and a new v2 fixture beside it if
clearer), `skills/dl-research/references/multi-agent-harness.md`.

**Scope (row shape per delta 1):**
- Add `row_type` discriminator: absent or `"run"` = experiment row (v1-compatible).
  New `row_type: "critic_verdict"` row: required `{row_type, target_run_id, critic_agent,
  verdict ∈ {pass, block, revise}, created_at}`; exempt from run-row REQUIRED fields.
- Add explicit `ledger_version` marker (row-level or first-row header, implementer's choice —
  must be explicit, never inferred). Files with no marker validate under v1 rules unchanged
  (**airtight**: the new rule keys only on the explicit marker).
- v2 rule: a run row with `decision: "promote"` is invalid unless an earlier
  `critic_verdict` row with `verdict: "pass"` targets that row's `run_id` (or its
  `experiment_id`). A `block`/`revise` verdict without a later `pass` also invalidates promote.
- `multi-agent-harness.md`: one short paragraph noting the prose MUST is now mechanically
  floored by the validator (cite the file, don't restate).

**Acceptance:** old v1 fixture validates unchanged; a v2 fixture with an unguarded promote
**fails**; the same fixture plus a preceding `pass` critic row **passes**. All three runs shown.

### T3 — openclaw-devops cycle circuit breaker (DASH-062)

**Touches:** `skills/openclaw-devops/scripts/openclaw_devops.py`,
`skills/openclaw-devops/references/runbook.md`.

**Scope (per deltas 6):** consecutive-FAIL streak persisted in the existing state store
(`state.json` in `STATE_DIR`); WARN does not increment; any non-FAIL cycle resets it. At
streak ≥ 3 (constant, documented): set `paused`, file a bugs-backlog entry (existing `bugs`
API), and from then on `cycle` performs **no repair/update actions** and exits **2** with a
one-line "paused: operator needed (resume or passing sanity clears)" message. New `resume`
subcommand clears paused+streak; a passing `sanity` also clears. flock semantics unchanged.

**Acceptance:** driven via the script's existing testable seams (or a temp STATE_DIR):
3 simulated FAIL cycles → paused, exit 2, bug entry present; WARN cycle does not increment;
`resume` (and separately a passing `sanity`) clears; healthy path still exits 0.

### T4 — Real phase-lock gates for this repo (DASH-064)

**Touches:** `.harness/gates/plan.sh`, `.harness/gates/implement.sh`,
`.harness/gates/review.sh`, `.harness/gates/finish.sh`, `agents/phase-lock-contract.md`
(document the checks). `brainstorm.sh` stays a stub by decision (delta 8).

**Scope (all POSIX sh, deterministic, no network):**
- `plan.sh`: `.harness/phase-state.json` names a `build_plan` path (new optional field, written
  at plan entry) AND that file exists. Unset/missing → exit 1 with message.
- `implement.sh`: `scripts/ship_plugin.sh validate` exits 0.
- `review.sh`: `.harness/last-turn-meta.json` exists and contains a non-empty `review_tier`
  (file-derived, D5 precedent).
- `finish.sh`: `scripts/ship_plugin.sh check-version` passes (a version bump exists vs main).
- Contract doc updated to describe each real check + the brainstorm-stays-stub decision.

**Acceptance:** each gate demonstrably exits 0 and 1 under the right/wrong conditions (shown);
`phase_lock_check.py` aggregate runs clean at end state on this branch.

### T5 — Lead: bumps, validators, ship (no worker)

project-meta **minor** → 1.22.0; dl-research **minor** → 1.3.0; openclaw-devops **minor** →
1.3.0; deep-survey-bfs **patch** → 1.2.2 (citation line). T4 is repo-local (covered by the
plugin bumps for check-version). Then: `ship_plugin.sh validate` → PR → fresh ship-review of
the full diff (gate 3) → `land` → board writes (items → done, milestone v0.10 → done) →
lesson/receipt writeback.

## Verification matrix

| Gate | Command |
|---|---|
| project-meta validator | `python3 scripts/validate_project_meta.py` |
| dl-research ledger fixtures | `python3 skills/dl-research/scripts/validate_ledger.py <fixture>` (v1 pass / v2-bad fail / v2-good pass) |
| loop_state round-trip | `loop_state.py init/checkpoint/should-stop` demo |
| T3 breaker | scripted FAIL/WARN/resume scenario, exit codes asserted |
| T4 gates | per-gate 0/1 demonstrations + `phase_lock_check.py` |
| Ship | `ship_plugin.sh validate` + fresh-review + `land` |

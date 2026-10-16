# Tier policy (allocation, selection, switch boundaries)

Canonical semantics for the four collaboration tiers. Everything here is a **documentation
contract**: nothing in this release enforces a tier, persists one, or gates on one.

## 1. What a tier controls

A tier controls **workload allocation and participation** between the upstream frontier host
and the downstream worker. A tier **never** changes:

- the model's thinking-token budget,
- the model or harness identity used by either side,
- acceptance quality or the required acceptance checks,
- safety or permissions (a tier never widens scope or grants a write/autonomous gate).

| tier | upstream frontier | downstream worker |
|---|---|---|
| `eco` | minimal: goal, critical planning only, independent acceptance | bulk exploration, planning detail, coding, tests, self-check |
| `balanced` *(visible default)* | plans; resolves critical ambiguities, hypotheses, acceptance oracles | routine exploration, coding, tests, self-check |
| `boost` | proactive diagnosis, hard reasoning, key design, tight critical-path decisions to avoid retries | routine exploration, execution, coding, tests, self-check (bulk) |
| `full` | may handle any stage directly | optional; no forced hop; bounded/executable work |

Cross-tier rules:

- **No gratuitous worker hop.** Even in `full`, upstream may finish a stage directly; a
  round-trip is added only when it helps, never as a formality.
- **`full` promises no unlimited spend and no guaranteed speed.**
- **Worker tokens are non-binding in every tier.** Do not optimize toward them or spend effort
  instrumenting them beyond data the run already produced.
- **Required acceptance checks are fixed.** A leaner tier trims redundant reads and
  discretionary review effort, never a gate.
- **No invented ratios, tuned thresholds, or "optimal" split** is asserted for any tier, and
  no tier is claimed faster without a measured, matched comparison.

## 2. Selection and inheritance

Order of precedence:

1. **Explicit user selection** for this task.
2. **Inherited** last manual selection — only within the current task/conversation, or from an
   explicitly persisted project choice the user made. Never inherit silently across unrelated
   repos or chats.
3. Otherwise: propose the **visible default `balanced`** and mark provenance **`default`
   (provisional)**. A provisional default must always be labeled as such; never represent it as
   user-selected.

Record on each task: the tier, its `tier_source` (`user` | `inherited` | `default`), and the
route reason for this task within the tier.

## 3. Switch boundaries

- **No automatic switch** from task type, difficulty, latency, failure, or the retrospective.
  The model may recommend; **the human selects**.
- **Adapt within the tier.** If the extra frontier work would exceed the selected tier's scope,
  record a recommendation for the user; do not silently switch.
- **Manual mid-task switch** is allowed only at a task boundary and only by the user. Record
  `{time, from, to, source, actor, reason}`, preserve all prior events and results, and never
  backdate earlier work into the new tier.
- **No progress** → bounded re-scope, stop, and report. No unbounded retries and no automatic
  tier-up.
- Ordinary work already inside scope needs **no new approval ritual**.

## 4. Objective and honest measurement

Two outcome dimensions, kept separate and never collapsed into one score:

1. **Accepted-task elapsed time** — worker + supervisor + waits + rework.
2. **Upstream consumption** — the frontier side's effort/tokens; this is the number the
   workflow is trying to reduce.

Reported proxies (substantive upstream interventions, round-trips, ingested evidence size)
must be **labeled as proxies**, never passed off as exact token counts. If upstream tokens are
not exposed by the host runtime, record **unknown** — do not fabricate. Do not claim
whole-loop or cross-task savings from unmatched tasks; a savings claim needs a paired,
same-tier comparison on comparable tasks, one variable at a time.

## 5. Source ownership, permissions, and acceptance

- The **target repo's** source-ownership, permission, and commit rules govern the task. This
  skill deliberately does **not** carry LICP's local development restrictions (worker-only
  edits, no commits, no installs) as universal rules; those are one project's policy, not the
  workflow's.
- In `full`, direct upstream implementation is allowed **only** where the local agreement
  allows it.
- **Independent final acceptance remains upstream.** The worker returns
  `status: implementation ready — supervisor review pending` and never declares a gate
  accepted, in any tier.

## 6. Not shipped in 0.1.0

Programmatic `run`/`resume`/`result` verbs, a run loop or worker pool, autonomous scheduling,
tier validation/enforcement, per-tier reports, and an automatic close hook are **not** part of
this release. A tier is a label the humans choose and honor, not a field any bundled code
checks.

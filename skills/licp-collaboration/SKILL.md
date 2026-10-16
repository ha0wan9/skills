---
name: licp-collaboration
description: >-
  Run a manual, explicitly-invoked collaboration between an upstream frontier host and a
  downstream worker harness (pi first) on one scoped task, with a human-selected tier (Eco,
  Balanced, Boost, Full) that allocates participation only — never thinking budget,
  model/harness identity, acceptance quality, safety, or permissions. Use when deciding how
  much the frontier side does itself versus delegates, invoking pi manually with an explicit
  session and evidence packet, recording a bidirectional close retrospective (worker to
  frontier and frontier to worker), or choosing, inheriting, or manually switching a tier.
  Optimizes accepted-task wall-clock time against upstream consumption; worker tokens are a
  non-binding diagnostic. Ships workflow instructions plus bundled references only: no
  run/resume/result adapter, scheduler, automatic retrospective hook, or tier enforcement.
  Distinct from the orchestration skill, which owns milestone contracts and run engines.
metadata: {version: 0.1.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# licp collaboration

Manual upstream(frontier) ↔ downstream(worker) collaboration on **one scoped task**. The
objective is a two-dimensional tradeoff, with no invented scalar weight: minimize **upstream
(Codex-class) consumption** while bounding **accepted-task wall-clock time** (worker +
supervisor + waits + rework). Quality and safety are **fixed** and outrank both. Worker token
use is a **non-binding diagnostic**, never a constraint or gate.

**Status of 0.1.0 — do not overstate.** This release is **workflow instructions + bundled
references**. There is **no** programmatic `run`/`resume`/`result` adapter, **no** autonomous
scheduling or background worker, **no** automatic retrospective hook, and **no** typed tier
enforcement. Do not invent `licp` worker/tier commands or flags, and do not claim an automatic
close hook. Optional monitoring exists only in the LICP source environment and is **not
bundled** here — read [references/pi-worker-invocation.md](references/pi-worker-invocation.md)
before citing any monitor API.

## Four tiers (human-selected; allocation only)

A tier sets **which side participates in which stage**. A tier never changes the model's
thinking budget, the model or harness identity, acceptance quality, safety, or permissions.

| tier | upstream frontier does | downstream worker does |
|---|---|---|
| `eco` | goal, critical planning, independent acceptance | almost all detailed work: exploration, planning detail, coding, tests, self-check |
| `balanced` *(visible default)* | planning; critical ambiguities, hypotheses, acceptance oracles | routine exploration, coding, tests, self-check |
| `boost` | proactive diagnosis, key design, hard critical-path reasoning to avoid retries | bulk exploration, execution, coding, tests, self-check |
| `full` | may handle any stage directly | optional — no gratuitous worker hop |

No invented ratios, tuned quotas, or "guaranteed faster" tiers. `full` grants no unlimited
spend and no promised speed, and direct upstream implementation is allowed only where the
**target repo's** source-ownership and permission agreement allows it.

## Invariants

- **Selection**: from an explicit user choice, or inherited from the last manual choice within
  the current task/conversation or an explicit project choice. With neither, use the **visible
  default `balanced` and mark its provenance provisional** — never present a default as if the
  user picked it. Nothing here persists tiers automatically.
- **No automatic tier switch.** The model may recommend; the human selects. Adapt routing
  *within* the tier. A manual mid-task switch is recorded as
  `{time, from, to, source, actor, reason}` and prior outcomes are preserved, never rewritten.
- **Target-repo rules win.** Follow the target repo's source-ownership, permission, and commit
  rules. Do **not** transplant LICP's local restrictions (worker-only edits, no commits, no
  installs) onto other repos as universal rules.
- **Independent final acceptance stays upstream.** An implementation worker never certifies its
  own gate.
- **Scripts first.** Before new model work in either direction, consider an existing
  deterministic script. If no Script-Dispatcher/registry exists in the environment, record it
  as unavailable and proceed — never invent commands, never build a second registry.
- **Both retrospective directions are checked every close** — `worker_to_frontier` **and**
  `frontier_to_worker`, each `candidate_found` / `no_candidate` / `insufficient_evidence` /
  `not_applicable` + a short reason. See
  [references/retrospective.md](references/retrospective.md).

## Loop (manual)

1. Confirm the tier and its provenance (user / inherited / provisional default).
2. Check for an existing reusable script before delegating new model work.
3. Send one **scoped** task envelope and invoke the worker explicitly —
   [references/pi-worker-invocation.md](references/pi-worker-invocation.md).
4. Review the returned delta and evidence independently; accept, or send bounded corrections in
   the same session.
5. At close, record the bidirectional retrospective —
   [references/retrospective.md](references/retrospective.md).

Tier policy detail, including switch boundaries and non-degradation limits, is in
[references/tier-policy.md](references/tier-policy.md). This skill is self-contained: it does
not link outside its own directory and does not depend on any other plugin. The
`orchestration` skill is a **different** concern (milestone → orchestration contract → run
engine); name it, do not merge the two.

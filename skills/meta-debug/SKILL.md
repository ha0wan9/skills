---
name: meta-debug
description: >-
  A gated, rollbackable, looping meta-debug pipeline for root-causing hard,
  flaky, or recurring bugs: triage & mitigate → clean-context case file →
  deterministic repro → red test (reuse existing CI) → falsifiable hypotheses →
  constraint-scored solutions → top-k parallel sandbox fixes → adversarial-critic
  validation → canary with a rollback trigger → recorded lesson. Runtime-agnostic
  (Claude Code, Codex, OpenClaw); composes with project-meta. Use whenever the
  user wants to debug, root-cause, or systematically fix a non-trivial bug, a
  regression, a heisenbug, a "works locally but fails in prod" issue, or a
  post-incident root cause — even if they don't name this skill.
---

# Meta-Debug

A bug fix is only trustworthy when you can **reproduce** the failure, a **test
goes red→green because of your change**, the change addresses a **root cause
confirmed by a probe** (not the first plausible culprit), and the prod step is
**reversible**. This skill encodes that as a phased pipeline with **gates** you do
not pass until they hold, **checkpoints** to roll back to, and a **bounded loop**
that escalates instead of thrashing. The procedure lives in
`references/debug-pipeline.md`; the session state, gates, hypotheses, candidate
critic-scores, and the closing lesson are tracked by `scripts/debug_session.py`.

## Trigger Decision

- **Hard/recurring bug**: a non-trivial defect to root-cause and fix, or one that
  keeps coming back.
- **Flaky/heisenbug**: intermittent failures, "works locally / fails in CI/prod".
- **Regression**: something that used to work broke after a change/deploy.
- **Post-incident**: root-cause an outage and turn it into a durable guard.
- **"Why does X break?"**: any request for systematic diagnosis over a guess.

## Bootstrap Order

1. Load `references/debug-pipeline.md` — the phase contract and gates.
2. Collect context via the **project-meta harness format** (canonical memory
   entrypoint → topical files → preferences), not ad-hoc grep — phase 1 defers
   to project-meta for *how* memory is laid out. If the repo has no harness, run
   `/project-meta init` first (hand-off), then proceed.
3. Track the session with `scripts/debug_session.py` so gates are enforced and the
   close writes a lesson.

## Core Rules

- **MUST follow the gated pipeline for a non-trivial bug — never skip a gate.**
  Reason: skipping repro/test/confirmation produces fixes that can't be trusted.
  `debug_session.py phase` refuses to pass a gate while an earlier gate is red.
- **MUST have a deterministic reproduction + a red test before fixing.** Reason:
  with no reliable repro you cannot prove a fix; with no red test the fix can't be
  verified or guarded against regression. No repro → switch to the heisenbug
  (observability) track, do not fix blind.
- **MUST confirm the root cause with a discriminating probe before designing a
  fix.** Reason: the first plausible culprit is often innocent; record refuted
  hypotheses so the same dead end isn't re-walked. Confirm before you blame.
- **MUST reuse the environment's existing test/CI harness for the red test.**
  Reason: a throwaway repro script that isn't wired into CI rots and won't catch
  the next regression. Only author standalone when no harness exists.
- **MUST apply prod fixes behind a reversible step with a predefined rollback
  trigger + observation window.** Reason: deploying is not succeeding; the
  observation window passing is. Define the rollback trigger *before* applying.
- **MUST record a lesson on a fixed close, and promote durable ones to canonical
  memory.** Reason: a diagnosis you don't capture is one you'll repeat.
- **Default:** loop budget 3 → on exhaustion, escalate to a human with the case
  file, not another blind round.

## Skill Arbitration

| Request shape | Owning skill | This skill's role |
|---|---|---|
| Debug / root-cause / systematically fix a bug | **meta-debug** | acts (runs the pipeline) |
| *How* to read/lay out repo memory, the multi-agent dispatch contract, promoting a lesson into canonical memory, repo harness bootstrap | **project-meta** | meta-debug **delegates** to it: phase 1 reads memory in project-meta layout, phase 6 dispatches workers via project-meta's multi-agent protocol, phase 9 promotes lessons via project-meta's CRUD rules. Run `/project-meta init` first if no harness exists. |
| Maintaining an OpenClaw install, or the concrete reproduce/verify/rollback mechanics for an OpenClaw bug (phase 0 mitigate, phase 8 canary/revert) | **openclaw-devops** | meta-debug calls its `rollback`/`verify`/`sanity` as the OpenClaw backing for those phases; openclaw-devops owns the maintenance actions, meta-debug owns the debug workflow. |

meta-debug owns the *debugging workflow*; project-meta owns the *harness* the
workflow reads from and writes back to. They compose — meta-debug never
re-derives memory structure or the multi-agent contract.

## Gotchas

- **Never let a debug agent swallow the whole repo.** A clean-context collector
  that reads everything balloons context and times out (a real failure mode: a
  collector that read five rendered pages hit a ~191k-token request and timed
  out). Hand each agent the bounded **case file**, not the codebase.
- **The lead never edits inside workers' sandboxes.** Workers each own one
  candidate in isolation; the lead integrates only the phase-7 winner.
- **"Deployed" ≠ "fixed".** Success is the observation window passing with no
  rollback trigger hit — wire that in before applying.
- **Flaky bugs go on the observability track**, not the fixing track — capture a
  failure-rate baseline first; a "fix" you can't see fail again proves nothing.
- **`debug_session.py` writes lessons to this skill's `state/lessons.jsonl`.**
  That's the fast journal; durable lessons still get promoted to canonical memory.

## Quick Workflow

Phases: `triage → context → reproduce → tests → hypotheses → solutions →
candidates → validate → prod → close`. Gates: reproduce, tests, hypotheses,
validate, prod. Detail + per-runtime mechanics in `references/debug-pipeline.md`.

```bash
DBG=<skill>/scripts/debug_session.py
python3 $DBG start --title "…" --severity sev2          # → session id
python3 $DBG phase <id> reproduce --status pass --artifact "repro cmd / CI job"
python3 $DBG hypothesis <id> --text "…" --probe "…"      # then --confirm/--refute <Hn> --evidence
python3 $DBG candidate <id> --label fixA --passed-red yes --scores "correctness=9,elegance=7,risk=6" --status winner
python3 $DBG checkpoint <id> --label pre-prod --ref <git-sha>   # rollback <id> --to pre-prod
python3 $DBG loop <id> --to hypotheses --reason "canary regressed"   # bounded (3)
python3 $DBG close <id> --outcome fixed --root-cause "…" --fix "…"   # writes a lesson
python3 $DBG show <id>   # or: list
```

## When To Load References

- Running a session — the phase definitions, each gate, rollback/loop discipline,
  the project-meta harness + multi-agent + memory-promotion hand-offs, the critic
  axes, per-runtime sandbox backings, and anti-patterns:
  - load [`references/debug-pipeline.md`](references/debug-pipeline.md).

## Output Footer

End every invocation with: the session id, the current phase + gate status, which
gates are green, the chosen candidate (if any), and — on close — the outcome
(fixed / escalated) with the recorded root cause and lesson reference.

# Meta-Debug Pipeline

A gated, rollbackable, looping pipeline for root-causing and fixing a non-trivial
bug with discipline. Load this when running a debug session; the phase state,
gates, checkpoints, candidates, and critic scores are tracked by
`scripts/debug_session.py` so the session is a *recorded activity*, not a vibe.

Runtime-agnostic (Claude Code / Codex / OpenClaw). Each phase names the mechanic
to use per runtime where it differs, and **delegates harness/coordination/memory
concerns to the sibling `project-meta` skill** rather than re-deriving them.

## Why these phases (and why gates)

A bug fix is only trustworthy if (a) you can reproduce the failure, (b) a test
goes red→green because of your change, (c) the change addresses a *confirmed*
root cause rather than a plausible-looking culprit, and (d) prod recovery is
reversible. Each is a **gate**: you do not advance until it holds. Gates are what
separate a real fix from a lucky-looking one.

## Phases

Order: `triage → context → reproduce → tests → hypotheses → solutions →
candidates → validate → prod → close`.

### 0. triage (& mitigate-first)
Classify **severity × blast radius**. If prod is actively harmed, apply the
cheapest *reversible* mitigation first (revert the deploy, flip a feature flag,
disable the offending job; for OpenClaw, `openclaw-devops rollback`) and log it as
debt — stop the bleeding before root-causing. Decide the track: **deterministic**
bug vs **heisenbug** (flaky). Gate: a one-line problem statement + severity.

### 1. context (clean agent, bounded case file)
Dispatch a **fresh-context** agent to collect ONLY the relevant context. It MUST
read the project's maintenance harness in **project-meta layout and bootstrap
order** — not ad-hoc grep. For the full layout and bootstrap sequence, defer to
[`../../project-meta/references/repo-memory-structure.md`](../../project-meta/references/repo-memory-structure.md)
and [`../../project-meta/references/mirrors-and-updates.md`](../../project-meta/references/mirrors-and-updates.md).
The meta-debug-specific reading discipline on top:
1. **Selective read** — load only topical memory (`agents/*.md`) relevant to the bug area; do not read the entire harness.
2. Read prior related debugging lessons (`state/lessons.jsonl`).
3. Then the suspected code/config.

If the repo has no harness, run `/project-meta init` first.

Emit a bounded **case file**: bug statement, environment, suspected area,
constraints (latency/compat/…), cited memory excerpts (path + why), and prior
lessons. The collector **gathers — it does NOT propose fixes** (avoids anchoring).
The case file is the session SSOT every later agent reads, so each stays
context-bounded — never let a debug agent swallow the whole repo (real failure
mode: a collector that read five rendered pages hit a ~191k-token request and
timed out).
- Claude Code: `Explore` / `general-purpose` subagent. OpenClaw: a sub-session.

### 2. reproduce (deterministic + failure-rate baseline)
Produce a **minimal, deterministic, cheap** reproduction: exact command, inputs,
seed, env. Run it **N times** and record the failure rate.
- **Gate:** no reliable repro → DO NOT enter fixing. Switch to the heisenbug
  track: add observability/logging, raise sampling, wait for recurrence.

### 3. tests (red first — reuse existing harness)
Encode the bug as a **failing test** — the acceptance gate for every candidate fix
(must go red→green). Written *before* the fix so it can't be retrofitted to bless
a wrong one.
- **Reuse the project's existing test infrastructure first.** Discover what's
  there — CI workflows, the project's test runner/suite, pre-commit/lint, tests
  adjacent to the blast radius — and add the red test *into that harness* so it
  runs exactly as CI does and becomes a durable regression guard.
- **Reuse > reinvent.** A one-off repro script not wired into CI rots and won't
  catch the *next* regression. Author standalone only when no harness exists, and
  leave a note to fold it in.
- Add **characterization tests** around the blast radius (same suite).
- **Gate:** a red test, runnable via the project's normal test path, fails for the
  right reason. Record its location/command as the phase artifact (→ the
  close-lesson's regression-test pointer).

### 4. hypotheses (falsifiable attribution)
Brainstorm candidate root causes. For EACH: a **cheap discriminating probe** that
confirms or refutes it, plus a prior likelihood. Rank by `likelihood × cheapness`.
**Bisect** (`git bisect`, or binary search across time/code/config/input) is a
first-class tool. **Record refuted hypotheses with evidence** — negative results
stop re-investigation and are the antidote to fingering the "obvious" culprit
(e.g. a component that looked guilty but a probe exonerated it).
- **Gate:** a root cause **confirmed by a probe**, not a guess.

### 5. solutions (+ first critic round)
Design **≥2 distinct** approaches that fix the *confirmed root cause* (not the
symptom). Score each with critics on constraint axes: `correctness/root-cause-ness
· minimality/blast-radius · engineering elegance & fit with existing patterns ·
performance/latency & resource constraints · reversibility/risk · test+maintenance
cost`. Symptom-only patches are allowed only as logged debt. Select **top-k**.

### 6. candidates (top-k parallel sandbox fixes)
Run the top-k approaches as a **project-meta multi-agent dispatch**, not ad-hoc
parallelism: a **lead** owns decomposition, context packaging, review criteria,
and integration; each **worker** implements ONE candidate in an **isolated
sandbox** so they never conflict. Defer the orchestration contract (lead/worker
separation, the file-count tier selecting cheap subagent *dispatch* vs a scripted
*engine*, read-only roles never edit) to project-meta's
`references/multi-agent-protocols.md`.
- **Context package** per worker = the **case file** (phase 1) + the **red +
  characterization tests** (phase 3) as acceptance criterion + the one approach it
  owns. Workers stay context-bounded — they do NOT re-collect the repo.
- **Definition-of-done** per worker = its candidate passes the red test AND the
  characterization tests *inside its own sandbox*. Drop the ones that don't.
- **Isolation backings**: Claude Code — `Workflow` `parallel()` with agents at
  `isolation:"worktree"` (or `Agent` `isolation:"worktree"`); Codex — dispatch via
  `.codex/agents/*.toml` (Agents-SDK) or a plain subagent turn per candidate;
  OpenClaw/other — `openclaw sandbox` containers or git worktrees, one per
  candidate; fallback prose: a sequential per-subtask loop with a fresh context
  window per candidate.
- The lead **does not edit inside workers' sandboxes**; it integrates only the
  phase-7 winner.

### 7. validate (+ second, adversarial critic round)
For survivors: full validation — red→green, regression suite, perf benchmark if a
latency constraint exists. Then a **second, adversarial critic** pass on the
*validated* winner: "is this a real fix or test-gaming/overfit? what does it
break? does it reintroduce a past lesson?" Choose the winner by **validated
evidence**, not phase-5 scores alone.
- **Gate:** winner passes validation and survives adversarial review.

### 8. prod (canary + predefined rollback trigger)
Apply the winner to prod behind a **reversible** step. BEFORE applying, define the
**rollback trigger**, the **observation window**, and the **success metric**.
Deploying is not success — the observation window passing is. (For OpenClaw,
`openclaw-devops verify` + `rollback` back this; otherwise use your deploy's
health gate + revert.)
- **Gate:** observation window passes with no rollback trigger hit.

### 9. close
- **Fixed:** record a lesson (bug · confirmed root cause · refuted hypotheses ·
  fix pattern · regression-test pointer). `debug_session.py close --outcome
  fixed …` writes it into `state/lessons.jsonl` (the fast journal) automatically.
  Then, if the lesson is **durable and project-relevant**, promote it into
  **project-meta canonical memory** per
  [`../../project-meta/references/repo-memory-crud.md`](../../project-meta/references/repo-memory-crud.md)
  (Memory Contract): update only the canonical `agents/*.md` file it belongs to,
  sync mirrors only if structure/high-priority guidance changed, keep provenance.
- If the bug came from a tracked backlog (e.g. openclaw-devops' bugs panel),
  **close its entry**: `openclaw_devops.py bugs --update <BUG-N> --status fixed
  --session <this dbg-id> --lesson "…"`. A session that fixes a tracked bug must
  record the resolution against it.
- If the bug *class* recurs, **promote it to a guardrail** (lint / check / CI
  rule) — don't just document.
- **Not fixed within the loop budget:** **escalate to a human** with the case
  file, what was tried, and the refuted hypotheses.

## Cross-cutting practices

- **Rollback at every gate.** Each phase writes a checkpoint; a downstream gate
  failure rolls back to the last green checkpoint or abandons that candidate.
- **Bounded loop.** Any gate failure may loop back to an earlier phase *with the
  new evidence* (usually `hypotheses`), but `loop_count` is capped (default 3) →
  escalate. Prevents thrashing.
- **Bounded context per agent.** Every dispatched agent reads the case file, not
  the whole repo. Context bloat is itself a failure mode.
- **One discriminating experiment per hypothesis**; always record negative results.
- **Diverse critics beat redundant ones** — give each critic a different lens.
- **Determinism first.** Capture seeds/inputs; flaky bugs go on the observability
  track, not the fixing track.

## Anti-patterns

meta-debug's named failure modes — cite by ID in reviews and close-lessons.
Several map onto project-meta's catalog (cross-referenced below) and are
pressure-tested in [`../tests/pressure-test-scenarios.json`](../tests/pressure-test-scenarios.json).

- **AP-DBG-1 — Fix before a reliable repro + red test exists.** You can't prove
  the fix or guard the regression. (gates: reproduce, tests)
- **AP-DBG-2 — Throwaway repro instead of wiring the red test into existing
  CI/test.** A script not in CI rots and won't catch the next regression.
- **AP-DBG-3 — Blaming the first plausible culprit without a refuting probe.**
  Confirmation bias; record refuted hypotheses so the dead end isn't re-walked.
- **AP-DBG-4 — Single candidate, single critic pass.** No comparison and no
  adversarial check — overfit / test-gaming slips through.
- **AP-DBG-5 — "Deployed, therefore fixed."** No observation window / rollback
  trigger; deploying is not the success signal, the window passing is.
- **AP-DBG-6 — Debug agent ingests the whole repo.** Context-bloat timeout (real:
  a collector hit a ~191k-token request and timed out). Hand each agent the
  bounded case file, not the codebase. Maps to project-meta **AP-COORD-5**
  (read-pattern over-reading) — the case file is a context-mapping digest with
  `path + why` pointers, not the raw repo.
- **AP-DBG-7 — Looping forever instead of escalating.** `loop_count` is capped
  (default 3) → escalate with the case file.

Cross-skill: the **lead never edits inside a worker's sandbox** (phase 6,
Gotchas) is project-meta **AP-COORD-1**; deferring dispatch/review to
project-meta rather than re-deriving it avoids **AP-COORD-4** over-orchestration.

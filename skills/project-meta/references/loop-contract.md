# Loop Contract

The canonical loop specification: any skill that runs an iterative agent loop
(propose→verify→continue-or-stop) declares these six fields somewhere citable,
and checkpoints state to the canonical `loop_state.json` shape below. Existing
loops do not rewrite themselves — each adds a short conformance block that
cites this file (single swappable pointer, per `project-meta-as-root-skill`).

Evidence (cited sparingly; see `proposals/loop-engineering-2026.md` ¶1-4 for
the full grounding): a loop without a declared stopping rule is a named
static-analysis defect class ("Infinite Agentic Loops", 2026); the grader
must run separate from the generator's context (harness-design findings,
2026: a self-grading generator is "almost always confident even when
broken"); file-based state recovers work at ~100% vs 8-13% for chat-only
context (Crab, 2026); checkpoints belong at phase boundaries, not timers.

## The Six Fields

1. **Trigger** — what starts an iteration: a user command, a cron/wakeup, a
   re-audit round, a dispatched worker returning. State it explicitly; a loop
   with an implicit or ambient trigger is undeclared.
2. **Goal** — the completion condition the loop is driving toward, stated so
   an external reader (not just the loop itself) can tell when it's met.
3. **Budget** — a hard stop: token budget, iteration count, or wall-clock
   time (pick at least one). "Loop until nothing changes" / "loop until dry"
   is not a budget — the literature-correct pattern is an empirically-set cap,
   not convergence-seeking (see the proposal's ¶3, "context ceiling").
4. **Verification** — grader separate from doer:
   - **Computational floor (MANDATORY)**: a deterministic check — a script,
     linter, schema validator, or exit-code gate — runs before any
     keep/promote/continue decision. This is the floor every loop must clear;
     it is what makes "the loop declares victory" falsifiable rather than
     self-reported.
   - **Inferential critics (OPTIONAL, stack on top)**: an LLM-judge / adversarial
     reviewer / methodology-critic subagent may add judgment on top of the
     computational floor, but never substitutes for it. Grader separation
     means the critic runs in its own context, not the generator's reasoning
     trace.
5. **State/checkpoint** — file-based, not context-only. Checkpoint at phase
   boundaries (end of an iteration, after a keep/discard record, after a
   round completes) — not on a timer. The canonical shape is `loop_state.json`
   below.
6. **Stopping rule + escalation** — the exact condition(s) that end the loop
   (budget exceeded, max iterations, explicit stop flag, goal met) and what
   happens next: return control to the operator, surface a blocker, or hand
   off to a named follow-up. A loop that can stop without anyone finding out
   is not escalation, it's silence.

## Canonical `loop_state.json` Schema

Lifted from `deep-survey-bfs`'s `templates/loop_state.json` (the shipped
shape that already works) and generalized. A citing loop MAY add fields but
MUST keep these names and meanings so `scripts/loop_state.py` works
unmodified across skills.

```json
{
  "iteration": 0,
  "current_task": "<free-form: label, target id(s), or a short description>",
  "blockers": ["<free-text: anything preventing progress>"],
  "completed_targets": ["<free-form: label or id of finished work>"],
  "next_targets": ["<free-form: label or id of queued work>"],
  "stop_conditions": {
    "max_iterations": 8,
    "budget_spent_over_limit": false,
    "explicit_stop": false
  },
  "budget_spent": {"iterations": 0, "tokens": 0, "seconds": 0}
}
```

Field notes:

- `iteration` — integer, incremented once per checkpoint call.
- `current_task` — free-form; a string or object, whatever the loop's own
  vocabulary needs (e.g. deep-survey-bfs nests `label`/`target_paper_ids`).
- `blockers` — list of free-text strings; empty when nothing blocks progress.
- `completed_targets` / `next_targets` — lists, free-form entries (string or
  object); the ledger of what's done and what's queued.
- `stop_conditions` — the declared thresholds `should-stop` evaluates:
  `max_iterations` (int), plus any budget/explicit-stop keys the loop sets.
  A loop can add domain keys (e.g. deep-survey's `all_critical_gaps_closed`);
  `loop_state.py should-stop` only evaluates the three it knows about
  (budget exceeded, max iterations, explicit stop) and ignores the rest —
  domain-specific stop conditions stay the loop owner's judgment call.
- `budget_spent` — running totals the loop owner updates each checkpoint;
  compared against declared budget field 3 above to decide "budget exceeded".
- `phase` — **OPTIONAL, free-form.** Loops with phase structure (survey
  round/audit/synthesize) may add it; loops without phases (the ratchet,
  which checkpoints at one boundary — end of iteration) omit it. Do not
  force a phase taxonomy onto a loop that doesn't have one.

## Citation Mechanism (dev-time, NOT the runtime resolver)

This is a **dev-time same-repo relative pointer**, not the
`shared-cli-delegation.md` runtime resolver pattern — that pattern is for
skills that need to *execute* project-meta's runtime CLIs on an end user's
machine after install (`repo_memory.py`, `provenance.py`) and must handle
project-meta being absent. Loop-contract citation is different: it is a
same-repo dev-time canon reference (like the orchestration skill's
"Dependency & Canon" pattern) — the citing file is developed and shipped in
the same marketplace checkout as `loop-contract.md`, so a relative link
always resolves at dev time. There is no runtime resolution problem to solve.

A citing skill/reference adds:

1. A relative link to this file: `` [`project-meta/references/loop-contract.md`](../../project-meta/references/loop-contract.md) `` (path depth adjusted to the citing file's location).
2. An inline floor of **6 lines or fewer** restating just enough that the
   citing file is comprehensible standalone (trigger/goal/budget/verify/state/
   stop in one line each, or a condensed 2-3 line summary) — never the full
   six-field writeup duplicated.

## Using `scripts/loop_state.py`

Stdlib-only CLI over a `loop_state.json` path. Verbs:

```bash
python3 loop_state.py init <path> [--max-iterations N]
python3 loop_state.py checkpoint <path> --current-task "<label>" \
    [--completed "<label>"] [--next "<label>"] [--blocker "<text>"] \
    [--budget-tokens N] [--budget-seconds N]
python3 loop_state.py read <path>
python3 loop_state.py should-stop <path> [--max-tokens N] [--max-seconds N]
```

`should-stop` exits **0 = continue**, **1 = stop** (prints the reason to
stdout either way). It evaluates, in order: explicit stop flag, budget
exceeded (any of iterations/tokens/seconds vs. the declared or `--max-*`
limits), max iterations reached. No daemon, no timer — call it at loop
boundaries from the loop owner (a recipe, a mode file, a script).

## Anti-patterns

- **Undeclared loop.** A skill file with iteration/cap/wakeup/stop vocabulary
  but no citation of this contract — caught by `skill_architecture_lint.py`'s
  loop-marker WARN.
- **Self-graded loop.** The generator decides its own keep/promote/stop
  without a computational floor — the "early victory problem"; verification
  field 4's computational floor is not optional.
- **Convergence-seeking without a cap.** "Keep looping until nothing changes"
  with no iteration/budget ceiling underneath it.
- **Context-only state.** A loop that reconstructs progress by re-reading
  chat history instead of a checkpoint file loses ~90% of recovery fidelity
  on interruption (Crab, 2026).
- **Forcing `phase` where there is none.** Don't invent phase names for a
  loop whose only boundary is "end of iteration" — leave `phase` out.

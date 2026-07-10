# Proposal: loop-engineering audit (2026-07) → skill updates

> **Status:** Shipped except L5 (withdrawn) and L7 (deferred, DASH-065). L1-L4+L6 shipped as
> v0.10 (DASH-059..062,064, PR #69, project-meta 1.21.x-1.22).
> Shipped mapping: L1-L4+L6=DASH-059..062,064/PR #69/v0.10 milestone; L5=withdrawn; L7=deferred (DASH-065, unscheduled).
> **Scope:** audit every skill's loop design (iteration structure, verification, state, stopping)
> against the 2025–2026 loop-engineering literature; propose 7 prioritized updates (L1–L7).
> **Grounding:** one very-thorough repo inventory agent + two web-research agents (2026-07-06)
> covering (a) loop mechanics/state management and (b) generate-verify-refine + test-time-compute
> paradigms. Evidence cited inline with confidence flags. Aligns with memories
> `prefer-lightweight-derived-design` (every L extends existing machinery),
> `critic-before-build-canon` (panel gates implementation), `cli-toolkit-doctrine`
> (deterministic prose → CLI), `adversarial-lens-earns-keep` (grader separation).

## 0. Headline finding

The marketplace is **ahead of the ecosystem on loop fundamentals** — the 2026 "loop
engineering" consensus (bounded budgets, generator≠verifier, file-based state across
iterations, append-only lessons) is already implemented here in at least five places.
The real gaps are **uniformity and enforcement**: each skill hand-rolls its own loop
contract, one loop has no resume story, one prose gate has no mechanical floor, one cron
loop has no circuit breaker, and this repo's own phase-lock gates are still exit-0 stubs.

What the 2025–2026 literature converged on (primary sources; hype flagged):

1. **A loop is a specified artifact**: trigger, goal, verification, memory, **stopping rule**
   — formalized as a "loop specification" (arXiv:2607.00038 "Stop Hand-Holding Your Coding
   Agent", 2026); static analysis of "Infinite Agentic Loops" — feedback paths without an
   effective termination condition — is now a named defect class (arXiv:2607.01641, 2026).
   "The loop has a hard stop. Token budget, iteration count, or time limit" (Addy Osmani,
   "Loop Engineering", Jun 2026; Boris Cherny: "My job is to write loops" — secondary-relayed).
2. **The grader is not the doer — in a separate context window.** Claude Code `/goal`
   (shipped ~May 2026) grades the completion condition with a **separate small model** every
   turn; Anthropic's harness-design post (Mar 2026) found a generator asked to self-grade is
   "almost always confident even when broken" and prescribes a skeptical evaluator in its
   own context; Anthropic's rubric-grader "Outcomes" reports +8.4/+10.1% quantified lift
   from isolating the grader from the generator's reasoning trace; the named failure mode is
   the "early victory problem" (verifier passes after superficial checks); CMU's General
   AgentBench (arXiv:2602.18998, Feb 2026) shows parallel sampling only pays with an
   **external verifier** — model self-selection plateaus far below oracle (the "verification
   gap"). Fowler/Böckeler (Apr 2026) give the taxonomy: **computational** (deterministic:
   linters/tests) vs **inferential** (LLM-judge) verification — prefer a computational floor.
3. **Stop early, not at convergence.** The same CMU paper's "context ceiling": more turns
   degrade output past an effective-context knee — the literature's answer to "when to stop"
   is an empirically-set turn/budget cap, **not** loop-until-nothing-changes. ("Loop until
   dry" as a named paradigm: no credible source exists — searched and empty.)
4. **State lives in files, not context.** Chat-only crash recovery scores 8–13% vs ~100%
   with filesystem+chat state (Crab, arXiv:2604.28138); checkpoints belong at **phase
   boundaries**, not timers; Anthropic "Effective harnesses for long-running agents"
   (Nov 2025) prescribes shift-handoff artifacts (progress file, git, a feature list whose
   `passes` flags may only flip false→true, never be deleted); OpenAI's 25-hour Codex run
   (Feb 2026) ran on a four-file stack (frozen spec / plans with a stop-and-fix regression
   rule / runbook / audit-log doc).
5. **Lessons ratchet forward.** Ralph-lineage loops append learnings to `progress.txt` /
   AGENTS.md each iteration; "enforce and measure are universally absent" in shipped tools —
   which this repo's `lesson_registry.py` (capture→promote→enforce→measure) already covers.
6. **Continuous/ambient loops are event-triggered and output-gated.** GitHub Next
   "Continuous AI" (Jun 2025): scripted agent-like workflows over arbitrary autonomy, with
   "Safe Outputs" (default read-only; PR as the human checkpoint); LangChain "Ambient
   Agents" (Jan 2025): Notify/Question/Review as the three human-in-the-loop verbs.
7. **Fleets work when disjoint, fail when entangled.** Stanford CooperBench (Jun 2026):
   two agents *collaborating on shared code* lose ~half their capability vs one agent (the
   "coordination gap"); Anthropic's 16-agent C-compiler build (Feb 2026) succeeded on
   file-based task locking + decomposition and failed exactly where agents converged on one
   monolithic task. This **validates shipped work** — the disjoint-touch-set overlap gate
   (dispatch ledger v2) and the section-disjoint worktree fleet doctrine — and argues for
   enforcing it, not adding collaboration machinery.

## 1. Audit — how each skill's loop measures up

| Skill (version) | Loop | Verification | State/resume | Verdict |
|---|---|---|---|---|
| project-meta 1.21.0 — audit convergence | fix→re-audit, cap 3 rounds, operator escape (`--accept-residuals`) | `audit_ledger.py gate` (deterministic exit code) + Stop/land wiring | audit ledger JSONL | **strong** — matches ¶1–3 |
| project-meta — phase-lock | brainstorm→…→finish gates | `.harness/gates/*.sh` — **all `exit 0` stubs in this repo** | phase-state.json + bypass log | **inert → L6** |
| project-meta — dispatch | reviewer-between-subtasks; retro-inspect tier promotion | fresh reviewer PASS/BLOCKER; `dispatch_ledger.py gate/claim/overlap` | ledger v2 (capsule, budget, checkpoint) | **strong**; 2 designed PreToolUse gates unshipped → L7 |
| dl-research 1.2.1 — ratchet loop | propose→run→keep/discard; budget+patience+user stop; refuse-to-start-unless-known | `validate_ledger.py` MUST; methodology-critic block = hard stop — **but critic invocation is prose-gated** | `runs.jsonl` rows only; **no loop checkpoint/resume** | **gaps → L2, L3** |
| deep-survey-bfs 1.2.1 — BFS + `/loop` mode | audit-gated rounds, 4-round cap; self-paced wakeups | coverage matrix + `coverage_check.py` + `bias_audit.py` + `claims_validate.py` + claims-adversary MUST | `loop_state.json` with stop_conditions — best-in-repo resume story | **strong** — the template for L1/L2 |
| meta-debug 1.2.3 | gate-fail loops back, `MAX_LOOP=3` then escalate — code-enforced | 5 hard gates in `debug_session.py`; 2 critic rounds; checkpoint/rollback per phase | session JSON under `.harness/meta-debug/` | **strong** — matches ¶1–4 |
| openclaw-devops 1.2.1 | external cron loop (`cycle`, flock-guarded); transactional update+auto-rollback | `verify()` multi-check gate | bugs backlog + lessons + snapshot | **no failure-streak circuit breaker → L4** |
| orchestration 0.3.0 | none by design (policy, not engine — AP-COORD-7) | sign-before-emit; synchronous checkpoints | signed contract | **correct as-is** |
| global-meta / calendar / sketch-asset | one-shot verbs / single-pass with human or validator gate | emit-fix dry-run; batch-confirm; `validate_asset_pack.py` | snapshots / manifest | **correct as-is** — no loop needed |

Cross-cutting: an initial audit finding claimed the token-diet D6 CI token-coverage gate
was fixture-only; fresh-review verification **refuted this** — `check_trigger_coverage()`
in `validate_project_meta.py` consumes `evals/triggers.json` (80% floor) and runs as a
blocking CI step since 2026-06-10. L5 is withdrawn (kept below for the record).

## 2. Proposals (priority order)

### L1 — Loop Contract: one canonical loop-specification reference + lint (feat, project-meta)

**Evidence:** ¶1 (loop-specification formalization; infinite-loop defect class); five skills
currently restate the same contract fields in five vocabularies (dl-research
"Refuse To Start Unless Known", deep-survey `stop_conditions`, meta-debug `MAX_LOOP`,
audit "Convergence loop", `/loop` mode prose).

**Scope (new `references/loop-contract.md` + small lint):** define the canonical six-field
loop declaration — **trigger, goal, budget (tokens/iterations/time), verification (with
grader-separation requirement, classified computational vs inferential — a computational
floor is mandatory, inferential critics stack on top), state/checkpoint (file-based),
stopping rule + escalation path**. Existing loops don't rewrite; each adds a short
conformance block citing the contract (single swappable pointer, per
`project-meta-as-root-skill`). Lint leg: extend `skill_architecture_lint.py` to WARN when
a skill file declares a loop (heuristic: cap/iteration/wakeup vocabulary) without citing
the contract. No engine, no new state.

### L2 — Loop-state checkpoint primitive: generalize `loop_state.json` (feat, project-meta + dl-research)

**Evidence:** ¶4 (8–13% vs ~100% recovery; phase-boundary checkpoints; 12-factor #12
stateless reducer); dl-research's ratchet has no resume story — an interrupted run
reconstructs from `runs.jsonl` rows alone; deep-survey-bfs already ships the proven shape.

**Scope:** promote deep-survey's `loop_state.json` shape into a canonical schema in
`references/loop-contract.md` (iteration counter, current_task, blockers, completed/next,
stop_conditions, budget_spent) + a stdlib `loop_state.py` (init/checkpoint/read/should-stop)
in project-meta. dl-research's ratchet mode adopts it (checkpoint after step 6 of each
iteration — a phase boundary, not a timer); deep-survey-bfs swaps its prose-defined
stop-condition evaluation for `should-stop` (closing its one minor gap). Derived, not new:
the schema is lifted from the shipped skill that already works.

### L3 — Mechanize the ratchet's critic gate (feat, dl-research)

**Evidence:** ¶2 (grader≠doer; early-victory problem; verification gap). dl-research's
methodology-critic is a MUST in prose, but nothing forces it to run before promotion —
the exact prose→mechanical graduation `harness-engineering.md` prescribes, and the one
place in the marketplace where a loop's verifier is invoked on the honor system.

**Scope:** extend `validate_ledger.py`: a ledger row that promotes a result (beats keep-rule
and is marked promotable) is invalid unless a critic-verdict row (agent id + verdict +
timestamp) precedes it in `runs.jsonl`. The critic stays an agent; the *presence check*
becomes deterministic — same pattern as `dispatch_ledger.py gate`. Schema addition is
backward-compatible (old ledgers validate under a version field).

### L4 — Cron circuit breaker for openclaw-devops `cycle` (feat, openclaw-devops)

**Evidence:** ¶1 (hard stops), ¶6 (continuous loops need output gates); a fixed-interval
cron that keeps firing into a persistently failing environment is the unbounded-loop
defect class applied at the schedule layer. Today `cycle` bounds *scope* (action catalog,
flock) but not *repetition* — repeated failures rely on human bug-panel review.

**Scope:** persist a consecutive-failure streak in the existing state dir; at N failures
(default 3) `cycle` short-circuits to a `paused` state — logs a bugs-backlog entry
(existing channel = the Notify verb) and exits 0 without acting until an operator
`resume` (or a successful manual `sanity`) clears the streak. Pure extension of
`openclaw_devops.py`; no new store.

### L5 — ~~Wire the D6 token-coverage CI gate~~ (WITHDRAWN — premise refuted on review)

The draft audit claimed the D6 gate was never wired. The fresh-context review of this
proposal's own PR (#68) verified the opposite: `check_trigger_coverage()` in
`scripts/validate_project_meta.py` loads `evals/triggers.json`, enforces an 80%
should-trigger coverage floor, and runs in the **blocking** "project-meta dev validator"
CI step (introduced 2026-06-10). project-meta is the only skill with an `evals/` dir, so
per-skill generalization is currently a no-op. Board item DASH-063 → wontfix. Kept here
as a worked example of the proposal's own ¶2: the finder's claim died under an
independent verifier — grader separation earning its keep on this very document.

### L6 — Fill this repo's phase-lock gate stubs (chore, repo-local — not plugin content)

**Evidence:** all five `.harness/gates/*.sh` are `exit 0` seeds — the phase-lock loop as
deployed here gates nothing, which is the "prose checklist / honor system" anti-pattern the
contract itself names. **Scope:** real checks per phase (e.g. plan → build-plan doc exists
for the active milestone; implement → `ship_plugin.sh validate` green; review → fresh-review
receipt in ledger; finish → board item moved + version bumped). Repo edit only; the
template stays a seed.

### L7 — Verb/turn state plumbing → the two designed PreToolUse gates (infra, project-meta)

**Evidence:** `multi-agent-protocols.md` §Mechanical Enforcement already names the gap:
read-only-verb-write blocking and pre-commit blocking are designed but blocked on
`.harness/current-verb` / `.harness/runner-active` plumbing that doesn't exist. This is
pre-flagged staleness — scheduled last because it's the largest surface and the least
loop-specific.

**Scope:** minimal verb-state file written at verb entry (recipes already have a single
entry point post-D4 staged reads), consumed by two new hook payloads; profile-laddered
(warn standard / block strict), same as the destructive-command guard.

## 3. Explicitly out of scope (researched, rejected)

- **Test-time-compute scaling machinery** (Recursive Tournament Voting, Parallel-Distill-
  Refine — arXiv:2604.16529): engine-layer orchestration; the runtime's workflow judge-panel
  patterns already cover the need. AP-COORD-7.
- **Deterministic replay engine** (SWE-agent `run-replay`, event-sourced trajectories):
  heavy, engine-owned; ledgers + session transcripts + `loop_state.json` give the harness-
  altitude equivalent.
- **`/goal`-style separate-grader model on every Stop:** the Stop hook's deterministic
  gates are the harness-appropriate floor; a grader model is an engine feature.
- **"Loop-until-dry" formalization:** real only as an engine-layer *discovery* pattern
  (K consecutive dry rounds for unbounded finding-hunts — already available in the runtime's
  workflow patterns); for harness task loops the literature-correct design is the bounded
  cap the skills already have — do not add convergence-seeking loops.
- **Scheduled "dreaming"/reflect pass** (Anthropic Managed Agents, May 2026): the lesson
  registry already covers capture→promote→enforce→measure; a cron-driven reflector leg is
  a possible future ratchet but adds a trigger surface this repo doesn't need yet.
- **New ambient/event-triggered agents:** no in-repo trigger source beyond the existing
  cron (openclaw) and land-queue; Safe-Outputs posture is already matched by the ship
  flow's PR-checkpoint. Revisit if a real event stream lands.

## 4. Sequencing & next steps

1. Operator reviews; suggested slice for the next loop-milestone: **L1+L2+L3** (the
   contract, the checkpoint primitive, and the one honor-system gate — smallest coherent
   set that makes every loop in the marketplace declared, resumable, and externally
   verified). L6 is an independent repo-local chore that can ride along; L4 is a
   self-contained openclaw-devops minor; L7 waits for appetite; L5 withdrawn.
2. Per `critic-before-build-canon`: dispatch a fresh adversarial critic panel against the
   chosen L's *plan* before any canon/code edit.
3. Implement via validated-edit → ship → reload; board items track state.

Board items filed (source: this proposal): L1–L7 → **DASH-059…DASH-065**, maturity refined,
status unscheduled — scheduling is a roadmap decision with the operator. DASH-063 (L5)
subsequently marked **wontfix** after the fresh review refuted its premise.

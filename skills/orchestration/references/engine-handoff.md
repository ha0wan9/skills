# Reference: contract → engine handoff

**DASH-11.** A **signed** contract ([`orchestration-contract.md`](orchestration-contract.md)) is
**emitted to the runtime's scripted engine**. This file defines that handoff: when the skill may
call the engine, what it must never do, and how the same contract degrades across runtimes.

This is the **compliant replacement for the killed `autopilot` run-engine**: the skill owns the
contract (policy); it never builds a run loop (mechanism). AP-COORD-7.

## The opt-in posture (precise)

Orchestration is **user-invoked**, and this skill's instructions **name the tool and its cost
surface**. That is exactly the sanctioned opt-in for calling the scripted engine: *"the user invoked
a skill whose instructions tell you to call Workflow"* **and** the two-bar rule's *"a recipe that
names the tool and its cost surface."* So when the user invoked `orchestrate`, the recipe **MAY call
the Workflow tool** to emit the signed contract.

What it still does **NOT** do:

- **Does not enable `ultracode` session-mode** — that is user-only (an `effortLevel` a skill cannot
  set; `effortLevel:"ultracode"` in settings.json silently no-ops if a skill tries).
- **Does not call the engine autonomously, from a hook, or when the user did not invoke
  `orchestrate`.** No background/cross-turn launch. The engine call is foreground, on the user's
  invocation, after a signed + delivered contract.
- **Does not build its own run loop, worker pool, or run-journal** that duplicates the engine
  (AP-COORD-7). It requests a *shape* (`parallelization`); the engine supplies the mechanism.

Reference the engine **generically** ("the scripted-engine tier") in durable prose so a rename
(the historical `workflow` → `ultracode` churn) cannot rot the contract.

## Cross-runtime backings (one contract, three emissions + a floor)

The signed contract is runtime-agnostic policy. It is emitted via whichever backing the runtime has:

| Runtime | Backing | Emission |
|---|---|---|
| **Claude Code** | the **Workflow** tool (scripted) | translate the contract's per-task table into a workflow script: `model_tier` → `agent(... {model})`, `parallelization` → `parallel()`/`pipeline()`, `review_level` → a verify stage, `human_checkpoint` → a `log()` + stop. Called only on the user's `orchestrate` invocation. |
| **Codex** | **OpenAI Agents-SDK** (`codex mcp`) + `.codex/agents/*.toml` roles | a PM/orchestrator script with handoffs + gating; read-only roles → Codex `explorer`, workers → `worker`. (canon: `project-meta/references/multi-agent-protocols.md`, Orchestration Backings.) |
| **OpenClaw / none** | — | **degrade to the Agent/Task subagent-loop floor**: the conductor runs the contract as a prose dispatch loop (fresh worker → fresh reviewer per task, BLOCKER halts). Slower, but the contract still executes. |

**AP-VAL-1 floor:** a contract mechanized on only one runtime, with no backing on another declared
compat runtime **and** no prose fallback, is a gap. The Agent/Task loop is the cross-runtime floor
so no runtime is left with an un-runnable contract.

## Safety invariants applied at the boundary

- **Signed first.** No emission before the contract is signed, delivered, and committed.
- **Checkpoints are synchronous.** A `human_checkpoint` and a BLOCKER review verdict **stop forward
  dispatch** under *any* backing — a background/batched runner must stop on the first BLOCKER and
  return, never batch-collect them to end-of-run (that reopens the AP-COORD-2 window). Resume is
  re-entry after the user decides (`resumeFromRunId` on Claude Code; Codex re-entry), never a license
  to run past the blocker.
- **Budget hint ≠ engine budget.** The contract's budget hint informs *signing*; it does not set the
  engine's `budget`. The skill cannot control the engine (AP-COORD-7).
- **Promotion-time safety.** The engine runs background/cross-turn, so turn-scoped hooks (Stop,
  pre-commit) cannot gate it — apply the contract's invariants when the contract is *promoted to a
  run*, not via a hook on the run itself.
- **Codex operating loop preservation.** When the signed contract's `operating_loop` is
  `codex-long-running`, `goal-run`, or `heartbeat-monitor`, the Codex Agents-SDK emission must carry
  the artifact surface, writeback target, and verification oracle into the run prompt/handoff.
  Elastic profile state is advisory visibility only; it must not relax approval-sensitive gates.

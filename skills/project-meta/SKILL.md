---
name: project-meta
description: "Bootstrap, audit, and evolve a repository agent-work harness via /project-meta commands — /project-meta init, status, validate, deliver, audit. Manages canonical memory (AGENTS.md), local USER.md preference presets, and an existing agent-facing documentation framework with user-facing delivery; instantiates canonical templates; sets trigger policy and behavior guardrails; coordinates multi-agent dispatch with pre-commit delivery; handles mirror sync, multi-host manifests, phase-lock gates, and skill-critic pressure-testing; promotes validated lessons into durable knowledge. Use when starting work in a repo, repairing repo memory, improving agent instructions, coordinating project work, authoring or auditing a skill, or turning validated lessons into durable harness updates."
metadata: {version: 1.26.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Project Meta

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace
> _OpenClaw: untested — installs Claude Code / Codex harness artifacts._

This file is the router: trigger policy, arbitration, and routing summaries only. Procedures live in `recipes/<verb>.md` and `references/*.md`; load only what the task needs.

## Trigger Decision

Use this skill for any of these triggers:

- Command: `/project-meta <command>` — `init`, `plan`, `roadmap`, `status`, `validate`, `deliver`, `audit`, `settings`.
- Bootstrap: entering a repo where agent instructions, memory, or read order matter.
- Memory: creating, repairing, splitting, pruning, or syncing canonical memory files.
- Harness: improving agent instructions, behavior guardrails, validation loops, or project operating rules.
- Documentation: updating agent-facing docs, user-facing docs, or pre-commit delivery expectations.
- Iteration: a project lesson, failure, review finding, or recurring workflow should become durable guidance.
- Coordination: explicit multi-agent ask, or complexity warrants plan/delegate/review.
- User-preference: create, reset, or change local `USER.md` options.
- Settings: view/change the enforcement profile (`HARNESS_PROFILE`, or its floor/ceiling), or enable/disable an optional capability (hooks, phase-lock, multi-host, issue-tracker, code-graph, land-queue) after init — route to `settings`, not a full `init`.

Do not use the skill for ordinary implementation work that touches none of the above.

## Bootstrap Order

1. Find repo-level shared docs (`README.md`), the canonical project-memory file, and the canonical user-preference file.
2. `/project-meta init` must not depend on existing `USER.md` — load the init recipe and create or repair project memory first.
3. Read canonical project memory when it exists; it routes what to load next — when it points to `agents/*.md`, load only task-relevant files.
4. Inspect shared docs lightly (title, TOC, heading map); read fully only when short or directly relevant.
5. Read the canonical user-preference file when it exists.
6. Load `templates/*.md` only when instantiating or reviewing artifacts; load references per *When To Load References* below.
7. Near session start, when the repo carries git worktrees, run the Worktree Trim Contract: `python3 scripts/worktree_audit.py --target-root . --base <base>`, then trim stale, surface in-progress, route mergeable.

## Core Rules

- Detect the primary agent tool before assigning canonical-vs-mirror roles: Claude Code primary → `CLAUDE.md` canonical, `AGENTS.md` mirror; Codex/GPT-5.x primary → the reverse; `.github/copilot-instructions.md` always secondary ([mirrors-and-updates](references/mirrors-and-updates.md)). No established convention → default `AGENTS.md` + `USER.md`.
- On first init or a preference reset, use `USER.template.md` as a questionnaire and render only selected items into ignored local `USER.md` via `scripts/render_user_preferences.py`; never copy or commit the template into a target repo.
- Shared docs are the primary project explanation but read them selectively; keep a README structure map in agent-facing docs once one grows structurally important.
- References define protocols; templates define copyable seeds. Instantiated artifacts must be project-concrete and keep their provenance frontmatter (fields in *Gotchas*).
- The canonical `/project-meta <command>` route table lives in [cli-command-patterns](references/cli-command-patterns.md); this entrypoint stays trigger policy + routing summaries, never per-command workflow contracts.
- Prefer a short memory loader plus narrow topical files in larger repos; restructure missing/bloated/messy memory instead of working around it (AP-MEM-1..3); keep memory concise, durable, free of session-only notes.
- Update only the canonical file matching the lesson; sync mirrors only on canonical-structure or high-priority changes. Verify external guidance from primary sources when it may have changed.
- Derive the **read-pattern**: default `minimal`; escalate to `context-mapping` only on design signals or cross-subsystem scope, stating the choice in the delivery ([execution-policy](references/execution-policy.md) "Read-Pattern Derivation").
- **MUST use this skill when its trigger conditions match.** Invoke it before any non-trivial harness edit; a deliberate skip must be documented inline with the reason (AP-SKL-2 — soft "consider" language is the failure mode this replaces).
- **MUST resolve trigger collisions explicitly** before acting. Default: the narrower skill wins; otherwise delegate to the peer with an explicit hand-off rather than duplicating procedure (AP-SKL-3; table below).
- Treat repeated agent mistakes as missing harness — improve docs, routing, validation, or tooling, not just the output; keep the harness agent-legible.
- **MUST dispatch via the multi-agent protocol when its conditions match** ([multi-agent-protocols](references/multi-agent-protocols.md)); editing recipes dispatch, read-only verbs never edit; escalate to a scripted engine only on opt-in/scope (AP-COORD-4).
- **MUST converge gating audits — they are multi-round.** After BLOCKER/MAJOR fixes (audit itself stays read-only), re-audit the changed scope with fresh reviewer context until a round reports zero BLOCKER+MAJOR, cap 3 re-audit rounds; at the cap, do not ship — surface residuals. Record every round; `audit_ledger.py gate` enforces. Procedure: `recipes/audit.md`, per `references/loop-contract.md`.
- Preserve the agent-facing documentation framework; show a concise pre-commit delivery separating user-facing from agent-facing docs before committing harness changes.

## Skill Arbitration

When a request matches `project-meta` *and* a peer skill, state the resolution before acting:

| Request shape | Owner | `project-meta`'s role |
|---|---|---|
| Bootstrap repo memory, audit harness, install hooks, render/sync mirrors, change `USER.md` | **`project-meta`** | acts |
| Literature review / survey, "research X" with no experimental component | **`deep-survey-bfs`** | dispatches; init first if no harness |
| DL research study, runs, ablations, autonomous ratchet loop | **`dl-research`** | dispatches; ditto |
| Debug / root-cause a hard, flaky, or recurring bug | **`meta-debug`** | provides the harness it reads/writes (memory, dispatch, lesson CRUD); init first if none |
| Mixed "research X and set up the repo" | **`project-meta` first** | init/audit, then delegate the research portion explicitly |
| Package survey/research output as a target-repo artifact | **`project-meta`** | wraps the peer's output for delivery (provenance, mirrors, delivery) |
| Schedule/classify/bulk-edit calendar events | **`calendar-crud-workflow`** | defer; init only if the work lives in a repo needing a harness |
| Claude *or Codex* config profile, or the global config root (`~/.claude*`, `~/.codex*`) | **`global-meta`** | defer; `project-meta` owns repo memory, not user-level config dirs |
| Orchestrate a milestone across agents: draft/review/cost/sign an **orchestration contract** | **`orchestration`** | defer the contract workflow; stays canonical for the cited dispatch canon; ad-hoc dispatch inside verbs only |
| Multi-agent orchestration *execution* — spawning, scripted workflows, effort tier | **the runtime engine** (user-gated) | owns *policy*, delegates *execution*; never re-implement the engine (AP-COORD-7) |
| Intra-task software-engineering *method* (brainstorm→plan→TDD→review→verify) | **the methodology plugin** (external, not bindable) | defer intra-task process; own harness/skill authoring + cross-task governance; assume its bootstrap is mandatory — additive, never contradictory |

If an arbitration is unclear, ask the user before invoking either skill. Never silently invoke both.

## Gotchas

- **`USER.md` is local-only and Git-ignored** — never stage or commit it; merge `.gitignore.template` into the target repo first.
- **`USER.template.md` is a skill-layer questionnaire, not a target-repo file** — render selections into ignored local `USER.md` via `scripts/render_user_preferences.py`.
- **`templates/*.md` are skill-level seeds, not a target-repo template library** — instantiate at semantic project paths (`agents/delegation.md`, …), never a generic `agents/templates/` directory.
- **Every instantiated artifact carries a YAML provenance frontmatter block** (`artifact_name`, `instantiated_from`, `source_reference`, `project_scope`, `owner`, `review_policy`, `last_reviewed`) — never strip these fields; the manifest and audit checks rely on them.
- **`scripts/validate_project_meta.py` is the dev-repo validator** (not shipped; needs a git working tree). The validator that ships with the skill is `scripts/validate_target_harness.py`.
- **Mirror roles depend on tool context** — always detect the primary tool before syncing; write durable rules into topical files, not into the loader.
- **`/project-meta init` does not depend on existing `USER.md`** — ask for preset and checklist selection first, then render `USER.md`.

## Recipes

On `/project-meta <command>`, load exactly **one** recipe; it owns that verb's workflow end-to-end (trigger / mode / references / steps / output / anti-patterns):

| Verb | Mode | Recipe |
|---|---|---|
| `init` | editing | [`recipes/init.md`](recipes/init.md) |
| `plan` | editing | [`recipes/plan.md`](recipes/plan.md) |
| `status` | read-only | [`recipes/status.md`](recipes/status.md) |
| `validate` | read-only | [`recipes/validate.md`](recipes/validate.md) |
| `deliver` | read-only | [`recipes/deliver.md`](recipes/deliver.md) |
| `audit` | read-only by default | [`recipes/audit.md`](recipes/audit.md) |
| `settings` | editing (read-only view by default) | [`recipes/settings.md`](recipes/settings.md) |
| `roadmap` | editing | [`recipes/roadmap.md`](recipes/roadmap.md) |
| `refine` | editing (`roadmap` sub-workflow; standalone ok) | [`recipes/refine.md`](recipes/refine.md) |
| `mirror-linear` | editing (issue-tracker Track Loop sub-workflow) | [`recipes/mirror-linear.md`](recipes/mirror-linear.md) |

Cross-cutting policy (route contract, reserved verbs, shared rules, footer contract) lives in [cli-command-patterns](references/cli-command-patterns.md).

## Quick Workflow

1. Bootstrap from canonical memory + shared docs (selective read).
2. Classify: `/project-meta <verb>` → its recipe; otherwise → the matching reference below.
3. Resolve arbitration if a peer could match; derive the read-pattern (Core Rules).
4. Apply the single matching procedure; fix messy structure as you go (AP-MEM-1..3).
5. Write back durable lessons only if they pass the *End Check*.

## When To Load References

| Task | Load / run |
|---|---|
| `init`, project lifecycle, preserve lessons, decide what evolves | [project-lifecycle](references/project-lifecycle.md) |
| Reset/change local `USER.md` | [project-lifecycle](references/project-lifecycle.md), then `scripts/render_user_preferences.py --reset` |
| Interpret `/project-meta` workflows; change the route table | [cli-command-patterns](references/cli-command-patterns.md) |
| Behavior guardrails for editing/reviewing project memory | [agent-behavior-protocol](references/agent-behavior-protocol.md) |
| Hard-stops, budgets, worker constraints for bounded execution | [execution-policy](references/execution-policy.md), then `templates/execution-rules.md` when instantiating |
| Agent-facing docs, user-facing docs, pre-commit delivery | [documentation-delivery](references/documentation-delivery.md) |
| Instantiate/review artifacts from skill templates | [documentation-delivery](references/documentation-delivery.md) + the relevant `templates/*.md` seed |
| Monolith vs split memory; keep the loader thin | [repo-memory-structure](references/repo-memory-structure.md) |
| Inspect long shared docs with minimal context | `python3 scripts/extract_doc_context.py <doc> --index`, then `--heading`/`--query` |
| CRUD rules for canonical memory files | [repo-memory-crud](references/repo-memory-crud.md) |
| Mirror policy for tool-specific instruction files | [mirrors-and-updates](references/mirrors-and-updates.md) |
| Audit/redesign a harness (legibility, enforcement, cleanup) | [harness-engineering](references/harness-engineering.md) |
| Multi-agent coordination | [multi-agent-protocols](references/multi-agent-protocols.md) |
| Write/audit a harness rule; diagnose recurring agent failures | [anti-patterns](references/anti-patterns.md) — cite AP ids when a rule fixes a named pattern |
| Author/audit a skill; scaffold from `templates/SKILL.template.md` | [writing-skills](references/writing-skills.md) + [skill-critics](references/skill-critics.md) — the publish gate |
| Install/diagnose phase-lock workflow gates | `templates/phase-lock-contract.md`; verify via `python3 scripts/phase_lock_check.py --harness-dir <repo>/.harness` (also the Stop-hook payload) |
| Hooks pack, `HARNESS_PROFILE`, hook payloads (receipt/lesson/guards/env-probe), elastic profiles | `templates/hooks/README.md` (+ `scripts/derive_profile.py` for elastic resolution) |
| Lint canonical memory for stale citations | `python3 scripts/memory_staleness.py --target-root <repo>` (advisory leg of `validate`/`audit`) |
| Wire/audit an external issue tracker (Linear/GitHub/Jira) | [issue-tracking-integration](references/issue-tracking-integration.md), then `templates/issue-tracking.md`; `init --issue-tracker <tracker>` / `settings enable` |
| Wire/audit a code-knowledge-graph engine | [code-graph-integration](references/code-graph-integration.md), then `templates/code-graph.md`; `init --code-graph` / `settings enable` |
| Deterministic parallel-branch landing; merge-tax diagnosis | [land-queue-integration](references/land-queue-integration.md), then `templates/land-queue.md` + `templates/land/land.sh`; `init --land-queue` / `settings enable` |
| Codex-primary operating loop (durable threads, disk-backed memory, steering, check-ins) | [codex-operating-loop](references/codex-operating-loop.md), then `templates/codex-operating-loop.md` |
| Project Board CRUD or board enforcement | [project-board-crud](references/project-board-crud.md) — `board.py` is the only writer; scaffold via `init --board` |
| Mirror board rows to Linear | [linear-mirror](references/linear-mirror.md) + `recipes/mirror-linear.md`; push-only, interactive-only — never live-push headless |
| Per-host manifests from canonical memory; mirror drift | [multi-host-manifests](references/multi-host-manifests.md); `scripts/render_host_manifests.py` (`--dry-run` previews) |
| Pressure-test MUST-rules; design scenarios for a new MUST | [pressure-testing](references/pressure-testing.md); fixture `templates/pressure-test-scenarios.json`; run `scripts/pressure_test_skill.py` |
| Plan/milestone risk score → review-tier floor + readiness | [review-tier](references/review-tier.md) "Plan-time risk rubric"; `python3 scripts/risk_score.py --scope N … --reversibility N` (advisory) |
| Trim/route git worktrees at session start | [worktree-hygiene](references/worktree-hygiene.md) + `scripts/worktree_audit.py` |

## Output Footer

End every invocation with:

```
project-meta/<verb> done — <N> file(s) written, <N> file(s) read, memory updated: <yes|no>, delivery shown: <yes|no>
```

Omit zero counts. Editing verbs (`init`, `plan`, `roadmap`, `refine`, `settings`, `mirror-linear`) additionally write `.harness/last-turn-meta.json` via `scripts/last_turn_meta.py` — machine-counterpart contract in [cli-command-patterns](references/cli-command-patterns.md).

## End Check

- Would a future agent waste time or repeat this discovery without the note? Is it durable, repo- or user-relevant, and actionable?
- Should the lesson stay documentation, or become a linter, script, template, or recurring cleanup?
- Has the pre-commit delivery been shown when a commit will be created?
- If the note passes, update the matching canonical memory file; otherwise leave memory untouched.

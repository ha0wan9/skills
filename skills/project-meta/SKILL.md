---
name: project-meta
description: "Bootstrap, audit, and evolve a repository agent-work harness via /project-meta commands — /project-meta init, status, validate, deliver, audit. Manages canonical memory (AGENTS.md), local USER.md preference presets, and an existing agent-facing documentation framework with user-facing documentation delivery; instantiates canonical templates via project-level artifact instantiation; sets trigger policy and behavior guardrails; coordinates multi-agent dispatch with review and pre-commit delivery; handles mirror sync, multi-host manifests, phase-lock gates, a skill-critic suite, and pressure-testing of MUST-rules; and promotes validated lessons into durable knowledge. Use when starting work in a repo, creating or repairing repo memory, improving agent instructions, coordinating complex project work, authoring or auditing a skill, or turning validated lessons into durable harness updates."
metadata: {version: 1.6.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# Project Meta

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace
> _OpenClaw: untested — installs Claude Code / Codex harness artifacts (hooks, mirrors)._

Use this skill when starting work in a repo, designing or maintaining project memory, improving agent instructions, coordinating complex project work, or turning validated lessons into durable project harness updates.

Keep this file as the skill entrypoint. Load the linked reference files only as needed.

## Trigger Decision

Use this skill for any of these triggers:

- Command trigger: the user says `/project-meta <command>`, especially `init`, `plan`, `roadmap`, `status`, `validate`, `deliver`, `audit`, or `settings`.
- Bootstrap trigger: entering a repo or project where agent instructions, memory, or read order matter.
- Memory trigger: creating, repairing, splitting, pruning, or syncing canonical memory files.
- Harness trigger: improving agent instructions, behavior guardrails, validation loops, or project-specific operating rules.
- Documentation trigger: updating the existing agent-facing docs, user-facing docs, or pre-commit delivery expectations.
- Iteration trigger: a project lesson, failure, review finding, or recurring workflow should become durable guidance.
- Coordination trigger: the user explicitly asks for multi-agent work, or task complexity warrants planning, delegated execution, and review.
- User-preference trigger: the user asks to create, reset, or change local `USER.md` options.
- Settings trigger: the user asks to view or change the harness enforcement profile (`HARNESS_PROFILE`) or to enable/disable an optional capability (hooks, phase-lock, multi-host, issue-tracker) after init — route to `settings`, not a full `init`.

Do not use the skill for ordinary implementation work that does not touch project memory, operating rules, coordination, or durable knowledge.

## Bootstrap Order

1. Find repo-level shared docs such as `README.md`, plus the repo's canonical project-memory and user-preference files.
2. If this is `/project-meta init`, do not depend on existing `USER.md`; load the init workflow and create or repair project memory first.
3. Read the canonical project-memory file when it exists; use it as the routing layer for what to load next.
4. Inspect shared docs lightly before full loading: title, first section, table of contents, heading map, or agent-facing README structure map. Read the full shared doc only when it is short or directly relevant to the task.
5. Read the canonical user-preference file when it exists.
6. If the project-memory file routes to `agents/*.md` or another topical-memory directory, load only the files relevant to the current task.
7. Load canonical templates from `templates/*.md` only when instantiating or reviewing project-specific artifacts.
8. Load this skill's reference files only when you need them:
   - [`references/project-lifecycle.md`](references/project-lifecycle.md)
   - [`references/cli-command-patterns.md`](references/cli-command-patterns.md)
   - [`references/agent-behavior-protocol.md`](references/agent-behavior-protocol.md)
   - [`references/execution-policy.md`](references/execution-policy.md)
   - [`references/documentation-delivery.md`](references/documentation-delivery.md)
   - [`references/repo-memory-structure.md`](references/repo-memory-structure.md)
   - [`references/repo-memory-crud.md`](references/repo-memory-crud.md)
   - [`references/mirrors-and-updates.md`](references/mirrors-and-updates.md)
   - [`references/harness-engineering.md`](references/harness-engineering.md)
   - [`references/multi-agent-protocols.md`](references/multi-agent-protocols.md)
   - [`references/anti-patterns.md`](references/anti-patterns.md)
   - [`references/writing-skills.md`](references/writing-skills.md)
   - [`references/multi-host-manifests.md`](references/multi-host-manifests.md)
   - [`references/pressure-testing.md`](references/pressure-testing.md)
   - [`references/worktree-hygiene.md`](references/worktree-hygiene.md)
   - [`references/review-tier.md`](references/review-tier.md)
9. Near session start, before substantive work, run the **Worktree Trim Contract** when the repo carries git worktrees: `python3 scripts/worktree_audit.py --target-root . --base <base>`, then trim stale, surface in-progress, and route mergeable per [`references/worktree-hygiene.md`](references/worktree-hygiene.md).

## Core Rules

- Detect the primary agent tool before assigning canonical-vs-mirror roles. When Claude Code is the primary consumer, `CLAUDE.md` is the canonical entrypoint and `AGENTS.md` is the mirror. When Codex/GPT-5.4 is primary, `AGENTS.md` is canonical and `CLAUDE.md` is the mirror. In both cases, treat `.github/copilot-instructions.md` as secondary. See `references/mirrors-and-updates.md` for the tool-awareness policy.
- If the repo has no established convention, default to `AGENTS.md` for project memory and `USER.md` for stable user preferences.
- Default: on first project init, or when the user asks to reset or change local preferences, use the installed `USER.template.md` as a questionnaire and target-config input. Ask which preset and checklist items to enable, then create or repair ignored local `USER.md` with only selected checked preferences. Prefer `scripts/render_user_preferences.py` when available. Do not copy or commit `USER.template.md` into a target repo by default.
- Shared/user-facing docs are the primary project explanation, but primary does not mean eager full-context loading. Use selective reads unless the task requires the whole document.
- If a shared doc becomes long or structurally important, maintain a README structure map in agent-facing documentation. Store headings, section purposes, routing hints, and update triggers there; do not copy user-facing prose.
- References define protocols; templates define copyable skill-level seeds. Project-level artifacts instantiated from Project Meta seeds must be concrete to that project and keep `instantiated_from`, `source_reference`, owner, review policy, and last review metadata.
- The canonical `/project-meta <command>` route table lives in `references/cli-command-patterns.md`. Keep this entrypoint to trigger policy and reference-routing summaries; do not duplicate command workflow contracts here.
- Default: in larger repos, prefer a short project-memory loader/index plus narrow topical memory files.
- If the repo-memory structure is missing, bloated, inconsistent, or messy enough to slow future work, restructure it instead of working around it.
- Keep repo memory concise, durable, and free of speculative or session-only notes.
- Update only the canonical file that matches the lesson learned. Sync mirrors only when canonical structure or high-priority guidance changed.
- Verify external best practices from official or primary sources when the task depends on tooling or framework guidance that may have changed.
- **MUST use this skill when its trigger conditions match.** When a request matches one of the triggers above (`/project-meta` command, bootstrap, memory CRUD, harness work, documentation delivery, iteration, coordination, or user-preference), invoke this skill before any non-trivial harness edit. If you decide to skip the skill deliberately, document the decision and the reason inline so the user can review. Soft "consider" language is the failure mode this rule replaces (see `references/anti-patterns.md` AP-SKL-2).
- **MUST resolve trigger collisions explicitly.** When a request would also match `deep-survey-bfs` or `dl-research` (or another peer skill), state the arbitration before acting. Default contract: a *narrower* skill wins; otherwise this skill delegates to the survey or research skill with an explicit hand-off, rather than duplicating procedure (see AP-SKL-3 and the Skill Arbitration table below).
- Treat repeated agent mistakes as missing harness: improve documentation, routing, validation, or tooling instead of only patching the immediate output.
- Make the harness agent-legible: a concise map, versioned sources of truth, selective loading, behavior guardrails, and rules that can be verified or promoted into tooling.
- Preserve the existing agent-facing documentation framework and pair it with user-facing documentation prepared for user review.
- **MUST** dispatch via the multi-agent protocol when its conditions match (see `references/multi-agent-protocols.md`); editing recipes dispatch, read-only verbs never edit; escalate to a scripted engine only on opt-in/scope, never raw file count (AP-COORD-4).
- Before committing harness changes, present a concise delivery for user review that separates user-facing documentation from agent-facing documentation.

## Skill Arbitration

When the user's request would match `project-meta` *and* a peer skill on this marketplace, resolve as follows. Always state the resolution before acting.

| Request shape | Owning skill | `project-meta`'s role |
|---|---|---|
| Bootstrap repo memory, audit harness, install hooks, render mirrors, sync `CLAUDE.md` / `.github/copilot-instructions.md`, change `USER.md` preferences | **`project-meta`** | acts |
| Literature review, survey of a topic, "research X for me" *with no experimental component*, expand or audit an existing survey | **`deep-survey-bfs`** | dispatches; if no harness exists in the survey's repo, run `/project-meta init` first, then hand off |
| DL research study (frame → experiments → eval → synthesize), launch and monitor runs, ablation design, autonomous ratchet loop | **`dl-research`** | dispatches; ditto |
| Debug / root-cause / systematically fix a hard, flaky, or recurring bug (gated repro → red test → hypotheses → top-k sandbox fixes → validate → ship) | **`meta-debug`** | provides the harness it reads/writes: `meta-debug` collects context in project-meta memory layout, dispatches its top-k sandbox fixes via project-meta's multi-agent protocol, and promotes lessons into canonical memory via project-meta's CRUD rules. Run `/project-meta init` first if no harness exists. |
| Mixed: "research X and set up the repo for me" | **`project-meta` first**, then peer | run init/audit, then explicitly delegate the research portion |
| Survey or research output needs to be packaged as a target-repo artifact (with provenance frontmatter, mirror sync, delivery summary) | **`project-meta`** | wraps the peer's output for delivery |
| Schedule, classify, or bulk-edit calendar events (CRUD across Google/Apple/Notion/MCP calendars) | **`calendar-crud-workflow`** | not this skill — defer; run `/project-meta init` only if the calendar work lives in a repo that needs a harness |
| Create/manage a Claude *or Codex* config profile, or the global config root (`~/.claude*`, `~/.codex*`) | **`global-meta`** (supersedes `profile-creator`) | not this skill — defer; `project-meta` owns repo memory, not user-level config dirs (`global-meta` reuses project-meta's engine) |
| Multi-agent orchestration *execution* — spawning/parallelizing subagents, scripted workflows, effort tier | **the runtime engine** (Claude Code Workflow / "ultracode"; Codex Agents-SDK) — not a skill | `project-meta` owns the *policy* (when to dispatch, review/verify topology) and delegates *execution* to the engine. It recommends/prepares but **cannot enable it** (user-gated). Never re-implement it — AP-COORD-7. Reference it generically ("scripted-engine tier"), not by name. |
| Intra-task software-engineering *method* (brainstorm→plan→TDD→review→verify) | **the methodology plugin** (e.g. `superpowers`) — external, not bindable | defer for intra-task process; `project-meta` *reclaims* only harness/skill authoring + cross-task governance. Assume the methodology's SessionStart bootstrap is mandatory/uncontrollable — be additive, never contradictory. |

If an arbitration is unclear, ask the user before invoking either skill. Never silently invoke both.

## Gotchas

Non-obvious traps the agent will hit without being warned. Keep these here, not in references — the agent reads them before encountering the situation.

- **`USER.md` is local-only and Git-ignored.** Never stage or commit it. The skill's `.gitignore.template` must be merged into the target repo's `.gitignore` before any `USER.md` exists, otherwise the first init may track it accidentally.
- **`USER.template.md` is a skill-layer questionnaire, not a target-repo file.** Do not copy it into target repos. Render selected presets and checked items directly into ignored local `USER.md` via `scripts/render_user_preferences.py`.
- **`templates/*.md` are skill-level seeds, not a target-repo template library.** Instantiate at semantic project paths (`agents/delegation.md`, `agents/pre-commit-delivery.md`, `agents/readme-structure.md`, etc.); do not commit a generic `agents/templates/*.md` directory in the target repo.
- **Every instantiated artifact carries a YAML provenance frontmatter block** (`artifact_name`, `instantiated_from`, `source_reference`, `project_scope`, `owner`, `review_policy`, `last_reviewed`). Do not strip these fields when editing — the manifest and audit checks rely on them.
- **`scripts/validate_project_meta.py` requires a git working tree** for the `check_memory_boundaries` git ignore checks. Outside one, those sub-checks are skipped (the script no longer crashes), but a full validation still requires running from the dev repo or a git checkout.
- **Mirror roles depend on tool context.** When Claude Code is the primary agent, `CLAUDE.md` is canonical and `AGENTS.md` is the mirror. When Codex is primary, the reverse. Always detect tool context before syncing. In both cases, write durable rules into topical files, not into the loader.
- **`/project-meta init` does not depend on existing `USER.md`.** Do not assume preferences exist before init runs; ask for preset and checklist selection first, then render `USER.md`.

## Recipes

When the user invokes `/project-meta <command>`, route via the recipes directory. Each recipe owns one verb's workflow end-to-end (trigger / mode / required references / steps / output / anti-patterns). Load **one** recipe per invocation:

| Verb | Mode | Recipe |
|---|---|---|
| `init` | editing | [`recipes/init.md`](recipes/init.md) |
| `plan` | editing | [`recipes/plan.md`](recipes/plan.md) |
| `status` | read-only | [`recipes/status.md`](recipes/status.md) |
| `validate` | read-only | [`recipes/validate.md`](recipes/validate.md) |
| `deliver` | read-only | [`recipes/deliver.md`](recipes/deliver.md) |
| `audit` | read-only by default | [`recipes/audit.md`](recipes/audit.md) |
| `settings` | editing (read-only view by default) | [`recipes/settings.md`](recipes/settings.md) |

Cross-cutting policy (route contract, reserved verbs, shared rules, implementation risks) lives in [`references/cli-command-patterns.md`](references/cli-command-patterns.md). Recipes own *how each verb works*; that reference owns *what's true across all verbs*.

When the request is not a `/project-meta` command but matches another trigger (bootstrap, memory CRUD, harness work, etc.), don't load a recipe — go straight to the matching reference per *When To Load References* below.

## Quick Workflow

Triage by task class, then delegate to the matching recipe or reference. SKILL.md is the router; procedures live in recipes and references. If a step's *how* is more than one line, it belongs there, not here.

1. Bootstrap context from canonical memory + shared docs (selective read).
2. Classify the task:
   - `/project-meta <verb>` command → load `recipes/<verb>.md`
   - `bootstrap` / `memory-crud` / `harness-design` / `iteration` / `mirror-sync` / `coordination` / `delivery` (no explicit verb) → matching reference per *When To Load References*
   - Derive the **read-pattern** (orthogonal to verb mode and dispatch tier): default `minimal` (just-in-time narrow reads); escalate to `context-mapping` only on design signals or `semantic_scope >= cross_subsystem`, and state the choice in the delivery. See [`references/execution-policy.md`](references/execution-policy.md) "Read-Pattern Derivation".
3. Resolve skill arbitration if a peer skill could also match — see *Skill Arbitration* above.
4. Load the **single** recipe or reference whose scope matches the task class.
5. If the current structure is messy, fix it as part of the task — see [`references/anti-patterns.md`](references/anti-patterns.md) AP-MEM-1..3.
6. Apply the recipe's or reference's procedure. Write durable lessons back to canonical memory only if they pass the *End Check*.

Detail for each step lives in the artifact owning that step:
- step 2 (verb commands): `recipes/<verb>.md`
- step 1, 4 (no-verb tasks): [`references/repo-memory-structure.md`](references/repo-memory-structure.md)
- step 3: *Skill Arbitration* table above + [`references/multi-agent-protocols.md`](references/multi-agent-protocols.md)
- step 5: [`references/harness-engineering.md`](references/harness-engineering.md), [`references/anti-patterns.md`](references/anti-patterns.md)
- step 6: [`references/repo-memory-crud.md`](references/repo-memory-crud.md), [`references/agent-behavior-protocol.md`](references/agent-behavior-protocol.md)

## When To Load References

- Need to run `/project-meta init`, start a project, preserve lessons across iterations, or decide what should evolve after project work:
  - load [`references/project-lifecycle.md`](references/project-lifecycle.md)
- Need to reset or change local `USER.md` options:
  - load [`references/project-lifecycle.md`](references/project-lifecycle.md), then run `python3 scripts/render_user_preferences.py --target-root <repo> --reset`
- Need to interpret `/project-meta <command>` workflows or change the supported command route table:
  - load [`references/cli-command-patterns.md`](references/cli-command-patterns.md)
- Need behavior guardrails for any agent editing, reviewing, or refactoring project memory:
  - load [`references/agent-behavior-protocol.md`](references/agent-behavior-protocol.md)
- Need hard-stop categories, soft budgets, or worker constraints for bounded-execution agents (Codex-class workers, scope gates, halt-and-ask rules):
  - load [`references/execution-policy.md`](references/execution-policy.md), then [`templates/execution-rules.md`](templates/execution-rules.md) when instantiating
- Need to create or review agent-facing docs, user-facing docs, or pre-commit delivery:
  - load [`references/documentation-delivery.md`](references/documentation-delivery.md)
- Need to instantiate or review project-specific artifacts from skill-level templates:
  - load [`references/documentation-delivery.md`](references/documentation-delivery.md), then the relevant `templates/*.md` seed
- Need to decide monolith vs split memory, or how the project-memory loader should stay thin:
  - load [`references/repo-memory-structure.md`](references/repo-memory-structure.md)
- Need to inspect long shared docs while minimizing context:
  - use `python3 scripts/extract_doc_context.py <doc> --index`, then a bounded `--heading` or `--query` extraction
- Need create/read/update/delete rules for canonical memory files:
  - load [`references/repo-memory-crud.md`](references/repo-memory-crud.md)
- Need mirror policy for tool-specific instruction files:
  - load [`references/mirrors-and-updates.md`](references/mirrors-and-updates.md)
- Need to audit or redesign a repo-memory harness for agent-legibility, enforcement, or recurring cleanup:
  - load [`references/harness-engineering.md`](references/harness-engineering.md)
- User explicitly asks for multi-agent coordination, or task complexity warrants planning, delegated execution, and review:
  - load [`references/multi-agent-protocols.md`](references/multi-agent-protocols.md)
- About to write or audit a harness rule, design a skill, set up coordination, or diagnose recurring agent behaviour failures:
  - load [`references/anti-patterns.md`](references/anti-patterns.md). Cite anti-pattern IDs (e.g. AP-SKL-2) inline when the rule you are writing fixes a named pattern, so the lineage is auditable.
- Need to author a new skill, audit an existing skill against the project-meta contract, or scaffold from `templates/SKILL.template.md`:
  - load [`references/writing-skills.md`](references/writing-skills.md) and [`references/skill-critics.md`](references/skill-critics.md). The audit checklist in writing-skills.md plus the deterministic critic suite in skill-critics.md are the gate before publishing.
- Installing or configuring an opt-in phase-lock workflow (brainstorm → plan → implement → review → finish gates), or diagnosing a phase-lock failure:
  - load [`templates/phase-lock-contract.md`](templates/phase-lock-contract.md). Run `python3 scripts/phase_lock_check.py --harness-dir <repo>/.harness` to verify gates locally; the script is also the Stop-hook payload.
- Installing or tuning the Claude Code hooks pack (SessionStart bootstrap, PostToolUse formatting, Stop verification), or switching `HARNESS_PROFILE` between minimal/standard/strict:
  - load [`templates/hooks/README.md`](templates/hooks/README.md). The settings fragment lives at `templates/hooks/settings.json.fragment`; the three hook scripts at `templates/hooks/scripts/*.sh`.
- Wiring a repo to an external issue tracker (Linear/GitHub/Jira) so feature work is mirrored — check-first / write-progress-back / open-if-missing — or installing/auditing the `issue-tracker` capability and its advisory reminder hook:
  - load [`references/issue-tracking-integration.md`](references/issue-tracking-integration.md), then instantiate [`templates/issue-tracking.md`](templates/issue-tracking.md). Install via `/project-meta init --issue-tracker <tracker>` or `/project-meta settings enable issue-tracker`.
- Generating per-host plugin manifests (`.claude/`, `.cursor/`, `.opencode/`, `.github/copilot-instructions.md`, `gemini-extension.json`) from one canonical AGENTS.md / CLAUDE.md, or detecting drift between canonical and a hand-edited mirror:
  - load [`references/multi-host-manifests.md`](references/multi-host-manifests.md). Run `python3 scripts/render_host_manifests.py --target-root <repo>` to regenerate; `--dry-run` previews.
- Validating that a skill's MUST-rules hold under adversarial pressure (time pressure, sunk-cost, authority flips, plausible exceptions, silent omission), or designing scenarios for a new MUST-rule:
  - load [`references/pressure-testing.md`](references/pressure-testing.md). Use [`templates/pressure-test-scenarios.json`](templates/pressure-test-scenarios.json) as a starting fixture; run `python3 scripts/pressure_test_skill.py SKILL_DIR SCENARIOS_FILE` to walk a verdict pass.

## Output Footer

At the end of every invocation, print a single status line:

```
project-meta/<verb> done — <N> file(s) written, <N> file(s) read, memory updated: <yes|no>, delivery shown: <yes|no>
```

Omit counts that are zero. This line is the handoff signal for the user and for any orchestrating agent checking completion.

## End Check

- Would a future agent likely waste time, break something, or repeat this discovery without the note?
- Is the note durable, repo-relevant or user-relevant, and specific enough to act on?
- Should the lesson remain documentation, or should it become a linter, script, template, checklist, or recurring cleanup routine?
- Has the pre-commit delivery been shown to the user when a commit will be created?
- If the note passes the durability check, update the relevant canonical memory file. If not, leave memory untouched.

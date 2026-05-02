# CLI Command Patterns

## Contents

- [Canonical Command Route Contract](#canonical-command-route-contract) — single source of truth for `/project-meta <command>` routing
- [Supported Commands](#supported-commands) — the small stable command surface
- [Reserved Commands](#reserved-commands) — held until core proves stable
- [Command Contracts](#command-contracts) — mode, references, output per command
- [Shared Command Rules](#shared-command-rules) — read-only vs editing, delivery requirements
- [Implementation Risks](#implementation-risks) — false CLI expectation, command surface bloat

Use this reference when the user invokes `/project-meta <command>` or asks for explicit Project Meta command workflows.

These are slash-command workflow patterns, not a separate shell binary. The command selects the workflow and reference set; the skill references keep the actual rules.

## Canonical Command Route Contract

This file owns the canonical `/project-meta <command>` route table. `SKILL.md` may list trigger examples and reference-loading hints, but it must not define separate command behavior. `README.md` may summarize the supported command surface for users, but it must point back to this reference for the exact workflow contract.

Each supported command entry must define:

- command name and read/write mode
- purpose
- required reference loads, if any
- output contract
- editing and delivery constraints

When a command's route, mode, required references, or output contract changes, update this file first, then adjust `SKILL.md` and `README.md` only as summaries. Validation should treat drift from this reference as a documentation defect.

## Supported Commands

Start with a small stable command surface:

- `/project-meta init`: cold-start or repair a project harness and local preferences.
- `/project-meta status`: inspect the current harness state without editing files.
- `/project-meta validate`: run configured validation checks without unrelated edits.
- `/project-meta deliver`: prepare the pre-commit delivery for user review.
- `/project-meta audit`: review harness health, documentation layering, triggers, mirrors, and memory boundaries.

## Reserved Commands

These commands are useful but should stay reserved until the core workflows prove stable:

- `/project-meta plan`: plan complex work before edits.
- `/project-meta sync`: sync canonical docs and mirrors.
- `/project-meta promote`: write validated lessons to the right memory layer.
- `/project-meta prune`: remove stale or duplicated harness guidance.
- `/project-meta doctor`: run comprehensive health checks and suggest repairs.

If a user invokes a reserved command, explain that it is reserved, then either map it to the closest supported command or ask before proceeding.

## Command Contracts

| Command | Mode | Canonical workflow owner | Required references | Output contract summary |
| --- | --- | --- | --- | --- |
| `/project-meta init` | editing | this file plus `references/project-lifecycle.md` | `project-lifecycle`, `repo-memory-structure`, `repo-memory-crud`, `documentation-delivery`, `execution-policy` | detected conventions, files created or repaired, preference setup, execution-rules artifact when applicable, validation, delivery |
| `/project-meta status` | read-only | this file | none by default | current harness state, gaps, recommended next command |
| `/project-meta validate` | read-only | this file | none by default | commands run, pass/fail, failed checks, repair suggestion |
| `/project-meta deliver` | read-only | this file plus `references/documentation-delivery.md` | `documentation-delivery` | standard pre-commit delivery sections |
| `/project-meta audit` | read-only by default | this file plus target-specific references | load only references relevant to audit target | harness health findings and repair recommendations |

### `/project-meta init`

> Lifecycle detail for the init workflow lives in [`project-lifecycle.md`](project-lifecycle.md). This entry owns only the route contract.

Purpose: initialize a project harness from a cold start.

Load:
- `references/project-lifecycle.md`
- `references/repo-memory-structure.md`
- `references/repo-memory-crud.md`
- `references/documentation-delivery.md`
- `references/execution-policy.md` when the target repo will host bounded-execution agents

Output:
- project type and detected conventions
- files created or repaired
- preference preset selection or resulting local `USER.md`
- offered execution-rules instantiation (`agents/execution-rules.md` plus AGENTS.md insert) when bounded-execution agents will operate in the target repo
- validation result, including `skill/scripts/validate_target_harness.py` when run against the target
- pre-commit delivery when changes are made

If the user asks to reset or change local `USER.md` options, reuse the init preference-rendering path instead of editing stale local preferences directly. Load the installed preference template, ask for the new preset and checklist items, and render the result into ignored local `USER.md`. Prefer `scripts/render_user_preferences.py --target-root <repo> --reset` when available.

### `/project-meta status`

Purpose: report the current harness state without editing files.

Output:
- project type
- canonical project-memory file
- local user-preference status
- shared/user-facing docs
- agent-facing docs
- validation commands
- known gaps
- recommended next command

### `/project-meta validate`

Purpose: run available validation checks.

Output:
- commands run
- pass/fail result
- failed checks and likely owner
- next repair suggestion

Do not edit files during `validate` unless the user explicitly asks for repair.

### `/project-meta deliver`

Purpose: produce the pre-commit delivery for review.

Load:
- `references/documentation-delivery.md`

Output the standard delivery sections:
- user-facing docs
- agent-facing docs
- behavior or trigger changes
- validation
- commit scope

Do not commit as part of `deliver`; wait for user approval.

### `/project-meta audit`

Purpose: review harness health and layering.

Load only the relevant references for the audit target. Default target is the whole harness.

Check:
- shared/user-facing docs are primary and readable by users
- agent-facing docs contain only agent-specific execution details
- `USER.md` is local-only when appropriate
- `AGENTS.md` has not become a manual
- references are not stale, overlapping, or too thin
- multi-agent triggers are not too broad
- mirrors are correctly assigned based on tool context (Claude Code → `CLAUDE.md` canonical, `AGENTS.md` mirror; Codex → reverse)
- validation is documented and passing

## Shared Command Rules

- Commands should not duplicate reference content.
- Command routing and workflow contracts are canonical in this file; other docs summarize or link to this route table.
- Commands must state whether they are read-only or may edit files.
- Read-only commands are `status`, `validate`, and `deliver` unless the user explicitly asks for repair.
- Editing commands must show a delivery before commit when user-facing docs, agent-facing docs, trigger behavior, or validation changes.
- Use local `USER.md` preferences only after they exist. During `init`, ask for preset selection first.

## Implementation Risks

- False CLI expectation: users may assume `/project-meta` is a shell executable. State that these are agent slash-command workflows unless a real CLI is later added.
- Command surface bloat: too many commands can make triggering ambiguous. Keep only core commands supported until usage proves the need for more.
- Over-triggering: ordinary implementation tasks should not invoke Project Meta unless they affect memory, docs, harness behavior, coordination, or durable lessons.
- Unsafe automation: commands that commit, push, sync, or rewrite docs must honor local `USER.md` and pre-commit delivery rules.
- Validation drift: command contracts must be covered by `scripts/validate_project_meta.py` so docs and behavior do not silently diverge.

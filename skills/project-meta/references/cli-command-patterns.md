# CLI Command Patterns

## Contents

- [Canonical Route Contract](#canonical-route-contract) — single source of truth for `/project-meta <command>` routing
- [Recipe Directory](#recipe-directory) — where each command's workflow lives
- [Reserved Commands](#reserved-commands) — held until core proves stable
- [Shared Command Rules](#shared-command-rules) — read-only vs editing, delivery requirements
- [Implementation Risks](#implementation-risks) — false CLI expectation, command surface bloat

Use this reference for the cross-cutting command policy. Per-command workflows live in `recipes/<verb>.md` files; this reference holds only what's shared across all verbs.

These are slash-command workflow patterns, not a separate shell binary. The verb selects the workflow recipe; the recipe loads the references and templates it needs.

## Canonical Route Contract

The `/project-meta <command>` route table maps verbs to recipe files:

| Command | Mode | Recipe |
|---|---|---|
| `/project-meta init` | editing | [`recipes/init.md`](../recipes/init.md) |
| `/project-meta plan` | editing | [`recipes/plan.md`](../recipes/plan.md) |
| `/project-meta status` | read-only | [`recipes/status.md`](../recipes/status.md) |
| `/project-meta validate` | read-only | [`recipes/validate.md`](../recipes/validate.md) |
| `/project-meta deliver` | read-only | [`recipes/deliver.md`](../recipes/deliver.md) |
| `/project-meta audit` | read-only by default | [`recipes/audit.md`](../recipes/audit.md) |
| `/project-meta settings` | editing (read-only view by default) | [`recipes/settings.md`](../recipes/settings.md) |

**`plan` readiness keyword.** `/project-meta plan` writes a falsifiable build plan at one
of two tiers. The default `floor` tier mandates the §6 per-item verification matrix
(test target + data + threshold). The words **`autopilot` / `goal` / `unattended`** in the
request escalate it to `strict` — recording `readiness: strict` in the artifact frontmatter
so `audit`'s Goal-readiness dimension runs a GO/NO-GO gate. The keyword is the human-facing
trigger; the frontmatter field is the audit-facing, legible record. There is **no execution
engine** — execution governance lives in `references/execution-policy.md`; `plan` only
produces the target, `audit` only judges readiness.

`SKILL.md` may list trigger examples and reference-loading hints, but it must not duplicate per-command workflow contracts. `README.md` may summarize the supported command surface for users, but it must point back here for the canonical route.

When a route or shared rule changes, update this file and the matching recipe; SKILL.md and README.md are summaries that follow.

## Recipe Directory

Each recipe file owns one verb's workflow. The recipe documents:

- Trigger (when to load)
- Mode (read-only / editing)
- Required references (what the recipe loads)
- Workflow steps (the procedure)
- Output contract (what the agent produces)
- Anti-patterns (named AP-XXX-N references)

The agent loads exactly one recipe per `/project-meta <command>` invocation. Recipes are the lazy-loaded layer between `SKILL.md` (always loaded) and references/templates (loaded when the recipe needs them).

## Reserved Commands

These commands are useful but should stay reserved until the core set proves stable:

- `/project-meta sync` — sync canonical docs and mirrors (today: invoke `scripts/render_host_manifests.py` directly)
- `/project-meta promote` — write validated lessons to the right memory layer
- `/project-meta prune` — remove stale or duplicated harness guidance
- `/project-meta doctor` — comprehensive health checks + suggested repairs
- `/project-meta roadmap` — proposed Project Board grooming mode; reserved until `docs/backlog/project-board-system.md` DASH-05/06/08/17 are implemented and validated

If a user invokes a reserved command, explain that it is reserved, then either map it to the closest supported command or ask before proceeding. Do not silently invoke a related command.

Promotion path: when a reserved command sees consistent demand and a stable workflow shape, promote it by adding `recipes/<verb>.md` and an entry in the route table above. `settings` was promoted this way and now owns the **profile + capability toggles** (`recipes/settings.md`). Keep the reserved verbs disjoint from it: if `doctor` is promoted it owns *health checks + repairs* (read-then-suggest), not toggles; `sync` owns *mirror regeneration*, which `settings` may invoke when toggling the multi-host capability but does not duplicate.

## Shared Command Rules

- **No duplication**: commands must not duplicate reference content. The recipe loads the reference; the reference holds the procedure.
- **Single source of truth**: command routing and workflow contracts are canonical here + in the recipe; other docs summarize or link.
- **Mode declaration**: every recipe MUST state whether it is read-only or may edit files. Mixing modes silently is a contract violation.
- **Read-only commands**: `status`, `validate`, `audit`, `deliver` — none edit by default. The user must explicitly switch to an editing recipe (`init`) for repair.
- **Delivery before commit**: editing commands MUST show a delivery (via the `deliver` recipe contract) before any commit when user-facing docs, agent-facing docs, trigger behavior, or validation changes.
- **Local USER.md**: use only after it exists. During `init`, ask for preset selection first (AP-LIFE-1).
- **Subagent dispatch**: when an editing recipe touches ≥2 of {AGENTS.md, agents/*.md, mirrors, templates}, MUST dispatch per-file edits to fresh subagents with a reviewer between (AP-COORD-1, AP-COORD-2). Detail in [`multi-agent-protocols.md`](multi-agent-protocols.md).

## Implementation Risks

- **False CLI expectation**: users may assume `/project-meta` is a shell executable. State that these are agent slash-command workflows unless a real CLI is later added.
- **Command surface bloat**: too many commands make triggering ambiguous. Keep the supported set small until usage proves the need for more.
- **Over-triggering**: ordinary implementation tasks should not invoke project-meta unless they affect memory, docs, harness behavior, coordination, or durable lessons (the trigger-decision rule in `SKILL.md`).
- **Unsafe automation**: commands that commit, push, sync, or rewrite docs MUST honor local `USER.md` and pre-commit delivery rules.
- **Validation drift**: command contracts must be covered by `scripts/validate_target_harness.py` so docs and behavior do not silently diverge (AP-VAL-2). *Build-plan coverage status:* provenance frontmatter on an instantiated build plan is already covered by `check_artifact_provenance`. The §6 verification-matrix completeness check (every row has test-target / data / threshold) is **not yet mechanized** — today it is enforced by hand in `audit`'s Goal-readiness dimension. Promoting it to a dedicated linter is the open AP-VAL-2 follow-up for this verb; until then, do not claim the matrix is mechanically gated.
- **Recipe drift**: when a recipe's workflow changes, update the matching SKILL.md routing entry and the cli-command-patterns route table together. A recipe whose route is stale silently fires on the wrong verb.

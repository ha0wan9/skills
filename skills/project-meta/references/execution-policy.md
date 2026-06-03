# Execution Policy

## Contents

- [Purpose](#purpose) — enforcement protocol vs behavior philosophy
- [Three Tiers](#three-tiers) — MUST STOP, SHOULD ASK, MAY PROCEED WITH NOTE
- [MUST STOP Categories](#must-stop-categories) — actions that always halt
- [SHOULD ASK Categories](#should-ask-categories) — actions that need explicit approval
- [MAY PROCEED WITH NOTE](#may-proceed-with-note) — record in delivery and continue
- [Soft Budgets](#soft-budgets) — configurable signals, not baked thresholds
- [Read-Pattern Derivation](#read-pattern-derivation) — how much context to acquire before acting, derived not guessed
- [Codex-Class Worker Constraints](#codex-class-worker-constraints) — bounded execution defaults
- [Relationship To Runtime Enforcement](#relationship-to-runtime-enforcement) — what this protocol is and isn't

Use this reference when generating, reviewing, or auditing the execution constraints a target repository imposes on bounded-execution agents.

## Purpose

This protocol defines *when an agent must halt for approval before continuing*. It complements [`agent-behavior-protocol.md`](agent-behavior-protocol.md), which defines how an agent should think and edit. Behavioral guidance answers "how to be careful"; this file answers "when to stop."

Project Meta's job is to generate and validate this policy as a target-repo artifact. It is not a runtime sandbox. Real enforcement comes from the agent's CLI configuration — Claude Code permissions and hooks, Codex CLI approval modes, and per-repo pre-commit hooks or CI gates. See [Relationship To Runtime Enforcement](#relationship-to-runtime-enforcement).

## Three Tiers

Every potential action falls into one of three tiers:

- **MUST STOP**: Halt immediately, ask the user, do not proceed without explicit approval. Irreversible, expensive, or scope-redefining actions.
- **SHOULD ASK**: Produce a plan, name the action, wait for confirmation. Reversible-but-significant actions.
- **MAY PROCEED WITH NOTE**: Take the action, but record it in the pre-commit delivery so the user sees what happened. Routine actions that still benefit from visibility.

Tier assignment depends on the target project's adapter. The defaults below are sensible for application, service, library, and tooling repos; documentation or content repos may relax SHOULD ASK rules around new files but should keep MUST STOP intact.

## MUST STOP Categories

The agent must halt and request explicit approval before:

- **Destructive operations**: `rm -rf`, force-push to shared branches, branch deletion, history rewrite, database drops, file overwrites that erase prior history.
- **Network commands**: outbound HTTP, package installs, external API calls, anything that depends on or affects systems outside the repo.
- **Auth and security changes**: secrets, credentials, signing keys, IAM roles, `.env` files, certificates, permission grants.
- **Structural renames**: moving files between top-level directories, renaming public modules, changing import paths consumers depend on.
- **Public API or interface changes**: CLI flags, function signatures, config keys, schema fields, exported types — anything callers or downstream tools depend on.
- **CI, CD, build, or packaging changes**: workflow files, build configs, package manifests, Dockerfiles, deploy scripts.
- **Dependency changes**: adding, removing, or upgrading runtime or build dependencies.
- **Generated bulk rewrites**: codemod runs, format-everything passes, auto-fix-all on the entire repo.
- **Scope expansion**: any change outside the file set the user requested or the agent itself proposed and the user approved.
- **Unclear target files**: when the agent cannot name the specific files it intends to edit. Guessing is not allowed; ask which files are in scope before any edit.
- **File modification under a read-only command**: the requested workflow is `status`, `validate`, `deliver`, `audit`, `review`, or any other read-only mode, and the proposed change would write to disk. Read-only is binding unless the user explicitly upgrades it to repair. **This binding holds inside any orchestration runner** (subagent dispatch, Claude Code Workflow, Codex Agents-SDK): a read-only verb's runner MUST contain no edit-capable stages by construction. A runner that *can* emit a write under a read-only verb is a MUST-STOP violation by construction, not merely at runtime.

## SHOULD ASK Categories

The agent should produce a plan and wait for confirmation before:

- **Commits, pushes, PRs, merges**: even reversible ones — visibility before the fact is cheaper than reconstruction after.
- **Multi-subsystem edits**: changes that span more than one logical module, package, or domain.
- **Refactors not requested by the user**: opportunistic cleanup, parallel structure migrations, name standardization.
- **New files at the top level or in protected directories**: anything that adds to the repo's visible structure.
- **Test infrastructure changes**: framework swaps, mock or stub library introductions, CI test runner changes.
- **Documentation that creates new top-level files**: new README sections at root, new docs in primary user-facing folders.
- **Edits to canonical project memory** (`AGENTS.md`, project-memory loader, topical memory files): only after a lesson is validated, never speculatively.

## MAY PROCEED WITH NOTE

The agent may proceed but must record the action in the pre-commit delivery so the user sees it:

- single-file fixes confined to the request scope
- adding tests for code the user just asked to change
- updating inline comments and docstrings adjacent to the requested change
- bug-fix commits with clear before-and-after evidence
- typo fixes in files already being edited

If the action would cross into a SHOULD ASK or MUST STOP category, treat it as that tier instead.

## Soft Budgets

Soft budgets are configurable per-project signals, not baked-in thresholds. The target project's `agents/execution-rules.md` artifact defines them. A reasonable default shape:

```yaml
change_budget:
  default_files_soft_limit: 3      # exceed -> escalate to SHOULD ASK
  default_lines_soft_limit: 200    # exceed -> escalate to SHOULD ASK
  semantic_scope_escalation:
    one_subsystem: may proceed with note
    cross_subsystem: should ask
    cross_repo: must stop
```

File count alone is not a risk signal. A 20-file mechanical rename can be safer than a 2-file auth change. Use semantic scope (which subsystems, which interfaces) as the primary signal; use file count as a heuristic flag, not a hard threshold.

## Read-Pattern Derivation

Soft budgets answer *when to stop*. The **read-pattern** answers a different question — *how much context to acquire before acting* — and it is orthogonal to both the verb's mode (editing/read-only) and the dispatch tier (single-context / subagent dispatch / scripted engine). It is **derived, not a separate classifier the agent computes from scratch**: reuse `semantic_scope` as the spine so the harness does not carry a third independent risk axis (a redundant classifier is its own over-machinery — AP-COORD-5).

```yaml
read_pattern:
  default: minimal                # just-in-time, narrowest file set per subtask
  escalate_to: context-mapping
  escalate_when:
    - semantic_scope >= cross_subsystem
    - design intent signalled        # "redesign", "rethink", "architecture",
                                      # "restructure", "should we", authoring a new skill
    - verb == audit AND investigative # not a mechanical re-run
```

- **minimal** (default): each subtask reads the smallest file set it needs, just in time — the Context Package "Read first" discipline. No upfront shared digest.
- **context-mapping**: a read-only Explorer fan-out builds a compressed global map *before* decomposition, consumed by the Lead/Planner. Mechanics and the four constraints that keep it from becoming a drift source live in [`multi-agent-protocols.md`](multi-agent-protocols.md) "Context Mapping Phase".

Rules:

- **Default minimal; escalate on the signals above, never the reverse.** Escalation is cheap — the Lead pulls more context just-in-time when minimal proves insufficient; unwinding a propagated stale digest is not. This mirrors Soft Budgets ("File count alone is not a risk signal") and the dispatch tiers ("the engine is the higher bar").
- **State the derived read-pattern in the delivery**, exactly like the Mandatory Subagent Dispatch bypass acknowledgement. A silently mis-derived read-pattern is the failure mode (AP-COORD-5); a stated one is auditable and the user can correct it.
- **When signals conflict, ask before entering context-mapping** rather than guess — the mapping phase has real cost, and a cheap question beats an over-mapped run. Aligns with the init questionnaire as a synchronous human gate.
- **Derived, runtime-agnostic.** This derivation is prose every runtime executes; a Workflow / Agents-SDK backing may accelerate the mapping fan-out but never owns the decision (mechanizing it on one runtime only is an AP-VAL-1 gap).

## Codex-Class Worker Constraints

Codex-class agents — high execution-throughput, optimistic-action defaults — need explicit constraints because behavioral prose alone underdetermines their actions. They are Workers by default, not Leads.

Before any non-trivial edit, a Codex-class worker must produce:

```text
Goal:
Files to inspect:
Files likely to change:
Out of scope:
Commands likely to run:
Approval needed: yes / no
```

A Codex-class worker must not:

- expand scope beyond the goal or approved plan
- opportunistically refactor adjacent code
- introduce new dependencies, even when "the obvious next step" suggests one
- claim validation success without command output or a passing test
- claim correctness when validation cannot be run; instead, name the missing check in the delivery and mark the work as unverified
- promote uncertainty into durable canonical memory
- update mirrors before canonical memory has been integrated
- act as Lead when planning is part of the work — return the planning question to a Lead agent instead
- modify files when the requested workflow is read-only (`status`, `validate`, `deliver`, `audit`, `review`); read-only is binding

These constraints belong in the target repo's [`agents/execution-rules.md`](../templates/execution-rules.md) (because the worker reads it on every invocation), not only in this skill reference. The skill template seeds the artifact; the target repo owns the concrete instance.

## Relationship To Runtime Enforcement

Markdown rules are advisory. Real enforcement comes from runtime configuration:

- **Claude Code**: `settings.json` permissions, `hooks` for pre-tool-use approval, MCP server allowlists, plan-mode gates, and the **Workflow** tool for deterministic scripted orchestration (pipeline/parallel/barrier/resume/budget).
- **Codex CLI**: `config.toml` approval modes, sandbox settings, network and file-scope flags, native **subagents** (`.codex/agents/*.toml`, native roles `worker`/`explorer`/`default` — exact TOML schema is Codex-version-dependent), Codex hooks, and the **Agents SDK + `codex mcp`** for deterministic scripted orchestration.
- **Repo-side**: pre-commit hooks, branch protection, CI gates that block on test or lint failures.

Project Meta's role: generate the *policy* (this reference, the template, the instantiated `agents/execution-rules.md`), validate that target repos have it, and document the recommended runtime settings. The CLI and repo gates do the actual blocking. A target repo with an instantiated `agents/execution-rules.md` but no matching CLI configuration has only half the enforcement; **both layers must agree — on every declared compat runtime.** A rule mechanized on Claude Code (e.g. a Workflow) but absent on Codex is only half-enforced across the runtime matrix; provide the Codex-side backing or keep the prose path as the cross-runtime floor (see `multi-agent-protocols.md` "Orchestration Backings").

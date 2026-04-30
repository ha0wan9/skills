---
template_name: execution-rules
description: "Seed template for target-repo execution constraints that bounded-execution agents (Codex-class) read on every invocation."
source_reference: references/execution-policy.md
intended_project_path: agents/execution-rules.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-when-stop-or-ask-categories-change
---

# Execution Rules Template

Use this seed when a target project needs concrete halt-and-ask constraints separate from behavioral guidance. The target's `AGENTS.md` should reference the instantiated artifact in its read order so bounded-execution agents see it before any non-trivial edit.

## Project Artifact Frontmatter

```yaml
---
artifact_name: execution-rules
instantiated_from: project-meta/templates/execution-rules.md
source_reference: project-meta/references/execution-policy.md
project_scope: this repo only
owner: agent-facing
review_policy: user review when stop or ask categories change
last_reviewed: YYYY-MM-DD
---
```

## Copyable Block

```markdown
# Execution Rules

Bounded-execution agents working in this repository must read this file before any non-trivial edit. This file is advisory — runtime enforcement lives in the agent's CLI configuration. Both layers must agree.

## Decision Tiers

- **MUST STOP**: halt and ask. Do not proceed without explicit approval.
- **SHOULD ASK**: produce a plan, wait for confirmation.
- **MAY PROCEED WITH NOTE**: act, then record in the pre-commit delivery.

## MUST STOP

Halt and ask before:

- destructive operations (`rm -rf`, force-push, branch deletion, history rewrite, db drops)
- network commands and dependency changes (installs, upgrades, removals)
- auth, security, or credential edits (secrets, keys, IAM, `.env`, certificates)
- structural renames or public-API changes (CLI flags, function signatures, config keys, schema fields)
- CI, CD, build, packaging, or Docker changes
- generated bulk rewrites (codemods, format-everything passes, auto-fix-all)
- any change outside the requested or approved scope
- editing any file when target files are unclear; ask which files are in scope before guessing
- modifying files under a read-only workflow (`status`, `validate`, `deliver`, `audit`, `review`); read-only is binding unless the user explicitly upgrades it to repair

## SHOULD ASK

Produce a plan and wait for confirmation before:

- creating commits, pushes, PRs, or merges
- editing more than one subsystem in a single change
- refactoring outside the user's request
- adding new top-level files or directories
- changing test infrastructure, mocking libraries, or test runners
- editing canonical project memory (`AGENTS.md`, project-memory loader, topical memory)

## MAY PROCEED WITH NOTE

Act, then surface in the pre-commit delivery:

- single-file edits within the requested scope
- adding tests adjacent to the requested change
- updating comments or docstrings adjacent to the requested change
- typo fixes in files already being edited

## Soft Budgets

These are heuristics, not hard limits. Adjust per project:

```yaml
change_budget:
  default_files_soft_limit: 3
  default_lines_soft_limit: 200
  semantic_scope_escalation:
    one_subsystem: may proceed with note
    cross_subsystem: should ask
    cross_repo: must stop
```

File count alone is not a risk signal. Treat semantic scope as primary; file count is a flag, not a gate.

## Worker Plan Format

Bounded-execution workers (Codex-class default) must emit this plan before any non-trivial edit:

```text
Goal:
Files to inspect:
Files likely to change:
Out of scope:
Commands likely to run:
Approval needed: yes / no
```

## Worker Prohibitions

A bounded-execution worker must not:

- expand scope beyond the goal or approved plan
- opportunistically refactor adjacent code
- introduce new dependencies, even when "the obvious next step" suggests one
- claim validation success without command output or a passing test
- claim correctness when validation cannot be run; name the missing check in the delivery and mark the work as unverified instead
- promote uncertainty into durable canonical memory
- update mirrors before canonical memory has been integrated
- act as Lead when planning is part of the work
- modify files under a read-only workflow

## Runtime Enforcement

This file is advisory. Real enforcement comes from:

- Claude Code: `settings.json` permissions, hooks, MCP allowlists, plan-mode gates
- Codex CLI: approval mode, sandbox settings, network and file-scope flags
- Repo: pre-commit hooks, branch protection, CI gates

Keep this file aligned with the active CLI configuration. One without the other is incomplete enforcement.
```

## AGENTS.md Insert

Add the following to the target repo's `AGENTS.md` so bounded-execution agents see execution rules during cold start:

```markdown
## Execution Rules

Bounded-execution agents must read [`agents/execution-rules.md`](agents/execution-rules.md) before any non-trivial edit. Hard-stop categories: destructive operations, network commands, dependency changes, CI/CD changes, structural renames, public-API changes, and out-of-scope edits. Full tier definitions, soft budgets, and worker constraints live in the linked file.
```

## Instantiation Rules

- Render the artifact frontmatter as the first block of `agents/execution-rules.md`, then the Copyable Block as the body.
- Add the AGENTS.md Insert section to the target repo's `AGENTS.md` and ensure it appears in the read order.
- Customize `MUST STOP` / `SHOULD ASK` categories to match the target project: a documentation repo can relax SHOULD ASK rules around new files; an auth-sensitive repo should escalate scope rules.
- Customize `change_budget` numbers to match the target project's typical change shape.
- Do not remove `instantiated_from`, `source_reference`, `owner`, or `review_policy` fields.
- Do not store this template under `agents/templates/` in the target repo. Instantiate the concrete artifact instead.
- In Secure or Strict mode, do not overwrite an existing `agents/execution-rules.md` without showing a delivery.
- Pair the artifact with the matching CLI configuration (Claude Code permissions or Codex approval mode). The artifact alone is not enforcement.

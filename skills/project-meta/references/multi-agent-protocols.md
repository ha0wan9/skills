# Multi-Agent Protocols

## Contents

- [Default Rule](#default-rule) — single agent unless complexity justifies coordination
- [Trigger Modes](#trigger-modes) — explicit vs complexity triggers
- [Roles](#roles) — Lead, Planner, Explorer, Worker, Reviewer
- [Context Package](#context-package) — fields every delegation must include
- [Delegation Template](#delegation-template) — copyable shape
- [Ownership Rules](#ownership-rules) — write-set boundaries
- [Review Mechanism](#review-mechanism) — consistency, drift, routing, enforcement passes
- [Integration Checklist](#integration-checklist) — final reconciliation before commit
- [Failure Signals](#failure-signals) — when the protocol itself needs improvement

Use this reference when complex project-harness work benefits from explicit planning, delegated execution, and independent review.

## Default Rule

Use a single agent unless the task has enough complexity, uncertainty, or independent workstreams to justify coordination overhead.

## Trigger Modes

Use this protocol when either trigger applies:

- Explicit trigger: the user asks for multi-agent work, planning/execution separation, delegated workers, independent review, parallel agents, or a lead agent coordinating sub-agents.
- Complexity trigger: the lead agent judges that the task is complex enough to benefit from planning, bounded execution, and review.

For the complexity trigger, use the protocol when at least two signals apply, or when one strong signal clearly creates meaningful coordination or review risk:

- the task spans multiple independent files, tools, packages, domains, or repositories
- the work needs both exploration and implementation
- the work has independent subtasks that can proceed in parallel
- the work has meaningful risk from conflicting edits, stale guidance, or cross-file drift
- the task needs an explicit review pass before integration
- the requested outcome is ambiguous enough that planning artifacts would reduce rework

When this protocol is triggered, the lead agent should state the trigger reason before delegating work.

For complex work, separate planning from execution:

1. The lead agent plans, decomposes, and sets context.
2. Worker agents execute bounded subtasks with explicit ownership.
3. Reviewer agents check the resulting artifacts against stated criteria.
4. The lead agent integrates results and owns the final answer.

## Roles

- Lead: owns task framing, decomposition, context packages, ownership boundaries, review criteria, integration, and final memory writeback.
- Planner: explores the problem space and produces the task breakdown. In small teams, the lead agent may also be the planner.
- Explorer: answers narrow read-only questions and does not edit files.
- Worker: edits an explicitly assigned file set or produces a bounded artifact.
- Reviewer: checks consistency, drift, duplicate guidance, missing validation, and whether the output matches the protocol.

## Context Package

Every delegated task must include:

- Goal: the exact question or artifact the agent must produce.
- Read first: the smallest file list needed for the task.
- Ownership: read-only status or the exact files the agent may edit.
- Constraints: relevant rules from `AGENTS.md`, `SKILL.md`, and loaded references.
- Output format: findings, patch summary, review notes, or structured decision.
- Review criteria: what must be true for the subtask to pass.
- Memory policy: whether the agent may suggest memory updates, edit canonical memory, or only report durable lessons.

## Delegation Template

```text
Role: <Explorer | Worker | Reviewer>
Goal: <exact question or artifact>
Read first:
- <path>
- <path>
Ownership: <read-only | may edit exact files>
Constraints:
- <relevant AGENTS.md, SKILL.md, or reference rule>
Output format: <findings | patch summary | review notes | decision>
Review criteria:
- <pass/fail condition>
Memory policy: <may suggest updates | may edit canonical memory | report only>
```

## Ownership Rules

- Do not assign overlapping write sets unless the lead agent explicitly owns reconciliation.
- Keep `SKILL.md` as the entrypoint; move detailed protocol guidance into `references/`.
- Treat canonical memory as the source of truth and mirrors as secondary.
- Do not let workers update mirrors before canonical memory changes are integrated.
- Do not write speculative, transient, or session-only notes into repo memory.

## Review Mechanism

For complex changes, run at least one of these review passes before final integration:

- Consistency review: checks that `README.md`, `SKILL.md`, `agents/openai.yaml`, and relevant `references/*.md` agree.
- Drift review: checks stale, duplicated, or contradictory guidance.
- Routing review: checks that the entrypoint points to the right reference without becoming a manual.
- Enforcement review: identifies rules that should become a script, checklist, template, or recurring cleanup routine.

## Integration Checklist

Before finalizing multi-agent work:

1. Reconcile duplicate or conflicting recommendations.
2. Verify links, paths, and file ownership assumptions.
3. Check that workers did not exceed their write scope.
4. Keep durable lessons in canonical memory, not in mirrors first.
5. Sync mirrors only when canonical structure or high-priority guidance changed.
6. Run available diff, formatting, or validation checks.
7. Record any recurring coordination failure as a protocol improvement.

## Failure Signals

Improve the protocol when agents:

- ask each other vague questions instead of producing artifacts
- claim work was done without verifiable file changes or evidence
- edit outside their ownership boundary
- duplicate guidance across canonical files and mirrors
- skip review criteria or leave the lead agent to infer pass/fail state

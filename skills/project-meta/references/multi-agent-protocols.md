# Multi-Agent Protocols

## Contents

- [Default Rule](#default-rule) — single agent unless complexity justifies coordination
- [Trigger Modes](#trigger-modes) — explicit vs complexity triggers
- [Mandatory Subagent Dispatch](#mandatory-subagent-dispatch) — when project-meta editing recipes MUST dispatch
- [Roles](#roles) — Lead, Planner, Explorer, Worker, Reviewer
- [Context Package](#context-package) — fields every delegation must include
- [Delegation Template](#delegation-template) — copyable shape
- [Ownership Rules](#ownership-rules) — write-set boundaries
- [Review Mechanism](#review-mechanism) — consistency, drift, routing, enforcement passes
- [Reviewer-Between-Subtasks Protocol](#reviewer-between-subtasks-protocol) — the enforcement loop
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

## Mandatory Subagent Dispatch

The complexity trigger is judgement-based; the rule below is mechanical.

**MUST dispatch via subagents** (per-file Worker + Reviewer between subtasks) when a `/project-meta` editing recipe (`init`, `deliver`, or any future editing verb) touches **two or more** of:

- `AGENTS.md` (or the canonical equivalent for the active host)
- any `agents/*.md` topical file
- any mirror file (`CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/agents.md`, `.opencode/instructions.md`, `gemini-extension.json`, `.gemini/instructions.md`)
- any template under `templates/`
- any script under `scripts/`
- any hook script under `<target>/.claude/hooks/`

Single-file changes stay in the conductor's context. Trivial changes (typo fixes, docs-only edits ≤10 lines) can also stay single-context with explicit acknowledgement in the delivery summary.

**Why mechanical**: AP-COORD-1 (conductor edits + orchestrates simultaneously) and AP-COORD-2 (no review between subtasks) are the dominant failure modes for project-meta editing work. Judgement-based triggers under-fire when the conductor is already engaged. The file-count rule fires deterministically.

**Bypass requires explicit acknowledgement.** When the conductor judges the rule does not apply (e.g. all touched files form one logically atomic change), it MUST state the bypass in the delivery summary, name the AP-COORD-* rule it is bypassing, and justify why. A delivery that silently skips dispatch is itself an AP-COORD-1 violation.

The recipe owns *when* to dispatch; this reference owns *how* (Roles, Context Package, Reviewer-Between-Subtasks Protocol below).

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

## Reviewer-Between-Subtasks Protocol

Once mandatory dispatch is triggered (or when the lead agent invokes it for judgement reasons), the per-subtask loop is:

1. **Brief**: lead packages a context package per the Delegation Template above. Brief contains only what the worker needs — typically ≤1 page including the diff target, the rule motivating the change, the success criterion, and ≤3 surrounding-context references.

2. **Worker dispatch**: fresh subagent. Worker edits the assigned file, produces a patch summary, and reports back. Worker does NOT see the lead conductor's broader context; this is the AP-COORD-1 fix.

3. **Reviewer dispatch**: fresh subagent, separate from worker. Reviewer receives:
   - the original brief
   - the worker's diff
   - the success criterion
   Reviewer reports verdict: **PASS** / **BLOCKER** / **SUGGEST**.
   - PASS: lead proceeds to the next subtask.
   - BLOCKER: lead halts the chain, surfaces the blocker to the user. No further dispatch until the user decides (re-brief worker / re-scope / abort).
   - SUGGEST: lead may incorporate, queue for follow-up, or accept-as-is depending on the suggestion's weight; either way, the suggestion is logged in the delivery.

4. **Logging**: every dispatch records (worker subagent id, reviewer subagent id, brief hash, verdict, comment) so the chain is auditable. The delivery summary includes the chain.

5. **Reviewer rotation**: do not reuse the same reviewer subagent for consecutive subtasks. A reviewer that has been part of one subtask's context will pattern-match against it; rotation keeps reviewers naïve to prior work, which is the point.

6. **Lead never edits**. Once dispatch triggers, the lead's role is brief / review verdicts / integration. Lead writing files inside a dispatched chain is AP-COORD-1.

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

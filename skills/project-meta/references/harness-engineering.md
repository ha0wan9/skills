# Harness Engineering

> The user-facing vs agent-facing documentation surface contract is canonical in [`documentation-delivery.md`](documentation-delivery.md). This file owns the audit checklist, redesign triggers, and harness-engineering principles.

Use this reference when auditing or redesigning an agent-first project harness.

## Goal

Make the project legible enough that an agent can discover the right context, act within clear boundaries, verify its work, coordinate when needed, and feed durable lessons back into the repo.

## Principles

- Treat repository-local, versioned files as the agent's system of record.
- Keep bootstrap files short. `AGENTS.md` or the repo's equivalent should be a map, not a manual.
- Use progressive disclosure: route agents from a small stable entrypoint to the few topical files needed for the task.
- Add behavior guardrails for how agents should work, not only where information lives.
- Add lifecycle rules so the harness evolves as the project changes.
- Prefer precise, mechanical rules over broad taste guidance.
- When documentation repeatedly fails to shape behavior, promote the rule into a script, linter, test, template, or checklist.
- Keep complex plans, decisions, and known debt as first-class versioned artifacts when the work is too large for a lightweight in-chat plan.
- Run periodic cleanup of stale, duplicated, or contradictory memory instead of letting guidance accumulate indefinitely.

## Audit Checklist

Score each item as absent, partial, or enforced:

- Entry map: the bootstrap memory file is short, current, and routes to deeper sources.
- Sources of truth: canonical memory files are clear, and mirrors are explicitly secondary.
- Selective loading: topical files are narrow enough that agents can load only relevant context.
- Verifiability: important rules have exact paths, commands, ownership, dates, or checks.
- Guardrails: repeated mistakes are captured as constraints or tooling, not only prose.
- Behavior: agent execution rules are simple, surgical, goal-driven, and verifiable.
- Coordination: complex work has a planning, ownership, review, and integration protocol.
- Feedback loop: durable lessons from reviews, failures, and user corrections are written back to the right canonical file.
- Garbage collection: stale rules are replaced or removed, not layered over with contradictions.

## Redesign Triggers

Restructure repo memory when:

- the bootstrap file is becoming a general-purpose encyclopedia
- agents must read most files to find a small task-specific rule
- rules are duplicated across canonical files and mirrors
- memory contains session logs, speculation, or obsolete workflow notes
- repeated mistakes show that a rule needs stronger routing, examples, or mechanical enforcement
- project work repeatedly requires ad hoc planning, context packaging, or review

## Determinism-Gap Enforcement Tags

`scripts/determinism_gap_scan.py` (AP-VAL-1/2) flags prose rules that name a
backing script but that no hook actually invokes. Not every such rule is a
real gap — some are deliberately manual. Mark the honest state inline:

```
(enforcement: manual|advisory|hook|stop-gate|ci)
```

Place the tag on the flagged rule line itself, or on the physical line
immediately following it (bounded to +1 — no farther).

- `manual` — a command a human or agent deliberately runs (e.g. a
  workflow step, a one-off migration); never intended to be hook-fired.
- `advisory` — a session-start or best-effort leg that informs but does not
  block (e.g. a lint that surfaces findings without gating).
- `hook` / `stop-gate` / `ci` — intended to be enforced mechanically. These
  behave like an untagged line: the scan still checks actual hook wiring
  and reports GAP until one exists. Tagging documents intent; it does not
  by itself close the gap.
- Untagged — unchanged default: GAP when the script exists and no hook
  invokes it.

`manual`/`advisory` downgrade a GAP to INFO. `hook`/`stop-gate`/`ci` (and
untagged) stay GAP until a hook is wired.

**CONFLICT rule:** a rule line containing a MUST-ASSERTION cannot honestly be
marked `manual` or `advisory` — a hard MUST names a real gate, not a
best-effort leg. Tagging one is reported as CONFLICT and fails `--strict`. A
MUST-ASSERTION is a bold `**MUST**` or a line-initial/imperative `MUST`
token; mentions such as "MUST-rules" or "a new MUST" are not assertions and
never trigger the check.

## Output Pattern

When improving a project harness:

1. State the current structure and its failure mode.
2. Preserve coherent repo-specific conventions.
3. Move detailed guidance out of the bootstrap file and into topical files.
4. Add behavior, lifecycle, and coordination guidance only where they reduce repeated friction.
5. Add or update mirror guidance only after canonical structure changes.
6. Record only durable, repo-relevant or user-relevant knowledge.
7. Call out any rule that should eventually become a validation script or recurring cleanup task.

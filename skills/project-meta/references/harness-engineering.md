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

## Output Pattern

When improving a project harness:

1. State the current structure and its failure mode.
2. Preserve coherent repo-specific conventions.
3. Move detailed guidance out of the bootstrap file and into topical files.
4. Add behavior, lifecycle, and coordination guidance only where they reduce repeated friction.
5. Add or update mirror guidance only after canonical structure changes.
6. Record only durable, repo-relevant or user-relevant knowledge.
7. Call out any rule that should eventually become a validation script or recurring cleanup task.

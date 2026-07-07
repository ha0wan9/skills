# Dispatch Card

Quick reference for **when** a `/project-meta` editing recipe must dispatch subagents, and **how** to bypass. This is the small always-loadable card; the full mechanics (roles, context package, reviewer loop, model tier, fleet workflow) live in [`multi-agent-protocols.md`](multi-agent-protocols.md) and load only when a dispatch step actually fires.

## When to dispatch

This card covers the **`/project-meta` editing-recipe** trigger. The general *explicit* trigger — a user directly asking for multi-agent work, planning/execution separation, or independent review — also applies anywhere; see [`multi-agent-protocols.md#trigger-modes`](multi-agent-protocols.md#trigger-modes).

**Mechanical rule (editing recipes).** MUST dispatch (per-file Worker + Reviewer between subtasks) when an editing recipe (`init`, or any future editing verb — `deliver` is read-only and never edits) touches **two or more** of:

- `AGENTS.md` (or the canonical equivalent for the active host)
- any `agents/*.md` topical file
- any mirror file (`CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/agents.md`, `.opencode/instructions.md`, `gemini-extension.json`, `.gemini/instructions.md`)
- any template under `templates/`
- any script under `scripts/`
- any hook script under `<target>/.claude/hooks/`

**3-way tier selector (not binary):**

1. **Single-file change** → stay in the conductor's context.
2. **Trivial change** (typo fixes, docs-only ≤10 lines) → stay single-context, with explicit acknowledgement in the delivery.
3. **Two-or-more of the file set above** → dispatch.

The ≥2-file rule selects *cheap subagent dispatch*. Escalating to a *scripted orchestration engine* (Claude Code Workflow, Codex Agents-SDK) is a **separate, higher bar** — explicit user opt-in or a heavy-scope signal, never raw file count (see [`multi-agent-protocols.md#mandatory-subagent-dispatch`](multi-agent-protocols.md#mandatory-subagent-dispatch) and `anti-patterns.md` AP-COORD-4).

**Complexity trigger (judgement).** Also dispatch when ≥2 of these apply (or one strong signal with real coordination/review risk): the work spans multiple independent files/tools/domains; needs both exploration and implementation; has parallel independent subtasks; carries conflicting-edit or cross-file-drift risk; needs an explicit review pass; or is ambiguous enough that planning artifacts reduce rework. State the trigger reason before delegating.

## Bypass requires explicit acknowledgement

When the conductor judges the rule does not apply (e.g. all touched files form one logically atomic change), it MUST state the bypass in the delivery summary, name the `AP-COORD-*` rule it is bypassing, and justify why. A delivery that silently skips dispatch is itself an AP-COORD-1 violation. (The mechanical backing gates this via a `.harness/dispatch-ack` presence marker — a one-shot sentinel, not a log; see [`multi-agent-protocols.md#mechanical-enforcement`](multi-agent-protocols.md#mechanical-enforcement).)

## Load the full protocol when

You actually enter a dispatch step and need the mechanics: [Roles](multi-agent-protocols.md#roles), [Context Package](multi-agent-protocols.md#context-package), [Delegation Template](multi-agent-protocols.md#delegation-template), [Reviewer-Between-Subtasks Protocol](multi-agent-protocols.md#reviewer-between-subtasks-protocol), [Model Tier](multi-agent-protocols.md#model-tier) (tier ids `cli|haiku|sonnet|opus|fable`; that section is the single tier-id → model mapping point), or the [Fleet Delivery Workflow](multi-agent-protocols.md#fleet-delivery-workflow).

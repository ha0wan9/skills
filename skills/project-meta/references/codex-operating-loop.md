# Codex Operating Loop

Use this reference when a target repo is primarily operated from Codex and the user wants work to persist across long threads, remote check-ins, side-panel/browser review, Goals, Heartbeats, or recurring artifact updates.

External inspiration: Jason Liu, ["Codex-maxxing"](https://jxnl.co/writing/2026/05/10/codex-maxxing/) (2026-05-10). Treat the article as a product-pattern source, not a normative spec. Project Meta translates the pattern into reviewable repo harness rules.

## Purpose

Codex is strongest when the unit of work is not a single prompt but an operating loop:

1. durable thread context
2. shared memory on disk
3. steering while work is running
4. inspectable artifacts in the side panel or browser
5. remote check-ins and scheduled follow-up
6. a verification oracle that tells the agent when the work is actually done

Project Meta's job is to make that loop repo-legible. Conversation history may help continuity, but files remain the source of truth because they can be reviewed, diffed, pruned, and reused by future threads.

This reference is part of the **elastic harness ecosystem**. It is an optional, instantiable policy layer that composes with `HARNESS_PROFILE`, bounded elastic profile derivation, hooks, session receipts, lesson registry, board/issue tracking, and review-tier selection. It does not create a new enforcement dial.

## Required Shape

A Codex-primary repo should make these surfaces explicit:

| Surface | Repo artifact | Project Meta backing |
| --- | --- | --- |
| Canonical memory | `AGENTS.md` plus narrow `agents/*.md` topical files | `repo-memory-crud.md`, `repo-memory-structure.md` |
| Thread handoff | `.harness/session-receipt.json` (git-ignored) | `session_receipt.py`, hooks README |
| Elastic enforcement state | `HARNESS_PROFILE`, optional `HARNESS_PROFILE_FLOOR` / `HARNESS_PROFILE_CEILING`, transient `.harness/effective-profile` | `derive_profile.py`, hooks README, `recipes/settings.md` |
| Durable work queue | `docs/backlog/` board or external issue tracker linkback | `project-board-crud.md`, `issue-tracking-integration.md` |
| Artifact review | `index.html`, `docs/status.html`, slides, CSV, PDF, Storybook, Streamlit, or app preview | user-facing delivery + browser/side-panel verification |
| Automation/monitoring | Heartbeat or automation prompt that names cadence, stop condition, and writeback target | this reference + hook/board/issue policy |
| Finish line | tests, fixtures, acceptance checklist, rendered artifact inspection, or human approval gate | `execution-policy.md`, `review-tier.md` |

## Elastic Harness Position

The operating loop participates in Project Meta's elastic harness as follows:

- **Static capability:** `agents/codex-operating-loop.md` is a committed policy artifact. Enable, disable, or repair it through `/project-meta init` or `/project-meta settings`; do not treat it as an ad hoc chat note.
- **Elastic visibility:** SessionStart injection, receipt reminders, and lesson reminders may scale with `.harness/effective-profile` when bounded elasticity is configured. This makes long-running Codex loops quieter on low-risk/high-reliability work and more explicit on higher-risk work.
- **Invariant safety:** approval-sensitive gates do not read `.harness/effective-profile`. Destructive command guards, dispatch/board/audit gates, ship/test-integrity gates, and external-send authorization continue to read raw `HARNESS_PROFILE` or explicit user approval. Elasticity must never weaken blast-radius protection.
- **Evidence feedback:** Goals, Heartbeats, dispatch verdicts, review outcomes, and lesson effectiveness should feed the existing evidence stores (`dispatch-log`, `risk-context`, `lessons`, board/issue status). The operating loop consumes those stores; it does not create a parallel scoring system.
- **Settings surface:** profile and capability state remain visible through `/project-meta settings` and the dashboard. A Codex operating loop is "on" only when the artifact is routed from `AGENTS.md` and the backing capabilities it names are installed or explicitly marked manual.

## Operating Rules

- **Files are durable memory; thread history is cache.** Stable decisions, open loops, user preferences, and project state belong in `AGENTS.md`, `agents/*.md`, the board, issue tracker, or a user-reviewed artifact. Do not rely on a pinned thread as the only copy.
- **Diff memory like code.** Every memory write-back should be inspectable. A long-running Codex thread must not quietly accumulate unreviewed "vibes" in canonical memory.
- **Prefer artifact-first review.** When the output is visual, tabular, slide-like, or interactive, create or update an inspectable artifact (`index.html` is often enough) and verify it in the side panel/browser instead of only describing it in Markdown.
- **Steering is allowed, but scope is still binding.** Mid-run user instructions refine the active goal; they do not authorize unrelated edits, dependency changes, or expanded write-sets unless the execution policy says they may proceed.
- **Goals need oracles.** A Codex Goal or long-running task must include a concrete pass condition: command output, tests, rendered artifact inspection, checklist, or human approval. "Implement the plan" is not a sufficient finish line.
- **Heartbeats need stop conditions.** A recurring monitor must name cadence, data source, action boundary, writeback target, and stop/escalation condition. It drafts external messages unless the user explicitly authorizes sending.
- **Remote check-ins preserve the loop, not approval bypasses.** Mobile or remote steering can unblock a task, but destructive operations, auth changes, network calls, dependency changes, and public API changes still follow `execution-policy.md`.
- **Side-panel/browser state is evidence, not memory.** Screenshots, comments, or browser observations should be distilled into the relevant artifact or delivery summary when they affect future work.
- **Elasticity tunes friction, not authority.** A derived effective profile may change reminder verbosity or advisory lesson surfacing; it does not authorize writes, sends, installs, network calls, dependency changes, or merges.

## Codex Init Guidance

During `/project-meta init`, offer the Codex operating loop artifact when all apply:

- Codex is the primary host or a declared primary compat runtime.
- The repo is expected to run multi-turn work, recurring monitors, artifact review, or remote check-ins.
- The user wants durable continuity beyond a single coding task.

Skip it for short-lived repos, one-off edits, or documentation-only repos that already have a sufficient memory/writeback policy.

When enabled, instantiate `templates/codex-operating-loop.md` to `agents/codex-operating-loop.md`, route it from the canonical `AGENTS.md`, and add a row to `agents/project-artifacts.md` when that manifest exists. If hooks are installed, document the configured `HARNESS_PROFILE` and any elastic bounds in the instantiated artifact; if hooks are absent, mark the loop as manual-policy-only.

## Relationship To Existing Project Meta Features

- **Memory Contract:** this reference does not replace `repo-memory-crud.md`; it explains how Codex threads use it across long workstreams.
- **Session receipts:** use receipts for recent transient handoff. Promote only durable facts to canonical memory.
- **Elastic profile:** use `HARNESS_PROFILE` and optional bounds to tune advisory friction. The operating loop must cite the existing profile state instead of inventing a Codex-only strictness mode.
- **Project Board / issue tracker:** use them for open loops and work queues; do not turn `AGENTS.md` into a task log.
- **Hooks:** use hooks to inject receipts and enforce writeback/dispatch gates. Hooks are local enforcement; this reference is policy.
- **Multi-agent protocol:** long-running Codex work may still dispatch workers/reviewers. The operating loop tells Codex where state lives; the multi-agent protocol tells it how roles coordinate.

## Failure Signals

Update the repo harness when any of these repeat:

- The user has to restate project state that should have been on disk.
- A Codex Goal runs without a test, artifact inspection, or acceptance oracle.
- A Heartbeat keeps running after the useful stop condition passed.
- Browser/side-panel feedback disappears into chat history instead of changing an artifact.
- A remote check-in causes approval-sensitive work to proceed without the normal gate.
- Canonical memory grows with session notes instead of durable rules.

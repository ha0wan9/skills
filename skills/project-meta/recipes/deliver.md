# Recipe: deliver

Produce the pre-commit delivery for user review.

## When to load

- User invokes `/project-meta deliver`
- About to commit harness changes (any of: AGENTS.md, agents/*.md, mirrors, templates, USER.md preferences)
- After `/project-meta init` and before `git commit`

## Mode

**read-only** — the deliver conductor assembles the delivery summary and **never edits or commits**. Any file edits in the change set were produced earlier by an *editing* recipe (`init`, or a future editing verb), which owns the subagent dispatch + reviewer loop; `deliver` only verifies the result and assembles it for review. This keeps `deliver` free of edit-capable stages by construction (see `references/execution-policy.md` MUST-STOP "File modification under a read-only command"), so the read-only binding survives any orchestration runner. The user reviews the delivery, then commits separately.

## Required references

- [`references/documentation-delivery.md`](../references/documentation-delivery.md) — the delivery contract: what each section must contain
- [`templates/pre-commit-delivery.md`](../templates/pre-commit-delivery.md) — the seed for the per-project `agents/pre-commit-delivery.md`

Lazy-load:

- [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) — to verify the editing recipe's dispatch + review actually happened for a >1-file change (`deliver` verifies, never dispatches)
- [`references/multi-host-manifests.md`](../references/multi-host-manifests.md) — when mirrors are part of the change

## Workflow

1. **Identify scope**:
   - Which files have changed since last commit?
   - Group changes: user-facing docs / agent-facing docs / templates / mirrors / scripts / hooks / phase-lock / USER.md (the latter never gets committed; verify it's still git-ignored).

2. **Run `validate` first**: a delivery cannot ship with FAILs. If validate exits non-zero, return to `audit` or `init` and fix before delivering.

3. **Confirm the editing recipe already dispatched** (see [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) Reviewer-Between-Subtasks Protocol — its Logging step is where the per-file review verdicts `deliver` checks are recorded):
   - The ≥2-file dispatch (per-file Worker + Reviewer) is the *editing* recipe's responsibility, not `deliver`'s. By the time `deliver` runs, those edits and their review verdicts already exist.
   - `deliver` verifies that the dispatch happened (e.g. review verdicts are present in the change context) and surfaces any missing review as a delivery WARN. It does **not** dispatch editing workers itself, and it never edits.

4. **Render the standard delivery sections**:

   ```
   ### User-facing documentation
   <changes to README, docs/user/, etc.>
   <or "no user-facing changes" with a one-line justification>

   ### Agent-facing documentation
   <changes to AGENTS.md, agents/*.md, references/, templates/>
   <highlight any rule additions or changes>

   ### Behavior or trigger changes
   <new triggers, removed triggers, MUST-rule changes>
   <or "no behavior changes">

   ### Validation
   <validate_target_harness.py exit code + summary>
   <project verifier output if .harness/verify.sh exists>
   <phase-lock check if installed>

   ### Commit scope
   <git diff --stat output>
   <suggested commit message: 1-line subject + body>
   ```

5. **Mirror sync check**:
   - If canonical changed structurally, run `render_host_manifests.py --dry-run` and include the diff in the delivery so the user knows mirrors will need regeneration after commit.
   - Hand-edited mirrors that diverge from canonical: surface as WARN.
   - **Ordering**: mirrors are generated *from integrated canonical state*. In the editing recipe, mirror render must sit behind a hard barrier after canonical edits are integrated and reviewed — never in the same unbarriered parallel/pipeline stage as the canonical edits (see `references/multi-agent-protocols.md` "Ordering barriers"). `deliver` only reports the resulting drift; it does not render.

6. **Hand off to user**:
   - Present the assembled delivery.
   - Wait for explicit approval before any commit operation.
   - Never invoke `git commit` from within `deliver`.

## Output contract

The standard delivery sections (above), in order, with concrete file paths and rule citations. The user reviewing this should be able to decide commit/revise without re-reading the diff.

## Anti-patterns

- **`deliver` editing files.** `deliver` is read-only assembly. If edits are needed, the editing recipe (`init`) runs them with its dispatch + reviewer loop first; `deliver` only assembles the result. Edits performed under `deliver` are a MUST-STOP (execution-policy "File modification under a read-only command").
- **Auto-committing, or batch-running past a BLOCKER inside a background runner.** The commit boundary and any BLOCKER are synchronous user gates; a background run (Workflow / Agents-SDK) MUST return to them, never pass through (see `references/multi-agent-protocols.md` "Synchronous Gates Under Orchestration"). `deliver` never invokes `git commit`.
- **Skipping the validation section.** A delivery without validation evidence is incomplete; force `validate` first.
- **Bundling user-facing and agent-facing changes without separation.** They have different reviewers and different update cadences; keep them in distinct delivery sections.

## Where the dispatch protocol lives

`deliver` does **not** own the subagent dispatch protocol — the *editing* recipe (`init`, or a future editing verb) does. The single source of truth for the per-file Worker + Reviewer loop, the BLOCKER synchronous-halt semantics, and the per-runtime backings (Claude Code Workflow, Codex Agents-SDK) is [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) (Mandatory Subagent Dispatch + Reviewer-Between-Subtasks + Synchronous Gates). `deliver` consumes the *result* of that loop (edited files + review verdicts) and assembles the delivery; it never edits, dispatches editing workers, or commits.

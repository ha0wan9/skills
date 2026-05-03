# Recipe: deliver

Produce the pre-commit delivery for user review.

## When to load

- User invokes `/project-meta deliver`
- About to commit harness changes (any of: AGENTS.md, agents/*.md, mirrors, templates, USER.md preferences)
- After `/project-meta init` and before `git commit`

## Mode

**read-only** — assembles the delivery summary. Does not commit, does not edit files. The user reviews, then commits separately.

## Required references

- [`references/documentation-delivery.md`](../references/documentation-delivery.md) — the delivery contract: what each section must contain
- [`templates/pre-commit-delivery.md`](../templates/pre-commit-delivery.md) — the seed for the per-project `agents/pre-commit-delivery.md`

Lazy-load:

- [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md) — when the change touches >1 file and subagent dispatch is in scope
- [`references/multi-host-manifests.md`](../references/multi-host-manifests.md) — when mirrors are part of the change

## Workflow

1. **Identify scope**:
   - Which files have changed since last commit?
   - Group changes: user-facing docs / agent-facing docs / templates / mirrors / scripts / hooks / phase-lock / USER.md (the latter never gets committed; verify it's still git-ignored).

2. **Run `validate` first**: a delivery cannot ship with FAILs. If validate exits non-zero, return to `audit` or `init` and fix before delivering.

3. **Subagent dispatch decision** (see [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md)):
   - When the change touches ≥2 of {AGENTS.md, agents/*.md, mirrors, templates}, **MUST** dispatch per-file edits to fresh subagents with a reviewer subagent between commits. The deliver recipe orchestrates the dispatch; the conductor agent never edits.
   - Single-file or trivial changes can stay in the conductor's context.

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

6. **Hand off to user**:
   - Present the assembled delivery.
   - Wait for explicit approval before any commit operation.
   - Never invoke `git commit` from within `deliver`.

## Output contract

The standard delivery sections (above), in order, with concrete file paths and rule citations. The user reviewing this should be able to decide commit/revise without re-reading the diff.

## Anti-patterns

- AP-COORD-1: Conductor edits and orchestrates simultaneously. Multi-file harness changes MUST dispatch per-file subagents.
- AP-COORD-2: No reviewer between sub-tasks. Reviewer subagent runs after every implementation subagent commits.
- Committing inside deliver. Never. The user owns the commit boundary.
- Skipping the validation section. A delivery without validation evidence is incomplete; force `validate` first.
- Bundling user-facing and agent-facing changes without separation. They have different reviewers and different update cadences; keep them in distinct delivery sections.

## Subagent dispatch protocol (when triggered)

For each file in the change set:

1. Conductor packages a brief: target file path, the rule or anti-pattern motivating the change, the success criterion, the surrounding context (≤1 page).
2. Dispatch implementation subagent with the brief. Subagent edits only the target file; conductor does not see the edit until the subagent reports back.
3. Dispatch reviewer subagent with the diff + the original brief. Reviewer reports PASS / BLOCKER / SUGGEST. BLOCKER halts the chain; conductor surfaces it to the user.
4. Reviewer PASS → conductor proceeds to next file.
5. After all files PASS: assemble the delivery summary (this recipe's main path).

The dispatch protocol detail lives in [`references/multi-agent-protocols.md`](../references/multi-agent-protocols.md). The recipe enforces *when* it triggers; the reference documents *how*.

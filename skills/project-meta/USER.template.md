# User Preferences

This file is a Project Meta skill-layer seed and preference questionnaire. Do not copy or commit this file into target project repositories by default.

Use this seed as target-config input to render a local `USER.md` for project-specific user collaboration preferences.

`USER.md` is intentionally ignored by Git because it may contain personal workflow preferences that should not be pushed to the shared skill repository.

During `/project-meta init`, copy or merge `.gitignore.template` so local `USER.md` and accidental root `USER.template.md` files are ignored in the target project.

## Rendering Contract

During `/project-meta init`, or when resetting or changing local preferences, use this file as a questionnaire source:

1. Ask the user to choose one preset: Minimal, Structured, Strict, Secure, or Custom.
2. Ask the user which optional checklist items or categories should be enabled.
3. Render the result into root `USER.md` as local project configuration.
4. Mark selected preferences with `[x]`.
5. Omit unselected checklist items unless the user explicitly asks for an editable full checklist.
6. Do not copy this template body verbatim into `USER.md`.
7. Do not create or commit `USER.template.md` in target project repositories.

The rendered `USER.md` should contain only the selected preset, selected checked preferences, and any explicit free-form user preferences.

When updating an existing `USER.md`, reload this template first, ask the user to reselect options, then overwrite local `USER.md` only after confirmation.

## Preferences

Choose a preset during `/project-meta init`, then keep only the preferences that should apply to this local project.

## Presets

- [ ] Minimal: keep local `USER.md`, follow basic read order, write back durable memory only, run validation when available, and do not automatically commit or push.
- [ ] Structured: Minimal plus pre-commit delivery, user-facing docs review, validation before commit, memory writeback closeout, and concise final status.
- [ ] Strict: Structured plus complex-task planning/review, Lead-owned multi-agent delegation, branch/PR flow, commit after approved operations, and push after approved operations.
- [ ] Secure: Structured plus local-only user preferences, no secrets in memory, ask before destructive Git operations, require explicit write scopes for sub-agents, and require delivery before overwriting project-level artifacts.
- [ ] Custom: select individual preferences below.

## Preference Checklist

### Commit And Push

- [ ] Create a commit after each approved operation.
- [ ] Push each commit to the cloud remote.
- [ ] Ask before force-push, history rewrite, or destructive Git operations.
- [ ] Use a branch and PR flow instead of pushing directly to the default branch.

### Pre-Commit Delivery

- [ ] Show a delivery before every commit.
- [ ] Include user-facing docs, agent-facing docs, behavior changes, validation, and commit scope in each delivery.
- [ ] Require user review when user-facing docs change.

### Documentation Mode

- [ ] Treat shared/user-facing docs as the primary documentation read by both users and agents.
- [ ] Keep agent-only execution details in agent-facing docs.
- [ ] Keep `USER.md` local-only and out of Git.

### Memory Writeback

- [ ] Write back only durable repo facts, validated workflows, and reusable lessons.
- [ ] Do not write transient task logs, unresolved hypotheses, or secrets into memory.
- [ ] Run a memory writeback check at task closeout.

### Multi-Agent

- [ ] Allow explicit multi-agent trigger.
- [ ] Allow complexity-based multi-agent trigger.
- [ ] Require Lead-owned planning, context packages, ownership boundaries, and review criteria for delegated work.
- [ ] Default sub-agents to read-only unless given an explicit write scope.

### Validation

- [ ] Run available validation before commit.
- [ ] Block commit when validation fails.
- [ ] Allow commit with failed validation only when the delivery calls out the risk.

### Safety gates

- [ ] Ask before destructive Git operations.
- [ ] Ask before overwriting project-level artifacts.
- [ ] Keep secrets and local machine state out of tracked documentation.

### Tooling Preferences

- [ ] Consult RTK or `RTK.md` when available and relevant.
- [ ] Keep tool usage preferences and local tool machine state out of tracked project memory unless they are project requirements.

### Interaction Style

- [ ] Give a short plan before complex tasks.
- [ ] Keep final answers concise with changed files, validation, and commit or push status.
- [ ] Explain key decisions in Chinese.

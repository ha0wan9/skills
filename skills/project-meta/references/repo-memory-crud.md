# Repo Memory CRUD

> The monolith-vs-split decision policy and structural rules are canonical in [`repo-memory-structure.md`](repo-memory-structure.md). This file owns the per-action lifecycle (create, read, update, delete, consolidate).

Use this reference when creating, reading, updating, deleting, or consolidating repo memory.

## Memory Contract

The two-leg protocol every skill follows. It is enforced by hooks at the host
layer (read leg = `SessionStart`, write leg = `Stop`) and backed by
`scripts/repo_memory.py`; skills that cannot reach a hook restate this inline as
a thin floor (see [`shared-cli-delegation.md`](shared-cli-delegation.md)).

- **Read leg (session start / before substantive work).** Resolve the canonical
  entrypoint (`CLAUDE.md` when Claude Code is primary, else `AGENTS.md`), read
  it, and load only the topical `agents/*.md` the task needs. Mechanized by
  `repo_memory.py --target-root . read`. In repos that accumulate git worktrees,
  pair this with the **Worktree Trim Contract** (gather via
  `worktree_audit.py`, then trim/surface/route) — see
  [`worktree-hygiene.md`](worktree-hygiene.md).
- **Write-back leg (turn close).** If the turn changed substantive files,
  decide **write now / suggest only / skip** for any durable lesson before
  ending. Mechanized by `repo_memory.py --target-root . writeback`: it flags a
  pending decision when work landed but no memory file changed and no
  `.harness/writeback-ack` marker exists. Profile-gated (`minimal` disables;
  `strict` blocks the turn). The writeback quality bar is the rest of this file.

## Create

- First, detect whether the repo already has established canonical memory files and preserve that convention when it is coherent.
- Also detect the primary agent tool context. When Claude Code is primary, the canonical entrypoint is `CLAUDE.md`; when Codex is primary or the tool context is unknown, it is `AGENTS.md`.
- If the repo has no bootstrap memory yet, default to creating the correct canonical entrypoint for the detected tool context first.
- Create a canonical user-preference file such as `USER.md` only for explicit, stable user preferences.
- Create a topical-memory directory such as `agents/` only when repo memory is large enough that selective loading will materially reduce irrelevant context.
- When splitting memory, keep the project-memory loader/index short and move detailed guidance into topical files such as architecture, runtime, testing, operations, or legacy reference.
- Create a new topical file only when the content is durable, materially distinct, and would otherwise make another topical file too broad.
- If the current repo-memory structure is missing or obviously messy, treat cleanup and restructuring as valid create work, not as optional polish.

## Read

- Read the canonical memory files and the `README.md` structure map first.
- For long shared docs such as `README.md`, prefer an index, table of contents, or bounded extraction before loading the full file.
- Load the full `README.md` only when editing user-facing docs, checking install behavior, or needing the complete shared explanation.
- If the project-memory loader points to topical files, load only the files relevant to the current task.
- Prefer one or two topical files over bulk-loading every memory file.
- If a task crosses boundaries, load the smallest additional topical file that covers the second concern.

## Update

### Project-memory loader

Update the loader when:
- bootstrap order changed
- loading policy changed
- topic routing changed
- global guardrails changed
- the repo collapsed from split memory back to a monolith, or split from a monolith into topical files

Do not expand the loader with topic-specific detail when a topical file is the better home.
If the loader has drifted into a messy monolith, restructure it back into a clean loader plus topical files when justified.
If repeated agent behavior shows that the loader does not route clearly enough, tighten the routing rule before adding more content.

### Topical memory files

Update the relevant topical file when:
- the durable fact is specific to one concern
- a validated workflow or trap belongs to one topic
- a test map, architecture fact, runtime rule, or operations recipe changed

### User-preference file

Update only for explicit, stable user preferences that will matter again.

## Delete Or Consolidate

- Delete or merge a topical file when it became stale, overlaps heavily with another, or is too small to justify separate loading.
- Remove stale rules instead of layering contradictory notes on top.
- If you delete a topical file, update the loader routing in the same task.
- If you collapse split memory back into a single file, rewrite the loader so it remains authoritative and has no dangling links.
- If the structure is messy enough that CRUD actions alone are not enough, perform the larger reorganization needed to restore a clean, low-friction memory layout.

## Quality Bar

- Keep canonical memory concise, precise, and free of session-only notes.
- Prefer replacing stale guidance over appending contradictory guidance.
- Include exact paths, commands, config names, dates, or task IDs when they prevent ambiguity.
- Prefer guidance that is easy to verify mechanically. If an important memory rule needs regular enforcement, note the likely linter, script, checklist, or cleanup routine.

# Mirrors And Updates

Use this reference when syncing canonical repo memory into tool-specific mirrors or deciding whether a lesson belongs in memory at all.

## Canonical Sources

- canonical project-memory file
- topical memory files when present
- canonical user-preference file

Common defaults are `AGENTS.md`, `agents/*.md`, and `USER.md`, but preserve coherent repo-specific conventions when they already exist.

## Mirrors

### `CLAUDE.md`

- Keep it thin.
- Point to the canonical project-memory file, the topical-memory structure when present, and the canonical user-preference file.
- Do not let it drift into a second source of truth.

### `.github/copilot-instructions.md`

- Keep it thin and high-signal.
- Tell Copilot to read the canonical project-memory loader first and then only the relevant topical files.
- Mirror only the highest-priority repo rules, not the full memory corpus.

## When To Sync Mirrors

- canonical memory structure changed
- high-priority global guardrails changed
- bootstrap order changed
- user preferences relevant to those tools changed
- a canonical rule moved from advisory prose into a required validation or recurring cleanup workflow

## When Not To Edit Memory

Do not update canonical memory or mirrors for:
- speculative fixes
- one-off task logs
- local transient machine state
- facts that are not yet verified durable

## Cleanup Loop

- Periodically remove stale or duplicated mirror guidance.
- Keep mirrors as routing aids; do not let them become alternate manuals.
- If a mirror contains a rule missing from canonical memory, either promote it to the canonical source or delete it from the mirror.

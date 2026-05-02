# Mirrors And Updates

Use this reference when syncing canonical repo memory into tool-specific mirrors or deciding whether a lesson belongs in memory at all.

## Tool Awareness

Which file is canonical depends on which agent tool is the primary consumer. Detect the tool context before assigning canonical/mirror roles:

- **Claude Code is primary**: `CLAUDE.md` is the canonical entrypoint — Claude Code auto-loads it from the project root and parent directories. `AGENTS.md` is the mirror for non-Claude tools (Codex, Copilot, etc.).
- **Codex / GPT-5.4 is primary**: `AGENTS.md` is the canonical entrypoint. `CLAUDE.md` is the mirror.
- **Both tools are used**: pick one canonical entrypoint consistent with the repo's actual usage, keep both files as thin routing loaders pointing to the same topical files, and keep them in sync on bootstrap order and global guardrails.

## Canonical Sources

- canonical project-memory file (detected by tool context above)
- topical memory files when present
- canonical user-preference file

Default to `AGENTS.md`, `agents/*.md`, and `USER.md` when the tool context is unknown, but preserve coherent repo-specific conventions when they already exist. When Claude Code is the primary or only agent tool, treat `CLAUDE.md` as the canonical entrypoint and `AGENTS.md` as the mirror.

## Mirrors

### `CLAUDE.md`

When Claude Code is the primary consumer, `CLAUDE.md` is the canonical entrypoint; keep it thin, route to topical files, and treat it as the source of truth for bootstrap order and global guardrails. `AGENTS.md` is then the mirror.

When another tool is primary, `CLAUDE.md` is a mirror: keep it thin, point to the canonical project-memory file, and do not let it drift into a second source of truth.

In both cases, write the actual durable rules into topical files (e.g. `agents/*.md`), not into the loader.

### `AGENTS.md`

When Claude Code is the primary consumer, `AGENTS.md` is a mirror of `CLAUDE.md`: sync bootstrap order, routing, and global guardrails from `CLAUDE.md` so non-Claude agents have a clean entrypoint.

When another tool is primary, `AGENTS.md` is the canonical entrypoint.

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

# Repo Memory Structure

## Contents

- [Default Model](#default-model) — loader, topical files, user prefs, mirrors
- [Shared Docs Loading Policy](#shared-docs-loading-policy) — selective vs eager
- [README Structure Map](#readme-structure-map) — agent-facing routing aid for long shared docs
- [Monolith Vs Split](#monolith-vs-split) — when to keep memory in one file
- [Split-Memory Design Rules](#split-memory-design-rules) — keeping the loader thin
- [What Belongs Where](#what-belongs-where) — loader vs topical vs user-prefs
- [Anti-Patterns](#anti-patterns) — drift signals to fix not tolerate

Use this reference when deciding how repo memory should be organized.

## Default Model

- canonical project-memory file such as `AGENTS.md` (or `CLAUDE.md` when Claude Code is the primary agent): bootstrap loader, read order, global guardrails, and topic routing
- topical memory files such as `agents/*.md`: detailed topical memory when the repo is broad enough to benefit from selective loading
- canonical user-preference file such as `USER.md`: durable user collaboration preferences
- tool-specific mirrors such as `CLAUDE.md` and `.github/copilot-instructions.md`: thin mirrors of the canonical memory

If the repo already uses an established naming convention, preserve it. If not, detect the primary agent tool: when Claude Code is primary, default to `CLAUDE.md`, `agents/*.md`, and `USER.md`; when Codex is primary or tool context is unknown, default to `AGENTS.md`, `agents/*.md`, and `USER.md`.

## Shared Docs Loading Policy

Shared/user-facing docs such as `README.md` are the primary project explanation, but they should not automatically be loaded in full during cold start.

Use this loading order:

1. Read the project-memory loader first when it exists.
2. Inspect shared docs lightly: title, intro, table of contents, or heading map.
3. Read targeted sections that match the current task.
4. Read the full shared doc when it is short, when the task edits shared docs, or when the task depends on global project semantics.

Primary means authoritative for project purpose, usage, architecture, and reviewed behavior. It does not mean eager full-context loading.

## README Structure Map

When `README.md` or another shared doc becomes long enough that repeated full reads waste context, maintain a lightweight agent-facing structure map. Prefer `agents/readme-structure.md` when the project already has an `agents/` directory; otherwise keep a short `README Structure` section in the project-memory loader.

The structure map should contain:

- source path and last reviewed commit or date
- heading map with line ranges when available
- one-line purpose per major section
- routing hints: which task types should read which sections
- update triggers: when README headings, section order, or user-facing behavior changes

Do not copy user-facing prose into the structure map. It is a routing aid, not a parallel README.

For mechanical loading, use a heading-first bounded extractor when available:

```bash
python3 scripts/extract_doc_context.py README.md --index
python3 scripts/extract_doc_context.py README.md --heading "Install" --query "git repo" --within-lines 80 --max-lines 40
```

Best default behavior:

1. Load the heading index first.
2. Match the user's task to a heading or structure-map route.
3. Search for the body keyword only within a bounded line window after that heading.
4. Print a capped excerpt with line numbers.
5. Expand the budget only with an explicit reason.

## Monolith Vs Split

Keep a single canonical project-memory file when:
- repo memory is still short
- one-pass loading is efficient
- there are not enough distinct topics to justify routing

Split into a project-memory loader plus topical files when:
- repo memory is broad enough that full loading buries the relevant guidance
- the repo has stable domains such as architecture, runtime, testing, operations, or legacy reference
- different tasks routinely need different subsets of durable memory

## Split-Memory Design Rules

- Keep the project-memory loader short and decision-oriented.
- Use the loader/index as the router, not the long-form knowledge store.
- Keep topical files narrow and named by the questions they help answer.
- Prefer one durable concern per topical file.
- Avoid creating so many files that routing overhead cancels out the context savings.
- If the current memory structure is messy, contradictory, or inefficient to load, prefer restructuring it to a cleaner model rather than preserving accidental complexity.
- Make routing verifiable where possible: exact file paths, ownership, topic boundaries, and when-to-load rules beat broad advice.
- Capture large plans, design history, and technical debt as versioned artifacts when they need to survive beyond one task.

## What Belongs Where

### Project-memory loader

- bootstrap order
- loading policy
- topic routing
- global guardrails
- only the minimal facts needed to decide what to load next

### Topical memory files

- architecture and extension-point facts
- runtime and operations traps
- test selection and invariants
- date-scoped validated workflows
- legacy-reference guidance

### User-preference file

- explicit stable user preferences

## Anti-Patterns

- monolithic project-memory files that accumulate every detail forever
- topical files that overlap heavily or are too thin to justify separate loading
- putting volatile task logs into canonical memory
- duplicating the same guidance across the loader and topical files
- tolerating clearly broken or messy memory structure just because it already exists
- leaving high-impact rules as prose when a check, template, or script can enforce them

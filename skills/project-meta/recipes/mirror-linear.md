# Recipe: mirror-linear

Push-only, interactive mirror from the Project Board store to Linear (DASH-03). This is a specialization of the issue-tracker Track Loop, not a second backlog system.

## When to load

- User asks to mirror Project Board items to Linear.
- User asks for a Linear export/plan for `docs/backlog/items.jsonl`.
- User asks how to record or audit `linear_id` values.

## Mode

**Read-only by default.** The local command exports a dry-run plan and performs no live write. A live Linear push is a separate operator checkpoint through an available Linear MCP/CLI, followed by an explicit `board.py edit <id> --linear-id <LINEAR-ID>` write-back when an issue is created.

## Required references

**Base** — loaded when the verb runs:

- [`references/linear-mirror.md`](../references/linear-mirror.md) — Project Board push-only mirror contract.
- [`references/issue-tracking-integration.md`](../references/issue-tracking-integration.md) — generic Track Loop and canonical-vs-mirror rules.

## Workflow

1. Snapshot the store:

   ```bash
   python3 skills/project-meta/scripts/board.py mirror-linear --root .
   ```

   Add `--json` for machine-readable handoff to a connected Linear tool.
2. Check Linear for existing issues before creating anything. Match by existing `linear_id`, Project Board id, and title keywords.
3. For `create` rows, create a Linear issue with the exported title/body. The body must summarize and **link back** to the repo; do not paste the whole source artifact as a new source of truth.
4. For `update` rows, update the mirrored Linear issue from the repo-canonical row.
5. Record new Linear ids back into the repo with:

   ```bash
   python3 skills/project-meta/scripts/board.py edit <PROJECT-BOARD-ID> --linear-id <LINEAR-ID>
   ```

6. If Linear has changed directly, treat it as reverse drift. Do not pull automatically; decide interactively whether the repo should change, then use `board.py edit`.

## Output contract

A dry-run plan listing rows to create/update, or a JSON export carrying `dry_run: true`. If a live push is performed, report which Linear ids were created/updated and which repo rows still need `linear_id` write-back.

## Anti-patterns

- **Two-way sync.** Linear is not canonical; never pull direct Linear edits automatically.
- **Headless push.** The mirror is interactive-only and must not run from capture hooks/subprocesses.
- **Full-paste issues.** Linear bodies summarize and link back; they are not duplicate specs.
- **Duplicate creates.** Always check first; if uncertain, stop and ask rather than creating another issue.

---
artifact_name: linear-mirror
instantiated_from: project-meta/references/linear-mirror.md
source_reference: project-meta/references/issue-tracking-integration.md
project_scope: this repo only
owner: agent-facing
review_policy: wave review for project-board v0.3; live Linear pushes require operator checkpoint
last_reviewed: 2026-06-07
---

# Linear Mirror (Push-Only)

Use this reference when mirroring Project Board rows from the repo-canonical store to Linear. It specializes the issue-tracker Track Loop in [`issue-tracking-integration.md`](issue-tracking-integration.md) for the Project Board store.

## Contract

- **Repo canonical, Linear mirror.** `docs/backlog/items.jsonl` remains the source of truth. Linear issue bodies summarize the item and **link back** to the repo artifact/source path.
- **Push-only.** The mirror exports creates/updates from the repo to Linear. It does not pull Linear edits back into the store. Reverse drift is documented and resolved manually in the repo via `board.py edit`.
- **Interactive-only.** The mirror runs only in an operator/agent session with explicit intent. It never runs from the headless capture subprocess or from an autonomous hook.
- **Dry-run by default.** The local CLI emits a plan/export that lists what would be pushed. A live Linear write is a separate operator-triggered action through the connected Linear MCP/CLI.
- **Bidirectional id.** After a live create, record the returned Linear issue id back into the row's `linear_id` with `board.py edit <id> --linear-id <LINEAR-ID>`.

## Track Loop Specialization

1. **Check first.** Before creating a Linear issue, search Linear for the Project Board id/title and for any existing `linear_id`. Never create a duplicate.
2. **Plan from repo.** Run:

   ```bash
   python3 skills/project-meta/scripts/board.py mirror-linear --root .
   ```

   Use `--json` when a machine-readable export is needed for a connected Linear tool.
3. **Push interactively.** For rows with `action: create`, create a Linear issue with the exported title/body and repo backlink. For rows with `action: update`, update the existing issue's summary/state/comment from the exported body.
4. **Record ids.** For created issues, write the returned id back with `board.py edit <id> --linear-id <LINEAR-ID>`.
5. **Resolve reverse drift in repo.** If Linear has been edited directly, do not pull it automatically. Inspect the drift, then update `items.jsonl` through the board CLI if the repo should change.

## Export Shape

`board.py mirror-linear --json` emits:

- `id`, `linear_id`, `action` (`create` or `update`), `title`, `state_hint`, and `body`.
- `repo_backlink` and `source` so the Linear body can link back instead of becoming a second source of truth.
- `dry_run: true` to make the non-writing behavior explicit.

The command performs no network calls and does not mutate the store.

---
artifact_name: issue-tracking
instantiated_from: project-meta/templates/issue-tracking.md
source_reference: project-meta/references/issue-tracking-integration.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before tracker binding changes
last_reviewed: 2026-06-13
---

# Issue Tracking (Linear)

Feature work is tracked in **Linear**: team `ArkProjection` (key `ARK`, id `5932ba93-314a-4ead-a962-9421f9e79638`), project `hw-skills` (id `1b8771c8-e720-45ac-91aa-325421011557`, url https://linear.app/arkprojection/project/hw-skills-905187070672). The repo stays canonical — explored ideas and specs live in `docs/backlog/` and related repo artifacts; tracker issues **summarize and link back** to those artifacts, never the reverse.

When the user proposes or advances a feature, run the Track Loop using the connected Linear MCP tools (`list_issues`, `save_issue`, `list_projects`, `get_issue`, and related tools on the Linear MCP server — the hook cannot reach these; only the agent can):

1. **Check first.** Query the `hw-skills` project for an existing ticket (by feature name / keywords) before creating anything. Do not open a duplicate.
2. **Write progress back.** When a feature advances — spec added, phase planned, implemented, shipped — update the existing ticket (description, state, and/or a comment) so it reflects reality. This step runs at task closeout alongside the memory write-back check (`memory-writeback-check.md`).
3. **Open if missing.** If no ticket exists, create one using `save_issue` in team `ArkProjection` / project `hw-skills`: **no default label** (labels are chosen per-issue at push time — do not invent one); state `Backlog`; body = a summary + link to the canonical repo artifact (and a source link, e.g. the GitHub blob). Do not paste the full spec — the repo is source of truth; pastes drift.

After a new issue is created in Linear, write the assigned Linear id back into the repo artifact (e.g. the backlog index or relevant doc) via:

```
python3 skills/project-meta/scripts/board.py edit <ID> --linear-id <LINEAR-ID>
```

To preview what `board.py mirror-linear` would push without writing anything:

```
python3 skills/project-meta/scripts/board.py mirror-linear --root .
```

This produces a push-only dry-run plan. The repo (docs/backlog store) remains canonical; Linear issues summarize and link back, never the reverse.

## Conventions

- Issue body = **summary + link** to the canonical repo artifact. Do not paste full specs.
- Mark coupled features (e.g. intent/outcome pairs) as related to each other in Linear.
- Mirror the Linear ticket id back into the repo artifact so the link is bidirectional.
- Labels are chosen per-issue at push time — there is no project-wide default label; record this explicitly and do not invent one.
- Creating/updating tracker issues is outward-facing — confirm the structure (project vs. loose issues, labels) before writing when it is not obvious from the request.

## Binding

| Field | Value |
|---|---|
| Tracker | Linear |
| MCP / CLI | Linear MCP (`list_issues`, `save_issue`, `list_projects`, `get_issue`, etc.) — agent-only; hook cannot reach it |
| Team / org | ArkProjection (key `ARK`, id `5932ba93-314a-4ead-a962-9421f9e79638`) |
| Project / board | hw-skills (id `1b8771c8-e720-45ac-91aa-325421011557`, https://linear.app/arkprojection/project/hw-skills-905187070672) |
| Default state | Backlog |
| Label(s) | NONE by default — chosen per-issue at push time |
| Canonical spec path | `docs/backlog/` and related repo artifacts |
| Mirror script | `python3 skills/project-meta/scripts/board.py mirror-linear --root .` (dry-run plan) |
| Id write-back | `python3 skills/project-meta/scripts/board.py edit <ID> --linear-id <LINEAR-ID>` |

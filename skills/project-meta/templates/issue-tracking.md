---
artifact_name: issue-tracking
instantiated_from: project-meta/templates/issue-tracking.md
source_reference: project-meta/references/issue-tracking-integration.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before tracker binding or label conventions change
last_reviewed: <YYYY-MM-DD>
---

<!--
SEED — instantiate to agents/issue-tracking.md (or the repo's topical-memory
dir). Fill every <ANGLE_BRACKET> with the concrete binding, set last_reviewed,
and add a Topic Routing pointer to this file from the canonical memory file.
Keep tracker identifiers HERE, not in the loader or the hook. Procedure: see
project-meta/references/issue-tracking-integration.md. Delete this comment on
instantiation.
-->

# Issue Tracking (<TRACKER>)

Feature work is tracked in **<TRACKER>**: <SCOPE — e.g. team `<TEAM>`, project
`<PROJECT>` (`<PROJECT_URL>`)>. The repo stays canonical — explored ideas and
specs live in `<CANONICAL_SPEC_PATH — e.g. docs/backlog/*.md>`; tracker issues
**summarize and link back** to those artifacts, never the reverse.

When the user proposes or advances a feature, run the Track Loop using
<TRACKER_TOOL — e.g. the Linear MCP tools / `gh issue` / Jira MCP>:

1. **Check first.** Query <PROJECT/BOARD> for an existing ticket (by feature
   name / keywords) before creating anything. Do not open a duplicate.
2. **Write progress back.** When a feature advances (spec added, phase planned,
   implemented, shipped), update its ticket — description, state, and/or a
   comment — so it reflects reality. This runs at task closeout alongside
   [`memory-writeback-check`](memory-writeback-check.md).
3. **Open if missing.** If no ticket exists, create one in <PROJECT/TEAM> with
   `save_issue`/equivalent: <LABEL_CONVENTION — e.g. `premium` label>, state
   `<DEFAULT_STATE — e.g. Backlog>`, body = a summary + link to the canonical
   `<CANONICAL_SPEC_PATH>` artifact (and a source link, e.g. the GitHub blob).

## Conventions

- Issue body = **summary + link** to the canonical repo artifact. Do not paste
  full specs (the repo is source of truth; pastes drift).
- Mark coupled features (e.g. intent/outcome pairs) related to each other.
- Mirror the ticket id back into the repo artifact (e.g. a backlog index) so the
  link is bidirectional.
- Creating/updating tracker issues is outward-facing — confirm the structure
  (project vs. loose issues, labels) before writing when it is not already
  obvious from the request.

## Binding

| Field | Value |
|---|---|
| Tracker | <TRACKER> |
| MCP / CLI | <TRACKER_TOOL> |
| Team / org | <TEAM> |
| Project / board | <PROJECT> (`<PROJECT_URL>`) |
| Default state | <DEFAULT_STATE> |
| Label(s) | <LABELS> |
| Canonical spec path | <CANONICAL_SPEC_PATH> |

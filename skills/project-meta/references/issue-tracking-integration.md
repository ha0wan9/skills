# Issue-Tracking Integration

Use this reference when wiring a repo's harness to an external issue tracker
(Linear, GitHub Issues, Jira, …) so feature work is consistently mirrored, or
when installing / auditing the `issue-tracker` opt-in capability.

This is the **procedure**. The copyable seed is
[`templates/issue-tracking.md`](../templates/issue-tracking.md); the advisory
hook is `templates/hooks/scripts/issue-tracker-reminder.sh`. One source of truth
per fact: this reference owns the protocol; the template and recipe only point
here.

## Contents

- [What this capability is — and is not](#what-this-capability-is--and-is-not)
- [The Track Loop](#the-track-loop)
- [Canonical vs mirror: the repo stays source of truth](#canonical-vs-mirror-the-repo-stays-source-of-truth)
- [Install footprint](#install-footprint)
- [The advisory hook](#the-advisory-hook)
- [Audit signals](#audit-signals)
- [Anti-patterns](#anti-patterns)

## What this capability is — and is not

**Is:** a durable, agent-legible workflow that keeps an external tracker in step
with feature work — check for an existing ticket before opening one, write
progress back as work advances, open a ticket when none exists — plus an
optional advisory hook that *reminds* the agent to run the loop at the moment a
feature is proposed.

**Is not:** automation that reads or writes the tracker by itself. The tracker
is reachable only through an MCP server (or CLI) available to the **agent**, not
to a shell hook. The hook therefore **reminds**; it never queries, asserts, or
gates on tracker state. Treat any design that has the hook "check Linear" as a
bug (it cannot — see AP-VAL-1 and the *advisory hook* section).

## The Track Loop

When the user proposes or advances a feature, the agent runs three steps using
whatever tracker MCP/CLI is connected:

1. **Check first.** Query the project/board for an existing ticket (by feature
   name / keywords) before creating anything. Never open a duplicate.
2. **Write progress back.** When the feature advances — spec written, phase
   planned, implemented, shipped — update the existing ticket (description,
   state, and/or a comment) so it reflects reality. This is the *write-back*
   leg, and it runs at task closeout alongside the Memory Contract
   ([`repo-memory-crud.md#memory-contract`](repo-memory-crud.md#memory-contract)).
3. **Open if missing.** If no ticket exists, create one in the configured
   project/team with the configured labels, body = a summary that **links back
   to the canonical repo spec**, not a full paste.

The loop is tracker-agnostic. The instantiated `agents/issue-tracking.md`
records the *concrete* binding (which tracker, project/team identifiers, label
conventions, the MCP tool family to call).

## Canonical vs mirror: the repo stays source of truth

The repository is canonical; the tracker is a mirror. Issue bodies **summarize
and link back** to the in-repo artifact (a `docs/backlog/*.md` spec, an
`AGENTS.md` section, a design doc) — never the reverse. Full pastes into the
tracker drift the moment the repo changes (the *Writing for the Model* "one
source of truth per fact" rule). Mirror the ticket id back into the repo
artifact so the link is bidirectional and an auditor can cross-check both ways.

## Install footprint

The `issue-tracker` capability instantiates a small, provenance-stamped
footprint into the target repo:

- `agents/issue-tracking.md` — instantiated from `templates/issue-tracking.md`,
  carrying the full provenance frontmatter block and the concrete tracker
  binding. This is the durable workflow the agent reads.
- A **Topic Routing** pointer in the canonical memory file (`AGENTS.md` /
  `CLAUDE.md`) to `agents/issue-tracking.md`, plus a one-line closeout note in
  the memory write-back check so step 2 fires at task end.
- A manifest row in `agents/project-artifacts.md`.
- *(optional)* the advisory hook, when the repo also runs the hooks pack.

Keep the binding in the instantiated artifact, not in the hook or the loader —
the loader stays a thin router (AP-MEM-1).

## The advisory hook

`issue-tracker-reminder.sh` is a `UserPromptSubmit` hook that scans the user's
prompt for feature-proposal shape (a feature is being proposed, an idea pitched,
"let's build", a spec requested) and, on a match, prints a short reminder to run
the Track Loop. It is **profile-aware** (`$HARNESS_PROFILE`):

- `minimal` — disabled (exit 0).
- `standard` — advisory: prints the reminder on a keyword match, never blocks.
- `strict` — prints a stronger MUST-phrased reminder; still never blocks (a hook
  cannot verify tracker state, so it must not fail the turn — that would be
  enforcement it cannot back up).

The hook is **opt-in and separate from the default three-hook pack** — it ships
only when the `issue-tracker` capability is installed, and it carries no tracker
specifics (those live in `agents/issue-tracking.md`). Tune its trigger
vocabulary conservatively: a reminder that fires on every prompt is dead noise
(AP-VAL-1); one that fires only on genuine feature-proposal shape stays signal.

## Audit signals

`scripts/validate_target_harness.py` covers capability integrity: if
`agents/issue-tracking.md` is present it must carry provenance frontmatter and be
routed from the canonical memory file; if the advisory hook is installed, its
reminder must be reachable from `settings.json`. A half-installed capability
(doc without routing, or hook without doc) is a FAIL — that is the AP-VAL-2
"validation drift" guard for this feature.

## Anti-patterns

- **Hook-as-enforcer.** Designing the hook to query the tracker or fail the turn
  on missing tickets. It runs in a shell with no MCP access; it can only remind.
  AP-VAL-1.
- **Full-paste tickets.** Copying a whole spec into the ticket body instead of a
  summary + link. The repo is canonical; pastes drift.
- **Binding in the loader.** Putting tracker identifiers in `AGENTS.md`'s router
  or in the hook instead of the instantiated `agents/issue-tracking.md`. AP-MEM-1.
- **Over-firing reminder.** A trigger vocabulary so broad the reminder prints on
  ordinary prompts. Tighten to feature-proposal shape. AP-VAL-1.
- **Soft loop language.** Wording the Track Loop as "consider checking the
  tracker" — under pressure it gets skipped. State the steps as the workflow.
  AP-SKL-2.

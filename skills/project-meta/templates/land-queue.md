---
artifact_name: land-queue
template_name: land-queue
source_reference: project-meta/references/land-queue-integration.md
intended_project_path: agents/land-queue.md
description: Seed for a target repo's agents/land-queue.md — records the base branch, test command, pinned merge-engine version, .gitattributes scope, exit-code escalation ladder, and the sequential landing rule for the land-queue capability.
owner: agent-facing
review_policy: user review before base-branch, test-command, or engine version change
last_reviewed: <YYYY-MM-DD>
---

<!--
SEED — instantiate to agents/land-queue.md. Fill every <ANGLE_BRACKET> with
the concrete binding, set last_reviewed, copy templates/land/land.sh to
scripts/land.sh (executable), commit the .gitattributes lines, and add a
Topic Routing pointer from the canonical memory file (AGENTS.md / CLAUDE.md).
Keep base/test-command/engine bindings HERE, not in the loader. Procedure:
project-meta/references/land-queue-integration.md. Delete this comment on
instantiation.
-->

---
artifact_name: land-queue
instantiated_from: project-meta/templates/land-queue.md
source_reference: project-meta/references/land-queue-integration.md
project_scope: <this repo only | describe scope>
owner: agent-facing
review_policy: user review before base-branch, test-command, or engine version change
last_reviewed: <YYYY-MM-DD>
---

# Land-Queue Agent Binding

Branch integration in this repo goes through the deterministic landing
pipeline `scripts/land.sh` — **never resolve a merge in conversation context
before the pipeline has run**. Model context is spent only on what the
pipeline reports as residue. Protocol:
`project-meta/references/land-queue-integration.md`.

## Bindings

| Field | Value |
|---|---|
| Base branch | `<trunk — e.g. main>` |
| Test command (`land.testcmd`) | `<e.g. npm test>` |
| Merge engine | Mergiraf `<X.Y.Z — output of: mergiraf --version>` (or `absent — degraded to rerere only`) |
| `.gitattributes` scope | `<extensions with merge=mergiraf — e.g. *.ts *.tsx *.js *.py *.json *.yaml>` |
| Per-clone setup | `scripts/land.sh setup` (idempotent; run once per clone, like `core.hooksPath`) |

## Landing Workflow

```bash
scripts/land.sh status            # config health + branches awaiting landing
scripts/land.sh land <branch>     # rebase → auto-resolve → test → ff base
scripts/land.sh queue <b1> <b2>…  # sequential landing, stop at first failure
```

Exit codes route the escalation ladder:

| Exit | Meaning | Agent action |
|---|---|---|
| 0 | landed | none — branch cleanup per worktree hygiene |
| 2 | residual conflicts (rerere + Mergiraf exhausted) | bounded conflict session: re-run the rebase, read **both sides' intent**, resolve, re-run `land.sh land` (rerere records it — same conflict never costs twice). Incompatible architectural decisions → stop, surface to operator |
| 3 | tests failed on the rebased branch | investigate on the branch; base is untouched |
| 4 | config missing | run `scripts/land.sh setup` |
| 5 | base moved mid-land, or the base branch's worktree is dirty | clean the flagged worktree if any, then re-run `land.sh land` |

## Rules

- **Sequential landing:** one branch at a time; remaining branches rebase
  onto the new base before their own attempt (`queue` mechanizes this).
- **No bulk keep-ours/keep-theirs** in a conflict session.
- **Dispatch-time conflict avoidance:** tasks intersecting on hotspot files
  (<list this repo's hotspots — registries, route tables, shared configs>)
  are serialized at dispatch, not reconciled at landing. Generated artifacts
  (lockfiles, build output) are not committed on agent branches; regenerate
  at landing.
- **Push is a mirror, not integration:** push the updated base per this
  repo's existing policy; the pipeline never pushes.
- Mergeable worktree branches route into the queue per the Worktree Trim
  Contract; landing does not remove worktrees or delete branches.

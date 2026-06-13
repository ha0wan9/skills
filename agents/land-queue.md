---
artifact_name: land-queue
instantiated_from: project-meta/templates/land-queue.md
source_reference: project-meta/references/land-queue-integration.md
project_scope: this repo only
owner: agent-facing
review_policy: user review before base-branch or test-command changes
last_reviewed: 2026-06-13
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
| Base branch | `main` |
| Test command (`land.testcmd`) | `python3 scripts/validate_project_meta.py` |
| Merge engine | Mergiraf `0.17.0` (full, non-degraded mode — local tree-sitter parsing; no LLM calls, no network) |
| `.gitattributes` scope | `*.py *.json *.yml *.yaml *.md *.js *.html` |
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
  (AGENTS.md, agents/project-artifacts.md, .claude/settings.json, scripts/validate_project_meta.py)
  are serialized at dispatch, not reconciled at landing. Generated artifacts
  (lockfiles, build output) are not committed on agent branches; regenerate
  at landing.
- **Push is a mirror, not integration:** push the updated base per this
  repo's existing policy; the pipeline never pushes.
- Mergeable worktree branches route into the queue per the Worktree Trim
  Contract; landing does not remove worktrees or delete branches.

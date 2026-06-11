---
artifact_name: code-graph
template_name: code-graph
source_reference: project-meta/references/code-graph-integration.md
intended_project_path: agents/code-graph.md
description: Seed for a target repo's agents/code-graph.md — records the pinned graphify engine version, build command, indexed scope, staleness rule, and fallback behaviour for the code-graph capability.
owner: agent-facing
review_policy: user review before engine version change or indexed scope change
last_reviewed: <YYYY-MM-DD>
---

<!--
SEED — instantiate to agents/code-graph.md. Fill every <ANGLE_BRACKET> with
the concrete binding, set last_reviewed, and add a Topic Routing pointer from
the canonical memory file (AGENTS.md / CLAUDE.md). Keep engine version and
build command HERE, not in the loader. Procedure: see
project-meta/references/code-graph-integration.md. Delete this comment on
instantiation.
-->

---
artifact_name: code-graph
instantiated_from: project-meta/templates/code-graph.md
source_reference: project-meta/references/code-graph-integration.md
project_scope: <this repo only | describe scope>
owner: agent-facing
review_policy: user review before engine version change or indexed scope change
last_reviewed: <YYYY-MM-DD>
---

# Code-Graph Agent Binding

Code navigation for this repo is backed by the **graphify** engine
(`graphifyy`). Read `graphify-out/GRAPH_REPORT.md` and issue `graphify query`
calls when the graph is fresh; fall back to the Explorer fan-out
`context-mapping` path when it is stale or absent. Procedure:
`project-meta/references/code-graph-integration.md`.

## Engine & Pinned Version

| Field | Value |
|---|---|
| Pip package | `graphifyy` (double-y — not the unaffiliated `graphify`) |
| Installed version | `<X.Y.Z — output of: pip show graphifyy \| grep Version>` |
| Pin constraint | `pip install 'graphifyy>=0.8,<0.9'` |
| Install date | <YYYY-MM-DD> |

**NEVER run `graphify install`** (the engine's self-installer). It writes to
global `~/.claude/CLAUDE.md` and `settings.json` without graceful merge — all
wiring is owned by this artifact and the canonical memory pointer. This
prohibition is unconditional and does not change with engine version.

## Build Command & Indexed Scope

```bash
# Initial build
graphify <PATH — e.g. src/ or . (excluding docs/)>

# Incremental rebuild (run when graph is stale)
graphify --update
```

Indexed scope: `<describe — e.g. "src/ only; docs/ excluded">`.

Outputs: `graphify-out/graph.json`, `graphify-out/GRAPH_REPORT.md`,
`graphify-out/graph.html`, `graphify-out/cache/`. The `graphify-out/`
directory is git-ignored (derived, rebuildable).

## Staleness Rule

Per `project-meta/references/code-graph-integration.md` §Staleness & Fallback,
the graph is **stale** if either condition holds:

1. `graphify-out/graph.json` mtime < `git log -1 --format=%ct` (a commit
   occurred since the last build).
2. The installed `graphifyy` version ≠ the version recorded above (any version
   change, including a patch bump, invalidates the cache).

Stale → run `graphify --update` before relying on the graph.

## Fallback

When the graph is stale and a rebuild is not possible, or when `graphifyy` is
absent: fall back to the Explorer fan-out `context-mapping` path defined in
`project-meta/references/execution-policy.md` "Read-Pattern Derivation".
The fallback is always available; this capability is optional and degradable.

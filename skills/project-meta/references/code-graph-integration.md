# Code-Graph Integration

Use this reference when wiring a target repo's harness to an external
code-knowledge-graph engine for token-efficient code navigation, or when
installing / auditing the `code-graph` opt-in capability.

This is the **protocol**. The copyable seed is
[`templates/code-graph.md`](../templates/code-graph.md). One source of truth
per fact: this reference owns the protocol; the template only points here.

## Contents

- [Engine](#engine)
- [Install Contract](#install-contract)
- [Build Contract](#build-contract)
- [Read-Pattern Satisfaction](#read-pattern-satisfaction)
- [Staleness & Fallback](#staleness--fallback)
- [Engine Trust Boundary](#engine-trust-boundary)
- [Target-Repo Install](#target-repo-install)
- [Uninstall](#uninstall)

## Engine

This capability is engine-generic: any code-knowledge-graph backend that
satisfies the install and build contracts below may serve as the backing
engine. The **documented reference engine** is **graphify** — pip package
`graphifyy` (double-y). The single-y PyPI name `graphify` is an unaffiliated
package; installing the wrong name is a silent typosquat vector — always
verify the package name before installing.

Reference engine details at the time of documentation (2026-06-11, v0.8.x):

| Field | Value |
|---|---|
| Pip package | `graphifyy` (double-y) |
| Pin guidance | `pip install 'graphifyy>=0.8,<0.9'` |
| License | MIT |
| Repository | github.com/safishamsi/graphify |
| Stability | pre-1.0 (v0.8.x) |
| Maintainer | solo-maintainer |

Alternative engines that could back the same contract in a future iteration:
code-review-graph (pure tree-sitter + MCP, zero LLM calls); LSP/MCP symbol
servers such as Serena. Introducing an alternative engine requires a fresh
capability increment — do not silently swap the backing engine without
updating `agents/code-graph.md`.

**Usefulness threshold.** Enable this capability only for code-dominant repos
with ≳ 100 files, or repos where `context-mapping` read-pattern escalations
recur frequently. Do NOT enable for small repos or markdown-dominant repos
(this skill repo itself is below the threshold).

## Install Contract

**MUST NOT run `graphify install`** (the engine's self-installer). As of
v0.8.x, `graphify install` appends a directive block to the global
`~/.claude/CLAUDE.md` and injects a `PreToolUse` hook into `settings.json`
without graceful merge — these are global, un-merged writes outside harness
control. This prohibition stays in force on any engine version change (see
[Engine Trust Boundary](#engine-trust-boundary) for re-verification
requirements).

Instead, install only the pip package:

```bash
pip install 'graphifyy>=0.8,<0.9'
```

All agent-facing wiring is project-meta-owned: the instantiated
`agents/code-graph.md` (seeded from `templates/code-graph.md`) plus a
routing pointer in the canonical memory file (`AGENTS.md` / `CLAUDE.md`).
**No hook is part of this capability's contract.** A future advisory hook,
if ever wanted, is a separate capability increment with its own plan.

## Build Contract

**Default build — code-only tree-sitter pass (no API tokens consumed):**

```bash
graphify <path>          # initial build
graphify --update        # incremental rebuild
```

This pass performs local AST extraction over code files only. It requires no
API key and makes no LLM calls per v0.8.x docs.

**LLM doc-extraction pass (opt-in, costs API tokens):** graphify supports an
optional pass over documents, PDFs, and images that calls an LLM via the
user-configured key (`ANTHROPIC_API_KEY` or equivalent). This pass is
**opt-in**; enable it only when the caller explicitly requests it and
understands that it consumes API tokens billed to the configured key.

**Build outputs** land in `graphify-out/` at the repo root:

| File | Description |
|---|---|
| `graph.json` | machine-readable graph (staleness anchor) |
| `GRAPH_REPORT.md` | ~1–5K-token human/agent summary |
| `graph.html` | visual browser |
| `cache/` | incremental build cache |

`graphify-out/` is git-ignored in the target repo (derived, rebuildable).
The committed contract artifact is `agents/code-graph.md`, which records the
pinned engine version at install time.

## Read-Pattern Satisfaction

When `agents/code-graph.md` is present in the target repo AND the graph is
fresh (see [Staleness & Fallback](#staleness--fallback)), a read of
`graphify-out/GRAPH_REPORT.md` followed by targeted `graphify query` calls
**satisfies the `context-mapping` read-pattern escalation** defined in
`references/execution-policy.md` "Read-Pattern Derivation" — replacing the
Explorer fan-out for the compressed-global-map step.

Concretely: when `semantic_scope >= cross_subsystem` or design-intent signals
trigger `context-mapping`, the agent reads `GRAPH_REPORT.md` as the
compressed global map and issues `graphify query` calls for targeted symbol
lookup, rather than fanning out Explorer reads across the code tree. This
context-mapping path is faster and cheaper than the fan-out equivalent for
large, code-dominant repos.

The capability does not change the escalation conditions that trigger
`context-mapping` — only the mechanism used to satisfy it.

## Staleness & Fallback

**Mechanical staleness rule** — the graph is stale if EITHER condition holds:

1. `graphify-out/graph.json` mtime < `git log -1 --format=%ct` (the last
   commit timestamp). Any commit since the last build invalidates the graph.
2. The engine version recorded in `agents/code-graph.md` ≠ the installed
   `graphifyy` version. Any version change — even a patch bump — invalidates
   the cache; do not rely on a stale graph from a different engine version.

**Stale graph → rebuild before use:**

```bash
graphify --update
```

Then re-check staleness before relying on the graph.

**Fallback when rebuild is not possible** (engine missing, build fails, or
operator chooses not to rebuild): fall back to the Explorer fan-out
`context-mapping` path defined in `references/execution-policy.md`
"Read-Pattern Derivation". The fallback is always available — the `code-graph`
capability is optional and degradable by design. Never block on a stale or
absent graph; always fall back gracefully.

## Engine Trust Boundary

The safety-relevant claims documented in this reference — specifically:

- **(a)** `graphify install` (the engine's self-installer) appends to global
  `~/.claude/CLAUDE.md` and injects a `PreToolUse` hook into `settings.json`
  without graceful merge.
- **(b)** The default tree-sitter build pass makes no LLM calls and consumes
  no API tokens.

— were taken from the engine's README, docs, and third-party reviews at
**v0.8.x on 2026-06-11**, not from a source code audit.

**On any engine version change, re-verify both claims (a) and (b) before
relying on them.** The prohibition on running `graphify install` stays in
force regardless of re-verification outcome — the safety margin is the
harness-owned wiring, not trust in any specific installer version.

Pre-1.0 stability + solo-maintainer maintenance posture: this capability
stays **optional and degradable forever**. Do not promote it to a hard
dependency in any target repo's harness.

## Target-Repo Install

Install via `/project-meta init --code-graph` or
`/project-meta settings enable code-graph`. The install step MUST complete
all of the following atomically — a partial install is a validator FAIL:

1. **Instantiate the template:** copy `templates/code-graph.md` →
   `agents/code-graph.md` with full provenance frontmatter. Record the
   installed `graphifyy` version (output of `pip show graphifyy | grep Version`)
   and the repo's build command and indexed scope in the body.
2. **Add routing pointer:** add a Topic Routing pointer to `agents/code-graph.md`
   from the canonical memory file (`AGENTS.md` or `CLAUDE.md`). Half-install
   (doc present but not routed) is a validator FAIL.
3. **Gitignore:** add `graphify-out/` to the target repo's `.gitignore`
   (derived output, never committed).
4. **Manifest row:** register a row in `agents/project-artifacts.md` for
   `agents/code-graph.md`.

Run `pip install 'graphifyy>=0.8,<0.9'` (or the pinned version the repo
records) and the initial `graphify <path>` build after the artifact wiring is
complete.

## Uninstall

Remove via `/project-meta settings disable code-graph`. The uninstall step
MUST mirror the install atomically — a partial uninstall is a validator FAIL:

1. Remove `agents/code-graph.md`.
2. Remove its routing pointer from the canonical memory file.
3. Remove its manifest row from `agents/project-artifacts.md`.
4. *(Optional)* Delete `graphify-out/` and the `graphify-out/` line from
   `.gitignore`.

Never touch user application code. The pip package (`graphifyy`) is not
uninstalled by this step — manage it separately if desired.

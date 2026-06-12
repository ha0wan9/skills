# Land-Queue Integration

Use this reference when wiring a target repo's harness to the **land-queue**
opt-in capability — a deterministic merge/landing pipeline for parallel agent
branches — or when installing / auditing it.

This is the **protocol**. The copyable seed is
[`templates/land-queue.md`](../templates/land-queue.md); the pipeline script
seed is [`templates/land/land.sh`](../templates/land/land.sh). One source of
truth per fact: this reference owns the protocol; the template only points here.

## Contents

- [Problem & Token Policy](#problem--token-policy)
- [Escalation Ladder](#escalation-ladder)
- [Engine](#engine)
- [Install Contract](#install-contract)
- [Landing Contract](#landing-contract)
- [Sequential Landing Rule](#sequential-landing-rule)
- [Worktree Interplay](#worktree-interplay)
- [Engine Trust Boundary](#engine-trust-boundary)
- [Target-Repo Install](#target-repo-install)
- [Uninstall](#uninstall)

## Problem & Token Policy

Parallel agent branches pay a **merge tax**: line-based `git merge` reports
conflicts for changes that are textually adjacent but syntactically
independent (two branches each appending to a registry, an import block, a
route table). Resolving those in an agent's conversation context is the most
expensive possible venue — full-context model turns spent on work a
deterministic tool resolves for free, and the tax compounds as each landed
branch invalidates the next branch's base.

**Token policy (the capability's core invariant): no model runs inside the
landing pipeline.** `scripts/land.sh` is deterministic end-to-end; model
context is spent only when the pipeline *stops* and reports a residue
(exit codes below). Integration becomes a command, not a conversation.

## Escalation Ladder

Conflicts route through three layers, cheapest first. Each layer only sees
what the previous one could not resolve:

1. **`git rerere`** (git built-in, repo-local config) — replays previously
   recorded conflict resolutions. With `rerere.autoupdate` on, replayed
   resolutions are staged automatically. Zero cost, zero new tooling.
2. **Mergiraf** (syntax-aware merge driver, see [Engine](#engine)) — resolves
   textual conflicts that are independent in the syntax tree. Registered as a
   git merge driver, so it applies to `merge`, `rebase`, `cherry-pick`, and
   `revert` transparently. Zero tokens, deterministic.
3. **Bounded agent conflict session** — only for residue surviving layers
   1–2 (`land.sh` exit `2`). The agent re-runs the rebase, reads **both
   sides' intent** before resolving (never keep-ours/keep-theirs in bulk),
   resolves, re-runs `land.sh`. `rerere` records the resolution, so the same
   conflict never costs tokens twice. If both sides made incompatible
   architectural decisions, stop and surface to the operator instead of
   synthesizing a compromise neither branch intended.

## Engine

This capability is engine-generic in layer 2: any syntax-aware merge driver
honoring git's merge-driver contract may back it. The **documented reference
engine** is **Mergiraf**.

Reference engine details at the time of documentation (2026-06-12, v0.17.0):

| Field | Value |
|---|---|
| Install | `brew install mergiraf` (macOS) / `cargo install mergiraf` / prebuilt binaries |
| License | GPL-3.0-or-later |
| Repository | codeberg.org/mergiraf/mergiraf (docs: mergiraf.org) |
| Stability | pre-1.0 (v0.17.x) |
| Git requirement | best results with git ≥ 2.44 |
| Runtime behavior | local tree-sitter parsing only; no LLM calls, no network |

**Degradable by design.** When `mergiraf` is absent from `PATH`, the pipeline
runs with layers 1 and 3 only — `land.sh setup` and `land.sh status` report
the degradation; nothing blocks. Never promote the engine to a hard
dependency. A per-invocation escape hatch exists upstream: prefix
`mergiraf=0` to any git command to fall back to git's stock merge heuristics.

## Install Contract

**No global writes.** All git configuration is **repo-local** (`git config`
without `--global`): the mergiraf merge-driver registration and the `rerere`
switches live in `.git/config` of the clone, written idempotently by
`scripts/land.sh setup`. Do not write `~/.config/git/config`, global
attributes, or any file outside the target repo — global registration is the
operator's personal choice, not the harness's.

Per-clone setup (the same pattern as a tracked `core.hooksPath`) — run once
per clone:

```bash
scripts/land.sh setup --base <trunk> --test-cmd '<verification command>'
```

which performs, idempotently:

1. `git config rerere.enabled true` and `git config rerere.autoupdate true`.
2. When `mergiraf` is on `PATH`:
   `git config merge.mergiraf.name mergiraf` and
   `git config merge.mergiraf.driver 'mergiraf merge --git %O %A %B -s %S -x %X -y %Y -p %P -l %L'`.
3. Records `land.base` and `land.testcmd` in repo-local git config.

The **committed** artifacts are: the `merge=mergiraf` lines in the repo's
`.gitattributes` (generate the supported set with
`mergiraf languages --gitattributes`; commit only the extensions the repo
actually uses), `scripts/land.sh` itself, and the instantiated
`agents/land-queue.md` binding doc.

## Landing Contract

`scripts/land.sh` exposes four verbs; all are deterministic:

| Verb | Effect |
|---|---|
| `setup` | per-clone config above; idempotent |
| `status` | report config health (rerere on? driver registered? attributes present? base/testcmd set?), in-progress rebase, branches not yet merged into base |
| `land <branch>` | the pipeline: preflight → rebase onto base (layers 1–2 active) → run the test command → fast-forward base |
| `queue <branch>...` | sequential landing: `land` each branch in order; stop at first failure and report landed / blocked / remaining |

Pipeline steps for `land <branch>`:

1. **Preflight** — clean working tree, branch and base exist, `land.testcmd`
   configured (unset is a hard stop, not a silent skip: the test gate is the
   point).
2. **Rebase** `<branch>` onto base. rerere and the merge driver auto-resolve
   what they can. Residual conflict → print the conflicted-file list
   (token-light, names only), abort the rebase, restore the original
   checkout, **exit 2** — the layer-3 escalation signal. Nothing is lost by
   the abort: layer-1/2 resolutions are replayed for free on the next attempt.
3. **Verify** — run `land.testcmd`. Failure → stay on the rebased branch for
   investigation, **exit 3**. The base ref is untouched.
4. **Fast-forward base** to the branch (handles the base being checked out in
   the current worktree, a sibling worktree — refused if that worktree is
   dirty — or no worktree). Non-fast-forwardable base → **exit 5** (someone
   moved base mid-land; re-run).

Exit codes: `0` landed · `1` usage/preflight · `2` residual conflicts
(agent session) · `3` tests failed · `4` config missing (or empty) · `5` base
not fast-forwardable (base moved mid-land, or the base branch's worktree is
dirty — clean it, then re-run).

Pushing the updated base to a remote is **not** part of the pipeline. With
this capability, the remote is a mirror/backup of the locally integrated
trunk, not the integration mechanism; push policy (and any pre-push CI hook)
stays whatever the repo already does.

## Sequential Landing Rule

**One branch lands at a time; every remaining branch rebases onto the new
base before its own landing attempt.** `land.sh queue` mechanizes this. Never
land two parallel branches against the same stale base — each merge must see
the full context of what already landed, or conflict resolutions cascade and
invalidate each other.

Corollary for dispatch planning (the cheaper end of the same lever): tasks
whose write scopes intersect on hotspot files (registries, route tables,
shared configs, lockfiles) should be serialized at dispatch time, not
reconciled at landing time. Generated artifacts (lockfiles, `dist/`) should
not be committed on agent branches at all — regenerate at landing.

## Worktree Interplay

This capability composes with the Worktree Trim Contract
([`worktree-hygiene.md`](worktree-hygiene.md)): worktree branches classified
**mergeable** route into the land queue (`land.sh queue <branches…>`) instead
of ad-hoc merges. After a successful landing, branch deletion and worktree
removal remain the trim contract's job, not `land.sh`'s.

## Engine Trust Boundary

The safety-relevant claims documented here — specifically **(a)** Mergiraf's
merge pass is local tree-sitter parsing with no LLM calls and no network
access, and **(b)** registration via `merge.mergiraf.driver` affects merge
operations only when `.gitattributes` opts a path in — were taken from the
engine's documentation (mergiraf.org) at **v0.17.0 on 2026-06-12**, not from
a source code audit.

**On any engine version change, re-verify both claims before relying on
them**, and re-pin the version recorded in `agents/land-queue.md`. Pre-1.0
stability: this capability stays **optional and degradable forever**; layer 2
silently absent must never block a landing.

## Target-Repo Install

Install via `/project-meta init --land-queue` or
`/project-meta settings enable land-queue`. The install MUST complete all of
the following atomically — a partial install is a validator FAIL:

1. **Copy the pipeline script:** `templates/land/land.sh` →
   `<target>/scripts/land.sh`, executable bit set.
2. **Instantiate the template:** `templates/land-queue.md` →
   `agents/land-queue.md` with full provenance frontmatter. Record the base
   branch, the test command, the pinned engine version (`mergiraf --version`
   output, or "absent — degraded" when not installed), and the
   `.gitattributes` scope in the body.
3. **Commit `.gitattributes` lines** for the languages the repo actually uses
   (`mergiraf languages --gitattributes` for the menu).
4. **Add routing pointer:** a Topic Routing pointer to `agents/land-queue.md`
   from the canonical memory file (`AGENTS.md` / `CLAUDE.md`). Half-install
   (doc present but not routed) is a validator FAIL.
5. **Manifest row:** register `agents/land-queue.md` in
   `agents/project-artifacts.md`.
6. **Run per-clone setup:** `scripts/land.sh setup --base <trunk>
   --test-cmd '<cmd>'` (asks the operator for the test command if the repo
   has no obvious verification gate — that binding is a synchronous user
   gate, confirm before writing).

## Uninstall

Remove via `/project-meta settings disable land-queue`. Mirror the install
atomically — a partial uninstall is a validator FAIL:

1. Remove `scripts/land.sh` and `agents/land-queue.md`.
2. Remove the routing pointer from the canonical memory file and the manifest
   row from `agents/project-artifacts.md`.
3. *(Optional)* Remove the `merge=mergiraf` lines from `.gitattributes` and
   unset the repo-local `merge.mergiraf.*`, `rerere.*`, and `land.*` git
   config keys.

Never touch user application code. The `mergiraf` binary is not uninstalled
by this step — it is operator-owned tooling.

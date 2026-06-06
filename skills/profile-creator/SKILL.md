---
name: profile-creator
description: "DEPRECATED — folded into the global-meta skill. Creating a Claude Code (or Codex) config profile is now global-meta's `create` verb. This stub remains for one release so existing /profile-creator triggers keep working; it routes to global-meta. Triggers: add/create/spin up a new multi-claude profile, claude-X profile, isolated config dir."
metadata: {version: 1.3.0, compat: [claude-code], published: [claude-marketplace], deprecated: true, superseded_by: global-meta}
---

# profile-creator — DEPRECATED (use `global-meta`)

> **This skill has been absorbed into [`global-meta`](../global-meta/SKILL.md).**
> Profile creation is now `global-meta create`, generalized to both Claude Code
> and Codex. This stub stays for one deprecation release so existing
> `/profile-creator` muscle-memory keeps working, then it is removed from the
> marketplace.

## Trigger Decision

All profile-creation requests now belong to **`global-meta`**. Whether the user
says "add a multi-claude profile", "create a claude-X profile", "spin up a new
claude config", or asks for a Codex profile — **route immediately to `global-meta`
and run its `create` verb.** This stub performs no profile creation itself.

## Skill Arbitration

| Request shape | Owner | This stub's role |
|---|---|---|
| Create/manage any Claude or Codex config profile | **`global-meta`** (supersedes this skill) | redirect only — deprecated, performs no work |
| Repo-level memory / harness (`CLAUDE.md`, `AGENTS.md`, repo config) | **`project-meta`** | defer — out of scope for this deprecated stub |

## What to do instead

Route the request to **`global-meta`** and run its `create` verb:

```bash
# Claude profile (was: profile-creator <name>)
python3 skills/global-meta/scripts/create_profile.py [--isolated] [--seed-from <profile>] <name>

# Codex profile (new capability)
python3 skills/global-meta/scripts/create_profile.py --runtime codex <name>
```

Everything the old skill did — `~/.claude-<name>/`, the `plugins` symlink to the
shared store, the `~/.local/bin/claude-<name>` launcher (simple/isolated),
`--seed-from`, and the `ccplug`-only plugin-admin guard — lives in `global-meta`
unchanged for the claude runtime. See [`global-meta/SKILL.md`](../global-meta/SKILL.md)
and [`global-meta/references/create-profile.md`](../global-meta/references/create-profile.md).

## Why deprecated

`global-meta` is a strict superset: same profile creation, plus dual-runtime
(Codex) support and the audit/drift/reconcile/track lifecycle for the whole
config root (see [`proposals/global-meta.md`](../project-meta/proposals/global-meta.md)).
Maintaining two skills for one capability would drift — one source of truth.

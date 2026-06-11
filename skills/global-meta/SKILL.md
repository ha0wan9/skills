---
name: global-meta
description: Bootstrap, audit, and evolve a user's GLOBAL Claude Code / Codex config root (~/.claude, ~/.codex, and ~/.claude-<name>/~/.codex-<name> profiles). Replaces the retired profile-creator plugin — all its triggers (add/create/spin up a multi-claude profile, claude-X profile, isolated config dir) route here. LIVE — create a config profile for either runtime (config dir, plugins symlink, launcher in ~/.local/bin, optional memory seed); status — read-only inventory of profiles, plugins, hooks, launchers, and context-tax; audit — four-way consistency findings (stale-enablement, wrong-scope, dup-scope-records, cache-version-mismatch) with capture lines; audit --emit-fix — write a reviewable bash remediation script (dry-run by default, --apply to execute, snapshot before first mutation); snapshot/restore — ledger of the three config stores. ROADMAP (proposed, see proposals/global-meta.md) — drift/reconcile/settings/track for cross-profile drift and secret-safe dotfiles git. Use when the user asks to create/add/spin up a Claude or Codex profile, or to inventory/audit/reconcile their global config across profiles.
metadata: {version: 1.2.0, compat: [claude-code, codex], published: [claude-marketplace]}
---

# global-meta

> **Runtimes:** Claude Code · Codex &nbsp;|&nbsp; **Published:** Claude Marketplace
> _User/global scope — owns `~/.claude*` and `~/.codex*`. The repo-scope counterpart is `project-meta`, whose engine this skill reuses._

User/global-scope counterpart to `project-meta`: it manages the user's **config
root** — `~/.claude`, `~/.codex`, and every `~/.claude-<name>` / `~/.codex-<name>`
profile. It **absorbed and replaced `profile-creator`** (retired from the
marketplace; the claude leg is unchanged, now dual-runtime). The broader
audit/evolve lifecycle is designed in [`proposals/global-meta.md`](../project-meta/proposals/global-meta.md);
this version ships the `create` verb.

## Trigger Decision

- **Create a profile** (LIVE): user asks to create / add / spin up a new Claude
  *or* Codex profile, config dir, or launcher (`claude-<name>` / `codex-<name>`),
  or to clone/seed one from an existing profile.
- **Inventory / status** (LIVE): user asks to list or inspect profiles, plugins,
  hooks, launchers, or context-tax across their global config root. →
  `config_root_audit.py status`
- **Audit / consistency check** (LIVE): user asks to audit, find inconsistencies,
  check plugin hygiene, or identify stale/wrong-scope/duplicate/mismatched-cache
  entries. → `config_root_audit.py audit`
- **Emit remediation script** (LIVE): user wants a reviewable script to fix audit
  findings without running blind; combine with `audit --emit-fix <path>` then
  review the script before running `--apply`. →
  `config_root_audit.py audit --emit-fix <path>`
- **Snapshot / restore** (LIVE): user asks to snapshot the three config stores or
  restore from a snapshot. → `config_root_audit.py snapshot|restore`
- **Config-root corruption / incident root-cause** (ARBITRATE): `audit` reports
  findings and produces a case file; hand off to `meta-debug` for root-causing.
  See Skill Arbitration table below.
- **Drift / reconcile / settings / dotfiles git** (ROADMAP): user asks to diff or
  reconcile cross-profile settings, or put `~/.claude` under version control. →
  route to the proposal; do not improvise these lifecycle verbs.

## Bootstrap Order

1. Read this file (always).
2. For `create` mechanics / manual recovery: load [`references/create-profile.md`](references/create-profile.md).
3. To scaffold: invoke [`scripts/create_profile.py`](scripts/create_profile.py) (see Quick Workflow).
4. For `status` / `audit` / `snapshot` / `restore`: invoke [`scripts/config_root_audit.py`](scripts/config_root_audit.py) (see Quick Workflow).
5. Launcher bodies: `templates/launcher-{simple,isolated}.sh` — load only if generating by hand.
6. For any harness reuse (memory, provenance, mirrors, validators): resolve
   `project-meta` at runtime and delegate — see Core Rules.

## Core Rules

**MUST** validate the profile name against `^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$`
before creating anything. Exit with remediation if invalid.

**MUST NOT** create a profile if `~/.<runtime>-<name>/` already exists. Exit with
a remediation message naming the path.

**MUST NOT** run `claude plugin marketplace add/update` (or the Codex equivalent)
from a non-shared profile — it rewrites `known_marketplaces.json` paths and breaks
every other profile ("corrupted installLocation"). Plugin admin goes through
`ccplug` (Claude) only. This is the `multiclaude-marketplace-guard` invariant;
global-meta is its enforcement home.

**MUST own policy, delegate mechanism (AP-COORD-7).** global-meta never
re-implements orchestration the runtime engine provides, and **cannot enable** the
engine (user-gated). Reference it generically ("scripted-engine tier").

**MUST treat durable memory as a multi-writer set (AP-COORD-7).** CC auto-memory
(`~/.claude/projects/*/memory/`), methodology plan docs, and user `CLAUDE.md` are
co-writers; global-meta audits/promotes across lanes, never claims sole authorship.

**MUST delegate harness logic to `project-meta`, never vendor.** Resolve it
(`$PROJECT_META_DIR` → `~/.claude/skills/project-meta` → `~/.claude/plugins/*/*/*/skills/project-meta`)
and call its scripts; carry a thin floor if absent. See
`project-meta/references/shared-cli-delegation.md`.

Default: claude runtime; **simple** launcher form (inherits env) unless the user
asks for `--isolated`. The claude leg reproduces former `profile-creator` behavior.

## Skill Arbitration

| Request shape | Owner | global-meta's role |
|---|---|---|
| Create / manage a user config profile (Claude or Codex) | **`global-meta`** | acts |
| Create a Claude profile (legacy `/profile-creator`) | **`global-meta create`** | absorbed; the `profile-creator` plugin is retired — this skill owns the trigger |
| Inventory / audit / snapshot the config root | **`global-meta status/audit/snapshot`** | acts — runs `config_root_audit.py` |
| Config-root corruption or incident root-cause | `meta-debug` | global-meta `audit` reports findings + emits a case file; hand the case file to `meta-debug` for root-causing |
| Repo harness (`.claude/` in a repo, `AGENTS.md`, repo memory) | `project-meta` | defer; reuse its engine |
| Edit a single `settings.json` value/hook in isolation | `update-config` | delegate the leaf edit |
| Multi-agent orchestration *execution* (subagents, workflows, effort) | the runtime engine ("scripted-engine tier") — not a skill | own policy, delegate mechanism; never re-implement — AP-COORD-7 |

If arbitration is unclear, ask before acting. Never silently invoke two skills.

## Gotchas

- **`~/.local/bin` not on PATH** — launcher exists but `claude-<name>`/`codex-<name>`
  not found. Add `export PATH="$HOME/.local/bin:$PATH"` to the shell rc.
- **Codex plugins symlink is best-effort** — the Codex shared-plugin model is
  unverified (proposal §10); the symlink is created only if `~/.codex-shared/plugins`
  exists, else skipped with a note. Do not invent a Codex shared store.
- **`--seed-from` is same-runtime** — claude seeds `CLAUDE.md`/`RTK.md`; codex seeds
  `AGENTS.md`/`RTK.md`. Missing seed files are a `[skip]`, not an error.
- **Isolated vs simple mix-up** — simple inherits the parent shell's keys; isolated
  unsets them. A work profile accidentally made simple can leak secrets across contexts.

## Quick Workflow

1. **Ask for name + runtime** if not given — short, lowercase, no `claude-`/`codex-` prefix.
2. **Choose launcher form** — simple (default) or `--isolated`.
3. **Run (dry-run first if unsure):**
   ```bash
   python3 skills/global-meta/scripts/create_profile.py --dry-run [--runtime claude|codex] <name>
   python3 skills/global-meta/scripts/create_profile.py [--runtime claude|codex] [--isolated] [--seed-from <profile>] <name>
   ```
4. **Confirm output** — the script prints every action; verify `ls -la ~/.<rt>-<name>/`.
5. **Remind the user**: open a fresh terminal and run `claude-<name>` / `codex-<name>`.
6. **Never** run plugin marketplace add/update from the new profile — use `ccplug`.
7. **Lifecycle request?** Route to the proposal; do not improvise audit/drift/reconcile.
8. **Fix audit findings** — emit a reviewable script first, then apply:
   ```bash
   python3 skills/global-meta/scripts/config_root_audit.py audit \
     --config-home $HOME --home-dir $HOME --spec-marketplace <mkt> \
     --emit-fix /tmp/fix.sh
   /bin/bash /tmp/fix.sh          # dry-run: review plan
   /bin/bash /tmp/fix.sh --apply  # apply (operator-run only; snapshots first)
   ```

## When To Load References

| Task class | Load |
|---|---|
| `create` mechanics / manual recovery / simple-vs-isolated | [`references/create-profile.md`](references/create-profile.md) |
| Generating a launcher by hand | `templates/launcher-{simple,isolated}.sh` |
| Script usage | `scripts/create_profile.py --help` |
| The audit/drift/reconcile/track lifecycle design | [`proposals/global-meta.md`](../project-meta/proposals/global-meta.md) |
| Reusing project-meta harness logic | `project-meta/references/shared-cli-delegation.md` |

## Examples

- [`examples/sample-profile/`](examples/sample-profile/README.md) — dual-runtime `create` reference run.
- [`examples/audit-fixture/`](examples/audit-fixture/README.md) + [`examples/audit-fixture-clean/`](examples/audit-fixture-clean/README.md) — seeded/clean config-root fixtures for the roadmap `audit` verb (acceptance data for DASH-039/034; see `docs/plans/global-meta-lifecycle-build-plan.md`).

## Output Footer

```
global-meta/<verb> done — runtime: <claude|codex>, profile: <rt>-<name>, launcher: <simple|isolated>, seeded: <yes|no>
```

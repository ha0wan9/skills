---
name: profile-creator
description: Create a new Claude Code config profile in the user's multi-claude setup — a new ~/.claude-<name>/ dir with its own CLAUDE_CONFIG_DIR, a launcher script in ~/.local/bin, and a symlinked plugins/ dir so plugins stay shared across all profiles. Trigger when the user asks to "add a new multi-claude profile", "create a claude-X profile", "spin up a new claude config", or wants an isolated config directory for a different account/context.
metadata: {version: 1.2.0, compat: [claude-code], published: [claude-marketplace]}
---

# profile-creator

> **Runtimes:** Claude Code only &nbsp;|&nbsp; **Published:** Claude Marketplace
> _Claude-Code-specific by design — manages `~/.claude-<name>` config dirs, `CLAUDE_CONFIG_DIR`, and `ccplug`._

This user runs Claude Code with multiple profiles. Each profile is a separate config directory (`~/.claude-<name>/`) selected via the `CLAUDE_CONFIG_DIR` env var, with a launcher script at `~/.local/bin/claude-<name>` that sets the env and execs `claude`.

Plugins are shared: every profile's `plugins/` is a symlink to `~/.claude-shared/plugins/`. Plugin **administration is centralized** on the shared store — install/update/marketplace ops run only via `~/.local/bin/ccplug` (which sets `CLAUDE_CONFIG_DIR=$HOME/.claude-shared`). A new profile only *consumes* plugins through the symlink.

## Trigger Decision

- User asks to create, add, or spin up a new Claude Code profile, config, or context directory.
- User requests a new launcher at `~/.local/bin/claude-<name>`.
- User says "set up a new multi-claude profile" or "I need a new `claude-X` command".
- User asks to clone or seed an existing profile into a new one.

## Bootstrap Order

1. Read this file (always loaded).
2. If the request involves the manual procedure or recovery: load `references/create-profile.md`.
3. If the user asks which launcher form to use: load `references/create-profile.md` §Decision.
4. To scaffold: invoke `scripts/create_profile.py` (see Quick Workflow).
5. Templates `templates/launcher-simple.sh` and `templates/launcher-isolated.sh` are the canonical launcher bodies — load them only if generating a launcher by hand.

## Core Rules

**MUST NOT** run `claude plugin marketplace add/update` from a new profile. Reason: the CLI writes a profile-specific absolute path (e.g. `~/.claude-<name>/plugins/…`) into `known_marketplaces.json` and `installed_plugins.json`, replacing the shared `~/.claude-shared/…` paths and breaking plugin lookups in every other profile ("corrupted installLocation" failure). Plugin administration MUST go through `ccplug` only.

**MUST** validate the profile name against `^[a-z0-9][a-z0-9-]*$` before creating anything. Exit with a clear remediation message if invalid.

**MUST** verify `~/.claude-shared/plugins` exists before creating a symlink. Exit with a clear remediation message if missing — do not create the profile directory until prerequisites pass.

**MUST NOT** create a profile directory if `~/.claude-<name>/` already exists. Exit with a remediation message naming the path.

Default: use the simple launcher form (inherits env) unless the user explicitly asks for isolation.

`enable`/`disable` plugin state is stored per-profile. `claude plugin update` prints "restart required to apply" — relaunch the profile after updates.

## Skill Arbitration

| Request shape | Owning skill | This skill's role |
|---|---|---|
| Create or modify a Claude Code profile / launcher | **this skill** | primary |
| Install, update, or manage plugins | `ccplug` wrapper (not a skill) | none — redirect to `ccplug` |
| Set up repo-level memory (`CLAUDE.md`) | project-meta | none — delegate |
| Set up session-start hooks | session-start-hook | none — delegate |
| Configure `settings.json` | update-config | none — delegate |

project-meta owns repo-harness memory; session-start-hook owns hook scaffolding; this skill owns profile creation only.

## Gotchas

**`~/.local/bin` not on PATH** — the launcher exists but `claude-<name>` is not found. Remediation: add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` / `~/.zshrc` and open a fresh terminal.

**Plugin not visible after profile creation** — the plugins symlink may be missing. Check: `ls -la ~/.claude-<name>/plugins`. Re-run the symlink step from `references/create-profile.md` if absent.

**`--seed-from` silently skips files** — `CLAUDE.md` or `RTK.md` not found in the source profile is a skip, not an error; the script prints `[skip]`. Verify after seeding.

**Isolated vs simple mix-up** — simple launchers inherit the parent shell's `ANTHROPIC_API_KEY`; isolated launchers unset it. If a work profile is accidentally created as simple, secrets can leak across contexts.

**Skill symlink skipped silently** — if `~/.claude-shared/skills/profile-creator` does not exist, the script skips that step and prints `[skip]`. The profile is still functional.

## Quick Workflow

1. **Ask for name** if not provided — short, lowercase, no `claude-` prefix (e.g. `team`, `oss`, `client-acme`).
2. **Choose launcher form** — simple (default) or isolated (`--isolated`). See `references/create-profile.md` §Decision.
3. **Run the script** (dry-run first if uncertain):
   ```bash
   python3 skills/profile-creator/scripts/create_profile.py --dry-run <name>
   python3 skills/profile-creator/scripts/create_profile.py [--isolated] [--seed-from <profile>] <name>
   ```
4. **Confirm output** — script prints every action taken. Verify `ls -la ~/.claude-<name>/`.
5. **Remind the user**: open a fresh terminal and run `claude-<name>`.
6. **Never** run `claude plugin marketplace add/update` from the new profile — use `ccplug` for all plugin administration.

## When To Load References

| Task class | Load |
|---|---|
| Manual recovery / step-by-step procedure | `references/create-profile.md` |
| Choosing simple vs isolated launcher | `references/create-profile.md` §Decision |
| Generating launcher body by hand | `templates/launcher-simple.sh` or `templates/launcher-isolated.sh` |
| Script usage | `scripts/create_profile.py --help` |

## Output Footer

After every profile creation, confirm:
- Profile dir created: `~/.claude-<name>/`
- Plugins symlink: `~/.claude-<name>/plugins → ~/.claude-shared/plugins`
- Launcher installed: `~/.local/bin/claude-<name>` (form: simple or isolated)
- Seed files copied (if `--seed-from` used)
- Next step: `claude-<name>` in a fresh terminal

## Reference

- Existing profiles: `.claude` (default, no wrapper), `.claude-work`, `.claude-personal`, `.claude-exp`, `.claude-mine`
- Existing wrappers: `~/.local/bin/claude-{work,personal,exp,mine}`
- Plugin admin wrapper: `~/.local/bin/ccplug` → `CLAUDE_CONFIG_DIR=$HOME/.claude-shared claude plugin …`
- Shared plugins: `~/.claude-shared/plugins/` (one source of truth, all profiles symlink here)
- Shared skills dir: `~/.claude-shared/skills/` (not auto-loaded — manually symlinked into specific profile skills/ dirs)

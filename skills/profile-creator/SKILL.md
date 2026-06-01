---
name: profile-creator
description: Create a new Claude Code config profile in the user's multi-claude setup — a new ~/.claude-<name>/ dir with its own CLAUDE_CONFIG_DIR, a launcher script in ~/.local/bin, and a symlinked plugins/ dir so plugins stay shared across all profiles. Trigger when the user asks to "add a new multi-claude profile", "create a claude-X profile", "spin up a new claude config", or wants an isolated config directory for a different account/context.
---

# profile-creator

This user runs Claude Code with multiple profiles. Each profile is a separate config directory (`~/.claude-<name>/`) selected via the `CLAUDE_CONFIG_DIR` env var, with a launcher script at `~/.local/bin/claude-<name>` that sets the env and execs `claude`.

Plugins are shared: every profile's `plugins/` is a symlink to `~/.claude-shared/plugins/`. Plugin **administration is centralized** on the shared store — install/update/marketplace ops run only via `~/.local/bin/ccplug` (which sets `CLAUDE_CONFIG_DIR=$HOME/.claude-shared`). A new profile only *consumes* plugins through the symlink; it must never register its own marketplaces (see [Plugin administration](#plugin-administration)).

## When invoked

Ask for the profile name if not given (short, lowercase, no `claude-` prefix — e.g. `team`, `oss`, `client-acme`). Then run the steps below.

## Steps

1. **Validate**:
   - Name matches `^[a-z0-9][a-z0-9-]*$`
   - `~/.claude-<name>/` does not exist
   - `~/.local/bin/claude-<name>` does not exist

2. **Create the profile dir** with a shared-plugins symlink:
   ```bash
   NAME=<name>
   mkdir -p ~/.claude-${NAME}
   ln -s ~/.claude-shared/plugins ~/.claude-${NAME}/plugins
   ```

3. **Create the launcher** at `~/.local/bin/claude-<name>`. Use the same template as `claude-work` / `claude-personal`. If the user wants secret isolation (work-style), include the `unset` block; otherwise the simpler form. Default to simple form unless asked.

   Simple form:
   ```bash
   #!/usr/bin/env bash
   export CLAUDE_CONFIG_DIR="$HOME/.claude-<name>"
   if [ -f "$HOME/.config/claude-<name>/env" ]; then
     source "$HOME/.config/claude-<name>/env"
   fi
   exec claude "$@"
   ```

   Isolated form (work-style — unsets common API/token env vars before launch):
   ```bash
   #!/usr/bin/env bash
   export CLAUDE_CONFIG_DIR="$HOME/.claude-<name>"
   unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL
   unset GITHUB_TOKEN GOOGLE_APPLICATION_CREDENTIALS
   unset SLACK_BOT_TOKEN LINEAR_API_KEY JIRA_API_TOKEN CONFLUENCE_API_TOKEN
   if [ -f "$HOME/.config/claude-<name>/env" ]; then
     source "$HOME/.config/claude-<name>/env"
   fi
   exec claude "$@"
   ```

   Then `chmod +x ~/.local/bin/claude-<name>`.

4. **Optionally seed memory files**: if the user provides a source profile (e.g. "copy from claude-work"), copy `CLAUDE.md` and `RTK.md` from `~/.claude-<source>/` into `~/.claude-<name>/`. Otherwise skip — the profile will be empty until the user populates it.

5. **Symlink the profile-creator skill itself** so it stays accessible from the new profile:
   ```bash
   mkdir -p ~/.claude-<name>/skills
   ln -s ~/.claude-shared/skills/profile-creator ~/.claude-<name>/skills/profile-creator
   ```

6. **Verify** and report:
   - `ls -la ~/.claude-<name>/` — confirm dir exists with plugins symlink
   - `~/.local/bin/claude-<name> --version` — confirm launcher works (or just check executable)
   - Tell the user: launch with `claude-<name>` in a fresh terminal.

## Plugin administration

Plugins are managed from one base so the CLI's **literal** `installLocation` /
`installPath` prefix check never breaks across profiles (it does not resolve
the shared-plugins symlink). All paths in the shared
`known_marketplaces.json` / `installed_plugins.json` are normalized to
`~/.claude-shared/...`.

- **Manage** plugins only via `~/.local/bin/ccplug` (`ccplug marketplace add|update`, `ccplug install|update|disable <plugin>@<mkt>`, `ccplug list`). It execs `claude plugin` under `CLAUDE_CONFIG_DIR=$HOME/.claude-shared`.
- A new profile **must not** run `claude plugin marketplace add/update` itself — that writes a profile-specific absolute path into the shared registry and reintroduces the cross-profile "corrupted installLocation" failure. New profiles consume plugins through the symlink only.
- `enable`/`disable` is stored **per-profile**; `claude plugin update` prints "restart required to apply" — relaunch the profile.

## Reference

- Existing profiles: `.claude` (default, no wrapper), `.claude-work`, `.claude-personal`, `.claude-exp`, `.claude-mine`
- Existing wrappers: `~/.local/bin/claude-{work,personal,exp,mine}`
- Plugin admin wrapper: `~/.local/bin/ccplug` → `CLAUDE_CONFIG_DIR=$HOME/.claude-shared claude plugin …` (single admin base; `installLocation`/`installPath` normalized to `.claude-shared`)
- Shared plugins: `~/.claude-shared/plugins/` (one source of truth, all profiles symlink here)
- Shared skills dir: `~/.claude-shared/skills/` (currently NOT auto-loaded by profiles — only manually symlinked into specific profile skills/ dirs)

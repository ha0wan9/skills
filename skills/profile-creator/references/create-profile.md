# Profile Creation Reference

Detailed procedure for creating a new Claude Code config profile. The
script `scripts/create_profile.py` automates all steps; read this reference
for the underlying decisions and manual recovery paths.

## Decision: Simple vs. Isolated Launcher

**Simple (default)** — inherits the calling shell's environment. Use for
personal or open-source profiles where sharing API keys from the shell is fine.

**Isolated** — unsets common API/token env vars before exec-ing `claude`.
Use for work or client profiles where accidentally leaking keys from the
parent shell (e.g. a personal `ANTHROPIC_API_KEY`) would cause problems.
The unset block covers:

```
ANTHROPIC_API_KEY  ANTHROPIC_AUTH_TOKEN  ANTHROPIC_BASE_URL
GITHUB_TOKEN  GOOGLE_APPLICATION_CREDENTIALS
SLACK_BOT_TOKEN  LINEAR_API_KEY  JIRA_API_TOKEN  CONFLUENCE_API_TOKEN
```

Both forms load a per-profile env file if it exists:
`~/.config/claude-<name>/env`. Use this to inject profile-specific secrets
without polluting the shell.

## Step-by-Step (manual path)

Automate with `scripts/create_profile.py --help`; do manually only when
the script is unavailable.

```bash
NAME=<name>

# 1. Validate: name matches ^[a-z0-9][a-z0-9-]*$ and target dir absent
[[ "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "Invalid name"; exit 1; }
[ ! -d "$HOME/.claude-${NAME}" ] || { echo "Already exists"; exit 1; }

# 2. Prerequisite: shared plugins must exist
[ -d "$HOME/.claude-shared/plugins" ] || {
  echo "~/.claude-shared/plugins missing — run shared-store setup first"
  exit 1
}

# 3. Create profile dir and plugins symlink
mkdir -p ~/.claude-${NAME}
ln -s ~/.claude-shared/plugins ~/.claude-${NAME}/plugins

# 4. Write launcher (choose simple or isolated body from templates/)
install -m 0755 /dev/stdin ~/.local/bin/claude-${NAME} << 'LAUNCHER'
# ... paste launcher body here ...
LAUNCHER

# 5. Optional: seed memory files from an existing profile
# cp ~/.claude-<source>/CLAUDE.md ~/.claude-${NAME}/CLAUDE.md
# cp ~/.claude-<source>/RTK.md    ~/.claude-${NAME}/RTK.md

# 6. Symlink profile-creator skill
mkdir -p ~/.claude-${NAME}/skills
ln -s ~/.claude-shared/skills/profile-creator \
      ~/.claude-${NAME}/skills/profile-creator

# 7. Verify
ls -la ~/.claude-${NAME}/
```

## Why the Plugins Symlink Must Point at `~/.claude-shared/plugins`

Claude Code's plugin CLI resolves `installLocation`/`installPath` as a
literal prefix — it does **not** follow symlinks when comparing. All paths
in `known_marketplaces.json` and `installed_plugins.json` are normalized to
`~/.claude-shared/…`. A profile that runs `claude plugin marketplace add`
itself rewrites those paths as `~/.claude-<name>/plugins/…`, breaking every
other profile's plugin lookups (the "corrupted installLocation" failure).

Centralizing administration via `ccplug` keeps all registry paths under
`~/.claude-shared`.

## Existing Profiles Reference

| Profile | Config dir | Launcher |
|---|---|---|
| default | `~/.claude` | (none — invoked as `claude`) |
| work | `~/.claude-work` | `~/.local/bin/claude-work` |
| personal | `~/.claude-personal` | `~/.local/bin/claude-personal` |
| exp | `~/.claude-exp` | `~/.local/bin/claude-exp` |
| mine | `~/.claude-mine` | `~/.local/bin/claude-mine` |

Shared plugins: `~/.claude-shared/plugins/`
Plugin admin wrapper: `~/.local/bin/ccplug` → `CLAUDE_CONFIG_DIR=$HOME/.claude-shared claude plugin …`

## Troubleshooting

**Launcher not found after creation** — open a fresh terminal; `~/.local/bin`
must be on `PATH`. Add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc`
or `~/.zshrc` if needed.

**Plugin not visible in new profile** — confirm the plugins symlink resolves:
`ls -la ~/.claude-<name>/plugins`. If missing, re-run the symlink step.

**`--version` hangs or errors** — the launcher `exec claude "$@"` requires
`claude` to be on `PATH`. Verify with `which claude`.

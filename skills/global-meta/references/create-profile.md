# Profile Creation Reference

Detailed procedure for `global-meta create` — scaffolding a new Claude Code or
Codex config profile. The script `scripts/create_profile.py` automates every
step; read this for the underlying decisions and manual recovery paths.

## Runtime adapter

A profile = `(runtime, config-root)`. The script's `ADAPTERS` table parameterizes:

| Concept | claude | codex |
|---|---|---|
| Config-home env | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` |
| Profile dir | `~/.claude-<name>` | `~/.codex-<name>` |
| Launcher | `~/.local/bin/claude-<name>` | `~/.local/bin/codex-<name>` |
| Exec binary | `claude` | `codex` |
| Shared store | `~/.claude-shared` | `~/.codex-shared` |
| Canonical memory (seed) | `CLAUDE.md` | `AGENTS.md` |
| Plugins symlink | **required** | best-effort (model unverified, §10) |

The claude leg reproduces the former `profile-creator` behavior byte-for-byte
(its launcher `extra_unset` is empty).

`CODEX_HOME` is the same env var `project-meta/scripts/install_codex_hooks.py` already
reads (`$CODEX_HOME`, default `~/.codex`) — the Codex *home* is grounded in existing repo
tooling, not guessed. What remains genuinely unverified is the Codex *shared-plugin /
marketplace* model (the `~/.codex-shared` store + a `ccodexplug`-equivalent guard); the
plugins symlink is therefore best-effort until that model is confirmed (proposal §10).

## Decision: Simple vs. Isolated Launcher

**Simple (default)** — inherits the calling shell's environment. Use for
personal/OSS profiles where sharing keys from the shell is fine.

**Isolated** (`--isolated`) — unsets common API/token vars before exec-ing the
runtime. Use for work/client profiles where leaking a parent-shell key would
cause problems. Base unset list:

```
ANTHROPIC_API_KEY  ANTHROPIC_AUTH_TOKEN  ANTHROPIC_BASE_URL
GITHUB_TOKEN  GOOGLE_APPLICATION_CREDENTIALS
SLACK_BOT_TOKEN  LINEAR_API_KEY  JIRA_API_TOKEN  CONFLUENCE_API_TOKEN
```

codex profiles additionally unset `OPENAI_API_KEY`. Both forms load a
per-profile env file if present: `~/.config/<rt>-<name>/env`.

## Step-by-Step (manual path)

Automate with `scripts/create_profile.py --help`; do manually only when the
script is unavailable. (`<rt>` = `claude` or `codex`; `<VAR>` = the config-home
env var.)

```bash
NAME=<name>; RT=<rt>

# 1. Validate name and absence of target dir
[[ "$NAME" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "Invalid name"; exit 1; }
[ ! -d "$HOME/.${RT}-${NAME}" ] || { echo "Already exists"; exit 1; }

# 2. Prerequisite: shared plugins (required for claude; best-effort for codex)
[ -d "$HOME/.${RT}-shared/plugins" ] || echo "shared store missing"

# 3. Create profile dir + plugins symlink (if the shared store exists)
mkdir -p ~/.${RT}-${NAME}
ln -s ~/.${RT}-shared/plugins ~/.${RT}-${NAME}/plugins   # skip if absent

# 4. Write launcher from templates/launcher-{simple,isolated}.sh (substitute placeholders)
# 5. Optional: seed canonical memory from a same-runtime profile
# 6. Symlink the global-meta skill: ln -s ~/.${RT}-shared/skills/global-meta ~/.${RT}-${NAME}/skills/global-meta
# 7. Verify: ls -la ~/.${RT}-${NAME}/
```

## Why the Plugins Symlink Must Point at the Shared Store

Claude Code's plugin CLI resolves `installLocation`/`installPath` as a **literal
prefix** — it does not follow symlinks when comparing. All paths in
`known_marketplaces.json` / `installed_plugins.json` are normalized to
`~/.claude-shared/…`. A profile that runs `claude plugin marketplace add` itself
rewrites those paths to `~/.claude-<name>/plugins/…`, breaking every other
profile's plugin lookups (the "corrupted installLocation" failure). Centralizing
admin via `ccplug` keeps all registry paths under the shared store. This is the
`multiclaude-marketplace-guard` invariant — global-meta is its enforcement home,
and the same guard must be confirmed for Codex before a `ccodexplug` ships (§10).

## Existing Profiles Reference

| Profile | Config dir | Launcher |
|---|---|---|
| default | `~/.claude` | (none — `claude`) |
| work | `~/.claude-work` | `~/.local/bin/claude-work` |
| personal | `~/.claude-personal` | `~/.local/bin/claude-personal` |
| exp | `~/.claude-exp` | `~/.local/bin/claude-exp` |
| mine | `~/.claude-mine` | `~/.local/bin/claude-mine` |

Shared plugins: `~/.claude-shared/plugins/` · admin wrapper: `~/.local/bin/ccplug`.

## Troubleshooting

**Launcher not found** — open a fresh terminal; `~/.local/bin` must be on `PATH`
(`export PATH="$HOME/.local/bin:$PATH"`).

**Plugin not visible** — confirm the symlink resolves: `ls -la ~/.<rt>-<name>/plugins`.

**`--version` hangs** — the launcher `exec <bin> "$@"` requires the runtime binary
on `PATH` (`which claude` / `which codex`).

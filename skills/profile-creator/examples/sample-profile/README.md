# Example: `claude-work` profile

Reference output of `scripts/create_profile.py work` (a non-isolated profile that
shares the global plugin store). Point-in-time snapshot — re-render rather than
hand-editing.

- **Scope:** one simple (non-`--isolated`) profile named `work`.
- **Version:** 1.0
- **Coverage:** exercises the name-validation, dir-creation, shared-plugins
  symlink, and launcher-write legs of `create_profile.py`.

## Created tree

```
~/.claude-work/                      # CLAUDE_CONFIG_DIR for this profile
  plugins -> ~/.claude-shared/plugins   # symlink: plugins stay shared
~/.local/bin/claude-work             # launcher: CLAUDE_CONFIG_DIR=~/.claude-work exec claude "$@"
```

## Launcher (`~/.local/bin/claude-work`, from `templates/launcher-simple.sh`)

```sh
#!/usr/bin/env bash
export CLAUDE_CONFIG_DIR="$HOME/.claude-work"
exec claude "$@"
```

## Reproduce

```bash
python3 skills/profile-creator/scripts/create_profile.py --dry-run work
```

`--dry-run` prints each action without touching the filesystem; drop it to apply.

# Example: `global-meta create` — dual-runtime profiles

Reference run of the `create` verb (absorbed from `profile-creator`), showing both
runtimes. Point-in-time snapshot; re-render rather than edit by hand.

## Claude profile (isolated, seeded)

```bash
python3 skills/global-meta/scripts/create_profile.py --runtime claude --isolated --seed-from work client-acme
```

Produces:
- `~/.claude-client-acme/` (config dir)
- `~/.claude-client-acme/plugins` → `~/.claude-shared/plugins`
- `~/.local/bin/claude-client-acme` (isolated launcher; unsets API/token vars)
- seeded `CLAUDE.md`, `RTK.md` copied from `~/.claude-work/`
- `~/.claude-client-acme/skills/global-meta` → shared skill (if present)

Launch: `claude-client-acme` (fresh terminal).

## Codex profile (simple)

```bash
python3 skills/global-meta/scripts/create_profile.py --runtime codex oss
```

Produces:
- `~/.codex-oss/` (config dir; `CODEX_HOME`)
- `~/.local/bin/codex-oss` (simple launcher)
- plugins symlink only if `~/.codex-shared/plugins` exists (Codex shared-plugin
  model unverified — see `proposals/global-meta.md` §10)

Launch: `codex-oss` (fresh terminal).

## Dry-run first

```bash
python3 skills/global-meta/scripts/create_profile.py --dry-run --runtime claude client-acme
```

Prints every action without making changes — use to confirm parity before applying.

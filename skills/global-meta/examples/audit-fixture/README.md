# audit-fixture — seeded config root for `config_root_audit.py`

A fake user config root with **four seeded findings** (F1–F4). The acceptance test for
DASH-033 (and the convergence test for DASH-034's `--emit-fix`) runs against this tree.
The zero-findings twin is [`../audit-fixture-clean/`](../audit-fixture-clean/).

## Layout mapping (fixture dir ↔ real machine)

| Fixture path | Real path |
|---|---|
| `claude-shared/plugins/installed_plugins.json` | `~/.claude-shared/plugins/installed_plugins.json` |
| `claude-shared/enabled-plugins.local.json` | `~/.claude-shared/enabled-plugins.local.json` |
| `claude-shared/plugins/cache/<mkt>/<plugin>/<version>/` | the materialized plugin cache |
| `claude/settings.json` | `~/.claude/settings.json` (default profile user settings) |
| `claude-work/settings.json` | `~/.claude-work/settings.json` (a named profile) |
| `local-bin/` | `~/.local/bin` (launchers) |

## Path-resolution conventions (the script MUST honor these)

- `--config-home <dir>` points at this fixture root; the script derives all stores from it
  using the table above. On the real machine `--config-home` defaults to `$HOME` and the
  same relative layout applies (`.claude-shared`, `.claude`, `.claude-<name>`, `.local/bin`
  — dot-prefixed; the fixture drops the dots so the tree is visible).
- **Relative `installPath` values are fixture-root-relative.** The real registry stores
  absolute paths; the script treats any non-absolute `installPath` as relative to
  `--config-home`.
- The local-scope spec check compares `projectPath` against `--home-dir` (default: real
  `$HOME`). Fixture runs pass `--home-dir /Users/HaoranWang` because the fixture records
  use that literal.
- The four-way spec applies to plugins of the marketplace named by `--spec-marketplace`
  (fixture: `test-mkt`); other marketplaces are inventoried but not spec-checked.

## Schemas (mirrors of the real files)

`installed_plugins.json`:
```json
{"plugins": {"<name>@<mkt>": [{"scope": "local|user", "projectPath": "<abs>", "installPath": "<path>", "version": "X.Y.Z", "installedAt": "<iso>", "lastUpdated": "<iso>", "gitCommitSha": "<sha>"}]}}
```
`enabled-plugins.local.json` and `settings.json` (`enabledPlugins` key):
```json
{"enabledPlugins": {"<name>@<mkt>": true}}
```

## Seeded findings

| Code | What is wrong | Where |
|---|---|---|
| **F1** `stale-enablement` | `retired-plugin@test-mkt` is enabled but has **no registry entry** | `claude-shared/enabled-plugins.local.json` |
| **F2** `wrong-scope` | `beta-plugin@test-mkt` is installed at **user** scope — violates the local-scope@`--home-dir` spec | registry |
| **F3** `dup-scope-records` | `alpha-plugin@test-mkt` has **two** records (local@home **and** a user-scope duplicate) | registry |
| **F4** `cache-version-mismatch` | `gamma-plugin@test-mkt` registry says `1.2.0` but only cache dir `1.1.0/` exists | registry vs `cache/test-mkt/gamma-plugin/` |

Expected audit result on this fixture: **exit 1**, report contains all four codes above,
and (because findings exist) at least one ready-to-run `board.py inbox-add` capture line
(format contract: plan §8). On `audit-fixture-clean/`: **exit 0**, zero findings.

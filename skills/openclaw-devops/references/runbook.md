# OpenClaw DevOps Runbook

Load this when you need the manual procedure behind an engine verb, the
failure-mode catalog, the cron recipe, sudoers setup, or cross-runtime install.
The engine (`scripts/openclaw_devops.py`) automates all of this; this file is the
human-readable backing + the recovery path when automation is blocked.

## Contents
- [Engine verbs](#engine-verbs)
- [Update procedure (what `update` automates)](#update-procedure)
- [Rollback](#rollback)
- [Repair action catalog](#repair-action-catalog)
- [Failure modes](#failure-modes)
- [OpenClaw cron recipe](#openclaw-cron-recipe)
- [Passwordless sudo for system-copy updates](#passwordless-sudo)
- [Cross-runtime portability](#cross-runtime-portability)

## Engine verbs

| Verb | Mutates? | What it does |
|---|---|---|
| `sanity` | no | services, gateway health, config validate, version alignment, cron scheduler, stale-plugin count, disk, update-available. |
| `repair` | yes (bounded) | restart dead/failed services, daemon-reload, `doctor --fix`, re-align version skew. `--dry-run` plans. |
| `update` | yes | transactional upgrade: snapshot → install all copies → restart → `verify` → auto-rollback on fail. |
| `verify` | no | integrity gate: config validate + health + cron list + version aligned. Exit 1 if any gate fails. |
| `rollback` | yes | reinstall recorded previous version on all copies + restore config backup + restart. |
| `cycle` | yes | sanity → repair (if degraded) → update (if newer & policy) → verify/rollback. Lock-guarded. Cron entry. |

## Update procedure

What `update` automates (and the manual fallback if you must do it by hand):

1. **Snapshot**: copy `~/.openclaw/openclaw.json` → `*.devops-bak.<ts>`; record the
   current version in `state/state.json`.
2. **Install every copy to the same version** (skew is the #1 crash cause):
   - user copy: `npm i -g openclaw@<v> --prefix ~/.local`
   - system copy: `sudo npm i -g openclaw@<v>` (covers `/usr/lib`, which the
     gateway ExecStart runs).
3. **Bump** `Description=(v<old>)` → `(v<v>)` in `openclaw-node.service`, then
   `systemctl --user daemon-reload`.
4. **Restart** in order: `openclaw-gateway` → `-chloe` → `-node`.
5. **Verify** (the integrity gate): `openclaw config validate` must say
   "Config valid"; `openclaw health` must return; `openclaw cron list` must list
   jobs; all copies must report the same version.
6. **Rollback on any gate failure** (see below).

Policy gates before step 1: only the `latest` stable dist-tag; a major
(calendar-year) jump is held unless `--allow-major`; optional maintenance-hours
window.

## Rollback

`rollback` reinstalls the recorded previous version across all copies, restores
the snapshotted config, and restarts. Manual equivalent:
`sudo npm i -g openclaw@<prev>` + `npm i -g openclaw@<prev> --prefix ~/.local`,
restore `*.devops-bak.<ts>` over `openclaw.json`, restart the three services,
confirm `verify` passes.

## Repair action catalog

Only bounded, reversible actions run unattended:
- **Dead/failed service** → `systemctl --user reset-failed <svc>` then `restart`.
- **Gateway unhealthy, units drifted** → `daemon-reload` + restart gateway.
- **Stale plugin/cron config warnings** → `openclaw doctor --fix` (normalizes
  legacy storage; safe, non-destructive).
- **Version skew** → reinstall lagging copies up to the highest installed version.

Out of scope for auto-repair (recommend to a human instead): deleting state,
editing secrets, removing channels/agents, force-reinstalling plugins.

## Failure modes

- **Version skew crash-loop**: system `/usr/lib` and user `~/.local` copies on
  different versions; the gateway wrapper execs one, the node service the other,
  and incompatible payload shapes crash-loop. Fix: align all copies.
- **Stale plugin entries fail validation**: a `plugins.entries.<x>` or
  `plugins.allow` referencing a plugin that moved external (e.g. `discord`,
  `brave`) or a removed package (`mem9`) blocks `config validate`. Fix: install
  the official external plugin (`openclaw plugins install clawhub:@openclaw/<x>`)
  or remove the stale entry; `doctor --fix` normalizes most.
- **Plugin needs compiled JS**: newer OpenClaw drops TypeScript-source fallback;
  a hook plugin with only `index.ts` must ship `dist/index.js` + `package.json`
  `"main"`/`"type":"module"`. Fix: compile/strip types.
- **Headless browser can't start**: on a display-less host the gateway-managed
  browser may be configured headed (`browser.headless=false`) and CDP profiles
  ignore both the config flag and `OPENCLAW_BROWSER_HEADLESS=1`. For scraping use
  raw `google-chrome-stable --headless=new --dump-dom` instead — not a devops
  concern, but it shows up in browser doctor.
- **"minimal tool profile removed N tools"** in `doctor` is usually an
  intentionally-restricted agent (e.g. a PII/finance agent), not a fault.

## OpenClaw cron recipe

The cron must be a **thin agentTurn** — all logic lives in the engine:

```bash
openclaw cron add \
  --name "🛠️ OpenClaw DevOps — daily sanity+repair+update" \
  --cron "23 4 * * *" --tz Europe/Paris --agent chat --session isolated \
  --announce --channel <discord-channel-id> \
  --message "Run OpenClaw self-maintenance and report. Execute exactly:
python3 /home/<user>/.openclaw/workspace/skills/openclaw-devops/scripts/openclaw_devops.py cycle --json
Then post the engine's summary to this channel (compact, no tables). Do NOT take
any other maintenance action yourself — the script is authoritative. If it rolled
back or reports overall=fail, lead with a ⛔ alert."
```

Cadence guidance: a single daily `cycle` covers sanity+repair every day and only
applies an update when a newer stable exists and policy allows — so one job is
enough. Split into a more frequent read-only `sanity` and a weekly `cycle` if you
want lighter daily touch. Use an off-:00 minute to avoid fleet-wide API spikes.

## Passwordless sudo

Full unattended updates need the system copy upgraded, which needs sudo. Scope a
single sudoers rule to just the npm install (not blanket NOPASSWD):

```
# /etc/sudoers.d/openclaw-devops  (visudo -f)
<user> ALL=(root) NOPASSWD: /usr/bin/npm i -g openclaw@*, /usr/bin/npm install -g openclaw@*
```

Without it the engine updates the user copy, marks the system copy `skipped`, and
warns about skew — a human then runs `sudo npm i -g openclaw@<v>`.

## Bugs panel / backlog

A cross-bug registry in `state/bugs.json` (id `BUG-N`, `next_id` counter). Writes
take a blocking `state/bugs.lock` so concurrent agents don't clobber each other.

Record shape: `id · title · severity (sev1-4) · status · source · detail · tags ·
session (dbg-…) · lesson · assignee · created · updated · history[]`. Statuses:
`open → triaged → in-progress → fixed` (or `wontfix` / `duplicate`).

- **Any agent or cron logs a bug it hit** with one call — no orchestration needed:
  `openclaw_devops.py bugs --add --title "…" --severity sev2 --source "<agent/cron>" --detail "…" --tags "…"`
- **Triage / track**: `bugs --list [--status open]`, `bugs --show BUG-N`,
  `bugs --panel` (counts by status + open-by-severity + recently-fixed; cron-friendly).
- **Close the loop** when a meta-debug session fixes it:
  `bugs --update BUG-N --status fixed --session <dbg-id> --lesson "…" --note "…"`.
- `cycle` surfaces the open-bug count in its summary, so the maintenance cron
  reports backlog pressure alongside health. To post the full panel on a schedule,
  add a thin cron that runs `bugs --panel` and announces the output.

## Cross-runtime portability

The skill folder is self-contained and runtime-agnostic; the engine maintains the
OpenClaw install on the host regardless of which agent runtime invoked it.

- **OpenClaw**: `~/.openclaw/workspace/skills/openclaw-devops/`. Cron as above.
- **Claude Code**: drop the same folder into `~/.claude-shared/skills/openclaw-devops/`
  (or any skills root). Invoke the engine directly; schedule via the host's
  scheduler if not using the OpenClaw cron.
- **Codex**: drop into the Codex skills root. Same engine, same `config.json`.

`detect_runtime()` only resolves which root the folder sits in for reporting; it
does not change behavior. The single thing that varies per host is `config.json`
(`copies`, `services`, paths) — keep host-specifics there, never in the prompt.

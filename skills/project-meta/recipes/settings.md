# Recipe: settings

View and toggle the project's harness settings — the enforcement profile and
which optional capabilities are installed — without re-running a full `init`.

## When to load

- User invokes `/project-meta settings` (no args → view; with args → toggle)
- User asks to "turn on/off" a harness capability after init (hooks, phase-lock,
  multi-host, issue-tracker), or to change the `HARNESS_PROFILE`
- User asks "what's enabled in this harness and how do I change it?"

## Mode

**editing** — but defaults to a **read-only view** when invoked with no toggle
argument. It writes only on an explicit `profile` / `enable` / `disable`
operation, and only after pre-commit delivery. Mixing a silent edit into the
view is a contract violation (the *Mode declaration* shared rule).

`settings` is the **editing counterpart to `status`**. `status` *reports* harness
state read-only; `settings` *changes* the profile and capability set. Detection
of "what's currently on" is delegated to `status`'s capability inspection (step 7
there) — do not re-derive it here (one source of truth per fact).

## Settings model — derived, never a new state file

There is **no `.harness/settings.json`**. Inventing one would drift against the
real artifacts (AP-VAL-2). Settings are *derived* from where each fact already
lives:

| Setting | Source of truth |
|---|---|
| `HARNESS_PROFILE` | `.claude/settings.json` `env.HARNESS_PROFILE` (Codex: the `HARNESS_PROFILE=` prefix in `~/.codex/hooks.json`) |
| hooks | `.claude/hooks/*.sh` + their wiring in `.claude/settings.json` |
| phase-lock | `agents/phase-lock-contract.md` + `.harness/phase-state.json` + `.harness/gates/*.sh` |
| multi-host | generated mirror files (`.cursor/`, `.opencode/`, `gemini-extension.json`, `.codex/`) |
| issue-tracker | `agents/issue-tracking.md` (+ optional `issue-tracker-reminder.sh` wiring) |

A capability is "on" iff its artifacts are present **and** wired (routed +
manifest-registered). A doc without routing, or a hook without its doc, is
*half-installed* — report it as a FAIL, not as "on" (same integrity gate the
validator enforces).

**Not in scope: `USER.md`.** That file holds local, git-ignored *user workflow
preferences* and is owned by the preference questionnaire
(`render_user_preferences.py`, see `references/project-lifecycle.md`). `settings`
owns *project harness toggles* that live in committed artifacts. Keep the two
distinct; if the user wants to change preferences, route to the reset path in
`recipes/init.md`, not here.

## Required references

Load lazily, only for the operation requested:

- [`references/cli-command-patterns.md`](../references/cli-command-patterns.md) — route + shared rules (always, for the route contract)
- [`references/documentation-delivery.md`](../references/documentation-delivery.md) — pre-commit delivery, before any write
- When enabling/disabling a capability, load that capability's own reference and reuse `recipes/init.md` step 6 — **do not re-document install steps here**:
  - hooks → [`templates/hooks/README.md`](../templates/hooks/README.md)
  - phase-lock → [`templates/phase-lock-contract.md`](../templates/phase-lock-contract.md)
  - multi-host → [`references/multi-host-manifests.md`](../references/multi-host-manifests.md)
  - issue-tracker → [`references/issue-tracking-integration.md`](../references/issue-tracking-integration.md)

## Workflow

1. **Parse the operation** from the invocation:
   - no args → **view**
   - `profile <minimal|standard|strict>` → change the enforcement dial
   - `enable <hooks|phase-lock|multi-host|issue-tracker[:<tracker>]>` → install
   - `disable <capability>` → remove
   - Unknown operation/capability → list the supported set and stop; do not guess.

2. **View** (always runs first, including before a toggle so the user sees the
   before-state): render the settings matrix — current `HARNESS_PROFILE` and each
   capability's state (on / off / half-installed), reusing `status`'s detection.
   If the operation is a bare view, stop here (read-only; no delivery needed).

3. **profile** operation:
   - Edit `.claude/settings.json` `env.HARNESS_PROFILE` (create the key if
     absent). For a Codex-primary repo, also update the `HARNESS_PROFILE=` prefix
     via `install_codex_hooks.py --profile <p>`.
   - Guard rail: warn before setting `strict` if the repo has not been running
     `standard` cleanly (per `templates/hooks/README.md` Profile Selection). Do
     not silently jump to strict.

4. **enable** operation:
   - Run the matching `recipes/init.md` step-6 install for that capability
     (cite it; do not duplicate the steps). Every instantiated artifact carries
     full provenance frontmatter; add routing from the canonical memory file and
     a `agents/project-artifacts.md` manifest row.
   - If the install touches **≥2 harness files** (e.g. issue-tracker writes
     `agents/issue-tracking.md` + the loader pointer + the manifest), MUST
     dispatch per-file Worker + Reviewer per the *Subagent dispatch* shared rule
     (AP-COORD-1); the conductor does not edit once dispatch triggers.
   - Outward-facing bindings (issue-tracker team/project/labels) are a
     synchronous user gate — confirm before writing.

5. **disable** operation:
   - Remove the capability's artifacts **and** its routing pointer **and** its
     manifest row together — leaving a dangling pointer or orphaned manifest
     entry is a half-uninstall (the mirror of the half-install FAIL). For hooks,
     remove both the script and its `settings.json` wiring.
   - Disabling never deletes user content (a populated `docs/backlog/` stays);
     it removes the *harness wiring*, and says so in the delivery.

6. **Validate** after any write: `python3 scripts/validate_target_harness.py
   <repo>` — every check PASS or WARN. A capability left half-installed is a FAIL;
   loop back.

7. **Pre-commit delivery** (only when step 3/4/5 wrote): render the standard
   delivery sections and wait for user approval before committing. A bare view
   never commits.

## Output contract

- The **settings matrix**: `HARNESS_PROFILE` + per-capability state
  (on / off / half-installed), ≤20 lines.
- For a toggle: what changed (files added/removed, routing + manifest updates),
  the post-change validator result, and the pre-commit delivery sections.
- For a bare view: the matrix plus the one command to change each setting. No
  edits, no delivery.

## Anti-patterns

- **Inventing a settings state file.** A `.harness/settings.json` duplicates the
  real artifacts and drifts. Derive from the sources of truth above. AP-VAL-2.
- **Silent edit in the view.** `settings` with no toggle arg MUST NOT write.
  Mixing read and edit modes silently violates the shared *Mode declaration* rule.
- **Half-toggle.** enable that adds a doc but no routing/manifest, or disable that
  removes a doc but leaves a dangling pointer. A capability is on iff fully wired;
  off iff fully removed.
- **Conflating with `USER.md`.** Preferences are local/git-ignored and owned by
  the questionnaire; settings are committed harness toggles. Route preference
  changes to `init`'s reset path.
- **Premature strict.** Flipping to `strict` without a clean `standard` run
  invites work-arounds (see hooks README). Warn first.
- **Skipping dispatch on a multi-file enable.** ≥2 harness files → Worker +
  Reviewer dispatch (AP-COORD-1), same as `init`.
- AP-VAL-2: skipping `validate_target_harness.py` after a toggle — the validator
  is part of the contract.

## Quick checks (one-liner each)

```bash
# current profile (Claude Code)
jq -r '.env.HARNESS_PROFILE // "unset"' .claude/settings.json 2>/dev/null

# capability presence
ls .claude/hooks/*.sh 2>/dev/null            # hooks
[ -f .harness/phase-state.json ] && echo phase-lock
[ -f agents/issue-tracking.md ] && echo issue-tracker
ls .cursor/rules/agents.md .opencode/instructions.md 2>/dev/null  # multi-host

# half-install guard: issue-tracker doc present but not routed (match the path,
# not the bare stem, to mirror validate_target_harness.py)
grep -ql 'agents/issue-tracking.md' AGENTS.md CLAUDE.md 2>/dev/null || echo "WARN: issue-tracking.md not routed"
```

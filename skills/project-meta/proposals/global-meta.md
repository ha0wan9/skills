# Proposal: `global-meta` — a user/global-scope harness skill (superset of `profile-creator`, dual-runtime)

> **Status:** Partially shipped — the `create` verb is **live** in `skills/global-meta/` 1.0.0 (2026-06-11; `profile-creator`
> retired from marketplace, marketplace 2.0.x). Remaining verbs: verdict written back 2026-06-11 (see below).
> - `create` — **LIVE** since 1.0.0 (profile-creator retired 2026-06-11, marketplace 2.0.0).
> - `status` + `audit` — **APPROVED, build as v1.1** (DASH-039; `config_root_audit.py`; four-way consistency as first-class check; snapshot ledger; context-tax report; findings as `board.py inbox-add` lines).
> - `drift` — **FOLDED into `audit`** as a cross-profile section (2026-06-11; shared `~/.claude-shared` store eliminated most surface).
> - `reconcile` — **SUPERSEDED by `audit --emit-fix` v1.2** (DASH-040; reviewable idempotent snapshot-guarded fix script; never auto-applies; borrowed from openclaw-devops transactional shape).
> - `settings enable/disable` — **CUT** (update-config/`/config` own leaf edits; cross-profile toggles ride the emitted fix script).
> - `track` (dotfiles git) — **DEFERRED** (snapshot ledger covers rollback; revisit if diff-review demand materialises; secret-safety MUSTs stay).
> - `deliver` — **unchanged** (reuses project-meta deliver as specified).
> **Board items:** DASH-039 (`status`+`audit` v1.1), DASH-040 (`reconcile`→`audit --emit-fix` v1.2), DASH-041/036 (marketplace slimming / context-tax) — v0.5 milestone, see `docs/backlog/`.
> **Build plan:** `docs/plans/global-meta-lifecycle-build-plan.md`.
> **Scope:** a new top-level skill `skills/global-meta/` that **absorbs and deprecates `profile-creator`**, adds the
> audit/drift/reconcile/track lifecycle for Claude *and* Codex config roots, and reuses `project-meta` as its root engine.
> **Decisions locked (2026-06-06):** (1) absorb + deprecate `profile-creator`; (2) full Claude+Codex parity in v1;
> (3) this doc is the persisted plan.
> **Reviewed (2026-06-06):** adversarial self-critique → aligned to the **one-sided coordination stance** — `project-meta`/
> `global-meta` are the only bindable parties; the runtime engine and methodology plugins are *adapted to*, not bound (encoded
> as `AP-COORD-7`). global-meta owns *policy*, delegates *mechanism*, and treats durable memory as a multi-writer set.
> **Verdict reviewed 2026-06-11:** per-verb dispositions above; diagnosis arbitration: when `audit` surfaces a config-root
> corruption/incident, root-causing routes to `meta-debug`; global-meta reports findings and hands off a case file.
> **Grounding:** the gap analysis in this session (memory `global-meta-skill-gap`, `project-meta-vs-ultracode-superpowers`),
> verified against current Claude Code behavior (settings precedence, ~26 hook events, skill context-tax, `CLAUDE_CONFIG_DIR`
> isolation bug anthropics/claude-code#58815, hook-RCE CVE-2025-59536). Builds on the existing `profile-creator` skill and the
> `project-meta` root-skill / shared-CLI-delegation pattern.

## 1. Problem

Every tool that touches a *user's global* Claude/Codex config today is a **point-in-time, single-scope editor**: `/config`
(scalars), the `update-config` skill (one `settings.json`), `/hooks` (one hook), `profile-creator` (create one Claude
profile), `/plugin` (install). **None does ongoing audit → drift-detection → evolution.** `project-meta`'s arbitration table
explicitly defers user-level config to `profile-creator`, which only *creates* — so nobody owns the *lifecycle* of an existing
`~/.claude` / `~/.codex`. No prior art exists in the ecosystem.

This bites the operator specifically: a multi-profile setup (`~/.claude`, `~/.claude-work`, `~/.claude-personal`,
`~/.claude-exp`, `~/.claude-mine`) with a known cross-profile isolation bug (#58815: user `CLAUDE.md` bleeds across
`CLAUDE_CONFIG_DIR` profiles), heavy skill/plugin context-tax (dozens of skills + 12 plugins vs the ~8–12 community ceiling at
~100 tokens/skill), and accumulating machine-wide-blast-radius hooks (`rtk-rewrite`, `git-pull-ff`).

Three failure modes dominate global config over time:

- **AP-GLOB-1 (proposed) — silent cross-profile drift.** Profiles diverge with no baseline to diff against; the #58815 bleed
  and `known_marketplaces.json` corruption (memory `multiclaude-marketplace-guard`) are instances. Nobody notices until a
  profile misbehaves.
- **AP-GLOB-2 (proposed) — context-tax / orphan creep.** Skills and plugins accumulate; each costs context every session and
  nothing audits usage-vs-cost or flags orphans.
- **AP-GLOB-3 (proposed) — unreviewable global edits.** `~/.claude` is not a git repo by default, so global changes (incl.
  hooks with RCE surface) land with no diff, no review, no rollback.

## 2. Why this is `project-meta`'s category at a new scope

`project-meta` = per-repo harness engineering. `global-meta` = the **same engine pointed at the user config root**. It is the
*opposite* of `ultracode` (a runtime mode) and `superpowers` (global process discipline): like `project-meta`, it produces
**durable, versioned, reviewable infrastructure** — just at `~/.claude`/`~/.codex` instead of a repo (memory
`project-meta-vs-ultracode-superpowers`). That is exactly why it should be *derived*, not built from scratch (memory
`prefer-lightweight-derived-design`, `project-meta-as-root-skill`, `cli-toolkit-doctrine`).

## 3. The runtime-agnostic core: a config-root adapter

One abstraction — *a profile = (runtime, config-root)* — mirroring `project-meta`'s "one prose contract, two per-runtime
backings" (memory `codex-orchestration-parity`). A single `RuntimeAdapter` (one class, two instances) resolves:

| Concept | Claude Code | Codex |
|---|---|---|
| Config-home env | `CLAUDE_CONFIG_DIR` | `CODEX_HOME` |
| Default root / named | `~/.claude` · `~/.claude-<name>` | `~/.codex` · `~/.codex-<name>` |
| Launcher | `~/.local/bin/claude-<name>` | `~/.local/bin/codex-<name>` |
| Canonical memory | `CLAUDE.md` | `AGENTS.md` |
| Settings | `settings.json` | `config.toml` |
| Hooks | `settings.json` + `hooks/*.sh` | `hooks.json` + `hooks/` |
| Skills / plugins | `skills/`, `plugins/` + `known_marketplaces.json` | `skills/` (codex plugin model) |
| Shared store | `~/.claude-shared` (`ccplug`) | `~/.codex-shared` (parallel `ccodexplug`) |
| MCP config | `~/.claude.json` | `config.toml` mcp servers |
| **Secrets — never git** | `.credentials.json`, `~/.claude.json`, `projects/`, `sessions/`, `logs/` | `auth.json`, `sessions/`, `history` |

Every verb is written once against the adapter and runs on either runtime — satisfying the "compatible codex/claude"
requirement at the *capability* level, not just the frontmatter.

## 4. Capability surface (verbs) — `project-meta`-shaped

| Verb | Mode | What it does | Origin | Status |
|---|---|---|---|---|
| `create <name> [--runtime claude\|codex] [--isolated] [--seed-from]` | editing | scaffold a profile: dir, plugins symlink, launcher, optional memory seed | **absorbed from `profile-creator`**, now dual-runtime | **live 1.0.0** (2026-06-11) |
| `status` | read-only | inventory all profiles × runtimes: skills, plugins, hooks, MCP servers, launcher health, **context-tax estimate** | new | **approved v1.1 (DASH-039)** |
| `audit` | read-only | hygiene: stale/broken hooks, dead launchers, orphaned plugins, skills over context budget, unknown MCP, hook-provenance/CVE flags, `known_marketplaces.json` integrity; **first-class check: four-way consistency** (installed_plugins ↔ enabled-plugins ↔ cache dirs ↔ local-scope@home spec); context-tax report; findings as ready-to-run `board.py inbox-add` lines | new | **approved v1.1 (DASH-039)** |
| ~~`drift`~~ | ~~read-only~~ | ~~cross-profile diff vs a baseline; surfaces #58815 `CLAUDE.md` bleed + marketplace corruption~~ | ~~new~~ | **folded into `audit`** as cross-profile section (2026-06-11 verdict; shared `~/.claude-shared` store eliminated most surface) |
| ~~`reconcile`~~ | ~~editing (synchronous user gate)~~ | ~~apply drift fixes / re-sync the shared baseline across profiles~~ | ~~new~~ | **superseded by `audit --emit-fix` v1.2 (DASH-040)**; emits reviewable, idempotent, snapshot-guarded fix script; never auto-applies; transactional shape borrowed from openclaw-devops |
| ~~`settings enable/disable`~~ | ~~editing~~ | ~~toggle global capabilities/hooks~~ | ~~new~~ | **cut** — update-config/`/config` own leaf edits; cross-profile toggles ride the emitted fix script |
| `track` | editing | turn a config root into a **secret-safe dotfiles git repo** — the §6 safety prerequisite | new | **deferred** — snapshot ledger (v1.1) covers rollback; revisit if diff-review demand materialises; secret-safety MUSTs stay |
| `deliver` | read-only | pre-change review | reuses `project-meta deliver` | **unchanged** |

Read-only verbs never edit; editing verbs gate on dry-run + `deliver`. `reconcile` is superseded by `audit --emit-fix` (see above).

## 5. Reuse map (derived design — resolver + thin floor, no vendoring)

**Reuse `project-meta` via the runtime resolver** (`references/shared-cli-delegation.md`):

| From `project-meta` | Used for |
|---|---|
| `provenance.py`, `repo_memory.py` | memory CRUD on the dotfiles repo's `CLAUDE.md`/`AGENTS.md`/`rules/` — **as one writer among several** (CC auto-memory under `~/.claude/projects/*/memory/`, methodology plan docs, user `CLAUDE.md`); global-meta audits + promotes across lanes, never claims sole authorship (AP-COORD-7) |
| `render_host_manifests.py` | the `CLAUDE.md` ↔ `AGENTS.md` mirror = the dual-runtime memory sync, for free |
| `render_user_preferences.py` | global preference questionnaire (a global `USER.md`) |
| `validate_target_harness.py` | generalized to validate a config root |
| `install_codex_hooks.py` | the Codex hook backing |
| `writing-skills.md` + skill-critic suite | the authoring gate for `global-meta` itself |

**Absorb from `profile-creator`:** `create_profile.py` (generalized with the adapter) + `launcher-{simple,isolated}.sh` +
`references/create-profile.md`. The hard guards carry over (see §6).

**Coordination principle (AP-COORD-7):** global-meta owns *policy* (when to coordinate, what becomes durable) and delegates
*mechanism* to the runtime engine — it never re-implements orchestration, references the engine generically ("scripted-engine
tier") to survive renames, and cannot enable it unilaterally (the engine is user-gated).

**Genuinely new (small surface):**
- `config_root_audit.py` — inventory / hygiene / drift engine (lists profiles, skills, plugins, hooks, MCP; estimates context
  tax; cross-profile diff)
- `dotfiles_git.py` — `git init` with the secret-safe `.gitignore`, then memory/mirror wiring
- references: `config-root-model.md`, `profile-lifecycle.md`, `drift-and-reconcile.md`, `inventory-and-context-tax.md`,
  `dotfiles-git-safety.md`, `security-audit.md`
- templates: secret-safe `.gitignore`, per-runtime adapter config

## 6. Safety invariants (MUST — global blast radius)

- **MUST never git-commit secrets.** The `.gitignore` template excluding auth/creds/sessions/transcripts/logs is applied
  *before* `track` ever runs `git add` — same discipline as `project-meta`'s `USER.md`-gitignore gotcha.
- **MUST preserve `profile-creator`'s guards, generalized to Codex:** never run `claude plugin marketplace add/update` from a
  non-shared profile (corrupts `known_marketplaces.json`); plugin admin only via `ccplug` / its Codex equivalent. `global-meta`
  becomes the enforcement home of memory `multiclaude-marketplace-guard`.
- **MUST gate every editing verb** behind dry-run + `deliver`; `reconcile` is a synchronous user gate.
- **MUST flag, never auto-trust, hooks** found during `audit` (machine-wide RCE surface, CVE-2025-59536). Report provenance;
  do not execute discovered hooks.
- **MUST keep the validator's git-tree assumption honest:** `validate`/`drift`/`reconcile` require the config root be `track`ed
  first (git working tree), or they run in degraded read-only mode and say so.
- **MUST treat durable memory as a multi-writer set.** CC auto-memory (`~/.claude/projects/*/memory/`) is a native co-writer;
  `audit`/`reconcile` report and dedup across lanes but never overwrite auto-memory or claim sole authorship (AP-COORD-7).

## 7. Skill arbitration

| Request shape | Owner | `global-meta`'s role |
|---|---|---|
| Create / audit / reconcile / track a user config root or profile (Claude or Codex) | **`global-meta`** | acts |
| Repo harness (`.claude/`, `AGENTS.md`, repo memory) | `project-meta` | defer; `global-meta` *reuses* its engine (own policy, delegate mechanism — AP-COORD-7) |
| Edit a single `settings.json` value/hook in isolation | `update-config` | delegate the leaf edit |
| Create one Claude profile (legacy `/profile-creator`) | **`global-meta create`** | **absorbs**; `profile-creator` deprecated |
| Multi-agent orchestration *execution* (subagent fan-out, scripted workflows, effort tier) | **the runtime engine** (Workflow / "ultracode"; Codex Agents-SDK) — not a skill | own *policy*, delegate *execution*; recommend/prepare but cannot enable it (user-gated); never re-implement — AP-COORD-7 |
| Intra-task SE *method* (brainstorm→plan→TDD→review→verify) | **methodology plugin** (e.g. `superpowers`) — external, not bindable | defer intra-task; reclaim only global-config harness + skill authoring; assume its bootstrap is mandatory/uncontrollable — be additive |

## 8. `profile-creator` deprecation path (decision: absorb + deprecate)

1. ~~Move `create_profile.py` + launcher templates + `create-profile.md` into `skills/global-meta/`, generalized with the adapter.~~ **DONE** (2026-06-11, global-meta 1.0.0).
2. ~~Prove `global-meta create` parity against the existing 5 profiles in `--dry-run`.~~ **DONE** (2026-06-11, global-meta 1.0.0).
3. ~~Reduce `skills/profile-creator/SKILL.md` to a one-screen **deprecation stub** that routes to `global-meta create` (keeps the `/profile-creator` muscle-memory working for one release), and drop it from `marketplace.json` after a deprecation window.~~ **DONE** — stub removed and `profile-creator` dropped from `marketplace.json` (2026-06-11, marketplace 2.0.0).
4. ~~Update every peer skill's arbitration row that points at `profile-creator` (e.g. `project-meta`'s table) to point at `global-meta`.~~ **DONE** (2026-06-11, marketplace 2.0.0).

## 9. Build & ship plan

1. Scaffold from `templates/SKILL.template.md`; write `RuntimeAdapter` + the two new scripts.
2. Absorb `create_profile.py`; dual-runtime it; dry-run parity check.
3. Run the critic gate: `skill_architecture_lint.py`, `determinism_gap_scan.py`, `cross_skill_redundancy.py`,
   `trigger_collision_check.py`, `pressure_test_skill.py` — all PASS/WARN before publish.
4. Add `examples/` (a `status` + `audit` run over a sample config root).
5. Register in `marketplace.json` (`compat:[claude-code, codex]`, `published:[claude-marketplace]`); deprecate
   `profile-creator`; bump versions; reinstall to reload (memory `plugin-reload-needs-reinstall`).
6. Add proposed anti-patterns AP-GLOB-1..3 to `references/anti-patterns.md`.

## 10. Open questions (defer until build)

- Codex's exact plugin/marketplace model vs Claude's `known_marketplaces.json` — confirm the Codex-side corruption guard shape
  before writing `ccodexplug`.
- Whether the global preference questionnaire should be a single `USER.md` per config root or one shared across profiles.
- Context-tax thresholds: surface-only (report) in v1; promote to a `strict`-profile gate later. *(2026-06-11 verdict: context-tax report is included in `audit` v1.1; `strict` gate deferred.)*
- *(2026-06-11 verdict)* Drift detection surface: answered — `drift` verb folded into `audit` cross-profile section; the shared `~/.claude-shared` store eliminated most cross-profile drift surface; per-profile settings/CLAUDE.md/hooks divergence is the remaining scope.

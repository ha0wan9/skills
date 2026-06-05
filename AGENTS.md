# skills marketplace

`AGENTS.md` is the agent-facing routing file for this Claude Code plugin marketplace. It hosts skills under `skills/`, including [`project-meta`](skills/project-meta/), [`dl-research`](skills/dl-research/), [`deep-survey-bfs`](skills/deep-survey-bfs/), [`profile-creator`](skills/profile-creator/), [`calendar-crud-workflow`](skills/calendar-crud-workflow/), and [`sketch-asset-generator`](skills/sketch-asset-generator/). Each is independently installable via `.claude-plugin/marketplace.json`.

## Read Order

1. Read this file (`AGENTS.md`) for repo layout and routing.
2. Inspect [`README.md`](README.md) lightly — read it selectively at cold start instead of eagerly loading the whole file. Use the bounded doc context extractor (see below) when only a section is needed.
3. Read the relevant skill's `SKILL.md` when a task touches that skill.
4. Read [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) when adding, removing, or renaming a plugin.
5. Check local `USER.md` only if it exists at the repo root; it is local-only and Git-ignored.

## Repo Memory Surface

| Path | Purpose |
|---|---|
| `README.md` | shared/user-facing entrypoint for the marketplace |
| `AGENTS.md` (this file) | agent-facing routing for the marketplace |
| `.claude-plugin/marketplace.json` | plugin manifest; canonical source for installable plugin names and skill locations |
| `skills/project-meta/` | full project-meta skill, including its own SKILL.md, references, templates, agents/openai.yaml |
| `skills/dl-research/` | full dl-research skill, including phases, modes, references, templates, agents/openai.yaml |
| `skills/deep-survey-bfs/` | full deep-survey-bfs skill, including phases, references, templates, scripts (`arxiv_search.py`, `coverage_check.py`, `claims_validate.py`, `bias_audit.py`), agents/openai.yaml |
| `skills/profile-creator/` | multi-Claude profile creation skill with shared plugin-store conventions |
| `skills/calendar-crud-workflow/` | calendar event CRUD workflow skill for stable calendars, title prefixes, searchable tags, source links, and safe batch operations |
| `skills/sketch-asset-generator/` | extraction-first design-system asset packs from sketches or source UI; direct token/SVG/code extraction by default, GPT Image fallback; ships `scripts/validate_asset_pack.py` and `scripts/render_contact_sheet.py`, schema, references, and example fixtures |
| `scripts/validate_project_meta.py` | dev-only validator; not shipped to install. Validates the project-meta skill content under `skills/project-meta/` |

## Bounded Doc Loading

For long shared docs, prefer the heading-first extractor from the project-meta skill:

```bash
python3 skills/project-meta/scripts/extract_doc_context.py README.md --index
python3 skills/project-meta/scripts/extract_doc_context.py README.md --heading "Install" --query "git repo" --within-lines 80 --max-lines 40
```

This is the same `scripts/extract_doc_context.py` that ships with the project-meta plugin. It uses the Python standard library only.

## User Preference Rendering

Skills here do not require local `USER.md` to operate, but the project-meta skill provides `scripts/render_user_preferences.py` for projects that adopt local-only user preferences. Render selected presets directly into ignored local `USER.md`:

```bash
python3 skills/project-meta/scripts/render_user_preferences.py --target-root <repo> --reset
```

Do not commit `USER.md`. The repo's top-level `.gitignore` and the project-meta skill's `.gitignore.template` both protect it.

## Shared Harness CLIs

`project-meta` is the canonical home for cross-skill harness logic. Other skills reuse it by path (dev-time) or by resolving the install at runtime — they do not vendor copies. Canonical contract: `skills/project-meta/references/shared-cli-delegation.md`.

- `scripts/provenance.py` — frontmatter parse/validate/stamp (the `instantiated_from`/`source_reference`/`last_reviewed` trio). Skills must not re-roll frontmatter parsing; `skill_architecture_lint.py` WARNs when they do.
- `scripts/repo_memory.py` — runtime memory read leg, write-back gate, write, validate. The `SessionStart`/`Stop` hooks delegate to it; the Memory Contract it backs is in `references/repo-memory-crud.md#memory-contract`.
- `scripts/dispatch_ledger.py` — multi-agent dispatch audit ledger (record/validate/query) + the mandatory-dispatch `gate` the `Stop` hook runs. Enforcement/audit backing for the Task Dispatch paradigm in `references/multi-agent-protocols.md#mechanical-enforcement` (not a dispatch engine).
- `scripts/worktree_audit.py` — read-only gather+classify leg of the Worktree Trim Contract (`references/worktree-hygiene.md`). Backs the session-start worktree sweep below; never removes/merges/commits.

## Session Start: Worktree Trim Contract

This repo accumulates `.claude/worktrees/*` from agent runs. Near session start, before substantive work, run the Worktree Trim Contract:

```bash
python3 skills/project-meta/scripts/worktree_audit.py --target-root . --base main
```

Then **trim stale** (merged + clean → `git worktree remove` + `git branch -d`), **surface in-progress** (any uncommitted/untracked worktree — never trim; it may hold the only copy of unsaved work), and **route mergeable** (clean branch with unmerged commits → review+merge via the ship flow, not a blind merge). Full disposition table and safety invariants: [`skills/project-meta/references/worktree-hygiene.md`](skills/project-meta/references/worktree-hygiene.md).

## Working On The Marketplace

When editing this repo as agent work:

- For changes to the `project-meta` skill, run the dev validator after edits:
  ```bash
  python3 scripts/validate_project_meta.py
  ```
- For changes to `dl-research`, the skill ships its own ledger validator at `skills/dl-research/scripts/validate_ledger.py`; run it against any modified `runs.jsonl` fixture you produce while editing.
- For changes to `marketplace.json`, verify the JSON parses, that every `skills:[...]` path resolves to a directory containing a `SKILL.md`, and that every plugin `name` is unique.
- Treat shared docs (this `AGENTS.md`, `README.md`) as primary documentation. Edits to user-facing behavior require a pre-commit delivery; see `skills/project-meta/references/documentation-delivery.md` for the delivery contract.

## Workflow Preference: Validated Edit → Ship → Reload

Once an edit to this repo is **validated**, ship it end-to-end without waiting for further
prompting: commit → open PR → fresh-context review → merge-if-clean → reload the affected
plugin locally. "Validated" here is a two-gate bar — **both** must hold before any merge:

1. **Validator gate** — `scripts/ship_plugin.sh validate` exits 0 (marketplace.json sanity
   always, plus `validate_project_meta.py` when `project-meta` changed, plus the dl-research
   ledger validator when a `runs.jsonl` fixture changed).
2. **Fresh-review gate** — a **fresh-context** review agent (dispatch via the Agent tool,
   e.g. the `Explore`/general reviewer or `/code-review`) reads the PR diff and returns
   **no blocking findings**. The reviewing agent must not be this working session — spawn a
   clean one so the review is independent (see `skills/project-meta/references/multi-agent-protocols.md`).

Merge policy is **review, merge if clean**: if the fresh review surfaces a blocking finding,
**stop — do not merge**; report the findings and let the fix loop run again from gate 1.

The deterministic legs are scripted in [`scripts/ship_plugin.sh`](scripts/ship_plugin.sh);
the agent owns the two gates. Canonical sequence:

```bash
scripts/ship_plugin.sh validate                 # gate 1 — abort the whole flow if non-zero
scripts/ship_plugin.sh open "<concise PR title>"  # commit (if needed) + push + open PR
# gate 2: dispatch a FRESH review agent over the PR diff; merge only if it comes back clean
scripts/ship_plugin.sh land                      # merge-if-clean, then reload changed plugins
```

`land` re-checks GitHub mergeability and refuses on `DIRTY`/`BEHIND`/`BLOCKED`; it then runs
`claude plugin marketplace update ha0wan9-skills` and **reinstalls** each changed plugin —
`claude plugin uninstall <plugin>@ha0wan9-skills` (best-effort) then `claude plugin install
<plugin>@ha0wan9-skills` (use `scripts/ship_plugin.sh changed-plugins` to see the set).
Reinstall rather than `claude plugin update`, because `update` is a no-op when the manifest
version is unchanged (it reports "already at the latest version" and the materialized cache
copy stays stale), so same-version edits would never reload. The uninstall is best-effort (a
not-yet-installed plugin fails it harmlessly); the **install is load-bearing** — if it fails
after a successful uninstall the plugin is left removed locally, so `reload` exits non-zero
and refuses to report success. Plugin names in `installed_plugins.json` are
marketplace-qualified, so the `@ha0wan9-skills` suffix is required — the bare name fails with
"not found". Plugin reloads require a Claude Code restart to take effect — surface that
reminder after a successful land.

This is a personal workflow default for repo edits; for anything outside the validated-edit
loop (release tagging, bulk refactors, destructive history rewrites) fall back to asking first.

## Adding A New Skill

1. Create `skills/<new-skill-name>/SKILL.md` with name + description frontmatter. The `SKILL.md` `description` is the **canonical** description for the skill.
2. Add a plugin entry to `.claude-plugin/marketplace.json` with `name`, `version`, `description`, `source: "./"`, `strict: false`, and `skills: ["./skills/<new-skill-name>"]`. The plugin `description` MUST be copied **verbatim** from the skill's `SKILL.md` frontmatter — do not paraphrase. This keeps install-time discovery and trigger-time matching in sync (drift here is how the manifest goes stale).
3. Update this `AGENTS.md` and `README.md` with the new skill in the routing table, and refresh the marketplace `metadata.description` to mention the new plugin.
4. If the new skill needs a dev validator, place it under top-level `scripts/`, not inside `skills/<name>/`, so it is not shipped.
5. When a skill's `SKILL.md` description changes, re-copy it into the matching `marketplace.json` plugin `description` in the same change.

## Mirrors

The marketplace itself does not maintain `CLAUDE.md` or `.github/copilot-instructions.md` mirrors; canonical memory lives here in `AGENTS.md`. Each skill may carry its own mirror or memory file inside `skills/<name>/` as needed by that skill's own design.

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

## Working On The Marketplace

When editing this repo as agent work:

- For changes to the `project-meta` skill, run the dev validator after edits:
  ```bash
  python3 scripts/validate_project_meta.py
  ```
- For changes to `dl-research`, the skill ships its own ledger validator at `skills/dl-research/scripts/validate_ledger.py`; run it against any modified `runs.jsonl` fixture you produce while editing.
- For changes to `marketplace.json`, verify the JSON parses, that every `skills:[...]` path resolves to a directory containing a `SKILL.md`, and that every plugin `name` is unique.
- Treat shared docs (this `AGENTS.md`, `README.md`) as primary documentation. Edits to user-facing behavior require a pre-commit delivery; see `skills/project-meta/references/documentation-delivery.md` for the delivery contract.

## Adding A New Skill

1. Create `skills/<new-skill-name>/SKILL.md` with name + description frontmatter. The `SKILL.md` `description` is the **canonical** description for the skill.
2. Add a plugin entry to `.claude-plugin/marketplace.json` with `name`, `version`, `description`, `source: "./"`, `strict: false`, and `skills: ["./skills/<new-skill-name>"]`. The plugin `description` MUST be copied **verbatim** from the skill's `SKILL.md` frontmatter — do not paraphrase. This keeps install-time discovery and trigger-time matching in sync (drift here is how the manifest goes stale).
3. Update this `AGENTS.md` and `README.md` with the new skill in the routing table, and refresh the marketplace `metadata.description` to mention the new plugin.
4. If the new skill needs a dev validator, place it under top-level `scripts/`, not inside `skills/<name>/`, so it is not shipped.
5. When a skill's `SKILL.md` description changes, re-copy it into the matching `marketplace.json` plugin `description` in the same change.

## Mirrors

The marketplace itself does not maintain `CLAUDE.md` or `.github/copilot-instructions.md` mirrors; canonical memory lives here in `AGENTS.md`. Each skill may carry its own mirror or memory file inside `skills/<name>/` as needed by that skill's own design.

# Example: `/project-meta init` on a toy repo

**Skill version:** 1.1.0
**Command:** `/project-meta init`
**Repo fixture:** `toy-weather-cli` — a small Python CLI with one script, a `pyproject.toml`, and no prior agent harness.

## What init produced

Running `/project-meta init` on `toy-weather-cli` asked for a HARNESS_PROFILE preset (`minimal`), confirmed the canonical memory file convention (`AGENTS.md` for agent-facing, `CLAUDE.md` as mirror), and created:

| Artifact | Path in target repo | Source template |
|---|---|---|
| Canonical memory | `AGENTS.md` | `templates/SKILL.template.md` (custom) |
| User preferences | `USER.md` (git-ignored) | `USER.template.md` rendered via `render_user_preferences.py` |
| Delegation rules | `agents/delegation.md` | `templates/delegation.md` |
| Pre-commit delivery | `agents/pre-commit-delivery.md` | `templates/pre-commit-delivery.md` |

Mirror (`CLAUDE.md`) was generated from `AGENTS.md` via `scripts/render_host_manifests.py`.

## Coverage

- Provenance frontmatter: verified present on all instantiated artifacts.
- `.gitignore` patched to exclude `USER.md`.
- Mirror sync: `CLAUDE.md` regenerated and matches canonical.

## Re-rendering

All artifacts in this example were produced by the init recipe. To re-render against a fresh fixture, run:

```bash
python3 scripts/skill_architecture_lint.py skills/project-meta
python3 scripts/trigger_collision_check.py skills/project-meta
```

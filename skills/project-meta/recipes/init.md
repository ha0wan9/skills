# Recipe: init

Cold-start or repair a project's agent harness.

## When to load

- User invokes `/project-meta init`
- A repo lacks an `AGENTS.md` / `CLAUDE.md` and the user wants harness setup
- An existing harness is incoherent enough that a re-bootstrap is cheaper than incremental repair

## Mode

**editing** — creates or repairs canonical memory files, mirrors, templates, and (when opted in) hooks / phase-lock contracts.

## Required references

Load these in order, only when the corresponding step fires:

1. [`references/project-lifecycle.md`](../references/project-lifecycle.md) — questionnaire, presets, project-type classification, artifact instantiation rules
2. [`references/repo-memory-structure.md`](../references/repo-memory-structure.md) — monolith vs loader+topical decision, READ ORDER conventions
3. [`references/repo-memory-crud.md`](../references/repo-memory-crud.md) — file CRUD operations
4. [`references/documentation-delivery.md`](../references/documentation-delivery.md) — pre-commit delivery contract
5. [`references/execution-policy.md`](../references/execution-policy.md) — only when the target will host bounded-execution agents (Codex-class workers)

Optional, when the user passes feature flags:

- `--workflow phase-lock`: load [`templates/phase-lock-contract.md`](../templates/phase-lock-contract.md)
- `--hooks`: load [`templates/hooks/README.md`](../templates/hooks/README.md)
- `--multi-host`: invoke `scripts/render_host_manifests.py`

## Workflow

1. **Detect** existing conventions without assuming completeness:
   - `README.md` and its structure
   - `AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/`
   - `USER.md` (do not assume it exists)
   - `.gitignore` rules for `USER.md` / `USER.template.md`
   - existing `agents/` directory and any topical files

2. **Resolve canonical-vs-mirror** per the tool-awareness rule (see [`references/mirrors-and-updates.md`](../references/mirrors-and-updates.md)):
   - Claude Code primary → `CLAUDE.md` canonical, `AGENTS.md` mirror
   - Codex/GPT primary → `AGENTS.md` canonical, `CLAUDE.md` mirror
   - Unknown → default to `AGENTS.md` canonical

3. **Run the preference questionnaire** from `USER.template.md`:
   - Ask which preset (Minimal / Structured / Strict / Secure / Custom)
   - Walk through the per-item checklist
   - Render the result into `<target>/USER.md`. Prefer `scripts/render_user_preferences.py --target-root <repo>` when available.
   - Do not depend on existing `USER.md`. Do not copy `USER.template.md` into the target repo.

4. **Create or repair the canonical entrypoint**:
   - Write the project-memory loader/router to the canonical filename resolved in step 2
   - Keep it short — a routing map plus global guardrails (AP-MEM-1)
   - Reference `agents/<topical>.md` files only after the topical files exist

5. **Instantiate templates** as needed:
   - `templates/delegation.md` → `agents/delegation.md` (when multi-agent work is anticipated)
   - `templates/execution-rules.md` → `agents/execution-rules.md` (when bounded-execution agents will operate)
   - `templates/pre-commit-delivery.md` → `agents/pre-commit-delivery.md` (always)
   - `templates/readme-structure-map.md` → `agents/readme-structure.md` (when README is structurally important)
   - `templates/project-artifact-manifest.md` → `agents/project-artifact-manifest.md` (always; tracks instantiated artifacts)
   - `templates/memory-writeback-check.md` → `agents/memory-writeback-check.md` (always)
   - Each instantiated artifact MUST carry the YAML provenance frontmatter (`instantiated_from`, `source_reference`, `owner`, `review_policy`, `last_reviewed`).

6. **Optional opt-ins**:
   - `--workflow phase-lock`: instantiate `templates/phase-lock-contract.md` → `agents/phase-lock-contract.md`; create `.harness/phase-state.json` from the seed; create `.harness/gates/{brainstorm,plan,implement,review,finish}.sh` stubs.
   - `--hooks`: copy `templates/hooks/scripts/*.sh` to `<target>/.claude/hooks/`; merge `templates/hooks/settings.json.fragment` into `<target>/.claude/settings.json`. Set `HARNESS_PROFILE=standard` default.
   - `--multi-host`: run `python3 scripts/render_host_manifests.py --target-root <repo>` to emit `.codex/`, `.opencode/`, `gemini-extension.json`, etc.

7. **Wire `.gitignore`** for `USER.md` (and the accidental root `USER.template.md`) before any of those files exist. The `.gitignore.template` from this skill or an equivalent rule must merge in.

8. **Validate**:
   - Run `python3 scripts/validate_target_harness.py <repo>` — every check should be PASS or WARN. FAIL means the init didn't complete; loop back.
   - All instantiated artifacts have provenance frontmatter.
   - Mirror files (if generated) carry the generation banner.

9. **Pre-commit delivery**:
   - Render the standard delivery sections (user-facing docs, agent-facing docs, behavior/trigger changes, validation, commit scope).
   - Wait for user approval before committing.

## Output contract

Produce a delivery summary covering:

- Project type and detected conventions
- Files created or repaired
- Preference preset selection or resulting local `USER.md` (questionnaire transcript or summary)
- Offered execution-rules instantiation (when applicable)
- Optional capability install summary (phase-lock, hooks, multi-host)
- Validation result, including the `validate_target_harness.py` output
- Pre-commit delivery sections

## Anti-patterns

- AP-LIFE-1: Running init without the questionnaire — silently picks defaults the user didn't choose.
- AP-MEM-1: Bootstrap-as-encyclopedia — keep the canonical entrypoint short.
- AP-VAL-2: Skipping `validate_target_harness.py` — the validator is part of the contract, not optional.
- Committing inside `init` — always wait for user approval after delivery.

## Reset path

When the user asks to reset or change `USER.md` options:

```bash
python3 scripts/render_user_preferences.py --target-root <repo> --reset
```

Re-runs the questionnaire and re-renders the local `USER.md`. Skips the rest of init.

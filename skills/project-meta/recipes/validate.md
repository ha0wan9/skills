# Recipe: validate

Run available validation checks against the current harness.

## When to load

- User invokes `/project-meta validate`
- After `/project-meta init` or `/project-meta deliver` (sanity check before commit)
- Pre-commit hook can invoke this directly

## Mode

**read-only by default** — runs validators, reports findings, does not edit files. Switch to `init` / `audit` with explicit consent if repair is requested.

## Required references

None by default. Lazy-load when a failed check needs context:

- `references/harness-engineering.md` — the audit-checklist semantics
- `references/repo-memory-structure.md` — when memory layout failures surface
- `references/anti-patterns.md` — when a failure pattern matches a named AP-XXX-N
- `references/skill-critics.md` — when validating a skill or the marketplace (the deterministic critic suite)

## Workflow

1. **Run `validate_target_harness.py`** against the current repo:
   ```bash
   python3 scripts/validate_target_harness.py [target_repo]
   ```
   The validator is std-lib only and dependency-free. Each check is PASS, WARN, or FAIL. The script auto-detects the repo root from `.git` if `target_repo` is omitted.

2. **Run capability-specific validators** when their artifacts are present:
   - **Phase-lock contract installed**: run `phase_lock_check.py --harness-dir .harness --require-pass` to confirm gate state is consistent. Failure indicates a stale state file or a missing gate.
   - **Hooks installed**: verify each hook script in `.claude/hooks/` passes `bash -n` syntax check. Verify `settings.json` parses.
   - **Multi-host mirrors present**: run `render_host_manifests.py --target-root . --dry-run` and diff the dry-run output against the on-disk mirrors. Drift = failure.
   - **Target is a skill or marketplace**: run the deterministic critic suite — `skill_architecture_lint.py`, `trigger_collision_check.py`, `context_cost_estimate.py`, `determinism_gap_scan.py`, `cross_skill_redundancy.py` — against the skill dir or marketplace root. Each exits `0/1/2`; treat exit 1 as FAIL. These five are a **budget-independent floor** and run directly on any runtime (`python3 scripts/<critic>.py .`, no Workflow required); only reviewer-agent depth may scale to a token budget. See `references/skill-critics.md` for what each enforces.
   - **Memory files present**: run `memory_staleness.py --target-root <repo>` to check for referentially stale path citations in AGENTS.md/CLAUDE.md and `agents/*.md` topical files. STALE findings are advisory (do not flip validate to exit 1); exit 1 means at least one cited path has gone missing and should be updated.

3. **Run repo-defined verifiers** when the repo provides one:
   - `.harness/verify.sh` (or equivalent project-defined entrypoint)
   - tests / linters / type-checkers as named in the project memory

4. **Aggregate findings**:
   - Count PASS / WARN / FAIL.
   - For each FAIL, identify the likely owner (template, reference, script, instantiated artifact, mirror, hook).
   - For each WARN, surface the exact remediation.

## Output contract

Structured summary covering:

- **Commands run**: each validator command with its exit code
- **PASS / WARN / FAIL counts**
- **Failed checks**: each with the failing rule, the source file, and the suggested next step
- **Drift findings**: any mirror that diverges from canonical
- **Repair suggestion**: which command to run next (`init` for missing artifacts; `audit` for structural issues)

Do not commit, edit, or auto-fix during `validate`. Report only.

## Editing escape hatch

If the user explicitly asks `validate` to repair (e.g. "validate and fix"), promote to `init` (for missing artifacts) or `audit` (for structural issues) and run the editing path with explicit user consent. Never mix read-only and editing modes silently — the workflow boundary is the contract.

## Anti-patterns

- AP-VAL-1: Reporting "ENFORCED" on a rule that has no validator. If the rule isn't mechanically checkable, mark it WARN with the actual evidence ("found in prose; not enforced by script").
- AP-VAL-2: Skipping `validate_target_harness.py` because "I already know the state". The validator catches drift the human eye misses.
- Mixing validation + repair in one invocation. The user should see findings before edits.

## Exit semantics

- exit 0: all checks PASS or WARN with explicit acknowledgement
- exit 1: at least one FAIL
- exit 2: validator could not run (missing dependency, bad path)

Pre-commit hooks should treat exit 1 as a blocker.

# Shared CLI Delegation

How a dependent skill reuses `project-meta`'s shared CLIs at runtime without
vendoring a copy. Use this reference when authoring or auditing a skill that
needs the shared memory / provenance tooling.

## Canonical Toolkit

The single source of truth for cross-skill harness logic lives in
`project-meta/scripts/`:

| Script | Layer | Purpose |
|---|---|---|
| `provenance.py` | dev + runtime | frontmatter parse / validate / stamp (the provenance trio) |
| `repo_memory.py` | runtime | memory read leg, write-back gate, write, validate |
| `extract_doc_context.py` | dev | bounded heading-first doc loading |
| `skill_architecture_lint.py`, `determinism_gap_scan.py`, `cross_skill_redundancy.py`, … | dev | marketplace-repo checks |

Do not fork these into other skills. Fix the canonical copy here.

## Dev-Time vs Runtime — Different Distribution

- **Dev-time tooling** (lint, validate, scan, doc extraction) runs against
  *this marketplace repo* during development/CI. Other skills and `AGENTS.md`
  call it **by path** (`python3 skills/project-meta/scripts/<x>.py`). No
  distribution problem — it never has to ship inside an installed plugin.
- **Runtime code** (`repo_memory.py`, `provenance.py` when stamping in a target
  repo) runs on the end user's machine *after* a skill is installed. The
  marketplace has **no auto-install of dependencies**, and git submodules are
  **not** materialized by plugin install (anthropics/claude-code#17293). So a
  dependent skill cannot assume a sibling skill's files are present — it must
  either resolve `project-meta` at runtime (below) or carry a thin floor.

## Runtime Resolver (the scale-proof mechanism)

A dependent skill resolves the installed `project-meta` directory in priority
order, then delegates. This mirrors `templates/hooks/scripts/verify-before-stop.sh`,
which already resolves `phase_lock_check.py` the same way.

```bash
# Resolve project-meta's installed location. Override via PROJECT_META_DIR.
# Canonical executable copy of this resolver: templates/hooks/scripts/verify-before-stop.sh
pm_dir="${PROJECT_META_DIR:-$HOME/.claude/skills/project-meta}"
pm_mem="$pm_dir/scripts/repo_memory.py"

if [[ -f "$pm_mem" ]]; then
  python3 "$pm_mem" --target-root . read
else
  # Thin floor: project-meta not installed. State the minimum inline so the
  # skill still works standalone — read the canonical entrypoint, decide a
  # write-back at close. See the Memory Contract in project-meta's
  # references/repo-memory-crud.md (#memory-contract).
  echo "[memory] read CLAUDE.md or AGENTS.md before substantive work." >&2
fi
```

Rules:

- **Resolve, never vendor.** Calling the canonical script by resolved path
  keeps one implementation. Copying it in creates drift that lint must police.
- **Always carry a thin floor.** Because install may not include `project-meta`,
  the `else` branch must state the minimum protocol inline so the skill is not
  broken when the dependency is absent.
- **Declare the dependency** in the skill's Skill Arbitration / delegation row
  pointing at `project-meta`, and route harness work there.

## When Vendoring Is Actually Required

Only when a skill must run the runtime code with `project-meta` **absent** and
the thin floor is insufficient. Then materialize the file via `git subtree` or
a CI vendor step (NOT a submodule) and add a parity check to
`skill_architecture_lint.py`. Defer this until a real need appears — the
resolver + thin floor covers the normal case.

## Minimal-API Guardrail

The shared surface is intentionally small: parse/validate/stamp frontmatter,
and the four `repo_memory` verbs. Resist adding speculative parameters — the
abstraction is being derived from only a handful of call sites, so keep it to
primitives that are clearly stable. Grow it when a third real caller needs the
same thing, not before.

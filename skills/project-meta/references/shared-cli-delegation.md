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

A dependent skill resolves the installed `project-meta` directory by probing the
known locations in priority order, then delegates. **`~/.claude/skills/project-meta`
alone is not enough** — that is the *personal-skill* path; a marketplace **plugin**
install lands under `~/.claude/plugins/`, so the resolver must probe those too or
it silently falls to the thin floor on the most common install. Verified install
layouts (Claude Code 2.1.x, both cache generations):

- personal skill: `~/.claude/skills/project-meta/` (Codex: `~/.codex/skills/project-meta/`)
- plugin (marketplace checkout, full-repo clone — all versions): `~/.claude/plugins/marketplaces/<marketplace>/skills/project-meta/` (Codex: `~/.codex/plugins/marketplaces/<marketplace>/skills/project-meta/`)
- plugin (legacy full-repo-copy cache, pre-marketplace-3.0): `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills/project-meta/` (e.g. `<plugin>` = `global-meta` when bundled — the cache segment is the *plugin* name, not `project-meta`; Codex: `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/skills/project-meta/`)
- plugin (scoped cache, marketplace ≥3.0): `~/.claude/plugins/cache/<marketplace>/project-meta/<version>/` — under scoped sources (`source: "./skills/project-meta"`), the cache root **is** the skill root; no nested `skills/project-meta/` segment (Codex: `~/.codex/plugins/cache/<marketplace>/project-meta/<version>/`)

Claude Code and Codex install into parallel `~/.claude/` and `~/.codex/`
trees, so the resolver probes both runtimes' four tiers (8 globs total).

```bash
# Canonical executable copy: templates/hooks/scripts/verify-before-stop.sh
# (resolve_project_meta). The sentinel-file check skips older installed copies
# that lack the script, so the first match is always usable.
pm_dir=""
for c in "${PROJECT_META_DIR:-}" \
         "$HOME/.codex/skills/project-meta" \
         "$HOME/.claude/skills/project-meta" \
         "$HOME"/.codex/plugins/marketplaces/*/skills/project-meta \
         "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
         "$HOME"/.codex/plugins/cache/*/*/*/skills/project-meta \
         "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta \
         "$HOME"/.codex/plugins/cache/*/project-meta/* \
         "$HOME"/.claude/plugins/cache/*/project-meta/*; do
  [ -n "$c" ] && [ -f "$c/scripts/repo_memory.py" ] && { pm_dir="$c"; break; }
done
if [ -n "$pm_dir" ]; then
  python3 "$pm_dir/scripts/repo_memory.py" --target-root . read
else
  # Thin floor: project-meta not found. State the minimum inline so the skill
  # still works standalone. See the Memory Contract in project-meta's
  # references/repo-memory-crud.md (#memory-contract).
  echo "[memory] read CLAUDE.md or AGENTS.md before substantive work." >&2
fi
```

> **Most robust:** have `/project-meta init --hooks` bake the resolved
> `PROJECT_META_DIR` into the target repo's `.claude/settings.json` `env` at
> init time (it knows its own location via `$CLAUDE_PLUGIN_ROOT` then). The glob
> probe above is the zero-config fallback; an explicit `PROJECT_META_DIR` is
> immune to future changes in Claude Code's plugin directory layout.

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

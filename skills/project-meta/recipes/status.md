# Recipe: status

Inspect the current harness state without editing files.

## When to load

- User invokes `/project-meta status`
- User asks "what's the state of this repo's harness?" or similar
- Before deciding whether `init` / `validate` / `audit` is the right next step

## Mode

**read-only** — never edits files. If the user asks for repair, switch to `init` or `audit` (with explicit consent).

## Required references

**Lazy-load** — none loaded by default; pull only when status detection surfaces something needing detail:

- [`references/repo-memory-structure.md`](../references/repo-memory-structure.md) — when reporting on memory layout
- [`references/mirrors-and-updates.md`](../references/mirrors-and-updates.md) — when reporting on canonical-vs-mirror state

## Workflow

1. **Detect project type** (see `references/project-lifecycle.md` *Universal Project Model*).

2. **Inspect canonical entrypoint**:
   - Which file is canonical? (per tool-awareness rule)
   - Line count; is it a router or a manual? (AP-MEM-1)
   - Does it route to topical `agents/*.md` files, or is it monolithic?

3. **Inspect local user-preference file** (`USER.md`):
   - Present? Git-ignored? Stale (older than the preference template)?

4. **Inspect shared/user-facing docs**:
   - `README.md` size and structure
   - Existence of a README structure map (`agents/readme-structure.md`)

5. **Inspect agent-facing docs**:
   - Topical files under `agents/`
   - Provenance frontmatter present on instantiated artifacts?
   - Manifest (`agents/project-artifacts.md`) up to date?

6. **Inspect mirrors**:
   - `CLAUDE.md`, `.github/copilot-instructions.md`, `.cursor/rules/agents.md`, etc.
   - Generation banners present? Drift from canonical?

7. **Inspect optional capabilities** (inventory + detection globs sourced from
   `capabilities.json` — see the Quick checks probe below):
   - Hooks installed? (`<repo>/.claude/hooks/` + settings.json)
   - Phase-lock contract installed? (`agents/phase-lock-contract.md` + `.harness/`)
   - Multi-host manifests present?
   - **Code-graph capability present?** (`agents/code-graph.md`) — if so, check it is routed from
     canonical memory (AGENTS.md / CLAUDE.md contains a pointer to `agents/code-graph.md`); report
     on / off / half-installed. A doc without routing is a half-install — report as such.
   - **Land-queue capability present?** (`agents/land-queue.md`) — if so, check `scripts/land.sh`
     exists and is executable, and the doc is routed from canonical memory; report
     on / off / half-installed. Doc without script, script without doc, or doc unrouted is a
     half-install. `scripts/land.sh status` gives the runtime view (read-only).
   - **Project Board present?** (`docs/backlog/items.jsonl`) — if so, surface it read-only:
     `python3 scripts/board.py tx --root .` (integrity + item count + roadmap rev) and, for the
     version timeline, `python3 scripts/board.py list --root . --version <vX>`. Never mutate
     during status. The dashboard (`docs/dashboard.html`) is the derived view.

8. **Inspect validation**:
   - Is `scripts/validate_target_harness.py` runnable against this repo?
   - When was it last run? (heuristic: recent commits touching harness files)

9. **Identify gaps** that the user should consider addressing.

## Output contract

Concise summary, ≤30 lines, covering:

- Project type
- Canonical project-memory file (with line count + monolith/router classification)
- Local user-preference status
- Shared/user-facing docs (size, structure-map presence)
- Agent-facing docs (count, provenance compliance)
- Mirrors (canonical match status, drift warnings)
- Capabilities installed: hooks / phase-lock / multi-host / project board
- Validation: last-run status, command to run now
- Known gaps (bullet list)
- Recommended next command (`init`, `validate`, `audit`, or specific repair)

## Anti-patterns

- Editing during status. If the user asks for fix, switch verb explicitly.
- Long output. Status should fit on one screen; detail belongs in `audit`.
- Reporting "PASS" without running the validator. Status describes state; it should not assert validation pass without evidence.

## Quick checks (one-liner each)

```bash
# canonical file presence
ls -la AGENTS.md CLAUDE.md 2>&1 | head

# mirror drift detection
diff <(sed '/^<!--.*generated.*-->/d' AGENTS.md) <(sed '/^<!--.*generated.*-->/d' .github/copilot-instructions.md 2>/dev/null) | head

# provenance compliance
grep -L 'instantiated_from:' agents/*.md 2>/dev/null

# capability registry probe (all 6 entries — name + detection globs come from
# capabilities.json; resolve project-meta's own dir per references/shared-cli-delegation.md,
# or set $PROJECT_META_DIR explicitly)
python3 -c "
import glob, json, os
paths = (glob.glob(os.path.join(os.environ.get('PROJECT_META_DIR', ''), 'capabilities.json'))
         or glob.glob('**/skills/project-meta/capabilities.json', recursive=True))
reg = json.loads(open(paths[0]).read()) if paths else []
for cap in reg:
    hits = [g for g in cap['detection'] if glob.glob(g)]
    print(f\"{cap['name']:<14} {'on' if hits else 'off':<4} {hits}\")
"

# project board (if present) — read-only integrity + counts
[ -f docs/backlog/items.jsonl ] && python3 scripts/board.py tx --root .
```

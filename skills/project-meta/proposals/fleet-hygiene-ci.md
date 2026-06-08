# Proposal: marketplace CI gate + fleet-hygiene backlog (lessons from `fullstack-dev-skills`)

> **Status:** Partially landed (design + CI gate). Item #1 is implemented; #2–#5 are proposed.
> **Scope:** wire the deterministic critic floor into CI (done), and track the four follow-on
> hygiene items mined from `jeffallan/claude-skills` (`fullstack-dev-skills`, v0.4.15).
> **Grounding:** direct read of `fullstack-dev-skills` (CLAUDE.md, SKILLS_GUIDE.md, `scripts/validate-skills.py`
> 23 checker classes, `commands/workflow-manifest.yaml`) against the current `hw-skills` tree, this session
> (2026-06-07). Aligns with memory `cli-toolkit-doctrine` (CLI-ify deterministic prose; lint enforces),
> `prefer-lightweight-derived-design` (reuse existing critics, don't build new machinery), and the
> `references/anti-patterns.md` AP-VAL-2 contract.

## 0. Framing — different species

`fullstack-dev-skills` is a **published library**: 66 domain-expert persona skills + 9 workflow commands +
an Astro docs site. `project-meta` is a **meta-engine** that bootstraps/audits/evolves a per-repo harness.
The 66 personas, decision trees, and framework references are **not** the lesson — `project-meta` already
out-engineers it on the harness contract (deterministic + reviewer critic split, pressure-testing, multi-host
manifests, dispatch ledger, provenance frontmatter).

What `fullstack-dev-skills` does better is **fleet maintenance discipline** — the layer that keeps a *corpus*
of skills honest at marketplace scale. That is where the gaps below come from.

## 1. ✅ Wire the critic floor into CI (LANDED)

**Finding.** `references/skill-critics.md` calls critics 1–5 "the `validate` floor" and says they are
"directly CLI-invokable on any runtime" — but `hw-skills` had **no `.github/workflows/` at all**. Nothing
automatically ran them. By our own AP-VAL-2 ("validator not in the gate"), the floor existed but was
unenforced at the repo level. `fullstack-dev-skills` runs `validate-skills.py` / `validate-markdown.py` /
`update-docs.py --check` on every push via `ci.yml`.

**What landed.** `.github/workflows/ci.yml` — a **tiered** gate (reuses the existing critics; no new logic):

| Tier | Checks | Why |
|---|---|---|
| **Blocking** | manifest sanity (JSON parses, skill paths resolve, names unique); `skill_architecture_lint.py .`; `validate_project_meta.py` | all exit 0 today → green on arrival |
| **Advisory** | `trigger_collision_check.py`, `context_cost_estimate.py`, `determinism_gap_scan.py`, `cross_skill_redundancy.py` | their opt-in `--strict` flag is the tell they are not meant to always-block; non-blocking so a red-on-arrival CI doesn't get ignored |

**Live findings the advisory tier surfaces today** (tracked here so they are not lost):

- **AP-SKL-3 / `trigger_collision_check`:** `orchestration` has no reciprocal Skill Arbitration row for
  `project-meta` (arbitration is one-directional: `project-meta → orchestration` exists, the reverse does not).
- **`context_cost_estimate`:** `project-meta`'s own description ≈ 225 tokens, over the 200 always-on ceiling.
  Either compress the description or raise the documented ceiling for router skills.
- **`determinism_gap_scan`:** 13 MUST/Gotcha rules name a backing script with no enforcing hook.

**Promotion path.** Each advisory critic graduates into the blocking tier once its findings are resolved
(e.g. add the reciprocal arbitration row → make `trigger_collision_check` blocking).

## 2. Derive doc/manifest counts instead of hand-maintaining prose (PROPOSED)

`fullstack-dev-skills` keeps a `version.json` single-source-of-truth and `update-docs.py` that **computes**
skill/reference/workflow counts from disk and propagates them into README/plugin.json, with a `--check` mode
CI fails on. `hw-skills`'s `.claude-plugin/marketplace.json` carries a long hand-written `metadata.description`
enumerating every skill, plus a per-plugin description that AGENTS.md requires to match each `SKILL.md`
**verbatim** — both are drift bait maintained by hand.

**Proposed:** `scripts/update_marketplace.py --check` that (a) verifies every plugin `description` equals its
`SKILL.md` frontmatter description verbatim, and (b) flags skills present on disk but absent from
`metadata.description`. Add `--check` to the CI blocking tier. Textbook `cli-toolkit-doctrine` (CLI-ify
deterministic prose). The verbatim-description check was deliberately left out of the v1 CI manifest-sanity
step to avoid a fragile inline frontmatter parser — this item is where it belongs, backed by `provenance.py`.

## 3. Declarative, DAG-validated phase manifest for `orchestration` (PROPOSED)

`fullstack-dev-skills`'s `commands/workflow-manifest.yaml` declares phases with typed edges
(`depends_on` + `strength: required|recommended` + `run_once` + `optional` + `external_skills`) and a
`ManifestDagChecker` that validates it with real cycle detection (DFS coloring). `project-meta`'s
orchestration story is prose (`references/multi-agent-protocols.md`, 26KB) + a *linear* phase-lock
(brainstorm→plan→implement→review→finish).

**Proposed:** the `orchestration` sibling skill (which already turns a milestone into a "signed orchestration
contract") gains a machine-checkable phase DAG with typed dependency edges, promoting phase-lock from a fixed
line into a validated graph. Owner: `orchestration`, not `project-meta`.

## 4. Two mechanical checks worth stealing from `validate-skills.py` (PROPOSED)

Its 23 checker classes include two that catch failures our suite structurally cannot:

- **`CrossRefChecker`** — every `related-skills` / arbitration pointer must resolve to a real skill dir.
  `project-meta`'s arbitration table names `deep-survey-bfs`, `dl-research`, `meta-debug`, `global-meta`,
  `calendar-crud-workflow`; rename or drop one and nothing fails today. `cross_skill_redundancy` checks
  *dedup* and `trigger_collision` checks *overlap* — neither checks *link integrity*. Fold into
  `skill_architecture_lint.py`.
- **`DescriptionFormatChecker`** — mechanically asserts the description contains a "Use when" trigger and
  *no* process steps (their named "Description Trap"). We document this rule in prose (`references/writing-skills.md`);
  confirm `skill_architecture_lint.py` enforces it as a hard check rather than leaving it to a reviewer agent.

## 5. Progressive-disclosure as *tiers* with enforced line budgets (PROPOSED, minor)

`fullstack-dev-skills` splits the budget (Tier-1 SKILL.md 80–100 lines, Tier-2 references 100–600) and
enforces it with `LineCountChecker` + `CoreWorkflowStepCountChecker`. `writing-skills.md` has one budget
(SKILL.md < 250 lines) and `context_cost_estimate.py` for tokens, but no per-tier line gate. A cheap
reference-file line-count check would catch the 700-line reference that should have been split. Low priority —
router skills are legitimately a different shape.

## What NOT to copy

- The 66 personas, decision trees, and `MODELCLAUDE.md`'s TDD/debugging mandates — the arbitration table
  **deliberately defers** intra-task methodology to the methodology plugin (superpowers). Importing them
  would violate lane discipline (AP-COORD-7).
- `the-fool` (5 adversarial reasoning modes) — already covered by `claims-adversary`, `methodology-critic`,
  and `pressure_test_skill.py`. Only borrowable idea: its mode taxonomy (Socratic / pre-mortem / red-team /
  falsification) as vocabulary for pressure-test scenarios.

# Writing Skills

Use this reference when authoring a new skill in `project-meta` style or auditing an existing skill for compliance.

The contract here is opinionated. It exists because skills that don't follow it tend to fail in predictable ways — see `references/anti-patterns.md` AP-SKL-* for the named patterns. Skills that do follow it are auditable, composable, and survive multi-host migration.

## Contents

- [Skill Anatomy](#skill-anatomy)
- [SKILL.md Contract](#skill-md-contract)
- [Reference vs Template vs Script](#reference-vs-template-vs-script)
- [Trigger Design](#trigger-design)
- [Writing for the Model](#writing-for-the-model)
- [Invariants and Soft Rules](#invariants-and-soft-rules)
- [Shared Harness Delegation](#shared-harness-delegation)
- [Examples Folder](#examples-folder)
- [Skill Audit Checklist](#skill-audit-checklist)

## Skill Anatomy

A skill is a directory with this shape:

```
my-skill/
  SKILL.md                  # router; trigger + intent only
  references/
    <topic>.md              # how-to procedures, lazy-loaded
    ...
  templates/
    <artifact>.md           # copyable seeds, lazy-loaded
    ...
  scripts/
    <verb>.py               # executable helpers; std-lib only when possible
  examples/                 # optional; reference end-to-end runs
    <example-id>/
      ... (artifacts a real run produces)
```

`SKILL.md` is read every time the skill is invoked. Everything under `references/` and `templates/` loads only when the matching task class runs. `scripts/` are invoked directly by the agent or by hooks.

A skill that ships only `SKILL.md` is not yet a skill — it is a prompt fragment. The reference / template / script layer is what makes the skill durable.

## SKILL.md Contract

`SKILL.md` is a **router**, not a manual. Keep it under ~250 lines. The agent reads it on every invocation; long routers waste context budget on every turn.

Required sections, in this order:

1. **YAML frontmatter** — `name`, `description`. The description must list every distinct capability the skill ships and end with a sentence stating the trigger condition. The frontmatter is what marketplace listings show; treat it as the skill's storefront.
2. **Trigger Decision** — bullet list naming each kind of request that should invoke this skill. One bullet per trigger class.
3. **Bootstrap Order** — what the agent reads before acting; ends with a list of references it may load lazily.
4. **Core Rules** — the invariants. Use MUST language. See *Invariants and Soft Rules* below.
5. **Skill Arbitration** — table of request shapes × owning skill × this skill's role. Required when the skill ships alongside peers that could ambiguously match the same prompt.
6. **Gotchas** — non-obvious traps in the skill's *own mechanics*. Five lines max each, with the trap as the lead clause.
7. **Quick Workflow** — 5-8 step triage map; per-step reference pointers. Detail belongs in references.
8. **When To Load References** — which reference to load for each task class.
9. **Examples** (optional but recommended) — link to `examples/`.
10. **Output Footer** — what the skill prints at the end of every invocation.

Don't add sections beyond these without strong reason. Each section the agent re-reads on every invocation is a tax. If a new section is needed, ask first whether it belongs in a reference instead.

## Reference vs Template vs Script

The three artifact classes have non-overlapping jobs. Mixing them produces the AP-SKL-1 failure mode (procedures load after the trigger).

| Artifact | Role | Loaded when |
|---|---|---|
| `SKILL.md` | Trigger + arbitration + invariants | Every invocation |
| `references/<topic>.md` | Procedures, decision trees, anti-patterns, audit checklists | Lazy: only when the matching task class fires |
| `templates/<artifact>.md` | Copyable seed an agent instantiates into a target project | Lazy: when scaffolding the matching artifact |
| `scripts/<verb>.py` | Mechanical helper invoked by the agent or by hooks | Lazy: explicit invocation |

Test for placement: if the content's *purpose* is "the agent needs this before acting", it goes in `SKILL.md`. If "the agent needs this once it has decided to act", it goes in a reference. If "the agent will copy this into another repo", it goes in a template. If "this is code, not prose", it goes in a script.

When in doubt, prefer references over `SKILL.md` additions. The router stays cheap; the reference loads only when needed.

## Trigger Design

A skill's trigger conditions decide when the agent invokes it. Bad triggers cause two failure modes: missed invocations (skill fires too rarely) or trigger collisions (multiple skills fire on the same prompt — AP-SKL-3).

Write trigger bullets so each is:

- **Disjoint from peer skills' triggers**. If a request would fire two skills, one of the skills' triggers is too broad. Tighten the broader one.
- **Shape-based, not example-based**. "Whenever the user asks 'review my code'" is a single example; "whenever a request involves auditing existing code against a defined contract" is a shape that generalises.
- **Loadable from `SKILL.md` alone**. The agent decides whether to invoke before loading any references; if the trigger condition lives in a reference, it's already too late.

Every skill must include a Skill Arbitration section if any peer skill's triggers are even partially overlapping. Default contract:

- The narrower skill wins.
- A skill that needs the output of another delegates explicitly with a hand-off.
- A skill never silently invokes another.

## Writing for the Model

Skills are read by an agent under context pressure, not by a human reading at leisure. Optimise for the model:

- **State the invariant before the explanation.** "MUST X. Reason: Y" reads correctly under pressure; "Y, therefore consider X" gets the explanation but loses the rule.
- **Use named anti-patterns** (`see AP-SKL-3`) instead of re-explaining the same trap in every reference. Keep the catalog in one file (`references/anti-patterns.md` for project-meta).
- **Avoid railroading** (AP-SKL-5). Express *intent* and *invariants*; let the model resolve mechanics. Step-by-step procedures are fragile to surface variation. Prescribe step-by-step only where deviation cost is high (security, correctness, audit).
- **One source of truth per fact.** A rule that lives in two places drifts; one of them becomes wrong silently.
- **Explicit non-applicability.** When a skill *does not* own a category of request, say so in Skill Arbitration. Agents pattern-match on capabilities; absent denial reads as silent endorsement.

## Invariants and Soft Rules

`SKILL.md` Core Rules should distinguish:

- **Invariants** — MUST-language rules that gate action. A violation is a bug. Examples: "MUST validate before commit", "MUST use this skill when triggers match".
- **Defaults** — what the skill does when nothing else is specified. Overridable. "Default to AGENTS.md as the canonical memory file."
- **Heuristics** — guidance for ambiguous cases. "Prefer narrow files when memory grows past ~200 lines."

Mixing the three is a common failure: a heuristic worded as MUST creates false-positive violations; an invariant worded as "consider" gets ignored under pressure (AP-SKL-2).

Mark invariants with **MUST**. Mark defaults with "Default:". Heuristics need no marker but should not start with MUST.

## Shared Harness Delegation

`project-meta` is the canonical home for cross-skill harness logic (the memory read/write-back protocol, frontmatter/provenance handling). A new skill that needs any of it **reuses** it — it does not re-implement it and does not vendor a copy. The full contract is in [`shared-cli-delegation.md`](shared-cli-delegation.md); the authoring obligations are:

**Decide first: does this skill touch the shared harness?** It does if it reads or writes repo memory (`CLAUDE.md`/`AGENTS.md`/`agents/*.md`/`USER.md`), gates work on a write-back decision, or instantiates provenance-stamped artifacts (`instantiated_from`/`source_reference`/`last_reviewed`). If it does none of these, skip this section entirely — do not add dead pointers (AP-SKL-1: content that loads but never fires).

When it does:

- **MUST cite the Memory Contract, not restate it.** Point at [`repo-memory-crud.md#memory-contract`](repo-memory-crud.md#memory-contract) for the read/write-back legs. One source of truth per fact (the *Writing for the Model* rule); a restated protocol drifts.
- **MUST delegate to the canonical CLI by resolved path, never re-roll or vendor.** Resolve `project-meta` using the full probe order in [`shared-cli-delegation.md`](shared-cli-delegation.md) (the canonical resolver — `$PROJECT_META_DIR` plus all Claude and Codex install tiers, not just the personal-skill path), then call `scripts/repo_memory.py` / `scripts/provenance.py`. Re-rolling frontmatter parsing is the specific trap the lint WARNs on; vendoring a copy creates drift the lint must then police.
- **MUST carry a thin floor.** The marketplace has no auto-install and submodules don't materialize at install, so `project-meta` may be absent. The delegation block's `else` branch states the minimum protocol inline so the skill still works standalone.
- **Default placement:** the `## Shared Harness Delegation` section in [`templates/SKILL.template.md`](../templates/SKILL.template.md) already carries the resolver + thin-floor snippet. Instantiate it (and delete it when the skill does not touch the harness).
- **Declare the dependency** in the skill's Skill Arbitration / delegation row pointing at `project-meta`, and route harness work there rather than freelancing it.

Vendoring (git-subtree / CI copy + a parity check) is required only when the skill must run the runtime code with `project-meta` absent and the thin floor is insufficient — defer it until that need is real.

## Examples Folder

A skill with non-trivial output benefits from an `examples/` folder containing one or more reference runs.

Per-example layout:

```
examples/<example-id>/
  README.md        # marketplace card: scope, version, coverage stats
  ... (the artifacts a real run produces)
```

Examples serve three purposes:

1. **Smoke tests** — every script in `scripts/` should produce sensible output against every example.
2. **Pattern templates** — schemas and prose tone are easier to imitate than to derive.
3. **Regression catches** — when the skill evolves, examples re-render to confirm no break.

Examples are point-in-time snapshots. The underlying domain keeps moving; re-render rather than edit by hand.

## Skill Audit Checklist

Score each item ABSENT, PARTIAL, or ENFORCED:

- [ ] `SKILL.md` under 250 lines.
- [ ] Frontmatter description names every distinct capability and the trigger condition.
- [ ] Trigger bullets are shape-based, disjoint from peer skills.
- [ ] Skill Arbitration table present if any peer skill could partially match.
- [ ] Core Rules use MUST for invariants; "Default:" or unmarked for the rest.
- [ ] Every procedure that exceeds one line lives in a reference, not in `SKILL.md`.
- [ ] References cite anti-pattern IDs when fixing a named trap.
- [ ] Scripts have argparse `--help`, std-lib only where possible, and exit with a remediation message on missing dependencies.
- [ ] At least one `examples/` entry exists for any skill that produces non-trivial artifacts.
- [ ] All scripts run cleanly against every example.
- [ ] If the skill touches repo memory or provenance, it cites the Memory Contract and delegates to `project-meta` via the resolver + thin floor (no restated protocol, no re-rolled frontmatter, no vendored copy). See *Shared Harness Delegation*.

When the audit returns ABSENT or PARTIAL on any line, fix it before shipping. Promote ABSENT items into the skill's next version backlog.

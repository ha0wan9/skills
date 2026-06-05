---
template_name: SKILL.template
description: "Seed scaffold for authoring a new skill in project-meta style. Instantiate at <skill-root>/SKILL.md."
source_reference: references/writing-skills.md
intended_project_path: skills/<skill-name>/SKILL.md
owner: agent-facing
secure_derivation: required
review_policy: user-review-before-publishing-skill
---

# SKILL.template.md

Use this seed when authoring a new skill that should follow project-meta's
contract. Replace every `<placeholder>` with skill-specific content; remove
sections that do not apply to your skill, but keep the order of those that
remain. See [`references/writing-skills.md`](../references/writing-skills.md)
for the full contract and the audit checklist.

## Project Artifact Frontmatter

The instantiated skill itself does not carry the project-meta provenance
frontmatter (skills are reusable artifacts, not project-specific). Track
the lineage in your skill's CHANGELOG or SKILL.md commit history instead.

## Copyable Block

Paste the block below into `<skill-root>/SKILL.md` and edit. Lines marked
`# REMOVE` are commentary — delete them before shipping.

```markdown
---
name: <skill-name-kebab-case>
description: >-
  <One paragraph that names every distinct capability the skill ships, in
  agent-readable terms. End with a sentence stating the trigger condition,
  e.g. "Use when the user asks for X, Y, or Z." This is what marketplace
  listings show.>
---

# <Skill Display Name>

<One sentence: what is this skill for? Read the agent-style description in
the frontmatter as the contract; this section restates the purpose for
human readers.>

Keep this file as the skill router. Load the linked reference files only as
needed.

## Trigger Decision

Use this skill for any of these triggers:

- <Trigger class 1, shape-based, disjoint from peer skills>: <when it fires>
- <Trigger class 2>: <when it fires>
- <Trigger class 3>: <when it fires>

Do not use the skill for <one or two clear non-applicability cases>.

## Bootstrap Order

1. <First read the agent must do, e.g. canonical project memory>
2. <Second read>
3. <...>
4. Load this skill's reference files only when you need them:
   - [`references/<topic-1>.md`](references/<topic-1>.md)
   - [`references/<topic-2>.md`](references/<topic-2>.md)

## Core Rules

- **MUST <invariant 1>.** <One-sentence reason. Cite anti-pattern IDs when
  the rule fixes a named trap, e.g. "Soft 'should' language is the AP-SKL-2
  failure mode this rule replaces."> # REMOVE: pick a real invariant.
- **MUST <invariant 2>.** <Reason.>
- Default: <override-able default>.
- <Heuristic, not marked with MUST>.

## Skill Arbitration

# REMOVE: include this section only if any peer skill's triggers could
# partially match the same prompt as yours. Otherwise omit.

When the user's request would match this skill *and* a peer, resolve as
follows. Always state the resolution before acting.

| Request shape | Owning skill | This skill's role |
|---|---|---|
| <shape A> | **`<this-skill>`** | acts |
| <shape B> | **`<peer-skill>`** | dispatches; do not act |
| <mixed shape C> | **`<peer-skill>` first**, then this skill | hand off |

If an arbitration is unclear, ask the user before invoking either skill.
Never silently invoke a peer skill.

## Gotchas

Non-obvious traps in this skill's own mechanics. Five lines max each, lead
with the trap. Keep these here, not in references — the agent reads them
before encountering the situation.

- **<Trap 1>.** <One-paragraph what-and-why; no procedural detail.>
- **<Trap 2>.** <...>

## Quick Workflow

Triage by task class, then delegate to the matching reference. Detail
belongs in references; this section is the router.

1. <Step 1>
2. <Step 2>
3. <...>

Detail for each step lives in the reference owning that step:
- step <N>: [`references/<topic>.md`](references/<topic>.md)

## When To Load References

- <Need-to-do-X>: load [`references/<topic-1>.md`](references/<topic-1>.md)
- <Need-to-do-Y>: load [`references/<topic-2>.md`](references/<topic-2>.md)

## Shared Harness Delegation

# REMOVE this section unless the skill touches repo memory or instantiates
# provenance-stamped artifacts. When it does, delegate to project-meta's
# canonical CLIs instead of re-rolling the logic — resolve the install path,
# fall back to a thin floor. Contract: project-meta's own
# references/shared-cli-delegation.md (NOT this skill's references/).

This skill reuses project-meta's shared tooling at runtime. Probe the install
locations (override, personal skill, plugin layouts); if none, use the floor.

```bash
# canonical resolver: project-meta's templates/hooks/scripts/verify-before-stop.sh
pm_dir=""
for c in "${PROJECT_META_DIR:-}" "$HOME/.claude/skills/project-meta" \
         "$HOME"/.claude/plugins/marketplaces/*/skills/project-meta \
         "$HOME"/.claude/plugins/cache/*/*/*/skills/project-meta; do
  [ -n "$c" ] && [ -f "$c/scripts/repo_memory.py" ] && { pm_dir="$c"; break; }
done
if [ -n "$pm_dir" ]; then
  python3 "$pm_dir/scripts/repo_memory.py" --target-root . read
else
  echo "[memory] read CLAUDE.md or AGENTS.md before substantive work." >&2  # thin floor
fi
```

## Examples

# REMOVE if the skill has no examples/ folder yet. Add one when the skill
# starts producing non-trivial artifacts.

Reference run: [`examples/<example-id>/`](examples/<example-id>/). See
[`examples/README.md`](examples/README.md) for the index.

## Output Footer

End each invocation with:

```text
**Skill**: <skill-name>  **Status**: <status>  **Next**: <action|done>
```
```

## Authoring Checklist

Before shipping the new skill:

- [ ] Frontmatter description names every capability and ends with the trigger sentence.
- [ ] `SKILL.md` is under ~250 lines.
- [ ] Trigger bullets are shape-based, disjoint from peer skills.
- [ ] Skill Arbitration table is present if any peer skill could match.
- [ ] Every procedure longer than one line lives in a reference, not `SKILL.md`.
- [ ] All MUST rules are invariants, not heuristics.
- [ ] At least one `examples/` entry produced if the skill ships non-trivial artifacts.
- [ ] All scripts pass smoke tests against the example.
- [ ] References cite anti-pattern IDs (AP-XXX-N) when relevant.
- [ ] If the skill touches memory/provenance, it delegates to project-meta via the resolver + carries a thin floor (no vendored copy). See project-meta's `references/shared-cli-delegation.md`.

Run the full audit checklist in [`references/writing-skills.md`](../references/writing-skills.md#skill-audit-checklist) before merging.

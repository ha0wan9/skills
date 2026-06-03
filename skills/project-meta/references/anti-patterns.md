# Anti-patterns

Concrete failure modes that recur across agent harnesses. The Gotchas section
in `SKILL.md` warns about traps in *this skill's mechanics*; this file
catalogs traps in the *harness designs* the skill produces or audits.

Each anti-pattern is named, described in one line, paired with the symptom
the user will see, and the fix that re-enables progress. Skim before
auditing or redesigning a harness; consult by name when a symptom matches.

## Memory layer

### AP-MEM-1 — Bootstrap-as-encyclopedia
The repo's bootstrap memory file (e.g. `AGENTS.md`) accumulates every rule
ever written, becoming a 600-line wall agents can no longer triage.

**Symptom**: agents start ignoring sections; new contributors paste their
rules at the bottom; the file's table of contents stops matching its body.

**Fix**: split topical content into `agents/<topic>.md` files; reduce the
bootstrap file to a routing map plus global guardrails (see
`repo-memory-structure.md`).

### AP-MEM-2 — Mirror as alternate manual
A tool-specific mirror (`CLAUDE.md`, `.github/copilot-instructions.md`,
`.cursor/rules`) grows rules that don't exist in the canonical memory file.
The mirror becomes a parallel source of truth with subtle drift.

**Symptom**: a behaviour observed under one tool can't be reproduced under
another; rules contradict each other across files.

**Fix**: treat mirrors as views, not manuals. Generate or sync them from the
canonical file (`mirrors-and-updates.md`). Reject any mirror-only rule
addition.

### AP-MEM-3 — Stale rules layered with contradictions
New guidance is appended on top of obsolete guidance instead of replacing
it. Agents read both and pick the one that fits the current request,
producing inconsistent behaviour run-to-run.

**Symptom**: same task done two ways across two sessions; reviewers cite
different rules to justify opposing positions.

**Fix**: replace, don't append. When a rule changes, edit the existing
clause and date the change. Maintain garbage-collection cadence
(`harness-engineering.md` audit checklist).

### AP-MEM-4 — Session log in canonical memory
Time-stamped notes ("we tried X on 2026-04-12, didn't work") accumulate in
`AGENTS.md` or topical memory files instead of being distilled into durable
rules.

**Symptom**: memory files grow without the harness improving; rules become
specific to past incidents rather than general guidance.

**Fix**: write only durable, repo-relevant facts. Past incidents belong in
git log or a separate `audits/` directory; only the *lesson learned*
belongs in memory.

## Skill / harness authoring

### AP-SKL-1 — Body text loaded after the trigger
Critical guardrails live in a reference file that loads only after the
agent has decided to act. The trigger fires, the agent edits, then loads
the rule that would have prevented the edit.

**Symptom**: rules in `references/*.md` are documented but routinely
violated.

**Fix**: anything that gates *whether* to act lives in `SKILL.md`. References
hold the *how* once the decision is made.

### AP-SKL-2 — Soft "should" instead of hard "MUST"
Skills say "consider X" or "use Y when applicable". Agents under pressure
read these as optional and skip.

**Symptom**: skills cited in retrospect as "should have applied" but not at
the time of action.

**Fix**: use MUST language for invariants. Document deliberate non-use
explicitly when it happens, so the exception is reviewable.

### AP-SKL-3 — Trigger collision between skills
Two skills' trigger conditions overlap (e.g. "research X" matches a survey
skill and a research-workflow skill). Agents pick whichever loaded first;
behaviour is order-dependent.

**Symptom**: same prompt produces different skill invocations across
sessions.

**Fix**: write explicit arbitration rules. The narrower skill wins; or one
skill delegates to the other with a documented contract. Encode in the
ambiguous skill's trigger section.

### AP-SKL-4 — Skill ships procedures the user can't run
Skill references invoke scripts, libraries, or external services the user
hasn't installed. The skill's "how to invoke" section omits the
prerequisite list.

**Symptom**: first invocation fails with import errors or "command not
found"; user abandons the skill before learning what it does.

**Fix**: every script-invoking section names its prerequisites in a
Requirements block. Validate prerequisites in the script's first lines and
exit with an actionable message, not a stack trace.

### AP-SKL-5 — Anti-pattern: railroading the model
Skills prescribe step-by-step procedures so rigid that the agent can't
adapt to surface variation. Performance degrades on edge cases the author
didn't anticipate.

**Symptom**: skill works on canonical examples, fails subtly on real
projects.

**Fix**: write skills for the model, not the human reader. Express
*intent* and *invariants*; let the model resolve mechanics. Prescribe only
where the failure cost is high.

### AP-SKL-6 — Skill writes runtime state into its own install dir
A skill's script persists session/run state next to itself
(`STATE_DIR = SKILL_ROOT / "state"`) instead of in a project-scoped location.

**Symptom**: state vanishes or fails to write after a marketplace update (the
install lives in a read-only / wiped plugin cache); worse, one install serving
several repos silently *bleeds* state and lessons across unrelated projects, so a
"lesson" learned in repo A surfaces while debugging repo B; the state also lands
in the skill repo's own version control because no `.gitignore` rule covers it.

**Fix**: resolve a **project-scoped** state dir — nearest ancestor with `.git`
→ `<repo-root>/.harness/<skill>/` — with an explicit `--state-dir` flag and an
env override, and never fall back to the install dir. Add the `.harness/` ignore
rule to the target repo. Runtime artifacts are per-project; the install dir is
shared and ephemeral.

## Coordination & multi-agent

### AP-COORD-1 — Conductor edits and orchestrates simultaneously
The lead agent both makes file edits and dispatches subtasks. Its context
fills with implementation detail; routing decisions degrade.

**Symptom**: lead agent's later decisions ignore earlier work; subtasks get
duplicate or conflicting briefs.

**Fix**: when a task touches >1 file or >1 reviewable unit, dispatch each
unit to a fresh subagent. Conductor reviews and integrates only.

### AP-COORD-2 — No review gate between sub-tasks
Subagents merge their work back to the trunk without review. A flaw in
sub-task N is discovered at sub-task N+5, requiring rollback of all
intermediate work.

**Symptom**: long autonomous runs end with large rollbacks; bug bisection
crosses many subagent commits.

**Fix**: dispatch a fresh reviewer subagent between sub-tasks. Reviewer
sees only the diff and the brief, not the full conductor context. A
background or batched runner that defers the review verdict to end-of-run
does **not** satisfy this fix: the gate must be able to STOP forward
dispatch, not merely annotate after the fact. See
`multi-agent-protocols.md` "Synchronous Gates Under Orchestration".

### AP-COORD-3 — Plan documents drift from execution
The written plan is composed once, then execution diverges. The plan stays
as a stale artifact alongside the actual work.

**Symptom**: PR descriptions reference plan items that no longer match the
implementation; reviewers pull the plan to verify and find it outdated.

**Fix**: treat the plan as a versioned artifact. Either update it as
execution proceeds or mark sections as superseded with a pointer to the
diverging code.

### AP-COORD-4 — Over-orchestration
A heavyweight scripted orchestration engine (Claude Code Workflow, Codex
Agents-SDK, worktree-isolated parallel runs) is launched where a cheap
subagent loop — or a single-context edit — would do. The mirror image of
AP-COORD-1's under-firing: this is over-firing.

**Symptom**: a 2-file logically-atomic change spins up a worktree, a
journal/runId, and a multi-stage pipeline; setup cost and coordination
overhead exceed the work; the user is surprised by an expensive run they
didn't ask for.

**Fix**: keep two distinct bars (`multi-agent-protocols.md` Mandatory
Subagent Dispatch). The ≥2-file rule selects *subagent dispatch*; the
scripted *engine* needs a higher bar — explicit opt-in or semantic scope,
never raw file count. When a set of edits is one coherent interdependent
change, prefer single-context authoring + a dispatched review pass over
parallel authoring (parallel authors drift on shared cross-references);
state the bypass per Mandatory Subagent Dispatch.

### AP-COORD-5 — Read-pattern mis-derived
The context-acquisition pattern is set wrong for the task. Either a CRUD /
single-subsystem task triggers an eager context-mapping Explorer fan-out
(wasted reads — the read-volume sibling of AP-COORD-4), or a complex design
/ cross-subsystem task proceeds on minimal just-in-time reads and the Lead
decomposes without a coherent global model (stale or partial design
propagates down the worker chain).

**Symptom**: a one-file path rename spins up a multi-Explorer survey before
acting; or a redesign ships with workers each reading a narrow slice and no
one holding the whole picture, so a cross-cutting constraint is missed.

**Fix**: derive the read-pattern, don't guess it (`execution-policy.md`
"Read-Pattern Derivation"): default `minimal`, escalate to
`context-mapping` only on design signals or `semantic_scope >=
cross_subsystem`. State the derived pattern in the delivery so a misfire is
visible. The mapping phase's own four constraints live in
`multi-agent-protocols.md` "Context Mapping Phase".

## Validation & enforcement

### AP-VAL-1 — Advisory rules with no validator
Rules are documented but never mechanically checked. Each rule's enforcement
depends on the agent reading and respecting the prose.

**Symptom**: rule violations land in commits; reviewers catch them
manually; the rule is restated rather than enforced.

**Fix**: when a rule is repeatedly missed, promote it: add a script,
linter, hook, or template. `harness-engineering.md` calls this out
explicitly — prefer mechanical rules. **Promote across the full compat
matrix**, not one runtime: a MUST-rule mechanized only on Claude Code
(e.g. a Workflow) with no Codex-side backing (Agents-SDK script or
`.codex/agents/*.toml` config) **and** no prose fallback is itself an
AP-VAL-1 gap — it silently regresses the other runtime's leg. Either
back it on every declared compat runtime or keep the prose path as the
cross-runtime floor (`multi-agent-protocols.md` "Orchestration Backings";
overlaps AP-SKL-4 when the un-backed runtime can't run the procedure).

### AP-VAL-2 — Validation script not in the delivery contract
A validator exists but isn't part of the pre-commit / pre-merge gate.
Agents skip it under time pressure.

**Symptom**: the validator is named in references but not invoked in
practice; CI catches errors the validator would have caught locally.

**Fix**: wire validators into the delivery contract
(`documentation-delivery.md`). Require them to pass before commit; surface
their output in the delivery summary.

### AP-VAL-3 — Pressure-test gap
Skills are tested on calm, canonical scenarios. They fail under
time-pressure prompts ("just patch it quickly", "skip validation, deadline
tight"), sunk-cost prompts ("we already started, finish this way"), or
authority-flipping prompts ("the rule doesn't apply here").

**Symptom**: skills cited as compliant in audits, violated under real
session pressure.

**Fix**: maintain a pressure-test suite (planned for v1.0). Replay each
pressure scenario; verify invariants hold.

## Lifecycle

### AP-LIFE-1 — Init runs without USER.md decision
First-time init silently picks defaults rather than walking the user
through the preset/checklist questionnaire. The user inherits choices they
didn't make and the harness doesn't fit their workflow.

**Symptom**: user later asks "why is X enabled?"; preferences feel
external.

**Fix**: `/project-meta init` MUST run the questionnaire before rendering
`USER.md`. Default-on is a reasonable starting state; *opt-in* is the
contract.

### AP-LIFE-2 — Lesson never makes it back into memory
A user correction, review finding, or post-mortem identifies a durable
lesson. The agent fixes the immediate issue; the lesson stays in chat and
is lost on session end.

**Symptom**: same mistake recurs across sessions; users repeat the same
correction.

**Fix**: at end of every substantive task, ask: does this lesson belong in
canonical memory? If yes, write it back to the right file (the one whose
scope matches the lesson) before closing the task.

### AP-LIFE-3 — Audit cadence absent
Harnesses are designed once, not maintained. After 6 months they're full
of stale rules; after 12 months they're misleading.

**Symptom**: rule citations point at obsolete file paths or removed
features; agents follow rules that no longer match the codebase.

**Fix**: schedule periodic audits (`/project-meta audit`). Treat the audit
as part of the harness, not as one-off cleanup.

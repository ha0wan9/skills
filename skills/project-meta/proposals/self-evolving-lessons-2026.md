# Proposal: self-evolving lesson lifecycle (2026-07) → skill updates

> **Status:** Revised (v2) — adversarial critic panel (4 lenses: mechanism-correctness,
> reward-hacking, redundancy/lightweight-design, cost/complexity) returned **NO_GO on v1**;
> this revision folds every BLOCKER/MAJOR finding. Awaiting operator GO for implementation.
> **Scope:** benchmark the marketplace's self-evolution machinery (lesson registry, memory
> write-back, dispatch telemetry) against the 2025–2026 self-evolving-agent literature;
> propose 1 bug fix + 7 prioritized updates (E0–E7).
> **Grounding:** one very-thorough repo inventory agent + one web-research agent (2026-07-10)
> covering academic lines (ACE, SkillWeaver/Trace2Skill/SkillOS, Memento-Skills, SEAL, DGM,
> GEPA, the 2025–26 self-evolving-agent surveys) and practitioner lines (Agent Skills spec,
> skill-creator v2 eval loop, auto-MEMORY.md, community Learnings.md/Stop-hook patterns).
> Aligns with memories `prefer-lightweight-derived-design`, `critic-before-build-canon`,
> `adversarial-lens-earns-keep`, `cli-toolkit-doctrine`.

## 0. Headline finding

The marketplace is **ahead of the field on validation-gate and lifecycle structure** — the
two dimensions the 2025–26 surveys name as least mature industry-wide. `lesson_registry.py`
already has a four-state ladder with legal (note-gated) demotions, structural validation
that fails closed, and model-tier-filtered injection; the dl-research ratchet's promote
gate (critic-verdict row required before `promote`) is the mechanized form of what
Anthropic's CoEvoSkills calls an evolution-resistant verifier.

The real gap is symmetric and specific: **the measure and forget legs are schema-complete
but data-starved.** `outcome --helpful/--harmful` exists and nothing ever calls it;
promotion checks structure but never evidence; `trim-candidates` exists and nothing runs it
on a cadence; dispatch-ledger tier telemetry has a mechanical read leg and a prose-only
write leg. The critic panel additionally found that one already-shipped leg —
`promote-draft`'s collision check — has **never functioned** (E0). Every E below extends an
existing script; the only new artifacts are two small git-ignored event/schema additions,
named explicitly in E1 (v1's "no new stores" pledge was found internally inconsistent and
is withdrawn in favor of naming the state).

What the 2025–2026 literature converged on (primary sources; confidence flagged):

1. **Context evolves by itemized deltas, never monolithic rewrite.** ACE (Stanford/
   SambaNova, open-sourced Nov 2025) names the two failure modes: *brevity bias* (LLM
   rewriting converges to short generic prose, discarding hard-won heuristics) and
   *context collapse* (their trace: one rewrite step, 18,282 tokens/66.7% → 122
   tokens/57.1%, worse than no adaptation). Fix = structured bullets with stable IDs
   + delta ops + periodic grow-and-refine de-dup. `lessons.jsonl` is already the right
   shape; the appended-dated-bullet path in `repo_memory.py write` is not.
2. **Self-generated success signals are gameable; the gate needs an authority the
   generator can't satisfy.** Darwin Gödel Machine's documented incident: the agent
   fabricated test-execution logs, believed its own faked "passed", and carried unverified
   code forward (sakana.ai/dgm). Mem0's reward-hacked-refunds case is the memory-layer
   analog. CoEvoSkills' answer: keep the verifier evolution-resistant — the skill-writer
   must not be able to edit its own grader. The panel applied this test to v1 and found
   the outcome counters themselves fail it; see the Trust Model note in §2.
3. **Effectiveness signals can be cheap and heuristic — but they must exist.** Dynamic
   Cheatsheet (arXiv:2504.07952, EACL 2026) runs its whole curation loop with **no ground
   truth**; SkillWeaver gates skills on generated test cases; skill-creator v2 stops
   iteration when feedback is empty or gains plateau. The industry's shipped tools,
   per the P-series audit, "universally lack enforce and measure" — this repo shipped
   enforce (D-series gates) and stubbed measure (the outcome counters).
4. **Capture triggers: correction-triggered beats every-turn reflection.** Claude Code's
   auto-MEMORY.md writes only "when it detects a recurring pattern or a correction you
   apply multiple times" — high precision, low recall, by design. Community Stop-hook
   reflect loops work but come with the warning "you want a lot of confidence in what the
   reflect mechanism is doing" before full automation; unconditional-update-on-every-stop
   patterns are documented to accumulate vague entries that "waste context space and don't
   change behavior".
5. **Forgetting/consolidation is the field's weakest dimension.** No surveyed system has
   an automated, safe, general forgetting policy; the best shipped practice is scheduled
   human pruning ("a file that shrinks slightly each quarter is usually getting better")
   plus hard caps (MEMORY.md 200 lines/25KB). SkillOS's executor/curator split
   ("sleep consolidation") is the clearest architecture; ACE's grow-and-refine the
   clearest mechanism. A demotion lifecycle that exists but never fires is the named gap.
6. **Skills distilled in one context transfer to others.** Trace2Skill (arXiv:2603.25158):
   hierarchical SKILL.md + references split, dominance-aware consolidation of conflicting
   patches, and a +57.65-point cross-model transfer result; SkillWeaver skills from a
   strong agent lifted a weak agent up to +130% on some sites. Lessons locked to a single
   repo's `.harness/` forfeit exactly this compounding.
7. **Retrieval, not artifact quality, becomes the bottleneck at scale** (Memento-Skills'
   router: 80% vs 50% end-to-end success over BM25; the "irrelevant-skill-via-semantic-
   similarity" trap is named). At the current registry size (≪100 rows) the 20-line
   inject cap + `applies_below` tier filter is the correct amount of machinery — noted
   here so E-series doesn't over-build retrieval.

## 1. Audit — the six design dimensions vs. this repo

| Dimension (2026 frontier) | Here today | Verdict |
|---|---|---|
| Capture trigger | `lesson_registry.py add` — manual only; no hook drafts candidates from high-signal events | **gap → E6** |
| Artifact granularity | `lessons.jsonl` itemized rows with IDs (ACE-correct) — but `target_path` conflates "enforcement artifact location" with "scope the lesson concerns", and no field links a lesson to a gate; `repo_memory.py write` appends dated prose bullets to AGENTS.md (bloat/brevity-bias exposure) | **gap → E1(a), E4** |
| Validation gate | structural `validate` fails closed; ratchet promote gate mechanized (dl-research L3) — but **no evidence threshold** on lesson promotion, and `promote-draft`'s collision check is a silent no-op today (E0) | **gap → E0, E2** |
| Promotion/demotion lifecycle | full state ladder incl. legal demotions — but `outcome` counters never written, so no signal ever triggers a demotion; `trim-candidates` exists, nothing schedules it | **gap → E1, E3** |
| Retrieval/injection | 20-line cap, tier-filtered, SessionStart-wired — but `inject` only surfaces candidates + *stale* promoted/enforced rows; recorded and healthy promoted/enforced lessons are never re-shown | **gap → E1(b)** |
| Forgetting/consolidation | trim suggestions → board inbox (manual); consolidation exists as prose (`repo-memory-crud.md` §Delete Or Consolidate) with no mechanized leg; staleness lint advisory-only | **gap → E3, E4** |

Adjacent, same shape: dispatch-ledger retro-inspect tier promotion — mechanical read leg
(`query --tiers`), 100% prose write leg (`multi-agent-protocols.md` §Retro-inspect) → E5.

## 2. Proposals (priority order)

**Trust Model note (panel finding, applies to E1–E3, E6).** The lesson store is plain
git-tracked text in the agent's working tree; `outcome` is a plain CLI. No design at this
altitude can make the counters tamper-proof against the agent being measured — the same
actor can hand-edit the file. The E-series therefore treats effectiveness evidence as
**decision-support with an audit trail, not a security boundary**: observations are
append-only rows carrying `source` (`observe` = hook-written heuristic vs `manual`),
mandatory notes on negative/manual entries, and a scope snapshot binding each observation
to the target it was measured against; every draft that consumes them prints the
underlying evidence inline so the operator judges the claim, not an opaque integer. Git
history is the tamper record. Anything stronger (actor identity, attestation) is engine/
platform work — out of scope (§3), limitation inherited and documented.

### E0 — Bug: `promote-draft`'s collision check has never functioned (bug, project-meta)

**Evidence (panel, mechanically verified):** `cmd_promote_draft` invokes
`trigger_collision_check.py`/`cross_skill_redundancy.py` with `--statement <text>`; both
scripts take a positional *path* and define no `--statement` — the call exits 2 and, since
only stdout is inspected, the failure is silently swallowed. The "collision-checked
promotion draft" leg shipped in DASH-048 is a no-op.

**Scope:** make the check real and shaped for the tools: write the lesson statement to a
scratch reference file and run `cross_skill_redundancy.py` against it in a supported mode
(or add an explicit statement-vs-tree comparison entry point to that script); check
returncodes and surface stderr instead of swallowing them. Independent of every other E;
also a prerequisite for E7.

### E1 — Close the measure loop: schema v2 + injection surface + Stop-hook observe (feat, project-meta)

**Evidence:** ¶3; repo audit — no code path anywhere calls `outcome`. Highest-leverage
item because E2 and E3 are gated on evidence existing at all. Panel BLOCKERs folded:
v1's heuristic was uncomputable (no gate link field; `target_path` is the enforcement
artifact, not a concern-scope; `inject` never surfaces the rows that matter; the hook's
`advisory_exit` terminates before any later step can see a failure).

**Scope:**
- (a) **Lesson schema v2** (versioned, back-compat): add `scope_paths` (list of
  repo-relative globs the lesson's guidance concerns — distinct from `target_path`, which
  stays "where the enforcement artifact lives"), `gate_id` (optional, closed enum of
  `verify-before-stop.sh` leg names, validated), and `observations[]` (append-only rows
  `{direction, source, scope_snapshot, note, utc}`); `helpful_count`/`harmful_count`
  become derived views over `observations[]`.
- (b) **Injection surface:** `inject` additionally surfaces `recorded` rows and healthy
  `promoted`/`enforced` rows (priority order: candidates → stale → recorded → healthy),
  still under `MAX_INJECT_LINES` — named explicitly as a change to the injection budget.
- (c) **Gate-event artifact (new, small, named):** `advisory_exit` appends one line
  `{gate, profile, utc}` to git-ignored `.harness/stop-gate-events.jsonl` (size-capped)
  before exiting. This is the enabling change that makes "a gate failed this turn"
  observable at all — shared with E6.
- (d) **`observe` subcommand**, called from `verify-before-stop.sh`'s D6 leg (advisory,
  fail-open, exit 0, skipped at `minimal`): recomputes in-scope rows directly from
  `lessons.jsonl` + model tier via the existing `_should_show` logic (**no inject-receipt
  file** — the panel's derived alternative, adopted; v1's `.harness/last-inject.json` is
  dropped). Records `helpful` when the turn's changed files match a row's `scope_paths`
  and its `gate_id` (if set) has no failure event this session; `harmful` when its
  `gate_id` appears in `stop-gate-events.jsonl`. Rows without `scope_paths` are
  ineligible — no scope, no signal. Overly-broad scopes are the known farming vector
  (panel): `validate` WARNs on `scope_paths` matching more than a threshold share of the
  tree, and E2's gate weighs breadth (below).

**Known costs (panel, accepted and documented):** a second `git status --porcelain`
subprocess at Stop (bounded; implementation may pass the changed-file list from the
writeback step via the hook instead); the advisory `_lesson_lock` is fail-fast, so an
agent-invoked `add` can race a hook-invoked `observe` and error without retry (advisory
side is fail-open; CLI side surfaces a real error — low probability, documented);
per-worktree `lessons.jsonl` copies mean fleet sessions accumulate counters that can
conflict at merge — counters are **approximate and lossy under fleet merges** by design;
`observations[]` being append-only rows (not a mutable int) makes those conflicts
line-mergeable in the common case.

### E2 — Evidence-gated promotion + derived protected-paths check (feat, project-meta)

**Evidence:** ¶2, ¶3; repo audit. Same graduation `harness-engineering.md` prescribes and
the same pattern as dl-research's shipped promote gate. Panel findings folded: evidence
must bind to the scope in force (retarget-then-promote farming), and the protected list
must be derived, not hand-typed.

**Scope:**
- (a) `status <id> promoted` requires ≥3 `helpful` observations whose `scope_snapshot`
  matches the row's **current** `scope_paths`/`target_path` (retargeting invalidates
  prior evidence by construction) and no unresolved `harmful` observation; `status <id>
  enforced` additionally requires the target hook/linter file to exist and be executable.
  `--force` + mandatory `--note` overrides, leaving the audit trail in `notes[]`.
  Observations with `source: manual` count only when they carry a note citing the
  turn/gate; drafts print the evidence rows inline (Trust Model note).
- (b) **Protected-paths leg** (¶2, DGM incident): `validate` FAILs any lesson whose
  `target_path` or `scope_paths` point at the machinery that grades lessons. The list is
  **derived programmatically**, not enumerated by hand (panel BLOCKER): the union of
  (i) every `agents/*.md` listed in each plugin's `agents` array in
  `.claude-plugin/marketplace.json`, (ii) `skill-critics.md` itself, and (iii) the five
  deterministic critic scripts enumerated in `skill-critics.md`'s Deterministic Critics
  sections — `trigger_collision_check.py`, `context_cost_estimate.py`,
  `determinism_gap_scan.py`, `cross_skill_redundancy.py`, `skill_architecture_lint.py`
  (parse the section headings or hand-list them; either derivation is acceptable, but all
  five MUST be included — E0 makes two of them lesson-promotion graders, and a grader must
  not itself be lesson-targetable). Override requires a note with the exact prefix
  `verifier_ack:` (specified format, matched literally — panel MINOR).

  *Note (2026-07-10): this replaces the earlier "parse Suite Overview rows 6–7"
  derivation — those two hardcoded per-skill rows collapsed into one generic
  owning-skill-self-declaration row (task C1), so the protected-paths leg can no longer
  enumerate agent paths from that table and instead derives them from the marketplace
  manifest's `agents` arrays.*

### E3 — Symmetric demotion + scheduled trim (feat, project-meta)

**Evidence:** ¶5; repo audit; AP-LIFE-3 ("schedule periodic audits") is prose with no
mechanical floor. Panel findings folded: reuse the in-file resolver; mandatory evidence
on harmful; drafts show their evidence.

**Scope:**
- (a) `outcome --harmful` requires `--note` citing the gate/turn (mechanical: non-empty +
  references a gate id or file); `outcome --helpful` from the CLI requires `--note` too
  (hook-written `observe` rows carry their trigger automatically).
- (b) `lesson_registry.py auto-demote [--apply]`: ≥2 `harmful` observations against the
  current scope, or `target_path` stale per the **in-file `_check_path_resolves`** (v1
  wrongly cited `memory_staleness.py`'s resolver — both critics flagged it; corrected) →
  draft (default) or apply (`--apply`) the legal demotion one rung down. Drafts print the
  full `observations[]`/`notes[]` evidence inline so the operator judges substance, not a
  bare count (panel: draft-not-execute must not launder an opaque integer).
- (c) Wire `trim-candidates` + `auto-demote` (draft mode) into `recipes/audit.md` as a
  standing audit dimension — cadence rides the existing audit loop, no new cron.
  Board-inbox drafting stays the write path for retirements.

### E4 — Mechanize repo-memory-crud.md's consolidation section (feat, project-meta)

**Evidence:** ¶1, ¶5 — and, per the panel, the practice already has a canonical prose
home: `references/repo-memory-crud.md` §Delete Or Consolidate + §Quality Bar ("prefer
replacing stale guidance over appending contradictory guidance"). v1 overstated the gap
("no consolidation pass") — the gap is that the section has no mechanized leg. E4 cites
it by pointer and mechanizes it; the recipe leg restates nothing.

**Scope:** a `repo_memory.py consolidate` subcommand: parse the canonical entrypoint's
dated write-back bullets, group by topic, and emit a **draft delta plan** (merge
duplicates, retire superseded bullets, relocate stable clusters into `agents/<topic>.md`)
— delta ops only, never a full-file rewrite (¶1: context-collapse guard), applied deltas
must not net-add lines (checked on the applied delta, not the draft). Output is capped
(constant mirroring `READ_CAP`/`MAX_INJECT_LINES`, truncation notice when clipped — panel
MAJOR). Advisory; the writeback gate remains the enforcement point; operator is merge
authority.

### E5 — Script the retro-inspect write leg: `dispatch_ledger.py suggest-tier` (feat, project-meta)

**Evidence:** repo audit — the one learning loop whose read leg is mechanical and write
leg is pure Lead judgment; ¶3. Panel findings folded: verdict mapping made explicit; the
demotion half is descoped (its data source is repo-memory prose, unreachable from the
ledger); threshold aligned with canon.

**Scope:** `suggest-tier` reads the ledger's per-task_type tier/verdict aggregation
(existing `query --tiers` internals) and prints **promotion drafts** in the
`multi-agent-protocols.md` §Retro-inspect record format, ready to paste into repo memory.
Verdict mapping stated: `BLOCKER` counts as a failure; `SUGGEST`/`pending` are excluded.
Threshold defaults to **1 failure** — matching the documented single-failure trigger in
§Retro-inspect (v1's silent n=2 divergence corrected; configurable via flag). Promotion
drafts are capped at the existing Opus/Terra ceiling. The **demotion half stays prose**:
promotion records live in repo memory by canon ("ledger = transient evidence; repo memory
= durable policy"), and parsing them needs the structured-record design already tracked
as **DASH-071** — E5 links there rather than inventing a second store. Inherited
limitation, documented: the ledger has no actor-identity enforcement on recorded
verdicts; hardening that is a dispatch_ledger concern, not E5's.

### E6 — Correction-triggered reflector capture (feat, project-meta, capped; sequenced after E1–E3)

**Evidence:** ¶4 — correction-triggered capture is the documented high-precision design;
every-turn reflection is the documented bloat generator. AP-LIFE-2 ("lesson never makes
it back into memory") has no trigger today. Panel findings folded: v1's three triggers
included one duplicate and two unobservable events; and low-friction capture upstream of
an unhardened promotion pipeline amplifies farming risk — hence the sequencing.

**Scope:** extend `verify-before-stop.sh`'s D6 leg: when this turn shows a high-signal
event readable from **durable state** — (1) a dispatch reviewer returned `BLOCKER`
(`dispatch-log.jsonl`), or (2) a gate failed earlier this session then passed
(`stop-gate-events.jsonl`, the E1(c) artifact) — print **one** pre-filled
`lesson_registry.py add` draft command to stderr for the agent to run or discard. The
v1 "writeback gate fired" trigger is **dropped**: `repo_memory.py`'s `WRITEBACK_BLOCK`
already owns that event's capture nudge, and the hook exits on it anyway. Draft-created
rows are stamped `source: reflector-draft` so E2's gate can weigh them differently from
deliberately-authored lessons. Deterministic trigger, no model call, no auto-write; max 1
draft per stop; suppressed at `minimal`. Ships only after E1–E3's evidence-integrity
legs.

### E7 — Cross-repo upstream channel: lesson → skill distillation (feat, project-meta + marketplace; gated on E0)

**Evidence:** ¶6; repo audit — same project-meta install in N repos, zero lesson flow
between them; this marketplace is the natural upstream. Panel BLOCKER folded: the
collision-check leg this rides on is broken today; E0 fixes it first.

**Scope:** `lesson_registry.py promote-draft --target upstream`: for a promoted/enforced
lesson whose statement generalizes beyond the repo (operator judgment, aided by the
E0-fixed statement-vs-tree redundancy check run against the *marketplace* skill tree),
emit a board-inbox draft **for this marketplace's repo** proposing the lesson as a
SKILL.md/references edit to the owning skill — the Trace2Skill universal-vs-niche split:
universal rules climb to the skill, repo quirks stay in `.harness/`. Prefer a
`references/*.md` target unless the lesson is genuinely router-worthy: router SKILL.md
bodies carry an on-invoke token ceiling (`context_cost_estimate.py --max-invoke-tokens
--fail-on-invoke`, live since 1.25.0/1.26.0) — run it on the draft target before filing
the inbox item. Transport is the existing board inbox + ship flow; no new sync store,
no automation of the judgment call.

## 3. Explicitly out of scope (researched, rejected)

- **SEAL/DGM-tier self-modification** (weights, agent code): sandboxed-research maturity;
  reward-hacking unresolved (¶2); wrong altitude for a harness.
- **Tamper-proof effectiveness counters** (actor identity, attestation, store signing):
  engine/platform altitude; the Trust Model note documents the inherited limitation and
  the audit-trail posture instead.
- **Semantic/embedding lesson retrieval or a learned router:** Memento-Skills' own result
  says naive similarity is the trap; at ≪100 rows the cap+tier filter wins. Revisit with
  deterministic task-type tags if the registry passes ~100 active rows (¶7).
- **Every-turn LLM reflector on Stop:** documented bloat generator (¶4); E6's
  deterministic-trigger draft is the floor; an LLM reflector is an engine feature.
- **Restructuring verify-before-stop.sh to accumulate-then-report:** the panel sized the
  full accumulate-all-gates refactor as its own reviewed change; E1(c)'s one-line event
  write in `advisory_exit` delivers the observable signal without re-architecting the
  hook. Revisit only if the event file proves insufficient.
- **Automated pressure-testing red-team:** `pressure_test_skill.py`'s human-in-the-loop
  verdicts are a deliberate design (AP-VAL-3 floor), not a missing automation.
- **A friction dashboard / rule-level cross-tagging store** (the P-series' original
  `audit --friction` vision): E1's observations + E5's ledger aggregation deliver the
  measurable subset; a dedicated store is machinery ahead of evidence.
- **Auto-applying any promotion, demotion, retirement, or memory write:** every E keeps
  draft-not-execute posture where state changes canon — with the panel's caveat folded:
  drafts must carry their evidence inline, so the operator reviews substance rather than
  rubber-stamping a count (¶2).

## 4. Sequencing & next steps

1. **E0 first** — a shipped-bug fix, independent and small.
2. Suggested slice for the first milestone: **E1+E2+E3** — measure, evidence-gate,
   forget: the smallest coherent set that turns the existing lifecycle from
   schema-complete to signal-complete (with E1's schema/injection changes now explicitly
   in scope, per the panel — v1 understated them). E4 and E5 are independent minors; E6
   is sequenced after E1–E3 by design; E7 is gated on E0 and waits for a second consuming
   repo with promoted lessons.
3. Implement via validated-edit → ship → reload; board items track state. Panel round 2
   (re-review of this v2) is satisfied by the fresh-context PR review gate.

Board items filed (source: this proposal): E0–E7 → **DASH-072…DASH-079**, status
unscheduled — scheduling is a roadmap decision with the operator. E5 (DASH-077)
cross-links DASH-071 (structured promotion-record fit); E0 (DASH-072) supersedes the
silent-no-op collision leg shipped under DASH-048.

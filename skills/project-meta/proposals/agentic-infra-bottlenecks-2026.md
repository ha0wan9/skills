# Proposal: agentic-coding infra bottlenecks (2026) → harness additions/refactors

> **Status:** Proposed — awaiting operator GO + adversarial critic panel before any canon/code change.
> **Scope:** map the 2025–2026 practitioner-reported infra bottlenecks of agentic coding onto
> project-meta's capability surface; propose 7 prioritized additions/refactors (P1–P7).
> **Grounding:** 6 parallel web-research agents (2026-06-12), one per bottleneck domain
> (context/memory, verification/trust, multi-agent orchestration, execution environment,
> repo-scale code understanding, spec/governance). Rounds 2–3 (same day, 4 more agents):
> lesson-promotion loops (industry scorecard + academic lineage) folded into P3; harness-
> elasticity evidence (scaffold×model interaction, adaptive-oversight frameworks) added as P7.
> Evidence cited inline. Aligns with memories
> `prefer-lightweight-derived-design` (every P refactors/extends existing machinery),
> `critic-before-build-canon` (panel gates implementation), `cli-toolkit-doctrine`
> (deterministic prose → CLI), and the in-flight land-queue capability
> (`references/land-queue-integration.md` — boundary stated in P1).

## 0. Headline finding

The strongest convergent signal across all six research domains: the unsolved gaps are
**session-boundary and dispatch-state problems, not model problems** — exactly the layer a
repo harness owns. Three findings recur independently:

1. **Dispatch/shared state is too thin.** Coordination/specification issues account for 79%
   of multi-agent production breakdowns (MAST taxonomy via Augment Code 2026); context
   handoff loss, duplicate work, runaway cost (a documented $47k 11-day agent loop —
   waxell.ai post-mortem, Mar 2026), and unsalvageable crashes (chat-only recovery 8–13%
   correctness vs ~100% for checkpoint/restore — Augment Code, Terminal-Bench) all reduce to
   the same root: no enforced pre-dispatch/post-execution contract.
2. **Memory staleness is undetected and harmful.** Stale context files "degrade AI assistance
   without any error or warning" (arXiv:2606.09090, which names code-vs-context consistency
   checking as open future work); a practitioner-cited figure attributes ~62% of memory
   problems to stale entries overriding correct rules (SFEIR Institute); an ETH Zurich study
   found context files often *reduce* agent success and add ~20% cost when low-quality
   (InfoQ, Mar 2026). No shipped tool checks whether memory-file claims still match the repo.
3. **Review/verification is the new rate limiter.** High-AI teams: +98% PRs merged, +154% PR
   size, review time +91% → +441% YoY, incidents per PR +242% (Faros AI telemetry, 10k devs,
   2025→2026). Agent-specific failure modes (test weakening, assertion gaming) have no
   standard detector; AI code carries 2.74× more vulns (Veracode 2025), 1-in-5 orgs had an
   AI-code security incident (Aikido 2026).

Validation for shipped work: the land-queue capability is squarely confirmed — Anthropic's
CPO publicly stated they "had to completely re-architect" their merge queue under agent PR
volume (Trunk.io, Jun 2025); merge-queue-at-scale is now a named product category (Mergify,
Graphite). It landed as PR #52 (DASH-045) while this research ran; nothing below duplicates it.

## 1. Capability map — covered / partial / gap

| Bottleneck (domain) | project-meta today | Verdict |
|---|---|---|
| Multi-tool config fragmentation (CLAUDE.md/.cursor/copilot drift) | `render_host_manifests.py` one-canonical→generated mirrors + drift detection | **covered** |
| Instruction-file token tax | `context_cost_estimate.py`, DASH-031 token diet, selective loading | **covered** (keep DASH-031 moving) |
| Token-efficient code navigation | code-graph capability (graphify wrap), `extract_doc_context.py` | **covered**; small gap: graph staleness scoring (folded into P2) |
| Review tiering economics | L0–L3 + scorer (DASH-019/020), fresh-review gate, audit convergence ledger | **covered**; DASH-028 risk rubric extends |
| Merge/landing of parallel branches | land-queue capability (landed as project-meta 1.15.0, PR #52, DASH-045) | **landed — priority confirmed by this research** |
| Dispatch state: claim/touch-set/capsule/budget/checkpoint | `dispatch_ledger.py` records + gates dispatch *occurrence*, but schema is thin | **gap → P1** |
| Memory staleness vs repo reality | `repo_memory.py` validates structure, not referential truth | **gap → P2** |
| Per-rule effectiveness / rule bloat | `audit --friction` (session-level), pressure-testing (adversarial, not observational) | **partial → P3** |
| Cross-session task state / re-exploration tax | board (task-grained); nothing session-grained | **gap → P4** |
| Test-integrity (assertion gaming) | adversarial review lens (prose); no deterministic detector | **gap → P5** |
| Destructive-command + env-readiness guards | hooks pack (SessionStart/PostToolUse/Stop) without these payloads | **partial → P6** |

## 2. Proposals (priority order)

### P1 — Dispatch Ledger v2: the orchestration state spine (infra, refactor)

**Evidence:** MAST 79% coordination failures; superlinear merge tax past ~4 agents (Dave
Paola, Feb 2026; Augment Code 2026); $47k runaway loop (waxell.ai); 8–13% chat-only crash
recovery; duplicate-work reports across Composio/OMC writeups. Four of six research agents
independently concluded "the dispatch ledger (or equivalent) is either absent or too thin"
and that the harness is the natural owner — it alone has pre-dispatch context *and*
post-execution authority (Stop hook, gates).

**Scope (refactor `dispatch_ledger.py` + `references/multi-agent-protocols.md`):**
- **Task-claim atomicity** — worker records `claimed_by` before starting; ledger refuses
  duplicate claims (same mechanics as inbox append-only discipline).
- **Declared touch-set + pre-dispatch overlap gate** — each dispatch declares planned file
  surfaces; conductor gets a pairwise overlap report *before* spawning (complements
  land-queue, which resolves at landing time; this prevents at dispatch time).
- **Context capsule schema** — minimal required fields the conductor must write per dispatch
  (goal, constraints, decisions-so-far, out-of-scope); addresses subagent context isolation
  (documented CLAUDE.md-not-inherited failures, e.g. claude-code#41411).
- **Budget ceiling field** — `budget_tokens` per dispatch; Stop-gate check flags exceedance
  (extends `budget_hint.py` from hint to enforceable field; stays non-predictive).
- **Worker write-back/checkpoint contract** — completed steps, touched files, open decisions;
  Stop hook validates presence, making partial work salvageable.

**Boundary:** land-queue owns landing/merge; P1 owns pre-dispatch and in-flight state. DASH-027
(blocking-decision ledger) is plan-time; the capsule references it, doesn't replace it.

### P2 — Memory staleness lint (feat, new small script)

**Evidence:** arXiv:2606.09090 names code-vs-context consistency checking as unbuilt future
work; SFEIR ~62% stale-memory figure; AgentLint: "agents trust the file more, so a stale rule
corrupts more decisions"; graph-staleness complaints (DeepWiki weekly rebuilds).

**Scope (new `memory_staleness.py`, wired into `validate` verb + `repo_memory.py` write-back
gate + `audit`):** extract referential claims from canonical memory + topical files (file
paths, script names, command invocations, anchor links); check each against the repo tree;
age-stamp entries via `git log` over cited paths; emit OK/STALE/UNKNOWN per claim. Optional
module: same scoring for code-graph freshness (`git log --since` over graph-covered paths).
Deterministic, stdlib-only, no LLM — pure `cli-toolkit-doctrine`.

### P3 — Lesson Registry + watermark hooks + per-lesson effectiveness (feat, extends harness-feedback)

**Evidence (round-2 deep dive, 2 agents):** full-loop scorecard across Devin Knowledge,
Windsurf/Cursor Memories, Claude Code auto-memory + Auto Dream, Letta Skill Learning, Mem0/
Zep, claude-reflect, self-improving-agent — **capture/dedup are crowded; promote is gated-
manual everywhere; enforce and measure are universally absent.** Nobody verifies a promoted
lesson was applied in later sessions or scores per-lesson utility. Key numbers: prose-rule
compliance ~25–40% vs hook-level ~95% (merlinmann gist, 1,480 blocks, Apr 2026; Distyl:
≤68% at 500 instructions); ACE context collapse — one monolithic rewrite dropped a playbook
18,282→122 tokens, −10pp accuracy (arXiv:2510.04618); most-automated promote trigger in the
wild = recurrence threshold 3+ hits / 2+ tasks / 30 days (self-improving-agent skill).
Validated design principles: incremental append with per-entry metadata (never monolithic
rewrite); extraction by a separate reflector pass, not the working agent; per-lesson
utility counts (ACE helpful/harmful; MemRL Q-values) + age-stamping, prune by utility not
age alone.

**Scope (extends `audit --friction` + harness-feedback capability; store mirrors the
board/ledger JSONL discipline — single-writer CLI, append-only, git-diffable; SQLite only
as an optional derived index):**
- **Lesson Registry** — `lessons.jsonl`: `id / created_at / source_session / status
  (candidate→recorded→promoted→enforced→retired) / target (memory|hook|linter) /
  helpful·harmful_count / last_validated`.
- **Watermark hooks** — registry keeps a last-processed-transcript timestamp; Stop hook
  checks (a) did this session yield candidate lessons (cheap heuristic + optional separate
  reflector pass), (b) do promoted lessons still resolve to their target file/hook (ties
  into P2 staleness lint). SessionStart injects unprocessed-lesson reminders.
- **Per-rule effectiveness**: friction events and audit findings tagged to the specific
  rule/lesson they implicate; trend across sessions; persistent-zero-value rules surface as
  inbox trim candidates (rule bloat / silent dropout).
- **Promotion ladder with enforcement preference**: lesson → memory entry (context) →
  hook/linter (enforced) wherever compilable — the 25–40%→95% compliance jump is the
  single largest validated win, and automating that translation is white space.
- Semi-automated promotion leg: validated finding → drafted candidate rule →
  `trigger_collision_check.py` + `cross_skill_redundancy.py` conflict pass → board inbox
  item with draft attached. Operator still approves; the pipeline stops being prose.

### P4 — Session receipt primitive (feat, extends repo_memory + hooks pack)

**Evidence:** re-exploration is "the hidden token tax" (Augment Code 2026); AGENTS.md
presence → −28.6% wall-clock / −16.6% tokens (arXiv:2601.20404) showing carried context pays;
planning-with-files (Manus-style 3-file pattern) requires per-task boilerplate — the harness
session boundary is the natural default owner; no mainstream tool ships carry-forward task
memory (arXiv:2605.06717).

**Scope:** Stop hook writes a structured receipt (active goal, completed, blocked, next
action, exploration memo: modules touched + dependency chain observed); SessionStart injects
the latest receipt. One small schema + two hook payload extensions. **Boundary:** board owns
task-grained durable state; the receipt is session-grained connective tissue and must stay
≤1 screen (hard cap enforced, per Hermes-style quality gate).

### P5 — Test-integrity gate (feat, new small script + ship-gate wiring)

**Evidence:** documented agent behaviors: weakened assertions, `expect(x).toBe(x)`,
test-env guards (ShapedThoughts 2025); checksummed read-only eval scripts as the
benchmark-world fix (arXiv:2603.17973); mutation testing for the agentic era (Trail of Bits
MuTON, Apr 2026); memory `adversarial-lens-earns-keep` already prescribes the *prose* lens —
this adds the deterministic floor.

**Scope (new `test_integrity_diff.py`):** diff test files before/after agent work; flag
removed assertions, widened matchers, added skips/conditionals in test bodies, deleted test
files. Advisory in `validate`, hard gate option in ship flow at strict profile. No mutation
testing in v1 (cost); leave as documented escalation.

### P6 — Hooks pack payloads: destructive-command guard + env-readiness probe (chore, extends templates/hooks)

**Evidence:** destructive incidents (Copilot `git reset --hard` wiping 4–5 days' work,
GitHub #198646; Replit prod-DB deletion, Jul 2025); only 1.1% of YOLO-mode users configure
deny rules (UpGuard, Jan 2026); agents misdiagnosing env breakage as code bugs (Ronacher,
Jun 2025); secrets: AI-assisted commits leak ~2× baseline (GitGuardian 2026).

**Scope:** PreToolUse guard for `rm -rf` / `git reset --hard` / `DROP|TRUNCATE` (profile-
laddered: warn at standard, block at strict); SessionStart env probe (canonical
test/build/lint commands resolvable; warn on credential-shaped strings in tracked files).
Pure hook-payload additions to the existing pack; no new state.

### P7 — Elastic harness: derived HARNESS_PROFILE + model-tier rule tags + reliability feedback (feat, depends on P3/DASH-028)

**Evidence (round-3, 2 agents):** the harness/token trade-off splits into three layers with
different scaling laws. (1) *In-context prose* is expensive and weak for every tier: ETH
Zurich (arXiv:2602.11988) — LLM-generated context files degrade success in 5/8 settings
(−3%, +20% cost), uniformly across model tiers; only non-discoverable facts pay rent.
(2) *Execution-flow harness* keeps paying on hard tasks regardless of tier: +13.7pp
Terminal-Bench from harness changes alone (LangChain, Feb 2026). (3) *Out-of-context gates*
(hooks/linters/CI) are ~0 context tokens and deterministic. Scaffold×model interaction is
large and real: mini-SWE-agent (~100 lines) scores 88% SWE-bench with Opus 4.8 but 21.6%
with GPT-4o (vs 48.6% under a heavy scaffold) — structural scaffolding's marginal value
collapses with model strength. Production precedents for risk-tiered oversight: Meta
DRS/RADAR (331k+ auto-landed diffs, ⅓ revert rate, 1/50 incident rate), Cloudflare 3-tier
review ($0.20/$0.67/$1.68, security paths always full). Canonical model-conditional config:
aider per-model edit formats. **White space confirmed: no product auto-derives harness
stringency from model id or measured per-task-class reliability.**

**Scope (wires existing knobs; no new engine):**
- **Profile from constant to function** — SessionStart hook derives the session's effective
  profile: `f(model_tier, risk_score [DASH-028], measured_reliability [P3 ledger])`; repo
  config sets only floor/ceiling. **Invariant core excluded from elasticity:** destructive-
  command gates, ship gates, audit convergence — blast-radius gates never scale down with
  model strength ("no model has earned the right to skip them").
- **Model-tier rule tags** (aider pattern): memory/rule entries carry `applies_below:
  <tier>`; Fable-class sessions skip remedial/structural rules, Sonnet-class workers load
  the full structured set. Directly cuts the strong-model prose tax.
- **Reliability feedback**: P3's per-rule/per-task-class data demotes rules to
  weak-model-only after N zero-friction frontier sessions; falling task-class pass rates
  auto-escalate the default review tier. Judgment comes from an external cheap scorer +
  ledger history, never model self-report (Meta DRS principle; Devin's self-confidence
  caveat).

## 3. Explicitly out of scope (researched, rejected)

- **MCP tool-sprawl management** — runtime concern (ToolSearch/deferred loading already solve
  it at the engine layer); harness-side audit adds little.
- **Cross-repo service-boundary manifests** — real gap (mabl's 75-repo writeup) but wrong
  altitude for a per-repo harness v1; revisit if a multi-repo use case lands.
- **AI-reviewer F-score tracking, flaky-test registry, structured compaction** — value
  unclear vs complexity; flaky-test work belongs to meta-debug's repro discipline anyway.
- **New orchestration engine features** — AP-COORD-7; engine execution stays with the runtime.

## 4. Sequencing & next steps

1. Operator reviews this proposal; pick the slice for the next milestone (suggested: **P1+P2**
   — the state spine and the staleness lint are independent, both pure-derived, and P1
   unblocks safer fleet use of everything else; land-queue already landed via PR #52).
2. Per `critic-before-build-canon`: dispatch a fresh adversarial critic panel against the
   chosen P's *plan* before any canon/code edit.
3. Implement via the validated-edit → ship → reload workflow; board items track state.

Board items filed (source: this proposal): P1–P6 → **DASH-046…DASH-051**, P7 → **DASH-052**;
maturity refined, status unscheduled — scheduling is a roadmap decision with the operator.
DASH-048 carries the round-2 enrichment (Lesson Registry + watermark hooks); DASH-052
depends on DASH-028 + DASH-048 (they are its risk scorer and its sensor).

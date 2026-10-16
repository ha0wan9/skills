# Bidirectional close retrospective

At every task close, the retrospective checks **both** directions and records a short,
declarative result. It is bounded: fill fields from data the run already produced — **no raw
transcript replay, no obligatory extra model pass**, and no full logs or prompts. Store
metadata and evidence **references**.

If no place to record exists in the target repo, record the two-slot summary in the task's
normal close note (or state that recording was skipped). This release ships **no second
registry and no ledger schema of its own** — reuse the target repo's existing routing/experience
store if it has one, and preserve existing records rather than rewriting them.

## 1. Both directions, every close

- **`worker_to_frontier`** — where the downstream worker struggled (retries, weak quality,
  slow) and whether frontier-direct plausibly finished faster.
- **`frontier_to_worker`** — which work currently done **upstream** could move downstream
  without degrading accepted quality. Candidates are **not** only coding: include upstream
  **orchestration, discovery, log analysis/parsing, and reporting**. Consider a deterministic
  script first in either direction.

Each direction gets one of `candidate_found` / `no_candidate` / `insufficient_evidence` /
`not_applicable` plus a one-line reason. A lone `direction` field on one record is **not**
proof both directions were considered — the two-slot per-close summary is what proves it.

## 2. Non-degradation is earned, not assumed

`non_degrading = yes` requires **all** of:

1. the **predeclared acceptance oracles** did not move **and still pass**
   (`acceptance_oracle_unchanged: true`),
2. a **predeclared quality criterion** (non-regression / non-inferiority) is met with stated
   evidence scope, and
3. a **paired same-tier comparison** exists (`paired_control: true`).

Worse measured quality ⇒ `no`. Missing or sparse evidence ⇒ `unknown`. Time and upstream-use
deltas are **tradeoffs, not quality proof**, and never infer `yes` from them. One paired test
shows non-degradation **for that task signature and tier only** — never a universal
conclusion. Counterfactual recollections stay `proposed` / `unknown`.

The retrospective **may recommend** executor changes in either direction and **may recommend a
tier**; it never auto-selects one. **Independent final acceptance always stays upstream** —
never delegated to a self-certifying implementation worker.

## 3. Fields (declarative)

Base record per observation:

| field | meaning |
|---|---|
| `signature` | task pattern/tags, the match key for a future similar task |
| `environment` | repo / interpreter / host (model-agnostic) |
| `harness`, `model_version` | worker harness and underlying model+version, kept separate |
| `outcome`, `failure_dimension` | success/partial/fail plus which axis (correctness, coverage, bugs, time…) |
| `quality_evidence` | short evidence, references not transcripts |
| `worker_time`, `frontier_time`, `elapsed_time` | observed values, `null` when unknown |
| `frontier_consumption`, `proxy` | exact upstream tokens if the host exposes them, else a labeled proxy |
| `route_this`, `route_next`, `rationale` | what ran, the conditional next route, why |
| `confidence`, `evidence_refs`, `refresh_trigger` | limited-confidence label, refs, and when the route goes stale (backend/model/env change or new counted counterevidence) |
| `status` | `proposed` / `supervisor_review_pending` — never self-accepted |

Bidirectional additions:

| field | meaning |
|---|---|
| `direction` | `worker_to_frontier` \| `frontier_to_worker` |
| `per_close_check` | **both** slots filled every close, each `candidate_found` \| `no_candidate` \| `insufficient_evidence` \| `not_applicable` + short reason |
| `current_executor`, `proposed_executor` | worker · frontier-direct · script · pipeline |
| `stage` | coding · orchestration · discovery · log-parsing · reporting · review |
| `acceptance_oracle_unchanged` | bool / `unknown` — the predeclared checks did not move and still pass |
| `quality_criterion` | predeclared non-regression/non-inferiority criterion + evidence scope, or `unknown` |
| `paired_control` | bool — a controlled same-tier comparison exists (`false` almost always) |
| `delta` | `{accepted_quality, elapsed_time, codex_use}`, each measured or `null` |
| `non_degrading` | `yes` / `no` / `unknown` per §2 |
| `tier_recommendation` | free text, advisory only, never auto-applied |

**Example shape only — not an observation, and no measured delta:**

```jsonc
{"direction":"frontier_to_worker",
 "per_close_check":{"worker_to_frontier":"no_candidate","frontier_to_worker":"candidate_found: log-parsing"},
 "current_executor":"frontier","proposed_executor":"worker",
 "stage":"log-parsing","acceptance_oracle_unchanged":true,
 "quality_criterion":"unknown","paired_control":false,
 "delta":{"accepted_quality":null,"elapsed_time":null,"codex_use":null},
 "non_degrading":"unknown","tier_recommendation":"advisory — human selects, never auto-applied"}
```

## 4. Close trigger and honesty guards

There is **no automatic close hook in this release**. If the host genuinely exposes a close
event, use it; otherwise the upstream host explicitly declares the close. **Never guess
idle = end.**

- Route from a closed record only to the **matching signature** — a conditional next route,
  not a global blacklist built from one failure.
- The worker is **optional** next time: frontier-direct is a legitimate route when evidence
  supports it, and a forced worker re-trial per occurrence is not required.
- Re-read a record when its `refresh_trigger` fires — deliberately, not as an automatic retry.
- Seed records from real conversations only. Never fabricate paired frontier-vs-worker timings
  that were not measured, and never present a labeled proxy as an exact count.

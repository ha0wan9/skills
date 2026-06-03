# Case file — cache null-deref under concurrent eviction

The bounded, single-source-of-truth artifact the phase-1 clean-context collector
produces. Every later agent (hypothesis prober, candidate workers, validators)
reads *this*, never the whole repo (AP-DBG-6 / project-meta AP-COORD-5).

## Bug statement
`GET /v1/profile/:id` intermittently 500s in prod (~0.3% of reads under load).
Stack trace: `AttributeError: 'NoneType' object has no attribute 'fields'` in
`cache.get()`. Never reproduces in local dev or staging at low concurrency.

## Environment
- prod: 8 app pods, shared in-process LRU+TTL cache, ~2k req/s/pod
- local: single process, low concurrency → never fails
- first seen: after deploy `v4.2.0` (added TTL eviction to the cache)

## Suspected area (NOT a conclusion — to be probed)
`cache/lru_ttl.py`: `evict_expired()` runs on a timer thread; `get()` reads on
request threads. No lock observed across the evict/read boundary.

## Constraints
- latency budget: `cache.get()` p99 < 0.5ms (hot path) — a fix may not add
  measurable read latency
- compat: cache API is internal; signature changes are cheap
- no new runtime dependencies (execution-policy MUST-STOP)

## Cited memory excerpts (path + why)
- `agents/concurrency.md` → "all shared-mutable cache access goes through
  `with entry.lock`" — *why*: the suspected code path appears to bypass this rule.
- `agents/perf.md` → "cache.get is on the profile hot path; guard added latency" —
  *why*: constrains which fixes are acceptable (rules out a coarse global lock).

## Prior related lessons (state/lessons.jsonl, project-meta canonical memory)
- none for this subsystem yet — this session is expected to create the first.

## Out of scope
Serializer, transport, DB layer — unless a probe implicates them. (It didn't: the
serializer hypothesis H2 was probed and refuted.)

# Example: cache null-deref (works locally, 500s in prod)

A reference end-to-end `meta-debug` session — a concurrency race in a cache layer
that only surfaces under prod load. Point-in-time snapshot; re-render rather than
hand-edit (see `writing-skills.md` Examples Folder).

- **Skill version**: meta-debug (post-audit-fixes)
- **Track**: deterministic · **Severity**: sev2 · **Outcome**: fixed
- **Session**: `state/debug-sessions/dbg-20260603T165614Z.json`
- **Lesson**: `state/lessons.jsonl`
- **Case file**: [`case-file.md`](case-file.md)

## What it demonstrates (coverage)

Every pipeline phase and gate, plus the discipline the gates enforce:

| Aspect | In this example |
|---|---|
| **All 5 gates green** | reproduce · tests · hypotheses · validate · prod |
| **Deterministic repro before fixing** (AP-DBG-1) | `pytest …::test_concurrent_evict`, 7/10 fail at seed 1337 |
| **Red test wired into existing CI** (AP-DBG-2) | added to the `unit` CI job, not a throwaway script |
| **Root cause confirmed by a probe** (AP-DBG-3) | H1 confirmed (lock-held assert), **H2 refuted** and recorded |
| **≥2 candidates, adversarial critic** (AP-DBG-4) | `fix-lock` (winner, avg 7.0) vs `fix-copy-on-read` (dropped, 6.25) |
| **Reversible prod step** (AP-DBG-5) | canary 10%/30m, rollback trigger `5xx>0.1%`, window passed |
| **Lesson recorded + promotable** | root cause + refuted H2 + fix written to `lessons.jsonl` |
| **Checkpoint** | `pre-prod@hypotheses` (ref `abc1234`) for rollback |

## Reproduce this session

```bash
DBG=skills/meta-debug/scripts/debug_session.py
python3 $DBG show dbg-20260603T165614Z --state-dir skills/meta-debug/examples/null-deref-cache/state
```

State here lives under the example dir via `--state-dir`; a real run defaults to
`<repo-root>/.harness/meta-debug/` (never the skill's install dir — AP-SKL-6).

To run the automated smoke test (non-interactive, exits 0 on success):

```bash
bash skills/meta-debug/tests/smoke_test.sh
```

## Smoke test

This example doubles as the script smoke test: every `debug_session.py` subcommand
(`start`, `phase`, `hypothesis` add/confirm/refute, `candidate`, `checkpoint`,
`close`, `show`) was exercised to produce the artifacts above, with the gate
ordering enforced throughout. The smoke test at
[`tests/smoke_test.sh`](../../tests/smoke_test.sh) runs `show` and `list` against
this example's `--state-dir`, asserting exit 0.

#!/usr/bin/env python3
"""Audit convergence governance: round ledger + mechanical gate for the
"final audits are multi-round" MUST (recipes/audit.md, Convergence loop /
workflow step 8). NOT the dispatch ledger — multi-agent dispatch governance
lives in dispatch_ledger.py (AP-COORD-1).

The recipe owns the judgment (what is a finding, what severity); this script
does the two deterministic halves:

  - record/validate/query — the auditable round trail: one row per audit round
    (blockers/majors counts + optional finding slugs), per-round acks while a
    fix is in progress, and a final/close row — including the operator
    override at the cap (--accept-residuals), which is a persistent ledger
    row, never an ephemeral marker
  - gate                  — open + red transaction => exit 1 (Stop hook step 6
    advisory/strict; ship_plugin.sh land refuses to merge)

Transactions are implicit (no start/close lifecycle commands): the first
release-gated round row opens one; a `record --final` row closes it. Rows
carry branch + git sha + session id so the trail is reviewable and a stale
ledger from another branch never blocks unrelated work.

Gate predicate (deterministic; rows filtered to the current branch):
  no round rows ............................ 0 (no audit claimed — gates never
                                               force audits to happen)
  final row after the last round row ....... 0 (closed; override printed if
                                               --accept-residuals was used)
  last round green (B+M == 0) .............. 0 (converged; suggest --final)
  last round older than 72h ................ 0 + stale warning (zombie txn)
  last round red, round >= 4 ............... 1 CAP — acks are NOT honored at
                                               the cap; only an operator
                                               --final --accept-residuals row
  last round red, acked this round ......... 0 (fix in progress, one ack per
                                               round — the ack is a ledger row)
  last round red, no ack ................... 1 (re-audit required)

Trigger boundary (recipes/audit.md step 8): a transaction is opened when and
only when a final audit gates a ship/release (`--gate release`). Ordinary
L1/L2 delivery reviews MUST NOT record rounds here.

Usage (NB: --target-root is a top-level flag — it goes BEFORE the subcommand):
    python3 audit_ledger.py --target-root . record --round 1 --gate release \
        --blockers 2 --majors 3 [--minors 4] [--findings "AP-MEM-3,stale-refs"]
    python3 audit_ledger.py --target-root . record --ack --round 1 --note "fixing"
    python3 audit_ledger.py --target-root . record --final \
        [--accept-residuals "operator: ship with known MINOR risk"]
    python3 audit_ledger.py --target-root . gate
    python3 audit_ledger.py --target-root . query
    python3 audit_ledger.py --target-root . validate
    python3 audit_ledger.py --self-test

Exit: record/validate/query 0 ok | 1 problem | 2 bad invocation.
gate 0 = ok | 1 = convergence required before ship. Standard library only.
Profile-aware via $HARNESS_PROFILE (minimal disables the gate).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

LEDGER = ".harness/audit-ledger.jsonl"
GATE_TYPES = {"release"}
ROUND_CAP = 4          # Round 1 = initial pass; re-audits 2-4; cap triggers at 4
STALE_HOURS = 72       # a red round older than this no longer blocks (zombie txn)


def _profile() -> str:
    return os.environ.get("HARNESS_PROFILE", "standard")


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""


def _is_git(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-inside-work-tree")[0] == 0


def _branch(root: Path) -> str:
    code, out = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return out if code == 0 else ""


def _sha(root: Path) -> str:
    code, out = _git(root, "rev-parse", "--short", "HEAD")
    return out if code == 0 else ""


def _session() -> str:
    return os.environ.get("CLAUDE_SESSION_ID", "") or os.environ.get("CODEX_SESSION_ID", "")


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _ledger_path(root: Path) -> Path:
    return root / LEDGER


def _read_ledger(root: Path) -> list[dict]:
    p = _ledger_path(root)
    if not p.is_file():
        return []
    rows = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{LEDGER}:{i}: invalid JSON ({exc})") from exc
    return rows


def _append(root: Path, row: dict) -> None:
    p = _ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _branch_rows(rows: list[dict], branch: str) -> list[dict]:
    return [r for r in rows if r.get("branch", "") == branch]


def _last_of(rows: list[dict], kind: str) -> tuple[int, dict | None]:
    """(index, row) of the last row of `kind`, or (-1, None)."""
    for i in range(len(rows) - 1, -1, -1):
        if rows[i].get("kind") == kind:
            return i, rows[i]
    return -1, None


def cmd_record(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    branch = _branch(root)
    modes = sum(1 for m in (args.ack, args.final) if m)
    if modes > 1:
        print("record: --ack and --final are mutually exclusive", file=sys.stderr)
        return 2
    try:
        rows = _branch_rows(_read_ledger(root), branch)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    _, last_round = _last_of(rows, "round")

    base = {
        "utc": _now().isoformat(timespec="seconds"),
        "branch": branch,
        "git_sha": _sha(root),
        "session": _session(),
    }

    if args.ack:
        if args.round is None:
            print("record --ack requires --round", file=sys.stderr)
            return 2
        if not last_round or last_round.get("round") != args.round:
            print(f"record --ack: round {args.round} is not the current round", file=sys.stderr)
            return 2
        if args.round >= ROUND_CAP:
            print(f"record --ack: acks are not honored at the cap (Round {ROUND_CAP}); "
                  "only `record --final --accept-residuals` (operator override) passes the gate",
                  file=sys.stderr)
            return 2
        _append(root, {**base, "kind": "ack", "round": args.round, "note": args.note or ""})
        print(f"acked round {args.round} (fix in progress) to {LEDGER}")
        return 0

    if args.final:
        if not last_round:
            print("record --final: no round rows for this branch — nothing to close", file=sys.stderr)
            return 2
        red = (last_round.get("blockers", 0) + last_round.get("majors", 0)) > 0
        if red and not args.accept_residuals:
            print("record --final: last round is red — an operator override requires "
                  "--accept-residuals \"reason\" (this is a persistent, auditable ledger row)",
                  file=sys.stderr)
            return 2
        _append(root, {**base, "kind": "final", "round": last_round.get("round", 0),
                       "accept_residuals": args.accept_residuals or ""})
        verdict = "override (residuals accepted)" if red else "clean"
        print(f"closed audit transaction at round {last_round.get('round')} — {verdict}")
        return 0

    # round mode
    if args.round is None or args.blockers is None or args.majors is None:
        print("record (round mode) requires --round, --blockers, --majors", file=sys.stderr)
        return 2
    if args.gate_type not in GATE_TYPES:
        print(f"--gate must be one of {sorted(GATE_TYPES)}", file=sys.stderr)
        return 2
    expected = (last_round.get("round", 0) + 1) if last_round else 1
    fi, _ = _last_of(rows, "final")
    ri, _ = _last_of(rows, "round")
    if fi > ri:
        expected = 1  # previous transaction closed; this row opens a new one
    if args.round != expected:
        print(f"record: expected round {expected} (rounds are sequential per transaction), got {args.round}",
              file=sys.stderr)
        return 2
    if args.round > ROUND_CAP:
        print(f"record: Round {ROUND_CAP} is the cap — do not ship; hand residuals to the operator "
              "(recipes/audit.md, Convergence loop)", file=sys.stderr)
        return 2
    _append(root, {**base, "kind": "round", "round": args.round, "gate_type": args.gate_type,
                   "blockers": args.blockers, "majors": args.majors, "minors": args.minors or 0,
                   "findings": args.findings or ""})
    state = "red" if (args.blockers + args.majors) > 0 else "green"
    print(f"recorded round {args.round} ({state}: B={args.blockers} M={args.majors}) to {LEDGER}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    try:
        rows = _read_ledger(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    problems: list[str] = []
    for i, row in enumerate(rows, 1):
        kind = row.get("kind")
        if kind not in {"round", "ack", "final"}:
            problems.append(f"row {i}: bad kind {kind!r}")
            continue
        if kind == "round":
            for k in ("round", "blockers", "majors"):
                if not isinstance(row.get(k), int):
                    problems.append(f"row {i}: missing/non-int {k}")
            if row.get("gate_type") not in GATE_TYPES:
                problems.append(f"row {i}: bad gate_type {row.get('gate_type')!r}")
        if kind in {"ack", "final"} and not isinstance(row.get("round"), int):
            problems.append(f"row {i}: missing/non-int round")
    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    print(f"PASS audit ledger ok ({len(rows)} row(s))")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    try:
        rows = _read_ledger(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    branch = _branch(root)
    mine = _branch_rows(rows, branch)
    print(f"[audit] {len(mine)} row(s) on branch {branch or '<none>'} ({len(rows)} total)")
    for r in mine[-args.last:] if args.last else mine:
        if r.get("kind") == "round":
            state = "red" if (r.get("blockers", 0) + r.get("majors", 0)) > 0 else "green"
            extra = f"B={r.get('blockers')} M={r.get('majors')} {state}  {r.get('findings', '')}"
        elif r.get("kind") == "ack":
            extra = f"ack  {r.get('note', '')}"
        else:
            extra = f"final  {r.get('accept_residuals', '') or 'clean'}"
        print(f"  {r.get('utc','?')}  round {r.get('round','?')}  {extra}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    if _profile() == "minimal":
        return 0
    root = Path(args.target_root).expanduser().resolve()
    if not _is_git(root):
        return 0
    try:
        rows = _branch_rows(_read_ledger(root), _branch(root))
    except ValueError as exc:
        # A corrupt ledger must not brick the harness: warn, fail open.
        print(f"[audit] WARNING: unreadable ledger, gate skipped ({exc})", file=sys.stderr)
        return 0
    ri, last_round = _last_of(rows, "round")
    if not last_round:
        return 0
    fi, last_final = _last_of(rows, "final")
    if fi > ri:
        if last_final and last_final.get("accept_residuals"):
            print(f"[audit] note: transaction closed by operator override at round "
                  f"{last_final.get('round')}: {last_final['accept_residuals']}", file=sys.stderr)
        return 0
    red = (last_round.get("blockers", 0) + last_round.get("majors", 0)) > 0
    if not red:
        print("[audit] last round is green — close the transaction with "
              "`audit_ledger.py record --final`.", file=sys.stderr)
        return 0
    try:
        age_h = (_now() - datetime.datetime.fromisoformat(last_round["utc"])).total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        # TypeError: naive (hand-edited) timestamp minus aware now. Corrupt
        # timestamps are treated as non-stale — never fail closed on bad data.
        age_h = 0.0
    if age_h > STALE_HOURS:
        print(f"[audit] WARNING: red round {last_round.get('round')} is {age_h:.0f}h old (> {STALE_HOURS}h) "
              "— treated as a stale/abandoned transaction; record a new round or --final to resume.",
              file=sys.stderr)
        return 0
    rnd = last_round.get("round", 0)
    if rnd >= ROUND_CAP:
        print(f"[audit] CAP: round {rnd} is still red (B={last_round.get('blockers')} "
              f"M={last_round.get('majors')}) — the Convergence loop is exhausted. DO NOT SHIP. "
              "Hand the operator the round trail (`audit_ledger.py query`); the only path through this "
              "gate is an operator override: `audit_ledger.py record --final --accept-residuals \"reason\"`.",
              file=sys.stderr)
        return 1
    ai, last_ack = _last_of(rows, "ack")
    if last_ack and last_ack.get("round") == rnd and ai > ri:
        print(f"[audit] fix in progress (round {rnd} acked) — record round {rnd + 1} after re-audit.",
              file=sys.stderr)
        return 0
    print(f"[audit] convergence gate: round {rnd} is red (B={last_round.get('blockers')} "
          f"M={last_round.get('majors')}) — final audits are multi-round (recipes/audit.md step 8). "
          f"Fix, then record the re-audit (`audit_ledger.py record --round {rnd + 1} --gate release ...`), "
          f"or mark the fix in progress (`audit_ledger.py record --ack --round {rnd}`).",
          file=sys.stderr)
    return 1


def _self_test() -> int:
    import tempfile
    fails: list[str] = []

    def check(name: str, got: int, want: int) -> None:
        if got != want:
            fails.append(f"{name}: exit {got}, want {want}")

    with tempfile.TemporaryDirectory() as td:
        os.environ.pop("HARNESS_PROFILE", None)
        subprocess.run(["git", "init", "-q", "-b", "main", td], check=True, capture_output=True)
        subprocess.run(["git", "-C", td, "commit", "--allow-empty", "-q", "-m", "x",
                        "-c", "user.email=t@t", "-c", "user.name=t"],
                       check=False, capture_output=True)
        run = lambda *a: main(["--target-root", td, *a])
        check("gate/no-ledger", run("gate"), 0)
        check("record/r1-red", run("record", "--round", "1", "--gate", "release",
                                   "--blockers", "1", "--majors", "2"), 0)
        check("gate/red-blocks", run("gate"), 1)
        check("record/ack-r1", run("record", "--ack", "--round", "1", "--note", "fixing"), 0)
        check("gate/acked-passes", run("gate"), 0)
        check("record/skip-round-rejected",
              run("record", "--round", "3", "--gate", "release", "--blockers", "0", "--majors", "0"), 2)
        check("record/r2-green", run("record", "--round", "2", "--gate", "release",
                                     "--blockers", "0", "--majors", "0"), 0)
        check("gate/green-passes", run("gate"), 0)
        check("final/clean", run("record", "--final"), 0)
        check("gate/closed", run("gate"), 0)
        # second transaction: ride to the cap
        for n, b in ((1, 2), (2, 2), (3, 1), (4, 1)):
            check(f"record/t2-r{n}", run("record", "--round", str(n), "--gate", "release",
                                         "--blockers", str(b), "--majors", "0"), 0)
        check("gate/cap-blocks", run("gate"), 1)
        check("record/ack-at-cap-rejected", run("record", "--ack", "--round", "4"), 2)
        check("final/red-needs-reason", run("record", "--final"), 2)
        check("final/override", run("record", "--final", "--accept-residuals", "operator: ok"), 0)
        check("gate/override-passes", run("gate"), 0)
        # third transaction: a red round older than STALE_HOURS no longer blocks
        stale_utc = (_now() - datetime.timedelta(hours=STALE_HOURS + 28)).isoformat(timespec="seconds")
        _append(Path(td), {"utc": stale_utc, "branch": "main", "git_sha": "", "session": "",
                           "kind": "round", "round": 1, "gate_type": "release",
                           "blockers": 3, "majors": 0, "minors": 0, "findings": ""})
        check("gate/stale-red-passes", run("gate"), 0)
        check("validate", run("validate"), 0)
    if fails:
        for f in fails:
            print(f"SELF-TEST FAIL {f}", file=sys.stderr)
        return 1
    print("SELF-TEST PASS (21 scenario(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target-root", default=".", help="repo to operate on (default: cwd)")
    parser.add_argument("--self-test", action="store_true", help="run the deterministic gate scenarios")
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_rec = sub.add_parser("record", help="append a round / ack / final row to the ledger")
    p_rec.add_argument("--round", type=int)
    p_rec.add_argument("--gate", dest="gate_type", default="release",
                       help="audit gate type (only 'release' exists; the explicit flag is the "
                            "deliberate this-audit-gates-a-ship declaration)")
    p_rec.add_argument("--blockers", type=int)
    p_rec.add_argument("--majors", type=int)
    p_rec.add_argument("--minors", type=int)
    p_rec.add_argument("--findings", help="comma-separated finding slugs (identity across rounds)")
    p_rec.add_argument("--ack", action="store_true", help="mark the current red round as fix-in-progress")
    p_rec.add_argument("--note")
    p_rec.add_argument("--final", action="store_true", help="close the transaction")
    p_rec.add_argument("--accept-residuals",
                       help="operator override reason (required to close a red transaction)")
    p_rec.set_defaults(func=cmd_record)

    p_val = sub.add_parser("validate", help="validate the audit ledger schema")
    p_val.set_defaults(func=cmd_validate)

    p_q = sub.add_parser("query", help="print the round trail for the current branch")
    p_q.add_argument("--last", type=int, default=0, help="show only the last N rows")
    p_q.set_defaults(func=cmd_query)

    p_gate = sub.add_parser("gate", help="convergence Stop/land gate (open+red transaction => 1)")
    p_gate.set_defaults(func=cmd_gate)

    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    if not args.cmd:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

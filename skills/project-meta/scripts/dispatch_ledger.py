#!/usr/bin/env python3
"""Dispatch governance: audit ledger + mechanical gate for the multi-agent
Task Dispatch paradigm (references/multi-agent-protocols.md).

This is the *enforcement/audit* backing for dispatch — NOT a dispatch engine.
The engine (fan-out, briefing, adjudication) is the Workflow tool / Codex
Agents-SDK / the prose loop. This script does the two deterministic halves:

  - record/validate/query  — the auditable dispatch chain (Reviewer-Between-
    Subtasks "Logging": worker id, reviewer id, brief hash, verdict, comment),
    plus retro-inspect evidence (task_type + tier) for cross-run tier promotion
  - gate                   — the "Mandatory Subagent Dispatch" rule: a turn that
    edited >=2 harness files without dispatching is the AP-COORD-1 failure mode

Ships inside project-meta; dependent skills/hooks resolve it (resolve-don't-
vendor, see references/shared-cli-delegation.md). Standard library only.
Profile-aware via $HARNESS_PROFILE (minimal disables the gate).

Usage:

    # audit trail
    python3 dispatch_ledger.py record --target-root . \
        --worker w-abc --reviewer r-def --role worker --verdict PASS \
        --brief-hash 9f2c --comment "edited AGENTS.md"
    python3 dispatch_ledger.py validate --target-root .
    python3 dispatch_ledger.py query --target-root .

    # mechanical gate (Stop hook calls this)
    python3 dispatch_ledger.py gate --target-root .

Exit: record/validate/query 0 ok | 1 problem. gate 0 = ok | 1 = dispatch
required but not acknowledged. 2 = bad invocation.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

LEDGER = ".harness/dispatch-log.jsonl"
ACK_MARKER = ".harness/dispatch-ack"
VERDICTS = {"PASS", "BLOCKER", "SUGGEST", "pending"}
REQUIRED_FIELDS = ("worker", "role", "verdict")

# The "Mandatory Subagent Dispatch" file set (multi-agent-protocols.md). Editing
# >=2 of these in one turn is the dispatch trigger.
MIRROR_FILES = {
    "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md",
    ".cursor/rules/agents.md", ".opencode/instructions.md",
    "gemini-extension.json", ".gemini/instructions.md",
}


def _profile() -> str:
    return os.environ.get("HARNESS_PROFILE", "standard")


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
        # NB: do NOT .strip() — it would lstrip the first porcelain line's leading
        # status space (" M file"), corrupting line[3:] parsing in _changed_files.
        return p.returncode, p.stdout
    except FileNotFoundError:
        return 127, ""


def _is_git(root: Path) -> bool:
    return _git(root, "rev-parse", "--is-inside-work-tree")[0] == 0


def is_harness_file(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    if rel in MIRROR_FILES:
        return True
    parts = rel.split("/")
    if "agents" in parts and rel.endswith(".md"):
        return True
    if "templates" in parts or "scripts" in parts:
        return True
    if ".claude" in parts and "hooks" in parts:
        return True
    return False


def _changed_files(root: Path) -> list[str]:
    # --untracked-files=all so a brand-new untracked dir lists its files
    # individually (git otherwise collapses "agents/x.md" to "agents/", which
    # would dodge the .md harness classification and under-count the gate).
    code, out = _git(root, "status", "--porcelain", "--untracked-files=all")
    if code != 0 or not out:
        return []
    files = []
    for line in out.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


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


def cmd_record(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    if args.verdict not in VERDICTS:
        print(f"verdict must be one of {sorted(VERDICTS)}: {args.verdict}", file=sys.stderr)
        return 2
    rec = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "worker": args.worker,
        "reviewer": args.reviewer or "",
        "role": args.role,
        "verdict": args.verdict,
        "brief_hash": args.brief_hash or "",
        "comment": args.comment or "",
        # Retro-inspect evidence (multi-agent-protocols.md "Retro-inspect promotion"):
        # task_type keys cross-run tier promotion; tier is the (model, effort) attempted,
        # e.g. "sonnet/medium" or "opus/max". Both optional + free-form so the ledger
        # stays decoupled from any specific tier vocabulary.
        "task_type": args.task_type or "",
        "tier": args.tier or "",
    }
    p = _ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"recorded dispatch ({args.role}/{args.verdict}) to {LEDGER}")
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
        missing = [k for k in REQUIRED_FIELDS if not row.get(k)]
        if missing:
            problems.append(f"row {i}: missing {', '.join(missing)}")
        if row.get("verdict") and row["verdict"] not in VERDICTS:
            problems.append(f"row {i}: bad verdict {row['verdict']}")
    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    print(f"PASS dispatch ledger ok ({len(rows)} record(s))")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    try:
        rows = _read_ledger(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    blockers = [r for r in rows if r.get("verdict") == "BLOCKER"]
    print(f"[dispatch] {len(rows)} record(s); {len(blockers)} BLOCKER(s)")
    for r in rows[-args.last :] if args.last else rows:
        print(f"  {r.get('utc','?')}  {r.get('role','?')}/{r.get('verdict','?')}  {r.get('comment','')}")
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    if _profile() == "minimal":
        return 0
    root = Path(args.target_root).expanduser().resolve()
    if not _is_git(root):
        return 0
    ack = root / ACK_MARKER
    if ack.is_file():
        # One-shot: honor + consume, like the write-back ack. Prevents a stale
        # marker from permanently disabling the gate.
        try:
            ack.unlink()
        except OSError:
            pass
        return 0
    harness = [f for f in _changed_files(root) if is_harness_file(f)]
    if len(harness) < 2:
        return 0
    print(
        f"[dispatch] mandatory-dispatch check: {len(harness)} harness files changed this turn "
        "without an acknowledged dispatch — this is the AP-COORD-1 pattern (conductor editing "
        "multiple harness files instead of dispatching Workers + Reviewer).",
        file=sys.stderr,
    )
    for f in harness[:12]:
        print(f"    {f}", file=sys.stderr)
    print(
        "[dispatch] resolve: dispatch per-file Worker+Reviewer and log via "
        "`dispatch_ledger.py record`, OR acknowledge a deliberate bypass "
        f"(`touch {ACK_MARKER}`, naming the AP-COORD-* rule in the delivery). "
        "See references/multi-agent-protocols.md#mandatory-subagent-dispatch.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target-root", default=".", help="repo to operate on (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rec = sub.add_parser("record", help="append a dispatch record to the ledger")
    p_rec.add_argument("--worker", required=True)
    p_rec.add_argument("--reviewer")
    p_rec.add_argument("--role", required=True, choices=["lead", "planner", "explorer", "worker", "reviewer"])
    p_rec.add_argument("--verdict", default="pending")
    p_rec.add_argument("--brief-hash")
    p_rec.add_argument("--comment")
    p_rec.add_argument("--task-type", help="retro-inspect key: the kind of subtask (e.g. 'reviewer:methodology')")
    p_rec.add_argument("--tier", help="the (model, effort) attempted, e.g. 'sonnet/medium' or 'opus/max'")
    p_rec.set_defaults(func=cmd_record)

    p_val = sub.add_parser("validate", help="validate the dispatch ledger schema")
    p_val.set_defaults(func=cmd_validate)

    p_q = sub.add_parser("query", help="summarize the dispatch chain")
    p_q.add_argument("--last", type=int, default=0, help="show only the last N records")
    p_q.set_defaults(func=cmd_query)

    p_gate = sub.add_parser("gate", help="mandatory-dispatch Stop gate (>=2 harness files, no ack)")
    p_gate.set_defaults(func=cmd_gate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

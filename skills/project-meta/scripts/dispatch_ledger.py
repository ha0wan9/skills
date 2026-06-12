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

v2 schema additions (schema_version >= 2 rows only):
  - claim / overlap   — atomic task-claim atomicity + pairwise touch-set overlap
  - touch_set         — list of files a dispatch record touches
  - capsule           — context package (goal, constraints, decisions, out_of_scope)
  - budget_tokens / spent_tokens — optional budget envelope
  - checkpoint        — completed/touched_files/open_decisions at Stop

Ships inside project-meta; dependent skills/hooks resolve it (resolve-don't-
vendor, see references/shared-cli-delegation.md). Standard library only.
Profile-aware via $HARNESS_PROFILE (minimal disables the gate).

Usage:

    # audit trail (v1)
    python3 dispatch_ledger.py record --target-root . \\
        --worker w-abc --reviewer r-def --role worker --verdict PASS \\
        --brief-hash 9f2c --comment "edited AGENTS.md"
    python3 dispatch_ledger.py validate --target-root .
    python3 dispatch_ledger.py query --target-root .

    # atomic task claim (v2)
    python3 dispatch_ledger.py --target-root . claim --task T1 --worker w1
    # → exit 0 first time; exit 1 "duplicate claim" on second claim of T1

    # touch-set overlap detection (v2)
    python3 dispatch_ledger.py --target-root . overlap
    # → exit 0 if no overlaps; exit 1 + report if any pairwise overlap exists

    # v2 record with full capsule + budget + checkpoint
    python3 dispatch_ledger.py --target-root . record \\
        --worker w-abc --role worker --verdict PASS \\
        --touch-set "a.py,b.py" \\
        --capsule-goal "implement X" --capsule-constraints "stdlib only" \\
        --capsule-decisions "used approach Y" --capsule-out-of-scope "Z" \\
        --budget-tokens 10000 --spent-tokens 8000 \\
        --checkpoint '{"completed": ["step1"], "touched_files": ["a.py"], "open_decisions": []}' \\
        --schema-version 2

    # mechanical gate (Stop hook calls this)
    python3 dispatch_ledger.py gate --target-root .

Exit: record/validate/query/claim/overlap 0 ok | 1 problem. gate 0 = ok | 1 =
dispatch required but not acknowledged. 2 = bad invocation.
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
CLAIMS = ".harness/dispatch-claims.jsonl"
ACK_MARKER = ".harness/dispatch-ack"
VERDICTS = {"PASS", "BLOCKER", "SUGGEST", "pending"}
REQUIRED_FIELDS = ("worker", "role", "verdict")

# v2 capsule sub-fields required when schema_version >= 2
CAPSULE_FIELDS = ("goal", "constraints", "decisions", "out_of_scope")
# v2 checkpoint sub-fields required when schema_version >= 2
CHECKPOINT_FIELDS = ("completed", "touched_files", "open_decisions")

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


def _claims_path(root: Path) -> Path:
    return root / CLAIMS


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


def _read_claims(root: Path) -> list[dict]:
    p = _claims_path(root)
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
            raise ValueError(f"{CLAIMS}:{i}: invalid JSON ({exc})") from exc
    return rows


def _parse_touch_set(raw: str) -> list[str]:
    """Parse a comma-separated touch-set string into a sorted deduplicated list."""
    return sorted(set(p.strip() for p in raw.split(",") if p.strip()))


def _parse_capsule_args(args: argparse.Namespace) -> dict | None:
    """Build a capsule dict from --capsule-* args or --capsule JSON arg.

    Returns None if no capsule args are present (v1-compatible record).
    """
    # --capsule JSON overrides individual --capsule-* args
    if hasattr(args, "capsule") and args.capsule:
        try:
            obj = json.loads(args.capsule)
        except json.JSONDecodeError as exc:
            raise ValueError(f"--capsule: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise ValueError("--capsule: must be a JSON object")
        return obj

    parts = {
        "goal": getattr(args, "capsule_goal", None) or "",
        "constraints": getattr(args, "capsule_constraints", None) or "",
        "decisions": getattr(args, "capsule_decisions", None) or "",
        "out_of_scope": getattr(args, "capsule_out_of_scope", None) or "",
    }
    # If every field is empty, treat as absent (v1 path)
    if not any(parts.values()):
        return None
    return parts


def _parse_checkpoint_arg(args: argparse.Namespace) -> dict | None:
    """Parse --checkpoint JSON arg."""
    raw = getattr(args, "checkpoint", None)
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--checkpoint: invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("--checkpoint: must be a JSON object")
    return obj


def cmd_record(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    if args.verdict not in VERDICTS:
        print(f"verdict must be one of {sorted(VERDICTS)}: {args.verdict}", file=sys.stderr)
        return 2

    # Parse optional v2 fields
    try:
        capsule = _parse_capsule_args(args)
        checkpoint = _parse_checkpoint_arg(args)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 2

    schema_version = getattr(args, "schema_version", None)

    rec: dict = {
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

    # v2 fields — only emit when provided to keep v1-produced rows clean
    if schema_version is not None:
        rec["schema_version"] = schema_version
    if hasattr(args, "touch_set") and args.touch_set:
        rec["touch_set"] = _parse_touch_set(args.touch_set)
    if capsule is not None:
        rec["capsule"] = capsule
    if hasattr(args, "budget_tokens") and args.budget_tokens is not None:
        rec["budget_tokens"] = args.budget_tokens
    if hasattr(args, "spent_tokens") and args.spent_tokens is not None:
        rec["spent_tokens"] = args.spent_tokens
    if checkpoint is not None:
        rec["checkpoint"] = checkpoint

    p = _ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"recorded dispatch ({args.role}/{args.verdict}) to {LEDGER}")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    """Atomically claim a task id for a worker.

    Append-only: a task id may only be claimed once. A second claim on the
    same task id is rejected (exit 1) regardless of worker.  The claims file
    is separate from the main ledger so it can be checked without loading the
    full audit chain.
    """
    root = Path(args.target_root).expanduser().resolve()
    task_id = args.task
    worker = args.worker

    p = _claims_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Read existing claims and check for duplicate
    try:
        existing = _read_claims(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    for row in existing:
        if row.get("task") == task_id:
            claimed_by = row.get("claimed_by", "?")
            print(
                f"duplicate claim: task {task_id!r} already claimed by {claimed_by!r}",
                file=sys.stderr,
            )
            return 1

    # Append-only write: write the new claim
    rec = {
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "task": task_id,
        "claimed_by": worker,
    }
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"claimed task {task_id!r} for worker {worker!r}")
    return 0


def cmd_overlap(args: argparse.Namespace) -> int:
    """Pairwise touch-set overlap report across recorded dispatches.

    Reads all ledger rows that have a non-empty touch_set. For every pair of
    such rows, computes the intersection. If any intersection is non-empty,
    exits 1 and prints a report naming both workers and the overlapping paths.
    Exits 0 when all touch-sets are disjoint (or there are fewer than 2 rows
    with touch sets).
    """
    root = Path(args.target_root).expanduser().resolve()
    try:
        rows = _read_ledger(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    # Collect rows that carry a touch_set
    touching: list[dict] = [r for r in rows if r.get("touch_set")]
    found_overlap = False

    for i in range(len(touching)):
        for j in range(i + 1, len(touching)):
            a = touching[i]
            b = touching[j]
            set_a = set(a["touch_set"])
            set_b = set(b["touch_set"])
            common = sorted(set_a & set_b)
            if common:
                w_a = a.get("worker", "?")
                w_b = b.get("worker", "?")
                paths = ", ".join(common)
                print(
                    f"OVERLAP: workers {w_a!r} and {w_b!r} both touch: {paths}",
                    file=sys.stderr,
                )
                found_overlap = True

    if found_overlap:
        return 1
    print("overlap: no touch-set overlaps detected")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.target_root).expanduser().resolve()
    try:
        rows = _read_ledger(root)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1

    problems: list[str] = []
    advisories: list[str] = []

    for i, row in enumerate(rows, 1):
        sv = row.get("schema_version")

        # v1 floor — applies to all rows regardless of schema_version
        missing = [k for k in REQUIRED_FIELDS if not row.get(k)]
        if missing:
            problems.append(f"row {i}: missing {', '.join(missing)}")
        if row.get("verdict") and row["verdict"] not in VERDICTS:
            problems.append(f"row {i}: bad verdict {row['verdict']}")

        # v2 validations — only for rows explicitly marked schema_version >= 2
        if sv is not None and sv >= 2:
            # capsule completeness
            capsule = row.get("capsule")
            if not isinstance(capsule, dict):
                problems.append(f"row {i}: schema_version {sv}: missing capsule object")
            else:
                for field in CAPSULE_FIELDS:
                    if not capsule.get(field):
                        problems.append(
                            f"row {i}: schema_version {sv}: capsule missing required field '{field}'"
                        )

            # checkpoint completeness
            checkpoint = row.get("checkpoint")
            if not isinstance(checkpoint, dict):
                problems.append(f"row {i}: schema_version {sv}: missing checkpoint object")
            else:
                for field in CHECKPOINT_FIELDS:
                    if field not in checkpoint:
                        problems.append(
                            f"row {i}: schema_version {sv}: checkpoint missing required field '{field}'"
                        )

            # budget advisory (not a hard error)
            budget = row.get("budget_tokens")
            spent = row.get("spent_tokens")
            if budget is not None and spent is not None:
                try:
                    if int(spent) > int(budget):
                        advisories.append(
                            f"row {i}: budget exceedance: spent_tokens {spent} > budget_tokens {budget} (advisory)"
                        )
                except (TypeError, ValueError):
                    pass

    for advisory in advisories:
        print(f"ADVISORY {advisory}")

    if problems:
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1

    v2_count = sum(1 for r in rows if r.get("schema_version") is not None and r["schema_version"] >= 2)
    print(f"PASS dispatch ledger ok ({len(rows)} record(s), {v2_count} v2)")
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
    # v2 fields
    p_rec.add_argument("--touch-set", help="comma-separated list of files this dispatch touches")
    p_rec.add_argument("--capsule", help="context package as a JSON object (overrides --capsule-* args)")
    p_rec.add_argument("--capsule-goal", help="capsule: goal for this dispatch")
    p_rec.add_argument("--capsule-constraints", help="capsule: constraints for this dispatch")
    p_rec.add_argument("--capsule-decisions", help="capsule: decisions recorded")
    p_rec.add_argument("--capsule-out-of-scope", help="capsule: out-of-scope items")
    p_rec.add_argument("--budget-tokens", type=int, help="token budget for this dispatch")
    p_rec.add_argument("--spent-tokens", type=int, help="tokens actually spent")
    p_rec.add_argument("--checkpoint", help="checkpoint state as a JSON object with completed/touched_files/open_decisions")
    p_rec.add_argument("--schema-version", type=int, default=None,
                       help="ledger schema version (default: omitted for v1 compat; pass 2 for v2 rows)")
    p_rec.set_defaults(func=cmd_record)

    p_claim = sub.add_parser("claim", help="atomically claim a task id for a worker (reject duplicates)")
    p_claim.add_argument("--task", required=True, help="task id to claim (e.g. T1, DASH-046)")
    p_claim.add_argument("--worker", required=True, help="worker id claiming the task")
    p_claim.set_defaults(func=cmd_claim)

    p_overlap = sub.add_parser("overlap", help="pairwise touch-set overlap report across ledger records")
    p_overlap.set_defaults(func=cmd_overlap)

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

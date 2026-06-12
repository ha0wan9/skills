#!/usr/bin/env python3
"""Session receipt: write/inject a per-session context capsule.

Provides two subcommands:

  write   Write (or overwrite) .harness/session-receipt.json with a structured
          receipt under --target-root. Accepts optional semantic fields
          (--goal, --done, --blocked, --next, --memo, --items). Also accepts
          --auto which records a minimal receipt from git state without
          clobbering a richer receipt written earlier in the same session
          (see --auto semantics below).

  inject  Print the latest receipt as a compact human block, hard-capped at
          30 lines. Prints nothing and exits 0 when HARNESS_PROFILE=minimal
          or when no receipt file exists.

Ships inside project-meta; dependent hooks resolve it (resolve-don't-vendor).
Standard library only. Profile-aware via $HARNESS_PROFILE.

Usage:
    python3 session_receipt.py --target-root . write --goal "fix auth" \
        --done "patched token refresh" --next "write tests" --items DASH-12
    python3 session_receipt.py --target-root . inject

Auto write (Stop hook):
    python3 session_receipt.py --target-root . write --auto
    Writes timestamp + git-branch + changed-file count. If a receipt already
    exists, is younger than 24h, AND has any semantic field (goal/done/blocked/
    next/memo), --auto is a no-op (the richer receipt is preserved).

Board pointer:
    --items accepts a comma-separated list of board item ids. These are stored
    as a pointer only — no board state is duplicated into the receipt.

Exit codes:
    0  success (or no-op for inject/auto)
    1  error (write failed; inject parse error)
    2  bad invocation
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

RECEIPT_PATH = ".harness/session-receipt.json"
SEMANTIC_FIELDS = ("goal", "done", "blocked", "next", "memo")
AUTO_PRESERVE_AGE_HOURS = 24
MAX_INJECT_LINES = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_receipt_path(target_root: str) -> Path:
    return Path(target_root) / RECEIPT_PATH


def _git_branch(root: Path) -> str:
    """Return current git branch name, or '' on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _git_changed_count(root: Path) -> int:
    """Return number of changed files (staged + unstaged) vs HEAD, or 0."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.strip().splitlines() if l]
            return len(lines)
    except Exception:
        pass
    return 0


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_rich(receipt: dict) -> bool:
    """True if the receipt has at least one non-empty semantic field."""
    return any(receipt.get(f) for f in SEMANTIC_FIELDS)


def _receipt_age_hours(receipt: dict) -> float:
    """Return age in hours of the receipt, or infinity if unparseable."""
    ts = receipt.get("written_utc", "")
    if not ts:
        return float("inf")
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - dt).total_seconds() / 3600.0
    except Exception:
        return float("inf")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_write(args: argparse.Namespace) -> int:
    root = Path(args.target_root)
    receipt_path = resolve_receipt_path(args.target_root)

    # --auto mode: skip if existing receipt is fresh + semantic
    if args.auto:
        if receipt_path.exists():
            try:
                existing = json.loads(receipt_path.read_text())
                age_h = _receipt_age_hours(existing)
                if age_h < AUTO_PRESERVE_AGE_HOURS and _is_rich(existing):
                    # Preserve the richer receipt; auto is a no-op
                    return 0
            except Exception:
                pass  # Corrupt receipt — fall through and overwrite

    # Build the receipt dict
    receipt: dict = {"written_utc": _now_utc()}

    if args.auto:
        receipt["auto"] = True
        branch = _git_branch(root)
        if branch:
            receipt["branch"] = branch
        receipt["changed_files"] = _git_changed_count(root)
    else:
        receipt["auto"] = False

    # Semantic fields (write even if None so inject can detect presence)
    for field in SEMANTIC_FIELDS:
        value = getattr(args, field, None)
        if value is not None:
            receipt[field] = value

    # Board pointer
    if args.items:
        ids = [i.strip() for i in args.items.split(",") if i.strip()]
        if ids:
            receipt["items"] = ids

    # Ensure .harness/ directory exists
    try:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    except OSError as exc:
        print(f"[session_receipt] write error: {exc}", file=sys.stderr)
        return 1

    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    # Profile gate: minimal → silent no-op
    profile = os.environ.get("HARNESS_PROFILE", "standard")
    if profile == "minimal":
        return 0

    receipt_path = resolve_receipt_path(args.target_root)
    if not receipt_path.exists():
        return 0

    try:
        receipt = json.loads(receipt_path.read_text())
    except Exception as exc:
        print(f"[session_receipt] parse error: {exc}", file=sys.stderr)
        return 1

    # Build human-readable block
    lines: list[str] = []
    lines.append("[session-receipt]")

    ts = receipt.get("written_utc", "")
    if ts:
        lines.append(f"  written: {ts}")

    branch = receipt.get("branch", "")
    if branch:
        lines.append(f"  branch:  {branch}")

    changed = receipt.get("changed_files")
    if changed is not None:
        lines.append(f"  changed-files: {changed}")

    for field in SEMANTIC_FIELDS:
        value = receipt.get(field)
        if value:
            lines.append(f"  {field}: {value}")

    items = receipt.get("items")
    if items:
        lines.append(f"  items: {', '.join(items)}")

    auto = receipt.get("auto", False)
    if auto:
        lines.append("  (auto-written at Stop; no semantic goal recorded this turn)")

    # Hard cap at MAX_INJECT_LINES
    if len(lines) > MAX_INJECT_LINES:
        lines = lines[: MAX_INJECT_LINES - 1]
        lines.append("  ...truncated")

    for line in lines:
        print(line)

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="session_receipt.py",
        description="Write/inject a per-session context receipt.",
    )
    parser.add_argument(
        "--target-root",
        default=".",
        metavar="DIR",
        help="Repo root (default: current directory).",
    )

    sub = parser.add_subparsers(dest="subcommand", metavar="subcommand")
    sub.required = True

    # write
    write_p = sub.add_parser("write", help="Write/overwrite the session receipt.")
    write_p.add_argument("--goal", default=None, help="High-level goal for this session.")
    write_p.add_argument("--done", default=None, help="What was completed.")
    write_p.add_argument("--blocked", default=None, help="Current blockers.")
    write_p.add_argument("--next", default=None, help="Next steps.")
    write_p.add_argument("--memo", default=None, help="Free-form notes.")
    write_p.add_argument(
        "--items",
        default=None,
        metavar="ID[,ID...]",
        help="Comma-separated board item ids (pointer only — no board state duplicated).",
    )
    write_p.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Auto mode: record timestamp + git branch + changed-file count. "
            "No-op when an existing receipt is younger than 24h and has semantic fields."
        ),
    )

    # inject
    sub.add_parser("inject", help="Print the current receipt (≤30 lines); silent when absent/minimal.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "write":
        return cmd_write(args)
    elif args.subcommand == "inject":
        return cmd_inject(args)
    else:
        parser.print_help(sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

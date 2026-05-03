#!/usr/bin/env python3
"""Verify phase-lock gates for the current task.

Reads `.harness/phase-state.json` (project-meta phase-lock-state.v1
schema) and runs `.harness/gates/<phase>.sh` for the current phase. Used
by the `Stop` hook to block phase transitions until the previous phase's
deliverable + gate pass.

Usage:
    python3 phase_lock_check.py [--harness-dir DIR] [--phase PHASE]
                                [--require-pass] [--dry-run]

Modes:
    default      Read state, run the gate for the current phase, exit
                 0 on pass / non-zero on fail.
    --require-pass
                 Exit non-zero if the current phase has not had a
                 successful gate run since `started_utc`. Used by the
                 next phase's Entry to enforce the lock.
    --dry-run    Resolve gate scripts but do not execute. Useful for
                 hook-debugging.

Exit codes:
    0   gate passed (or bypass / lightweight / phase=none)
    1   gate failed
    2   bad CLI / state file missing or malformed
    3   gate script missing or non-executable

Designed to be std-lib-only and dependency-free so the Stop hook can
invoke it from any environment.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path


PHASES = ("none", "brainstorm", "plan", "implement", "review", "finish")
SCHEMA_PREFIX = "project-meta.phase-lock-state."


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(state_path: Path) -> dict:
    if not state_path.is_file():
        sys.stderr.write(
            f"phase_lock_check: state file missing at {state_path}\n"
            f"  hint: /project-meta init --workflow phase-lock should have "
            f"created it. If the contract is intentionally not installed "
            f"for this repo, do not invoke this script from hooks.\n"
        )
        sys.exit(2)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(
            f"phase_lock_check: state file invalid JSON: {e}\n"
            f"  path: {state_path}\n"
        )
        sys.exit(2)
    schema = state.get("_schema", "")
    if not schema.startswith(SCHEMA_PREFIX):
        sys.stderr.write(
            f"phase_lock_check: state file _schema {schema!r} not recognised "
            f"(expected prefix {SCHEMA_PREFIX!r})\n"
        )
        sys.exit(2)
    return state


def write_state(state_path: Path, state: dict) -> None:
    state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_gate(gate_script: Path, dry_run: bool) -> tuple[int, str]:
    if not gate_script.is_file():
        return 3, f"gate script missing: {gate_script}"
    if not os.access(gate_script, os.X_OK):
        return 3, f"gate script not executable: {gate_script}"
    if dry_run:
        return 0, f"dry-run: would invoke {gate_script}"
    try:
        proc = subprocess.run(
            [str(gate_script)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return 1, f"gate timed out: {gate_script}"
    return proc.returncode, proc.stdout + proc.stderr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--harness-dir",
        type=Path,
        default=Path(".harness"),
        help="Directory holding phase-state.json and gates/ (default .harness/).",
    )
    parser.add_argument(
        "--phase",
        choices=PHASES,
        default=None,
        help="Override the phase to check (default: read from state).",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="Fail if the current phase has no successful gate run since started_utc.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve gate but do not execute.",
    )
    args = parser.parse_args(argv)

    state_path = args.harness_dir / "phase-state.json"
    gates_dir = args.harness_dir / "gates"

    state = load_state(state_path)
    phase = args.phase or state.get("phase", "none")

    if phase == "none":
        # No active task; nothing to check.
        print("phase_lock_check: phase=none (no active task)")
        return 0

    if phase not in PHASES:
        sys.stderr.write(f"phase_lock_check: unknown phase {phase!r}\n")
        return 2

    if args.require_pass:
        last_pass = state.get("last_gate_pass_utc")
        started = state.get("started_utc")
        if not last_pass or (started and last_pass < started):
            sys.stderr.write(
                f"phase_lock_check: phase={phase} has no gate pass since "
                f"started_utc={started}; cannot advance.\n"
            )
            return 1
        print(f"phase_lock_check: phase={phase} last gate pass at {last_pass}")
        return 0

    gate_script = gates_dir / f"{phase}.sh"
    rc, output = run_gate(gate_script, args.dry_run)

    if rc == 0:
        # Update state: record gate pass time.
        state["last_gate_pass_utc"] = _utcnow()
        write_state(state_path, state)
        print(f"phase_lock_check: phase={phase} gate PASSED")
        if output.strip():
            print(output.rstrip())
        return 0

    sys.stderr.write(
        f"phase_lock_check: phase={phase} gate FAILED (rc={rc})\n"
    )
    if output.strip():
        sys.stderr.write(output.rstrip() + "\n")
    return rc if rc in (1, 3) else 1


if __name__ == "__main__":
    sys.exit(main())

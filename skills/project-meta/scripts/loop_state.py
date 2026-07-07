#!/usr/bin/env python3
"""Loop-state checkpoint primitive — the canonical `loop_state.json` file ops
declared by `references/loop-contract.md` (state/checkpoint field + stopping
rule field). Any skill running a bounded iterative loop (ratchet, survey
`/loop`, audit convergence, ...) can init/checkpoint/read/should-stop a
`loop_state.json` at a path of its choosing without hand-rolling the same
file format five times.

Subcommands:

  init         Write a fresh loop_state.json (refuses to clobber an existing
               file unless --force).
  checkpoint   Update iteration/current_task/blockers/completed_targets/
               next_targets/budget_spent in place. Increments `iteration` by
               1 unless --no-increment.
  read         Print the current loop_state.json as formatted JSON.
  should-stop  Evaluate the declared stop_conditions against the current
               state (+ optional --max-* overrides). Prints the reason
               either way.

No daemon, no timer — the loop owner calls this at loop boundaries (typically
once per iteration, at the phase boundary the loop already has).

Exit codes:
    init/checkpoint/read : 0 ok | 1 file problem | 2 bad invocation
    should-stop           : 0 continue | 1 stop (reason printed to stdout)

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_STOP_CONDITIONS = {
    "max_iterations": 8,
    "budget_spent_over_limit": False,
    "explicit_stop": False,
}


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"loop_state.py: no such file: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"loop_state.py: {path} is not valid JSON: {exc}")


def _dump(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists() and not args.force:
        print(f"loop_state.py init: {path} already exists (use --force to overwrite)", file=sys.stderr)
        return 1
    stop_conditions = dict(DEFAULT_STOP_CONDITIONS)
    stop_conditions["max_iterations"] = args.max_iterations
    state = {
        "iteration": 0,
        "current_task": args.current_task or "",
        "blockers": [],
        "completed_targets": [],
        "next_targets": [],
        "stop_conditions": stop_conditions,
        "budget_spent": {"iterations": 0, "tokens": 0, "seconds": 0},
    }
    if args.phase:
        state["phase"] = args.phase
    _dump(path, state)
    print(f"initialized {path} (max_iterations={args.max_iterations})")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    path = Path(args.path)
    state = _load(path)
    if not args.no_increment:
        state["iteration"] = int(state.get("iteration", 0)) + 1
    if args.current_task is not None:
        state["current_task"] = args.current_task
    if args.completed is not None:
        state.setdefault("completed_targets", []).append(args.completed)
    if args.next is not None:
        state.setdefault("next_targets", []).append(args.next)
        # A target moving into current_task should not linger in the queue.
        if args.current_task is not None and args.current_task in state["next_targets"]:
            state["next_targets"].remove(args.current_task)
    if args.blocker is not None:
        state.setdefault("blockers", []).append(args.blocker)
    if args.clear_blockers:
        state["blockers"] = []
    if args.phase is not None:
        state["phase"] = args.phase
    if args.explicit_stop:
        state.setdefault("stop_conditions", dict(DEFAULT_STOP_CONDITIONS))["explicit_stop"] = True

    budget = state.setdefault("budget_spent", {"iterations": 0, "tokens": 0, "seconds": 0})
    budget["iterations"] = int(budget.get("iterations", 0)) + 1
    if args.budget_tokens is not None:
        budget["tokens"] = int(budget.get("tokens", 0)) + args.budget_tokens
    if args.budget_seconds is not None:
        budget["seconds"] = int(budget.get("seconds", 0)) + args.budget_seconds

    _dump(path, state)
    print(f"checkpointed {path} (iteration={state['iteration']})")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    state = _load(Path(args.path))
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


def evaluate_stop(state: dict, max_tokens: int | None, max_seconds: int | None) -> tuple[bool, str]:
    """Return (should_stop, reason). Evaluates only the three contract-known
    conditions (explicit stop, budget exceeded, max iterations) in that
    order — domain-specific stop_conditions keys are left to the loop owner's
    own judgment and are not evaluated here (loop-contract.md field notes)."""
    stop_conditions = state.get("stop_conditions", {})
    if stop_conditions.get("explicit_stop"):
        return True, "explicit stop flag set"

    budget = state.get("budget_spent", {})
    if stop_conditions.get("budget_spent_over_limit"):
        return True, "budget_spent_over_limit flag set"
    if max_tokens is not None and int(budget.get("tokens", 0)) >= max_tokens:
        return True, f"budget exceeded: tokens {budget.get('tokens', 0)} >= max {max_tokens}"
    if max_seconds is not None and int(budget.get("seconds", 0)) >= max_seconds:
        return True, f"budget exceeded: seconds {budget.get('seconds', 0)} >= max {max_seconds}"

    max_iterations = stop_conditions.get("max_iterations")
    iteration = int(state.get("iteration", 0))
    if isinstance(max_iterations, int) and iteration >= max_iterations:
        return True, f"max_iterations reached: iteration {iteration} >= max {max_iterations}"

    return False, f"continue: iteration {iteration}/{max_iterations if max_iterations is not None else '?'}"


def cmd_should_stop(args: argparse.Namespace) -> int:
    state = _load(Path(args.path))
    stop, reason = evaluate_stop(state, args.max_tokens, args.max_seconds)
    print(reason)
    return 1 if stop else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="write a fresh loop_state.json")
    i.add_argument("path", help="path to loop_state.json")
    i.add_argument("--max-iterations", type=int, default=8)
    i.add_argument("--current-task", default="")
    i.add_argument("--phase", default=None, help="optional free-form phase label")
    i.add_argument("--force", action="store_true", help="overwrite an existing file")
    i.set_defaults(func=cmd_init)

    c = sub.add_parser("checkpoint", help="update loop_state.json in place (increments iteration)")
    c.add_argument("path", help="path to loop_state.json")
    c.add_argument("--current-task", default=None)
    c.add_argument("--completed", default=None, help="append to completed_targets")
    c.add_argument("--next", default=None, help="append to next_targets")
    c.add_argument("--blocker", default=None, help="append to blockers")
    c.add_argument("--clear-blockers", action="store_true")
    c.add_argument("--phase", default=None, help="set the optional free-form phase label")
    c.add_argument("--explicit-stop", action="store_true", help="set stop_conditions.explicit_stop")
    c.add_argument("--budget-tokens", type=int, default=None, help="tokens spent this iteration (added to running total)")
    c.add_argument("--budget-seconds", type=int, default=None, help="seconds spent this iteration (added to running total)")
    c.add_argument("--no-increment", action="store_true", help="do not increment iteration (rare — e.g. a correction checkpoint)")
    c.set_defaults(func=cmd_checkpoint)

    r = sub.add_parser("read", help="print loop_state.json")
    r.add_argument("path", help="path to loop_state.json")
    r.set_defaults(func=cmd_read)

    s = sub.add_parser("should-stop", help="evaluate stop_conditions; exit 0=continue 1=stop")
    s.add_argument("path", help="path to loop_state.json")
    s.add_argument("--max-tokens", type=int, default=None, help="override/add a token budget ceiling")
    s.add_argument("--max-seconds", type=int, default=None, help="override/add a wall-clock ceiling")
    s.set_defaults(func=cmd_should_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

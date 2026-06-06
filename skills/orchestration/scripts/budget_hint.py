#!/usr/bin/env python3
"""budget_hint.py — a coarse, NON-PREDICTIVE budget hint for an orchestration contract.

DASH-22. This is **not** a forecast. Pre-run agentic token/runtime prediction is
order-of-magnitude unreliable, so this tool deliberately refuses to pretend otherwise:
it prints a **wide** low/expected/high band whose only job is to let an operator eyeball
whether a contract is Opus-heavy or fan-out-wide and adjust tiers/parallelism *before*
signing. Every output is labelled "estimate, not a guarantee."

It does **NOT** drive the engine `budget` and cannot enable or control the engine — a
skill owns policy, the engine owns mechanism (AP-COORD-7). The numbers below are heuristic
constants, not calibrated against any cost corpus (none exists yet: `dispatch_ledger.py`
has no token/runtime fields; adding them + collecting actuals is a separate later item).

Usage:
    budget_hint.py --task <tier>:<class>:<fanout>[:<label>] [--task ...] [--json]

    <tier>   = cli | sonnet | opus       (cli = no model = 0 tokens)
    <class>  = mechanical | lint | edit | review | research | plan | hard | scaffold
               (lint≈mechanical, hard≈plan; any other value → default band, flagged with *)
    <fanout> = positive int (parallel copies of this task); default 1

Examples:
    budget_hint.py --task cli:lint:1
    budget_hint.py --task opus:hard:1 --task sonnet:review:4 --json
"""
from __future__ import annotations

import argparse
import json
import sys

DISCLAIMER = "estimate, not a guarantee — coarse heuristic, NOT a calibrated forecast"

# Expected *output* tokens for a single Sonnet-tier agent of the given work class.
# Heuristic order-of-magnitude anchors, not measurements.
CLASS_BANDS: dict[str, int] = {
    "mechanical": 1_500,
    "lint": 1_500,
    "edit": 8_000,
    "review": 6_000,
    "research": 20_000,
    "plan": 15_000,
    "hard": 15_000,
    "scaffold": 12_000,
}
DEFAULT_BAND = 8_000

# Tier multipliers. cli runs no model (0 tokens). Opus reasons more per step → more tokens.
TIER_FACTOR: dict[str, float] = {"cli": 0.0, "sonnet": 1.0, "opus": 2.5}

# Order-of-magnitude envelope around the expected value (the critic's non-predictive finding).
LOW_MULT = 0.3
HIGH_MULT = 3.0


def round100(x: float) -> int:
    return int(round(x / 100.0) * 100)


def parse_task(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError(f"task '{spec}' must be tier:class[:fanout[:label]]")
    tier = parts[0].strip().lower()
    cls = parts[1].strip().lower()
    fanout = 1
    label = ""
    if len(parts) >= 3 and parts[2].strip():
        try:
            fanout = int(parts[2])
        except ValueError as exc:
            raise ValueError(f"fanout in '{spec}' must be an integer") from exc
        if fanout < 1:
            raise ValueError(f"fanout in '{spec}' must be >= 1")
    if len(parts) >= 4:
        label = ":".join(parts[3:]).strip()
    if tier not in TIER_FACTOR:
        raise ValueError(f"unknown tier '{tier}' in '{spec}' (cli|sonnet|opus)")
    band_known = cls in CLASS_BANDS
    band = CLASS_BANDS.get(cls, DEFAULT_BAND)
    expected = band * TIER_FACTOR[tier] * fanout
    return {
        "tier": tier,
        "class": cls,
        "class_known": band_known,
        "fanout": fanout,
        "label": label,
        "expected": expected,
    }


def hint(tasks: list[dict]) -> dict:
    rows = []
    total = 0.0
    for t in tasks:
        rows.append(
            {
                "label": t["label"] or f"{t['tier']}:{t['class']}",
                "tier": t["tier"],
                "class": t["class"],
                "class_known": t["class_known"],
                "fanout": t["fanout"],
                "expected_tokens": round100(t["expected"]),
            }
        )
        total += t["expected"]
    return {
        "tasks": rows,
        "low_tokens": round100(total * LOW_MULT),
        "expected_tokens": round100(total),
        "high_tokens": round100(total * HIGH_MULT),
        "disclaimer": DISCLAIMER,
        "predictive": False,
        "drives_engine_budget": False,
    }


def render(result: dict) -> str:
    lines = ["Orchestration budget hint  (" + result["disclaimer"] + ")", ""]
    lines.append(f"{'task':<28} {'tier':<7} {'class':<11} {'fan':>3} {'~tokens':>10}")
    lines.append("-" * 62)
    for r in result["tasks"]:
        cls = r["class"] + ("" if r["class_known"] else "*")
        lines.append(
            f"{r['label'][:28]:<28} {r['tier']:<7} {cls:<11} {r['fanout']:>3} {r['expected_tokens']:>10,}"
        )
    lines.append("-" * 62)
    lines.append(
        f"{'TOTAL (output tokens)':<51} {result['expected_tokens']:>10,}"
    )
    lines.append(
        f"  range  low {result['low_tokens']:,}  ·  expected {result['expected_tokens']:,}"
        f"  ·  high {result['high_tokens']:,}"
    )
    if any(not r["class_known"] for r in result["tasks"]):
        lines.append("  * unknown work class → default band used")
    lines.append("")
    lines.append("This is a HINT to set expectations before signing, NOT a forecast and NOT")
    lines.append("the engine `budget` (a skill cannot control the engine — AP-COORD-7).")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--task",
        action="append",
        default=[],
        metavar="tier:class:fanout[:label]",
        help="one task in the contract; repeatable",
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)

    if not args.task:
        ap.error("at least one --task is required")
    try:
        tasks = [parse_task(s) for s in args.task]
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = hint(tasks)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    budget_hint.py --task <tier>:<class>:<fanout>[:<label>] [--task ...] [--json] [--dollars]

    <tier>   = cli | haiku | sonnet | opus | fable  (cli = no model = 0 tokens)
    <class>  = mechanical | lint | edit | review | research | plan | hard | scaffold
               (lint≈mechanical, hard≈plan; any other value → default band, flagged with *)
    <fanout> = positive int (parallel copies of this task); default 1

Examples:
    budget_hint.py --task cli:lint:1
    budget_hint.py --task opus:hard:1 --task sonnet:review:4 --json
    budget_hint.py --task fable:plan:1 --task sonnet:edit:3 --dollars
    budget_hint.py --task haiku:lint:8 --task sonnet:edit:2 --task opus:plan:1
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

# Tier token-emission multipliers. These scale TOKENS, not dollars — stronger models think
# and emit more output per task. All values are uncalibrated heuristics (no cost corpus
# exists yet); they are never pricing ratios. cli runs no model (0 tokens). Fable's
# adaptive thinking (always on) raises emission above Opus — factor is a rough heuristic.
# haiku is the opt-in utility rung below fleet (bounded high-fanout judgment) — it emits
# less per task than Sonnet.
TIER_FACTOR: dict[str, float] = {
    "cli": 0.0,
    "haiku": 0.6,
    "sonnet": 1.0,
    "opus": 2.5,
    "fable": 3.0,
}

# Output price in $/MTok for the --dollars flag only. Never used in token estimation.
# Source: Anthropic API pricing (2026-06). Separated from TIER_FACTOR intentionally —
# pricing and emission volume are independent dimensions.
TIER_PRICE: dict[str, float] = {
    "cli": 0.0,
    "haiku": 5.0,
    "sonnet": 15.0,
    "opus": 25.0,
    "fable": 50.0,
}

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
        raise ValueError(f"unknown tier '{tier}' in '{spec}' (cli|haiku|sonnet|opus|fable)")
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


def _cost_usd(tokens: float, tier: str) -> float:
    """Convert output tokens to USD using TIER_PRICE ($/MTok)."""
    return tokens * TIER_PRICE.get(tier, 0.0) / 1_000_000


def hint(tasks: list[dict]) -> dict:
    rows = []
    total_tokens = 0.0
    total_cost = 0.0
    tier_totals: dict[str, float] = {}
    tier_counts: dict[str, int] = {}
    for t in tasks:
        expected_cost = _cost_usd(t["expected"], t["tier"])
        rows.append(
            {
                "label": t["label"] or f"{t['tier']}:{t['class']}",
                "tier": t["tier"],
                "class": t["class"],
                "class_known": t["class_known"],
                "fanout": t["fanout"],
                "expected_tokens": round100(t["expected"]),
                "expected_cost_usd": round(expected_cost, 4),
            }
        )
        total_tokens += t["expected"]
        total_cost += expected_cost
        tier_totals[t["tier"]] = tier_totals.get(t["tier"], 0.0) + t["expected"]
        tier_counts[t["tier"]] = tier_counts.get(t["tier"], 0) + 1

    # Tier-mix: fleet share = (haiku + sonnet) expected tokens / total expected tokens.
    # cli is excluded from the concept — it is "no model", contributes 0 anyway.
    fleet_tokens = tier_totals.get("haiku", 0.0) + tier_totals.get("sonnet", 0.0)
    fleet_share = (fleet_tokens / total_tokens) if total_tokens > 0 else 0.0

    return {
        "tasks": rows,
        "low_tokens": round100(total_tokens * LOW_MULT),
        "expected_tokens": round100(total_tokens),
        "high_tokens": round100(total_tokens * HIGH_MULT),
        "low_cost_usd": round(total_cost * LOW_MULT, 4),
        "expected_cost_usd": round(total_cost, 4),
        "high_cost_usd": round(total_cost * HIGH_MULT, 4),
        "disclaimer": DISCLAIMER,
        "predictive": False,
        "drives_engine_budget": False,
        "fleet_share": round(fleet_share, 4),
        "tier_totals": {k: round100(v) for k, v in tier_totals.items()},
        "tier_counts": tier_counts,
    }


def render(result: dict, dollars: bool = False) -> str:
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
    if dollars:
        lines.append(
            f"  cost   low ${result['low_cost_usd']:.4f}  ·  expected ${result['expected_cost_usd']:.4f}"
            f"  ·  high ${result['high_cost_usd']:.4f}  (output $/MTok; estimate only)"
        )
    if any(not r["class_known"] for r in result["tasks"]):
        lines.append("  * unknown work class → default band used")
    lines.append("")
    lines.append("This is a HINT to set expectations before signing, NOT a forecast and NOT")
    lines.append("the engine `budget` (a skill cannot control the engine — AP-COORD-7).")

    tier_counts = result.get("tier_counts", {})
    n_opus = tier_counts.get("opus", 0)
    n_fable = tier_counts.get("fable", 0)
    n_cli = tier_counts.get("cli", 0)
    n_haiku = tier_counts.get("haiku", 0)
    fleet_pct = round(result.get("fleet_share", 0.0) * 100)
    footer = f"tier-mix: {fleet_pct}% fleet / {n_opus}×opus / {n_fable}×fable / {n_cli}×cli"
    if n_haiku:
        footer += f" / {n_haiku}×haiku"
    lines.append(footer)
    if result["expected_tokens"] > 0 and result.get("fleet_share", 0.0) < 0.8:
        lines.append(
            "WARN: fleet token-share below 80% target (advisory — mistagged tiers are not "
            "detectable here; review the per-task model_tier column)"
        )
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
    ap.add_argument(
        "--dollars",
        action="store_true",
        help="additionally print a low/expected/high cost band in USD (output $/MTok × tokens)",
    )
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
        print(render(result, dollars=args.dollars))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

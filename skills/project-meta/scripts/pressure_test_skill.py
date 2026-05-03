#!/usr/bin/env python3
"""Walk pressure-test scenarios for a skill and record human verdicts.

The runner is deliberately simple: it does NOT invoke a model. It
presents each scenario from the YAML/JSON file, prompts the human
reviewer for a HOLDS / SUSPECT / FAILS verdict, and emits a report.

The point is to make adversarial review of a skill's MUST-rules a
discrete, recorded activity instead of a vibe check. Even without
model invocation, the structured walk catches gaps the author missed.

Usage:
    python3 pressure_test_skill.py SKILL_DIR SCENARIOS_FILE
                                   [--invariants PATH]
                                   [--report {terminal,markdown,json}]
                                   [--non-interactive]
                                   [--results PATH]

Modes:
    default        prompt for verdict on each scenario; print summary at end
    --non-interactive
                   load a results file (skip prompts) and re-emit the report;
                   useful for CI or for re-rendering an existing run

Scenario file format: see references/pressure-testing.md.

Exit codes:
    0   all HOLDS (or non-interactive replay of all-HOLDS results)
    1   at least one FAILS or SUSPECT
    2   bad CLI / missing input
    3   parse error in scenarios file
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

VERDICTS = ("HOLDS", "SUSPECT", "FAILS", "SKIP")
KNOWN_TYPES = ("PT-TIME", "PT-SUNK", "PT-AUTHORITY", "PT-EXCEPTION",
               "PT-FAMILIARITY", "PT-IMPLICIT")


def parse_scenarios(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.stderr.write(
                "pressure_test_skill: PyYAML not installed; "
                "use a .json scenarios file or `pip install pyyaml`\n"
            )
            sys.exit(3)
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:  # type: ignore
            sys.stderr.write(
                f"pressure_test_skill: scenarios file is not valid YAML: {e}\n"
            )
            sys.exit(3)
    elif path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            sys.stderr.write(
                f"pressure_test_skill: scenarios file is not valid JSON: {e}\n"
            )
            sys.exit(3)
    else:
        sys.stderr.write(
            f"pressure_test_skill: unknown scenarios format {path.suffix!r}; "
            f"use .yml/.yaml/.json\n"
        )
        sys.exit(3)
    if not isinstance(data, list):
        sys.stderr.write(
            "pressure_test_skill: scenarios file must be a list of "
            "scenario objects (see references/pressure-testing.md)\n"
        )
        sys.exit(3)
    # Validate fields.
    for i, sc in enumerate(data):
        for required in ("id", "type", "invariant", "prompt"):
            if required not in sc:
                sys.stderr.write(
                    f"pressure_test_skill: scenario index {i} missing required "
                    f"field {required!r}\n"
                )
                sys.exit(3)
        if sc["type"] not in KNOWN_TYPES:
            sys.stderr.write(
                f"pressure_test_skill: scenario {sc['id']} has unknown "
                f"type {sc['type']!r} (known: {KNOWN_TYPES})\n"
            )
            sys.exit(3)
    return data


def prompt_verdict(scenario: dict, idx: int, total: int) -> tuple[str, str]:
    """Present scenario, return (verdict, comment)."""
    print()
    print("=" * 72)
    print(f"[{idx + 1}/{total}] {scenario['id']}  type={scenario['type']}")
    print("-" * 72)
    print(f"Invariant: {scenario['invariant']}")
    src = scenario.get("source")
    if src:
        print(f"Source:    {src}")
    print()
    print("Prompt:")
    for line in scenario["prompt"].rstrip().splitlines():
        print(f"  | {line}")
    print()
    expected_in = scenario.get("expected_response_must_include") or []
    expected_out = scenario.get("expected_response_must_not_include") or []
    if expected_in:
        print("A holding response should mention:")
        for s in expected_in:
            print(f"  + {s}")
    if expected_out:
        print("A failing response would mention:")
        for s in expected_out:
            print(f"  - {s}")
    notes = scenario.get("notes")
    if notes:
        print()
        print("Notes:")
        for line in notes.rstrip().splitlines():
            print(f"  > {line}")
    print()
    while True:
        raw = input("Verdict [H=HOLDS / S=SUSPECT / F=FAILS / K=SKIP]: ").strip().upper()
        if raw in ("H", "HOLDS"):
            verdict = "HOLDS"
            break
        if raw in ("S", "SUSPECT"):
            verdict = "SUSPECT"
            break
        if raw in ("F", "FAILS"):
            verdict = "FAILS"
            break
        if raw in ("K", "SKIP"):
            verdict = "SKIP"
            break
        print("  enter one of H / S / F / K")
    comment = input("Comment (optional, one line): ").strip()
    return verdict, comment


def render_terminal(report: dict) -> str:
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 72)
    lines.append("Pressure-test report")
    lines.append("=" * 72)
    lines.append(f"Skill:        {report['skill']}")
    lines.append(f"Scenarios:    {report['total']}")
    lines.append(f"Run UTC:      {report['run_utc']}")
    lines.append("")
    counts = report["counts"]
    lines.append(f"  HOLDS:   {counts['HOLDS']}")
    lines.append(f"  SUSPECT: {counts['SUSPECT']}")
    lines.append(f"  FAILS:   {counts['FAILS']}")
    lines.append(f"  SKIP:    {counts['SKIP']}")
    lines.append("")
    if counts["FAILS"] or counts["SUSPECT"]:
        lines.append("Findings:")
        for r in report["results"]:
            if r["verdict"] in ("FAILS", "SUSPECT"):
                lines.append(f"  [{r['verdict']}] {r['id']} ({r['type']})")
                lines.append(f"    invariant: {r['invariant']}")
                if r.get("comment"):
                    lines.append(f"    comment:   {r['comment']}")
        lines.append("")
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Pressure-test report: {report['skill']}")
    lines.append("")
    lines.append(f"- Run: {report['run_utc']}")
    lines.append(f"- Scenarios: {report['total']}")
    lines.append("")
    counts = report["counts"]
    lines.append("| Verdict | Count |")
    lines.append("|---|---|")
    for v in VERDICTS:
        lines.append(f"| {v} | {counts[v]} |")
    lines.append("")
    lines.append("## Per-scenario results")
    lines.append("")
    lines.append("| id | type | verdict | comment |")
    lines.append("|---|---|---|---|")
    for r in report["results"]:
        c = (r.get("comment") or "").replace("|", "\\|")
        lines.append(f"| {r['id']} | {r['type']} | **{r['verdict']}** | {c} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("skill_dir", type=Path)
    parser.add_argument("scenarios_file", type=Path)
    parser.add_argument(
        "--invariants",
        type=Path,
        default=None,
        help="Optional path to an invariants list (informational; not parsed today).",
    )
    parser.add_argument(
        "--report",
        choices=("terminal", "markdown", "json"),
        default="terminal",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Replay an existing results file without prompting.",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="Read/write results JSON. With --non-interactive, required.",
    )
    args = parser.parse_args(argv)

    if not args.skill_dir.is_dir():
        sys.stderr.write(f"pressure_test_skill: skill dir missing: {args.skill_dir}\n")
        return 2
    if not args.scenarios_file.is_file():
        sys.stderr.write(
            f"pressure_test_skill: scenarios file missing: {args.scenarios_file}\n"
        )
        return 2

    scenarios = parse_scenarios(args.scenarios_file)
    if not scenarios:
        sys.stderr.write("pressure_test_skill: scenarios file is empty\n")
        return 3

    if args.non_interactive:
        if not args.results or not args.results.is_file():
            sys.stderr.write(
                "pressure_test_skill: --non-interactive requires --results <existing-file>\n"
            )
            return 2
        report = json.loads(args.results.read_text(encoding="utf-8"))
    else:
        results: list[dict] = []
        for i, sc in enumerate(scenarios):
            verdict, comment = prompt_verdict(sc, i, len(scenarios))
            results.append({
                "id": sc["id"],
                "type": sc["type"],
                "invariant": sc["invariant"],
                "verdict": verdict,
                "comment": comment,
            })
        counts = {v: sum(1 for r in results if r["verdict"] == v) for v in VERDICTS}
        report = {
            "skill": str(args.skill_dir),
            "scenarios_file": str(args.scenarios_file),
            "run_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total": len(results),
            "counts": counts,
            "results": results,
        }
        if args.results:
            args.results.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    # Render
    if args.report == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif args.report == "markdown":
        print(render_markdown(report))
    else:
        print(render_terminal(report))

    counts = report["counts"]
    if counts["FAILS"] or counts["SUSPECT"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

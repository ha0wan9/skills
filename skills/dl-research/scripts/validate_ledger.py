#!/usr/bin/env python3
"""Validate a dl-research runs.jsonl ledger without external dependencies."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


REQUIRED = {
    "run_id",
    "study_id",
    "experiment_id",
    "status",
    "hypothesis",
    "intervention",
    "command",
    "code_revision",
    "data_version",
    "primary_metric",
    "metric_direction",
    "created_utc",
}

STATUSES = {
    "prepared",
    "running",
    "completed",
    "failed",
    "stopped",
    "discarded",
    "invalid",
}

DIRECTIONS = {"minimize", "maximize"}
VERDICTS = {"kept", "killed", "inconclusive", "invalid", None}
DECISIONS = {"promote", "kill", "fork", "repeat", "inconclusive", None}

CRITIC_VERDICTS = {"pass", "block", "revise"}
CRITIC_VERDICT_REQUIRED = {
    "row_type",
    "target_run_id",
    "critic_agent",
    "verdict",
    "created_at",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_critic_verdict_row(row: dict[str, Any], line_no: int) -> list[str]:
    errors: list[str] = []
    missing = sorted(CRITIC_VERDICT_REQUIRED - set(row))
    if missing:
        errors.append(f"line {line_no}: missing required keys: {', '.join(missing)}")

    for key in CRITIC_VERDICT_REQUIRED & set(row):
        if not isinstance(row[key], str) or not row[key].strip():
            errors.append(f"line {line_no}: {key} must be a non-empty string")

    verdict = row.get("verdict")
    if verdict is not None and verdict not in CRITIC_VERDICTS:
        errors.append(f"line {line_no}: verdict must be one of {sorted(CRITIC_VERDICTS)}")

    return errors


def validate_row(row: dict[str, Any], line_no: int) -> list[str]:
    if row.get("row_type") == "critic_verdict":
        return validate_critic_verdict_row(row, line_no)

    errors: list[str] = []
    missing = sorted(REQUIRED - set(row))
    if missing:
        errors.append(f"line {line_no}: missing required keys: {', '.join(missing)}")

    for key in REQUIRED & set(row):
        if not isinstance(row[key], str) or not row[key].strip():
            errors.append(f"line {line_no}: {key} must be a non-empty string")

    status = row.get("status")
    if status is not None and status not in STATUSES:
        errors.append(f"line {line_no}: status must be one of {sorted(STATUSES)}")

    direction = row.get("metric_direction")
    if direction is not None and direction not in DIRECTIONS:
        errors.append(f"line {line_no}: metric_direction must be 'minimize' or 'maximize'")

    verdict = row.get("verdict", None)
    if verdict not in VERDICTS:
        errors.append(f"line {line_no}: verdict must be kept, killed, inconclusive, invalid, or null")

    decision = row.get("decision", None)
    if decision not in DECISIONS:
        errors.append(f"line {line_no}: decision must be promote, kill, fork, repeat, inconclusive, or null")

    track_id = row.get("track_id", None)
    if track_id is not None and (not isinstance(track_id, str) or not track_id.strip()):
        errors.append(f"line {line_no}: track_id must be a non-empty string or null")

    slug = row.get("slug", None)
    if slug is not None and (not isinstance(slug, str) or not slug.strip()):
        errors.append(f"line {line_no}: slug must be a non-empty string or null")

    parent_id = row.get("parent_id", None)
    if parent_id is not None and (not isinstance(parent_id, str) or not parent_id.strip()):
        errors.append(f"line {line_no}: parent_id must be a non-empty string or null")

    graph_nodes = row.get("graph_nodes", None)
    if graph_nodes is not None:
        if not isinstance(graph_nodes, list) or not all(
            isinstance(item, str) and item.strip() for item in graph_nodes
        ):
            errors.append(f"line {line_no}: graph_nodes must be a list of non-empty strings or null")

    metric_value = row.get("metric_value", None)
    if metric_value is not None and not _is_number(metric_value):
        errors.append(f"line {line_no}: metric_value must be a finite number or null")

    design_deviation = row.get("design_deviation", None)
    if design_deviation is not None and not isinstance(design_deviation, bool):
        errors.append(f"line {line_no}: design_deviation must be boolean or null")

    return errors


def _check_promote_gate(rows: list[tuple[int, dict[str, Any]]]) -> list[str]:
    """v2 rule: a run row with decision "promote" needs an earlier critic_verdict
    "pass" targeting its run_id or experiment_id, with no later block/revise.

    Only called when an explicit ledger_version marker is present (v2 opt-in);
    v1 files (no marker) never reach this check.
    """
    errors: list[str] = []
    for line_no, row in rows:
        if row.get("row_type") == "critic_verdict":
            continue
        if row.get("decision") != "promote":
            continue

        run_id = row.get("run_id")
        experiment_id = row.get("experiment_id")
        targets = {t for t in (run_id, experiment_id) if t is not None}

        last_verdict = None
        for verdict_line_no, verdict_row in rows:
            if verdict_line_no >= line_no:
                break
            if verdict_row.get("row_type") != "critic_verdict":
                continue
            if verdict_row.get("target_run_id") in targets:
                last_verdict = verdict_row.get("verdict")

        if last_verdict != "pass":
            errors.append(
                f"line {line_no}: decision \"promote\" requires an earlier critic_verdict "
                "row with verdict \"pass\" targeting this run_id or experiment_id "
                "(none found, or the most recent targeting verdict is block/revise)"
            )

    return errors


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path}: file does not exist"]

    ledger_version: str | None = None
    rows: list[tuple[int, dict[str, Any]]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(row, dict):
                errors.append(f"line {line_no}: row must be a JSON object")
                continue
            if row.get("ledger_version") is not None and ledger_version is None:
                ledger_version = str(row["ledger_version"])
            errors.extend(validate_row(row, line_no))
            rows.append((line_no, row))

    if ledger_version is not None:
        errors.extend(_check_promote_gate(rows))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Path to runs.jsonl")
    args = parser.parse_args()

    errors = validate(args.ledger)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"ok: {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

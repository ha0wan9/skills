#!/usr/bin/env python3
"""Derive an effective HARNESS_PROFILE from external evidence.

Advisory only. Static by default: unless HARNESS_PROFILE_FLOOR or
HARNESS_PROFILE_CEILING is configured, the script prints the configured
HARNESS_PROFILE unchanged. When elasticity is enabled, it derives one bounded
step from model tier, risk-context, dispatch-ledger history, and lesson
effectiveness. Invariant core gates must keep reading HARNESS_PROFILE directly.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PROFILES = ("minimal", "standard", "strict")
PROFILE_RANK = {name: i for i, name in enumerate(PROFILES)}
STRONG_MODEL_TIERS = {"opus", "fable"}


def _profile_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower()


def _valid_profile(value: str | None, field: str, fallback: str) -> tuple[str, str | None]:
    if value in PROFILE_RANK:
        return value, None
    return fallback, f"{field}={value!r} is invalid; using {fallback!r}"


def _step(value: str, delta: int) -> str:
    idx = max(0, min(len(PROFILES) - 1, PROFILE_RANK[value] + delta))
    return PROFILES[idx]


def _clamp(value: str, floor: str, ceiling: str) -> str:
    idx = PROFILE_RANK[value]
    idx = max(idx, PROFILE_RANK[floor])
    idx = min(idx, PROFILE_RANK[ceiling])
    return PROFILES[idx]


def _model_tier(model_id: str | None) -> str:
    mid = (model_id or os.environ.get("CLAUDE_MODEL") or os.environ.get("ANTHROPIC_MODEL") or "").lower()
    if "haiku" in mid:
        return "haiku"
    if "sonnet" in mid or "luna" in mid:
        return "sonnet"
    if "opus" in mid or "terra" in mid:
        return "opus"
    if "fable" in mid or "sol" in mid:
        return "fable"
    return "unknown"


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    if not path.exists():
        return [], None
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception as exc:
        return [], f"{path}: unreadable ({exc})"
    return rows, None


def _risk_band(root: Path) -> tuple[str | None, str | None]:
    path = root / ".harness" / "risk-context.json"
    if not path.exists():
        return None, None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{path}: unreadable ({exc})"
    band = obj.get("band")
    return (band if isinstance(band, str) else None), None


def _dispatch_history(root: Path) -> tuple[dict[str, Any], list[str]]:
    rows, err = _read_jsonl(root / ".harness" / "dispatch-log.jsonl")
    warnings = [err] if err else []
    last10 = rows[-10:]
    blockers = [r for r in last10 if r.get("verdict") == "BLOCKER"]
    return {
        "rows": len(rows),
        "last10": len(last10),
        "last10_blockers": len(blockers),
        "last10_blocker_rate": (len(blockers) / len(last10)) if last10 else None,
    }, warnings


def _lesson_effectiveness(root: Path) -> tuple[dict[str, int], list[str]]:
    rows, err = _read_jsonl(root / ".harness" / "lessons.jsonl")
    warnings = [err] if err else []
    helpful = 0
    harmful = 0
    for row in rows:
        try:
            helpful += int(row.get("helpful_count", 0))
            harmful += int(row.get("harmful_count", 0))
        except (TypeError, ValueError):
            warnings.append(f"lesson {row.get('id', '<unknown>')}: non-numeric effectiveness count ignored")
    return {"helpful": helpful, "harmful": harmful}, warnings


def derive(root: Path, model_id: str | None) -> dict[str, Any]:
    configured, warn = _valid_profile(_profile_env("HARNESS_PROFILE", "standard"), "HARNESS_PROFILE", "standard")
    warnings = [warn] if warn else []

    floor_raw = _profile_env("HARNESS_PROFILE_FLOOR")
    ceiling_raw = _profile_env("HARNESS_PROFILE_CEILING")
    if floor_raw is None and ceiling_raw is None:
        return {
            "configured": configured,
            "effective": configured,
            "elasticity": "disabled",
            "model_tier": _model_tier(model_id),
            "reason": "HARNESS_PROFILE_FLOOR/HARNESS_PROFILE_CEILING not configured",
            "warnings": warnings,
        }

    floor, warn = _valid_profile(floor_raw, "HARNESS_PROFILE_FLOOR", configured)
    if warn:
        warnings.append(warn)
    ceiling, warn = _valid_profile(ceiling_raw, "HARNESS_PROFILE_CEILING", configured)
    if warn:
        warnings.append(warn)

    if PROFILE_RANK[floor] > PROFILE_RANK[ceiling]:
        return {
            "configured": configured,
            "effective": configured,
            "elasticity": "invalid-bounds",
            "model_tier": _model_tier(model_id),
            "floor": floor,
            "ceiling": ceiling,
            "reason": "HARNESS_PROFILE_FLOOR is stricter than HARNESS_PROFILE_CEILING; fail-static",
            "warnings": warnings,
        }

    tier = _model_tier(model_id)
    risk_band, risk_warning = _risk_band(root)
    if risk_warning:
        warnings.append(risk_warning)
    dispatch, dispatch_warnings = _dispatch_history(root)
    warnings.extend(dispatch_warnings)
    lessons, lesson_warnings = _lesson_effectiveness(root)
    warnings.extend(lesson_warnings)

    effective = _clamp(configured, floor, ceiling)
    reason = "static: insufficient evidence for bounded change"
    evidence_warnings = [w for w in [risk_warning, *dispatch_warnings, *lesson_warnings] if w]
    if evidence_warnings:
        return {
            "configured": configured,
            "effective": effective,
            "elasticity": "enabled",
            "model_tier": tier,
            "floor": floor,
            "ceiling": ceiling,
            "risk_band": risk_band,
            "dispatch": dispatch,
            "lessons": lessons,
            "reason": "fail-static: one or more evidence inputs were unreadable",
            "warnings": warnings,
        }

    blocker_rate = dispatch["last10_blocker_rate"]
    should_scale_up = risk_band == "spike-first" or (blocker_rate is not None and blocker_rate >= 0.20)
    clean_history = dispatch["last10"] >= 10 and dispatch["last10_blockers"] == 0
    harmful_signal = lessons["harmful"] > lessons["helpful"] and lessons["harmful"] > 0
    should_scale_down = tier in STRONG_MODEL_TIERS and clean_history and not harmful_signal

    if should_scale_up:
        effective = _clamp(_step(effective, 1), floor, ceiling)
        reason = "scaled up one step: spike-first risk or >=20% blocker rate in last 10 dispatches"
    elif should_scale_down:
        effective = _clamp(_step(effective, -1), floor, ceiling)
        reason = "scaled down one step: strong model tier with 10 clean dispatch records"

    return {
        "configured": configured,
        "effective": effective,
        "elasticity": "enabled",
        "model_tier": tier,
        "floor": floor,
        "ceiling": ceiling,
        "risk_band": risk_band,
        "dispatch": dispatch,
        "lessons": lessons,
        "reason": reason,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-id", default=None, help="Model id override; otherwise CLAUDE_MODEL/ANTHROPIC_MODEL")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repo root (default: cwd)")
    parser.add_argument("--json", action="store_true", dest="emit_json", help="emit full JSON payload")
    args = parser.parse_args(argv)

    payload = derive(args.root.resolve(), args.model_id)
    for warning in payload.get("warnings", []):
        print(f"derive_profile warning: {warning}", file=sys.stderr)
    if payload.get("elasticity") == "invalid-bounds":
        print(f"derive_profile error: {payload['reason']}", file=sys.stderr)

    if args.emit_json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(payload["effective"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

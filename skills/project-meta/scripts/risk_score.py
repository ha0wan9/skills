#!/usr/bin/env python3
"""Score a plan against a 7-dimension risk rubric and derive review-tier/readiness recommendations.

Adapted from the fullstack-dev-skills create-epic-plan rubric. Each of the 7 dimensions
is scored 1–3; the sum drives a band (proceed / incremental / spike-first), which maps to
a review-tier FLOOR recommendation (L1/L2/L3) and a plan-readiness keyword (floor/strict).
The review-tier recommendation is a FLOOR only — take the max with review_tier.py's
mechanical floor; the readiness keyword is advisory — risk can raise attention (recommend
strict) but the plan keyword remains authoritative and is never lowered by this script.

Usage:

    python3 risk_score.py --scope 1 --dependencies 1 --blocking 1 --stability 2 \\
                          --ux 1 --testing 1 --reversibility 1
    python3 risk_score.py --scope 3 --dependencies 3 --blocking 3 --stability 3 \\
                          --ux 3 --testing 3 --reversibility 3 --json
    python3 risk_score.py --scope 2 --dependencies 2 --blocking 2 --stability 2 \\
                          --ux 2 --testing 2 --reversibility 2 \\
                          --write-context --root /tmp/w1

Dependency-free. Advisory: always exits 0 (exit 2 only on bad invocation); the
conductor owns the final call.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Bands keyed by (low_inclusive, high_inclusive) -> (band, review_tier, readiness, sequencing)
_BANDS = [
    (7, 11, "proceed", "L1", "floor", "no sequencing constraint"),
    (12, 16, "incremental", "L2", "strict", "schedule mid-version after dependencies land"),
    (17, 21, "spike-first", "L3", "strict", "spike before scheduling; schedule early in its version"),
]

DIMS = ("scope", "dependencies", "blocking", "stability", "ux", "testing", "reversibility")


def _classify(total: int) -> tuple[str, str, str, str]:
    """Return (band, review_tier, readiness, sequencing) for a given total."""
    for lo, hi, band, tier, readiness, seq in _BANDS:
        if lo <= total <= hi:
            return band, tier, readiness, seq
    # Should never happen given validated inputs (7–21)
    raise ValueError(f"total {total} out of expected range 7–21")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for dim in DIMS:
        parser.add_argument(
            f"--{dim}",
            type=int,
            required=True,
            metavar="N",
            help=f"risk score for {dim} dimension (1–3)",
        )
    parser.add_argument("--json", action="store_true", dest="emit_json", help="emit JSON to stdout (nothing else)")
    parser.add_argument("--write-context", action="store_true", help="write .harness/risk-context.json under --root")
    parser.add_argument("--root", type=Path, default=None, help="root dir for --write-context (default: cwd)")

    args = parser.parse_args(argv)

    # Validate each dimension is in [1, 3]
    errors: list[str] = []
    dim_values: dict[str, int] = {}
    for dim in DIMS:
        val = getattr(args, dim)
        if val < 1 or val > 3:
            errors.append(f"  --{dim} {val}: must be 1–3")
        else:
            dim_values[dim] = val

    if errors:
        print("usage error: dimension values must be 1–3. Offending arguments:", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n7 dimensions: {', '.join('--' + d for d in DIMS)}", file=sys.stderr)
        sys.exit(2)

    for dim in DIMS:
        dim_values[dim] = getattr(args, dim)

    total = sum(dim_values[d] for d in DIMS)
    band, review_tier, readiness, sequencing = _classify(total)

    if args.emit_json:
        out = {
            "total": total,
            "band": band,
            "review_tier": review_tier,
            "readiness": readiness,
            "sequencing": sequencing,
            "dims": dict(dim_values),
        }
        print(json.dumps(out))
    else:
        print(f"total: {total}  band: {band}")
        print(f"review_tier floor recommendation: {review_tier}")
        print(f"  (advisory — take the MAX of this and review_tier.py's mechanical floor; never lowers it)")
        print(f"plan readiness recommendation: {readiness}")
        print(f"  (advisory — risk can raise attention; the plan keyword is authoritative and never lowered here)")
        print(f"sequencing hint: {sequencing}")
        print(f"dims used: {', '.join(f'{d}={v}' for d, v in dim_values.items())}")
        print(
            "NOTE: this is an ADVISORY rubric — floor — escalate on judgment. "
            "Behavior-change/blast-radius judgment still belongs to the conductor; "
            "this rubric informs, never overrides."
        )

    if args.write_context:
        root = (args.root or Path.cwd()).resolve()
        harness_dir = root / ".harness"
        harness_dir.mkdir(parents=True, exist_ok=True)
        ctx_path = harness_dir / "risk-context.json"
        ctx = {
            "total": total,
            "band": band,
            "written_at": datetime.now(timezone.utc).isoformat(),
        }
        ctx_path.write_text(json.dumps(ctx, indent=2) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

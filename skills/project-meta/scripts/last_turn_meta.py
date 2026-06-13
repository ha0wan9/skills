#!/usr/bin/env python3
"""Last-turn metadata: the machine contract an editing recipe leaves behind.

The prose Output Footer (`project-meta/<verb> done — …`) is for humans. This
script owns the *machine* counterpart: a small `.harness/last-turn-meta.json`
that an editing recipe writes at completion, and that the Stop gate checks —
*without grepping the transcript* (which is not reliably implementable). The
file is the single source of truth; the Stop gate reads the file, never the
turn tail.

Subcommands:

  write   Write/overwrite .harness/last-turn-meta.json from flags. Validates
          against SCHEMA before writing; refuses to write a malformed record.
  check   Stop-gate leg. Fires only when the working tree has uncommitted
          *harness* changes (an editing recipe ran) — reusing the exact
          harness-file definition from `dispatch_ledger.py` so the two gates
          agree. Then: missing or malformed meta → violation (exit 1); valid
          meta → exit 0. A non-editing turn (no harness change), a non-git
          tree, or HARNESS_PROFILE=minimal → exit 0 (nothing to enforce).
  schema  Print the required keys + types (the shared spec, for humans/tests).

Ships inside project-meta; dependent hooks resolve it (resolve-don't-vendor).
Standard library only. Profile-aware via $HARNESS_PROFILE.

Exit codes:
    0  ok / no-op (nothing to enforce, or valid meta)
    1  violation (write failed; or harness changed and meta missing/malformed)
    2  bad invocation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Reuse the canonical harness-file definition + change detection so the
# last-turn-meta gate and the mandatory-dispatch gate fire on the same set.
from dispatch_ledger import _changed_files, _is_git, is_harness_file  # noqa: E402

META_PATH = ".harness/last-turn-meta.json"

# The shared spec — the single source of truth for the record's shape. The
# Stop gate (`check`) and any test validate against this; `write` populates it.
SCHEMA: dict[str, object] = {
    "verb": str,            # the /project-meta editing verb (init, roadmap, …)
    "review_tier": {"L0", "L1", "L2", "L3"},      # review level applied
    "read_pattern": {"minimal", "context-mapping"},  # context read-pattern
    "files_written": int,   # files created/modified this turn
    "files_read": int,      # files consulted (excluding mandatory framework loads)
    "memory_updated": bool,  # did canonical memory change?
    "delivery_shown": bool,  # was a pre-commit delivery presented?
}
REQUIRED_KEYS = tuple(SCHEMA)


def _profile() -> str:
    return os.environ.get("HARNESS_PROFILE", "standard").strip() or "standard"


def validate_record(rec: object) -> list[str]:
    """Return a list of human-readable problems; empty means valid."""
    errors: list[str] = []
    if not isinstance(rec, dict):
        return ["record is not a JSON object"]
    for key, spec in SCHEMA.items():
        if key not in rec:
            errors.append(f"missing required key: {key}")
            continue
        val = rec[key]
        if isinstance(spec, set):
            if val not in spec:
                errors.append(f"{key}={val!r} not one of {sorted(spec)}")
        elif spec is bool:
            if not isinstance(val, bool):
                errors.append(f"{key} must be a boolean, got {type(val).__name__}")
        elif spec is int:
            # bool is a subclass of int; reject it explicitly
            if isinstance(val, bool) or not isinstance(val, int) or val < 0:
                errors.append(f"{key} must be a non-negative integer")
        elif spec is str:
            if not (isinstance(val, str) and val.strip()):
                errors.append(f"{key} must be a non-empty string")
    return errors


def cmd_write(args: argparse.Namespace) -> int:
    rec = {
        "verb": args.verb,
        "review_tier": args.review_tier,
        "read_pattern": args.read_pattern,
        "files_written": args.files_written,
        "files_read": args.files_read,
        "memory_updated": args.memory_updated,
        "delivery_shown": args.delivery_shown,
    }
    errors = validate_record(rec)
    if errors:
        print("refusing to write malformed last-turn-meta:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 2
    path = Path(args.target_root).expanduser() / META_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {META_PATH} (verb={rec['verb']}, tier={rec['review_tier']})")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    if _profile() == "minimal":
        return 0
    root = Path(args.target_root).expanduser()
    if not _is_git(root):
        return 0
    # Fire only when an editing recipe actually ran this working tree — i.e. the
    # uncommitted change set touches >=1 harness file (same rule as the dispatch
    # gate). A read-only / no-op turn leaves nothing to enforce.
    changed_harness = [f for f in _changed_files(root) if is_harness_file(f)]
    if not changed_harness:
        return 0
    path = root / META_PATH
    if not path.is_file():
        print(
            f"last-turn-meta gate: {len(changed_harness)} harness file(s) changed "
            f"but {META_PATH} is missing — an editing recipe must write it at completion "
            "(scripts/last_turn_meta.py write …).",
            file=sys.stderr,
        )
        return 1
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"last-turn-meta gate: {META_PATH} is unreadable/invalid JSON: {exc}", file=sys.stderr)
        return 1
    errors = validate_record(rec)
    if errors:
        print("last-turn-meta gate: malformed record:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 1
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    def render(spec: object) -> str:
        if isinstance(spec, set):
            return "one of " + "|".join(sorted(spec))
        return {str: "non-empty string", int: "non-negative integer", bool: "boolean"}[spec]

    print("last-turn-meta.json required keys:")
    for key, spec in SCHEMA.items():
        print(f"  {key}: {render(spec)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target-root", default=".", help="repository root (default .)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="write/overwrite .harness/last-turn-meta.json (validated)")
    w.add_argument("--verb", required=True, help="the /project-meta editing verb")
    w.add_argument("--review-tier", required=True, choices=sorted(SCHEMA["review_tier"]))
    w.add_argument("--read-pattern", required=True, choices=sorted(SCHEMA["read_pattern"]))
    w.add_argument("--files-written", type=int, default=0)
    w.add_argument("--files-read", type=int, default=0)
    w.add_argument("--memory-updated", action="store_true")
    w.add_argument("--delivery-shown", action="store_true")
    w.set_defaults(func=cmd_write)

    c = sub.add_parser("check", help="Stop-gate leg: enforce a valid meta when harness files changed")
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("schema", help="print the required keys + types (the shared spec)")
    s.set_defaults(func=cmd_schema)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Lesson registry — durable per-repo learned-policy store.

Store: .harness/lessons.jsonl  (git-TRACKED — durable learned policy)
One JSON row per lesson. Single writer; full-file atomic rewrite on each mutation.

Row schema:
  {id, statement, status, target, target_path, applies_below,
   helpful_count, harmful_count, notes, created_at, updated_at,
   source_session, last_validated}

Status ladder (legal transitions only):
  candidate → recorded → promoted → enforced
  any → retired
  enforced → promoted  (demotion; requires --note)
  promoted → recorded  (demotion; requires --note)

Subcommands (all accept --target-root, default cwd):
  add           Add a new candidate lesson
  status        Transition a lesson's status
  outcome       Record helpful/harmful feedback
  validate      Hard gate: checks structure + path resolution
  watermark     Advisory visibility: candidate count + stale targets
  inject        SessionStart reminder block (≤20 lines)
  effectiveness Print helpful/harmful table
  trim-candidates  Identify zero-value/stale promoted/enforced lessons
  promote-draft    Check for collisions, emit board inbox draft

Fail directions:
  Direct CLI → fail CLOSED (exit 1 on bad input/bad state)
  Hook legs (watermark/inject) → fail OPEN (missing store → warn + exit 0)

Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STORE_RELPATH = ".harness/lessons.jsonl"
LOCK_RELPATH = ".harness/.lesson_registry.lock"

VALID_STATUSES = {"candidate", "recorded", "promoted", "enforced", "retired"}
VALID_TARGETS = {"memory", "hook", "linter"}
TIER_ORDER = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}

# Legal forward transitions (no-skip rule enforced here)
FORWARD_TRANSITIONS: dict[str, str] = {
    "candidate": "recorded",
    "recorded": "promoted",
    "promoted": "enforced",
}
# Legal demotion transitions (require a --note)
DEMOTION_TRANSITIONS: set[tuple[str, str]] = {
    ("enforced", "promoted"),
    ("promoted", "recorded"),
}
# any → retired is always legal

MAX_INJECT_LINES = 20

APPLIES_BELOW_TIERS = set(TIER_ORDER.keys())
UNIVERSAL_KEYWORDS = re.compile(r"\b(MUST|always|never)\b")

STALE_LOCK_SECONDS = 3600


# ---------------------------------------------------------------------------
# Timestamp + UTC helpers
# ---------------------------------------------------------------------------

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Lock helpers (replicated from board.py discipline)
# ---------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _lock_is_stale(lock: Path) -> bool:
    try:
        text = lock.read_text(encoding="utf-8")
    except FileNotFoundError:
        return True
    m = re.search(r"pid=(\d+)", text)
    if m and not _pid_alive(int(m.group(1))):
        return True
    try:
        age = dt.datetime.now(dt.timezone.utc).timestamp() - lock.stat().st_mtime
    except FileNotFoundError:
        return True
    return age > STALE_LOCK_SECONDS


@contextlib.contextmanager
def _lesson_lock(root: Path):
    lock = root / LOCK_RELPATH
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        if not _lock_is_stale(lock):
            raise SystemExit(f"lesson registry is locked: {lock}") from exc
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc2:
            raise SystemExit(f"lesson registry is locked: {lock}") from exc2
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} utc={utc_now()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


# ---------------------------------------------------------------------------
# Store I/O
# ---------------------------------------------------------------------------

def store_path(root: Path) -> Path:
    return root / STORE_RELPATH


def read_store(root: Path) -> list[dict[str, Any]]:
    p = store_path(root)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{p}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{p}:{lineno}: each JSONL row must be an object")
        rows.append(row)
    return rows


def _jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def write_store_atomic(root: Path, rows: list[dict[str, Any]]) -> None:
    p = store_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    text = _jsonl_text(rows)
    fd, tmp = tempfile.mkstemp(prefix=".lessons.", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, p)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# ID allocation
# ---------------------------------------------------------------------------

def _parse_les_num(row_id: str) -> int | None:
    m = re.match(r"^LES-(\d+)$", str(row_id))
    return int(m.group(1)) if m else None


def _next_id(rows: list[dict[str, Any]]) -> str:
    nums = [n for r in rows if (n := _parse_les_num(str(r.get("id", "")))) is not None]
    return f"LES-{(max(nums, default=0) + 1):03d}"


def _find_row(rows: list[dict[str, Any]], lesson_id: str) -> dict[str, Any]:
    for row in rows:
        if row.get("id") == lesson_id:
            return row
    raise SystemExit(f"no lesson with id {lesson_id!r}")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _check_row_structure(row: dict[str, Any]) -> list[str]:
    """Return hard errors for a single row."""
    errors: list[str] = []
    rid = row.get("id", "<missing>")
    status = row.get("status")

    if status not in VALID_STATUSES:
        errors.append(f"{rid}: invalid status {status!r}")

    target = row.get("target")
    if target is not None and target not in VALID_TARGETS:
        errors.append(f"{rid}: invalid target {target!r} (must be one of {sorted(VALID_TARGETS)})")

    applies_below = row.get("applies_below")
    if applies_below is not None and applies_below not in APPLIES_BELOW_TIERS:
        errors.append(f"{rid}: invalid applies_below {applies_below!r}")

    # promoted/enforced require target + target_path
    if status in ("promoted", "enforced"):
        if not row.get("target"):
            errors.append(f"{rid}: status={status} requires target to be set")
        if not row.get("target_path"):
            errors.append(f"{rid}: status={status} requires target_path to be set")

    return errors


def _check_path_resolves(root: Path, row: dict[str, Any]) -> str | None:
    """Return an error string if target_path doesn't resolve, else None."""
    rid = row.get("id", "<missing>")
    tp = row.get("target_path")
    if not tp:
        return None
    candidate = (root / tp).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return f"{rid}: target_path {tp!r} escapes repo root"
    if not candidate.exists():
        # Only report STALE when the first path component exists (anchored)
        parts = Path(tp).parts
        if parts and (root / parts[0]).exists():
            return f"{rid}: target_path {tp!r} does not exist in repo tree (STALE)"
        return f"{rid}: target_path {tp!r} is unresolvable (first component not found)"
    return None


def _check_applies_below_warning(row: dict[str, Any]) -> str | None:
    """Return a WARN string for universal-rule + applies_below mismatch."""
    rid = row.get("id", "<missing>")
    applies_below = row.get("applies_below")
    if applies_below is None:
        return None
    statement = row.get("statement", "")
    if UNIVERSAL_KEYWORDS.search(statement):
        return f"WARN {rid}: statement contains MUST/always/never but has applies_below={applies_below!r} — a universal rule must not be tier-filtered"
    return None


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_add(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    with _lesson_lock(root):
        rows = read_store(root)
        now = utc_now()
        new_id = _next_id(rows)
        row: dict[str, Any] = {
            "id": new_id,
            "statement": args.statement,
            "status": "candidate",
            "target": None,
            "target_path": None,
            "applies_below": args.applies_below if args.applies_below else None,
            "helpful_count": 0,
            "harmful_count": 0,
            "notes": [],
            "created_at": now,
            "updated_at": now,
            "source_session": args.source_session if args.source_session else None,
            "last_validated": None,
        }
        rows.append(row)
        write_store_atomic(root, rows)
    print(new_id)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    to_status: str = args.to_status

    if to_status not in VALID_STATUSES:
        raise SystemExit(f"invalid status {to_status!r}; must be one of {sorted(VALID_STATUSES)}")

    with _lesson_lock(root):
        rows = read_store(root)
        row = _find_row(rows, args.id)
        from_status: str = row["status"]

        changing_status = from_status != to_status
        field_update_requested = args.target is not None or args.target_path is not None

        # Determine legality
        if to_status == "retired":
            if field_update_requested:
                raise SystemExit("retirement cannot also update target fields; retarget before retiring")
            pass  # any → retired is always legal
        elif (from_status, to_status) in DEMOTION_TRANSITIONS:
            # Demotion requires a note
            if not args.note:
                raise SystemExit(
                    f"demotion {from_status!r} → {to_status!r} requires --note to record the cause"
                )
            if field_update_requested:
                raise SystemExit("demotion cannot also update target fields; retarget in a separate forward transition")
        elif from_status == to_status:
            if not field_update_requested:
                raise SystemExit(f"lesson {args.id} is already {from_status!r}")
        else:
            # Must be a legal forward step (no skipping)
            expected_next = FORWARD_TRANSITIONS.get(from_status)
            if expected_next is None:
                raise SystemExit(
                    f"no forward transition from {from_status!r} (lesson may already be in a terminal state)"
                )
            if to_status != expected_next:
                raise SystemExit(
                    f"illegal transition {from_status!r} → {to_status!r}: "
                    f"next legal forward step from {from_status!r} is {expected_next!r} "
                    f"(no skipping; demotions to {sorted(t for _, t in DEMOTION_TRANSITIONS if _ == from_status)} require --note)"
                )

        # Apply optional field updates
        if args.target:
            if args.target not in VALID_TARGETS:
                raise SystemExit(f"invalid target {args.target!r}; must be one of {sorted(VALID_TARGETS)}")
            row["target"] = args.target
        if args.target_path:
            row["target_path"] = args.target_path

        # Check promoted/enforced requirements (either already set or supplied now).
        # Only a forward transition can establish these fields; same-status retargeting
        # is allowed for repairing a stale target, while demotion/retirement cannot
        # smuggle in field changes.
        if changing_status and to_status in ("promoted", "enforced"):
            if not row.get("target"):
                raise SystemExit(
                    f"cannot transition to {to_status!r}: target is not set. "
                    f"Supply --target (one of {sorted(VALID_TARGETS)})."
                )
            if not row.get("target_path"):
                raise SystemExit(
                    f"cannot transition to {to_status!r}: target_path is not set. "
                    f"Supply --target-path."
                )

        row["status"] = to_status
        row["updated_at"] = utc_now()
        if args.note:
            row.setdefault("notes", []).append(args.note)

        write_store_atomic(root, rows)

    print(f"{args.id}: {from_status} → {to_status}")
    return 0


def cmd_outcome(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    with _lesson_lock(root):
        rows = read_store(root)
        row = _find_row(rows, args.id)
        if args.helpful:
            row["helpful_count"] = row.get("helpful_count", 0) + 1
        elif args.harmful:
            row["harmful_count"] = row.get("harmful_count", 0) + 1
        else:
            raise SystemExit("supply --helpful or --harmful")
        if args.note:
            row.setdefault("notes", []).append(args.note)
        row["updated_at"] = utc_now()
        write_store_atomic(root, rows)
    direction = "helpful" if args.helpful else "harmful"
    print(f"{args.id}: {direction} count incremented")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    # Hook leg: fail OPEN if store absent
    p = store_path(root)
    if not p.exists():
        return 0

    try:
        rows = read_store(root)
    except SystemExit as exc:
        print(f"[lesson_registry] validate: store parse error: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    ids_seen: set[str] = set()
    for row in rows:
        rid = str(row.get("id", "<missing>"))
        if rid in ids_seen:
            errors.append(f"duplicate id: {rid}")
        ids_seen.add(rid)

        errors.extend(_check_row_structure(row))

        status = row.get("status")
        if status in ("promoted", "enforced"):
            path_err = _check_path_resolves(root, row)
            if path_err:
                errors.append(path_err)

        w = _check_applies_below_warning(row)
        if w:
            warnings.append(w)

    for w in warnings:
        print(w, file=sys.stderr)

    if errors:
        for e in errors:
            print(f"ERROR {e}", file=sys.stderr)
        return 1

    print(f"lesson_registry validate: OK ({len(rows)} lessons)")
    return 0


def cmd_watermark(args: argparse.Namespace) -> int:
    """Advisory visibility — always exits 0."""
    root = Path(args.target_root).resolve()
    p = store_path(root)
    if not p.exists():
        return 0

    try:
        rows = read_store(root)
    except Exception as exc:
        print(f"[lesson_registry] watermark: store parse error: {exc}", file=sys.stderr)
        return 0

    candidates = [r for r in rows if r.get("status") == "candidate"]
    stale: list[str] = []
    for row in rows:
        if row.get("status") in ("promoted", "enforced"):
            path_err = _check_path_resolves(root, row)
            if path_err:
                stale.append(f"  {row.get('id')}: {row.get('target_path')} → {path_err.split('(', 1)[-1].rstrip(')')}")

    print(f"[lesson_registry] watermark: {len(candidates)} unprocessed candidate(s)", file=sys.stderr)
    if stale:
        print(f"[lesson_registry] watermark: {len(stale)} stale target_path(s):", file=sys.stderr)
        for s in stale:
            print(s, file=sys.stderr)
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    """SessionStart reminder block — fail OPEN."""
    profile = os.environ.get("HARNESS_PROFILE", "standard")
    if profile == "minimal":
        return 0

    root = Path(args.target_root).resolve()
    p = store_path(root)
    if not p.exists():
        return 0

    try:
        rows = read_store(root)
    except Exception as exc:
        print(f"[lesson_registry] inject: store parse error: {exc}", file=sys.stderr)
        return 0

    if not rows:
        return 0

    model_tier = getattr(args, "model_tier", None)

    def _should_show(row: dict[str, Any]) -> bool:
        ab = row.get("applies_below")
        if ab is None:
            return True
        if model_tier is None:
            return True
        # Show lesson when session tier is BELOW applies_below tier
        # e.g. applies_below=sonnet → show only when model_tier < sonnet
        session_rank = TIER_ORDER.get(model_tier, -1)
        applies_rank = TIER_ORDER.get(ab, -1)
        return session_rank < applies_rank

    # Collect lines to show
    unprocessed = [r for r in rows if r.get("status") == "candidate" and _should_show(r)]
    stale_targets: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") in ("promoted", "enforced"):
            if not _should_show(row):
                continue
            path_err = _check_path_resolves(root, row)
            if path_err:
                stale_targets.append(row)

    if not unprocessed and not stale_targets:
        return 0

    lines: list[str] = ["[lesson_registry]"]
    if unprocessed:
        lines.append(f"  {len(unprocessed)} unprocessed candidate lesson(s):")
        for row in unprocessed:
            stmt = str(row.get("statement", ""))
            truncated = stmt[:72] + "…" if len(stmt) > 72 else stmt
            lines.append(f"    {row['id']}: {truncated}")
    if stale_targets:
        lines.append(f"  {len(stale_targets)} promoted/enforced lesson(s) with stale target_path:")
        for row in stale_targets:
            lines.append(f"    {row['id']}: {row.get('target_path')!r} not found")

    # Hard cap at MAX_INJECT_LINES
    if len(lines) > MAX_INJECT_LINES:
        lines = lines[: MAX_INJECT_LINES - 1]
        lines.append("  ...truncated")

    for line in lines:
        print(line)
    return 0


def cmd_effectiveness(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    rows = read_store(root)
    if not rows:
        print("no lessons")
        return 0
    print(f"{'ID':<10} {'STATUS':<10} {'HELPFUL':>8} {'HARMFUL':>8}  STATEMENT")
    for row in rows:
        print(
            f"{str(row.get('id','')):<10} "
            f"{str(row.get('status','')):<10} "
            f"{row.get('helpful_count', 0):>8} "
            f"{row.get('harmful_count', 0):>8}  "
            f"{str(row.get('statement',''))[:60]}"
        )
    return 0


def _resolve_board_py(root: Path) -> Path | None:
    """Resolve board.py using the same probe logic as the hooks."""
    home = Path.home()
    candidates = [
        os.environ.get("PROJECT_META_DIR", ""),
        str(home / ".codex/skills/project-meta"),
        str(home / ".claude/skills/project-meta"),
    ]
    # glob-style expansions
    for base in [home / ".codex/plugins/marketplaces", home / ".claude/plugins/marketplaces"]:
        if base.is_dir():
            for c in sorted(base.glob("*/skills/project-meta")):
                candidates.append(str(c))
    for base in [home / ".codex/plugins/cache", home / ".claude/plugins/cache"]:
        if base.is_dir():
            for c in sorted(base.glob("*/*/*/skills/project-meta")):
                candidates.append(str(c))
            for c in sorted(base.glob("*/project-meta/*")):
                candidates.append(str(c))
    for c in candidates:
        if not c:
            continue
        p = Path(c) / "scripts" / "board.py"
        if p.is_file():
            return p
    return None


def cmd_trim_candidates(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    rows = read_store(root)
    suggestions: list[dict[str, Any]] = []

    for row in rows:
        status = row.get("status")
        if status not in ("promoted", "enforced"):
            continue
        reasons = []
        if row.get("helpful_count", 0) == 0:
            reasons.append("zero helpful_count")
        path_err = _check_path_resolves(root, row)
        if path_err:
            reasons.append(f"stale target_path: {row.get('target_path')!r}")
        if reasons:
            suggestions.append({"row": row, "reasons": reasons})

    if not suggestions:
        print("trim-candidates: no zero-value or stale-target promoted/enforced lessons found")
        return 0

    print(f"trim-candidates: {len(suggestions)} suggestion(s):")
    for s in suggestions:
        row = s["row"]
        print(f"  {row['id']}: {', '.join(s['reasons'])} — suggest retiring")

    if args.apply:
        board_py = _resolve_board_py(root)
        for s in suggestions:
            row = s["row"]
            stmt = f"Retire lesson {row['id']}: {row.get('statement', '')[:60]}"
            if board_py:
                cmd = [
                    "python3", str(board_py),
                    "--root", str(root),
                    "inbox-add",
                    "--kind", "chore",
                    "--title", stmt,
                    "--source", "lesson_registry.trim-candidates",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  board inbox captured: {stmt}")
                else:
                    print(f"  board inbox FAILED for {row['id']}: {result.stderr.strip()}")
            else:
                print(f"  [board.py unresolved] suggested: {stmt}")
    return 0


def cmd_promote_draft(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    rows = read_store(root)
    row = _find_row(rows, args.id)

    statement = row.get("statement", "")

    # Try to run collision/redundancy checks
    pm_scripts = None
    home = Path.home()
    for base in [
        os.environ.get("PROJECT_META_DIR", ""),
        str(home / ".codex/skills/project-meta"),
        str(home / ".claude/skills/project-meta"),
    ]:
        if base and (Path(base) / "scripts" / "trigger_collision_check.py").is_file():
            pm_scripts = Path(base) / "scripts"
            break

    collision_notes: list[str] = []
    if pm_scripts:
        for script_name in ("trigger_collision_check.py", "cross_skill_redundancy.py"):
            script = pm_scripts / script_name
            if script.is_file():
                try:
                    result = subprocess.run(
                        ["python3", str(script), "--statement", statement],
                        capture_output=True, text=True, timeout=15,
                    )
                    if result.stdout.strip():
                        collision_notes.append(f"[{script_name}] {result.stdout.strip()}")
                except Exception as exc:
                    collision_notes.append(f"[{script_name}] warning: {exc}")
    else:
        print("WARN promote-draft: trigger_collision_check.py / cross_skill_redundancy.py not resolved; skipping collision check", file=sys.stderr)

    print(f"promote-draft {args.id}:")
    print(f"  statement: {statement}")
    if collision_notes:
        for note in collision_notes:
            print(f"  {note}")

    board_py = _resolve_board_py(root)
    board_cmd = "board.py" if not board_py else str(board_py)
    print(f"\nBoard inbox draft (operator approval required):")
    print(f"  python3 {board_cmd} --root . inbox-add \\")
    print(f"    --kind chore \\")
    print(f"    --title 'Promote lesson {args.id} to next status' \\")
    print(f"    --body '{statement[:120]}' \\")
    print(f"    --source 'lesson_registry.promote-draft'")
    print("\nDoes NOT auto-promote. Review collision notes above before applying.")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lesson_registry.py",
        description="Lesson registry: durable per-repo learned-policy store.",
    )
    parser.add_argument(
        "--target-root",
        default=".",
        metavar="DIR",
        help="Repo root (default: current directory).",
    )

    sub = parser.add_subparsers(dest="subcommand", metavar="subcommand")
    sub.required = True

    # add
    p_add = sub.add_parser("add", help="Add a new candidate lesson.")
    p_add.add_argument("--statement", required=True, help="Lesson statement text.")
    p_add.add_argument("--source-session", default=None, metavar="SESSION_ID",
                       help="Optional source session identifier.")
    p_add.add_argument("--applies-below", default=None, choices=sorted(TIER_ORDER.keys()),
                       help="Only applies to sessions running a model below this tier.")
    p_add.set_defaults(func=cmd_add)

    # status
    p_status = sub.add_parser("status", help="Transition a lesson's status.")
    p_status.add_argument("id", help="Lesson id (e.g. LES-001).")
    p_status.add_argument("to_status", metavar="to",
                          choices=sorted(VALID_STATUSES),
                          help="Target status.")
    p_status.add_argument("--target", choices=sorted(VALID_TARGETS),
                          help="Set target (memory|hook|linter).")
    p_status.add_argument("--target-path", dest="target_path",
                          help="Set target_path (repo-relative).")
    p_status.add_argument("--note", default=None, help="Note to append (required for demotions).")
    p_status.set_defaults(func=cmd_status)

    # outcome
    p_outcome = sub.add_parser("outcome", help="Record helpful/harmful feedback.")
    p_outcome.add_argument("id", help="Lesson id.")
    group = p_outcome.add_mutually_exclusive_group(required=True)
    group.add_argument("--helpful", action="store_true")
    group.add_argument("--harmful", action="store_true")
    p_outcome.add_argument("--note", default=None)
    p_outcome.set_defaults(func=cmd_outcome)

    # validate
    p_val = sub.add_parser("validate", help="Hard gate: check structure + path resolution.")
    p_val.set_defaults(func=cmd_validate)

    # watermark
    p_wm = sub.add_parser("watermark", help="Advisory visibility (always exits 0).")
    p_wm.set_defaults(func=cmd_watermark)

    # inject
    p_inj = sub.add_parser("inject", help="Print SessionStart reminder block (≤20 lines).")
    p_inj.add_argument("--model-tier", dest="model_tier",
                       choices=sorted(TIER_ORDER.keys()), default=None,
                       help="Current session model tier; filters applies_below lessons.")
    p_inj.set_defaults(func=cmd_inject)

    # effectiveness
    p_eff = sub.add_parser("effectiveness", help="Print helpful/harmful table per lesson.")
    p_eff.set_defaults(func=cmd_effectiveness)

    # trim-candidates
    p_trim = sub.add_parser("trim-candidates",
                             help="List zero-value/stale promoted/enforced lessons; suggest retiring.")
    p_trim.add_argument("--apply", action="store_true",
                        help="Write board inbox captures for suggested retirements.")
    p_trim.set_defaults(func=cmd_trim_candidates)

    # promote-draft
    p_pd = sub.add_parser("promote-draft",
                           help="Run collision checks + emit board inbox draft for operator approval.")
    p_pd.add_argument("id", help="Lesson id to draft promotion for.")
    p_pd.set_defaults(func=cmd_promote_draft)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.target_root = str(Path(args.target_root).resolve())
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Lesson registry — durable per-repo learned-policy store.

Store: .harness/lessons.jsonl  (git-TRACKED — durable learned policy)
One JSON row per lesson. Single writer; full-file atomic rewrite on each mutation.

Row schema (v2 — E1/DASH-073; v1 rows without the new fields stay valid):
  {id, statement, status, target, target_path, scope_paths, gate_id,
   applies_below, helpful_count, harmful_count, observations, notes,
   created_at, updated_at, source_session, last_validated}

  target_path  — where the lesson's enforcement artifact lives (unchanged, v1)
  scope_paths  — list of repo-relative globs the lesson's GUIDANCE concerns
                 (distinct from target_path; required for observe eligibility)
  gate_id      — optional verify-before-stop.sh leg this lesson corresponds to
                 (closed enum, see GATE_IDS)
  observations — append-only evidence rows
                 {direction: helpful|harmful, source: observe|manual,
                  scope_snapshot, note, utc}
                 helpful_count/harmful_count are the frozen v1 baseline ints;
                 effective counts = baseline + observation tallies. The E2
                 promotion gate counts ONLY observations bound to the row's
                 current scope (retargeting invalidates evidence by construction).

Status ladder (legal transitions only):
  candidate → recorded → promoted → enforced
  any → retired
  enforced → promoted  (demotion; requires --note)
  promoted → recorded  (demotion; requires --note)

  promoted/enforced transitions additionally require evidence (E2/DASH-074):
  >=3 helpful observations bound to the current scope and no blocking harmful
  observation; enforced also requires a runnable target artifact. --force with
  a mandatory --note overrides, leaving the audit trail in notes[].

Subcommands (all accept --target-root, default cwd):
  add           Add a new candidate lesson
  status        Transition a lesson's status (evidence-gated at promoted/enforced)
  outcome       Record helpful/harmful feedback (manual; --note required)
  observe       Stop-hook heuristic evidence leg (advisory, fail OPEN)
  validate      Hard gate: structure + path resolution + protected-paths
  watermark     Advisory visibility: candidate count + stale targets
  inject        SessionStart reminder block (≤20 lines)
  effectiveness Print helpful/harmful table (baseline + observations)
  trim-candidates  Identify zero-value/stale promoted/enforced lessons
  auto-demote      Draft (or --apply) demotions on harmful evidence / stale target
  promote-draft    Statement-coverage check + board inbox draft

Trust model (proposal §2, self-evolving-lessons-2026): observations are
decision-support with an audit trail, NOT a security boundary — the store is
plain text the measured agent can edit. Git history is the tamper record; every
draft prints its evidence inline so the operator judges substance.

Fail directions:
  Direct CLI → fail CLOSED (exit 1 on bad input/bad state)
  Hook legs (watermark/inject/observe) → fail OPEN (missing store → warn + exit 0)

Standard library only.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fnmatch
import hashlib
import itertools
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
TIER_ALIASES = {"luna": "sonnet", "terra": "opus", "sol": "fable"}

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

# --- E1/DASH-073: schema v2 constants ---------------------------------------

# Gate-event artifact written by verify-before-stop.sh's advisory_exit; consumed
# (read + truncated) by `observe` on the next invocation.
EVENTS_RELPATH = ".harness/stop-gate-events.jsonl"

# observe's dirty-tree watermark: the previous invocation's porcelain entries.
# Only the DELTA counts as "the turn's changed files" — a static dirty file
# re-observed across invocations farms nothing (PR #74 adversarial review F4).
SNAPSHOT_RELPATH = ".harness/observe-snapshot.json"

# Closed enum of verify-before-stop.sh legs a lesson's gate_id may name.
GATE_IDS = {
    "phase-lock", "project-verify", "writeback", "dispatch", "board-tx",
    "audit-convergence", "last-turn-meta", "lesson-validate",
}

VALID_OBS_DIRECTIONS = {"helpful", "harmful"}
VALID_OBS_SOURCES = {"observe", "manual"}

# E2/DASH-074 evidence gate threshold.
PROMOTION_EVIDENCE_MIN = 3

# E3/DASH-075 auto-demote threshold.
DEMOTE_HARMFUL_MIN = 2

# validate WARNs when a scope_paths glob is one of these, or matches more files.
BROAD_SCOPE_PATTERNS = {".", "*", "**", "**/*", "./**", "./*"}
BROAD_SCOPE_FILE_CAP = 200

# E2/DASH-074: protected-paths override note prefix (matched literally).
VERIFIER_ACK_PREFIX = "verifier_ack:"

# Frozen fallback for the derived protected-paths set, used only when the
# project-meta install is unresolvable. The derived set (see _protected_basenames)
# is preferred so new gates can't silently drift out of protection.
FROZEN_PROTECTED_BASENAMES = {
    # scripts/ graders + shared CLIs
    "lesson_registry.py", "repo_memory.py", "dispatch_ledger.py", "board.py",
    "audit_ledger.py", "last_turn_meta.py", "session_receipt.py",
    "phase_lock_check.py", "memory_staleness.py", "derive_profile.py",
    "worktree_audit.py", "provenance.py", "test_integrity_diff.py",
    "loop_state.py", "pressure_test_skill.py",
    # skill-critics suite (references/skill-critics.md)
    "skill_architecture_lint.py", "trigger_collision_check.py",
    "context_cost_estimate.py", "determinism_gap_scan.py",
    "cross_skill_redundancy.py",
    # hook pack
    "verify-before-stop.sh", "load-agents-md.sh", "board-guard.sh",
    "pre-tool-guard.sh", "dispatch-tier-guard.sh", "format-on-edit.sh",
    "env-readiness-probe.sh", "issue-tracker-reminder.sh",
    "provenance-on-edit.sh", "capture-out-of-scope.sh",
}


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
# Schema v2 helpers (E1/E2/E3 — DASH-073..075)
# ---------------------------------------------------------------------------

def _observations(row: dict[str, Any]) -> list[dict[str, Any]]:
    obs = row.get("observations")
    return obs if isinstance(obs, list) else []


def _effective_counts(row: dict[str, Any]) -> tuple[int, int]:
    """(helpful, harmful) = frozen v1 baseline ints + observation tallies."""
    helpful = int(row.get("helpful_count", 0) or 0)
    harmful = int(row.get("harmful_count", 0) or 0)
    for o in _observations(row):
        if o.get("direction") == "helpful":
            helpful += 1
        elif o.get("direction") == "harmful":
            harmful += 1
    return helpful, harmful


def _scope_key(scope: Any) -> Any:
    """Order-insensitive comparison key: ["a","b"] and ["b","a"] are the same
    scope, not a semantic retarget."""
    if isinstance(scope, list):
        return tuple(sorted(str(p) for p in scope))
    return scope


def _scope_bound_obs(row: dict[str, Any], direction: str) -> list[dict[str, Any]]:
    """Observations of `direction` whose scope_snapshot matches the row's
    CURRENT scope_paths — the E2 binding rule: retargeting invalidates evidence."""
    current = _scope_key(row.get("scope_paths"))
    out = []
    for o in _observations(row):
        if o.get("direction") != direction:
            continue
        if _scope_key(o.get("scope_snapshot")) == current:
            out.append(o)
    return out


def _blocking_harmful_obs(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Harmful observations that block promotion: bound to the current scope,
    or recorded with no snapshot at all (conservative)."""
    current = _scope_key(row.get("scope_paths"))
    out = []
    for o in _observations(row):
        if o.get("direction") != "harmful":
            continue
        snap = o.get("scope_snapshot")
        if snap is None or _scope_key(snap) == current:
            out.append(o)
    return out


def _append_observation(row: dict[str, Any], direction: str, source: str,
                        note: str | None) -> None:
    row.setdefault("observations", []).append({
        "direction": direction,
        "source": source,
        "scope_snapshot": row.get("scope_paths"),
        "note": note,
        "utc": utc_now(),
    })
    row["updated_at"] = utc_now()


def _format_evidence(row: dict[str, Any], indent: str = "    ") -> list[str]:
    """Render observations + notes inline so drafts show substance, not a count."""
    lines: list[str] = []
    for o in _observations(row):
        note = f" — {o.get('note')}" if o.get("note") else ""
        lines.append(f"{indent}[{o.get('utc','?')}] {o.get('direction')}/{o.get('source')}{note}")
    for n in row.get("notes") or []:
        lines.append(f"{indent}note: {n}")
    if not lines:
        lines.append(f"{indent}(no observations or notes recorded)")
    return lines


def _path_in_scope(path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        pat = pat.strip()
        if not pat:
            continue
        if fnmatch.fnmatch(path, pat) or path == pat:
            return True
        if path.startswith(pat.rstrip("/") + "/"):
            return True
    return False


def _resolve_pm_dir() -> Path | None:
    """Resolve the installed project-meta dir (same probe order as the hooks)."""
    home = Path.home()
    candidates = [
        os.environ.get("PROJECT_META_DIR", ""),
        str(home / ".codex/skills/project-meta"),
        str(home / ".claude/skills/project-meta"),
    ]
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
        if c and (Path(c) / "scripts").is_dir() and (Path(c) / "scripts" / "lesson_registry.py").is_file():
            return Path(c)
    return None


def _protected_basenames() -> set[str]:
    """Derive the protected grader/hook file set from the installed project-meta
    (so new gates are protected automatically); fall back to the frozen list."""
    pm = _resolve_pm_dir()
    if pm is None:
        return set(FROZEN_PROTECTED_BASENAMES)
    derived: set[str] = set()
    with contextlib.suppress(OSError):
        derived |= {p.name for p in (pm / "scripts").glob("*.py")}
    with contextlib.suppress(OSError):
        derived |= {p.name for p in (pm / "templates" / "hooks" / "scripts").glob("*.sh")}
    return derived | set(FROZEN_PROTECTED_BASENAMES)


def _protected_path_hit(relpath: str, basenames: set[str]) -> str | None:
    """Return a reason string when relpath points at lesson-grading machinery."""
    rp = relpath.strip().rstrip("/")
    if not rp:
        return None
    if rp in (STORE_RELPATH, LOCK_RELPATH, EVENTS_RELPATH):
        return "the lesson store/lock/event files themselves"
    if rp == ".harness/verify.sh" or rp.startswith(".harness/gates/"):
        return "a repo-local verification gate"
    if "templates/hooks/scripts/" in rp:
        return "the hook pack"
    if Path(rp).name in basenames:
        return "a grader/hook script (derived protected set)"
    return None


def _ack_covers(note: str, candidate: str) -> bool:
    """True when a verifier_ack: note names `candidate` as an exact
    whitespace/punctuation-delimited token (not a substring)."""
    if not note.startswith(VERIFIER_ACK_PREFIX):
        return False
    tokens = re.split(r"[\s,;:'\"()]+", note[len(VERIFIER_ACK_PREFIX):])
    return candidate in tokens


def _check_protected(row: dict[str, Any], basenames: set[str]) -> str | None:
    """E2(b): a lesson must not target the machinery that grades lessons,
    unless a note with the literal prefix `verifier_ack:` records the review."""
    rid = row.get("id", "<missing>")
    candidates: list[str] = []
    if row.get("target_path"):
        candidates.append(str(row["target_path"]))
    for pat in row.get("scope_paths") or []:
        # Only literal (non-glob) scope entries are checked; a glob has no basename.
        if not any(ch in pat for ch in "*?["):
            candidates.append(pat)
    for c in candidates:
        reason = _protected_path_hit(c, basenames)
        if reason:
            # The ack is PATH-BOUND: it must start with the prefix AND name this
            # exact path as a whole token — substring matching would let an ack
            # citing dashboard.py unlock board.py. One ack cannot blanket-cover
            # a later retarget to a different protected file. (Ack authorship
            # remains trust-model — git history is the tamper record.)
            notes = row.get("notes") or []
            if any(_ack_covers(str(n), c) for n in notes):
                continue
            return (f"{rid}: path {c!r} points at {reason} — the lesson system must "
                    f"not rewrite its own grader unreviewed. Add a note starting with "
                    f"{VERIFIER_ACK_PREFIX!r} and naming {c!r} after an operator review "
                    f"to override.")
    return None


def _scope_breadth_warning(root: Path, row: dict[str, Any]) -> str | None:
    """WARN on scope_paths broad enough to farm helpful observations (E1)."""
    rid = row.get("id", "<missing>")
    for pat in row.get("scope_paths") or []:
        p = pat.strip()
        if p in BROAD_SCOPE_PATTERNS:
            return f"WARN {rid}: scope_paths pattern {p!r} matches the whole tree — too broad to be meaningful evidence"
        if any(ch in p for ch in "*?["):
            try:
                matched = list(itertools.islice(
                    (m for m in root.glob(p) if ".git" not in m.parts),
                    BROAD_SCOPE_FILE_CAP + 1))
            except (OSError, ValueError, NotImplementedError):
                continue
            if len(matched) > BROAD_SCOPE_FILE_CAP:
                return (f"WARN {rid}: scope_paths pattern {p!r} matches >"
                        f"{BROAD_SCOPE_FILE_CAP} files — too broad to be meaningful evidence")
    return None


def _porcelain_entries(root: Path) -> list[str]:
    """Raw `git status --porcelain -z` entries ("XY path"). -z avoids the
    octal-quoting of non-ASCII paths that a text-mode parse cannot round-trip."""
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "-z", "--untracked-files=all"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []
    fields = result.stdout.split("\0")
    entries: list[str] = []
    i = 0
    while i < len(fields):
        f = fields[i]
        if not f:
            i += 1
            continue
        entries.append(f)
        # Rename/copy entries carry the ORIGINAL path as a second NUL field —
        # consume it so it is not misread as a standalone entry.
        if len(f) >= 2 and f[0] in ("R", "C"):
            i += 2
        else:
            i += 1
    return entries


def _entry_paths(entries: list[str]) -> list[str]:
    return [e[3:] for e in entries if len(e) > 3]


def _changed_files(root: Path) -> list[str]:
    """Repo-relative changed paths via git porcelain (same source repo_memory.py uses)."""
    return _entry_paths(_porcelain_entries(root))


def _consume_gate_events(root: Path) -> list[dict[str, Any]]:
    """Read + truncate the stop-gate-events artifact (at-most-once accounting)."""
    p = root / EVENTS_RELPATH
    if not p.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            with contextlib.suppress(json.JSONDecodeError):
                row = json.loads(line)
                if isinstance(row, dict):
                    events.append(row)
        p.write_text("", encoding="utf-8")
    except OSError:
        return events
    return events


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def _parse_scope_paths(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


def cmd_add(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    with _lesson_lock(root):
        rows = read_store(root)
        now = utc_now()
        new_id = _next_id(rows)
        scope_paths = _parse_scope_paths(args.scope_paths)
        if args.gate_id and args.gate_id not in GATE_IDS:
            raise SystemExit(f"invalid gate_id {args.gate_id!r}; must be one of {sorted(GATE_IDS)}")
        row: dict[str, Any] = {
            "id": new_id,
            "statement": args.statement,
            "status": "candidate",
            "target": None,
            "target_path": None,
            "scope_paths": scope_paths,
            "gate_id": args.gate_id if args.gate_id else None,
            "applies_below": args.applies_below if args.applies_below else None,
            "helpful_count": 0,
            "harmful_count": 0,
            "observations": [],
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
        field_update_requested = (args.target is not None or args.target_path is not None
                                  or args.scope_paths is not None)

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
        if args.scope_paths is not None:
            row["scope_paths"] = _parse_scope_paths(args.scope_paths)

        # Check promoted/enforced requirements. These run whenever the row ENDS
        # UP in promoted/enforced and this call changed anything (status OR
        # fields) — a same-status retarget must re-pass every gate, otherwise
        # `status <id> enforced --target-path NEW` on an already-enforced row
        # would bypass the evidence/protected/runnable checks entirely
        # (found by the PR #74 adversarial review).
        if to_status in ("promoted", "enforced") and (changing_status or field_update_requested):
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

            # E2/DASH-074: protected-paths check at transition time (not only in
            # validate) — refuse to point a promoted/enforced lesson at the
            # grading machinery. The path-bound verifier_ack: note (checked
            # inside) is the operator-review override; --force does NOT bypass
            # this check.
            note_pool = list(row.get("notes") or [])
            if args.note:
                note_pool.append(args.note)
            probe = dict(row)
            probe["notes"] = note_pool
            prot_err = _check_protected(probe, _protected_basenames())
            if prot_err:
                raise SystemExit(f"cannot apply transition: {prot_err}")

            # E2/DASH-074: evidence gate. Counts ONLY observations bound to the
            # row's current scope — a retarget-then-promote farms nothing because
            # the snapshot comparison invalidates prior evidence by construction.
            if not args.force:
                helpful = _scope_bound_obs(row, "helpful")
                harmful = _blocking_harmful_obs(row)
                problems: list[str] = []
                if len(helpful) < PROMOTION_EVIDENCE_MIN:
                    problems.append(
                        f"needs >={PROMOTION_EVIDENCE_MIN} helpful observation(s) bound to the "
                        f"current scope_paths; has {len(helpful)}")
                if harmful:
                    problems.append(f"has {len(harmful)} blocking harmful observation(s)")
                # E2 weighs breadth (proposal E1(d)/E2): observe-farmed evidence
                # on a whole-tree or >cap scope is not promotable without --force.
                breadth = _scope_breadth_warning(root, row)
                if breadth:
                    problems.append(f"scope too broad for observe evidence ({breadth.split(': ', 1)[-1]})")
                if problems:
                    evidence = "\n".join(_format_evidence(row))
                    raise SystemExit(
                        f"cannot transition {args.id} to {to_status!r}: "
                        + "; ".join(problems)
                        + f"\nEvidence on record:\n{evidence}"
                        + "\nOverride with --force --note '<why>' (leaves an audit trail)."
                    )
            elif not args.note:
                raise SystemExit("--force requires --note to record why the evidence gate was bypassed")

            # E2/DASH-074: enforced additionally requires a runnable target artifact.
            if to_status == "enforced" and not args.force:
                tp = root / str(row.get("target_path"))
                if not tp.is_file():
                    raise SystemExit(
                        f"cannot transition to 'enforced': target_path {row.get('target_path')!r} "
                        f"is not a file in the repo tree")
                if row.get("target") in ("hook", "linter"):
                    runnable = os.access(tp, os.X_OK) or tp.suffix == ".py"
                    if not runnable:
                        raise SystemExit(
                            f"cannot transition to 'enforced': target {row.get('target_path')!r} "
                            f"is neither executable nor a .py script — an enforced lesson "
                            f"needs a runnable enforcement artifact")

        row["status"] = to_status
        row["updated_at"] = utc_now()
        if args.note:
            row.setdefault("notes", []).append(args.note)

        write_store_atomic(root, rows)

    print(f"{args.id}: {from_status} → {to_status}")
    return 0


def _harmful_note_ok(note: str) -> bool:
    """E3: a manual harmful note must cite a gate id or a file/path-like token."""
    if any(g in note for g in GATE_IDS):
        return True
    return bool(re.search(r"/|[\w-]+\.\w{1,6}", note))


def cmd_outcome(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    # E3/DASH-075: manual outcomes are evidence — they must carry their trigger.
    # (Hook-written `observe` rows stamp their trigger automatically.)
    if not args.note:
        raise SystemExit("outcome requires --note citing the turn/gate/file that produced the evidence")
    if args.harmful and not _harmful_note_ok(args.note):
        raise SystemExit(
            f"--harmful note must reference a gate id ({', '.join(sorted(GATE_IDS))}) "
            f"or a file path, so the demotion trail is judgeable")
    with _lesson_lock(root):
        rows = read_store(root)
        row = _find_row(rows, args.id)
        direction = "helpful" if args.helpful else "harmful"
        _append_observation(row, direction, "manual", args.note)
        write_store_atomic(root, rows)
    print(f"{args.id}: {direction} observation recorded (manual)")
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    """E1/DASH-073: Stop-hook heuristic evidence leg. Advisory — ALWAYS exits 0.

    Recomputes in-scope rows directly from the store (no inject-receipt file):
      helpful — the turn's changed files match a row's scope_paths and its
                gate_id (if set) has no failure event pending;
      harmful — the row's gate_id appears in .harness/stop-gate-events.jsonl
                (written by advisory_exit; consumed read-then-truncate here).
    Rows without scope_paths are ineligible — no scope, no signal.
    At most one observation per row per invocation. Deliberately coarse:
    cheap heuristic signals beat absent signals (proposal ¶3).
    """
    if os.environ.get("HARNESS_PROFILE", "standard") == "minimal":
        return 0
    try:
        root = Path(args.target_root).resolve()
        if not store_path(root).exists():
            return 0

        if args.changed_files_from:
            # An explicit list from the hook is authoritative (already a delta).
            try:
                changed = [ln.strip() for ln in Path(args.changed_files_from)
                           .read_text(encoding="utf-8").splitlines() if ln.strip()]
            except OSError:
                changed = []
        else:
            # Delta vs the previous invocation's snapshot: a file left dirty
            # across Stop cycles counts once, not once per cycle. Each entry is
            # fingerprinted with mtime/size so a file genuinely edited AGAIN
            # between observes re-counts, while an untouched dirty file doesn't.
            entries = _porcelain_entries(root)

            def _fingerprint(entry: str) -> str:
                # Content-based (first 64KB + size): a no-op touch/autosave that
                # bumps mtime without changing bytes must not re-count as a new
                # change (fix-verify residual on PR #74 F4).
                path = entry[3:] if len(entry) > 3 else ""
                p = root / path
                try:
                    size = p.stat().st_size
                    with open(p, "rb") as fh:
                        digest = hashlib.sha256(fh.read(65536)).hexdigest()[:16]
                    return f"{entry}|{digest}:{size}"
                except OSError:
                    return f"{entry}|absent"

            fingerprints = [_fingerprint(e) for e in entries]
            snap_p = root / SNAPSHOT_RELPATH
            prev: set[str] = set()
            if snap_p.exists():
                with contextlib.suppress(OSError, json.JSONDecodeError):
                    loaded = json.loads(snap_p.read_text(encoding="utf-8"))
                    if isinstance(loaded, list):
                        prev = {str(x) for x in loaded}
            changed = _entry_paths([e for e, fp in zip(entries, fingerprints)
                                    if fp not in prev])
            with contextlib.suppress(OSError):
                snap_p.parent.mkdir(parents=True, exist_ok=True)
                snap_p.write_text(json.dumps(fingerprints), encoding="utf-8")

        events = _consume_gate_events(root)
        failed_gates = {str(e.get("gate")) for e in events if e.get("gate")}

        raw_tier = getattr(args, "model_tier", None)
        model_tier = TIER_ALIASES.get(raw_tier, raw_tier)

        recorded_ids: list[str] = []
        with _lesson_lock(root):
            rows = read_store(root)
            for row in rows:
                if row.get("status") not in ("recorded", "promoted", "enforced"):
                    continue
                scope = row.get("scope_paths")
                if not scope:
                    continue
                ab = row.get("applies_below")
                if ab is not None and model_tier is not None:
                    if TIER_ORDER.get(model_tier, -1) >= TIER_ORDER.get(ab, -1):
                        continue
                gate = row.get("gate_id")
                if gate and gate in failed_gates:
                    _append_observation(row, "harmful", "observe",
                                        f"auto: gate {gate} failed this turn")
                    recorded_ids.append(f"{row['id']}:harmful")
                    continue
                if changed and any(_path_in_scope(f, scope) for f in changed):
                    _append_observation(row, "helpful", "observe",
                                        "auto: changed files matched scope; no gate failure")
                    recorded_ids.append(f"{row['id']}:helpful")
            if recorded_ids:
                write_store_atomic(root, rows)
        if recorded_ids:
            print(f"[lesson_registry] observe: {', '.join(recorded_ids)}", file=sys.stderr)
    except (Exception, SystemExit) as exc:
        # Fail OPEN: an advisory evidence leg must never wedge the turn
        # (lock contention with an agent-invoked CLI call included).
        print(f"[lesson_registry] observe: skipped ({exc})", file=sys.stderr)
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
    protected = _protected_basenames()

    ids_seen: set[str] = set()
    for row in rows:
        rid = str(row.get("id", "<missing>"))
        if rid in ids_seen:
            errors.append(f"duplicate id: {rid}")
        ids_seen.add(rid)

        errors.extend(_check_row_structure(row))

        # E1/DASH-073: schema v2 field checks (absent fields stay valid — v1 rows).
        gate_id = row.get("gate_id")
        if gate_id is not None and gate_id not in GATE_IDS:
            errors.append(f"{rid}: invalid gate_id {gate_id!r} (must be one of {sorted(GATE_IDS)})")
        scope_paths = row.get("scope_paths")
        if scope_paths is not None and (
                not isinstance(scope_paths, list)
                or not all(isinstance(p, str) and p.strip() for p in scope_paths)):
            errors.append(f"{rid}: scope_paths must be a list of non-empty strings")
        for o in _observations(row):
            if not isinstance(o, dict) or o.get("direction") not in VALID_OBS_DIRECTIONS \
                    or o.get("source") not in VALID_OBS_SOURCES:
                errors.append(f"{rid}: malformed observation row {o!r}")
                break

        # E2/DASH-074: protected-paths — the lesson system must not rewrite its
        # own grader unreviewed (verifier_ack: note overrides after review).
        prot_err = _check_protected(row, protected)
        if prot_err:
            errors.append(prot_err)

        status = row.get("status")
        if status in ("promoted", "enforced"):
            path_err = _check_path_resolves(root, row)
            if path_err:
                errors.append(path_err)

        w = _check_applies_below_warning(row)
        if w:
            warnings.append(w)
        w2 = _scope_breadth_warning(root, row)
        if w2:
            warnings.append(w2)

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
    except (Exception, SystemExit) as exc:
        # Advisory leg: a corrupt store must NOT wedge the turn. read_store raises
        # SystemExit on bad JSON (a BaseException, not caught by `except Exception`),
        # so catch it explicitly here. `validate` (the gate) still fails closed.
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
    except (Exception, SystemExit) as exc:
        # Advisory leg: fail OPEN on a corrupt store (read_store raises SystemExit on
        # bad JSON, a BaseException). The gate is `validate`, not inject.
        print(f"[lesson_registry] inject: store parse error: {exc}", file=sys.stderr)
        return 0

    if not rows:
        return 0

    raw_model_tier = getattr(args, "model_tier", None)
    model_tier = TIER_ALIASES.get(raw_model_tier, raw_model_tier)

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

    # Collect lines to show. E1/DASH-073 extends the surfaced set: recorded rows
    # and healthy promoted/enforced rows are re-shown (they were previously
    # invisible after leaving candidate status, starving the observe/evidence
    # loop). Priority under the cap: candidates → stale → recorded → healthy.
    unprocessed = [r for r in rows if r.get("status") == "candidate" and _should_show(r)]
    stale_targets: list[dict[str, Any]] = []
    healthy: list[dict[str, Any]] = []
    for row in rows:
        if row.get("status") in ("promoted", "enforced"):
            if not _should_show(row):
                continue
            path_err = _check_path_resolves(root, row)
            if path_err:
                stale_targets.append(row)
            else:
                healthy.append(row)
    recorded = [r for r in rows if r.get("status") == "recorded" and _should_show(r)]

    if not unprocessed and not stale_targets and not recorded and not healthy:
        return 0

    def _stmt(row: dict[str, Any], width: int = 72) -> str:
        stmt = str(row.get("statement", ""))
        return stmt[:width] + "…" if len(stmt) > width else stmt

    lines: list[str] = ["[lesson_registry]"]
    if unprocessed:
        lines.append(f"  {len(unprocessed)} unprocessed candidate lesson(s):")
        for row in unprocessed:
            lines.append(f"    {row['id']}: {_stmt(row)}")
    if stale_targets:
        lines.append(f"  {len(stale_targets)} promoted/enforced lesson(s) with stale target_path:")
        for row in stale_targets:
            lines.append(f"    {row['id']}: {row.get('target_path')!r} not found")
    if recorded:
        lines.append(f"  {len(recorded)} recorded lesson(s) (apply; evidence gates promotion):")
        for row in recorded:
            lines.append(f"    {row['id']}: {_stmt(row)}")
    if healthy:
        lines.append(f"  {len(healthy)} active promoted/enforced lesson(s):")
        for row in healthy:
            lines.append(f"    {row['id']}: {_stmt(row)}")

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
    print(f"{'ID':<10} {'STATUS':<10} {'HELPFUL':>8} {'HARMFUL':>8} {'OBS':>4}  STATEMENT")
    for row in rows:
        helpful, harmful = _effective_counts(row)
        print(
            f"{str(row.get('id','')):<10} "
            f"{str(row.get('status','')):<10} "
            f"{helpful:>8} "
            f"{harmful:>8} "
            f"{len(_observations(row)):>4}  "
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
        if _effective_counts(row)[0] == 0:
            reasons.append("zero helpful evidence")
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


def cmd_auto_demote(args: argparse.Namespace) -> int:
    """E3/DASH-075: symmetric demotion. Draft by default; --apply performs the
    legal one-rung demotion with an auto-stamped note. Drafts print the full
    evidence inline so the operator judges substance, not an opaque count."""
    root = Path(args.target_root).resolve()
    rows = read_store(root)

    suggestions: list[tuple[dict[str, Any], list[str]]] = []
    for row in rows:
        status = row.get("status")
        if status not in ("promoted", "enforced"):
            continue
        reasons: list[str] = []
        # Evidence older than the last applied demotion is spent — the same two
        # harmful observations must not walk a lesson down two rungs across two
        # runs (PR #74 correctness review F4).
        cutoff = row.get("last_demoted_at")
        harmful = [o for o in _blocking_harmful_obs(row)
                   if not cutoff or str(o.get("utc", "")) > str(cutoff)]
        if len(harmful) >= DEMOTE_HARMFUL_MIN:
            reasons.append(f"{len(harmful)} harmful observation(s) against the current scope")
        path_err = _check_path_resolves(root, row)
        if path_err:
            reasons.append(f"stale target_path: {row.get('target_path')!r}")
        if reasons:
            suggestions.append((row, reasons))

    if not suggestions:
        print("auto-demote: no promoted/enforced lessons with demotion triggers")
        return 0

    down_map = {"enforced": "promoted", "promoted": "recorded"}
    for row, reasons in suggestions:
        down = down_map[row["status"]]
        trigger = "; ".join(reasons)
        print(f"auto-demote: {row['id']} {row['status']} → {down} — {trigger}")
        print("  evidence:")
        for line in _format_evidence(row):
            print(line)
        if not args.apply:
            print(f"  draft: python3 lesson_registry.py --target-root {root} "
                  f"status {row['id']} {down} --note 'auto-demote: {trigger}'")

    if args.apply:
        with _lesson_lock(root):
            fresh = read_store(root)
            for row, reasons in suggestions:
                live = _find_row(fresh, row["id"])
                if live.get("status") not in down_map:
                    continue
                down = down_map[live["status"]]
                live["status"] = down
                live.setdefault("notes", []).append(
                    f"auto-demote: {'; '.join(reasons)}")
                live["last_demoted_at"] = utc_now()
                live["updated_at"] = utc_now()
            write_store_atomic(root, fresh)
        print(f"auto-demote: applied {len(suggestions)} demotion(s)")
    return 0


def cmd_promote_draft(args: argparse.Namespace) -> int:
    root = Path(args.target_root).resolve()
    rows = read_store(root)
    row = _find_row(rows, args.id)

    statement = row.get("statement", "")

    # E0/DASH-072: statement-coverage check via cross_skill_redundancy.py's
    # --statement mode. (The previous invocation passed --statement to scripts
    # that only take a positional path and only read stdout — argparse exited 2
    # to stderr and the check was a silent no-op since it shipped.
    # trigger_collision_check.py compares whole trigger surfaces pairwise and
    # has no meaningful single-statement mode, so it is no longer invoked here.)
    pm_dir = _resolve_pm_dir()
    collision_notes: list[str] = []
    if pm_dir is None:
        print("WARN promote-draft: project-meta scripts not resolved; skipping coverage check", file=sys.stderr)
    else:
        script = pm_dir / "scripts" / "cross_skill_redundancy.py"
        # Prefer the target repo's own skill tree; fall back to the tree the
        # installed project-meta lives in (marketplace checkout / cache).
        tree_candidates = [root, pm_dir.parent.parent]
        ran = False
        for tree in tree_candidates:
            try:
                result = subprocess.run(
                    ["python3", str(script), str(tree), "--statement", statement],
                    capture_output=True, text=True, timeout=30,
                )
            except Exception as exc:
                collision_notes.append(f"[cross_skill_redundancy] warning: {exc}")
                ran = True
                break
            if result.returncode == 0:
                if result.stdout.strip():
                    collision_notes.append(f"[cross_skill_redundancy @ {tree}] {result.stdout.strip()}")
                ran = True
                break
            if result.returncode == 2:
                continue  # path/refs not resolvable for this tree — try the next
            # Any other returncode is a real failure (crash/traceback) — surface
            # it loudly instead of silently emitting a draft with no check
            # (E0/DASH-072: returncodes checked, stderr surfaced).
            print(f"WARN promote-draft: coverage check FAILED (rc={result.returncode}) @ {tree}:\n"
                  f"{result.stderr.strip()}", file=sys.stderr)
            collision_notes.append(f"[cross_skill_redundancy @ {tree}] CHECK FAILED rc={result.returncode} — see stderr")
            ran = True
            break
        if not ran:
            print(f"WARN promote-draft: coverage check found no skill tree under "
                  f"{[str(t) for t in tree_candidates]}: {result.stderr.strip()}", file=sys.stderr)

    print(f"promote-draft {args.id}:")
    print(f"  statement: {statement}")
    print("  evidence:")
    for line in _format_evidence(row):
        print(line)
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
    p_add.add_argument("--scope-paths", dest="scope_paths", default=None,
                       help="Comma-separated repo-relative globs the lesson's guidance concerns.")
    p_add.add_argument("--gate-id", dest="gate_id", default=None,
                       choices=sorted(GATE_IDS),
                       help="verify-before-stop.sh leg this lesson corresponds to.")
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
    p_status.add_argument("--scope-paths", dest="scope_paths", default=None,
                          help="Set scope_paths (comma-separated globs). Resets evidence binding.")
    p_status.add_argument("--note", default=None, help="Note to append (required for demotions).")
    p_status.add_argument("--force", action="store_true",
                          help="Bypass the promoted/enforced evidence gate (requires --note).")
    p_status.set_defaults(func=cmd_status)

    # outcome
    p_outcome = sub.add_parser("outcome", help="Record helpful/harmful feedback (manual; --note required).")
    p_outcome.add_argument("id", help="Lesson id.")
    group = p_outcome.add_mutually_exclusive_group(required=True)
    group.add_argument("--helpful", action="store_true")
    group.add_argument("--harmful", action="store_true")
    p_outcome.add_argument("--note", default=None,
                           help="Evidence citation (turn/gate/file). Required.")
    p_outcome.set_defaults(func=cmd_outcome)

    # observe
    p_obs = sub.add_parser("observe",
                           help="Stop-hook heuristic evidence leg (advisory; always exits 0).")
    p_obs.add_argument("--model-tier", dest="model_tier",
                       choices=sorted(set(TIER_ORDER) | set(TIER_ALIASES)), default=None,
                       help="Current session model tier; filters applies_below lessons.")
    p_obs.add_argument("--changed-files-from", dest="changed_files_from", default=None,
                       metavar="FILE",
                       help="Read the turn's changed files from FILE (one per line) instead of running git status.")
    p_obs.set_defaults(func=cmd_observe)

    # validate
    p_val = sub.add_parser("validate", help="Hard gate: check structure + path resolution.")
    p_val.set_defaults(func=cmd_validate)

    # watermark
    p_wm = sub.add_parser("watermark", help="Advisory visibility (always exits 0).")
    p_wm.set_defaults(func=cmd_watermark)

    # inject
    p_inj = sub.add_parser("inject", help="Print SessionStart reminder block (≤20 lines).")
    p_inj.add_argument("--model-tier", dest="model_tier",
                       choices=sorted(set(TIER_ORDER) | set(TIER_ALIASES)), default=None,
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

    # auto-demote
    p_ad = sub.add_parser("auto-demote",
                          help="Draft (or --apply) one-rung demotions on harmful evidence / stale target.")
    p_ad.add_argument("--apply", action="store_true",
                      help="Apply the demotions (default: print drafts with evidence).")
    p_ad.set_defaults(func=cmd_auto_demote)

    # promote-draft
    p_pd = sub.add_parser("promote-draft",
                           help="Run statement-coverage check + emit board inbox draft for operator approval.")
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

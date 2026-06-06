#!/usr/bin/env python3
"""Project Board store CRUD + static dashboard renderer.

Standard-library only. The repo-local store is:
  docs/backlog/items.jsonl
  docs/backlog/inbox.jsonl
  docs/backlog/roadmap.json
  docs/backlog/.provenance.json
  docs/backlog/.refine-guidance.md
  docs/dashboard.html
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator


KIND_VALUES = {"bug", "feat", "infra", "docs", "chore", "spike"}
MATURITY_VALUES = {"fuzzy", "refined"}
STATUS_VALUES = {"unscheduled", "scheduled", "in_progress", "done"}
DISPOSITION_VALUES = {"active", "deferred", "trimmed", "wontfix"}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today() -> str:
    return dt.date.today().isoformat()


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_template() -> Path:
    return skill_root() / "templates" / "board.dashboard.html"


def store_dir(root: Path) -> Path:
    return root / "docs" / "backlog"


def paths(root: Path) -> dict[str, Path]:
    d = store_dir(root)
    return {
        "dir": d,
        "items": d / "items.jsonl",
        "inbox": d / "inbox.jsonl",
        "roadmap": d / "roadmap.json",
        "provenance": d / ".provenance.json",
        "guidance": d / ".refine-guidance.md",
        "dashboard": root / "docs" / "dashboard.html",
        "lock": d / ".board.lock",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{lineno}: each JSONL row must be an object")
        rows.append(row)
    return rows


def jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    write_text_atomic(path, jsonl_text(rows))


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: root must be a JSON object")
    return data


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    write_text_atomic(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)


STALE_LOCK_SECONDS = 3600  # a lock older than this is treated as left by a crashed run


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # exists (e.g. owned by another user) or a platform without signals
    return True


def _lock_is_stale(lock: Path) -> bool:
    """A lock is stale if its recorded pid is no longer running, or the file is
    older than STALE_LOCK_SECONDS — both signatures of a crashed mutation that
    would otherwise block every future write until the lock is removed by hand."""
    try:
        text = lock.read_text(encoding="utf-8")
    except FileNotFoundError:
        return True
    m = re.search(r"pid=(\d+)", text)
    if m and not _pid_alive(int(m.group(1))):
        return True
    try:
        age = dt.datetime.now(dt.UTC).timestamp() - lock.stat().st_mtime
    except FileNotFoundError:
        return True
    return age > STALE_LOCK_SECONDS


@contextlib.contextmanager
def board_lock(root: Path) -> Iterator[None]:
    p = paths(root)
    p["dir"].mkdir(parents=True, exist_ok=True)
    lock = p["lock"]
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        # Break a lock left behind by a crashed run (dead pid / stale mtime); a live
        # lock still wins. The second O_EXCL closes the unlink->create race safely.
        if not _lock_is_stale(lock):
            raise SystemExit(f"board store is locked: {lock}") from exc
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc2:
            raise SystemExit(f"board store is locked: {lock}") from exc2
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()} utc={utc_now()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def initial_roadmap() -> dict[str, Any]:
    return {"_meta": {"rev": 1, "created_at": utc_now(), "updated_at": utc_now()}, "milestones": []}


def initial_provenance() -> dict[str, Any]:
    return {
        "artifact_name": "project-board-store",
        "source_reference": "docs/backlog/project-board-system.md",
        "owner": "shared-user-facing",
        "review_policy": "groom + version-assign during /project-meta roadmap (DASH-08)",
        "last_reviewed": today(),
    }


def init_store(root: Path) -> None:
    p = paths(root)
    p["dir"].mkdir(parents=True, exist_ok=True)
    if not p["items"].exists():
        write_jsonl_atomic(p["items"], [])
    if not p["inbox"].exists():
        write_jsonl_atomic(p["inbox"], [])
    if not p["roadmap"].exists():
        roadmap = initial_roadmap()
        roadmap["_meta"]["items_sha256"] = file_hash(p["items"])
        write_json_atomic(p["roadmap"], roadmap)
    if not p["provenance"].exists():
        write_json_atomic(p["provenance"], initial_provenance())
    if not p["guidance"].exists():
        write_text_atomic(
            p["guidance"],
            "# Project Board Refinement Guidance\n\n"
            "Distilled guidance from DASH-08 co-review sessions. Keep this small and actionable.\n",
        )


def normalize_labels(values: list[str] | None) -> list[str]:
    labels: list[str] = []
    for value in values or []:
        for part in value.split(","):
            label = part.strip()
            if label and label not in labels:
                labels.append(label)
    return labels


def next_id(rows: list[dict[str, Any]], prefix: str | None = None) -> str:
    """Allocate the next sequential id. The prefix defaults to the dominant prefix
    already in the store (so a store seeded as DASH-* keeps producing DASH-*),
    falling back to 'PB' for an empty store."""
    pat = re.compile(r"^([A-Za-z]+)-(\d+)$")
    counts: dict[str, int] = {}
    maxima: dict[str, int] = {}
    for row in rows:
        m = pat.match(str(row.get("id", "")))
        if m:
            pfx, num = m.group(1), int(m.group(2))
            counts[pfx] = counts.get(pfx, 0) + 1
            maxima[pfx] = max(maxima.get(pfx, 0), num)
    if prefix is None:
        prefix = max(counts, key=lambda k: (counts[k], maxima[k])) if counts else "PB"
    return f"{prefix}-{maxima.get(prefix, 0) + 1:03d}"


def find_item(rows: list[dict[str, Any]], item_id: str) -> dict[str, Any]:
    for row in rows:
        if row.get("id") == item_id:
            return row
    raise SystemExit(f"no item with id {item_id!r}")


def validate_item(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = (
        "id",
        "kind",
        "title",
        "body",
        "acceptance_shape",
        "rough_size",
        "labels",
        "links",
        "linear_id",
        "maturity",
        "status",
        "disposition",
        "version",
        "source",
        "created_at",
        "updated_at",
    )
    for key in required:
        if key not in row:
            errors.append(f"{row.get('id', '<missing id>')}: missing {key}")
    if row.get("kind") not in KIND_VALUES:
        errors.append(f"{row.get('id')}: bad kind {row.get('kind')!r}")
    if row.get("maturity") not in MATURITY_VALUES:
        errors.append(f"{row.get('id')}: bad maturity {row.get('maturity')!r}")
    if row.get("status") not in STATUS_VALUES:
        errors.append(f"{row.get('id')}: bad status {row.get('status')!r}")
    if row.get("disposition") not in DISPOSITION_VALUES:
        errors.append(f"{row.get('id')}: bad disposition {row.get('disposition')!r}")
    if not (row.get("version") is None or isinstance(row.get("version"), str)):
        errors.append(f"{row.get('id')}: version must be null or string")
    if not isinstance(row.get("labels", []), list):
        errors.append(f"{row.get('id')}: labels must be a list")
    if not isinstance(row.get("links", []), list):
        errors.append(f"{row.get('id')}: links must be a list")
    return errors


def validate_store(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    p = paths(root)
    rows = read_jsonl(p["items"])
    roadmap = read_json(p["roadmap"], initial_roadmap())
    errors: list[str] = []
    ids: set[str] = set()
    for row in rows:
        item_id = str(row.get("id", ""))
        if item_id in ids:
            errors.append(f"duplicate id: {item_id}")
        ids.add(item_id)
        errors.extend(validate_item(row))
    for milestone in roadmap.get("milestones", []):
        for item_id in milestone.get("items", []):
            if item_id not in ids:
                errors.append(f"roadmap references missing item: {item_id}")
    meta = roadmap.get("_meta", {})
    expected_hash = meta.get("items_sha256")
    actual_hash = file_hash(p["items"])
    if not expected_hash:
        errors.append("roadmap _meta.items_sha256 is missing")
    elif expected_hash != actual_hash:
        errors.append(f"roadmap _meta.items_sha256 is stale: {expected_hash} != {actual_hash}")
    return rows, roadmap, errors


def write_items_and_roadmap_atomic(root: Path, rows: list[dict[str, Any]], roadmap: dict[str, Any], before_hash: str) -> None:
    p = paths(root)
    meta = roadmap.setdefault("_meta", {})
    expected_hash = meta.get("items_sha256")
    if expected_hash and expected_hash != before_hash:
        raise SystemExit(f"stale board snapshot: roadmap items_sha256 {expected_hash} != current {before_hash}")
    items_text = jsonl_text(rows)
    meta["rev"] = int(meta.get("rev", 0)) + 1
    meta["updated_at"] = utc_now()
    meta["items_sha256"] = text_hash(items_text)
    write_text_atomic(p["items"], items_text)
    write_json_atomic(p["roadmap"], roadmap)


def mutate_items(root: Path, mutate: Any, *, template: Path) -> None:
    init_store(root)
    with board_lock(root):
        p = paths(root)
        before = file_hash(p["items"])
        rows = read_jsonl(p["items"])
        roadmap = read_json(p["roadmap"], initial_roadmap())
        mutate(rows)
        errors = []
        ids: set[str] = set()
        for row in rows:
            if row.get("id") in ids:
                errors.append(f"duplicate id: {row.get('id')}")
            ids.add(str(row.get("id")))
            errors.extend(validate_item(row))
        if errors:
            raise SystemExit("store validation failed:\n  - " + "\n  - ".join(errors))
        write_items_and_roadmap_atomic(root, rows, roadmap, before)
    render_dashboard(root, template)


def cmd_init(args: argparse.Namespace) -> int:
    init_store(args.root)
    render_dashboard(args.root, args.template)
    print(f"initialized {store_dir(args.root)}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    def mutate(rows: list[dict[str, Any]]) -> None:
        now = utc_now()
        item_id = args.id or next_id(rows)
        if any(row.get("id") == item_id for row in rows):
            raise SystemExit(f"duplicate id: {item_id}")
        rows.append(
            {
                "id": item_id,
                "kind": args.kind,
                "title": args.title,
                "body": args.body or "",
                "acceptance_shape": args.acceptance_shape or "",
                "rough_size": args.rough_size or "",
                "labels": normalize_labels(args.label),
                "links": normalize_labels(args.link),
                "linear_id": args.linear_id,
                "maturity": args.maturity,
                "status": args.status,
                "disposition": args.disposition,
                "version": args.version,
                "source": args.source or "manual",
                "created_at": now,
                "updated_at": now,
            }
        )

    mutate_items(args.root, mutate, template=args.template)
    print(f"added {args.id or '<auto>'}: {args.title}")
    return 0


def cmd_refine(args: argparse.Namespace) -> int:
    def mutate(rows: list[dict[str, Any]]) -> None:
        row = find_item(rows, args.id)
        row["maturity"] = "refined"
        if args.acceptance_shape is not None:
            row["acceptance_shape"] = args.acceptance_shape
        if args.rough_size is not None:
            row["rough_size"] = args.rough_size
        if args.body is not None:
            row["body"] = args.body
        row["updated_at"] = utc_now()

    mutate_items(args.root, mutate, template=args.template)
    print(f"refined {args.id}")
    return 0


def cmd_move(args: argparse.Namespace) -> int:
    def mutate(rows: list[dict[str, Any]]) -> None:
        row = find_item(rows, args.id)
        row["status"] = args.status
        if args.version is not None:
            row["version"] = args.version
        row["updated_at"] = utc_now()

    mutate_items(args.root, mutate, template=args.template)
    print(f"moved {args.id} -> {args.status}")
    return 0


def cmd_disposition(args: argparse.Namespace) -> int:
    def mutate(rows: list[dict[str, Any]]) -> None:
        row = find_item(rows, args.id)
        row["disposition"] = args.disposition
        row["updated_at"] = utc_now()

    mutate_items(args.root, mutate, template=args.template)
    print(f"{args.id} disposition -> {args.disposition}")
    return 0


def cmd_edit(args: argparse.Namespace) -> int:
    def mutate(rows: list[dict[str, Any]]) -> None:
        row = find_item(rows, args.id)
        for key in ("title", "body", "acceptance_shape", "rough_size", "kind", "maturity", "status", "disposition", "version", "linear_id"):
            val = getattr(args, key)
            if val is not None:
                row[key] = val
        if args.label is not None:
            row["labels"] = normalize_labels(args.label)
        if args.link is not None:
            row["links"] = normalize_labels(args.link)
        row["updated_at"] = utc_now()

    mutate_items(args.root, mutate, template=args.template)
    print(f"edited {args.id}")
    return 0


def row_matches(row: dict[str, Any], args: argparse.Namespace) -> bool:
    for key in ("kind", "maturity", "status", "disposition", "version"):
        val = getattr(args, key)
        if val is not None and row.get(key) != val:
            return False
    return True


def cmd_list(args: argparse.Namespace) -> int:
    rows = [row for row in read_jsonl(paths(args.root)["items"]) if row_matches(row, args)]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not rows:
        print("no items")
        return 0
    widths = {"id": 8, "kind": 6, "maturity": 8, "status": 11, "version": 8}
    for row in rows:
        print(
            f"{str(row.get('id','')):<{widths['id']}} "
            f"{str(row.get('kind','')):<{widths['kind']}} "
            f"{str(row.get('maturity','')):<{widths['maturity']}} "
            f"{str(row.get('status','')):<{widths['status']}} "
            f"{str(row.get('version','') or '-'):<{widths['version']}} "
            f"{row.get('title','')}"
        )
    return 0


def dashboard_data(root: Path) -> dict[str, Any]:
    p = paths(root)
    rows, roadmap, errors = validate_store(root)
    if errors:
        raise SystemExit("store validation failed:\n  - " + "\n  - ".join(errors))
    counts = {
        "items": len(rows),
        "active": sum(1 for row in rows if row.get("disposition") == "active"),
        "refined": sum(1 for row in rows if row.get("maturity") == "refined"),
        "done": sum(1 for row in rows if row.get("status") == "done"),
    }
    return {
        "generated_at": utc_now(),
        "source_reference": "docs/backlog/project-board-system.md",
        "store": {
            "items": str(p["items"].relative_to(root)),
            "roadmap": str(p["roadmap"].relative_to(root)),
            "inbox": str(p["inbox"].relative_to(root)),
            "dashboard": str(p["dashboard"].relative_to(root)),
        },
        "counts": counts,
        "items": rows,
        "roadmap": roadmap,
    }


def render_dashboard(root: Path, template: Path) -> None:
    init_store(root)
    p = paths(root)
    if not template.exists():
        raise SystemExit(f"dashboard template not found: {template}")
    data = dashboard_data(root)
    # Embedded inside a <script> block. json.dumps does NOT escape '<', so a value
    # containing '</script>' (or '<!--') would close the tag early — corrupting the
    # dashboard and enabling stored XSS once arbitrary content (DASH-02/DASH-25) is fed
    # in. Escape the three HTML-significant chars to \uXXXX: still valid JSON (they only
    # occur inside string values), and no '</script>' can survive.
    payload = (
        json.dumps(data, ensure_ascii=False, sort_keys=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    template_text = template.read_text(encoding="utf-8")
    if "__BOARD_DATA_JSON__" not in template_text:
        raise SystemExit(f"dashboard template missing __BOARD_DATA_JSON__ marker: {template}")
    rendered = template_text.replace("__BOARD_DATA_JSON__", payload)
    write_text_atomic(p["dashboard"], rendered)
    print(f"rendered {p['dashboard']}")


def cmd_render(args: argparse.Namespace) -> int:
    render_dashboard(args.root, args.template)
    return 0


def cmd_tx(args: argparse.Namespace) -> int:
    p = paths(args.root)
    if not p["items"].exists() and not p["roadmap"].exists():
        print(f"board tx: no store at {store_dir(args.root)}")
        return 0
    rows, roadmap, errors = validate_store(args.root)
    if errors:
        print("board tx: FAIL", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    rev = roadmap.get("_meta", {}).get("rev", "?")
    print(f"board tx: PASS ({len(rows)} items, roadmap rev {rev})")
    return 0


def cmd_inbox_add(args: argparse.Namespace) -> int:
    init_store(args.root)
    p = paths(args.root)
    now = utc_now()
    row = {
        "id": args.id or f"INBOX-{now}",
        "kind": args.kind,
        "title": args.title,
        "body": args.body or "",
        "labels": normalize_labels(args.label),
        "maturity": "fuzzy",
        "status": "unscheduled",
        "disposition": "active",
        "version": None,
        "source": args.source or "capture",
        "created_at": now,
        "updated_at": now,
    }
    with p["inbox"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"captured {row['id']}: {row['title']}")
    return 0


def add_common(parser: argparse.ArgumentParser, *, subcommand: bool = True) -> None:
    default: Any = argparse.SUPPRESS if subcommand else Path.cwd()
    template_default: Any = argparse.SUPPRESS if subcommand else default_template()
    parser.add_argument("--root", type=Path, default=default, help="target repository root")
    parser.add_argument("--template", type=Path, default=template_default, help="dashboard template")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project Board CRUD + render")
    add_common(parser, subcommand=False)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    add_common(p_init)
    p_init.set_defaults(func=cmd_init)

    p_add = sub.add_parser("add")
    add_common(p_add)
    p_add.add_argument("--id")
    p_add.add_argument("--kind", default="feat", choices=sorted(KIND_VALUES))
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--body")
    p_add.add_argument("--acceptance-shape")
    p_add.add_argument("--rough-size")
    p_add.add_argument("--label", action="append")
    p_add.add_argument("--link", action="append")
    p_add.add_argument("--linear-id")
    p_add.add_argument("--maturity", default="fuzzy", choices=sorted(MATURITY_VALUES))
    p_add.add_argument("--status", default="unscheduled", choices=sorted(STATUS_VALUES))
    p_add.add_argument("--disposition", default="active", choices=sorted(DISPOSITION_VALUES))
    p_add.add_argument("--version")
    p_add.add_argument("--source")
    p_add.set_defaults(func=cmd_add)

    p_refine = sub.add_parser("refine")
    add_common(p_refine)
    p_refine.add_argument("id")
    p_refine.add_argument("--acceptance-shape")
    p_refine.add_argument("--rough-size")
    p_refine.add_argument("--body")
    p_refine.set_defaults(func=cmd_refine)

    p_move = sub.add_parser("move")
    add_common(p_move)
    p_move.add_argument("id")
    p_move.add_argument("status", choices=sorted(STATUS_VALUES))
    p_move.add_argument("--version")
    p_move.set_defaults(func=cmd_move)

    for name in ("defer", "trim", "wontfix"):
        p_disp = sub.add_parser(name)
        add_common(p_disp)
        p_disp.add_argument("id")
        disposition = "trimmed" if name == "trim" else name
        p_disp.set_defaults(func=cmd_disposition, disposition=disposition)

    p_edit = sub.add_parser("edit")
    add_common(p_edit)
    p_edit.add_argument("id")
    for key in ("title", "body", "acceptance-shape", "rough-size", "kind", "maturity", "status", "disposition", "version", "linear-id"):
        p_edit.add_argument(f"--{key}")
    p_edit.add_argument("--label", action="append")
    p_edit.add_argument("--link", action="append")
    p_edit.set_defaults(func=cmd_edit)

    p_list = sub.add_parser("list")
    add_common(p_list)
    for key in ("kind", "maturity", "status", "disposition", "version"):
        p_list.add_argument(f"--{key}")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_render = sub.add_parser("render")
    add_common(p_render)
    p_render.set_defaults(func=cmd_render)

    p_tx = sub.add_parser("tx")
    add_common(p_tx)
    p_tx.set_defaults(func=cmd_tx)

    p_inbox = sub.add_parser("inbox-add")
    add_common(p_inbox)
    p_inbox.add_argument("--id")
    p_inbox.add_argument("--kind", default="feat", choices=sorted(KIND_VALUES))
    p_inbox.add_argument("--title", required=True)
    p_inbox.add_argument("--body")
    p_inbox.add_argument("--label", action="append")
    p_inbox.add_argument("--source")
    p_inbox.set_defaults(func=cmd_inbox_add)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = args.root.resolve()
    args.template = args.template.resolve()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""debug_session.py — phase-gated, rollbackable, looping debug-pipeline tracker.

Makes the meta-debug pipeline (references/debug-pipeline.md) a *recorded* activity
instead of a vibe: it tracks phase gates, hypotheses (with confirm/refute),
top-k candidate fixes (with critic scores), checkpoints/rollback, a bounded loop
counter, and — on a successful close — writes a lesson into this skill's
state/lessons.jsonl (the fast journal; promote durable lessons into project-meta
canonical memory per its CRUD rules).

The script does NOT dispatch agents or run sandboxes — that's the runtime's job
(Claude Code Workflow/Agent worktrees, Codex subagents, or `openclaw sandbox`),
coordinated via project-meta's multi-agent protocol. It enforces the *discipline*:
you cannot pass a gate while an earlier gate is failed (without --force + reason),
and close --fixed requires a confirmed root cause.

Stdlib only. Sessions live under state/debug-sessions/<id>.json.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
STATE_DIR = SKILL_ROOT / "state"
SESS_DIR = STATE_DIR / "debug-sessions"
LESSONS_FILE = STATE_DIR / "lessons.jsonl"

PHASES = ["triage", "context", "reproduce", "tests", "hypotheses",
          "solutions", "candidates", "validate", "prod", "close"]
GATE_PHASES = ["reproduce", "tests", "hypotheses", "validate", "prod"]
MAX_LOOP = 3
ICON = {"pass": "🟢", "fail": "🔴", "skip": "⚪", "open": "·"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sid() -> str:
    return "dbg-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def spath(i: str) -> Path:
    return SESS_DIR / f"{i}.json"


def load(i: str) -> dict:
    p = spath(i)
    if not p.exists():
        raise SystemExit(f"no such session: {i} (try: debug_session.py list)")
    return json.loads(p.read_text(encoding="utf-8"))


def save(s: dict) -> None:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    s["updated"] = now()
    spath(s["id"]).write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def log(s: dict, msg: str) -> None:
    s.setdefault("events", []).append({"ts": now(), "msg": msg})


def append_lesson(title: str, bug: str, cause: str, fix: str, tags: list[str]) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now(), "title": title, "bug": bug, "root_cause": cause,
             "fix": fix, "tags": tags, "_source": "debug_session"}
    with LESSONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return sum(1 for _ in LESSONS_FILE.open(encoding="utf-8"))


def failed_prior_gates(s: dict, phase: str) -> list[str]:
    """Gate phases at-or-before `phase` that are not yet pass."""
    if phase not in PHASES:
        return []
    upto = PHASES.index(phase)
    bad = []
    for g in GATE_PHASES:
        if PHASES.index(g) < upto:
            st = s["phases"].get(g, {}).get("status")
            if st != "pass":
                bad.append(f"{g}={st or 'open'}")
    return bad


# --------------------------------------------------------------------------- #
def cmd_start(a):
    s = {
        "id": sid(), "title": a.title, "severity": a.severity,
        "track": a.track, "status": "open", "created": now(), "updated": now(),
        "current_phase": "triage", "loop_count": 0,
        "phases": {}, "hypotheses": [], "candidates": [], "checkpoints": [],
        "events": [],
    }
    log(s, f"session started (severity={a.severity}, track={a.track})")
    save(s)
    print(f"started {s['id']}  — {a.title}")
    print("next: collect a bounded case file (clean agent), then `phase <id> context --status pass`.")
    print("see references/debug-pipeline.md for the gated flow.")


def cmd_phase(a):
    s = load(a.id)
    if a.name not in PHASES:
        raise SystemExit(f"phase must be one of: {', '.join(PHASES)}")
    if a.status == "pass":
        bad = failed_prior_gates(s, a.name)
        if bad and not a.force:
            raise SystemExit("refusing to pass '" + a.name + "': prior gate(s) not green: "
                             + ", ".join(bad) + "  (fix them, or --force with --note)")
    s["phases"][a.name] = {"status": a.status, "note": a.note or "",
                           "artifact": a.artifact or "", "ts": now(),
                           "forced": bool(a.force)}
    s["current_phase"] = a.name
    log(s, f"phase {a.name} -> {a.status}" + (f" (forced: {a.note})" if a.force else ""))
    save(s)
    print(f"{ICON.get(a.status,'?')} {a.name} = {a.status}")
    if a.status == "fail" and a.name in GATE_PHASES:
        print("gate failed → loop back with new evidence (`loop`) or rollback (`rollback`).")


def cmd_hypothesis(a):
    s = load(a.id)
    if a.text:  # add
        hid = f"H{len(s['hypotheses'])+1}"
        s["hypotheses"].append({"id": hid, "text": a.text, "prior": a.prior,
                                "probe": a.probe or "", "status": "open",
                                "evidence": "", "ts": now()})
        log(s, f"hypothesis {hid} added (prior={a.prior})")
        save(s)
        print(f"added {hid}: {a.text}")
        return
    if a.confirm or a.refute:
        target = a.confirm or a.refute
        st = "confirmed" if a.confirm else "refuted"
        for h in s["hypotheses"]:
            if h["id"] == target:
                h["status"] = st
                h["evidence"] = a.evidence or ""
                log(s, f"hypothesis {target} -> {st}: {a.evidence or ''}")
                save(s)
                print(f"{target} -> {st}")
                if st == "confirmed":
                    print("→ confirmed root cause; you may pass the `hypotheses` gate and design solutions.")
                return
        raise SystemExit(f"no hypothesis {target}")
    # list
    for h in s["hypotheses"]:
        mark = {"confirmed": "✅", "refuted": "❌", "open": "·"}[h["status"]]
        print(f"{mark} {h['id']} [{h['prior']}] {h['text']}  | probe: {h['probe']}  | {h['evidence']}")


def cmd_candidate(a):
    s = load(a.id)
    scores = {}
    if a.scores:
        for kv in a.scores.split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                try:
                    scores[k.strip()] = float(v)
                except ValueError:
                    scores[k.strip()] = v.strip()
    s["candidates"].append({"label": a.label, "sandbox": a.sandbox or "",
                            "passed_red": a.passed_red, "scores": scores,
                            "status": a.status, "ts": now()})
    log(s, f"candidate {a.label} ({a.status}) scores={scores}")
    save(s)
    avg = round(sum(v for v in scores.values() if isinstance(v, (int, float))) / len(scores), 2) if scores else None
    print(f"candidate {a.label}: {a.status} | passed_red={a.passed_red} | scores={scores} | avg={avg}")


def cmd_checkpoint(a):
    s = load(a.id)
    s["checkpoints"].append({"label": a.label, "phase": s["current_phase"],
                             "ref": a.ref or "", "ts": now()})
    log(s, f"checkpoint '{a.label}' @ {s['current_phase']} (ref={a.ref or '-'})")
    save(s)
    print(f"checkpoint '{a.label}' @ phase {s['current_phase']}" + (f" ref={a.ref}" if a.ref else ""))


def cmd_rollback(a):
    s = load(a.id)
    if not s["checkpoints"]:
        raise SystemExit("no checkpoints to roll back to")
    cp = None
    if a.to:
        cp = next((c for c in reversed(s["checkpoints"]) if c["label"] == a.to), None)
        if not cp:
            raise SystemExit(f"no checkpoint '{a.to}'")
    else:
        cp = s["checkpoints"][-1]
    s["current_phase"] = cp["phase"]
    log(s, f"rolled back to checkpoint '{cp['label']}' (phase {cp['phase']}, ref={cp['ref']})")
    save(s)
    print(f"↩ rolled back to '{cp['label']}' @ phase {cp['phase']}"
          + (f" — restore ref {cp['ref']}" if cp['ref'] else ""))


def cmd_loop(a):
    s = load(a.id)
    if a.to not in PHASES:
        raise SystemExit(f"--to must be one of: {', '.join(PHASES)}")
    s["loop_count"] += 1
    s["current_phase"] = a.to
    log(s, f"loop #{s['loop_count']} -> {a.to}: {a.reason}")
    save(s)
    print(f"🔁 loop #{s['loop_count']} → {a.to}: {a.reason}")
    if s["loop_count"] >= MAX_LOOP:
        print(f"⚠️ loop budget reached ({MAX_LOOP}). If the next pass fails, "
              f"escalate: `close --outcome escalated`.")


def cmd_close(a):
    s = load(a.id)
    if a.outcome == "fixed":
        confirmed = [h for h in s["hypotheses"] if h["status"] == "confirmed"]
        if not (a.root_cause or confirmed) and not a.force:
            raise SystemExit("close --fixed needs a confirmed root cause "
                             "(--root-cause '...' or a confirmed hypothesis), or --force.")
        cause = a.root_cause or (confirmed[0]["text"] if confirmed else "(unspecified)")
        refuted = [h["text"] for h in s["hypotheses"] if h["status"] == "refuted"]
        fix = a.fix or "(see session)"
        if refuted:
            fix += " | refuted: " + "; ".join(refuted[:4])
        n = append_lesson(s["title"], a.bug or s["title"], cause, fix,
                          (a.tags or "").split(",") if a.tags else ["debug-session"])
        s["status"] = "fixed"
        s["phases"]["close"] = {"status": "pass", "note": "lesson recorded", "ts": now()}
        log(s, f"closed FIXED; lesson recorded (#{n})")
        save(s)
        print(f"✅ closed {s['id']} FIXED — lesson recorded ({n} total in lessons.jsonl)")
    else:
        s["status"] = a.outcome
        log(s, f"closed {a.outcome}: {a.reason or ''}")
        save(s)
        print(f"closed {s['id']} {a.outcome.upper()}" + (f" — {a.reason}" if a.reason else ""))
        if a.outcome == "escalated":
            print("hand a human the case file (phase 'context' artifact), tried candidates, and refuted hypotheses.")


def render(s: dict) -> str:
    out = [f"🐞 {s['id']} — {s['title']}",
           f"   status={s['status']} severity={s['severity']} track={s['track']} "
           f"loop={s['loop_count']}/{MAX_LOOP} current={s['current_phase']}", "   phases:"]
    for p in PHASES:
        st = s["phases"].get(p, {}).get("status", "open")
        note = s["phases"].get(p, {}).get("note", "")
        gate = " (gate)" if p in GATE_PHASES else ""
        out.append(f"     {ICON.get(st,'?')} {p}{gate}" + (f" — {note}" if note else ""))
    if s["hypotheses"]:
        out.append("   hypotheses:")
        for h in s["hypotheses"]:
            mark = {"confirmed": "✅", "refuted": "❌", "open": "·"}[h["status"]]
            out.append(f"     {mark} {h['id']} [{h['prior']}] {h['text']}")
    if s["candidates"]:
        out.append("   candidates:")
        for c in s["candidates"]:
            avg = ([v for v in c["scores"].values() if isinstance(v, (int, float))])
            avg = round(sum(avg) / len(avg), 2) if avg else "-"
            out.append(f"     · {c['label']} [{c['status']}] red={c['passed_red']} avg={avg}")
    if s["checkpoints"]:
        out.append("   checkpoints: " + ", ".join(f"{c['label']}@{c['phase']}" for c in s["checkpoints"]))
    return "\n".join(out)


def cmd_show(a):
    print(render(load(a.id)))


def cmd_list(a):
    if not SESS_DIR.exists():
        print("no debug sessions yet")
        return
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(SESS_DIR.glob("dbg-*.json"))]
    for s in rows:
        print(f"{s['id']}  {ICON.get(s['phases'].get(s['current_phase'],{}).get('status','open'),'·')} "
              f"{s['status']:9} {s['current_phase']:10} {s['title']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase-gated debug-pipeline session tracker "
                                             "(see references/debug-pipeline.md).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("start", help="start a new debug session")
    p.add_argument("--title", required=True)
    p.add_argument("--severity", default="sev3", choices=["sev1", "sev2", "sev3", "sev4"])
    p.add_argument("--track", default="deterministic", choices=["deterministic", "heisenbug"])
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("phase", help="record a phase gate result")
    p.add_argument("id"); p.add_argument("name")
    p.add_argument("--status", required=True, choices=["pass", "fail", "skip"])
    p.add_argument("--note"); p.add_argument("--artifact"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_phase)

    p = sub.add_parser("hypothesis", help="add/confirm/refute/list hypotheses")
    p.add_argument("id"); p.add_argument("--text")
    p.add_argument("--prior", default="med", choices=["high", "med", "low"])
    p.add_argument("--probe"); p.add_argument("--confirm"); p.add_argument("--refute"); p.add_argument("--evidence")
    p.set_defaults(fn=cmd_hypothesis)

    p = sub.add_parser("candidate", help="record a top-k candidate fix + critic scores")
    p.add_argument("id"); p.add_argument("--label", required=True)
    p.add_argument("--sandbox"); p.add_argument("--passed-red", dest="passed_red",
                                                choices=["yes", "no", "unknown"], default="unknown")
    p.add_argument("--scores", help='e.g. "correctness=9,elegance=7,latency=8,risk=6"')
    p.add_argument("--status", default="survived", choices=["survived", "dropped", "winner"])
    p.set_defaults(fn=cmd_candidate)

    p = sub.add_parser("checkpoint", help="record a rollback point")
    p.add_argument("id"); p.add_argument("--label", required=True); p.add_argument("--ref")
    p.set_defaults(fn=cmd_checkpoint)

    p = sub.add_parser("rollback", help="roll back to a checkpoint")
    p.add_argument("id"); p.add_argument("--to")
    p.set_defaults(fn=cmd_rollback)

    p = sub.add_parser("loop", help="loop back to an earlier phase with new evidence")
    p.add_argument("id"); p.add_argument("--to", required=True); p.add_argument("--reason", required=True)
    p.set_defaults(fn=cmd_loop)

    p = sub.add_parser("close", help="close the session (fixed -> writes a lesson)")
    p.add_argument("id")
    p.add_argument("--outcome", required=True, choices=["fixed", "escalated", "abandoned"])
    p.add_argument("--root-cause", dest="root_cause"); p.add_argument("--fix")
    p.add_argument("--bug"); p.add_argument("--tags"); p.add_argument("--reason"); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_close)

    p = sub.add_parser("show", help="show a session"); p.add_argument("id"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("list", help="list sessions"); p.set_defaults(fn=cmd_list)

    a = ap.parse_args(argv)
    a.fn(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""openclaw-devops engine — portable OpenClaw maintenance orchestrator.

Runtime-agnostic (Codex / Claude Code / OpenClaw): the maintenance *target* is
always the OpenClaw install on the host; this script only needs Python stdlib +
the host's `openclaw`, `systemctl`, and `npm`.

Sub-commands:
  sanity    Health probe (services, gateway health, config validity, version
            alignment across the npm copies, cron scheduler, channels, plugins).
  repair    Bounded, idempotent self-repair of issues sanity found.
  update    Transactional auto-update across all npm copies (snapshot first).
  verify    Post-update integrity gate (validate + health + smoke).
  rollback  Restore the previous version + config snapshot.
  cycle     Orchestrate sanity -> repair -> update -> verify -> rollback-on-fail,
            with a run lock and an append-only history. This is the cron entry.

Design invariants (see references/runbook.md):
  * Update is transactional: snapshot -> update -> verify -> auto-rollback on fail.
  * All npm copies are kept version-aligned (skew crash-loops the gateway).
  * Repair only takes bounded, reversible actions; nothing destructive.
  * --dry-run plans without mutating. cycle defaults to ACTING (it's a cron).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
DEFAULT_CONFIG = SKILL_ROOT / "config.json"
STATE_DIR = SKILL_ROOT / "state"
LOCK_FILE = STATE_DIR / "devops.lock"
STATE_FILE = STATE_DIR / "state.json"
HISTORY_FILE = STATE_DIR / "history.jsonl"
LESSONS_FILE = STATE_DIR / "lessons.jsonl"
BUGS_FILE = STATE_DIR / "bugs.json"
BUGS_LOCK = STATE_DIR / "bugs.lock"

OK, WARN, FAIL = "ok", "warn", "fail"
BUG_STATUSES = ["open", "triaged", "in-progress", "fixed", "wontfix", "duplicate"]
BUG_OPEN = {"open", "triaged", "in-progress"}


# --------------------------------------------------------------------------- #
# small utilities
# --------------------------------------------------------------------------- #
def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def expand(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def detect_runtime() -> str:
    """Best-effort: where is this skill folder mounted?"""
    s = str(SKILL_ROOT)
    if ".openclaw" in s:
        return "openclaw"
    if ".claude" in s:
        return "claude"
    if "codex" in s.lower() or os.environ.get("CODEX_HOME"):
        return "codex"
    return "unknown"


def run(cmd: list[str] | str, timeout: int = 60, shell: bool = False) -> dict:
    """Run a command, capture rc/out/err. Never raises."""
    try:
        p = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        return {"rc": p.returncode, "out": (p.stdout or "").strip(), "err": (p.stderr or "").strip()}
    except subprocess.TimeoutExpired:
        return {"rc": 124, "out": "", "err": f"timeout after {timeout}s"}
    except FileNotFoundError as e:
        return {"rc": 127, "out": "", "err": str(e)}
    except Exception as e:  # noqa
        return {"rc": 1, "out": "", "err": str(e)}


class Config:
    DEFAULTS = {
        "npm_package": "openclaw",
        "channel": "latest",
        "hold_major": True,
        "version_major_index": 0,
        "allow_repair": True,
        "allow_update": True,
        "openclaw_bin": "openclaw",
        "user_prefix": "~/.local",
        "copies": {
            "system": {"package_json": "/usr/lib/node_modules/openclaw/package.json", "needs_sudo": True},
            "user": {"package_json": "~/.local/lib/node_modules/openclaw/package.json", "needs_sudo": False},
        },
        "cli_probe": "~/.local/bin/openclaw",
        "services": [
            "openclaw-gateway.service",
            "openclaw-gateway-chloe.service",
            "openclaw-node.service",
        ],
        "node_service_unit": "~/.config/systemd/user/openclaw-node.service",
        "systemctl_scope": "--user",
        "config_path": "~/.openclaw/openclaw.json",
        "maintenance_hours": None,           # e.g. [2,3,4,5]; None = any time
        "min_free_disk_mb": 500,
        "health_timeout": 40,
    }

    def __init__(self, path: Path | None):
        data = {}
        if path and path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        self.d = {**self.DEFAULTS, **data}

    def __getitem__(self, k):
        return self.d.get(k, self.DEFAULTS.get(k))


# --------------------------------------------------------------------------- #
# probes
# --------------------------------------------------------------------------- #
def _oc(cfg: Config, *args: str, timeout: int = 40) -> dict:
    return run([cfg["openclaw_bin"], *args], timeout=timeout)


def pkg_version(package_json: str) -> str | None:
    p = Path(expand(package_json))
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("version")
    except Exception:
        return None


def npm_latest(cfg: Config) -> str | None:
    r = run(["npm", "view", f"{cfg['npm_package']}", "dist-tags", "--json"], timeout=45)
    if r["rc"] != 0:
        return None
    try:
        return json.loads(r["out"]).get(cfg["channel"])
    except Exception:
        return None


def version_tuple(v: str) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", v or "") if x[:1].isdigit() or x.isdigit())


def is_major_jump(cfg: Config, cur: str, new: str) -> bool:
    idx = cfg["version_major_index"]
    try:
        return version_tuple(new)[idx] > version_tuple(cur)[idx]
    except Exception:
        return False


def check_services(cfg: Config) -> list[dict]:
    out = []
    scope = cfg["systemctl_scope"]
    for svc in cfg["services"]:
        r = run(["systemctl", scope, "is-active", svc])
        active = r["out"] == "active"
        out.append({"name": "service:" + svc, "status": OK if active else FAIL,
                    "detail": r["out"] or r["err"], "_svc": svc, "_active": active})
    return out


def check_versions(cfg: Config) -> dict:
    versions = {}
    for name, c in cfg["copies"].items():
        versions[name] = pkg_version(c["package_json"])
    cli = _oc(cfg, "--version", timeout=20)
    m = re.search(r"(\d{4}\.\d+\.\S+)", cli["out"])
    versions["cli"] = m.group(1) if m else None
    distinct = {v for v in versions.values() if v}
    aligned = len(distinct) <= 1
    return {"versions": versions, "aligned": aligned, "distinct": sorted(distinct)}


def check(cfg: Config) -> dict:
    """Full sanity probe -> structured report."""
    checks: list[dict] = []
    checks.extend(check_services(cfg))

    health = _oc(cfg, "health", timeout=cfg["health_timeout"])
    healthy = health["rc"] == 0 and bool(health["out"]) and "abnormal" not in (health["out"] + health["err"]).lower()
    checks.append({"name": "gateway:health", "status": OK if healthy else FAIL,
                   "detail": (health["out"] or health["err"])[:200]})

    val = _oc(cfg, "config", "validate", timeout=40)
    valid = "config valid" in (val["out"] + val["err"]).lower()
    stale = len(re.findall(r"plugin not (?:installed|found)|requires compiled runtime", val["out"] + val["err"]))
    checks.append({"name": "config:valid", "status": OK if valid else FAIL,
                   "detail": "valid" if valid else (val["out"] or val["err"])[:200]})
    checks.append({"name": "config:stale_plugins", "status": OK if stale == 0 else WARN,
                   "detail": f"{stale} stale-plugin warning(s)", "_count": stale})

    ver = check_versions(cfg)
    checks.append({"name": "version:aligned", "status": OK if ver["aligned"] else FAIL,
                   "detail": json.dumps(ver["versions"], ensure_ascii=False), "_ver": ver})

    cron = _oc(cfg, "cron", "list", timeout=40)
    cron_ok = cron["rc"] == 0 and "ID" in cron["out"]
    checks.append({"name": "cron:scheduler", "status": OK if cron_ok else WARN,
                   "detail": "reachable" if cron_ok else (cron["err"] or cron["out"])[:160]})

    latest = npm_latest(cfg)
    cur = ver["versions"].get("cli") or ver["distinct"][0] if ver["distinct"] else None
    update_avail = bool(latest and cur and version_tuple(latest) > version_tuple(cur))
    checks.append({"name": "update:available", "status": WARN if update_avail else OK,
                   "detail": f"installed={cur} latest={latest}",
                   "_latest": latest, "_current": cur, "_update": update_avail})

    du = shutil.disk_usage(expand(cfg["config_path"].rsplit("/", 1)[0] if "/" in cfg["config_path"] else "~"))
    free_mb = du.free // (1024 * 1024)
    checks.append({"name": "disk:free", "status": OK if free_mb >= cfg["min_free_disk_mb"] else WARN,
                   "detail": f"{free_mb} MiB free"})

    statuses = [c["status"] for c in checks]
    overall = FAIL if FAIL in statuses else (WARN if WARN in statuses else OK)
    return {"generatedAt": now(), "runtime": detect_runtime(), "overall": overall,
            "checks": checks, "versions": ver, "latest": latest}


# --------------------------------------------------------------------------- #
# repair (bounded, idempotent)
# --------------------------------------------------------------------------- #
def repair(cfg: Config, report: dict, dry: bool) -> list[dict]:
    actions = []
    scope = cfg["systemctl_scope"]

    def act(label, fn):
        if dry:
            actions.append({"action": label, "status": "planned"})
            return
        res = fn()
        actions.append({"action": label, "status": "done" if res.get("rc", 1) == 0 else "failed",
                        "detail": (res.get("err") or res.get("out") or "")[:160]})

    by_name = {c["name"]: c for c in report["checks"]}

    # 1) restart inactive/failed services (with reset-failed first)
    for c in report["checks"]:
        if c.get("_svc") and not c.get("_active"):
            svc = c["_svc"]
            act(f"reset-failed {svc}", lambda s=svc: run(["systemctl", scope, "reset-failed", s]))
            act(f"restart {svc}", lambda s=svc: run(["systemctl", scope, "restart", s]))

    # 2) daemon-reload + restart if unit files drifted and gateway unhealthy
    if by_name.get("gateway:health", {}).get("status") == FAIL and not any(
            c.get("_svc") and not c.get("_active") for c in report["checks"]):
        act("daemon-reload", lambda: run(["systemctl", scope, "daemon-reload"]))
        act("restart gateway", lambda: run(["systemctl", scope, "restart", cfg["services"][0]]))

    # 3) stale plugin config -> let openclaw normalize legacy cron/plugin storage
    if by_name.get("config:stale_plugins", {}).get("_count", 0) > 0:
        act("doctor --fix (normalize stale plugin/cron config)",
            lambda: _oc(cfg, "doctor", "--fix", timeout=120))

    # 4) version skew -> re-align by reinstalling the lagging copies to the highest
    ver = report["versions"]
    if not ver["aligned"] and ver["distinct"]:
        target = max(ver["distinct"], key=version_tuple)
        actions.append({"action": f"version skew detected -> re-align to {target}", "status": "delegated-to-update"})
        if not dry and cfg["allow_update"]:
            actions.extend(_install_all_copies(cfg, target, dry=False))

    return actions


# --------------------------------------------------------------------------- #
# update (transactional)
# --------------------------------------------------------------------------- #
def _sudo_ok() -> bool:
    return run(["sudo", "-n", "true"], timeout=10)["rc"] == 0


def _install_all_copies(cfg: Config, version: str, dry: bool) -> list[dict]:
    pkg = cfg["npm_package"]
    spec = f"{pkg}@{version}"
    acts = []
    # user copy (no sudo)
    prefix = expand(cfg["user_prefix"])
    if dry:
        acts.append({"action": f"npm i -g {spec} --prefix {prefix}", "status": "planned"})
    else:
        r = run(["npm", "i", "-g", spec, "--prefix", prefix], timeout=300)
        acts.append({"action": f"user copy -> {spec}", "status": "done" if r["rc"] == 0 else "failed",
                     "detail": (r["err"] or r["out"])[-160:]})
    # system copy (needs sudo)
    sys_copy = cfg["copies"].get("system")
    if sys_copy and sys_copy.get("needs_sudo"):
        if dry:
            acts.append({"action": f"sudo npm i -g {spec}", "status": "planned"})
        elif _sudo_ok():
            r = run(["sudo", "-n", "npm", "i", "-g", spec], timeout=300)
            acts.append({"action": f"system copy -> {spec}", "status": "done" if r["rc"] == 0 else "failed",
                         "detail": (r["err"] or r["out"])[-160:]})
        else:
            acts.append({"action": f"system copy -> {spec}", "status": "skipped",
                         "detail": "passwordless sudo unavailable; system /usr/lib copy NOT updated "
                                   "(version skew risk) — run manually: sudo npm i -g " + spec})
    # node-service Description bump
    unit = Path(expand(cfg["node_service_unit"]))
    if unit.exists():
        if dry:
            acts.append({"action": f"bump {unit.name} Description -> v{version}", "status": "planned"})
        else:
            try:
                txt = unit.read_text(encoding="utf-8")
                new = re.sub(r"(Description=.*?)\(v[0-9][^)]*\)", rf"\1(v{version})", txt)
                if new != txt:
                    unit.write_text(new, encoding="utf-8")
                    acts.append({"action": f"bump {unit.name} Description -> v{version}", "status": "done"})
                run(["systemctl", cfg["systemctl_scope"], "daemon-reload"])
            except Exception as e:  # noqa
                acts.append({"action": "bump Description", "status": "failed", "detail": str(e)[:120]})
    return acts


def snapshot(cfg: Config, version_before: str | None) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    cfgp = Path(expand(cfg["config_path"]))
    bak = None
    if cfgp.exists():
        bak = str(cfgp) + f".devops-bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        shutil.copy2(cfgp, bak)
    snap = {"ts": now(), "version_before": version_before, "config_backup": bak}
    STATE_FILE.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return snap


def restart_services(cfg: Config, dry: bool) -> list[dict]:
    acts = []
    scope = cfg["systemctl_scope"]
    for svc in cfg["services"]:
        if dry:
            acts.append({"action": f"restart {svc}", "status": "planned"})
        else:
            r = run(["systemctl", scope, "restart", svc], timeout=60)
            acts.append({"action": f"restart {svc}", "status": "done" if r["rc"] == 0 else "failed",
                         "detail": (r["err"])[:120]})
            time.sleep(2)
    return acts


def wait_healthy(cfg: Config, tries: int = 12, delay: int = 4) -> bool:
    for _ in range(tries):
        h = _oc(cfg, "health", timeout=cfg["health_timeout"])
        if h["rc"] == 0 and h["out"] and "abnormal" not in (h["out"] + h["err"]).lower():
            return True
        time.sleep(delay)
    return False


def update(cfg: Config, report: dict, dry: bool, allow_major: bool) -> dict:
    upd = next((c for c in report["checks"] if c["name"] == "update:available"), {})
    latest = upd.get("_latest")
    cur = upd.get("_current")
    if not latest or not cur or version_tuple(latest) <= version_tuple(cur):
        return {"updated": False, "reason": f"no newer {cfg['channel']} (installed={cur}, latest={latest})"}
    if is_major_jump(cfg, cur, latest) and cfg["hold_major"] and not allow_major:
        return {"updated": False, "held": True,
                "reason": f"major jump {cur} -> {latest} held (hold_major); pass --allow-major to apply"}
    if cfg["maintenance_hours"]:
        hour = datetime.now().hour
        if hour not in cfg["maintenance_hours"]:
            return {"updated": False, "reason": f"outside maintenance window (hour {hour})"}

    snap = snapshot(cfg, cur)
    install = _install_all_copies(cfg, latest, dry)
    if dry:
        return {"updated": False, "dry_run": True, "target": latest, "from": cur,
                "snapshot": snap, "plan": install}
    restart = restart_services(cfg, dry=False)
    healthy = wait_healthy(cfg)
    ver = verify(cfg)
    if ver["pass"] and healthy:
        return {"updated": True, "from": cur, "to": latest, "snapshot": snap,
                "install": install, "restart": restart, "verify": ver}
    # integrity failed -> rollback
    rb = rollback(cfg, to_version=cur, dry=False, reason="post-update verify failed")
    return {"updated": False, "rolled_back": True, "from": cur, "attempted": latest,
            "verify": ver, "rollback": rb, "alert": True,
            "reason": "post-update integrity gate failed; rolled back to " + str(cur)}


# --------------------------------------------------------------------------- #
# verify (integrity gate)
# --------------------------------------------------------------------------- #
def verify(cfg: Config) -> dict:
    gates = []
    val = _oc(cfg, "config", "validate", timeout=40)
    gates.append({"gate": "config validate", "pass": "config valid" in (val["out"] + val["err"]).lower(),
                  "detail": (val["out"] or val["err"])[:140]})
    h = _oc(cfg, "health", timeout=cfg["health_timeout"])
    gates.append({"gate": "gateway health", "pass": h["rc"] == 0 and bool(h["out"]),
                  "detail": (h["out"] or h["err"])[:140]})
    cron = _oc(cfg, "cron", "list", timeout=40)
    gates.append({"gate": "cron list", "pass": cron["rc"] == 0 and "ID" in cron["out"],
                  "detail": "ok" if "ID" in cron["out"] else (cron["err"] or cron["out"])[:140]})
    ver = check_versions(cfg)
    gates.append({"gate": "version aligned", "pass": ver["aligned"], "detail": json.dumps(ver["versions"])})
    return {"pass": all(g["pass"] for g in gates), "gates": gates}


# --------------------------------------------------------------------------- #
# rollback
# --------------------------------------------------------------------------- #
def rollback(cfg: Config, to_version: str | None, dry: bool, reason: str = "") -> dict:
    st = {}
    if STATE_FILE.exists():
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    target = to_version or st.get("version_before")
    if not target:
        return {"ok": False, "reason": "no previous version recorded in state"}
    acts = _install_all_copies(cfg, target, dry)
    # restore config backup
    bak = st.get("config_backup")
    if bak and Path(bak).exists():
        if dry:
            acts.append({"action": f"restore config from {bak}", "status": "planned"})
        else:
            shutil.copy2(bak, expand(cfg["config_path"]))
            acts.append({"action": "restore config backup", "status": "done"})
    if not dry:
        restart_services(cfg, dry=False)
        wait_healthy(cfg)
    return {"ok": True, "rolled_back_to": target, "reason": reason, "actions": acts}


# --------------------------------------------------------------------------- #
# cycle orchestrator (cron entry)
# --------------------------------------------------------------------------- #
class Lock:
    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def __enter__(self):
        import fcntl
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.fd = open(self.path, "w")
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("another devops run holds the lock; exiting")
        self.fd.write(f"{os.getpid()} {now()}\n")
        self.fd.flush()
        return self

    def __exit__(self, *a):
        try:
            import fcntl
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        except Exception:
            pass


def append_history(entry: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def cycle(cfg: Config, dry: bool, allow_major: bool, do_repair: bool, do_update: bool) -> dict:
    with Lock(LOCK_FILE):
        result = {"startedAt": now(), "runtime": detect_runtime(), "dry_run": dry}
        rep = check(cfg)
        result["sanity"] = {"overall": rep["overall"],
                            "issues": [c["name"] for c in rep["checks"] if c["status"] != OK]}
        if do_repair and cfg["allow_repair"] and rep["overall"] != OK:
            result["repair"] = repair(cfg, rep, dry)
            rep2 = check(cfg)
            result["post_repair"] = {"overall": rep2["overall"],
                                     "issues": [c["name"] for c in rep2["checks"] if c["status"] != OK]}
            rep = rep2
        if do_update and cfg["allow_update"]:
            result["update"] = update(cfg, rep, dry, allow_major)
        result["finishedAt"] = now()
        result["overall"] = rep["overall"]
        result["bugs_open"] = open_bug_count()
        append_history({"ts": result["finishedAt"], "overall": result["overall"],
                        "sanity": result["sanity"], "dry_run": dry,
                        "update": result.get("update", {}).get("updated") or result.get("update", {}).get("reason")})
        return result


# --------------------------------------------------------------------------- #
# lessons journal — record debugged bugs + the optimization pattern that fixed
# them, so future maintenance reuses the fix instead of re-diagnosing.
# --------------------------------------------------------------------------- #
def lessons_add(title: str, bug: str, cause: str, fix: str, tags: str | None) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now(), "title": title, "bug": bug, "root_cause": cause,
             "fix": fix, "tags": [t.strip() for t in (tags or "").split(",") if t.strip()]}
    with LESSONS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"recorded": True, "lesson": entry, "total": sum(1 for _ in LESSONS_FILE.open(encoding="utf-8"))}


def lessons_list() -> dict:
    items = []
    if LESSONS_FILE.exists():
        for line in LESSONS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    return {"count": len(items), "lessons": items}


def render_lessons(obj: dict) -> str:
    if "lesson" in obj:  # add
        e = obj["lesson"]
        return (f"**🛠️ DevOps lesson recorded** ({obj['total']} total)\n"
                f"- **{e['title']}** [{', '.join(e['tags']) or '—'}]\n"
                f"  bug: {e['bug']}\n  cause: {e['root_cause']}\n  fix: {e['fix']}")
    lines = [f"**🛠️ DevOps lessons** ({obj['count']})"]
    for e in obj.get("lessons", []):
        lines.append(f"- `{e.get('ts','')[:10]}` **{e.get('title')}** [{', '.join(e.get('tags',[])) or '—'}]")
        lines.append(f"   bug: {e.get('bug')}")
        lines.append(f"   cause: {e.get('root_cause')}")
        lines.append(f"   fix: {e.get('fix')}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# bugs panel / backlog — a cross-bug registry any agent or cron can append to,
# tracked to resolution and linkable to a meta-debug session + a lesson.
# --------------------------------------------------------------------------- #
def _bugs_load() -> dict:
    if BUGS_FILE.exists():
        try:
            return json.loads(BUGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"next_id": 1, "bugs": []}


def _bugs_save(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    BUGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class _FileLock:
    """Blocking exclusive flock for the brief bugs read-modify-write window."""
    def __enter__(self):
        import fcntl
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.fd = open(BUGS_LOCK, "w")
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        try:
            import fcntl
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        except Exception:
            pass


def bugs_add(title: str, severity: str, source: str, detail: str, tags: str | None) -> dict:
    with _FileLock():
        d = _bugs_load()
        bid = f"BUG-{d['next_id']}"
        d["next_id"] += 1
        bug = {"id": bid, "title": title, "severity": severity or "sev3", "status": "open",
               "source": source or "unknown", "detail": detail or "", "assignee": "",
               "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
               "session": "", "lesson": "", "created": now(), "updated": now(),
               "history": [{"ts": now(), "change": f"opened by {source or 'unknown'}"}]}
        d["bugs"].append(bug)
        _bugs_save(d)
    return {"added": bid, "bug": bug}


def bugs_update(bid: str, **fields) -> dict:
    with _FileLock():
        d = _bugs_load()
        bug = next((b for b in d["bugs"] if b["id"] == bid), None)
        if not bug:
            return {"error": f"no such bug {bid}"}
        changes = []
        for k in ("status", "severity", "session", "lesson", "assignee"):
            v = fields.get(k)
            if v:
                if k == "status" and v not in BUG_STATUSES:
                    return {"error": f"status must be one of {BUG_STATUSES}"}
                bug[k] = v
                changes.append(f"{k}={v}")
        if fields.get("note"):
            changes.append(f"note: {fields['note']}")
        if fields.get("tags"):
            bug["tags"] = sorted(set(bug["tags"]) | {t.strip() for t in fields["tags"].split(",") if t.strip()})
            changes.append("tags+")
        bug["updated"] = now()
        bug["history"].append({"ts": now(), "change": "; ".join(changes) or "touched"})
        _bugs_save(d)
    return {"updated": bid, "changes": changes, "bug": bug}


def bugs_view(status: str | None = None) -> dict:
    d = _bugs_load()
    bugs = d["bugs"]
    if status:
        bugs = [b for b in bugs if b["status"] == status]
    return {"count": len(bugs), "bugs": bugs, "total": len(d["bugs"])}


def bugs_panel() -> dict:
    d = _bugs_load()
    bugs = d["bugs"]
    open_bugs = [b for b in bugs if b["status"] in BUG_OPEN]
    by_status = {s: sum(1 for b in bugs if b["status"] == s) for s in BUG_STATUSES}
    by_sev = {}
    for b in open_bugs:
        by_sev[b["severity"]] = by_sev.get(b["severity"], 0) + 1
    recent_fixed = sorted([b for b in bugs if b["status"] == "fixed"],
                          key=lambda b: b["updated"], reverse=True)[:5]
    return {"total": len(bugs), "open": len(open_bugs), "by_status": by_status,
            "open_by_severity": by_sev,
            "open_bugs": sorted(open_bugs, key=lambda b: (b["severity"], b["created"])),
            "recent_fixed": recent_fixed}


def open_bug_count() -> int:
    return sum(1 for b in _bugs_load()["bugs"] if b["status"] in BUG_OPEN)


def render_bugs(obj: dict) -> str:
    if "added" in obj:
        b = obj["bug"]
        return f"🐞 logged **{b['id']}** [{b['severity']}] {b['title']} (status open, source {b['source']})"
    if "updated" in obj:
        return f"🐞 {obj['updated']}: {', '.join(obj['changes']) or 'touched'}"
    if "error" in obj:
        return f"❌ {obj['error']}"
    if "bugs" in obj and "by_status" not in obj:  # list view
        lines = [f"**🐞 Bugs ({obj['count']}/{obj['total']})**"]
        for b in obj["bugs"]:
            link = (f" → {b['session']}" if b.get("session") else "")
            lines.append(f"- `{b['id']}` [{b['severity']}] {b['status']:11} {b['title']}{link}")
        return "\n".join(lines)
    # panel
    p = obj
    lines = [f"**🐞 OpenClaw DevOps — Bugs Panel** ({p['open']} open / {p['total']} total)"]
    sev = " · ".join(f"{k}:{v}" for k, v in sorted(p["open_by_severity"].items())) or "none"
    lines.append(f"open by severity: {sev}")
    lines.append("by status: " + " · ".join(f"{k}:{v}" for k, v in p["by_status"].items() if v))
    if p["open_bugs"]:
        lines.append("\n**Open**")
        for b in p["open_bugs"][:12]:
            link = (f" → {b['session']}" if b.get("session") else "")
            lines.append(f"- `{b['id']}` [{b['severity']}] {b['status']}: {b['title']} (src {b['source']}){link}")
    if p["recent_fixed"]:
        lines.append("\n**Recently fixed**")
        for b in p["recent_fixed"]:
            lines.append(f"- ✅ `{b['id']}` {b['title']}" + (f" ({b['lesson']})" if b.get("lesson") else ""))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# reporting / CLI
# --------------------------------------------------------------------------- #
ICON = {OK: "🟢", WARN: "🟡", FAIL: "🔴"}


def _fmt_update(u: dict) -> str:
    if u.get("updated"):
        return f"update: ✅ {u['from']} → {u['to']} (verified)"
    if u.get("rolled_back"):
        return f"update: ⛔ {u['attempted']} failed verify → ROLLED BACK to {u['from']}"
    if u.get("dry_run"):
        return f"update: (dry-run) would go {u.get('from')} → {u.get('target')}"
    return f"update: none — {u.get('reason')}"


def render_summary(obj: dict) -> str:
    """Dispatch on output shape; defensive against every verb's result."""
    lines = ["**🛠️ OpenClaw DevOps**"]
    # sanity report
    if "checks" in obj:
        lines[0] += f" — sanity {ICON.get(obj['overall'],'')} {obj['overall'].upper()}"
        lines += [f"- {ICON.get(c['status'],'')} `{c['name']}`: {c['detail']}" for c in obj["checks"]]
        return "\n".join(lines)
    # verify gate
    if "gates" in obj:
        lines[0] += f" — verify {'🟢 PASS' if obj.get('pass') else '🔴 FAIL'}"
        lines += [f"- {'✅' if g['pass'] else '❌'} {g['gate']}: {g['detail']}" for g in obj["gates"]]
        return "\n".join(lines)
    # standalone update
    if "updated" in obj and "sanity" not in obj:
        lines[0] += " — update"
        lines.append("- " + _fmt_update(obj))
        return "\n".join(lines)
    # rollback (the only verb with a top-level "ok")
    if "ok" in obj:
        lines[0] += " — rollback"
        if obj.get("rolled_back_to"):
            lines.append(f"- {'✅' if obj.get('ok') else '❌'} rolled back to {obj['rolled_back_to']} ({obj.get('reason','')})")
        else:
            lines.append(f"- ❌ {obj.get('reason','rollback not performed')}")
        return "\n".join(lines)
    # standalone repair: {"sanity": <str>, "actions": [...]}
    if "actions" in obj and isinstance(obj.get("sanity"), str):
        lines[0] += f" — repair (sanity {obj['sanity']})"
        acts = obj["actions"] or [{"status": "-", "action": "no repair actions needed"}]
        lines += [f"- {a.get('status')}: {a.get('action')}" for a in acts[:8]]
        return "\n".join(lines)
    # cycle result
    s = obj.get("sanity", {}) if isinstance(obj.get("sanity"), dict) else {}
    lines[0] += f" — cycle {ICON.get(obj.get('overall'),'')} {str(obj.get('overall','')).upper()}"
    lines.append(f"- sanity: {s.get('overall')} | issues: {', '.join(s.get('issues') or []) or 'none'}")
    if obj.get("bugs_open") is not None:
        lines.append(f"- backlog: {obj['bugs_open']} open bug(s) — `openclaw_devops.py bugs --panel`")
    if "repair" in obj:
        lines.append(f"- repair: {len(obj['repair'])} action(s); post-repair {obj.get('post_repair',{}).get('overall')}")
        lines += [f"   · {a['status']}: {a['action']}" for a in obj["repair"][:6]]
    if "update" in obj:
        lines.append("- " + _fmt_update(obj["update"]))
    return "\n".join(lines)


def emit(obj: dict, as_json: bool):
    print(json.dumps(obj, indent=2, ensure_ascii=False) if as_json else render_summary(obj))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="OpenClaw DevOps maintenance engine (sanity/repair/update/verify/rollback/cycle).",
        epilog="Missing host tools (openclaw/systemctl/npm) surface as failed checks, not crashes.")
    ap.add_argument("command", choices=["sanity", "repair", "update", "verify", "rollback", "cycle", "lessons", "bugs"])
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to config.json")
    # bugs panel / backlog (any agent or cron can log a bug; track to resolution)
    ap.add_argument("--add", action="store_true", help="bugs: log a new bug (needs --title)")
    ap.add_argument("--panel", action="store_true", help="bugs: render the backlog panel")
    ap.add_argument("--update", metavar="BUG-ID", help="bugs: update a bug by id")
    ap.add_argument("--show", metavar="BUG-ID", help="bugs: show one bug")
    ap.add_argument("--status", help="bugs: status (open|triaged|in-progress|fixed|wontfix|duplicate); filters --list")
    ap.add_argument("--severity", help="bugs: sev1..sev4")
    ap.add_argument("--source", help="bugs: who/what reported it (agent, cron, user)")
    ap.add_argument("--detail", help="bugs: description")
    ap.add_argument("--session", help="bugs: link a meta-debug session id (dbg-...)")
    ap.add_argument("--lesson", help="bugs: link/Note a recorded lesson")
    ap.add_argument("--assignee", help="bugs: owner")
    ap.add_argument("--note", help="bugs: free-text history note")
    # lessons journal (record debugged bugs + the optimization pattern that fixed them)
    ap.add_argument("--title", help="lessons add: short title")
    ap.add_argument("--bug", help="lessons add: observed symptom")
    ap.add_argument("--cause", help="lessons add: verified root cause")
    ap.add_argument("--fix", help="lessons add: fix / optimization pattern")
    ap.add_argument("--tags", help="lessons add: comma-separated tags")
    ap.add_argument("--list", action="store_true", help="lessons: list recorded lessons")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--dry-run", action="store_true", help="plan actions without mutating")
    ap.add_argument("--allow-major", action="store_true", help="permit a held major-version jump")
    ap.add_argument("--no-repair", action="store_true", help="cycle: skip repair phase")
    ap.add_argument("--no-update", action="store_true", help="cycle: skip update phase")
    ap.add_argument("--to-version", help="rollback: target version (default: recorded previous)")
    args = ap.parse_args(argv)

    cfg = Config(Path(expand(args.config)))

    if args.command == "sanity":
        emit(check(cfg), args.json)
        return 0
    if args.command == "repair":
        rep = check(cfg)
        emit({"sanity": rep["overall"], "actions": repair(cfg, rep, args.dry_run)}, args.json)
        return 0
    if args.command == "update":
        emit(update(cfg, check(cfg), args.dry_run, args.allow_major), args.json)
        return 0
    if args.command == "verify":
        v = verify(cfg)
        emit(v, args.json)
        return 0 if v["pass"] else 1
    if args.command == "rollback":
        emit(rollback(cfg, args.to_version, args.dry_run), args.json)
        return 0
    if args.command == "cycle":
        res = cycle(cfg, args.dry_run, args.allow_major,
                    do_repair=not args.no_repair, do_update=not args.no_update)
        emit(res, args.json)
        return 0 if res.get("overall") != FAIL else 1
    if args.command == "lessons":
        if args.title and args.bug and args.cause and args.fix:
            out = lessons_add(args.title, args.bug, args.cause, args.fix, args.tags)
        else:
            out = lessons_list()
        print(json.dumps(out, indent=2, ensure_ascii=False) if args.json else render_lessons(out))
        return 0
    if args.command == "bugs":
        if args.update:
            out = bugs_update(args.update, status=args.status, severity=args.severity,
                              session=args.session, lesson=args.lesson, assignee=args.assignee,
                              note=args.note, tags=args.tags)
        elif args.show:
            v = bugs_view()
            b = next((x for x in v["bugs"] if x["id"] == args.show), None)
            out = b if args.json else {"bugs": [b] if b else [], "count": int(bool(b)), "total": v["total"]}
        elif args.add or (args.title and not args.list and not args.panel):
            out = bugs_add(args.title, args.severity, args.source, args.detail, args.tags)
        elif args.list:
            out = bugs_view(args.status)
        else:
            out = bugs_panel()
        print(json.dumps(out, indent=2, ensure_ascii=False) if args.json else render_bugs(out))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

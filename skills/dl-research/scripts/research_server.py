#!/usr/bin/env python3
"""Research-server — stdlib HTTP host for dl-research reports.

Serves the per-study HTML reports + sidecars under ``agents/research/<study-id>/``
over local HTTP. Stdlib only (no Flask, no FastAPI). Suitable for owner-loopback
use and read-only LAN exposure for guest reviewers.

Endpoints:

    GET /                              landing page (study cards)
    GET /<study-id>/                   serves report.html for the study
    GET /<study-id>/<path>             serves any per-study file
    GET /api/role                      owner / guest detection (loopback => owner)
    GET /api/studies                   /_registry.json passthrough
    GET /<study-id>/api/state          aggregated sidecar state
    GET /<study-id>/api/objectives/latest   last line of objectives/snapshots.jsonl

Role detection: source IP only. Loopback => owner; everything else => guest.
Server bind defaults to 127.0.0.1; pass ``--bind 0.0.0.0`` to allow LAN reach
(emits a loud warning at boot).

Foreground process — stop with Ctrl-C.

Usage
-----
    python scripts/research_server.py [--repo-root .] [--port 8765] [--bind 127.0.0.1]

The server expects studies under ``<repo-root>/agents/research/<study-id>/`` and
each study to contain ``adapter.yaml`` + ``report.html``. See
``templates/frontend/report.html`` for a generic report skeleton.
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, unquote

log = logging.getLogger("research-server")

# Loopback variants treated as owner. IPv6 ::1 included; LAN IPs are guest.
LOOPBACK = {"127.0.0.1", "::1", "localhost"}

# Repo root resolved at server start; one server per repo.
REPO_ROOT: Path = Path.cwd()
RESEARCH_ROOT: Path = REPO_ROOT / "agents" / "research"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def list_studies() -> list[dict]:
    """Walk agents/research/<study-id>/ and produce summary cards.

    Prefers the on-disk _registry.json when present and fresh; else scans
    the directory. Skips _-prefixed dirs (those are repo-level state).
    """
    registry = RESEARCH_ROOT / "_registry.json"
    if registry.exists():
        try:
            return json.loads(registry.read_text()).get("studies", [])
        except json.JSONDecodeError:
            log.warning("_registry.json is invalid, falling back to directory scan")

    studies = []
    if not RESEARCH_ROOT.exists():
        return studies
    for p in sorted(RESEARCH_ROOT.iterdir()):
        if not p.is_dir() or p.name.startswith("_"):
            continue
        adapter = p / "adapter.yaml"
        if not adapter.exists():
            continue
        studies.append({
            "study_id": p.name,
            "title": p.name,
            "status": "active",
            "current_phase": "?",
            "phase_versions": {},
            "gate_summary": {},
            "owner": "",
            "last_activity_utc": utc_now_iso(),
            "adapter_path": str(adapter.relative_to(REPO_ROOT)),
        })
    return studies


def load_latest_objective_snapshot(study_id: str) -> dict:
    """Return the most recent line of objectives/snapshots.jsonl as a dict.

    No-snapshot case returns a stub with `status: "no_snapshots_yet"` so the
    browser can render an empty tracker block without crashing.
    """
    study_dir = RESEARCH_ROOT / study_id
    jsonl = study_dir / "objectives" / "snapshots.jsonl"
    if not jsonl.is_file():
        return {"status": "no_snapshots_yet", "study_id": study_id,
                "hint": "run scripts/objectives_snapshot.py --study " + str(study_dir.relative_to(REPO_ROOT))}
    lines = [ln for ln in jsonl.read_text().splitlines() if ln.strip()]
    if not lines:
        return {"status": "no_snapshots_yet", "study_id": study_id}
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as e:
        return {"status": "parse_error", "study_id": study_id, "error": str(e)}


def aggregate_study_state(study_id: str) -> dict:
    """Return the merged sidecar state for a single study.

    First-pass scope: enumerate phases/diffs/citations/objectives files;
    deeper sidecar parsing is up to the project's renderer / loaders.
    """
    study_dir = RESEARCH_ROOT / study_id
    if not study_dir.is_dir():
        return {"error": f"unknown study: {study_id}"}

    def _safe_read_json(rel: str) -> dict | list | None:
        f = study_dir / rel
        if not f.exists():
            return None
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            return {"_parse_error": True, "path": rel}

    return {
        "study_id": study_id,
        "study_dir": str(study_dir.relative_to(REPO_ROOT)),
        "fetched_utc": utc_now_iso(),
        "adapter_yaml_present": (study_dir / "adapter.yaml").exists(),
        "phase_manifests": sorted(
            str(p.relative_to(study_dir))
            for p in study_dir.glob("phases/*/manifest.json")
        ),
        "diff_count": len(list(study_dir.glob("diffs/*/*.json"))),
        "citation_registry": _safe_read_json("citations/citations.json"),
        "library_refs": _safe_read_json("../_citations/library.json"),
        "objectives_latest": _safe_read_json("objectives/snapshots.jsonl"),
        "approvals_pending": _safe_read_json("approvals/pending.jsonl"),
    }


# ---------------------------------------------------------------------------
# Landing page — study cards rendered from agents/research/_registry.json
# (or a directory walk fallback when the registry is missing/invalid)
# ---------------------------------------------------------------------------


_LANDING_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>{repo_name} · Research</title>
<style>
  body {{ margin:0; background:#0f1419; color:#e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
  header {{ padding: 28px 36px; border-bottom: 1px solid #30363d; }}
  header h1 {{ margin:0; font-size: 22px; font-weight: 600; }}
  header .meta {{ color:#8b949e; font-size:13px; margin-top:6px; }}
  .role-badge {{ display:inline-block; padding:3px 10px; border-radius:10px;
    font-size:11px; text-transform:uppercase; letter-spacing:.5px; font-weight:600; margin-left:10px; }}
  .role-badge.owner {{ background: rgba(63,185,80,0.15); color: #3fb950; }}
  .role-badge.guest {{ background: rgba(210,153,34,0.15); color: #d29922; }}
  main {{ padding: 28px 36px; max-width: 1100px; margin: 0 auto; }}
  .grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }}
  .card {{ background:#1a2028; border:1px solid #30363d; border-radius:8px;
    padding:18px 20px; text-decoration:none; color:inherit; transition: border-color .15s; }}
  .card:hover {{ border-color:#4ec9ff; }}
  .card h2 {{ margin:0 0 4px; font-size:16px; color:#4ec9ff; font-weight:600; }}
  .card .sub {{ color:#8b949e; font-size:12px; margin-bottom:12px; }}
  .row {{ display:flex; justify-content:space-between; font-size:12.5px; margin: 4px 0; color:#e6edf3; }}
  .row .k {{ color:#8b949e; }}
  .gates {{ display:flex; gap:6px; margin-top:8px; }}
  .gate {{ font-size:11px; padding:2px 8px; border-radius:8px; }}
  .gate.pass {{ background:rgba(63,185,80,0.15); color:#3fb950; }}
  .gate.fail {{ background:rgba(248,81,73,0.15); color:#f85149; }}
  .gate.pending {{ background:#161b22; color:#8b949e; }}
  footer {{ padding: 18px 36px; color:#8b949e; font-size:11.5px;
    border-top:1px solid #30363d; margin-top: 32px; }}
  .empty {{ color:#8b949e; padding: 60px 0; text-align:center; }}
</style></head>
<body>
<header>
  <h1>{repo_name} · Research<span class="role-badge {role}">{role}</span></h1>
  <div class="meta">
    {study_count} studies · served from <code>{research_root}</code>
    · {bind_note}
  </div>
</header>
<main>
{study_cards}
</main>
<footer>
  research-server · stdlib · this page is rebuilt from
  <code>agents/research/_registry.json</code> on each request, or by walking
  the directory tree if the registry is absent.
</footer>
</body></html>
"""


def _gate_chip(status: str) -> str:
    cls = {"pass": "pass", "fail": "fail"}.get(status, "pending")
    label = {"pass": "✓", "fail": "✗"}.get(status, "🕓")
    return f'<span class="gate {cls}">{label} {status}</span>'


def render_landing(role: str, bind_addr: str) -> bytes:
    studies = list_studies()
    if not studies:
        cards_html = '<div class="empty">No studies yet. Run <code>dl-research frame &lt;study-id&gt;</code> to seed one.</div>'
    else:
        cards = []
        for s in studies:
            phases = s.get("phase_versions", {})
            phases_line = " · ".join(f"{k}:{v}" for k, v in phases.items()) or "—"
            gates = s.get("gate_summary", {})
            gates_html = "".join(
                _gate_chip(v) for v in [gates.get("latency", "pending"),
                                        gates.get("accuracy", "pending"),
                                        gates.get("recipe", "pending")]
            )
            cards.append(
                f'<a class="card" href="/{s["study_id"]}/">'
                f'<h2>{s["study_id"]}</h2>'
                f'<div class="sub">{s.get("title", "")}</div>'
                f'<div class="row"><span class="k">phase</span><span>{s.get("current_phase", "?")} · {phases_line}</span></div>'
                f'<div class="row"><span class="k">status</span><span>{s.get("status", "?")}</span></div>'
                f'<div class="row"><span class="k">owner</span><span>{s.get("owner", "")}</span></div>'
                f'<div class="row"><span class="k">last activity</span><span>{s.get("last_activity_utc", "?")}</span></div>'
                f'<div class="gates">{gates_html}</div>'
                f'</a>'
            )
        cards_html = f'<div class="grid">{"".join(cards)}</div>'

    bind_note = (
        '<span style="color:#3fb950">loopback (owner-only)</span>'
        if bind_addr in LOOPBACK
        else '<span style="color:#d29922">LAN bind</span>'
    )
    html = _LANDING_TEMPLATE.format(
        repo_name=REPO_ROOT.name,
        role=role,
        study_count=len(studies),
        research_root=str(RESEARCH_ROOT.relative_to(REPO_ROOT)),
        bind_note=bind_note,
        study_cards=cards_html,
    )
    return html.encode("utf-8")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "ResearchServer/0.1"

    # Silence default per-request stderr noise; we log selectively.
    def log_message(self, fmt, *args):
        log.info("%s — %s", self.address_string(), fmt % args)

    # ---------- helpers ----------

    def _role(self) -> str:
        addr = self.client_address[0]
        return "owner" if addr in LOOPBACK else "guest"

    def _send_json(self, payload: dict | list, code: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: bytes, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            return self._send_json({"error": "not found", "path": str(path)}, code=404)
        ctype, _ = mimetypes.guess_type(path.name)
        ctype = ctype or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _safe_join(self, base: Path, *parts: str) -> Path | None:
        """Resolve a request path under base, rejecting traversal."""
        target = (base.joinpath(*parts)).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            return None
        return target

    # ---------- routes ----------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        role = self._role()

        # Bind addr to display in landing (passed through global)
        bind_addr = self.server.server_address[0]

        # /api/* — global
        if path == "/api/role":
            return self._send_json({
                "role": role,
                "client_ip": self.client_address[0],
                "server_bind": bind_addr,
                "loopback": role == "owner",
            })

        if path == "/api/studies":
            return self._send_json({
                "schema_version": 1,
                "fetched_utc": utc_now_iso(),
                "role": role,
                "studies": list_studies(),
            })

        # / — landing page
        if path in ("", "/"):
            return self._send_html(render_landing(role, bind_addr))

        # /<study-id>/api/state
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) >= 3 and parts[1] == "api" and parts[2] == "state":
            study_id = parts[0]
            return self._send_json(aggregate_study_state(study_id))

        # /<study-id>/api/objectives/latest — most recent snapshot line
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "objectives" and parts[3] == "latest":
            study_id = parts[0]
            return self._send_json(load_latest_objective_snapshot(study_id))

        # /<study-id>/  → /<study-id>/report.html
        # /<study-id>/<file...>  → that file (sandboxed under the study dir)
        if len(parts) >= 1:
            study_id = parts[0]
            study_dir = RESEARCH_ROOT / study_id
            if study_dir.is_dir() and not study_id.startswith("_"):
                if len(parts) == 1:
                    return self._send_file(study_dir / "report.html")
                target = self._safe_join(study_dir, *parts[1:])
                if target is None:
                    return self._send_json({"error": "forbidden path"}, code=403)
                if target.is_dir():
                    return self._send_file(target / "report.html")
                return self._send_file(target)

        # /_design/...  → static read of the design tree (read-only)
        if parts and parts[0].startswith("_"):
            target = self._safe_join(RESEARCH_ROOT, *parts)
            if target is not None and target.is_file():
                return self._send_file(target)

        # /agents/research/...  → convenience passthrough for direct paths used
        # by the existing report's relative links (e.g. ../../trt-profiling.md)
        if len(parts) >= 2 and parts[0] == "agents":
            target = self._safe_join(REPO_ROOT, *parts)
            if target is not None and target.is_file():
                return self._send_file(target)

        return self._send_json({"error": "not found", "path": path}, code=404)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo-root", default=".",
                   help="Repo root (parent of agents/research/). Default: cwd.")
    p.add_argument("--port", type=int, default=8765, help="HTTP port. Default: 8765.")
    p.add_argument("--bind", default="127.0.0.1",
                   help="Bind address. Default: 127.0.0.1 (loopback only). "
                        "Pass 0.0.0.0 to allow LAN reach (guests).")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)5s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    global REPO_ROOT, RESEARCH_ROOT
    REPO_ROOT = Path(args.repo_root).resolve()
    RESEARCH_ROOT = REPO_ROOT / "agents" / "research"

    if not RESEARCH_ROOT.exists():
        log.error("agents/research/ not found under %s", REPO_ROOT)
        return 2

    # Loud warning on non-loopback bind: guest reviewers can reach the server
    # from the LAN. Owner role is still loopback-only; guest input (if any UI
    # is wired to write back) must go through whatever approval queue the
    # project defines — the server itself never mutates study files.
    if args.bind not in LOOPBACK and args.bind != "127.0.0.1":
        log.warning("=" * 60)
        log.warning("BIND %s — LAN guests will be able to connect.", args.bind)
        log.warning("Owner role still requires loopback. The server is")
        log.warning("read-only; any write-back UI must guard mutations on the")
        log.warning("client side. Press Ctrl-C to stop.")
        log.warning("=" * 60)

    log.info("Repo root      : %s", REPO_ROOT)
    log.info("Research root  : %s", RESEARCH_ROOT)
    log.info("Studies found  : %d", len(list_studies()))
    log.info("Listening on   : http://%s:%d", args.bind, args.port)
    if args.bind in LOOPBACK or args.bind == "127.0.0.1":
        log.info("(loopback only — owner role; LAN reach disabled)")
    log.info("Press Ctrl-C to stop")

    server = HTTPServer((args.bind, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

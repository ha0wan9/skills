#!/usr/bin/env python3
"""Render a deep-survey-bfs survey into a single self-contained HTML file.

Inputs:
    survey.md           markdown source
    paper_index.md      paper metadata
    claims.jsonl        claim metadata
    chart_data.csv      (optional) chart data for Plotly bindings
    citations.tsv       (optional) Mermaid citation graph edges
    clusters.tsv        (optional) Mermaid cluster groupings

Output:
    one self-contained HTML file with:
      - sticky TOC + scroll-spy
      - tooltip cards for (Pxxx) / (Cxxx) refs
      - search box (FlexSearch when CDN reachable, regex fallback otherwise)
      - sortable tables
      - Plotly charts in place of static PNGs (data injected via __SURVEY_DATA__)
      - Mermaid diagrams rendered client-side
      - dark / light mode + print stylesheet

Usage:
    python3 render_html.py SURVEY_DIR OUT_HTML
                          [--title TITLE] [--fully-offline]
                          [--include-citation-graphs lineage,critique,...]

`SURVEY_DIR` is the directory holding survey.md / paper_index.md / claims.jsonl.
`OUT_HTML` is the path the single HTML file is written to.

`--fully-offline` inlines the third-party libs (mermaid, plotly, flexsearch)
instead of CDN-loading them. Without it, the page CDN-loads at first paint
and degrades gracefully when offline.

`--include-citation-graphs` appends Mermaid graphs (one per view) just before
§14 / §13 — the script reads citations.tsv + clusters.tsv via citation_graph.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import markdown  # type: ignore
except ImportError:
    sys.stderr.write(
        "render_html.py requires the `markdown` library (pip install markdown).\n"
    )
    sys.exit(2)


CDN_LIBS = {
    "mermaid": "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js",
    "plotly":  "https://cdn.plot.ly/plotly-2.35.2.min.js",
    "flexsearch": "https://cdn.jsdelivr.net/npm/flexsearch@0.7.43/dist/flexsearch.bundle.min.js",
}


# ---------- markdown source loaders ----------

def parse_paper_index(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    out: dict[str, dict] = {}
    header: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            if cells and cells[0].lower() == "id":
                header = [c.lower() for c in cells]
            continue
        if cells and cells[0].startswith("---"):
            continue
        if not cells or not re.match(r"^P\d{3,5}$", cells[0]):
            continue
        row = dict(zip(header, cells))
        title = row.get("title (short)") or row.get("title") or cells[0]
        out[cells[0]] = {
            "title": title,
            "authors": row.get("first author") or row.get("authors") or "",
            "inst": row.get("inst") or row.get("institution") or "",
            "year": row.get("year", ""),
            "venue": row.get("venue", ""),
            "stars": row.get("stars", ""),
            "arxiv": row.get("arxiv", ""),
            "repro": row.get("repro", ""),
            "note": row.get("one-line note", ""),
        }
    return out


def parse_claims(path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            cid = obj.get("claim_id")
            if cid:
                out[cid] = obj
    return out


def parse_chart_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- markdown -> html ----------

def render_markdown(md_text: str) -> tuple[str, list[dict]]:
    """Return (html, toc) where toc is a list of {id, level, text}."""
    md = markdown.Markdown(
        extensions=[
            "extra",         # tables, fenced_code, abbreviations, footnotes
            "toc",
            "sane_lists",
            "admonition",
        ],
        extension_configs={
            "toc": {"permalink": True, "permalink_class": "section-anchor", "permalink_title": "link"},
        },
    )
    html = md.convert(md_text)
    toc_tokens = getattr(md, "toc_tokens", []) or []

    flat: list[dict] = []
    def walk(items: list[dict], level: int = 2):
        for it in items:
            if level <= 3:
                flat.append({"id": it["id"], "level": level, "text": it["name"]})
            walk(it.get("children", []) or [], level + 1)
    walk(toc_tokens, 2)
    return html, flat


# ---------- post-processing ----------

PAPER_REF_RE = re.compile(r"\((P\d{3,5})\)")
CLAIM_REF_RE = re.compile(r"\((C\d{3,5})\)")
MERMAID_BLOCK_RE = re.compile(
    r"<pre><code class=\"language-mermaid\">(.*?)</code></pre>", re.DOTALL
)
IMG_TAG_RE = re.compile(r"<img\s+[^>]*src=\"([^\"]+)\"[^>]*/?>")
# Inline `<code>artifacts/0X_*.png</code>` mentions inside a paragraph —
# common in surveys that name chart filenames in prose without ![](). When
# the surrounding paragraph is short enough that promoting it into a chart
# block makes sense, render_html.py replaces the whole paragraph.
CODE_PNG_PARAGRAPH_RE = re.compile(
    r"<p>(?P<pre>.*?)<code>(?P<path>(?:artifacts/)?(?P<digits>\d{2})_[\w./-]+\.png)</code>"
    r"(?P<post>.*?)</p>",
    re.DOTALL,
)


def annotate_refs(html: str, papers: dict[str, dict], claims: dict[str, dict]) -> str:
    def paper_sub(m: re.Match) -> str:
        pid = m.group(1)
        if pid not in papers:
            return m.group(0)
        return f'(<span class="paper-ref" data-id="{pid}">{pid}</span>)'

    def claim_sub(m: re.Match) -> str:
        cid = m.group(1)
        if cid not in claims:
            return m.group(0)
        return f'(<span class="claim-ref" data-id="{cid}">{cid}</span>)'

    html = PAPER_REF_RE.sub(paper_sub, html)
    html = CLAIM_REF_RE.sub(claim_sub, html)
    return html


def transform_mermaid(html: str) -> str:
    def repl(m: re.Match) -> str:
        body = m.group(1)
        # markdown library escapes the body — undo HTML escapes for mermaid
        body = (
            body.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
        )
        return f'<div class="mermaid">{body}</div>'
    return MERMAID_BLOCK_RE.sub(repl, html)


def transform_chart_imgs(html: str, chart_specs: dict[str, dict]) -> str:
    """Replace static chart PNG <img>s and inline `<code>NN_*.png</code>` mentions
    with Plotly placeholders.

    Recognises file names of the form 0X_*.png in artifacts/ and binds them
    to the chart spec keyed on the leading digit prefix ('01', '02', '03').

    For surveys that name chart filenames in prose paragraphs without using
    markdown image syntax, the whole paragraph that mentions the file is
    replaced with the chart placeholder (so the prose explanation, which
    follows in the next paragraph, becomes the caption).
    """
    seen_ids: set[str] = set()

    def img_repl(m: re.Match) -> str:
        src = m.group(1)
        m2 = re.search(r"(\d{2})_", Path(src).name)
        if not m2:
            return m.group(0)
        cid = m2.group(1)
        if cid not in chart_specs:
            return m.group(0)
        seen_ids.add(cid)
        return (
            f'<div class="plotly-chart" data-chart="{cid}">'
            f'<div class="chart-fallback">loading chart {cid}…</div>'
            f'</div>'
        )

    def code_repl(m: re.Match) -> str:
        cid = m.group("digits")
        if cid not in chart_specs or cid in seen_ids:
            return m.group(0)
        seen_ids.add(cid)
        return (
            f'<div class="plotly-chart" data-chart="{cid}">'
            f'<div class="chart-fallback">loading chart {cid}…</div>'
            f'</div>'
        )

    html = IMG_TAG_RE.sub(img_repl, html)
    html = CODE_PNG_PARAGRAPH_RE.sub(code_repl, html)
    return html


# ---------- citation graph injection ----------

def render_citation_graph(survey_dir: Path, view: str) -> str | None:
    citations = survey_dir / "citations.tsv"
    if not citations.is_file():
        return None
    clusters = survey_dir / "clusters.tsv"
    script = Path(__file__).parent / "citation_graph.py"
    cmd = [
        sys.executable, str(script), str(citations), str(survey_dir / "paper_index.md"),
        "--view", view, "--bare",
    ]
    if clusters.is_file():
        cmd += ["--clusters", str(clusters)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"citation_graph.py {view} failed: {e.stderr}\n")
        return None
    return out.strip()


def inject_citation_graphs(html: str, survey_dir: Path, views: list[str]) -> str:
    """Append a citation graphs section before §14 (or end of document)."""
    blocks: list[str] = []
    for v in views:
        body = render_citation_graph(survey_dir, v)
        if not body:
            continue
        blocks.append(
            f'<h3 id="cg-{v}">Citation graph — {v}</h3>'
            f'<div class="mermaid">{body}</div>'
        )
    if not blocks:
        return html
    section = (
        '<h2 id="citation-graphs">Citation graphs <a class="section-anchor" '
        'href="#citation-graphs">¶</a></h2>\n'
        + "\n".join(blocks)
    )
    # Try to insert before the first <h2> whose id starts with "14" or
    # "reproducibility"; otherwise append at end.
    m = re.search(r'<h2 id="(14[\w-]*|reproducibility[\w-]*)"', html)
    if m:
        return html[: m.start()] + section + "\n" + html[m.start():]
    return html + "\n" + section


# ---------- TOC -> nav HTML ----------

def render_toc_html(toc: list[dict]) -> str:
    if not toc:
        return ""
    parts = ['<ul>']
    for h in toc:
        cls = "toc-h2" if h["level"] == 2 else "toc-h3"
        parts.append(f'<li class="{cls}"><a href="#{h["id"]}">{h["text"]}</a></li>')
    parts.append("</ul>")
    return "\n".join(parts)


# ---------- chart specs (read from chart_specs.json or default) ----------

DEFAULT_CHART_SPECS = {
    "01": {
        "title": "Params (M) vs Accuracy (zero-shot Mean ↓)",
        "x": "params_M", "y": "accuracy_inv",
        "x_label": "Params (M)", "y_label": "zero-shot Mean (lower is better)",
        "x_type": "log",
    },
    "02": {
        "title": "Torch latency (ms) vs Accuracy",
        "x": "latency_torch_ms", "y": "accuracy_inv",
        "x_label": "Torch latency (ms)", "y_label": "zero-shot Mean (lower is better)",
        "x_type": "log",
    },
    "03": {
        "title": "TensorRT latency (ms) vs Accuracy",
        "x": "latency_trt_ms", "y": "accuracy_inv",
        "x_label": "TensorRT latency (ms)", "y_label": "zero-shot Mean (lower is better)",
        "x_type": "log",
    },
}


def load_chart_specs(survey_dir: Path) -> dict[str, dict]:
    explicit = survey_dir / "chart_specs.json"
    if explicit.is_file():
        return json.loads(explicit.read_text(encoding="utf-8"))
    return DEFAULT_CHART_SPECS


# ---------- CDN block ----------

def cdn_head_block(fully_offline: bool) -> str:
    if fully_offline:
        return "<!-- fully offline mode: third-party libs inlined in <body> -->"
    return ""


def cdn_body_block(fully_offline: bool, libs_dir: Path | None) -> str:
    if fully_offline and libs_dir is not None:
        # Inline whatever .min.js files exist in libs_dir
        out = []
        for name, _url in CDN_LIBS.items():
            p = libs_dir / f"{name}.min.js"
            if p.is_file():
                out.append(f"<!-- inlined {name} -->\n<script>{p.read_text(encoding='utf-8')}</script>")
        return "\n".join(out)
    return "\n".join(f'<script src="{url}" defer></script>' for url in CDN_LIBS.values())


# ---------- main ----------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("survey_dir", type=Path)
    parser.add_argument("out_html", type=Path)
    parser.add_argument("--title", default=None)
    parser.add_argument("--fully-offline", action="store_true",
                        help="Inline third-party libs from --libs-dir instead of CDN.")
    parser.add_argument("--libs-dir", type=Path, default=None)
    parser.add_argument(
        "--include-citation-graphs",
        default="",
        help="Comma-separated views to append (e.g. lineage,critique,temporal). "
             "Requires citations.tsv in survey_dir.",
    )
    args = parser.parse_args(argv)

    sd = args.survey_dir
    if not sd.is_dir():
        print(f"missing dir: {sd}", file=sys.stderr)
        return 2
    survey_md = sd / "survey.md"
    paper_idx = sd / "paper_index.md"
    if not survey_md.is_file() or not paper_idx.is_file():
        print(f"need survey.md and paper_index.md in {sd}", file=sys.stderr)
        return 2

    papers = parse_paper_index(paper_idx)
    claims = parse_claims(sd / "claims.jsonl")
    chart_data = parse_chart_csv(sd / "artifacts" / "chart_data.csv")
    if not chart_data:
        chart_data = parse_chart_csv(sd / "chart_data.csv")
    chart_specs = load_chart_specs(sd)

    md_text = survey_md.read_text(encoding="utf-8")
    body_html, toc = render_markdown(md_text)
    body_html = transform_mermaid(body_html)
    body_html = transform_chart_imgs(body_html, chart_specs)
    body_html = annotate_refs(body_html, papers, claims)

    if args.include_citation_graphs:
        views = [v.strip() for v in args.include_citation_graphs.split(",") if v.strip()]
        body_html = inject_citation_graphs(body_html, sd, views)

    title = args.title or (re.search(r"^#\s+(.+)$", md_text, re.MULTILINE) or [None, sd.name])[1]
    survey_date = (re.search(r"\*\*Survey date\*\*:?\s*(\S+)", md_text) or [None, _dt.date.today().isoformat()])[1]

    tpl_dir = Path(__file__).parent.parent / "templates" / "html"
    template = (tpl_dir / "survey.html.tpl").read_text(encoding="utf-8")
    styles = (tpl_dir / "styles.css").read_text(encoding="utf-8")
    app_js = (tpl_dir / "app.js").read_text(encoding="utf-8")

    data_payload: dict[str, Any] = {
        "papers": papers,
        "claims": claims,
        "chart_data": chart_data,
        "chart_specs": chart_specs,
        "toc": toc,
    }
    data_json = json.dumps(data_payload, ensure_ascii=False)

    html = (template
            .replace("{{TITLE}}", title or "Survey")
            .replace("{{GENERATED}}", _dt.datetime.now(_dt.timezone.utc).isoformat())
            .replace("{{SURVEY_DATE}}", survey_date)
            .replace("{{PAPER_COUNT}}", str(len(papers)))
            .replace("{{CLAIM_COUNT}}", str(len(claims)))
            .replace("{{TOC_HTML}}", render_toc_html(toc))
            .replace("{{BODY_HTML}}", body_html)
            .replace("{{STYLES_CSS}}", styles)
            .replace("{{APP_JS}}", app_js)
            .replace("{{DATA_JSON}}", data_json)
            .replace("{{CDN_HEAD}}", cdn_head_block(args.fully_offline))
            .replace("{{CDN_BODY}}", cdn_body_block(args.fully_offline, args.libs_dir))
            )

    args.out_html.parent.mkdir(parents=True, exist_ok=True)
    args.out_html.write_text(html, encoding="utf-8")
    size_kb = args.out_html.stat().st_size // 1024
    print(f"wrote {args.out_html} ({size_kb} KB; {len(papers)} papers, "
          f"{len(claims)} claims, {len(toc)} sections, {len(chart_data)} chart rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

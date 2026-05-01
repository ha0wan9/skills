/* deep-survey-bfs HTML viewer client-side runtime
   Reads window.__SURVEY_DATA__ which is injected by render_html.py:
     papers:       { Pxxx: {title, authors, year, venue, stars, repro, arxiv, ...}, ... }
     claims:       { Cxxx: {paper_id, kind, section, quote, confidence, depends_on, ...}, ... }
     chart_data:   array of rows from chart_data.csv (key/value objects)
     chart_specs:  { chart_id: {title, x, y, hover_template, ...} }
     toc:          [{id, level, text}, ...]
*/
(function () {
  "use strict";
  const data = window.__SURVEY_DATA__ || { papers: {}, claims: {}, chart_data: [], chart_specs: {}, toc: [] };

  /* ---------- theme toggle ---------- */
  const themeBtn = document.getElementById("theme-toggle");
  const root = document.documentElement;
  const stored = localStorage.getItem("dsb-theme");
  if (stored) root.dataset.theme = stored;
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      localStorage.setItem("dsb-theme", next);
      // Re-render mermaid + plotly to pick up theme
      reRenderMermaid();
      reRenderPlotly();
    });
  }

  /* ---------- tooltip ---------- */
  const tip = document.getElementById("tooltip");
  function showTooltip(el, html) {
    tip.innerHTML = html;
    tip.setAttribute("aria-hidden", "false");
    const rect = el.getBoundingClientRect();
    const tipRect = tip.getBoundingClientRect();
    const margin = 6;
    let top = rect.bottom + window.scrollY + margin;
    let left = rect.left + window.scrollX;
    if (left + tipRect.width > window.scrollX + window.innerWidth - 12) {
      left = window.scrollX + window.innerWidth - tipRect.width - 12;
    }
    if (top + tipRect.height > window.scrollY + window.innerHeight - 12) {
      top = rect.top + window.scrollY - tipRect.height - margin;
    }
    tip.style.top = top + "px";
    tip.style.left = left + "px";
  }
  function hideTooltip() { tip.setAttribute("aria-hidden", "true"); }

  function paperCardHTML(pid) {
    const p = data.papers[pid];
    if (!p) return `<div class="t-title">${pid}</div><div class="t-meta">unknown paper</div>`;
    const stars = p.stars || "";
    const venue = [p.year, p.venue].filter(Boolean).join(" · ");
    const arxiv = p.arxiv ? `<a class="t-link" href="https://arxiv.org/abs/${p.arxiv}" target="_blank" rel="noopener">arXiv:${p.arxiv}</a>` : "";
    const repro = p.repro && p.repro !== "pending" ? `<div class="t-meta">Repro: ${escapeHtml(p.repro)}</div>` : "";
    return `<div class="t-title">${pid} ${stars} ${escapeHtml(p.title || "")}</div>
            <div class="t-meta">${escapeHtml(venue)}${p.authors ? " · " + escapeHtml(p.authors) : ""}</div>
            ${repro}
            ${arxiv}`;
  }
  function claimCardHTML(cid) {
    const c = data.claims[cid];
    if (!c) return `<div class="t-title">${cid}</div><div class="t-meta">unknown claim</div>`;
    const paper = data.papers[c.paper_id] || {};
    const kind = c.kind ? `<span style="background:rgba(255,255,255,0.12);padding:1px 5px;border-radius:3px;">${escapeHtml(c.kind)}</span>` : "";
    const conf = c.confidence ? ` · confidence: ${escapeHtml(c.confidence)}` : "";
    const truncated = (c.quote || "").slice(0, 280) + ((c.quote || "").length > 280 ? "…" : "");
    return `<div class="t-title">${cid} ${kind}</div>
            <div class="t-meta">${c.paper_id}${paper.title ? " — " + escapeHtml(paper.title) : ""} · ${escapeHtml(c.section || "")}${conf}</div>
            <div class="t-quote">${escapeHtml(truncated)}</div>`;
  }
  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[ch]));
  }

  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest(".paper-ref, .claim-ref");
    if (!el) return;
    const isPaper = el.classList.contains("paper-ref");
    const id = el.dataset.id;
    if (!id) return;
    showTooltip(el, isPaper ? paperCardHTML(id) : claimCardHTML(id));
  });
  document.addEventListener("mouseout", (e) => {
    const el = e.target.closest(".paper-ref, .claim-ref");
    if (el) hideTooltip();
  });
  document.addEventListener("scroll", hideTooltip, { passive: true });

  /* ---------- TOC scroll-spy ---------- */
  const tocLinks = Array.from(document.querySelectorAll(".toc a"));
  const headings = tocLinks
    .map(a => document.getElementById(a.getAttribute("href").slice(1)))
    .filter(Boolean);
  function updateActiveTOC() {
    const y = window.scrollY + 100;
    let active = headings[0];
    for (const h of headings) {
      if (h.offsetTop <= y) active = h;
      else break;
    }
    tocLinks.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + active.id));
  }
  if (headings.length) {
    window.addEventListener("scroll", updateActiveTOC, { passive: true });
    updateActiveTOC();
  }

  /* ---------- search (FlexSearch when available, fallback to regex) ---------- */
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  let searchIndex = null;

  function buildSearchEntries() {
    const entries = [];
    Object.entries(data.papers).forEach(([pid, p]) => {
      entries.push({
        id: "paper:" + pid,
        kind: "paper",
        title: pid + " " + (p.title || ""),
        body: [p.authors, p.venue, p.year, p.note].filter(Boolean).join(" "),
        anchor: "paper-" + pid
      });
    });
    Object.entries(data.claims).forEach(([cid, c]) => {
      entries.push({
        id: "claim:" + cid,
        kind: "claim",
        title: cid + " (" + (c.paper_id || "") + ")",
        body: (c.quote || "") + " " + (c.section || ""),
        anchor: "claim-" + cid
      });
    });
    (data.toc || []).forEach((h) => {
      entries.push({ id: "section:" + h.id, kind: "section", title: h.text, body: "", anchor: h.id });
    });
    return entries;
  }
  const entries = buildSearchEntries();
  if (window.FlexSearch && entries.length) {
    searchIndex = new FlexSearch.Document({
      tokenize: "forward",
      document: { id: "id", index: ["title", "body"], store: ["kind", "title", "body", "anchor"] }
    });
    entries.forEach(e => searchIndex.add(e));
  }
  function fallbackSearch(q) {
    const re = new RegExp(q.split(/\s+/).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"), "i");
    return entries.filter(e => re.test(e.title) || re.test(e.body)).slice(0, 30);
  }
  function flexSearchQuery(q) {
    const out = [];
    const seen = new Set();
    const results = searchIndex.search(q, { limit: 25, enrich: true });
    results.forEach(field => {
      field.result.forEach(r => {
        if (seen.has(r.id)) return;
        seen.add(r.id);
        out.push(r.doc);
      });
    });
    return out.slice(0, 30);
  }
  function renderResults(items, q) {
    if (!items.length) {
      searchResults.innerHTML = `<div class="res"><span class="res-snippet">no matches</span></div>`;
    } else {
      searchResults.innerHTML = items.map(it => {
        const snippet = (it.body || "").slice(0, 140);
        return `<div class="res" data-anchor="${it.anchor}">
                  <span class="res-kind">${it.kind}</span>
                  <span class="res-title">${escapeHtml(it.title)}</span>
                  <div class="res-snippet">${escapeHtml(snippet)}</div>
                </div>`;
      }).join("");
    }
    searchResults.hidden = false;
  }
  let searchTimer = null;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.trim();
      clearTimeout(searchTimer);
      if (!q) { searchResults.hidden = true; return; }
      searchTimer = setTimeout(() => {
        const items = searchIndex ? flexSearchQuery(q) : fallbackSearch(q);
        renderResults(items, q);
      }, 100);
    });
    searchInput.addEventListener("blur", () => setTimeout(() => searchResults.hidden = true, 200));
    searchInput.addEventListener("focus", () => { if (searchInput.value.trim()) searchResults.hidden = false; });
  }
  if (searchResults) {
    searchResults.addEventListener("mousedown", (e) => {
      const r = e.target.closest(".res");
      if (!r) return;
      const a = r.dataset.anchor;
      if (a) {
        const target = document.getElementById(a);
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      searchResults.hidden = true;
    });
  }

  /* ---------- sortable tables ---------- */
  document.querySelectorAll(".content table").forEach(tbl => {
    const ths = tbl.tHead ? Array.from(tbl.tHead.rows[0].cells) : [];
    if (!ths.length || !tbl.tBodies[0]) return;
    ths.forEach((th, idx) => {
      th.classList.add("sortable");
      th.addEventListener("click", () => {
        const tbody = tbl.tBodies[0];
        const rows = Array.from(tbody.rows);
        const dir = th.classList.contains("sort-asc") ? -1 : 1;
        ths.forEach(t => t.classList.remove("sort-asc", "sort-desc"));
        th.classList.add(dir === 1 ? "sort-asc" : "sort-desc");
        rows.sort((a, b) => {
          const av = a.cells[idx] ? a.cells[idx].textContent.trim() : "";
          const bv = b.cells[idx] ? b.cells[idx].textContent.trim() : "";
          const an = parseFloat(av), bn = parseFloat(bv);
          if (!isNaN(an) && !isNaN(bn)) return (an - bn) * dir;
          return av.localeCompare(bv) * dir;
        });
        rows.forEach(r => tbody.appendChild(r));
      });
    });
  });

  /* ---------- mermaid ---------- */
  function reRenderMermaid() {
    if (!window.mermaid) return;
    document.querySelectorAll(".mermaid").forEach(el => {
      if (el.dataset.processed === "true") {
        // Mermaid v10+ does not auto re-render; replace with original source.
        if (el.dataset.src) {
          el.innerHTML = el.dataset.src;
          el.removeAttribute("data-processed");
        }
      } else {
        el.dataset.src = el.textContent;
      }
    });
    try {
      window.mermaid.initialize({
        startOnLoad: false,
        theme: root.dataset.theme === "dark" ? "dark" : "default",
        securityLevel: "loose",
        flowchart: { htmlLabels: true, curve: "basis" }
      });
      window.mermaid.run({ querySelector: ".mermaid:not([data-processed=true])" });
    } catch (e) { console.warn("mermaid render failed", e); }
  }
  if (window.mermaid) {
    document.querySelectorAll(".mermaid").forEach(el => { el.dataset.src = el.textContent; });
    reRenderMermaid();
  } else {
    document.querySelectorAll(".mermaid").forEach(el => {
      const fallback = document.createElement("div");
      fallback.className = "chart-fallback";
      fallback.textContent = "(Mermaid not loaded — diagram source below)";
      el.parentNode.insertBefore(fallback, el);
    });
  }

  /* ---------- plotly charts ---------- */
  function reRenderPlotly() {
    if (!window.Plotly) return;
    document.querySelectorAll(".plotly-chart").forEach(div => {
      const cid = div.dataset.chart;
      const spec = (data.chart_specs || {})[cid];
      if (!spec) return;
      const rows = (data.chart_data || []).filter(r => !spec.filter || spec.filter.split(",").every(f => {
        const [k, v] = f.split("=");
        return String(r[k] || "") === v;
      }));
      const xField = spec.x, yField = spec.y;
      const x = rows.map(r => parseFloat(r[xField])).map(v => isNaN(v) ? null : v);
      const y = rows.map(r => parseFloat(r[yField])).map(v => isNaN(v) ? null : v);
      const text = rows.map(r => {
        const parts = [r.paper_id, r.model, r.architecture];
        if (r.hardware) parts.push(r.hardware);
        return parts.filter(Boolean).join(" · ");
      });
      const dark = root.dataset.theme === "dark";
      const layout = {
        title: spec.title || "",
        xaxis: { title: spec.x_label || xField, type: spec.x_type || "linear" },
        yaxis: { title: spec.y_label || yField, type: spec.y_type || "linear" },
        margin: { t: 40, l: 60, r: 20, b: 50 },
        paper_bgcolor: dark ? "#18181b" : "#f7f7f4",
        plot_bgcolor: dark ? "#0a0a0a" : "#ffffff",
        font: { color: dark ? "#e4e4e7" : "#18181b", size: 12 },
        hovermode: "closest"
      };
      const trace = {
        type: "scatter", mode: "markers+text",
        x, y, text,
        textposition: "top center",
        textfont: { size: 10 },
        marker: { size: 12, color: spec.color || (dark ? "#60a5fa" : "#2563eb"), line: { width: 1, color: dark ? "#27272a" : "#e4e4e7" } },
        hovertemplate: "<b>%{text}</b><br>" + (spec.x_label || xField) + ": %{x}<br>" + (spec.y_label || yField) + ": %{y}<extra></extra>"
      };
      try {
        window.Plotly.newPlot(div, [trace], layout, { displaylogo: false, responsive: true });
      } catch (e) { console.warn("plotly render failed", cid, e); }
    });
  }
  if (window.Plotly) reRenderPlotly();
  else {
    document.querySelectorAll(".plotly-chart").forEach(div => {
      div.innerHTML = `<div class="chart-fallback">(Plotly not loaded — chart data available in __SURVEY_DATA__.chart_data)</div>`;
    });
  }
})();

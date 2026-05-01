<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{TITLE}}</title>
  <meta name="generator" content="deep-survey-bfs render_html.py" />
  <meta name="generated" content="{{GENERATED}}" />

  {{CDN_HEAD}}

  <style>
{{STYLES_CSS}}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{TITLE}}</span>
      <span class="topbar-meta">{{SURVEY_DATE}} · {{PAPER_COUNT}} papers · {{CLAIM_COUNT}} claims</span>
    </div>
    <div class="topbar-right">
      <input type="search" id="search-input" placeholder="Search papers, claims, sections…" autocomplete="off" />
      <button id="theme-toggle" title="Toggle dark mode" aria-label="Toggle dark mode">◐</button>
    </div>
  </header>

  <div id="search-results" class="search-results" hidden></div>

  <div class="layout">
    <nav class="toc" aria-label="Table of contents">
      <div class="toc-title">Contents</div>
      {{TOC_HTML}}
    </nav>

    <main class="content" id="content">
      {{BODY_HTML}}
    </main>
  </div>

  <div id="tooltip" class="tooltip" role="tooltip" aria-hidden="true"></div>

  <script>
    window.__SURVEY_DATA__ = {{DATA_JSON}};
  </script>

  {{CDN_BODY}}

  <script>
{{APP_JS}}
  </script>
</body>
</html>

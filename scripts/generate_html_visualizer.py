"""Generate a standalone interactive HTML visualizer for all Mermaid workflow graphs."""

import json
import os
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "out"

    graphs: dict[str, str] = {}
    for path in sorted(out_dir.rglob("*.mmd")):
        rel_path = path.relative_to(out_dir).as_posix()
        graphs[rel_path] = path.read_text(encoding="utf-8")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESP to Airflow 3 - Interactive Workflow Graph Visualizer</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b0f19;
      --sidebar-bg: #111827;
      --card-bg: #1f2937;
      --text: #f9fafb;
      --text-muted: #9ca3af;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --border: #374151;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', sans-serif;
      background-color: var(--bg);
      color: var(--text);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }}
    #sidebar {{
      width: 320px;
      background-color: var(--sidebar-bg);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
    }}
    #header {{
      padding: 1.25rem;
      border-bottom: 1px solid var(--border);
    }}
    #header h1 {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 0.25rem;
    }}
    #header p {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
    #search-box {{
      margin: 1rem 1.25rem 0.5rem;
      padding: 0.5rem 0.75rem;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text);
      font-size: 0.85rem;
      outline: none;
    }}
    #search-box:focus {{ border-color: var(--accent); }}
    #graph-list {{
      flex: 1;
      overflow-y: auto;
      padding: 0.5rem 1.25rem 1.25rem;
      list-style: none;
    }}
    .group-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--accent);
      margin: 1rem 0 0.5rem;
      font-weight: 600;
    }}
    .graph-item {{
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.85rem;
      cursor: pointer;
      color: var(--text-muted);
      transition: all 0.15s ease;
      margin-bottom: 2px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .graph-item:hover {{
      background-color: rgba(56, 189, 248, 0.1);
      color: var(--text);
    }}
    .graph-item.active {{
      background-color: var(--accent);
      color: #0b0f19;
      font-weight: 600;
    }}
    #content {{
      flex: 1;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    #toolbar {{
      padding: 0.75rem 1.5rem;
      background: var(--sidebar-bg);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    #current-title {{
      font-size: 1rem;
      font-weight: 600;
      color: var(--text);
    }}
    .btn-group {{ display: flex; gap: 0.5rem; }}
    .btn {{
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
      font-weight: 500;
      transition: all 0.15s ease;
    }}
    .btn:hover {{ background: var(--border); color: var(--accent); }}
    #diagram-container {{
      flex: 1;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      background: radial-gradient(circle at center, #1f2937 0%, #0b0f19 100%);
    }}
    #diagram-wrapper {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
  </style>
</head>
<body>
  <div id="sidebar">
    <div id="header">
      <h1>ESP → Airflow 3</h1>
      <p>Interactive Graph Visualizer</p>
    </div>
    <input type="text" id="search-box" placeholder="Filter workflows..." oninput="filterList()">
    <ul id="graph-list"></ul>
  </div>
  <div id="content">
    <div id="toolbar">
      <span id="current-title">Select a workflow</span>
      <div class="btn-group">
        <button class="btn" onclick="zoomIn()">Zoom In (+)</button>
        <button class="btn" onclick="zoomOut()">Zoom Out (-)</button>
        <button class="btn" onclick="resetZoom()">Reset View</button>
      </div>
    </div>
    <div id="diagram-container">
      <div id="diagram-wrapper"><div id="mermaid-diagram"></div></div>
    </div>
  </div>

  <script>
    const graphs = {json.dumps(graphs)};
    let currentPanZoom = null;

    mermaid.initialize({{
      startOnLoad: false,
      theme: 'dark',
      flowchart: {{ curve: 'basis', htmlLabels: true }},
      themeVariables: {{
        darkMode: true,
        background: '#0b0f19',
        primaryColor: '#38bdf8',
        primaryBorderColor: '#0284c7',
        primaryTextColor: '#f9fafb',
        lineColor: '#9ca3af'
      }}
    }});

    function init() {{
      const listEl = document.getElementById('graph-list');
      const groups = {{}};
      
      for (const path of Object.keys(graphs)) {{
        const parts = path.split('/');
        const group = parts.length > 1 ? parts[0] : 'General';
        if (!groups[group]) groups[group] = [];
        groups[group].push(path);
      }}

      for (const [group, items] of Object.entries(groups)) {{
        const title = document.createElement('div');
        title.className = 'group-title';
        title.textContent = group.replace(/_/g, ' ');
        listEl.appendChild(title);

        for (const path of items) {{
          const li = document.createElement('li');
          li.className = 'graph-item';
          li.dataset.path = path;
          const name = path.split('/').pop().replace('.mmd', '');
          li.textContent = name;
          li.onclick = () => loadGraph(path, li);
          listEl.appendChild(li);
        }}
      }}

      const firstItem = document.querySelector('.graph-item');
      if (firstItem) firstItem.click();
    }}

    async function loadGraph(path, el) {{
      document.querySelectorAll('.graph-item').forEach(i => i.classList.remove('active'));
      if (el) el.classList.add('active');

      document.getElementById('current-title').textContent = path;
      const raw = graphs[path];
      const wrapper = document.getElementById('diagram-wrapper');
      wrapper.innerHTML = '<div id="mermaid-diagram">' + raw + '</div>';

      try {{
        const id = 'svg-' + Math.random().toString(36).substr(2, 9);
        const {{ svg }} = await mermaid.render(id, raw);
        wrapper.innerHTML = svg;
        const svgEl = wrapper.querySelector('svg');
        if (svgEl) {{
          svgEl.style.width = '100%';
          svgEl.style.height = '100%';
          if (currentPanZoom) currentPanZoom.destroy();
          currentPanZoom = svgPanZoom(svgEl, {{
            zoomEnabled: true,
            controlIconsEnabled: false,
            fit: true,
            center: true,
            minZoom: 0.2,
            maxZoom: 10
          }});
        }}
      }} catch (err) {{
        console.error('Mermaid render error:', err);
        wrapper.innerHTML = '<pre style="color: #ef4444; padding: 2rem;">Render error: ' + err.message + '</pre>';
      }}
    }}

    function zoomIn() {{ if (currentPanZoom) currentPanZoom.zoomIn(); }}
    function zoomOut() {{ if (currentPanZoom) currentPanZoom.zoomOut(); }}
    function resetZoom() {{ if (currentPanZoom) {{ currentPanZoom.resetZoom(); currentPanZoom.center(); }} }}

    function filterList() {{
      const q = document.getElementById('search-box').value.toLowerCase();
      document.querySelectorAll('.graph-item').forEach(item => {{
        item.style.display = item.textContent.toLowerCase().includes(q) ? 'flex' : 'none';
      }});
    }}

    window.onload = init;
  </script>
</body>
</html>"""

    viewer_path = out_dir / "graph_viewer.html"
    viewer_path.write_text(html, encoding="utf-8")
    print(f"Generated {viewer_path} ({len(graphs)} graphs)")


if __name__ == "__main__":
    main()

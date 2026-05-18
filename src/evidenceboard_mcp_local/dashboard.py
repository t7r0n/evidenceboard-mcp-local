from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jinja2 import Environment, select_autoescape

from evidenceboard_mcp_local.models import RunSummary, project_root
from evidenceboard_mcp_local.runner import outputs_dir, run_suite


TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Evidenceboard MCP Dashboard</title>
  <style>
    :root { color-scheme: light; --bg:#f8faf8; --panel:#fff; --text:#17211d; --muted:#64706b; --line:#dde8e2; --green:#2d9b72; --blue:#426fd2; --red:#d85858; --amber:#c48a2c; --track:#ecf2ef; }
    html[data-theme="dark"] { color-scheme: dark; --bg:#101513; --panel:#18201d; --text:#eef6f1; --muted:#a6b3ad; --line:#2d3934; --track:#27322e; }
    * { box-sizing: border-box; }
    body { margin:0; overflow-x:hidden; background:var(--bg); color:var(--text); font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    main { max-width:1160px; margin:0 auto; padding:32px 20px 48px; }
    header { display:flex; justify-content:space-between; gap:16px; align-items:end; margin-bottom:26px; }
    h1 { margin:0 0 8px; font-size:32px; line-height:1.08; letter-spacing:0; }
    h2 { margin:0 0 14px; font-size:22px; letter-spacing:0; }
    p { margin:0; color:var(--muted); }
    .header-actions { display:flex; align-items:center; gap:10px; }
    .pill { border:1px solid var(--line); border-radius:999px; padding:8px 12px; color:var(--muted); font-size:13px; white-space:nowrap; }
    .theme-toggle { border:1px solid var(--line); border-radius:999px; padding:8px 12px; background:var(--panel); color:var(--text); font:inherit; font-size:13px; cursor:pointer; }
    .grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; }
    .metric span { color:var(--muted); font-size:13px; }
    .metric strong { display:block; margin-top:8px; font-size:28px; }
    .wide { grid-column:span 2; }
    .full { grid-column:1/-1; }
    .bar { display:grid; grid-template-columns:140px 1fr 52px; gap:12px; align-items:center; margin:12px 0; }
    .track { height:13px; border-radius:999px; background:var(--track); overflow:hidden; }
    .fill { height:100%; border-radius:999px; background:var(--blue); }
    .table-wrap { width:100%; overflow-x:auto; }
    table { width:100%; border-collapse:collapse; margin-top:8px; font-size:14px; }
    th,td { text-align:left; border-bottom:1px solid var(--line); padding:11px 8px; vertical-align:top; }
    th { color:var(--muted); font-weight:600; }
    .ok { color:var(--green); font-weight:700; }
    .bad { color:var(--red); font-weight:700; }
    @media (max-width:840px) { header { display:block; } .header-actions { margin-top:16px; } .grid { grid-template-columns:1fr; } .wide { grid-column:auto; } }
  </style>
  <script>
    const savedTheme = localStorage.getItem("evidenceboard-theme") || "light";
    document.documentElement.dataset.theme = savedTheme;
    function toggleTheme() {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("evidenceboard-theme", next);
      document.querySelector(".theme-toggle").textContent = next === "dark" ? "Light" : "Dark";
    }
    window.addEventListener("DOMContentLoaded", () => {
      document.querySelector(".theme-toggle").textContent =
        document.documentElement.dataset.theme === "dark" ? "Light" : "Dark";
    });
  </script>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Evidenceboard MCP Dashboard</h1>
      <p>Evidence-first product feedback tools with citations and prompt-injection-safe notes.</p>
    </div>
    <div class="header-actions">
      <button class="theme-toggle" type="button" onclick="toggleTheme()">Dark</button>
      <div class="pill">Run {{ summary.run_id }}</div>
    </div>
  </header>
  <section class="grid">
    <div class="panel metric"><span>Tool results</span><strong>{{ summary.result_count }}</strong></div>
    <div class="panel metric"><span>Citation accuracy</span><strong>{{ "%.0f"|format(summary.citation_accuracy * 100) }}%</strong></div>
    <div class="panel metric"><span>Sanitizer block</span><strong>{{ "%.0f"|format(summary.sanitizer_block_rate * 100) }}%</strong></div>
    <div class="panel metric"><span>p95 latency</span><strong>{{ summary.p95_latency_ms }} ms</strong></div>
    <div class="panel wide">
      <h2>Tool Mix</h2>
      {% for label, count in tool_rows %}
      <div class="bar"><span>{{ label }}</span><div class="track"><div class="fill" style="width: {{ widths[label] }}%"></div></div><strong>{{ count }}</strong></div>
      {% endfor %}
    </div>
    <div class="panel wide">
      <h2>Safety Gates</h2>
      <div class="table-wrap">
        <table>
          <tbody>
            {% for gate, ok in gates.items() %}
            <tr><td>{{ gate }}</td><td class="{{ 'ok' if ok else 'bad' }}">{{ "PASS" if ok else "FAIL" }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    <div class="panel full">
      <h2>Representative Evidence</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tool</th><th>Subject</th><th>Answer</th><th>Evidence IDs</th></tr></thead>
          <tbody>
            {% for item in sample %}
            <tr><td>{{ item.tool }}</td><td>{{ item.subject_id }}</td><td>{{ item.answer }}</td><td>{{ item.evidence_ids }}</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </section>
</main>
</body>
</html>
"""


def build_dashboard() -> Path:
    if not (outputs_dir() / "summary.json").exists():
        run_suite()
    summary = RunSummary.model_validate_json((outputs_dir() / "summary.json").read_text(encoding="utf-8"))
    results = json.loads((outputs_dir() / "tool_results.json").read_text(encoding="utf-8"))
    counts = Counter(item["tool"] for item in results)
    max_count = max(counts.values()) if counts else 1
    widths = {tool: round(count / max_count * 100, 2) for tool, count in counts.items()}
    gates = {
        "Every result has citations": summary.citation_accuracy == 1.0,
        "Sanitizer exercised and blocks hostile text": summary.sanitizer_block_rate == 1.0,
        "p95 latency below 600 ms": summary.p95_latency_ms < 600,
        "No feature lacks evidence": summary.missing_evidence_flags == 0,
        "Overall pass": summary.pass_gates,
    }
    sample = [
        {
            "tool": item["tool"],
            "subject_id": item["subject_id"],
            "answer": item["answer"],
            "evidence_ids": ", ".join(span["note_id"] for span in item["_evidence"][:4]),
        }
        for item in results[:8]
    ]
    env = Environment(autoescape=select_autoescape(enabled_extensions=("html", "xml")), trim_blocks=True, lstrip_blocks=True)
    html = env.from_string(TEMPLATE).render(
        summary=summary,
        tool_rows=counts.most_common(),
        widths=widths,
        gates=gates,
        sample=sample,
    )
    path = project_root() / "outputs" / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path

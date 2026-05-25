"""
Self-contained HTML report generator for the stateful DAST audit lab.

Reads findings.jsonl (active suite) and cerberus_findings.jsonl (passive
observer) and produces a single HTML file with an executive summary, charts
(Chart.js via CDN) and a detailed finding table. Output is meant for both
browser viewing and Ctrl+P -> "Save as PDF".
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parent.parent / "lab" / "reports"
OUTPUT_FILE = REPORTS_DIR / "audit_report.html"

SEVERITY_COLORS = {
    "Critical": "#7f1d1d",
    "High":     "#dc2626",
    "Medium":   "#d97706",
    "Low":      "#16a34a",
    "Info":     "#2563eb",
}

SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Info"]

PROJECT_TITLE = "Steamworks DAST Lab — Technical Audit Report"
PROJECT_SUBTITLE = (
    "Stateful DAST methodology for auditing Steamworks integrations"
)
PROJECT_AUTHOR = "Paula Romero Gallart"
PROJECT_INST = (
    "Universidad Europea de Madrid — "
    "Double Degree in Video Game Design and Computer Engineering"
)
PROJECT_DIRECTOR = "Project director: José Javier Ruiz Cobo"


# ---------- load ----------

def load_findings() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    sources = (
        ("findings.jsonl",          "Active suite"),
        ("cerberus_findings.jsonl", "Cerberus (passive)"),
    )
    for fname, label in sources:
        fpath = REPORTS_DIR / fname
        if not fpath.exists():
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data["_source"] = label
                findings.append(data)
    return findings


def status_of(f: dict[str, Any]) -> str:
    """Normalises 'confirmed'/'observed' status across formats.

    The active suite and the Cerberus addon both use a boolean ``confirmed``
    field; older payloads use ``status``. We handle all three cases.
    """
    if "confirmed" in f:
        label = "confirmed" if f["confirmed"] else "observed"
    else:
        label = str(f.get("status", "observed")).lower()
    return label


def stats(findings: list[dict[str, Any]]) -> dict[str, Counter]:
    return {
        "severity": Counter(f.get("severity", "Info") for f in findings),
        "category": Counter(f.get("owasp_category", "Unknown") for f in findings),
        "status":   Counter(status_of(f) for f in findings),
        "source":   Counter(f.get("_source", "Unknown") for f in findings),
    }


# ---------- HTML helpers ----------

def fmt_evidence(evidence: Any) -> str:
    try:
        formatted = escape(json.dumps(evidence, indent=2, ensure_ascii=False))
    except Exception:
        formatted = escape(str(evidence))
    return formatted


def render_row(idx: int, f: dict[str, Any]) -> str:
    sev = f.get("severity", "Info")
    sev_color = SEVERITY_COLORS.get(sev, "#64748b")
    status = status_of(f)
    badge_class = "badge--confirmed" if status == "confirmed" else "badge--observed"
    status_label = status.upper()

    return f"""
    <tr>
      <td class="num">{idx}</td>
      <td><span class="source">{escape(str(f.get("_source", "")))}</span></td>
      <td><strong>{escape(str(f.get("vulnerability", "Unknown")))}</strong></td>
      <td><span class="sev" style="background:{sev_color}">{escape(sev)}</span></td>
      <td class="owasp">{escape(str(f.get("owasp_category", "")))}</td>
      <td><span class="badge {badge_class}">{status_label}</span></td>
      <td><code>{escape(str(f.get("endpoint", "")))}</code></td>
    </tr>
    <tr class="evidence-row">
      <td colspan="7">
        <details>
          <summary>Technical evidence &amp; mitigation</summary>
          <pre>{fmt_evidence(f.get("evidence", {}))}</pre>
          <p class="mitigation"><strong>Mitigation:</strong> {escape(str(f.get("mitigation", "See thesis.")))}</p>
        </details>
      </td>
    </tr>
    """


# ---------- page ----------

def build_html(findings: list[dict[str, Any]]) -> str:
    s = stats(findings)
    total = len(findings)
    confirmed = s["status"].get("confirmed", 0)
    observed = total - confirmed
    n_categories = len(s["category"])

    sev_labels = [k for k in SEVERITY_ORDER if k in s["severity"]]
    sev_values = [s["severity"][k] for k in sev_labels]
    sev_colors = [SEVERITY_COLORS.get(k, "#64748b") for k in sev_labels]

    cat_items = s["category"].most_common()
    cat_labels = [c[0] for c in cat_items]
    cat_values = [c[1] for c in cat_items]

    rows = "\n".join(render_row(i + 1, f) for i, f in enumerate(findings))
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(PROJECT_TITLE)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --ink:        #0f172a;
    --ink-soft:   #475569;
    --muted:      #94a3b8;
    --surface:    #f8fafc;
    --panel:      #ffffff;
    --border:     #e2e8f0;
    --accent:     #2563eb;
    --accent-dim: #1d4ed8;
    --ok:         #16a34a;
    --warn:       #d97706;
    --err:        #dc2626;
  }}

  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--surface);
    color: var(--ink);
    line-height: 1.55;
  }}

  /* ---------- header ---------- */
  header.report-header {{
    background:
      radial-gradient(circle at 95% 10%, rgba(37,99,235,0.35), transparent 55%),
      linear-gradient(120deg, #0f172a 0%, #1e293b 60%, #1e3a8a 100%);
    color: #f8fafc;
    padding: 2.5rem 3rem 2.25rem;
  }}
  .report-header .eyebrow {{
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.72rem;
    color: #bfdbfe;
    margin-bottom: 0.5rem;
  }}
  .report-header h1 {{
    margin: 0;
    font-size: 1.85rem;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}
  .report-header h2 {{
    margin: 0.4rem 0 1.25rem;
    font-size: 1.05rem;
    font-weight: 400;
    color: #e2e8f0;
  }}
  .report-header .meta {{
    display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem;
    font-size: 0.85rem; color: #cbd5e1;
  }}
  .report-header .meta span strong {{ color: #ffffff; }}

  /* ---------- layout ---------- */
  main {{
    max-width: 1240px;
    margin: -2rem auto 3rem;
    padding: 0 2rem;
  }}
  section.card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 24px -16px rgba(15, 23, 42, 0.25);
  }}
  section.card h3 {{
    margin: 0 0 1rem;
    font-size: 1.05rem;
    color: var(--ink);
    display: flex; align-items: center; gap: 0.6rem;
  }}
  section.card h3::before {{
    content: ""; display: inline-block;
    width: 6px; height: 22px; border-radius: 3px;
    background: var(--accent);
  }}

  /* ---------- KPIs ---------- */
  .kpis {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
  }}
  .kpi {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    position: relative;
    overflow: hidden;
  }}
  .kpi::after {{
    content: ""; position: absolute;
    top: 0; left: 0; height: 3px; width: 100%;
    background: var(--accent);
  }}
  .kpi.kpi--err::after  {{ background: var(--err); }}
  .kpi.kpi--warn::after {{ background: var(--warn); }}
  .kpi.kpi--ok::after   {{ background: var(--ok); }}

  .kpi .label {{
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: var(--ink-soft);
    margin-bottom: 0.35rem;
  }}
  .kpi .value {{
    font-size: 2.1rem;
    font-weight: 700;
    color: var(--ink);
    line-height: 1.05;
  }}
  .kpi.kpi--err  .value {{ color: var(--err); }}
  .kpi.kpi--warn .value {{ color: var(--warn); }}
  .kpi.kpi--ok   .value {{ color: var(--ok); }}
  .kpi .hint {{
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 0.4rem;
  }}

  /* ---------- charts ---------- */
  .charts-grid {{
    display: grid;
    grid-template-columns: 1.1fr 1.4fr;
    gap: 1.25rem;
  }}
  .chart-frame {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem 1.25rem 1.25rem;
    min-height: 280px;
    position: relative;
  }}
  .chart-frame h4 {{
    margin: 0 0 0.75rem;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-soft);
  }}
  .chart-frame canvas {{ max-height: 240px; }}

  /* ---------- table ---------- */
  .table-wrap {{ overflow-x: auto; }}
  table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.88rem;
  }}
  th {{
    background: #1e293b;
    color: #f8fafc;
    text-align: left;
    padding: 0.7rem 0.9rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.74rem;
  }}
  th:first-child {{ border-top-left-radius: 8px; }}
  th:last-child  {{ border-top-right-radius: 8px; }}
  td {{
    padding: 0.7rem 0.9rem;
    vertical-align: top;
    border-bottom: 1px solid var(--border);
  }}
  td.num   {{ font-variant-numeric: tabular-nums; color: var(--ink-soft); }}
  td.owasp {{ font-size: 0.78rem; color: var(--ink-soft); }}

  .source {{
    display: inline-block;
    background: #e2e8f0;
    color: var(--ink-soft);
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }}
  .sev {{
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 6px;
    color: #fff;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
  }}
  .badge {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
  }}
  .badge--confirmed {{ background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }}
  .badge--observed  {{ background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }}

  code {{
    background: #f1f5f9;
    color: #1e40af;
    padding: 0.1rem 0.45rem;
    border-radius: 4px;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  }}
  pre {{
    background: #0f172a;
    color: #e2e8f0;
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
    line-height: 1.5;
  }}
  details {{ margin-top: 0.4rem; }}
  summary {{
    cursor: pointer;
    color: var(--accent);
    font-weight: 600;
    user-select: none;
    padding: 0.25rem 0;
  }}
  summary:hover {{ color: var(--accent-dim); }}
  .evidence-row > td {{ background: #fafbfc; }}
  .mitigation {{ font-size: 0.85rem; color: var(--ink-soft); margin: 0.5rem 0 0; }}

  footer.report-footer {{
    text-align: center;
    padding: 2rem 1rem 3rem;
    color: var(--muted);
    font-size: 0.8rem;
  }}
  footer.report-footer a {{
    color: var(--accent);
    text-decoration: none;
  }}
  footer.report-footer a:hover {{ text-decoration: underline; }}

  /* ---------- responsive ---------- */
  @media (max-width: 920px) {{
    .kpis        {{ grid-template-columns: repeat(2, 1fr); }}
    .charts-grid {{ grid-template-columns: 1fr; }}
    main         {{ padding: 0 1rem; }}
    header.report-header {{ padding: 2rem 1.25rem; }}
  }}

  /* ---------- print / PDF ---------- */
  @media print {{
    header.report-header {{
      background: #1e3a8a !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    section.card {{ box-shadow: none; page-break-inside: avoid; }}
    .charts-grid {{ page-break-inside: avoid; }}
    pre {{ white-space: pre-wrap; word-break: break-word; }}
    body {{ background: #ffffff; }}
  }}
</style>
</head>
<body>

<header class="report-header">
  <div class="eyebrow">DAST · OWASP API Security 2023</div>
  <h1>{escape(PROJECT_TITLE)}</h1>
  <h2>{escape(PROJECT_SUBTITLE)}</h2>
  <div class="meta">
    <span><strong>Author:</strong> {escape(PROJECT_AUTHOR)}</span>
    <span><strong>Institution:</strong> {escape(PROJECT_INST)}</span>
    <span><strong>{escape(PROJECT_DIRECTOR)}</strong></span>
    <span><strong>Generated:</strong> {escape(generated)}</span>
  </div>
</header>

<main>

  <section class="card">
    <h3>Executive summary</h3>
    <div class="kpis">
      <div class="kpi">
        <div class="label">Total findings</div>
        <div class="value">{total}</div>
        <div class="hint">Active suite + Cerberus</div>
      </div>
      <div class="kpi kpi--err">
        <div class="label">Confirmed</div>
        <div class="value">{confirmed}</div>
        <div class="hint">Demonstrated impact</div>
      </div>
      <div class="kpi kpi--warn">
        <div class="label">Observed</div>
        <div class="value">{observed}</div>
        <div class="hint">Attack surface detected</div>
      </div>
      <div class="kpi kpi--ok">
        <div class="label">OWASP categories</div>
        <div class="value">{n_categories}</div>
        <div class="hint">API Security Top 10 — 2023</div>
      </div>
    </div>
  </section>

  <section class="card">
    <h3>Distribution</h3>
    <div class="charts-grid">
      <div class="chart-frame">
        <h4>By severity</h4>
        <canvas id="sevChart"></canvas>
      </div>
      <div class="chart-frame">
        <h4>By OWASP API category</h4>
        <canvas id="catChart"></canvas>
      </div>
    </div>
  </section>

  <section class="card">
    <h3>Detailed findings</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Source</th>
            <th>Vulnerability</th>
            <th>Severity</th>
            <th>OWASP</th>
            <th>Status</th>
            <th>Endpoint</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>

</main>

<footer class="report-footer">
  Steamworks DAST Lab · TFG 2025/2026 · UEM ·
  <a href="https://github.com/PaulaR17/TFG_CS-DAST-Integraciones-Steamworks-">repository</a>
  · auto-generated report
</footer>

<script>
  const palette = {{
    grid: 'rgba(15, 23, 42, 0.06)',
    tick: '#475569',
    accent: '#2563eb',
  }};

  const sevChartCtx = document.getElementById('sevChart');
  new Chart(sevChartCtx, {{
    type: 'doughnut',
    data: {{
      labels: {json.dumps(sev_labels, ensure_ascii=False)},
      datasets: [{{
        data: {json.dumps(sev_values)},
        backgroundColor: {json.dumps(sev_colors)},
        borderColor: '#ffffff',
        borderWidth: 2,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {{
        legend: {{
          position: 'right',
          labels: {{ color: palette.tick, font: {{ size: 12 }}, boxWidth: 14 }}
        }},
      }}
    }}
  }});

  const catChartCtx = document.getElementById('catChart');
  new Chart(catChartCtx, {{
    type: 'bar',
    data: {{
      labels: {json.dumps(cat_labels, ensure_ascii=False)},
      datasets: [{{
        label: 'Findings',
        data: {json.dumps(cat_values)},
        backgroundColor: palette.accent,
        borderRadius: 6,
        maxBarThickness: 28,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{
          beginAtZero: true,
          ticks: {{ color: palette.tick, stepSize: 1, precision: 0 }},
          grid: {{ color: palette.grid }}
        }},
        y: {{
          ticks: {{ color: palette.tick, font: {{ size: 11 }} }},
          grid: {{ display: false }}
        }}
      }}
    }}
  }});
</script>

</body>
</html>"""


def main() -> None:
    findings = load_findings()
    if not findings:
        print(f"[!] No findings under {REPORTS_DIR}")
        print("    Run the suite (python lab/attacks/run_all_attacks.py) and try again.")
    else:
        html = build_html(findings)
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(html, encoding="utf-8")
        print(f"[OK] HTML report written: {OUTPUT_FILE}")
        print(f"     {len(findings)} findings total — open the file and Ctrl+P for PDF.")


if __name__ == "__main__":
    main()

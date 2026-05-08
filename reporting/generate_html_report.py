"""
Generador de informe HTML autocontenido para auditoría DAST.
Lee findings.jsonl y cerberus_findings.jsonl y produce un HTML
con resumen ejecutivo, gráficos y tabla de hallazgos.
"""

import json
from datetime import datetime
from pathlib import Path
from collections import Counter

REPORTS_DIR = Path(__file__).resolve().parent.parent / "lab" / "reports"
OUTPUT_FILE = REPORTS_DIR / "audit_report.html"

SEVERITY_COLORS = {
    "Critical": "#7c2d12",
    "High": "#dc2626",
    "Medium": "#f59e0b",
    "Low": "#10b981",
    "Info": "#3b82f6",
}


def load_findings():
    findings = []
    for fname in ("findings.jsonl", "cerberus_findings.jsonl"):
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
                    data["_source"] = "Active Attack" if fname == "findings.jsonl" else "Cerberus Observer"
                    findings.append(data)
                except json.JSONDecodeError:
                    pass
    return findings


def stats(findings):
    sev = Counter(f.get("severity", "Info") for f in findings)
    cat = Counter(f.get("owasp_category", "Unknown") for f in findings)
    status = Counter(f.get("status", "observed") for f in findings)
    return {"severity": sev, "category": cat, "status": status}


def render_finding_row(idx, f):
    sev = f.get("severity", "Info")
    sev_color = SEVERITY_COLORS.get(sev, "#6b7280")
    status = f.get("status", "observed")
    status_badge = (
        f'<span class="badge badge-confirmed">CONFIRMED</span>'
        if status.lower() == "confirmed"
        else f'<span class="badge badge-observed">OBSERVED</span>'
    )
    evidence_json = json.dumps(f.get("evidence", {}), indent=2, ensure_ascii=False)
    return f"""
    <tr>
      <td>{idx}</td>
      <td>{f.get("_source", "")}</td>
      <td><strong>{f.get("vulnerability", "Unknown")}</strong></td>
      <td><span class="sev" style="background:{sev_color}">{sev}</span></td>
      <td>{f.get("owasp_category", "")}</td>
      <td>{status_badge}</td>
      <td><code>{f.get("endpoint", "")}</code></td>
    </tr>
    <tr class="evidence-row">
      <td colspan="7">
        <details>
          <summary>Evidencia técnica + mitigación</summary>
          <pre>{evidence_json}</pre>
          <p><strong>Mitigación recomendada:</strong> {f.get("mitigation", "Ver memoria.")}</p>
        </details>
      </td>
    </tr>
    """


def build_html(findings):
    s = stats(findings)
    confirmed = s["status"].get("confirmed", 0) + s["status"].get("Confirmed", 0)
    observed = sum(s["status"].values()) - confirmed
    total = len(findings)

    sev_data = [{"label": k, "value": v, "color": SEVERITY_COLORS.get(k, "#6b7280")}
                for k, v in s["severity"].items()]
    cat_data = list(s["category"].items())

    rows = "\n".join(render_finding_row(i + 1, f) for i, f in enumerate(findings))
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Steamworks DAST Lab — Technical Audit Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 0;
         background: #f3f4f6; color: #111827; }}
  header {{ background: linear-gradient(135deg, #1e3a8a, #1e40af); color: white;
           padding: 2.5rem 3rem; }}
  header h1 {{ margin: 0; font-size: 2rem; }}
  header p {{ margin: 0.5rem 0 0; opacity: 0.85; }}
  main {{ max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }}
  section {{ background: white; border-radius: 8px; padding: 2rem;
            margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  h2 {{ margin-top: 0; color: #1e40af; border-bottom: 2px solid #e5e7eb;
        padding-bottom: 0.5rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }}
  .metric {{ background: #f9fafb; border-left: 4px solid #1e40af;
             padding: 1rem; border-radius: 4px; }}
  .metric .num {{ font-size: 2.2rem; font-weight: 700; color: #1e40af; }}
  .metric .label {{ font-size: 0.85rem; color: #6b7280; text-transform: uppercase; }}
  .charts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;
             margin-top: 1rem; }}
  .chart-box {{ background: #f9fafb; padding: 1rem; border-radius: 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
  th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #1e40af; color: white; font-weight: 600; }}
  .sev {{ display: inline-block; padding: 2px 10px; border-radius: 4px;
          color: white; font-size: 0.8rem; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.75rem; font-weight: 600; }}
  .badge-confirmed {{ background: #dc2626; color: white; }}
  .badge-observed {{ background: #f59e0b; color: white; }}
  code {{ background: #1f2937; color: #fbbf24; padding: 2px 6px;
          border-radius: 3px; font-size: 0.85rem; }}
  pre {{ background: #1f2937; color: #e5e7eb; padding: 1rem;
         border-radius: 4px; overflow-x: auto; font-size: 0.8rem; }}
  details {{ margin-top: 0.5rem; }}
  summary {{ cursor: pointer; color: #1e40af; font-weight: 600; }}
  .evidence-row td {{ background: #f9fafb; }}
  footer {{ text-align: center; padding: 2rem; color: #6b7280; font-size: 0.85rem; }}
  @media print {{
    header {{ background: #1e3a8a !important; -webkit-print-color-adjust: exact; }}
    section {{ box-shadow: none; page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Steamworks DAST Lab — Technical Audit Report</h1>
  <p>Metodología DAST con estado para auditar integraciones Steamworks</p>
  <p>Paula Romero Gallart · Universidad Europea de Madrid · Generado {generated}</p>
</header>

<main>
  <section>
    <h2>Resumen ejecutivo</h2>
    <div class="grid">
      <div class="metric">
        <div class="num">{total}</div><div class="label">Hallazgos totales</div>
      </div>
      <div class="metric" style="border-color:#dc2626">
        <div class="num" style="color:#dc2626">{confirmed}</div>
        <div class="label">Confirmados</div>
      </div>
      <div class="metric" style="border-color:#f59e0b">
        <div class="num" style="color:#f59e0b">{observed}</div>
        <div class="label">Observados</div>
      </div>
      <div class="metric" style="border-color:#10b981">
        <div class="num" style="color:#10b981">{len(s["category"])}</div>
        <div class="label">Categorías OWASP</div>
      </div>
    </div>
  </section>

  <section>
    <h2>Distribución</h2>
    <div class="charts">
      <div class="chart-box"><canvas id="sevChart"></canvas></div>
      <div class="chart-box"><canvas id="catChart"></canvas></div>
    </div>
  </section>

  <section>
    <h2>Hallazgos detallados</h2>
    <table>
      <thead><tr>
        <th>#</th><th>Origen</th><th>Vulnerabilidad</th><th>Severidad</th>
        <th>OWASP</th><th>Estado</th><th>Endpoint</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</main>

<footer>
  Steamworks DAST Lab — TFG 2025/2026 · UEM · Generado automáticamente
</footer>

<script>
new Chart(document.getElementById('sevChart'), {{
  type: 'doughnut',
  data: {{
    labels: {[d["label"] for d in sev_data]},
    datasets: [{{
      data: {[d["value"] for d in sev_data]},
      backgroundColor: {[d["color"] for d in sev_data]}
    }}]
  }},
  options: {{ plugins: {{ title: {{ display: true, text: 'Severidad' }} }} }}
}});

new Chart(document.getElementById('catChart'), {{
  type: 'bar',
  data: {{
    labels: {[c[0] for c in cat_data]},
    datasets: [{{
      label: 'Hallazgos',
      data: {[c[1] for c in cat_data]},
      backgroundColor: '#1e40af'
    }}]
  }},
  options: {{
    indexAxis: 'y',
    plugins: {{ title: {{ display: true, text: 'Categoría OWASP API 2023' }} }},
    scales: {{ x: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }}
  }}
}});
</script>
</body>
</html>"""


def main():
    findings = load_findings()
    if not findings:
        print(f"[!] No hay hallazgos en {REPORTS_DIR}")
        return
    html = build_html(findings)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[OK] Informe HTML generado: {OUTPUT_FILE}")
    print(f"     Abre el archivo y usa Ctrl+P para exportar a PDF.")


if __name__ == "__main__":
    main()
import json
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.reactive import reactive
from textual.widgets import (Header, Footer, Static, DataTable, Button, RichLog)
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent.parent
ATTACKS_DIR = ROOT / "lab" / "attacks"
REPORTS_DIR = ROOT / "lab" / "reports"
INFRA_DIR = ROOT / "lab" / "infra"
REPORTING_SCRIPT = ROOT / "reporting" / "generate_html_report.py"
FINDINGS_FILE = REPORTS_DIR / "findings.jsonl"
CERBERUS_FILE = REPORTS_DIR / "cerberus_findings.jsonl"

BACKEND_URL = "http://192.168.0.103:8080"
PROXY_URL   = "http://192.168.0.103:8081"

ATTACKS = [
    ("1", "BOLA","bola_attack.py","#ef4444"),
    ("2", "BOPLA","bopla_attack.py","#f59e0b"),
    ("3", "Weak Token","weak_token_impersonation.py","#a855f7"),
    ("4", "Tx Fraud","transaction_fraud_attack.py","#06b6d4"),
    ("5", "RUN ALL","run_all_attacks.py","#10b981"),
]

SEVERITY_COLORS = {
    "Critical":"bold #b91c1c",
    "High":"bold #ef4444",
    "Medium":"bold #f59e0b",
    "Low":"bold #10b981",
    "Info":"bold #3b82f6",
}


class StatusPanel(Static):
    backend_ok = reactive(False)
    proxy_ok= reactive(False)
    db_ok= reactive(True)

    def render(self):
        def led(ok):
            return "[bold #10b981]●[/]" if ok else "[bold #ef4444]●[/]"

        lines = [
            "[bold #06b6d4]SYSTEM STATUS[/]",
            "",
            f"  {led(self.backend_ok)} Backend   [dim]{BACKEND_URL}[/]",
            f"  {led(self.proxy_ok)} Cerberus  [dim]{PROXY_URL}[/]",
            f"  {led(self.db_ok)} Database  [dim]postgres:5432[/]",
        ]
        return "\n".join(lines)


class StatsPanel(Static):
    total = reactive(0)
    confirmed = reactive(0)
    observed = reactive(0)
    critical = reactive(0)
    high = reactive(0)

    def render(self):
        return (
            "[bold #06b6d4]METRICS[/]\n\n"
            f"  Total findings   [bold white]{self.total:>4}[/]\n"
            f"  [bold #ef4444]Confirmed[/]        [bold #ef4444]{self.confirmed:>4}[/]\n"
            f"  [bold #f59e0b]Observed[/]         [bold #f59e0b]{self.observed:>4}[/]\n"
            f"\n"
            f"  Critical sev.    [bold #b91c1c]{self.critical:>4}[/]\n"
            f"  High sev.        [bold #ef4444]{self.high:>4}[/]"
        )


class SeverityBars(Static):
    counts = reactive({})

    def render(self):
        if not self.counts:
            return "[bold #06b6d4]SEVERITY[/]\n\n  [dim]Sin datos[/]"

        max_v = max(self.counts.values()) if self.counts else 1
        order = ["Critical", "High", "Medium", "Low", "Info"]
        lines = ["[bold #06b6d4]SEVERITY[/]", ""]

        for sev in order:
            v = self.counts.get(sev, 0)
            if v == 0:
                continue
            bar_len = int((v / max_v) * 18)
            bar = "█" * bar_len + "░" * (18 - bar_len)
            color = SEVERITY_COLORS.get(sev, "white")
            lines.append(f"  [{color}]{sev:<8}[/] [{color}]{bar}[/] [bold]{v}[/]")

        return "\n".join(lines)


class DASTDashboard(App):
    CSS = """
    Screen {
        background: #0a0e1a;
    }

    #main {
        layout: horizontal;
        height: 1fr;
    }

    #left-col {
        width: 38;
        height: 1fr;
    }

    #right-col {
        width: 1fr;
        height: 1fr;
    }

    StatusPanel, StatsPanel, SeverityBars {
        background: #131b2c;
        border: round #3b82f6;
        padding: 1 2;
        margin-bottom: 1;
    }

    StatusPanel { height: 8; }
    StatsPanel  { height: 10; }
    SeverityBars { height: 11; }

    #attacks-box {
        background: #131b2c;
        border: round #f59e0b;
        padding: 1 2;
        height: 1fr;
        margin-bottom: 1;
    }

    #findings-box {
        background: #131b2c;
        border: round #10b981;
        padding: 1 2;
        height: 60%;
        margin-bottom: 1;
    }

    #log-box {
        background: #131b2c;
        border: round #a855f7;
        padding: 1 2;
        height: 40%;
    }

    DataTable {
        background: transparent;
    }

    DataTable > .datatable--header {
        background: #1e3a8a;
        color: white;
        text-style: bold;
    }

    Button {
        width: 100%;
        margin-bottom: 1;
        background: #1f2937;
        border: tall #374151;
    }

    Button:hover {
        background: #374151;
    }

    .panel-title {
        text-style: bold;
        color: #06b6d4;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("1", "run_attack('bola_attack.py')",                "BOLA"),
        ("2", "run_attack('bopla_attack.py')",               "BOPLA"),
        ("3", "run_attack('weak_token_impersonation.py')",   "Weak Token"),
        ("4", "run_attack('transaction_fraud_attack.py')",   "Fraud"),
        ("5", "run_attack('run_all_attacks.py')",            "Run all"),
        ("r", "reset_db",                                    "Reset BD"),
        ("g", "generate_report",                             "Gen HTML"),
        ("o", "open_mitmweb",                                "Open mitmweb"),
        ("c", "clear_log",                                   "Clear"),
        ("q", "quit",                                        "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main"):
            with Vertical(id="left-col"):
                self.status = StatusPanel()
                yield self.status
                self.stats = StatsPanel()
                yield self.stats
                self.severity = SeverityBars()
                yield self.severity
                with Vertical(id="attacks-box"):
                    yield Static("[bold #f59e0b]ATTACK PANEL[/]   [dim](teclas 1-5)[/]")
                    yield Static("")
                    for k, name, _, color in ATTACKS:
                        yield Button(f"[{k}]  {name}", id=f"btn-{k}")
                    yield Static("")
                    yield Static("[dim][R] Reset BD  [G] HTML  [O] mitmweb[/]")
            with Vertical(id="right-col"):
                with Vertical(id="findings-box"):
                    yield Static("[bold #10b981]LIVE FINDINGS[/]   [dim](auto-refresh 2s)[/]")
                    yield Static("")
                    self.table = DataTable(zebra_stripes=True, cursor_type="row")
                    self.table.add_columns("#", "Time", "Source", "Vulnerability", "Severity", "Status")
                    yield self.table
                with Vertical(id="log-box"):
                    yield Static("[bold #a855f7]ACTIVITY LOG[/]   [dim]([C] clear)[/]")
                    yield Static("")
                    self.log_widget = RichLog(highlight=True, wrap=True, markup=True)
                    yield self.log_widget
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Steamworks DAST Dashboard"
        self.sub_title = "TFG · Paula Romero Gallart · UEM"
        self.set_interval(3.0, self.refresh_status)
        self.set_interval(2.0, self.refresh_findings)
        self.refresh_status()
        self._log_info("Dashboard iniciado")

    # ---------- helpers ----------
    def _now(self):
        return datetime.now().strftime("%H:%M:%S")

    def _log_info(self, msg):
        self.log_widget.write(f"[dim]{self._now()}[/] [#3b82f6]INFO[/]  {msg}")

    def _log_ok(self, msg):
        self.log_widget.write(f"[dim]{self._now()}[/] [#10b981]OK[/]    {msg}")

    def _log_warn(self, msg):
        self.log_widget.write(f"[dim]{self._now()}[/] [#f59e0b]WARN[/]  {msg}")

    def _log_err(self, msg):
        self.log_widget.write(f"[dim]{self._now()}[/] [#ef4444]ERROR[/] {msg}")

    # ---------- actions ----------
    def action_refresh_status(self):
        try:
            r = httpx.get(f"{BACKEND_URL}/", timeout=2.0)
            self.status.backend_ok = 200 <= r.status_code < 500
        except Exception:
            self.status.backend_ok = False
        try:
            r = httpx.get(f"{PROXY_URL}/", timeout=2.0, follow_redirects=False)
            self.status.proxy_ok = r.status_code < 500
        except Exception:
            self.status.proxy_ok = False
        self.status.db_ok = self.status.backend_ok  # si el backend va, asumimos BD ok

    refresh_status = action_refresh_status

    def refresh_findings(self):
        rows = []
        try:
            if FINDINGS_FILE.exists():
                with open(FINDINGS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            rows.append(("Attack", d))
                        except Exception:
                            pass
            if CERBERUS_FILE.exists():
                with open(CERBERUS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            rows.append(("Cerberus", d))
                        except Exception:
                            pass
        except Exception as e:
            self._log_err(f"refresh_findings: {e}")
            return

        # stats
        total = len(rows)
        confirmed = sum(1 for _, d in rows if str(d.get("status", "")).lower() == "confirmed")
        observed = total - confirmed
        critical = sum(1 for _, d in rows if d.get("severity") == "Critical")
        high = sum(1 for _, d in rows if d.get("severity") == "High")
        sev_counts = {}
        for _, d in rows:
            sev = d.get("severity", "Info")
            sev_counts[sev] = sev_counts.get(sev, 0) + 1

        self.stats.total = total
        self.stats.confirmed = confirmed
        self.stats.observed = observed
        self.stats.critical = critical
        self.stats.high = high
        self.severity.counts = sev_counts

        # tabla
        self.table.clear()
        for i, (source, d) in enumerate(rows[-30:], 1):
            sev = d.get("severity", "?")
            sev_color = SEVERITY_COLORS.get(sev, "white")
            sev_text = Text(sev, style=sev_color.replace("bold ", ""))

            status = str(d.get("status", "observed"))
            status_color = "#ef4444" if status.lower() == "confirmed" else "#f59e0b"
            status_text = Text(status.upper(), style=status_color)

            ts = d.get("timestamp", "")[-8:] if d.get("timestamp") else self._now()
            vuln = (d.get("vulnerability") or "?")[:40]

            self.table.add_row(str(i), ts, source, vuln, sev_text, status_text)

    def action_run_attack(self, script: str):
        path = ATTACKS_DIR / script
        if not path.exists():
            self._log_err(f"No existe {script}")
            return
        self._log_info(f"Lanzando [bold]{script}[/]")
        try:
            subprocess.Popen(
                [sys.executable, str(path)],
                cwd=str(ATTACKS_DIR.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._log_ok(f"{script} en background")
        except Exception as e:
            self._log_err(str(e))

    def action_reset_db(self):
        cmd = [
            "docker", "exec", "tfg_db", "psql", "-U", "postgres", "-d", "tfg",
            "-c", "UPDATE users SET credits=100;"
        ]
        self._log_info("Reseteando créditos en BD...")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                self._log_ok("Créditos reseteados a 100")
            else:
                self._log_err(f"reset_db: {r.stderr.strip()}")
        except Exception as e:
            self._log_err(str(e))

    def action_generate_report(self):
        if not REPORTING_SCRIPT.exists():
            self._log_err(f"No existe {REPORTING_SCRIPT}")
            return
        self._log_info("Generando informe HTML...")
        try:
            r = subprocess.run(
                [sys.executable, str(REPORTING_SCRIPT)],
                capture_output=True, text=True, timeout=20
            )
            if r.returncode == 0:
                self._log_ok("Informe HTML generado en lab/reports/audit_report.html")
            else:
                self._log_err(f"generate_report: {r.stderr.strip()}")
        except Exception as e:
            self._log_err(str(e))

    def action_open_mitmweb(self):
        webbrowser.open(PROXY_URL)
        self._log_info(f"Abriendo {PROXY_URL} en navegador")

    def action_clear_log(self):
        self.log_widget.clear()
        self._log_info("Log limpio")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        key = event.button.id.split("-")[-1]
        for k, _, script, _ in ATTACKS:
            if k == key:
                self.action_run_attack(script)
                return


if __name__ == "__main__":
    DASTDashboard().run()
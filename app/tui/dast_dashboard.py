"""
Steamworks DAST Lab — terminal dashboard.

Single-screen TUI for live monitoring of the lab during defense / demos.
Dark professional theme inspired by k9s / lazygit / btop.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import httpx
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Footer, Header, RichLog, Static


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent
ATTACKS_DIR = ROOT / "lab" / "attacks"
REPORTS_DIR = ROOT / "lab" / "reports"
REPORTING_SCRIPT = ROOT / "reporting" / "generate_html_report.py"
FINDINGS_FILE = REPORTS_DIR / "findings.jsonl"
CERBERUS_FILE = REPORTS_DIR / "cerberus_findings.jsonl"


# ----------------------------------------------------------------------------
# Env-configurable connection (defaults to local docker compose)
# ----------------------------------------------------------------------------
BACKEND_URL = os.getenv("DASHBOARD_BACKEND_URL", "http://localhost:8080")
PROXY_URL   = os.getenv("DASHBOARD_PROXY_URL",   "http://localhost:8081")

DB_CONTAINER = os.getenv("DASHBOARD_DB_CONTAINER", "tfg_db")
DB_USER      = os.getenv("DASHBOARD_DB_USER",      "paula")
DB_NAME      = os.getenv("DASHBOARD_DB_NAME",      "tfg_game_db")


# ----------------------------------------------------------------------------
# Attacks catalogue
# ----------------------------------------------------------------------------
ATTACKS = [
    ("1", "BOLA",         "API1:2023", "bola_attack.py"),
    ("2", "BOPLA",        "API3:2023", "bopla_attack.py"),
    ("3", "Weak Token",   "API2:2023", "weak_token_impersonation.py"),
    ("4", "Tx Fraud",     "API6:2023", "transaction_fraud_attack.py"),
    ("5", "RUN ALL",      "suite",     "run_all_attacks.py"),
]


# ----------------------------------------------------------------------------
# Theme — single accent (cyan), GitHub-dark inspired
# ----------------------------------------------------------------------------
BG          = "#0d1117"
SURFACE     = "#161b22"
BORDER      = "#30363d"
BORDER_HI   = "#21d4fd"

INK         = "#e6edf3"
INK_DIM     = "#7d8590"
INK_FAINT   = "#484f58"

ACCENT      = "#21d4fd"   # cyan
ACCENT_ALT  = "#a371f7"   # purple (links/hotkeys)
OK          = "#3fb950"
WARN        = "#d29922"
ERR         = "#f85149"
CRIT        = "#ff7b72"


SEVERITY_STYLE = {
    "Critical": CRIT,
    "High":     ERR,
    "Medium":   WARN,
    "Low":      OK,
    "Info":     ACCENT,
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def status_of(d: dict) -> str:
    if "confirmed" in d:
        label = "confirmed" if d["confirmed"] else "observed"
    else:
        label = str(d.get("status", "observed")).lower()
    return label


def _title(text: str, color: str = ACCENT) -> str:
    """Small section title rendered with a leading accent bar."""
    return f"[bold {color}]▍[/] [bold {INK}]{text}[/]"


# ----------------------------------------------------------------------------
# Panels
# ----------------------------------------------------------------------------
class StatusPanel(Static):
    backend_ok = reactive(False)
    proxy_ok = reactive(False)
    db_ok = reactive(True)

    def render(self):
        def chip(ok: bool) -> str:
            color = OK if ok else ERR
            label = "ONLINE " if ok else "OFFLINE"
            return f"[bold {color}]●[/] [bold {color}]{label}[/]"

        return "\n".join([
            _title("SERVICES"),
            "",
            f"  {chip(self.backend_ok)}  [bold]Backend[/]",
            f"             [dim {INK_DIM}]{BACKEND_URL}[/]",
            "",
            f"  {chip(self.proxy_ok)}  [bold]Cerberus / mitmweb[/]",
            f"             [dim {INK_DIM}]{PROXY_URL}[/]",
            "",
            f"  {chip(self.db_ok)}  [bold]PostgreSQL[/]",
            f"             [dim {INK_DIM}]{DB_CONTAINER} · {DB_NAME}[/]",
        ])


class StatsPanel(Static):
    total = reactive(0)
    confirmed = reactive(0)
    observed = reactive(0)
    critical = reactive(0)
    high = reactive(0)

    def render(self):
        def row(label: str, value: int, color: str, glyph: str = "") -> str:
            lbl = f"[{INK_DIM}]{label:<11}[/]"
            val = f"[bold {color}]{value:>4}[/]"
            g = f"[{color}]{glyph}[/]  " if glyph else "   "
            return f"  {g}{lbl}  {val}"

        return "\n".join([
            _title("FINDINGS"),
            "",
            row("Total",     self.total,     INK,  "■"),
            row("Confirmed", self.confirmed, ERR,  "●"),
            row("Observed",  self.observed,  WARN, "○"),
            "",
            f"  [dim {INK_FAINT}]── severity highlights ──[/]",
            "",
            row("Critical",  self.critical,  CRIT, "▲"),
            row("High",      self.high,      ERR,  "▲"),
        ])


class SeverityBars(Static):
    counts = reactive({})

    def render(self):
        order = ["Critical", "High", "Medium", "Low", "Info"]
        if not self.counts:
            lines = [
                _title("SEVERITY"),
                "",
                f"  [dim {INK_DIM}]No findings yet.[/]",
                f"  [dim {INK_DIM}]Press [bold {ACCENT_ALT}]1-5[/] to run an attack.[/]",
            ]
        else:
            max_v = max(self.counts.values()) or 1
            lines = [_title("SEVERITY"), ""]
            for sev in order:
                v = self.counts.get(sev, 0)
                if v != 0:
                    color = SEVERITY_STYLE.get(sev, INK)
                    bar_len = max(1, int((v / max_v) * 22))
                    bar = "█" * bar_len + "·" * (22 - bar_len)
                    lines.append(
                        f"  [{color}]{sev:<8}[/] [{color}]{bar}[/]  [bold {INK}]{v}[/]"
                    )
        return "\n".join(lines)


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
class DASTDashboard(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {INK};
    }}

    Header {{
        background: {SURFACE};
        color: {INK};
        text-style: bold;
    }}
    Footer {{
        background: {SURFACE};
        color: {INK_DIM};
    }}

    #banner {{
        height: 3;
        padding: 0 2;
        background: {SURFACE};
        color: {INK};
        border-bottom: solid {BORDER};
        content-align: left middle;
    }}

    #main {{
        layout: horizontal;
        height: 1fr;
        padding: 1 1 0 1;
    }}

    #left-col {{
        width: 44;
        height: 1fr;
        padding-right: 1;
    }}
    #right-col {{
        width: 1fr;
        height: 1fr;
    }}

    StatusPanel, StatsPanel, SeverityBars, #attacks-box, #findings-box, #log-box {{
        background: {SURFACE};
        border: round {BORDER};
        padding: 1 2;
        margin-bottom: 1;
    }}
    StatusPanel  {{ height: 13; }}
    StatsPanel   {{ height: 12; }}
    SeverityBars {{ height: 10; }}
    #attacks-box {{ height: 1fr; }}

    #findings-box {{ height: 60%; }}
    #log-box      {{ height: 40%; margin-bottom: 0; }}

    .panel-hint {{
        color: {INK_DIM};
    }}

    DataTable {{
        background: {SURFACE};
        color: {INK};
    }}
    DataTable > .datatable--header {{
        background: {BG};
        color: {ACCENT};
        text-style: bold;
    }}
    DataTable > .datatable--cursor {{
        background: {BORDER};
        color: {INK};
    }}
    DataTable > .datatable--odd-row {{
        background: {SURFACE};
    }}
    DataTable > .datatable--even-row {{
        background: {BG};
    }}

    Button {{
        width: 100%;
        height: 3;
        margin-bottom: 1;
        background: {BG};
        color: {INK};
        border: tall {BORDER};
        content-align: left middle;
        padding: 0 2;
    }}
    Button:hover {{
        background: {SURFACE};
        color: {ACCENT};
        border: tall {ACCENT};
    }}
    Button:focus {{
        text-style: bold;
        border: tall {ACCENT};
    }}
    """

    BINDINGS = [
        ("1", "run_attack('bola_attack.py')",               "BOLA"),
        ("2", "run_attack('bopla_attack.py')",              "BOPLA"),
        ("3", "run_attack('weak_token_impersonation.py')",  "Weak Token"),
        ("4", "run_attack('transaction_fraud_attack.py')",  "Tx Fraud"),
        ("5", "run_attack('run_all_attacks.py')",           "Run all"),
        ("r", "reset_db",                                   "Reset DB"),
        ("g", "generate_report",                            "Gen HTML"),
        ("o", "open_mitmweb",                               "mitmweb"),
        ("c", "clear_log",                                  "Clear log"),
        ("q", "quit",                                       "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            f"[bold {ACCENT}]CERBERUS[/]  [{INK_DIM}]·[/]  "
            f"[bold {INK}]Steamworks DAST Lab[/]   "
            f"[{INK_DIM}]Paula Romero Gallart  ·  "
            f"Universidad Europea de Madrid  ·  TFG 2025/26[/]",
            id="banner",
        )
        with Container(id="main"):
            with Vertical(id="left-col"):
                self.status_panel = StatusPanel()
                yield self.status_panel
                self.stats_panel = StatsPanel()
                yield self.stats_panel
                self.severity_panel = SeverityBars()
                yield self.severity_panel
                with Vertical(id="attacks-box"):
                    yield Static(_title("ATTACK SUITE", ACCENT_ALT))
                    yield Static("")
                    for key, name, owasp, _ in ATTACKS:
                        yield Button(
                            f"[bold {ACCENT_ALT}][{key}][/]  "
                            f"[bold]{name:<10}[/]  "
                            f"[dim {INK_DIM}]{owasp}[/]",
                            id=f"btn-{key}",
                        )
                    yield Static(
                        f"\n[dim {INK_DIM}]"
                        f"[bold {ACCENT_ALT}]R[/] reset db   "
                        f"[bold {ACCENT_ALT}]G[/] regen html   "
                        f"[bold {ACCENT_ALT}]O[/] mitmweb   "
                        f"[bold {ACCENT_ALT}]C[/] clear   "
                        f"[bold {ACCENT_ALT}]Q[/] quit"
                        f"[/]"
                    )

            with Vertical(id="right-col"):
                with Vertical(id="findings-box"):
                    yield Static(
                        _title("LIVE FINDINGS") +
                        f"  [dim {INK_DIM}]auto-refresh 1s · last 30[/]"
                    )
                    yield Static("")
                    self.table = DataTable(
                        zebra_stripes=True,
                        cursor_type="row",
                        show_cursor=False,
                    )
                    self.table.add_columns(
                        "#", "Time", "Source", "Vulnerability", "Severity", "Status"
                    )
                    yield self.table

                with Vertical(id="log-box"):
                    yield Static(
                        _title("ACTIVITY LOG", OK) +
                        f"  [dim {INK_DIM}]C to clear[/]"
                    )
                    yield Static("")
                    self.log_widget = RichLog(
                        highlight=True, wrap=True, markup=True
                    )
                    yield self.log_widget

        yield Footer()

    def on_mount(self) -> None:
        self.title = "Cerberus · Steamworks DAST"
        self.sub_title = "Live audit dashboard"
        self.set_interval(3.0, self.refresh_status)
        self.set_interval(1.0, self.refresh_findings)
        self.refresh_status()
        self.refresh_findings()
        self._log("INFO", "Dashboard ready. Press 1-5 to launch an attack.")

    # ----------------------- logging helpers ----------------------------
    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _log(self, level: str, msg: str) -> None:
        colors = {
            "INFO":  ACCENT,
            "OK":    OK,
            "WARN":  WARN,
            "ERROR": ERR,
        }
        color = colors.get(level, INK)
        self.log_widget.write(
            f"[{INK_FAINT}]{self._now()}[/] "
            f"[bold {color}]{level:<5}[/]  {msg}"
        )

    # ----------------------- actions ------------------------------------
    def refresh_status(self) -> None:
        try:
            r = httpx.get(f"{BACKEND_URL}/", timeout=2.0)
            self.status_panel.backend_ok = 200 <= r.status_code < 500
        except Exception:
            self.status_panel.backend_ok = False
        try:
            r = httpx.get(f"{PROXY_URL}/", timeout=2.0, follow_redirects=False)
            self.status_panel.proxy_ok = r.status_code < 500
        except Exception:
            self.status_panel.proxy_ok = False
        # Backend lives only if it can reach the DB, so we mirror that signal.
        self.status_panel.db_ok = self.status_panel.backend_ok

    def refresh_findings(self) -> None:
        rows: list[tuple[str, dict]] = []
        load_failed = False
        try:
            if FINDINGS_FILE.exists():
                with open(FINDINGS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            rows.append(("Active suite", json.loads(line)))
                        except Exception:
                            pass
            if CERBERUS_FILE.exists():
                with open(CERBERUS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            rows.append(("Cerberus", json.loads(line)))
                        except Exception:
                            pass
        except Exception as e:
            self._log("ERROR", f"refresh_findings: {e}")
            load_failed = True

        if not load_failed:
            total = len(rows)
            confirmed = sum(1 for _, d in rows if status_of(d) == "confirmed")
            critical = sum(1 for _, d in rows if d.get("severity") == "Critical")
            high = sum(1 for _, d in rows if d.get("severity") == "High")
            sev_counts: dict[str, int] = {}
            for _, d in rows:
                sev = d.get("severity", "Info")
                sev_counts[sev] = sev_counts.get(sev, 0) + 1

            self.stats_panel.total = total
            self.stats_panel.confirmed = confirmed
            self.stats_panel.observed = total - confirmed
            self.stats_panel.critical = critical
            self.stats_panel.high = high
            self.severity_panel.counts = sev_counts

            self.table.clear()
            for i, (source, d) in enumerate(rows[-30:], 1):
                sev = d.get("severity", "?")
                sev_text = Text(sev, style=SEVERITY_STYLE.get(sev, INK))

                st = status_of(d)
                st_color = ERR if st == "confirmed" else WARN
                st_text = Text(st.upper(), style=f"bold {st_color}")

                ts_raw = d.get("timestamp", "")
                ts = ts_raw[11:19] if "T" in ts_raw else (ts_raw[-8:] or self._now())

                vuln = (d.get("vulnerability") or "?")[:40]

                self.table.add_row(str(i), ts, source, vuln, sev_text, st_text)

    def action_run_attack(self, script: str) -> None:
        path = ATTACKS_DIR / script
        if not path.exists():
            self._log("ERROR", f"Script not found: {script}")
        else:
            self._log("INFO", f"Launching [bold]{script}[/]")
            try:
                subprocess.Popen(
                    [sys.executable, str(path)],
                    cwd=str(ATTACKS_DIR.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._log("OK", f"{script} running in background")
            except Exception as e:
                self._log("ERROR", str(e))

    def action_reset_db(self) -> None:
        cmd = [
            "docker", "exec", DB_CONTAINER, "psql",
            "-U", DB_USER, "-d", DB_NAME,
            "-c", "UPDATE users SET credits=100;",
        ]
        self._log("INFO", "Resetting credits to 100 in DB...")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                self._log("OK", "Credits reset to 100")
            else:
                self._log("ERROR", f"reset_db: {r.stderr.strip()}")
        except Exception as e:
            self._log("ERROR", str(e))

    def action_generate_report(self) -> None:
        if not REPORTING_SCRIPT.exists():
            self._log("ERROR", f"Reporting script not found: {REPORTING_SCRIPT}")
        else:
            self._log("INFO", "Generating HTML report...")
            try:
                r = subprocess.run(
                    [sys.executable, str(REPORTING_SCRIPT)],
                    capture_output=True, text=True, timeout=20,
                )
                if r.returncode == 0:
                    self._log("OK", "HTML report written to lab/reports/audit_report.html")
                else:
                    self._log("ERROR", f"generate_report: {r.stderr.strip()}")
            except Exception as e:
                self._log("ERROR", str(e))

    def action_open_mitmweb(self) -> None:
        webbrowser.open(PROXY_URL)
        self._log("INFO", f"Opening {PROXY_URL} in browser")

    def action_clear_log(self) -> None:
        self.log_widget.clear()
        self._log("INFO", "Log cleared")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        key = event.button.id.split("-")[-1]
        target_script = next(
            (script for k, _, _, script in ATTACKS if k == key),
            None,
        )
        if target_script is not None:
            self.action_run_attack(target_script)


if __name__ == "__main__":
    DASTDashboard().run()

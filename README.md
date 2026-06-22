# Stateful DAST Lab for Steamworks-like Integrations

🇬🇧 English · 🇪🇸 [Español](README.es.md)

> **Final Degree Project (TFG)** — Universidad Europea de Madrid
> Double Degree in Video Game Design and Computer Engineering
> Author: **Paula Romero Gallart** · 2025–2026
> Director: José Javier Ruiz Cobo

A reproducible lab for auditing logical vulnerabilities (BOLA, BOPLA, weak auth, business flow abuse) in video game APIs integrated with Steamworks. It empirically shows that a **stateful DAST** approach detects vulnerabilities that traditional tools (OWASP ZAP, Burp Suite in automated mode) miss.

---

## Key results

| Vulnerability (OWASP API 2023) | OWASP ZAP (auto) | **Cerberus** (this project) | Attack suite |
|---|---|---|---|
| API1 BOLA | not detected | **confirmed** | confirmed |
| API2 Broken Auth | not detected | n/a | confirmed |
| API3 BOPLA | not detected | observed | confirmed |
| API6 Sensitive Flow | not detected | observed | confirmed |
| **Total coverage** | **0 / 4** | **1 confirmed + 2 observed** | **4 / 4** |

- **0 confirmed false positives** on legitimate traffic from the Unity client (Phase A: 131 s of gameplay, 14 findings, 0 confirmed).
- **Real-time detection**: latency < 1 s from the offending request to the JSONL record.
- **Fully reproducible**: `docker compose up -d --build` and you're running.

---

## The two layers: *active suite* vs *Cerberus passive*

In one line: **the active suite attacks, Cerberus observes**.

| | **Active suite** (`lab/attacks/*.py`) | **Cerberus passive** (`lab/proxy/addon.py`) |
|---|---|---|
| Role | Automated pentester | Stateful SIEM / IDS |
| Traffic generated | Targeted malicious requests | None — only observes the traffic passing through mitmproxy |
| How it decides | Compares the vulnerable vs the secure endpoint response | Learns `token → user_id` at `/auth/login` and correlates with later requests |
| What it confirms | The lab's 4 vulnerabilities (BOLA, BOPLA, weak auth, tx fraud) | BOLA (with certainty, by correlation) + sensitive-field observations |
| File | `lab/reports/findings.jsonl` | `lab/reports/cerberus_findings.jsonl` |

**Why this split matters**

All four vulnerabilities could be validated with the active suite alone — that's the *ground truth*. The differential is **Cerberus**: it shows that a stateful proxy can detect the most critical category of the OWASP API Top 10 (BOLA) **without attacking**, just by watching legitimate traffic. That is exactly what ZAP in *Automated Scan* mode does **not** do. The empirical comparison is in the thesis, section 4.6.10, and is summarized in the [Key results](#key-results) table.

**Confirmed vs observed**

Cerberus separates findings into two levels so it does not artificially inflate the count:

- `confirmed` → demonstrated impact (cross-user access to another player's inventory with `200 OK`).
- `observed`  → suspicious pattern in the request (`credits`, `is_admin`, `approved_by_client` fields controlled by the client), with no proof of impact yet.

That is why, in a session of strictly legitimate Unity-client traffic (Phase A), Cerberus raises 14 `observed` and **0 `confirmed`**: the normal Steamworks store flow sends `approved_by_client=true`, which is a signal but not a vulnerability by itself.

---

## Architecture

```
            [Unity client (Steamworks.NET, AppID 480)]
                            |
                            v
            +---------------------------------+
            |  mitmproxy (port 8080)          |
            |   - Cerberus addon (stateful)   |
            |      * learns token->user_id    |
            |      * detects cross-user (BOLA)|
            |      * detects sensitive fields |
            +----------------+----------------+
                             | reverse proxy
                             v
            +---------------------------------+
            |  FastAPI backend (port 8000)    |
            |   - /vulnerable/ and /secure/ pairs|
            +----------------+----------------+
                             v
                       PostgreSQL 15
```

The lab simultaneously exposes:
- an **active attack suite** (`lab/attacks/`) that confirms 4/4 vulnerabilities,
- a **stateful observer** (`lab/proxy/addon.py`, "Cerberus") that correlates token and user to detect BOLA in real time,
- a **real Unity client** integrated with Steamworks.NET on AppID 480 (Spacewar) to generate traffic equivalent to a commercial game.

---

## Components

| Folder | What it does |
|---|---|
| `lab/backend/` | FastAPI with `/vulnerable/` and `/secure/` endpoint pairs |
| `lab/proxy/addon.py` | mitmproxy "Cerberus" addon with stateful detection |
| `lab/attacks/` | Python suite with 4 automated attacks |
| `lab/demo/` | Demo orchestrator (fast / demo / loop modes) |
| `lab/infra/docker-compose.yml` | Lab orchestration |
| `reporting/` | Markdown and HTML report generators |
| `app/tui/` | Terminal dashboard (Textual) for the presentation |
| `SteamworksDASTClient/` | Unity 2022.3 LTS client with Steamworks.NET |

---

## Demonstrated vulnerabilities

All four belong to the **OWASP API Security Top 10 — 2023**:

- **API1:2023 BOLA** — `GET /vulnerable/inventory/{user_id}` returns another user's resources if you know the victim's UUID.
- **API2:2023 Broken Authentication** — unsigned base64 token, trivially tampered with.
- **API3:2023 BOPLA / Mass Assignment** — `PATCH /vulnerable/users/me` accepts sensitive fields such as `credits` or `is_admin`.
- **API6:2023 Sensitive Business Flow** — `POST /vulnerable/transactions/finalize` trusts `approved_by_client=true` without verifying the actual payment.

For each one there is a parallel `/secure/...` endpoint that shows the correct mitigation and blocks the attack.

---

## Quickstart

**Requirements**: Docker (Desktop or Engine + compose plugin), Python 3.12, optionally Unity 2022.3 LTS + Steam running.

```bash
# 1. Start the lab
cd lab/infra
docker compose up -d --build
# API behind the proxy at http://localhost:8080
# mitmweb         at http://localhost:8081  (password: tfg2026)
cd ../..

# 2. Create a Python environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Run the full attack suite
python lab/attacks/run_all_attacks.py
# Expected result: Confirmed findings: 4/4

# 4. Generate the HTML report
python reporting/generate_html_report.py
# Open lab/reports/audit_report.html  (Ctrl+P -> Save as PDF)

# 5. (Optional) TUI dashboard
pip install -r app/tui/requirements.txt
python app/tui/dast_dashboard.py
```

### Optional environment variables

| Variable | Default | When to change it |
|---|---|---|
| `DAST_BASE_URL`            | `http://localhost:8080`     | Minerva lab or another host (`http://192.168.0.103:8080`) |
| `DAST_USE_PROXY`           | `0`                          | Force `httpx` to use an explicit PROXY_URL |
| `DASHBOARD_BACKEND_URL`    | `http://localhost:8080`     | Point the TUI dashboard to a remote backend |
| `DASHBOARD_PROXY_URL`      | `http://localhost:8081`     | Point the TUI dashboard to a remote mitmweb |
| `DASHBOARD_DB_CONTAINER`   | `tfg_db`                     | Rename the PostgreSQL container |
| `DASHBOARD_DB_USER`        | `paula`                      | Change the PostgreSQL user |
| `DASHBOARD_DB_NAME`        | `tfg_game_db`                | Change the database name |

Findings accumulate in:
- `lab/reports/findings.jsonl` — active layer (attack suite)
- `lab/reports/cerberus_findings.jsonl` — passive layer (Cerberus)
- `lab/reports/audit_logs.jsonl` — backend log
- `lab/reports/audit_report.html` — consolidated report

---

## Unity client (optional but recommended)

To reproduce HTTP traffic identical to a real Steamworks integration:

1. Open `SteamworksDASTClient/` with Unity 2022.3 LTS.
2. Have Steam open and logged in.
3. On the `ApiClient` object set `Base Url = http://localhost:8080`.
4. Play. Main menu → Play → it automatically generates calls to `/auth/steam_login`, `/users/me`, `/inventory/me/items`, `/achievements/unlock`, `/cloud/save`, `/transactions/init`, `/vulnerable/transactions/finalize`.

Cerberus observes this legitimate traffic and, by design, produces no confirmed false positives.

---

## Tech stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL 15.
- **Proxy/DAST**: mitmproxy 12.x with a custom addon.
- **Attacks**: Python 3.12, httpx.
- **Reporting**: Chart.js (CDN), self-contained HTML.
- **TUI**: Textual >= 0.50.
- **Infra**: Docker, Docker Compose, Ubuntu 24 base.
- **Client**: Unity 2022.3 LTS, C#, Steamworks.NET, UnityWebRequest.

---

## Differential contribution vs the state of the art

|   | OWASP ZAP | Burp Suite | RESTler | Wallarm | **Cerberus** |
|---|---|---|---|---|---|
| Native token→user correlation | no | no | sessions | yes | **yes** |
| Steamworks/domain-specific rules | no | no | no | no | **yes** |
| Parallel vulnerable/secure pairs | no | no | no | no | **yes** |
| Realistic legitimate client (Unity) | no | no | no | no | **yes** |
| Fully reproducible Docker lab | no | no | no | no | **yes** |
| Cost / license | free | commercial | research | commercial | **open source MIT** |

---

## Project status

Academic project (TFG). Pull requests and forks are welcome as a base for academic or industrial extensions.

**Planned future work**: state persistence in Redis, real validation against the Steam Web API, expansion to other OWASP API Top 10 categories (rate limiting, improper inventory management), native PDF export, automatic finding scoring.

---

## License

MIT License. See `LICENSE`.

---

## Academic citation

If you use this lab in research or teaching:

```bibtex
@misc{romerogallart2026dast,
  author       = {Romero Gallart, Paula},
  title        = {Stateful DAST methodology for auditing Steamworks-like integrations},
  year         = {2026},
  publisher    = {Universidad Europea de Madrid},
  howpublished = {\url{https://github.com/PaulaR17/TFG_CS-DAST-Integraciones-Steamworks-}}
}
```

---

## Contact

- Author: Paula Romero Gallart · paularomerogallart@gmail.com
- University: School of Architecture, Engineering and Design — UEM (Villaviciosa de Odón)
- Director: José Javier Ruiz Cobo

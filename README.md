# Stateful DAST Lab for Steamworks-like Integrations

> **Trabajo Fin de Grado** — Universidad Europea de Madrid
> Doble Grado en Diseño de Videojuegos e Ingeniería Informática
> Autora: **Paula Romero Gallart** · Curso 2025-2026
> Director: José Javier Ruiz Cobo

Laboratorio reproducible para auditar vulnerabilidades lógicas (BOLA, BOPLA, weak auth, business flow abuse) en APIs de videojuegos integradas con Steamworks. Demuestra empíricamente que un enfoque **DAST con estado** detecta vulnerabilidades que herramientas tradicionales (OWASP ZAP, Burp Suite en modo automated) pasan por alto.

---

## Resultados clave

| Vulnerabilidad OWASP API 2023 | OWASP ZAP (auto) | **Cerberus** (este TFG) | Suite ataques |
|---|---|---|---|
| API1 BOLA | no detectada | **confirmed** | confirmed |
| API2 Broken Auth | no detectada | n/a | confirmed |
| API3 BOPLA | no detectada | observed | confirmed |
| API6 Sensitive Flow | no detectada | observed | confirmed |
| **Cobertura total** | **0 / 4** | **1 confirmed + 2 observed** | **4 / 4** |

- **0 falsos positivos confirmados** sobre tráfico legítimo del cliente Unity (Fase A: 131 s de gameplay, 14 findings, 0 confirmed).
- **Detección en tiempo real**: latencia < 1 s desde la petición ofensiva hasta el registro en JSONL.
- **Reproducibilidad total**: `docker compose up -d --build` y a correr.

---

## Arquitectura

```
            [Cliente Unity (Steamworks.NET, AppID 480)]
                            |
                            v
            +---------------------------------+
            |  mitmproxy (puerto 8080)        |
            |   - addon Cerberus (stateful)   |
            |      * aprende token->user_id   |
            |      * detecta cross-user (BOLA)|
            |      * detecta campos sensibles |
            +----------------+----------------+
                             | reverse proxy
                             v
            +---------------------------------+
            |  FastAPI backend (puerto 8000)  |
            |   - pares /vulnerable/ y /secure/|
            +----------------+----------------+
                             v
                       PostgreSQL 15
```

El laboratorio expone simultáneamente:
- una **suite de ataques activos** (`lab/attacks/`) que confirma 4/4 vulnerabilidades,
- un **observador con estado** (`lab/proxy/addon.py`, "Cerberus") que correlaciona token y usuario para detectar BOLA en tiempo real,
- un **cliente Unity real** integrado con Steamworks.NET sobre el AppID 480 (Spacewar) para generar tráfico equivalente al de un videojuego comercial.

---

## Componentes

| Carpeta | Qué hace |
|---|---|
| `lab/backend/` | FastAPI con pares de endpoints `/vulnerable/` y `/secure/` |
| `lab/proxy/addon.py` | Addon mitmproxy "Cerberus" con detección stateful |
| `lab/attacks/` | Suite Python con 4 ataques automatizados |
| `lab/demo/` | Orquestador de la demo (modos fast / demo / loop) |
| `lab/infra/docker-compose.yml` | Orquestación del laboratorio |
| `reporting/` | Generadores de informe Markdown y HTML |
| `app/tui/` | Dashboard terminal (Textual) para presentación |
| `SteamworksDASTClient/` | Cliente Unity 2022.3 LTS con Steamworks.NET |

---

## Vulnerabilidades demostradas

Las cuatro pertenecen al **OWASP API Security Top 10 — 2023**:

- **API1:2023 BOLA** — `GET /vulnerable/inventory/{user_id}` devuelve recursos ajenos si conoces el UUID de la víctima.
- **API2:2023 Broken Authentication** — token base64 sin firma manipulable trivialmente.
- **API3:2023 BOPLA / Mass Assignment** — `PATCH /vulnerable/users/me` acepta campos sensibles como `credits` o `is_admin`.
- **API6:2023 Sensitive Business Flow** — `POST /vulnerable/transactions/finalize` confía en `approved_by_client=true` sin verificar el pago real.

Para cada una existe un endpoint `/secure/...` paralelo que muestra la mitigación correcta y bloquea el ataque.

---

## Cómo correrlo (Quickstart)

**Requisitos**: Docker Desktop, Python 3.12, opcionalmente Unity 2022.3 LTS + Steam abierto.

```bash
# 1. Levantar el laboratorio
cd lab/infra
docker compose up -d --build
# API tras el proxy en http://localhost:8080
# mitmweb en http://localhost:8081 (password: tfg2026)

# 2. Lanzar la suite completa de ataques
cd ../..
python -m venv .venv
.venv\Scripts\activate     # Linux/Mac: source .venv/bin/activate
pip install httpx
python lab/attacks/run_all_attacks.py
# Resultado esperado: Confirmed findings: 4/4

# 3. Generar informe HTML
python reporting/generate_html_report.py
# Abre lab/reports/audit_report.html

# 4. (Opcional) Dashboard TUI
cd app/tui
pip install -r requirements.txt
python dast_dashboard.py
```

Los hallazgos se acumulan en:
- `lab/reports/findings.jsonl` — capa activa (suite de ataques)
- `lab/reports/cerberus_findings.jsonl` — capa pasiva (Cerberus)
- `lab/reports/audit_logs.jsonl` — log del backend
- `lab/reports/audit_report.html` — informe consolidado

---

## Cliente Unity (opcional pero recomendado)

Para reproducir tráfico HTTP idéntico al de una integración Steamworks real:

1. Abrir `SteamworksDASTClient/` con Unity 2022.3 LTS.
2. Tener Steam abierto y logueado.
3. En el objeto `ApiClient` poner `Base Url = http://localhost:8080`.
4. Play. Menú principal → Play → se generan automáticamente las llamadas a `/auth/steam_login`, `/users/me`, `/inventory/me/items`, `/achievements/unlock`, `/cloud/save`, `/transactions/init`, `/vulnerable/transactions/finalize`.

Cerberus observa este tráfico legítimo y, por construcción, no genera falsos positivos confirmados.

---

## Stack técnico

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, PostgreSQL 15.
- **Proxy/DAST**: mitmproxy 12.x con addon propio.
- **Ataques**: Python 3.12, httpx.
- **Reporting**: Chart.js (CDN), HTML autocontenido.
- **TUI**: Textual >= 0.50.
- **Infra**: Docker, Docker Compose, Ubuntu 24 base.
- **Cliente**: Unity 2022.3 LTS, C#, Steamworks.NET, UnityWebRequest.

---

## Aportación diferencial frente al estado del arte

|   | OWASP ZAP | Burp Suite | RESTler | Wallarm | **Cerberus** |
|---|---|---|---|---|---|
| Correlación token→user nativa | no | no | sesiones | sí | **sí** |
| Reglas específicas dominio Steamworks | no | no | no | no | **sí** |
| Pares vulnerable/secure paralelos | no | no | no | no | **sí** |
| Cliente legítimo realista (Unity) | no | no | no | no | **sí** |
| Lab Docker totalmente reproducible | no | no | no | no | **sí** |
| Coste / licencia | gratis | comercial | investigación | comercial | **open source MIT** |

---

## Estado del proyecto

Proyecto académico (TFG). Pull requests y forks bienvenidos como base para extensiones académicas o industriales.

**Futuras líneas planteadas**: persistencia del state en Redis, validación real contra Steam Web API, expansión a otras categorías del OWASP API Top 10 (rate limiting, improper inventory management), exportación nativa a PDF, scoring automático de hallazgos.

---

## Licencia

MIT License. Consultar `LICENSE`.

---

## Cita académica

Si usas este laboratorio en investigación o docencia:

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

## Contacto

- Autora: Paula Romero Gallart · paularomerogallart@gmail.com
- Universidad: Escuela de Arquitectura, Ingeniería y Diseño — UEM (Villaviciosa de Odón)
- Director: José Javier Ruiz Cobo

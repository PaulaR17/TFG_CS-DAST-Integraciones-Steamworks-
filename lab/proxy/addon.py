"""
cerberus es el addon de mitmproxy para este lab.

su trabajo es mirar las peticiones y respuestas que pasan por el proxy. con eso
puede detectar campos raros enviados por el cliente y tambien confirmar algun
fallo cuando ve la respuesta del backend.

archivos que genera:
- reports/cerberus_startup_check.txt para saber que el addon ha cargado
- reports/cerberus_findings.jsonl para guardar hallazgos vistos por el proxy
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from mitmproxy import http


#archivos de salida dentro del contenedor
REPORTS_DIR = Path("/app/reports")
FINDINGS_FILE = REPORTS_DIR / "cerberus_findings.jsonl"
STARTUP_CHECK_FILE = REPORTS_DIR / "cerberus_startup_check.txt"


#memoria sencilla para relacionar tokens con usuarios
TOKEN_TO_USER_ID: Dict[str, str] = {}
TOKEN_TO_USERNAME: Dict[str, str] = {}


#campos que me parecen peligrosos si vienen controlados por el cliente
SENSITIVE_FIELDS = {
    "credits",
    "is_admin",
    "role",
    "approved_by_client"
}


#helpers
def now_iso() -> str: #devuelve la fecha actual en formato iso.
    return datetime.now(timezone.utc).isoformat()


def ensure_reports_dir() -> None: #crea /app/reports dentro del contenedor si todavia no existe.
   
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def write_startup_check() -> None: #crea un archivo pequeño para comprobar que mitmproxy ha cargado el addon.

    try:
        ensure_reports_dir()

        STARTUP_CHECK_FILE.write_text(
            f"Cerberus addon loaded at {now_iso()}\n",
            encoding="utf-8"
        )

        print("[CERBERUS] Startup check file written.")

    except Exception as error:
        print(f"[CERBERUS ERROR] Could not write startup check file: {error}")


def save_finding(finding: Dict[str, Any]) -> None: #guarda un hallazgo en reports/cerberus_findings.jsonl.

    finding["timestamp"] = now_iso()
    finding["source"] = "cerberus_mitmproxy"

    print("\n[CERBERUS FINDING]")
    print(json.dumps(finding, indent=2, ensure_ascii=False))

    try:
        ensure_reports_dir()

        with FINDINGS_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(finding, ensure_ascii=False) + "\n")

    except Exception as error:
        print(f"[CERBERUS ERROR] Could not write finding: {error}")


def parse_json_request(flow: http.HTTPFlow) -> Optional[Dict[str, Any]]: #intenta leer el body de una request como json.
   
    try:
        if not flow.request.content: #si no hay body, no es json o no es un objeto, devuelvo none.
            return None

        request_text = flow.request.get_text()

        if request_text is None:
            return None

        parsed = json.loads(request_text)

        if isinstance(parsed, dict):
            return parsed

        return None

    except Exception:
        return None


def parse_json_response(flow: http.HTTPFlow) -> Optional[Dict[str, Any]]: #ntenta leer el body de una response como json.

    # uso para aprender cosas del login, como token y user_id.
    try:
        if not flow.response:
            return None

        if not flow.response.content:
            return None

        response_text = flow.response.get_text()

        if response_text is None:
            return None

        parsed = json.loads(response_text)

        if isinstance(parsed, dict):
            return parsed

        return None

    except Exception:
        return None


def extract_bearer_token(flow: http.HTTPFlow) -> Optional[str]: #saca el token de la cabecera authorization.
    
    # se esoera q salga algo como: authorization: bearer <token>
  
    authorization = flow.request.headers.get("Authorization")

    if authorization is None:
        return None

    if not authorization.startswith("Bearer "):
        return None

    return authorization.replace("Bearer ", "").strip()


def extract_inventory_user_id(path: str) -> Optional[str]: #saca el user_id de /vulnerable/inventory/{user_id}.
    
    match = re.match(r"^/vulnerable/inventory/([^/]+)$", path)

    if not match:
        return None

    return match.group(1)


#hook de carga de mitmproxy

def load(loader) -> None: #asi puedo ver en logs y en archivo que cerberus esta vivo.

    print("[CERBERUS] Addon loaded successfully.")
    write_startup_check()


#hook de requests

def request(flow: http.HTTPFlow) -> None:  #cada vez que mitmproxy ve una request
    """
    aqui todavia no se si el ataque ha funcionado, pero si puedo marcar cosas
    sospechosas que el cliente esta intentando mandar.
    """

    method = flow.request.method
    path = flow.request.path

    print(f"[CERBERUS REQUEST] {method} {path}")

    request_body = parse_json_request(flow)

    if request_body is None:
        return

    #miro si el cliente ha mandado campos que no deberia controlar
    detected_sensitive_fields = [
        field for field in SENSITIVE_FIELDS
        if field in request_body
    ]

    if detected_sensitive_fields:
        save_finding({
            "vulnerability": "Sensitive Client-Controlled Property",
            "severity": "Medium",
            "endpoint": path,
            "owasp_category": (
                "API3:2023 Broken Object Property Level Authorization / "
                "API6:2023 Sensitive Business Flow"
            ),
            "confirmed": False,
            "evidence": {
                "method": method,
                "path": path,
                "detected_fields": detected_sensitive_fields,
                "request_body": request_body
            },
            "mitigation": (
                "Reject or ignore client-controlled sensitive fields such as "
                "credits, is_admin, role and approved_by_client."
            )
        })

    if path == "/vulnerable/transactions/finalize":
        approved_by_client = request_body.get("approved_by_client")

        if approved_by_client is True:
            #si veo approved_by_client=true, marco el intento aunque aun no sepa el impacto
            save_finding({
                "vulnerability": "Client-Side Transaction Approval Attempt",
                "severity": "High",
                "endpoint": "/vulnerable/transactions/finalize",
                "owasp_category": (
                    "API6:2023 Unrestricted Access to Sensitive Business Flows"
                ),
                "confirmed": False,
                "evidence": {
                    "method": method,
                    "path": path,
                    "request_body": request_body
                },
                "mitigation": (
                    "The backend must verify payment state server-side against "
                    "Steam Web API or another trusted payment provider."
                )
            })


#hook de responses
def response(flow: http.HTTPFlow) -> None:
    #aqui ya puedo aprender relaciones token -> usuario y confirmar algunos fallos.
    method = flow.request.method
    path = flow.request.path

    if not flow.response:
        return

    status_code = flow.response.status_code

    print(f"[CERBERUS RESPONSE] {method} {path} -> {status_code}")

    #aprendo token -> user_id leyendo la respuesta del login
    if method == "POST" and path == "/auth/login" and status_code == 200:
        response_body = parse_json_response(flow)

        if response_body is None:
            return

        access_token = response_body.get("access_token")
        user_id = response_body.get("user_id")
        username = response_body.get("username")

        if isinstance(access_token, str) and isinstance(user_id, str):
            TOKEN_TO_USER_ID[access_token] = user_id
            TOKEN_TO_USERNAME[access_token] = username if isinstance(username, str) else "unknown"

            print(
                f"[CERBERUS] Learned authenticated session: "
                f"user_id={user_id}, username={username}"
            )

        return

    #confirmo bola si alguien pide un inventario ajeno y el backend responde 200
    requested_user_id = extract_inventory_user_id(path)

    if method == "GET" and requested_user_id and status_code == 200:
        token = extract_bearer_token(flow)

        if token is None:
            print("[CERBERUS] Inventory request without Bearer token.")
            return

        authenticated_user_id = TOKEN_TO_USER_ID.get(token)

        if authenticated_user_id is None:
            print(
                "[CERBERUS] Inventory request observed, but token is unknown. "
                "Cannot correlate BOLA state."
            )
            return

        if authenticated_user_id != requested_user_id:
            save_finding({
                "vulnerability": "Broken Object Level Authorization (BOLA)",
                "severity": "High",
                "endpoint": "/vulnerable/inventory/{user_id}",
                "owasp_category": "API1:2023 Broken Object Level Authorization",
                "confirmed": True,
                "evidence": {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "authenticated_user_id": authenticated_user_id,
                    "requested_user_id": requested_user_id
                },
                "mitigation": (
                    "Validate that the requested user_id matches the authenticated "
                    "user_id before returning inventory resources."
                )
            })

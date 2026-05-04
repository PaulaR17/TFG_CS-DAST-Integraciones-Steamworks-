import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import httpx


#configuracion basica del laboratorio

#aqui decido si los ataques van directos al backend o pasan antes por mitmproxy
#modo directo: attacks/*.py -> http://localhost:8000
#modo proxy: attacks/*.py -> mitmproxy:8080 -> http://api:8000
#para usar proxy se lanza con dast_use_proxy=1
#en docker el backend se llama "api", por eso la url cambia en modo proxy
USE_PROXY = os.getenv("DAST_USE_PROXY", "0") == "1"

BASE_URL = os.getenv(
    "DAST_BASE_URL",
    "http://192.168.0.103:8000" if USE_PROXY else "http://192.168.0.103:8000"
)

PROXY_URL = os.getenv(
    "DAST_PROXY_URL",
    "http://192.168.0.103:8080"
)


#carpeta donde dejo las pruebas que van sacando los ataques
REPORTS_DIR = Path("reports")

#archivo jsonl de los ataques activos: cada linea es un json distinto
FINDINGS_FILE = REPORTS_DIR / "findings.jsonl"


#tickets falsos del lab, tienen que coincidir con los que entiende el backend
ATTACKER_TICKET = "STEAM_TICKET_ATTACKER"
VICTIM_TICKET = "STEAM_TICKET_VICTIM"


#helpers para guardar evidencias

def ensure_reports_dir() -> None:
    """
    crea reports/ si no existe.

    lo hago antes de escribir para que no falle la primera ejecucion.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def write_finding(
    vulnerability: str,
    severity: str,
    endpoint: str,
    owasp_category: str,
    evidence: Dict[str, Any],
    mitigation: str,
    confirmed: bool
) -> None:
    """
    guarda un fallo encontrado en reports/findings.jsonl.

    aqui va la evidencia que sacan los scripts de ataque.

    mitmproxy escribe en otro archivo, asi no se mezcla todo sin saber de donde sale.
    """

    ensure_reports_dir()

    finding = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "automated_attack_script",
        "vulnerability": vulnerability,
        "severity": severity,
        "endpoint": endpoint,
        "owasp_category": owasp_category,
        "confirmed": confirmed,
        "evidence": evidence,
        "mitigation": mitigation
    }

    with FINDINGS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(finding, ensure_ascii=False) + "\n")


#helpers para hacer peticiones http

def create_client() -> httpx.Client:
    """
    crea el cliente http que usan los ataques.

    si no hay proxy, apunta al backend local.

    si hay proxy, manda primero las peticiones a mitmproxy para poder verlas.
    """

    print(f"[HTTP] USE_PROXY={USE_PROXY}")
    print(f"[HTTP] BASE_URL={BASE_URL}")

    client_kwargs = {
        "base_url": BASE_URL,
        "timeout": 10.0
    }

    if USE_PROXY:
        print(f"[HTTP] PROXY_URL={PROXY_URL}")

        return httpx.Client(
            **client_kwargs,
            proxy=PROXY_URL
        )

    return httpx.Client(**client_kwargs)


def login(client: httpx.Client, steam_ticket: str) -> Dict[str, Any]:
    """
    hace login con uno de los tickets falsos del laboratorio.

    devuelve cosas importantes como el token, el user_id y el steam_id.
    """

    response = client.post(
        "/auth/login",
        json={
            "steam_ticket": steam_ticket
        }
    )

    response.raise_for_status()
    return response.json()


def auth_headers(access_token: str) -> Dict[str, str]:
    """
    monta la cabecera authorization para no repetirla en cada peticion.

    al final queda como: authorization: bearer <token>
    """
    return {
        "Authorization": f"Bearer {access_token}"
    }


def get_me(client: httpx.Client, access_token: str) -> Dict[str, Any]:
    """
    pide /users/me para saber que usuario esta autenticado y cuantos creditos tiene.
    """

    response = client.get(
        "/users/me",
        headers=auth_headers(access_token)
    )

    response.raise_for_status()
    return response.json()


#helpers para tokens

def forge_demo_token(user_id: str, steam_id: str) -> str:
    """
    crea un token falso para demostrar la vulnerabilidad.

    esto es inseguro a proposito porque el lab quiere enseñar el fallo.

    el token solo es base64(json), asi que se puede cambiar el user_id y volver
    a codificarlo como si nada.
    """

    payload = {
        "user_id": user_id,
        "steam_id": steam_id
    }

    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


#helpers para que la salida por terminal se lea mejor

def print_title(title: str) -> None:
    """
    imprime un titulo grande para separar cada ataque en la terminal.
    """
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_result(success: bool, message: str) -> None:
    """
    imprime ok o fail segun si la comprobacion ha salido bien.
    """
    if success:
        print(f"[OK] {message}")
    else:
        print(f"[FAIL] {message}")

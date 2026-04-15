from mitmproxy import http
import json

def request(flow: http.HTTPFlow) -> None:
    # Detectamos si el usuario intenta enviar campos sensibles
    body = flow.request.get_text()
    if body:
        campos_criticos = ["is_admin", "credits", "role"]
        for campo in campos_criticos:
            if campo in body:
                print(f"⚠️ [ALERTA BOPLA] Intento de manipulacion de campo sensible: {campo}")

def response(flow: http.HTTPFlow) -> None:
    if "/inventory/" in flow.request.pretty_url:
        print(f"--- [RADAR CERBERUS] ---")
        print(f"Analizando peticion a: {flow.request.url}")
        
        if flow.response.status_code == 200:
            print(f"ALERTA: Acceso concedido a los datos del ID.") #luego hay que meter una comprobación del ID 
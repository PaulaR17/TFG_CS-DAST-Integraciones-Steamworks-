from mitmproxy import http
import json

#esta funcion intercepta las respuestas de la api
def response(flow: http.HTTPFlow) -> None:
    #si la api responde con un login exitoso, capturamos el id para el ataque
    if "/auth/login" in flow.request.pretty_url and flow.response.status_code == 200:
        data = json.loads(flow.response.text)
        user_id = data.get("user_id")
        print(f"alerta: capturado id de sesion para auditoria: {user_id}")
        
    #si detectamos una peticion de inventario, lanzamos el aviso de bola
    if "/inventory/" in flow.request.pretty_url:
        print(f"detectado flujo critico: comprobando vulnerabilidad bola en {flow.request.url}")
        #aqui es donde el sistema generaria el informe de vulnerabilidad [cite: 153]

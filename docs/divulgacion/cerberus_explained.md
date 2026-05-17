# Cerberus, en detalle: por qué un proxy con estado detecta lo que un DAST clásico no ve

**Documento técnico complementario · Paula Romero Gallart · TFG 2025/26**

---

## TL;DR

Cerberus es el motor de auditoría DAST con estado de este laboratorio. Está
implementado como un addon Python de ~150 líneas para mitmproxy. A diferencia
de un escáner DAST clásico (que ataca generando tráfico nuevo) o de un
agente IAST (que se instala dentro del proceso a auditar), Cerberus se
sitúa **en el camino del tráfico HTTP real**, aprende la asociación
`token → user_id` durante la fase de login y la usa para confirmar
vulnerabilidades de autorización a nivel de objeto (BOLA) **sin generar ni
una sola petición ofensiva**. Esta arquitectura es la que permite los dos
resultados experimentales que sostienen el TFG: detección de BOLA en
tráfico legítimo del cliente Unity y **cero falsos positivos confirmados**
sobre 131 segundos de gameplay real.

---

## 1. El problema que justifica una herramienta nueva

Las vulnerabilidades lógicas de las APIs modernas (BOLA, BOPLA, abuso de
flujos de negocio) tienen una propiedad común: las peticiones que las
explotan son **sintácticamente indistinguibles** de las legítimas. Un
`GET /vulnerable/inventory/8f3a-...-d7c1` con un token Bearer válido es
una operación correcta a nivel de protocolo HTTP, semánticamente coherente
para la API y conforme al esquema OpenAPI. Solo dejan de ser legítimas
cuando se evalúan con **dos piezas de información a la vez**:

1. La identidad real asociada al token utilizado.
2. La identidad propietaria del recurso solicitado.

Si esos dos `user_id` coinciden, es una petición normal. Si no coinciden y
el servidor responde con `200 OK`, hay BOLA confirmado. La conclusión es
clara: el detector necesita **estado** entre, al menos, la petición de
`/auth/login` y la petición posterior contra el recurso.

Ningún escáner DAST que opere petición a petición, sin contexto, puede
emitir ese juicio. No es un defecto de implementación: es una limitación
arquitectónica.

---

## 2. ¿Por qué un proxy programable y no un agente o un sidecar?

Para construir un detector con estado existen al menos tres caminos
viables. La elección de uno u otro condiciona la generalidad, la
intrusividad y el coste de adopción del sistema.

### Opción A — Agente in-process (estilo IAST)

Instalar una biblioteca dentro del proceso del backend (FastAPI) que
intercepte rutas y haga la correlación token-recurso en memoria.

- **Ventajas**: máxima visibilidad, acceso al stack trace, latencia mínima.
- **Inconvenientes**: invasivo (toca el código de producción), requiere
  desplegar una versión instrumentada, atado a un framework concreto y a un
  lenguaje (Python, en este caso). Para un equipo que use además un
  proxy-gateway delante del backend, duplica complejidad.

### Opción B — Sidecar / middleware en el balanceador

Reglas embebidas en un WAF moderno o en un proxy de servicio (Envoy,
nginx con Lua). Cada petición pasa por la regla.

- **Ventajas**: sin tocar la app, escala con la infraestructura existente.
- **Inconvenientes**: la programabilidad real (correlación entre peticiones
  separadas en el tiempo, parsing de cuerpos JSON arbitrarios) es muy
  limitada o requiere código compilado/ad-hoc por entorno. No facilita la
  reproducibilidad académica.

### Opción C — Proxy programable en Python (la elegida)

mitmproxy expone un API Python que permite escribir hooks (`request`,
`response`, `load`) sobre cada flujo HTTP. El estado puede mantenerse en
estructuras de datos Python ordinarias. El laboratorio se levanta entero
con `docker compose up`.

- **Ventajas**: no toca la app, no toca el balanceador, es trivialmente
  reproducible por terceros, el código es legible para cualquier
  estudiante con Python intermedio. El estado se externaliza fácilmente a
  Redis para producción.
- **Inconvenientes**: añade un salto de red, no tiene visibilidad del
  stack trace del backend, su rendimiento depende de mitmproxy (suficiente
  para tráfico moderado pero no para servicios de alta carga sin tuning).

La opción C es la que mejor encaja con los **objetivos académicos del
trabajo**: poder publicar el laboratorio entero como material reproducible,
permitir que un evaluador lo levante en una máquina sin más, y poder
explicar el algoritmo de detección al detalle sin que dependa de un
framework propietario. Es además la única que se traduce sin esfuerzo a un
escenario distribuido con tres equipos físicos, como el ensayo realizado en
el laboratorio Minerva de la UEM.

---

## 3. El algoritmo, en su versión mínima

Todo el motor cabe conceptualmente en dos hooks de mitmproxy:

```python
# Memoria del addon (en producción se externalizaría a Redis)
STATE: dict[str, str] = {}   # access_token -> user_id

SENSITIVE_FIELDS = {"credits", "is_admin", "role", "approved_by_client"}


def response(flow):
    """
    1. Aprende la asociación token -> user_id observando el login.
    2. Confirma BOLA si una petición posterior contra inventario
       devuelve recursos de otro user_id distinto al del token.
    """
    if flow.request.path in ("/auth/login", "/auth/steam_login") \
       and flow.response.status_code == 200:
        body = json.loads(flow.response.text)
        STATE[body["access_token"]] = body["user_id"]
        return

    m = re.match(r"^/vulnerable/inventory/([^/]+)$", flow.request.path)
    if m and flow.request.method == "GET" and flow.response.status_code == 200:
        token = flow.request.headers.get("Authorization", "") \
                                    .removeprefix("Bearer ").strip()
        requested = m.group(1)
        observed_user = STATE.get(token)
        if observed_user is not None and observed_user != requested:
            log_finding(
                vulnerability="Broken Object Level Authorization (BOLA)",
                confirmed=True,
                evidence={
                    "authenticated_user_id": observed_user,
                    "requested_user_id":     requested,
                },
            )


def request(flow):
    """
    Marca campos sensibles controlados por el cliente como superficie
    de ataque. NO confirma BOPLA por sí mismo: solo la capa activa
    puede saber si el backend acepta el valor enviado.
    """
    body = parse_json_body(flow.request)
    if not body:
        return
    detected = body.keys() & SENSITIVE_FIELDS
    if detected:
        log_finding(
            vulnerability="Sensitive Client-Controlled Property",
            confirmed=False,
            evidence={"detected_fields": sorted(detected)},
        )
```

Eso es todo. El código real, en `lab/proxy/addon.py`, añade
únicamente: persistencia de hallazgos a JSONL, logging para diagnóstico,
distinción entre `/auth/login` (suite) y `/auth/steam_login` (cliente
Unity), y manejo defensivo de respuestas no parseables.

**Complejidad**: la inspección de cada flujo es O(1) en el número de
tokens observados, lo que garantiza que la introducción de Cerberus no
añade una latencia perceptible al tráfico HTTP. La complejidad espacial
es lineal en el número de sesiones activas observadas. Durante el
experimento de la sección 4.6.9 de la memoria el consumo de memoria del
addon se mantuvo por debajo de 50 MB.

---

## 4. La separación `confirmed` vs `observed`: por qué importa

Cerberus etiqueta cada hallazgo con uno de dos estados, y la diferencia
es deliberada:

- `confirmed` significa **impacto observado**. Ejemplo canónico: un usuario
  X pidió inventario del usuario Y y el backend respondió con `200 OK` y
  los items de Y. Esto es BOLA real, no señal.
- `observed` significa **superficie de ataque detectada**. Ejemplo: una
  request lleva `approved_by_client=true` o `credits=99999`. Cerberus no
  sabe si el backend hizo caso a ese campo; solo sabe que el campo viajó
  por el canal. La capa activa termina de confirmarlo.

Esta división es lo que permite el resultado experimental clave de la
sección 4.6.9: en la **Fase A** (cliente Unity solo, sin ataques) Cerberus
registra **14 hallazgos**, todos `observed` y **cero `confirmed`**. Los
14 son el flujo legítimo de la tienda Steamworks-style, donde el cliente
manda `approved_by_client=true` como parte normal del checkout. Si Cerberus
los marcara como vulnerabilidades, el informe estaría diciendo "14 fallos"
sobre tráfico perfectamente legítimo: el clásico problema del DAST
tradicional inflando falsos positivos.

Es importante remarcarlo de cara al tribunal: **no se trata de un acto de
modestia. Es una decisión de diseño que mejora la precisión del sistema.**

---

## 5. Sobre la complementariedad pasiva/activa

Cerberus por sí solo cubre, en términos de confirmación rigurosa, una de
las cuatro categorías auditadas: BOLA. Para las otras tres (BOPLA, weak
auth, transaction fraud), Cerberus levanta señales (`observed`), pero la
confirmación llega de la suite activa. Esto **no es una debilidad**, es
coherente con la literatura académica del DAST con estado:

| Categoría OWASP API 2023 | ¿Cerberus puede confirmar solo? | Por qué |
|---|---|---|
| API1 BOLA | **Sí** | La correlación token-user_id basta |
| API2 Broken Auth | No | Requiere forjar tokens, lo cual es atacar |
| API3 BOPLA | No | Requiere observar el efecto del campo sobre el estado, no solo su presencia |
| API6 Sensitive Flow | No | Requiere medir el resultado del flujo (créditos sumados, transacción finalizada) |

La conclusión es que un detector pasivo con estado **complementa**, no
sustituye, a un auditor activo. Lo que sí hace, y ninguna herramienta
pasiva sin estado puede hacer, es **convertir tráfico legítimo en señal
útil de auditoría** — el holy grail de la observabilidad de seguridad
moderna.

---

## 6. Limitaciones honestas

Para que esta nota envejezca bien, conviene listar los puntos en los que
Cerberus es deliberadamente modesto:

1. **Estado en memoria local del addon**. Si mitmproxy reinicia, se
   pierde el mapeo token-user_id aprendido. La extensión natural es
   externalizar el estado a Redis, lo cual queda como línea futura.
2. **Reglas escritas a mano para el dominio Steamworks**. La detección
   de BOLA está acoplada a la forma de la ruta `/vulnerable/inventory/{id}`.
   Generalizar a otros patrones (ej. `/users/{id}/cloud-saves`) requiere
   añadir reglas explícitas. Esta especialización es **buscada**: es
   precisamente lo que diferencia el sistema de un fuzzer genérico.
3. **HTTPS con certificate pinning**. mitmproxy intercepta HTTPS si se
   instala su certificado raíz. Clientes con pinning estricto (móvil,
   binarios sin opción de override) requerirían configuraciones
   adicionales fuera del alcance del laboratorio.
4. **No mira respuestas con `Content-Encoding: br`** sin descompresión.
   En el laboratorio el backend responde sin compresión, así que no
   afecta. En producción habría que añadir el decode explícito.
5. **No detecta lo que no ve**. Si el atacante usa un canal lateral
   (websocket, gRPC) que no pasa por el proxy, Cerberus no se entera.
   Esto vale para cualquier sistema basado en intercepción HTTP.

---

## 7. Referencias relacionadas

- Microsoft Research. *RESTler: Stateful REST API fuzzing.*
  Línea académica más cercana al enfoque stateful, pero con énfasis en
  fuzzing activo, no en observación pasiva.
- OWASP. *API Security Top 10 — 2023.* Define las categorías que el
  trabajo audita.
- mitmproxy. *Addon API documentation.* La base sobre la que se construye
  el motor.
- ENISA. *Threat Landscape 2025.* Dato relevante: la mayoría de las
  brechas contra APIs proceden de sesiones autenticadas, justo el caso
  donde un detector con estado aporta valor.
- Capítulo 5 de la memoria, "Aportación diferencial frente al estado del
  arte", donde se desarrollan los cinco elementos que justifican esta
  combinación concreta (proxy programable + dominio Steamworks + pares
  vulnerable/secure + cliente legítimo realista + open source MIT).

---

## 8. Una analogía para la defensa

Si en la defensa hay que explicarlo en 30 segundos sin entrar en pseudocódigo,
funciona la siguiente analogía:

> "La suite activa es **un pentester**: entra, prueba a forzar puertas, te
> dice cuáles ceden. Cerberus es **una cámara de seguridad inteligente**:
> no toca ninguna puerta, pero sabe quién entró por la puerta principal y
> levanta una alerta si esa misma persona sale por una ventana cinco
> minutos después. El primer rol es el clásico del DAST automatizado. El
> segundo es lo que falta en herramientas como ZAP y lo que se materializa
> en este trabajo."

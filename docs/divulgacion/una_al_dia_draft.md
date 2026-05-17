# Cuando el escáner se queda corto: por qué OWASP ZAP no detecta el principal vector de ataque a las APIs de videojuegos

**Por Paula Romero Gallart · Universidad Europea de Madrid · 2026**

---

## Resumen (TL;DR para editores)

Una auditoría comparativa entre OWASP ZAP 2.17.0 (modo *Automated Scan*) y un
DAST *stateful* propio sobre el mismo backend muestra que la herramienta de
referencia no detecta ninguna de las cuatro vulnerabilidades del *OWASP API
Security Top 10 — 2023* introducidas en el laboratorio (BOLA, BOPLA, Broken
Authentication y Sensitive Business Flow). El motivo no es un fallo de ZAP,
sino una limitación arquitectónica de cualquier escáner DAST sin estado.
Se propone una metodología híbrida (proxy programable con correlación
token→usuario + suite de ataques activos) que cierra esa brecha sobre APIs
estilo Steamworks. Todo el laboratorio es reproducible con `docker compose up`
y se publica bajo licencia MIT.

Repositorio: <https://github.com/PaulaR17/TFG_CS-DAST-Integraciones-Steamworks->

---

## El problema: lógica frente a sintaxis

El *State of the API 2024* de Postman indica que el 74 % de las
organizaciones adoptan ya una estrategia *API-first*. Cloudflare, Salt
Security y Traceable coinciden en otro número incómodo: más de la mitad de
las brechas relevantes contra APIs en los últimos dos años proceden de
sesiones **autenticadas**. Es decir, el atacante no se cuela por una inyección
SQL ni por una cabecera mal validada; se cuela porque la API confía en él más
de lo que debería.

Esa categoría de fallos tiene nombre desde 2019: **Broken Object Level
Authorization (BOLA)** y, en su variante de propiedades, **BOPLA**. Una
petición `GET /inventory/123` con un token Bearer válido es sintácticamente
indistinguible de una `GET /inventory/456` con el mismo token. Un WAF, un
escáner pasivo o un DAST automatizado las ven exactamente igual. La
diferencia está en si el `123` pertenece o no a la identidad del token, y eso
solo se sabe **manteniendo estado** entre la petición de login y la petición
de inventario.

En el sector del videojuego, donde el modelo *Games as a Service* multiplica
las APIs (autenticación con tickets, inventario, microtransacciones,
guardado en la nube, logros), este tipo de fallo se traduce literalmente en
dinero: créditos virtuales clonados, inventarios secuestrados, transacciones
fraudulentas. Newzoo proyecta 197 000 M$ de mercado para 2025 y *The
Business Research Company* sitúa el segmento de microtransacciones en
84 010 M$.

## El experimento

Para medir el problema con datos, no con discurso, se construyó un
laboratorio reproducible con Docker Compose:

- **Backend FastAPI** con pares de endpoints `/vulnerable/...` y
  `/secure/...` para cuatro vulnerabilidades del OWASP API Top 10.
- **PostgreSQL 15** con UUIDs como identificadores (sin enumeración trivial).
- **mitmproxy** como proxy reverso programable.
- **Cliente Unity 2022.3 LTS** con Steamworks.NET sobre el `AppID 480`
  (Spacewar), la aplicación oficial de pruebas que Valve provee a los
  desarrolladores.
- **Suite de ataques en Python** que confirma BOLA, BOPLA, suplantación con
  token débil y fraude en microtransacciones.

Sobre ese entorno se ejecutó **OWASP ZAP 2.17.0 en modo Automated Scan** con
configuración por defecto, exactamente igual que lo correría un equipo
DevSecOps que añade ZAP a su pipeline sin pararse a programar contextos
personalizados. Y, en paralelo, se ejecutó la metodología propuesta en este
trabajo.

## Lo que ZAP detecta y lo que no

El informe de ZAP genera 3 alertas: una de severidad *Medium* (Content
Security Policy ausente) y un par de *Informational* sobre cabeceras. Nada
relevante para la lógica de autorización. El propio informe lo dice con
claridad en su sección de estadísticas: *"No Authentication Statistics
Found"*. Traducido: ZAP nunca completó una sesión autenticada, así que no
llegó siquiera a tocar los endpoints donde están las cuatro vulnerabilidades.

No es un defecto de ZAP. Es la naturaleza de un escáner automatizado *out of
the box*: no sabe qué endpoint genera un token, qué token corresponde a qué
identidad, ni qué peticiones posteriores deberían cruzar identidad con
recurso. Sin esa máquina de estado, la herramienta se queda midiendo
superficie de ataque genérica.

| OWASP API 2023        | ZAP (auto) | Cerberus (este trabajo) | Suite activa |
|-----------------------|:---------:|:-----------------------:|:------------:|
| API1 BOLA             | no        | **confirmed**           | confirmed    |
| API2 Broken Auth      | no        | n/a                     | confirmed    |
| API3 BOPLA            | no        | observed                | confirmed    |
| API6 Sensitive Flow   | no        | observed                | confirmed    |
| **Cobertura total**   | **0 / 4** | **1 confirmed + 2 obs** | **4 / 4**    |

## La propuesta: un DAST con estado

La pieza central es un addon de mitmproxy (~150 líneas de Python) que se
llama **Cerberus**. Su lógica cabe en dos *hooks*:

```python
STATE = {}   # token -> user_id

def response(flow):
    # Aprendizaje en el login: token -> user_id
    if flow.request.path in ("/auth/login", "/auth/steam_login") \
       and flow.response.status_code == 200:
        body = json.loads(flow.response.text)
        STATE[body["access_token"]] = body["user_id"]

    # Confirmación de BOLA por correlación
    m = re.match(r"^/vulnerable/inventory/([^/]+)$", flow.request.path)
    if m and flow.response.status_code == 200:
        token = flow.request.headers["Authorization"].removeprefix("Bearer ").strip()
        requested = m.group(1)
        observed  = STATE.get(token)
        if observed and observed != requested:
            log_finding("BOLA", confirmed=True,
                        evidence={"observed": observed, "requested": requested})
```

Con eso basta para detectar accesos cruzados de inventario en tiempo real.
Para BOPLA y Sensitive Business Flow, Cerberus genera *observaciones* sobre
campos sensibles controlados por el cliente (`credits`, `is_admin`,
`approved_by_client`), y la **suite activa** termina de confirmarlas con
inyecciones controladas. La división deliberada entre `confirmed` y
`observed` evita inflar el conteo de vulnerabilidades, un problema clásico
de los escáneres DAST genéricos.

## ¿Falsos positivos? Cero confirmados sobre tráfico legítimo

La pieza experimental más relevante del trabajo no es la detección, sino la
medición del **falso positivo**. Se diseñaron tres fases sobre el mismo
despliegue:

- **Fase A** — cliente Unity solo, 131 segundos de gameplay real
  cubriendo los seis flujos críticos (login, perfil, inventario, logros,
  tienda y guardado en la nube). **14 hallazgos, 0 confirmed.** Todos los
  hallazgos son observaciones estructurales (campo `approved_by_client`),
  ninguna vulnerabilidad demostrada.
- **Fase B** — suite de ataques sola. **4 confirmed.**
- **Fase C** — Unity y ataques en paralelo, simulando producción
  con un atacante activo entre usuarios legítimos. **4 confirmed, sin
  falsos positivos atribuidos al cliente Unity.**

La latencia entre la petición ofensiva y el registro del hallazgo en disco
quedó por debajo de un segundo en todos los casos. El consumo de memoria
del addon, por debajo de 50 MB durante toda la sesión.

## Por qué creo que esto importa

Existen herramientas comerciales (Wallarm, Salt Security, Traceable) que
cubren *stateful API testing* a nivel empresarial. Existen también líneas
académicas como RESTler de Microsoft Research. Lo que faltaba era una
referencia abierta, mínima y reproducible, especializada en el dominio
Steamworks/GaaS, que sirviese como:

1. **Material docente** sobre vulnerabilidades de lógica de negocio.
2. **Base** para integrar DAST con estado en pipelines DevSecOps de estudios
   indie con presupuesto limitado.
3. **Prueba empírica** de que el problema no es la velocidad del escáner,
   sino su falta de contexto.

El código se publica bajo licencia MIT. El laboratorio se levanta entero con
`docker compose up -d --build`. Los hallazgos se exportan como JSONL y se
consolidan en un informe HTML autocontenido que se imprime a PDF sin
dependencias externas. Pull requests bienvenidos.

---

**Sobre la autora**: Paula Romero Gallart cursa el Doble Grado en Diseño de
Videojuegos e Ingeniería Informática en la Universidad Europea de Madrid.
Este artículo resume el capítulo experimental de su Trabajo Fin de Grado,
dirigido por José Javier Ruiz Cobo. Contacto:
[paularomerogallart@gmail.com](mailto:paularomerogallart@gmail.com).

**Lecturas recomendadas**:
- OWASP. *API Security Top 10 — 2023*. <https://owasp.org/API-Security/editions/2023/>
- Cloudflare. *2024 API Security and Management Report*.
- ENISA. *Threat Landscape 2025*.
- Microsoft Research. *RESTler: Stateful REST API fuzzing*.
- Valve. *Steamworks Documentation — Microtransactions Implementation Guide*.

---

## Notas para envío

- Versión corta (Una al Día): recortar la sección "Por qué creo que esto
  importa" a un párrafo único.
- Versión larga (LOOP / GameReport): añadir el detalle del cliente Unity y
  capturas de gameplay/HUD, dado el público gaming.
- Adjuntar dos imágenes: tabla comparativa ZAP vs Cerberus, y la captura del
  informe HTML autogenerado.
- Pedir DOI a Zenodo antes de enviar, citarlo en el pie.

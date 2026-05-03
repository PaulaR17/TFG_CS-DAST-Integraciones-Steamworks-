# Manual de Usuario - Steamworks DAST Lab

## 1. Introducción

Steamworks DAST Lab es un laboratorio de auditoría dinámica de seguridad orientado a APIs de videojuegos inspiradas en integraciones tipo Steamworks.

El sistema permite simular flujos habituales de un backend Games as a Service, como autenticación, inventario, perfil de usuario, logros, guardado en la nube y microtransacciones.

El laboratorio incluye endpoints vulnerables y endpoints seguros equivalentes. De esta forma, el usuario puede comprobar tanto la explotación de una vulnerabilidad como su mitigación.

Además, el proyecto incorpora una suite de ataques automatizados y un proxy de observación llamado Cerberus, basado en mitmproxy, que permite analizar el tráfico HTTP con estado y generar hallazgos de seguridad.

---

## 2. Requisitos previos

Antes de ejecutar el laboratorio, el usuario debe tener instalado:

- Docker.
- Docker Compose.
- Python 3.12 o superior.
- Git.
- Un navegador web.
- Visual Studio Code u otro editor de código.

Opcionalmente, se recomienda tener instalada la herramienta `tree` para visualizar la estructura del proyecto:

```bash
sudo apt install tree
```

---

## 3. Estructura general del proyecto

La estructura principal del laboratorio es la siguiente:

```text
lab/
├── attacks/
│   ├── bola_attack.py
│   ├── bopla_attack.py
│   ├── common.py
│   ├── run_all_attacks.py
│   ├── transaction_fraud_attack.py
│   └── weak_token_impersonation.py
│
├── backend/
│   ├── audit_logger.py
│   ├── database.py
│   ├── Dockerfile
│   ├── main.py
│   ├── models.py
│   ├── requirements.txt
│   ├── schemas.py
│   └── security.py
│
├── infra/
│   └── docker-compose.yml
│
├── proxy/
│   └── addon.py
│
├── reporting/
│   └── generate_report.py
│
└── reports/
    ├── findings.jsonl
    ├── cerberus_findings.jsonl
    └── audit_report.md
```

Cada carpeta tiene una función concreta:

```text
backend/
Contiene la API FastAPI, los modelos de base de datos, los esquemas Pydantic, la conexión con PostgreSQL y la autenticación demostrativa.

attacks/
Contiene los scripts que ejecutan ataques automatizados contra el laboratorio.

proxy/
Contiene el addon de mitmproxy, llamado Cerberus, encargado de observar tráfico HTTP y detectar patrones sospechosos.

reporting/
Contiene el generador automático de informes técnicos.

reports/
Contiene los ficheros generados durante las pruebas: evidencias JSONL e informe Markdown.

infra/
Contiene el archivo docker-compose.yml que levanta la base de datos, la API y el proxy.
```

---

## 4. Puesta en marcha del laboratorio

### 4.1. Acceder al directorio del proyecto

```bash
cd ~/Desktop/TFG/lab
```

### 4.2. Activar el entorno virtual de Python

```bash
source backend/venv/bin/activate
```

Para comprobar que el entorno está activo:

```bash
which python
```

Debe aparecer una ruta similar a:

```text
/home/paulapnz/Desktop/TFG/lab/backend/venv/bin/python
```

### 4.3. Levantar los servicios con Docker Compose

```bash
docker compose -f infra/docker-compose.yml up --build
```

Este comando levanta tres servicios:

```text
tfg_db      -> base de datos PostgreSQL
tfg_api     -> backend FastAPI
tfg_proxy   -> proxy mitmproxy con Cerberus
```

Si se desea levantar el entorno en segundo plano:

```bash
docker compose -f infra/docker-compose.yml up --build -d
```

### 4.4. Comprobar que los contenedores están activos

```bash
docker ps
```

Deben aparecer los contenedores:

```text
tfg_db
tfg_api
tfg_proxy
```

### 4.5. Detener el laboratorio

```bash
docker compose -f infra/docker-compose.yml down
```

Para detenerlo y borrar también los datos persistidos de la base de datos:

```bash
docker compose -f infra/docker-compose.yml down -v
```

---

## 5. Acceso a la API

Una vez levantado el laboratorio, la API estará disponible en:

```text
http://localhost:8000
```

La documentación Swagger estará disponible en:

```text
http://localhost:8000/docs
```

El esquema OpenAPI estará disponible en:

```text
http://localhost:8000/openapi.json
```

La interfaz web de mitmproxy estará disponible en:

```text
http://localhost:8081
```

La contraseña configurada para mitmproxy web es:

```text
paula123
```

---

## 6. Usuarios de prueba

El laboratorio utiliza tickets sintéticos para simular una autenticación tipo Steamworks.

Los tickets disponibles son:

```text
STEAM_TICKET_PAULA
STEAM_TICKET_ATTACKER
STEAM_TICKET_VICTIM
```

Cada ticket representa un usuario diferente dentro del laboratorio.

---

## 7. Prueba manual de autenticación

### 7.1. Login como atacante

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"steam_ticket": "STEAM_TICKET_ATTACKER"}'
```

La respuesta tendrá una estructura similar a:

```json
{
  "access_token": "TOKEN_GENERADO",
  "token_type": "bearer",
  "user_id": "UUID_DEL_USUARIO",
  "steam_id": "76561198000000002",
  "username": "Attacker_Test"
}
```

### 7.2. Login como víctima

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"steam_ticket": "STEAM_TICKET_VICTIM"}'
```

### 7.3. Guardar el token en una variable

Una vez obtenido el `access_token`, se puede guardar en una variable de entorno temporal:

```bash
TOKEN="PEGAR_AQUI_EL_ACCESS_TOKEN"
```

### 7.4. Consultar el perfil del usuario autenticado

```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 8. Prueba manual de inventario

### 8.1. Crear un objeto en el inventario propio

```bash
curl -X POST "http://localhost:8000/inventory/me/items" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"item_name": "Golden AK47", "quantity": 1}'
```

Este endpoint crea un objeto asociado al usuario autenticado.

### 8.2. Consultar inventario vulnerable

```bash
curl -X GET "http://localhost:8000/vulnerable/inventory/USER_ID_A_CONSULTAR" \
  -H "Authorization: Bearer $TOKEN"
```

Este endpoint es vulnerable porque permite consultar el inventario de cualquier usuario si se conoce su identificador.

### 8.3. Consultar inventario seguro

```bash
curl -X GET "http://localhost:8000/secure/inventory/USER_ID_A_CONSULTAR" \
  -H "Authorization: Bearer $TOKEN"
```

Este endpoint comprueba que el `user_id` solicitado coincida con el usuario autenticado.

Si el usuario autenticado intenta acceder al inventario de otro usuario, el endpoint seguro devuelve:

```text
403 Forbidden
```

---

## 9. Prueba manual de BOLA / IDOR

BOLA significa Broken Object Level Authorization. En este laboratorio se demuestra cuando un atacante usa su propio token para acceder al inventario de una víctima cambiando el `user_id` en la URL.

Flujo manual:

```text
1. Hacer login como víctima.
2. Crear un objeto en el inventario de la víctima.
3. Hacer login como atacante.
4. Usar el token del atacante.
5. Consultar /vulnerable/inventory/{victim_user_id}.
6. Comprobar que el endpoint vulnerable devuelve objetos de la víctima.
7. Consultar /secure/inventory/{victim_user_id}.
8. Comprobar que el endpoint seguro devuelve 403.
```

Endpoint vulnerable:

```text
GET /vulnerable/inventory/{user_id}
```

Endpoint seguro:

```text
GET /secure/inventory/{user_id}
```

---

## 10. Prueba manual de BOPLA / Mass Assignment

BOPLA significa Broken Object Property Level Authorization. En este laboratorio se demuestra cuando el backend permite modificar propiedades internas que no deberían depender del cliente.

### 10.1. Endpoint vulnerable

```bash
curl -X PATCH "http://localhost:8000/vulnerable/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "HackerQueen", "credits": 999999}'
```

Este endpoint es vulnerable porque acepta campos sensibles enviados por el cliente, como `credits`.

### 10.2. Endpoint seguro

```bash
curl -X PATCH "http://localhost:8000/secure/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "SafeUser", "credits": 1}'
```

Este endpoint solo permite modificar `username`. El campo `credits` se ignora.

### 10.3. Comprobar el perfil

```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

Resultado esperado:

```text
/vulnerable/users/me -> modifica username y credits.
/secure/users/me     -> modifica username, pero no modifica credits.
```

---

## 11. Prueba manual de microtransacciones

### 11.1. Crear transacción

```bash
curl -X POST "http://localhost:8000/transactions/init" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_TEST_001", "item_name": "Mega Coins Pack", "amount": 5000}'
```

Este endpoint inicializa una transacción asociada al usuario autenticado.

### 11.2. Finalización vulnerable

```bash
curl -X POST "http://localhost:8000/vulnerable/transactions/finalize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_TEST_001", "approved_by_client": true}'
```

Este endpoint es vulnerable porque confía en el campo `approved_by_client`, enviado por el cliente.

Si el cliente envía:

```json
{
  "approved_by_client": true
}
```

el backend vulnerable finaliza la transacción y suma créditos al usuario.

### 11.3. Finalización segura

```bash
curl -X POST "http://localhost:8000/secure/transactions/finalize" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_TEST_001", "approved_by_client": true}'
```

Este endpoint rechaza la operación con:

```text
403 Forbidden
```

porque la aprobación de pago debería verificarse en el servidor, no confiarse al cliente.

---

## 12. Ejecución de ataques automatizados

### 12.1. Ejecutar todos los ataques sin proxy

```bash
cd ~/Desktop/TFG/lab
source backend/venv/bin/activate

rm -f reports/findings.jsonl
rm -f reports/audit_report.md

python attacks/run_all_attacks.py
```

El resultado esperado es:

```text
Confirmed findings: 4/4
```

Los ataques ejecutados son:

```text
BOLA / IDOR
BOPLA / Mass Assignment
Weak Token Impersonation
Transaction Fraud
```

Los hallazgos confirmados se guardan en:

```text
reports/findings.jsonl
```

---

## 13. Ejecución de ataques pasando por Cerberus

Para que Cerberus observe el tráfico, primero se debe tener Docker levantado:

```bash
docker compose -f infra/docker-compose.yml up --build
```

En otra terminal:

```bash
cd ~/Desktop/TFG/lab
source backend/venv/bin/activate

rm -f reports/findings.jsonl
rm -f reports/cerberus_findings.jsonl
rm -f reports/audit_report.md

DAST_USE_PROXY=1 python attacks/run_all_attacks.py
```

Este comando ejecuta los ataques pasando por mitmproxy.

El flujo es:

```text
scripts de ataque -> mitmproxy/Cerberus -> backend FastAPI
```

Cerberus observa el tráfico y genera hallazgos adicionales en:

```text
reports/cerberus_findings.jsonl
```

Para visualizar esos hallazgos:

```bash
cat reports/cerberus_findings.jsonl
```

Para contar cuántos hallazgos ha generado Cerberus:

```bash
wc -l reports/cerberus_findings.jsonl
```

Resultado esperado:

```text
6 reports/cerberus_findings.jsonl
```

---

## 14. Generación del informe técnico

Después de ejecutar los ataques:

```bash
python reporting/generate_report.py
```

El informe se genera en:

```text
reports/audit_report.md
```

Para visualizarlo:

```bash
cat reports/audit_report.md
```

El informe incluye:

```text
Resumen ejecutivo.
Tabla de hallazgos.
Severidad.
Categoría OWASP.
Endpoint afectado.
Estado del hallazgo.
Evidencias técnicas.
Mitigaciones recomendadas.
```

---

## 15. Ejecución completa recomendada

Este es el flujo completo recomendado para una demostración:

```bash
cd ~/Desktop/TFG/lab
source backend/venv/bin/activate

rm -f reports/findings.jsonl
rm -f reports/cerberus_findings.jsonl
rm -f reports/audit_report.md

DAST_USE_PROXY=1 python attacks/run_all_attacks.py
python reporting/generate_report.py

cat reports/audit_report.md
```

Este flujo demuestra:

```text
1. Ejecución de ataques automatizados.
2. Confirmación de vulnerabilidades.
3. Observación del tráfico mediante Cerberus.
4. Generación de evidencias JSONL.
5. Generación de informe técnico automático.
```

---

## 16. Archivos de salida

El sistema genera los siguientes archivos:

```text
reports/findings.jsonl
```

Contiene los hallazgos confirmados por los scripts de ataque activos.

```text
reports/cerberus_findings.jsonl
```

Contiene los hallazgos y observaciones detectados por Cerberus desde mitmproxy.

```text
reports/audit_report.md
```

Contiene el informe técnico final generado automáticamente.

---

## 17. Interpretación de resultados

El sistema diferencia entre dos tipos de hallazgos.

### Confirmed

Indica que la vulnerabilidad ha sido explotada y validada con impacto real dentro del laboratorio.

Ejemplo:

```text
El atacante accede al inventario de la víctima y el backend devuelve HTTP 200 con objetos cuyo owner_id pertenece a la víctima.
```

### Observed

Indica que Cerberus ha detectado un patrón sospechoso en el tráfico, pero no necesariamente confirma explotación completa.

Ejemplo:

```text
Cerberus detecta que el cliente ha enviado un campo sensible como credits o approved_by_client.
```

Esta diferencia es importante porque evita confundir señales sospechosas con vulnerabilidades confirmadas.

---

## 18. Vulnerabilidades cubiertas

El laboratorio cubre actualmente cuatro vulnerabilidades principales.

### 18.1. BOLA / IDOR

Permite demostrar qué ocurre cuando un usuario autenticado accede al recurso de otro usuario modificando un identificador en la URL.

Endpoint vulnerable:

```text
/vulnerable/inventory/{user_id}
```

Endpoint seguro:

```text
/secure/inventory/{user_id}
```

### 18.2. BOPLA / Mass Assignment

Permite demostrar qué ocurre cuando el backend acepta propiedades sensibles enviadas por el cliente.

Endpoint vulnerable:

```text
/vulnerable/users/me
```

Endpoint seguro:

```text
/secure/users/me
```

### 18.3. Weak Token Impersonation

Permite demostrar qué ocurre cuando un token no está firmado y puede ser manipulado para suplantar otro usuario.

Endpoint afectado:

```text
/users/me
```

### 18.4. Transaction Fraud

Permite demostrar qué ocurre cuando el backend confía en una aprobación de pago enviada por el cliente.

Endpoint vulnerable:

```text
/vulnerable/transactions/finalize
```

Endpoint seguro:

```text
/secure/transactions/finalize
```

---

## 19. Comandos útiles de Docker

Ver contenedores activos:

```bash
docker ps
```

Ver logs generales:

```bash
docker compose -f infra/docker-compose.yml logs -f
```

Ver logs de la API:

```bash
docker compose -f infra/docker-compose.yml logs -f api
```

Ver logs del proxy:

```bash
docker compose -f infra/docker-compose.yml logs -f proxy
```

Reiniciar todo desde cero:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```

---

## 20. Comandos útiles del proyecto

Ver estructura:

```bash
tree -I "venv|__pycache__|*.pyc"
```

Ejecutar ataques:

```bash
python attacks/run_all_attacks.py
```

Ejecutar ataques por proxy:

```bash
DAST_USE_PROXY=1 python attacks/run_all_attacks.py
```

Generar informe:

```bash
python reporting/generate_report.py
```

Leer informe:

```bash
cat reports/audit_report.md
```

Leer hallazgos activos:

```bash
cat reports/findings.jsonl
```

Leer hallazgos de Cerberus:

```bash
cat reports/cerberus_findings.jsonl
```

Contar hallazgos de Cerberus:

```bash
wc -l reports/cerberus_findings.jsonl
```

---

## 21. Problemas comunes

### 21.1. La API no responde

Comprobar que Docker está levantado:

```bash
docker ps
```

Comprobar logs de la API:

```bash
docker compose -f infra/docker-compose.yml logs -f api
```

### 21.2. El proxy no genera findings

Comprobar que los ataques se están ejecutando con:

```bash
DAST_USE_PROXY=1 python attacks/run_all_attacks.py
```

Comprobar logs del proxy:

```bash
docker compose -f infra/docker-compose.yml logs -f proxy
```

Comprobar si existe el fichero:

```bash
ls -la reports
```

### 21.3. El informe aparece vacío

Eliminar informes antiguos y volver a ejecutar:

```bash
rm -f reports/findings.jsonl
rm -f reports/cerberus_findings.jsonl
rm -f reports/audit_report.md

DAST_USE_PROXY=1 python attacks/run_all_attacks.py
python reporting/generate_report.py
```

### 21.4. Error de conexión con la base de datos

Reiniciar el entorno completo:

```bash
docker compose -f infra/docker-compose.yml down -v
docker compose -f infra/docker-compose.yml up --build
```

---

## 22. Cierre del laboratorio

Para cerrar el entorno:

```bash
docker compose -f infra/docker-compose.yml down
```

Para cerrar y borrar la base de datos:

```bash
docker compose -f infra/docker-compose.yml down -v
```

---

## 23. Resumen de uso

El flujo normal de uso es:

```text
1. Levantar Docker Compose.
2. Abrir Swagger si se quieren hacer pruebas manuales.
3. Ejecutar ataques automatizados.
4. Ejecutar ataques con proxy si se quiere activar Cerberus.
5. Generar el informe técnico.
6. Revisar findings.jsonl, cerberus_findings.jsonl y audit_report.md.
```

Comando final recomendado:

```bash
cd ~/Desktop/TFG/lab
source backend/venv/bin/activate

rm -f reports/findings.jsonl
rm -f reports/cerberus_findings.jsonl
rm -f reports/audit_report.md

DAST_USE_PROXY=1 python attacks/run_all_attacks.py
python reporting/generate_report.py
cat reports/audit_report.md
```

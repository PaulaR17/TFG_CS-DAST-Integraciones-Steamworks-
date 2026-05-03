# API1:2023 BOLA (Broken Object Level Authorization)# API1:2023 — BOLA (Broken Object Level Authorization)

**Qué es**
Vulnerabilidad donde un atacante **manipula el identificador de un objeto (object ID)** que la API recibe en la request para **acceder, modificar o borrar objetos que no le pertenecen** (IDOR a nivel de objeto).

- Objeto = cualquier recurso: users, orders, invoices, files, projects, tickets, etc.

## Dónde suele aparecer el ID (object identifier)
El identificador del objeto puede ir en:

- **Request target / path**: `/orders/123`
- **Query params**: `?orderId=123`
- **Headers** (menos común)
- **Request body / payload**: `{ "invoiceId": 123 }`

## Por qué pasa (causa real)
La API **autentica** al usuario (sabe quién es), pero **no autoriza a nivel de objeto**: no comprueba si el usuario autenticado tiene permisos sobre *ese* objeto concreto.

Resultado: basta con **cambiar el ID** para acceder a recursos ajenos.

## Cómo se detecta / se explota (idea)
1. Capturas una request válida (ej: `GET /orders/123`)
2. Cambias el ID (`/orders/124`)
3. Si devuelve datos o permite acciones, hay BOLA

Normalmente el atacante sabe si funcionó por:
- **códigos HTTP** (200/204 vs 403/404)
- **cambios visibles** en datos
- **diferencias** en el response

## Impacto
- Exposición de datos de otros usuarios (confidencialidad)
- Modificación/borrado de recursos ajenos (integridad/disponibilidad)
- Fraude / escalado si los recursos son sensibles

## Notas importantes
- Comparar un `userId` que venga del cliente (body/params) con el `userId` del JWT **NO es suficiente**, porque el atacante puede modificar lo que manda.
- La verificación correcta es:
  - obtener el usuario del **contexto de autenticación** (JWT/session)
  - comprobar en backend que **el recurso pertenece a ese usuario** o está permitido por una política/rol

## PARA PREVENIRLO
- Implementar **autorización a nivel de objeto** en **cada endpoint** que lea/modifique/borrе un recurso (GET/PUT/PATCH/DELETE).
- Centralizar autorización con **políticas** (RBAC/ABAC) y **deny by default**.
- Validar permisos con datos del servidor (no confiar en IDs del cliente).
- **Tests** específicos (IDOR/BOLA): intentar acceder a recursos de otro usuario en CI.
- **IDs impredecibles (UUID/GUID)** ayudan contra enumeración, pero **no reemplazan** la autorización.
- Minimizar filtrado de información: respuestas consistentes (evitar leaks por diferencias 403 vs 404 si aplica).




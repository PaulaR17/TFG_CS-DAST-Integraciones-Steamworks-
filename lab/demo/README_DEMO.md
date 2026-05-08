# Demo de defensa — Procedimiento

## Setup previo (5 min antes de defensa)

### Ubuntu (192.168.0.103) — backend + Cerberus
1. `cd ~/TFG/lab/infra && docker compose up -d`
2. Comprobar: `curl http://localhost:8080/` debe responder 200
3. Abrir mitmweb en navegador: `http://localhost:8081`
4. Limpiar findings antiguos: `> ~/TFG/lab/reports/cerberus_findings.jsonl`
5. Limpiar findings de ataques: `> ~/TFG/lab/reports/findings.jsonl`

### W1 (192.168.0.105) — cliente Unity
1. Abrir Steam con cuenta PaulaRG17
2. Abrir Unity, escena Game
3. Verificar `ApiClient.baseUrl = http://192.168.0.103:8080`
4. Pulsar Play, comprobar que el HUD muestra `Credits: 100`
5. Pausar (no salir, solo pausa) hasta el momento de la demo

### W2 (192.168.0.107) — atacante
1. Abrir terminal en `C:\Users\TechLabs\Desktop\TFG\lab`
2. `.venv\Scripts\activate`
3. Verificar `BASE_URL` en `attacks/common.py` = `http://192.168.0.103:8080`
4. Listo para lanzar

## Durante la defensa (3 min)

1. **Despierta a la audiencia**: muestra los 3 monitores y mitmweb vacío
2. **Inicia gameplay legítimo en W1**: Paula juega 20-30 segundos
   → mitmweb empieza a llenarse de POST /auth/steam_login, GET /users/me, etc.
3. **Lanza el atacante en W2**: python demo\demo_orchestrator.py --mode demo
4. **Mientras corre**: cuenta lo que está pasando.
   - "Mientras Paula juega, en otra máquina un atacante explota BOLA..."
   - "Cerberus correlaciona token y user_id en tiempo real"
5. **Cierre**: muestra mitmweb con tráfico mezclado y abre `cerberus_findings.jsonl`

## Plan B si algo falla

- Si el lab físico falla: levantas todo en local y demo en una sola máquina
- Si Unity peta: enseñas la suite atacando solo
- Si los ataques fallan: muestras el `audit_report.md` ya generado de la sesión del lab
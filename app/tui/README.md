# DAST Dashboard (TUI)

Dashboard interactivo para el lab Steamworks DAST.

## Instalación
cd app/tui
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt

## Uso
python dast_dashboard.py

## Atajos de teclado
- `1-4`: lanza ataque individual
- `5`: lanza la suite completa
- `r`: refresca estado
- `c`: limpia el log
- `q`: salir

## Configurar URL del backend
Edita las constantes `BACKEND_URL` y `PROXY_URL` al inicio del archivo si apuntas al lab físico.


@echo off
REM Lanzador rápido para la demo en Windows (W2)
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python demo\demo_orchestrator.py --mode demo
pause
@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 (
  echo ERRO: nao foi possivel criar o ambiente Python. Instale Python 3.10+.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" launcher.py --install
if errorlevel 1 (
  echo ERRO: instalacao ou inicializacao falhou. Consulte SOLUCAO_DE_PROBLEMAS.md
  pause
  exit /b 1
)
pause

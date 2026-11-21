@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launcher.py
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 launcher.py
  ) else (
    python launcher.py
  )
)
echo.
if errorlevel 1 echo Consulte SOLUCAO_DE_PROBLEMAS.md para diagnostico.
pause

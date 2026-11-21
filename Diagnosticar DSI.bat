@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" launcher.py --check
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 launcher.py --check
  ) else (
    python launcher.py --check
  )
)
pause

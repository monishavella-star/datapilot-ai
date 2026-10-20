@echo off
setlocal
cd /d "%~dp0backend"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (set "PY=py") else (set "PY=python")
%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo DataPilot AI requires Python 3.11 or newer.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv
if errorlevel 1 (
  echo Unable to create the virtual environment.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed. Check your internet connection and try again.
  pause
  exit /b 1
)
echo.
echo Setup complete. Run start-windows.bat.
pause
@echo off
setlocal
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Please run setup-windows.bat first.
  pause
  exit /b 1
)
echo.
echo DataPilot AI is starting at http://127.0.0.1:8000
echo API documentation: http://127.0.0.1:8000/docs
echo Press Ctrl+C to stop the server.
echo.
start "" http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

echo TabTool starting at http://127.0.0.1:8000
echo Remote: http://127.0.0.1:8000/remote
echo Press Ctrl+C to stop.
echo.

rem Open the browser once the server answers /api/health.
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

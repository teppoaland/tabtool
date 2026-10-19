@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

rem Refuse to start a second instance: two servers on the same port make
rem API and audio responses unpredictable. Run stop.bat first.
set "PORT=8000"
set "PORT_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:"LISTENING" ^| findstr /C:":%PORT% "') do (
  if not defined PORT_PID set "PORT_PID=%%P"
)
if defined PORT_PID (
  echo Port %PORT% is already in use by PID !PORT_PID!.
  echo Run stop.bat first, then start.bat again.
  exit /b 1
)

echo AI TabTool starting at http://127.0.0.1:%PORT%
echo Remote: http://127.0.0.1:%PORT%/remote
echo Press Ctrl+C to stop.
echo.

rem Open the browser once the server answers /api/health.
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%

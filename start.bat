@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

rem One click restarts the server: stop the previous instance, then start.
rem prepare_start.ps1 stops only a Python/uvicorn listener on the port; a
rem foreign program is reported and left alone.
set "PORT=8000"
call powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\prepare_start.ps1" -Port %PORT%
if errorlevel 1 (
  echo Could not prepare port %PORT%. Fix the message above and run start.bat again.
  exit /b 1
)

rem One launcher, one mode: bind all interfaces so the phone remote works on
rem the LAN without a second script or a flag. The QR code is on /remote.
set "TABTOOL_HOST=0.0.0.0"

echo AI TabTool:      http://127.0.0.1:%PORT%
echo Remote with QR:  http://127.0.0.1:%PORT%/remote
echo.
echo Keep the TV view open on this PC: http://127.0.0.1:%PORT%
echo Open /remote in a second tab (it shows the QR) - do not replace the TV tab.
echo.
call powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\lan_addresses.ps1" -Port %PORT%
echo If the phone cannot connect, allow port %PORT% in Windows Defender Firewall for private networks.
echo Optional PIN: set TABTOOL_LAN_PIN in .env before starting.
echo Press Ctrl+C to stop.
echo.

rem Open the browser once the server answers /api/health.
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%



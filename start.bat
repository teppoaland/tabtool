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

rem One launcher, one mode: bind all interfaces so the phone remote works on
rem the LAN without a second script or a flag. The QR code is on /remote.
set "TABTOOL_HOST=0.0.0.0"

echo AI TabTool:      http://127.0.0.1:%PORT%
echo Remote with QR:  http://127.0.0.1:%PORT%/remote
echo.
call powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\lan_addresses.ps1" -Port %PORT%
echo If the phone cannot connect, allow port %PORT% in Windows Defender Firewall for private networks.
echo Optional PIN: set TABTOOL_LAN_PIN in .env before starting.
echo Press Ctrl+C to stop.
echo.

rem Open the browser once the server answers /api/health.
start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1"

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%



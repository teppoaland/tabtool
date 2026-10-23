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

rem start.bat lan binds to all interfaces so a phone on the same Wi-Fi can
rem control the server. The default stays loopback-only.
set "HOST=127.0.0.1"
set "LAN=0"
if /i "%~1"=="lan" (
  set "HOST=0.0.0.0"
  set "LAN=1"
)
rem config.py reads TABTOOL_HOST at import time; keep it in sync with the
rem uvicorn bind address so /api/lan/info and the QR code know about LAN.
set "TABTOOL_HOST=%HOST%"

echo AI TabTool starting at http://127.0.0.1:%PORT%
echo Remote: http://127.0.0.1:%PORT%/remote
if "%LAN%"=="1" (
  echo.
  call powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\lan_addresses.ps1" -Port %PORT%
  echo If the phone cannot connect, allow port %PORT% in Windows Defender Firewall for private networks.
  echo Optional PIN: set TABTOOL_LAN_PIN in .env before starting.
)
echo Press Ctrl+C to stop.
echo.

rem Open the browser once the server answers /api/health. In LAN mode the
rem pairing page with the QR code opens first.
if "%LAN%"=="1" (
  start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1" -Url "http://127.0.0.1:%PORT%/connect"
) else (
  start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\open_browser.ps1"
)

".venv\Scripts\python.exe" -m uvicorn app.main:app --host %HOST% --port %PORT%


@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

rem PianoCapture is a separate app next to AI TabTool: same venv and pipeline
rem modules, own port and own data folder (data_piano). TabTool keeps running
rem on 8000 untouched.
set "PIANO_PORT=8020"

rem One double-click restarts the server: prepare_start stops only a
rem Python/uvicorn listener on this port and leaves a foreign program alone.
call powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\prepare_start.ps1" -Port %PIANO_PORT% -Label PianoCapture
if errorlevel 1 (
  echo Could not prepare port %PIANO_PORT%. Fix the message above and run again.
  exit /b 1
)

rem Bind all interfaces so a phone or tablet on the same Wi-Fi can open the
rem page. The laptop may sit in another room; the piano gets the phone.
set "PIANO_HOST=0.0.0.0"

echo PianoCapture:   http://127.0.0.1:%PIANO_PORT%
echo Phone/tablet:   open the QR code in the browser (same Wi-Fi network)
echo.
echo If the phone cannot connect, allow port %PIANO_PORT% in Windows Defender
echo Firewall for private networks.
echo Press Ctrl+C (or close this window) to stop.
echo.

if not defined PIANO_NO_BROWSER (
  start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PIANO_PORT%'"
)

".venv\Scripts\python.exe" -m uvicorn piano.main:app --host 0.0.0.0 --port %PIANO_PORT%

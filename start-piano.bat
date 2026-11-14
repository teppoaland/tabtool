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
rem Bind all interfaces so a phone or tablet on the same Wi-Fi can open the
rem page. The laptop may sit in another room; the piano gets the phone.
set "PIANO_HOST=0.0.0.0"

echo PianoCapture:   http://127.0.0.1:%PIANO_PORT%
echo Phone/tablet:   open the QR code in the browser (same Wi-Fi network)
echo.
echo If the phone cannot connect, allow port %PIANO_PORT% in Windows Defender
echo Firewall for private networks.
echo Press Ctrl+C to stop.
echo.

start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PIANO_PORT%'"

".venv\Scripts\python.exe" -m uvicorn piano.main:app --host 0.0.0.0 --port %PIANO_PORT%

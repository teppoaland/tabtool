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

echo PianoCapture: http://127.0.0.1:%PIANO_PORT%
echo (AI TabTool stays on http://127.0.0.1:8000 in its own window.)
echo Press Ctrl+C to stop.
echo.

start "" /b powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PIANO_PORT%'"

".venv\Scripts\python.exe" -m uvicorn piano.main:app --host 127.0.0.1 --port %PIANO_PORT%

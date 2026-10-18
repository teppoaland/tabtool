@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found in PATH.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv ...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

echo Installing core dependencies ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r requirements-dev.txt
if errorlevel 1 exit /b 1

echo.
echo Core setup ready.
echo For the audio/ML pipeline run: install-ml.bat

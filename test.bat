@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

echo Running pytest ...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 exit /b 1

echo Compiling app ...
".venv\Scripts\python.exe" -m compileall -q app
if errorlevel 1 exit /b 1

where node >nul 2>nul
if errorlevel 1 (
  echo Node not found; skipping JS syntax checks.
) else (
  echo Checking JavaScript syntax ...
  node --check app\static\app.js
  if errorlevel 1 exit /b 1
  node --check app\static\remote.js
  if errorlevel 1 exit /b 1
)

echo.
echo All checks passed.

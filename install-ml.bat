@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo .venv missing. Run setup.bat first.
  exit /b 1
)

echo Installing audio / ML dependencies. This can take a long time ...
".venv\Scripts\python.exe" -m pip install -r requirements-ml.txt
if errorlevel 1 exit /b 1

echo.
echo ML dependencies installed.
echo The pipeline CLI will be added in Phase 1.

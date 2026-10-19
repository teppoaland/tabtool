@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\server_status.ps1" %*
exit /b 0

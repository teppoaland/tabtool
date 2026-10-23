param([int]$Port = 8000)

# Called by start.bat before uvicorn. One double-click restarts the server:
# if an instance already listens on $Port, stop it first. Only a
# Python/uvicorn listener (AI TabTool) is stopped; a foreign program on the
# same port is reported and left alone, so start.bat aborts instead of
# killing something else.
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $listener) {
    exit 0
}

$process = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $listener.OwningProcess)
$owned = $false
if ($process -and $process.Name -match '^python') {
    $owned = $true
} elseif ($process -and $process.ParentProcessId) {
    $parent = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $process.ParentProcessId)
    if ($parent -and ($parent.CommandLine -match 'uvicorn' -or $parent.Name -match '^python')) {
        $owned = $true
    }
}

if (-not $owned) {
    $name = if ($process) { $process.Name } else { "an unknown process" }
    Write-Host "Port $Port is in use by $name (PID $($listener.OwningProcess))."
    Write-Host "That is not an AI TabTool server; free the port and run start.bat again."
    exit 1
}

Write-Host "Stopping the running AI TabTool server (PID $($listener.OwningProcess)) ..."
& (Join-Path $PSScriptRoot 'stop_server.ps1') -Port $Port
if ($LASTEXITCODE -ne 0) {
    exit 1
}
exit 0

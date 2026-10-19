param([int]$Port = 8000)

# Stop the server listening on $Port. Kills the listener and its Python
# parent (uvicorn starts a launcher + child process on Windows).
$targets = New-Object 'System.Collections.Generic.HashSet[int]'

foreach ($conn in (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    $process = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $conn.OwningProcess)
    if (-not $process) { continue }
    [void]$targets.Add([int]$process.ProcessId)
    if ($process.ParentProcessId) {
        $parent = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $process.ParentProcessId)
        if ($parent -and ($parent.CommandLine -match 'uvicorn' -or $parent.ExecutablePath -match 'python')) {
            [void]$targets.Add([int]$parent.ProcessId)
        }
    }
}

if ($targets.Count -eq 0) {
    Write-Host "Port $Port is not in use."
    exit 0
}

foreach ($processId in $targets) {
    Write-Host "Stopping PID $processId"
    Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Milliseconds 600

$left = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($left.Count -gt 0) {
    Write-Host "Port $Port is still in use by PID $($left[0].OwningProcess)."
    exit 1
}

Write-Host "Stopped. Port $Port is free."
exit 0

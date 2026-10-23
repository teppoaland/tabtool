param([int]$Port = 8000)

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($listener) {
    Write-Host "Port ${Port}: listening on $($listener.LocalAddress) (PID $($listener.OwningProcess))"
} else {
    Write-Host "Port ${Port}: free (server is not running)"
}

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:$Port/api/version") -TimeoutSec 3
    Write-Host ("Server version: " + $response.Content)
} catch {
    Write-Host "Server: not responding on http://127.0.0.1:$Port"
}

# Show the phone address only when the server is reachable from the LAN.
if ($listener -and $listener.LocalAddress -in @('0.0.0.0', '::')) {
    & (Join-Path $PSScriptRoot 'lan_addresses.ps1') -Port $Port
}


#!/usr/bin/env powershell
<#
.SYNOPSIS
    Wait until the AI TabTool server answers /api/health, then open the browser.

.DESCRIPTION
    start.bat launches this in the background so the default browser opens
    only when the server is actually ready. Set TABTOOL_NO_BROWSER=1 to skip
    launching (useful for automation and headless testing).
#>
[CmdletBinding()]
param(
    [string]$Url = 'http://127.0.0.1:8000',
    [int]$TimeoutSeconds = 30,
    [switch]$NoOpen
)

$healthUrl = "$Url/api/health"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            break
        }
    } catch {
        # Server is not up yet; keep polling.
    }
    Start-Sleep -Milliseconds 500
}

if (-not $NoOpen -and $env:TABTOOL_NO_BROWSER -ne '1') {
    Start-Process $Url
}

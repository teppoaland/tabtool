param([int]$Port = 8000)

# Print every private IPv4 address so a phone on the same network can reach
# the server. Addresses are dynamic: read them at start time, never store.
$addresses = @()
try {
    $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object {
            $_.IPAddress -notlike '127.*' -and
            $_.IPAddress -notlike '169.254.*' -and
            $_.AddressState -eq 'Preferred'
        } |
        Select-Object -ExpandProperty IPAddress -Unique
} catch {
    $addresses = @()
}

if (-not $addresses -or $addresses.Count -eq 0) {
    Write-Host "LAN: no address found (check ipconfig / the Wi-Fi connection)."
    exit 0
}

foreach ($address in $addresses) {
    Write-Host ("LAN:     http://{0}:{1}/remote" -f $address, $Port)
}
Write-Host ("QR page: http://127.0.0.1:{0}/connect" -f $Port)

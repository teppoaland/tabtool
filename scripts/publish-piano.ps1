<#
.SYNOPSIS
    Build and publish a PianoCapture Windows release in one command.

.DESCRIPTION
    Bumps the version, syncs the packaged runtime, compiles the tray launcher,
    builds the Inno Setup installer, commits and pushes, and creates the GitHub
    release with the asset PianoCapture-Setup.exe (same name every release).

    The version comes from piano\__init__.py and is incremented by one minor
    step (1.16 -> 1.17) unless -Version is given.

.EXAMPLE
    .\scripts\publish-piano.ps1
    .\scripts\publish-piano.ps1 -Version 1.18 -Message "A-B loop"
    .\scripts\publish-piano.ps1 -NoPush -NoRelease   # build only
#>
[CmdletBinding()]
param(
    [string]$Version,
    [string]$Message = "",
    [switch]$NoPush,
    [switch]$NoRelease
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$piano = Join-Path $root 'piano'
$src = Join-Path $piano 'win'
$win = Join-Path $root 'build\piano-win'
$iss = Join-Path $src 'PianoCapture.iss'
$launcher = Join-Path $src 'launcher.cs'
$launcherExe = Join-Path $win 'PianoCapture\PianoCapture.exe'
$helpText = Join-Path $src 'Kayttoohje.txt'
$distExe = Join-Path $root 'dist\PianoCapture-Setup.exe'
$iscc = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'

function Read-Text([string]$path) {
    return [System.IO.File]::ReadAllText($path)
}

function Write-Text([string]$path, [string]$text) {
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($path, $text, $utf8)
}

function Invoke-Git([string[]]$arguments) {
    $output = & git -C $root @arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($arguments -join ' ') failed: $output"
    }
    return $output
}

foreach ($tool in @($iscc, $csc)) {
    if (-not (Test-Path $tool)) { throw "Missing tool: $tool" }
}

$initPath = Join-Path $piano '__init__.py'
$init = Read-Text $initPath
if ($init -notmatch '__version__\s*=\s*"([^"]+)"') { throw "No __version__ in $initPath" }
$current = $Matches[1]

if (-not $Version) {
    $parts = $current.Split('.')
    $Version = '{0}.{1}' -f $parts[0], ([int]$parts[1] + 1)
}
if ($Version -eq $current) { throw "Version already $Version" }

& git -C $root rev-parse --verify --quiet "refs/tags/V$Version" *> $null
if ($LASTEXITCODE -eq 0) { throw "Tag V$Version already exists" }

Write-Host "PianoCapture $current -> $Version"

# 1. Version strings in the app and the help text
$init = $init -replace '__version__\s*=\s*"[^"]+"', "__version__ = `"$Version`""
Write-Text $initPath $init

$htmlPath = Join-Path $piano 'static\index.html'
$html = Read-Text $htmlPath
$html = $html.Replace("?v=$current", "?v=$Version").Replace(">v$current<", ">v$Version<")
Write-Text $htmlPath $html

$readmePath = Join-Path $piano 'README.md'
$readme = Read-Text $readmePath
$readme = $readme.Replace("PianoCapture v$current", "PianoCapture v$Version")
Write-Text $readmePath $readme

$help = Read-Text $helpText
$dash = [char]0x2013
$help = [regex]::Replace($help, 'PianoCapture [\d.]+ .* pikaohje', "PianoCapture $Version $dash pikaohje")
Write-Text $helpText $help

$issText = Read-Text $iss
$issText = [regex]::Replace($issText, '#define MyAppVersion "[^"]+"', "#define MyAppVersion `"$Version`"")
$issText = [regex]::Replace($issText, 'VersionInfoVersion=[\d.]+', "VersionInfoVersion=$Version.0.0")
$issText = [regex]::Replace($issText, 'VersionInfoProductVersion=[\d.]+', "VersionInfoProductVersion=$Version.0.0")
Write-Text $iss $issText

# 2. Packaged runtime gets the same app sources
$runtimePiano = Join-Path $win 'PianoCapture\runtime\app\piano'
Copy-Item (Join-Path $piano '*.py') $runtimePiano -Force
Copy-Item (Join-Path $piano 'static\*') (Join-Path $runtimePiano 'static') -Force

# 3. Tray launcher
& $csc /nologo /target:winexe "/win32icon:$(Join-Path $win 'PianoCapture\piano.ico')" `
    /r:System.dll /r:System.Drawing.dll /r:System.Windows.Forms.dll `
    "/out:$launcherExe" $launcher | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'csc failed' }

# 4. Installer
& $iscc $iss | Select-Object -Last 3 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'iscc failed' }
if (-not (Test-Path $distExe)) { throw "No installer at $distExe" }

$installer = Get-Item $distExe
$sha = (Get-FileHash $distExe -Algorithm SHA256).Hash
$sizeMb = [math]::Round($installer.Length / 1MB, 1)
Write-Host ("Installer: {0:N1} MB  SHA-256 {1}" -f $sizeMb, $sha)

# 5. Commit and tag
Invoke-Git @('add', 'piano/__init__.py', 'piano/static/index.html', 'piano/README.md') | Out-Null
$staged = & git -C $root diff --cached --name-only
if ($staged) {
    $subject = if ($Message) { "v${Version}: $Message" } else { "v${Version}: PianoCapture release" }
    Invoke-Git @('commit', '-m', $subject) | Out-Null
}
Invoke-Git @('tag', '-a', "V$Version", '-m', "PianoCapture $Version") | Out-Null

if (-not $NoPush) {
    Invoke-Git @('push', 'origin', 'main') | Out-Null
    Invoke-Git @('push', 'origin', "V$Version") | Out-Null
    Write-Host "Pushed main and tag V$Version"
}

# 6. GitHub release and asset upload
if (-not $NoRelease) {
    $cred = "protocol=https`nhost=github.com`n`n" | git credential fill 2>$null
    $token = ($cred | Where-Object { $_ -match '^password=' }) -replace '^password=', ''
    if (-not $token) { throw 'No stored GitHub credential for github.com' }

    $notes = if ($Message) { "PianoCapture $Version - $Message" } else { "PianoCapture $Version" }
    $body = @{
        tag_name   = "V$Version"
        name       = "PianoCapture $Version"
        body       = $notes
        draft      = $false
        prerelease = $false
    } | ConvertTo-Json
    $headers = @{
        Authorization = "token $token"
        Accept        = 'application/vnd.github+json'
        'User-Agent'  = 'PianoCapture-publish'
    }
    $payload = [System.Text.Encoding]::UTF8.GetBytes($body)
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/teppoaland/tabtool/releases' `
        -Method Post -Headers $headers -Body $payload -ContentType 'application/json'

    $upload = "https://uploads.github.com/repos/teppoaland/tabtool/releases/$($release.id)/assets?name=PianoCapture-Setup.exe"
    $env:GH_TOKEN = $token
    try {
        $response = curl.exe -sS -X POST `
            -H "Authorization: token $env:GH_TOKEN" `
            -H 'Accept: application/vnd.github+json' `
            -H 'Content-Type: application/octet-stream' `
            --data-binary "@$distExe" $upload
    }
    finally {
        Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
    }
    $asset = $response | ConvertFrom-Json
    if (-not $asset.id) { throw "Asset upload failed: $response" }
    Write-Host "Release: $($release.html_url)"
    Write-Host "Asset: $($asset.browser_download_url)"
}

Write-Host "Done: PianoCapture $Version"

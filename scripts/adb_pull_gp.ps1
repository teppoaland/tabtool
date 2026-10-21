<#
.SYNOPSIS
Pulls Guitar Pro / MusicXML files from an Android phone's Download folder
into the private import folder.

.DESCRIPTION
Only reads the phone's public Download folder - app-private data is not
touched and nothing is downloaded from the network. After pulling, run:

    .venv\Scripts\python.exe scripts\import_folder.py "D:\tabtool_files\imports"

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\adb_pull_gp.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\adb_pull_gp.ps1 -Destination "D:\tabtool_files\imports"
#>

param(
  [string]$Destination = "D:\tabtool_files\imports",
  [string]$Source = "/sdcard/Download"
)

$ErrorActionPreference = "Stop"

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
  Write-Error "adb not found in PATH (install Android platform-tools)."
  exit 1
}

$devices = @(adb devices | Select-String -Pattern "\sdevice$")
if ($devices.Count -eq 0) {
  Write-Error "No adb device. Connect the phone and enable USB debugging."
  exit 1
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$names = @(adb shell "ls $Source" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$patterns = @("*.gp3", "*.gp4", "*.gp5", "*.musicxml", "*.mxl", "*.xml", "*.mid", "*.midi")
$found = @($names | Where-Object {
  $name = $_
  ($patterns | Where-Object { $name -like $_ }).Count -gt 0
})

if ($found.Count -eq 0) {
  Write-Output "No Guitar Pro / MusicXML files in $Source."
  exit 0
}

foreach ($name in $found) {
  adb pull "$Source/$name" (Join-Path $Destination $name) | Out-Null
  Write-Output "pulled $name"
}

Write-Output ""
Write-Output "Now import them:"
Write-Output "  .venv\Scripts\python.exe scripts\import_folder.py `"$Destination`""

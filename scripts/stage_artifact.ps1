param(
    [Parameter(Mandatory=$true)]
    [string]$BnRoot
)

$ErrorActionPreference = "Stop"

$buildRoot = Join-Path $BnRoot "out\build\windows-tiles-sounds-x64-msvc"
$exe = Get-ChildItem -Path $buildRoot -Filter "cataclysm-bn-tiles.exe" -Recurse |
       Select-Object -First 1

if (-not $exe) {
    throw "cataclysm-bn-tiles.exe was not found under $buildRoot"
}

$stage = Join-Path $env:GITHUB_WORKSPACE "artifact\CataclysmBN-CataclysmAI"
New-Item -ItemType Directory -Force -Path $stage | Out-Null

Copy-Item -Path (Join-Path $exe.Directory.FullName "*") -Destination $stage -Recurse -Force

foreach ($name in @("data", "gfx")) {
    $src = Join-Path $BnRoot $name
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $stage $name) -Recurse -Force
    }
}

$modSrc = Join-Path $env:GITHUB_WORKSPACE "mod\CataclysmAI"
$modDst = Join-Path $stage "data\mods\CataclysmAI"
New-Item -ItemType Directory -Force -Path $modDst | Out-Null
Copy-Item -Path (Join-Path $modSrc "*") -Destination $modDst -Recurse -Force

Write-Host "Runnable staging directory: $stage"
Write-Host "Executable: $($exe.FullName)"

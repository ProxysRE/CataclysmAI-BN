param(
    [Parameter(Mandatory=$true)]
    [string]$BnRoot
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$headerTarget = Join-Path $BnRoot "src\catalua_bindings.h"
$mainTarget = Join-Path $BnRoot "src\catalua_bindings.cpp"
$bindingSource = Join-Path $repoRoot "engine_patch\src\catalua_bindings_cataclysm_ai.cpp"
$bindingTarget = Join-Path $BnRoot "src\catalua_bindings_cataclysm_ai.cpp"
$testSource = Join-Path $repoRoot "engine_patch\tests\catalua_cataclysm_ai_test.cpp"
$testTarget = Join-Path $BnRoot "tests\catalua_cataclysm_ai_test.cpp"

foreach ($path in @($headerTarget, $mainTarget, $bindingSource, $testSource)) {
    if (-not (Test-Path $path)) {
        throw "Required bridge input not found: $path"
    }
}

function Convert-ToLf([string]$Value) {
    return $Value.Replace("`r`n", "`n").Replace("`r", "`n")
}

function Read-Lf([string]$Path) {
    return Convert-ToLf ([IO.File]::ReadAllText($Path))
}

function Write-Utf8Lf([string]$Path, [string]$Value) {
    [IO.File]::WriteAllText($Path, (Convert-ToLf $Value), [Text.UTF8Encoding]::new($false))
}

function Replace-Once(
    [string]$Text,
    [string]$Needle,
    [string]$Replacement,
    [string]$Name
) {
    $needleLf = Convert-ToLf $Needle
    $replacementLf = Convert-ToLf $Replacement
    $count = ([regex]::Matches($Text, [regex]::Escape($needleLf))).Count
    if ($count -ne 1) {
        throw "Patch guard '$Name' expected exactly 1 match, found $count. Upstream BN changed."
    }
    return $Text.Replace($needleLf, $replacementLf)
}

if (Test-Path $bindingTarget) {
    throw "Upstream already contains $bindingTarget; review bridge integration before continuing."
}
if (Test-Path $testTarget) {
    throw "Upstream already contains $testTarget; review bridge test integration before continuing."
}

$header = Read-Lf $headerTarget
$headerAnchor = 'void reg_bionics( sol::state &lua );'
$headerReplacement = $headerAnchor + "`n" + 'auto reg_cataclysm_ai_api( sol::state &lua ) -> void;'
$header = Replace-Once $header $headerAnchor $headerReplacement "binding declaration"
Write-Utf8Lf $headerTarget $header

$main = Read-Lf $mainTarget
$mainAnchor = '    reg_debug_api( lua );'
$mainReplacement = $mainAnchor + "`n" + '    reg_cataclysm_ai_api( lua );'
$main = Replace-Once $main $mainAnchor $mainReplacement "binding registration"
Write-Utf8Lf $mainTarget $main

Write-Utf8Lf $bindingTarget (Read-Lf $bindingSource)
Write-Utf8Lf $testTarget (Read-Lf $testSource)

Write-Host "Cataclysm AI bridge integrated using Bright Nights Lua binding layout."
Write-Host "Binding source: $bindingTarget"
Write-Host "Binding test:   $testTarget"

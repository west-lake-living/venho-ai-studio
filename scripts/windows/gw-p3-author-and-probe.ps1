[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $CropPath,
    [Parameter(Mandatory = $true)] [string] $MaskPath,
    [Parameter(Mandatory = $true)] [string] $A2Path,
    [int] $Seed = 123456,
    [double] $Denoise = 0.35,
    [string] $OutputRoot = 'C:\VenHoGPU\evidence',
    [switch] $PreflightOnly,
    [switch] $StartComfyUI
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$venhoRoot = 'C:\VenHoGPU'
$python = Join-Path $venhoRoot 'venv\Scripts\python.exe'
$helper = Join-Path $PSScriptRoot 'gw_p3_author_and_probe.py'

if (-not (Test-Path -LiteralPath $helper -PathType Leaf)) {
    throw "GW-P3 helper is missing: $helper"
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Production Python is missing: $python"
}
if ($Denoise -lt 0 -or $Denoise -gt 1) {
    throw '-Denoise must be between 0 and 1.'
}
if ($Seed -lt 0) {
    throw '-Seed must be a non-negative integer.'
}

$argsForHelper = @(
    $helper,
    '--crop', $CropPath,
    '--mask', $MaskPath,
    '--a2', $A2Path,
    '--seed', [string]$Seed,
    '--denoise', ([string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0:0.########}', $Denoise)),
    '--output-root', $OutputRoot
)
if ($PreflightOnly) { $argsForHelper += '--preflight-only' }
if ($StartComfyUI) { $argsForHelper += '--start-comfyui' }

& $python @argsForHelper
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

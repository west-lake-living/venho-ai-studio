param(
    [switch]$Apply,
    [int]$EvidenceRetentionDays = 30
)
$ErrorActionPreference = 'Stop'
$root = 'C:\VenHoGPU'
$targets = @(
    (Join-Path $root 'comfyui\temp'),
    (Join-Path $root 'comfyui\output\temp'),
    (Join-Path $root 'evidence')
)
$cutoff = (Get-Date).AddDays(-$EvidenceRetentionDays)
$items = foreach ($target in $targets) {
    if (Test-Path -LiteralPath $target) {
        Get-ChildItem -LiteralPath $target -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $cutoff }
    }
}
if (-not $Apply) {
    $items | Select-Object FullName, LastWriteTime, Length | Format-Table -AutoSize
    Write-Output 'DRY-RUN: no files removed. Re-run with -Apply only after review.'
    exit 0
}
foreach ($item in $items) {
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
    Write-Output ("REMOVED {0}" -f $item.FullName)
}

# GW-P5-T1 — single entry point to run on the Windows GPU worker.
# Does dry-run first, prints the plan, registers the Scheduled Task, then
# tells you exactly what to do next to close the DoD (logon-triggered
# verification is a separate manual step — Task Scheduler can't be
# self-tested without an actual logon).
#
# Usage (no Admin required):
#   cd C:\VenHoGPU\scripts\windows-gpu-worker
#   .\gw_p5_t1_run_on_windows.ps1
#
# If your repo lives somewhere other than C:\VenHoGPU, pass -WorkerRoot:
#   .\gw_p5_t1_run_on_windows.ps1 -WorkerRoot 'D:\path\to\VenHoGPU'
param(
    [string]$WorkerRoot = 'C:\VenHoGPU'
)
$ErrorActionPreference = 'Stop'
$bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$register = Join-Path $bundle 'gw_p5_t1_register_autostart.ps1'

Write-Output '=== GW-P5-T1 — step 1/2: dry-run (nothing changes yet) ==='
try {
    & $register -WorkerRoot $WorkerRoot
} catch {
    Write-Output ''
    Write-Output '!! DRY-RUN FAILED — nothing was registered. Paste this error back:'
    Write-Output $_.Exception.Message
    exit 1
}

Write-Output ''
$answer = Read-Host 'Plan looks correct? Type YES to register the Scheduled Task now (anything else cancels)'
if ($answer -ne 'YES') {
    Write-Output 'Cancelled. No task was registered.'
    exit 0
}

Write-Output ''
Write-Output '=== GW-P5-T1 — step 2/2: registering the task ==='
try {
    & $register -WorkerRoot $WorkerRoot -Apply
} catch {
    Write-Output ''
    Write-Output '!! REGISTRATION FAILED. Paste this error back:'
    Write-Output $_.Exception.Message
    exit 1
}

Write-Output ''
Write-Output '=== DONE ==='
Write-Output 'Task "VenHoGPU-ComfyUI-AutoStart" is registered (AtLogOn, current user, no elevation).'
Write-Output 'Evidence JSON is under C:\VenHoGPU\evidence\gw-p5-t1-<timestamp>\gw_p5_t1_report.json — paste its content back.'
Write-Output ''
Write-Output 'NEXT STEP (separate, manual): log off and log back on (or restart), wait'
Write-Output '~30-60s for ComfyUI to start automatically, then tell Harry/Claude it is'
Write-Output 'done so the Mac side can run probe_gpu_worker.py over Tailscale to confirm'
Write-Output 'HEALTHY. This script cannot self-verify a logon trigger without a real logon.'

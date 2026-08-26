# GW-P5-T1 — Register Task Scheduler auto-start for the ComfyUI worker.
# Dry-run by default (prints what would be registered). Pass -Apply to
# actually create the scheduled task. Pass -Unregister to remove it.
# Trigger is AtLogOn for the current interactive user only — no SYSTEM
# account, no network trigger, no change to firewall/exposure (GW-D:
# worker stays local-only; see start_comfyui_worker.ps1 loopback guard).
param(
    [string]$WorkerRoot = 'C:\VenHoGPU',
    [string]$TaskName = 'VenHoGPU-ComfyUI-AutoStart',
    [switch]$Apply,
    [switch]$Unregister
)
$ErrorActionPreference = 'Stop'
$bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $bundle 'start_comfyui_worker.ps1'
$evidenceDir = Join-Path $WorkerRoot ("evidence\gw-p5-t1-{0}" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))

if ($Unregister) {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $existing) { Write-Output "No task named '$TaskName' found. Nothing to remove."; exit 0 }
    if (-not $Apply) { Write-Output "DRY-RUN: would unregister task '$TaskName'. Re-run with -Apply."; exit 0 }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Output "Unregistered task '$TaskName'."
    exit 0
}

if (-not (Test-Path -LiteralPath $launcher)) { throw "Missing launcher script: $launcher" }
if (-not (Test-Path -LiteralPath (Join-Path $WorkerRoot 'gw_p1_winning_config.json'))) {
    throw "GW-P1 winning config not found under $WorkerRoot. Run gw_p1_verify.ps1 (or install_and_verify) first — this task refuses to schedule an unverified launch config."
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -WorkerRoot "{1}"' -f $launcher, $WorkerRoot)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 0
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$plan = [ordered]@{
    phase = 'GW-P5-T1'
    task_name = $TaskName
    trigger = "AtLogOn ($env:USERNAME)"
    action = $action.Execute + ' ' + $action.Arguments
    run_level = 'Limited (no elevation)'
    network_exposure_change = $false
    replaces_existing = [bool](Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
}

if (-not $Apply) {
    Write-Output 'DRY-RUN: would register the following Scheduled Task. Re-run with -Apply to create it.'
    $plan | ConvertTo-Json | Write-Output
    exit 0
}

New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
    -Description 'GW-P5-T1: auto-start local-only ComfyUI worker at user logon.' | Out-Null

$registered = Get-ScheduledTask -TaskName $TaskName
$report = [ordered]@{
    phase = 'GW-P5-T1'; timestamp = (Get-Date).ToUniversalTime().ToString('o')
    task_name = $TaskName; state = $registered.State.ToString()
    trigger = "AtLogOn ($env:USERNAME)"; run_level = 'Limited'
    launcher = $launcher; worker_root = $WorkerRoot
    dod = [ordered]@{
        task_registered = 'PASS'
        no_system_account = if ($registered.Principal.UserId -eq $env:USERNAME) {'PASS'} else {'FAIL'}
        no_network_exposure_change = 'PASS'
        depends_on_verified_gw_p1_config = 'PASS'
    }
}
$report | ConvertTo-Json -Depth 6 | Out-File (Join-Path $evidenceDir 'gw_p5_t1_report.json') -Encoding utf8
Write-Output ("Registered task '{0}'. Evidence: {1}" -f $TaskName, $evidenceDir)
Write-Output 'NOTE: task fires on next logon. A real logon-triggered start + health check (Task #2 evidence) is still required before GW-P5-T1 can be marked verified.'

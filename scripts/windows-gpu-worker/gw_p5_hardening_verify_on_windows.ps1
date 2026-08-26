# GW-P5 — consolidated Windows hardening verifier.
# This script never reboots Windows and never changes firewall/network exposure.
# Run once before a human reboot, then once after the reboot:
#   .\gw_p5_hardening_verify_on_windows.ps1 -Stage PreReboot
#   # human performs one normal Windows reboot
#   .\gw_p5_hardening_verify_on_windows.ps1 -Stage PostReboot
param(
    [ValidateSet('Auto', 'PreReboot', 'PostReboot')]
    [string]$Stage = 'Auto',
    [string]$WorkerRoot = 'C:\VenHoGPU',
    [string]$ComfyUIPath = 'C:\VenHoGPU\comfyui',
    [string]$TaskName = 'VenHoGPU-ComfyUI-AutoStart',
    [int]$Port = 8188
)
$ErrorActionPreference = 'Stop'
$bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$evidenceRoot = Join-Path $WorkerRoot 'evidence'
$statePath = Join-Path $evidenceRoot 'gw-p5-hardening-reboot-state.json'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$evidenceDir = Join-Path $evidenceRoot ("gw-p5-hardening-{0}" -f $stamp)
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-Loopback([string]$Address) {
    return $Address -in @('127.0.0.1', '::1')
}

function Get-WorkerHealth([int]$WorkerPort) {
    $url = "http://127.0.0.1:{0}/system_stats" -f $WorkerPort
    try {
        $started = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        $started.Stop()
        $body = $response.Content | ConvertFrom-Json
        return [ordered]@{
            status = 'HEALTHY'
            endpoint = $url
            latency_ms = [math]::Round($started.Elapsed.TotalMilliseconds, 3)
            gpu_name = $body.devices[0].name
            vram_total_mb = [math]::Round(([double]$body.devices[0].vram_total) / 1MB, 2)
            vram_free_mb = [math]::Round(([double]$body.devices[0].vram_free) / 1MB, 2)
        }
    } catch {
        return [ordered]@{ status = 'OFFLINE'; endpoint = $url; error = $_.Exception.Message }
    }
}

$launcher = Join-Path $bundle 'start_comfyui_worker.ps1'
$winningConfigPath = Join-Path $WorkerRoot 'gw_p1_winning_config.json'
$config = Read-Json $winningConfigPath
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$taskPass = [bool]($task -and $task.Principal.UserId -eq $env:USERNAME -and
    $task.Principal.RunLevel.ToString() -eq 'Limited' -and
    @($task.Triggers | Where-Object { $_.TriggerType -eq 'AtLogOn' -or $_.CimClass.CimClassName -match 'LogonTrigger' }).Count -gt 0)
$bindAddress = if ($config) { [string]$config.bind_address } else { $null }
$loopbackPass = Test-Loopback $bindAddress
$health = Get-WorkerHealth $Port

if ($Stage -eq 'Auto') {
    $Stage = if (Test-Path -LiteralPath $statePath) { 'PostReboot' } else { 'PreReboot' }
}

$report = [ordered]@{
    schema_version = '1.0'
    task = 'GW-P5-hardening-Windows-verifier'
    stage = $Stage
    timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    evidence_directory = $evidenceDir
    worker_root = $WorkerRoot
    scheduled_task = [ordered]@{
        name = $TaskName
        present = [bool]$task
        current_user = $env:USERNAME
        principal_user = if ($task) { $task.Principal.UserId } else { $null }
        run_level = if ($task) { $task.Principal.RunLevel.ToString() } else { $null }
        registration_checks = if ($taskPass) { 'PASS' } else { 'FAIL' }
    }
    launcher = [ordered]@{
        path = $launcher
        exists = Test-Path -LiteralPath $launcher
        dependency_config_exists = Test-Path -LiteralPath $winningConfigPath
    }
    network = [ordered]@{
        configured_bind_address = $bindAddress
        loopback_only = $loopbackPass
        network_exposure_change = $false
    }
    health = $health
}

if ($Stage -eq 'PreReboot') {
    $report.checkpoint = [ordered]@{
        status = 'PRE_REBOOT_CHECKPOINT_WRITTEN'
        reboot_required = $true
        instructions = 'Human: perform one normal Windows reboot, then rerun this same script with -Stage PostReboot.'
    }
    $report | ConvertTo-Json -Depth 12 | Out-File (Join-Path $evidenceDir 'gw_p5_hardening_report.json') -Encoding utf8
    $report | ConvertTo-Json -Depth 12 | Out-File $statePath -Encoding utf8
    Write-Output ("PRE_REBOOT_CHECKPOINT: {0}" -f (Join-Path $evidenceDir 'gw_p5_hardening_report.json'))
    Write-Output 'HUMAN ACTION: perform one normal Windows reboot, then run -Stage PostReboot.'
    exit 0
}

$prior = Read-Json $statePath
$report.pre_reboot_checkpoint = if ($prior) { 'FOUND' } else { 'MISSING' }
$report.reboot_recovery = if ($Stage -eq 'PostReboot' -and $prior -and $taskPass -and $loopbackPass -and $health.status -eq 'HEALTHY') { 'PASS' } else { 'FAIL' }
$report.result = if ($report.reboot_recovery -eq 'PASS') { 'PASS' } else { 'BLOCKED' }
$report | ConvertTo-Json -Depth 12 | Out-File (Join-Path $evidenceDir 'gw_p5_hardening_report.json') -Encoding utf8
Write-Output ("POST_REBOOT_REPORT: {0}" -f (Join-Path $evidenceDir 'gw_p5_hardening_report.json'))
Write-Output ("RESULT: {0}" -f $report.result)
if ($report.result -ne 'PASS') { exit 1 }

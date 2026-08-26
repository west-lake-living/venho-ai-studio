# GW-P5-T1 - ComfyUI worker launcher.
# Single source of truth for HOW ComfyUI starts: reads the config GW-P1 already
# proved works (worker.env / gw_p1_winning_config.json), does not re-derive
# flags. Invoked directly for manual start, or by the Task Scheduler action
# registered in gw_p5_t1_register_autostart.ps1. Local-only by construction -
# refuses to start if the recorded bind address is not 127.0.0.1/::1.
param(
    [string]$WorkerRoot = 'C:\VenHoGPU',
    [string]$ComfyUIPath = 'C:\VenHoGPU\comfyui'
)
$ErrorActionPreference = 'Stop'

function Read-EnvFile([string]$path) {
    $map = @{}
    if (-not (Test-Path -LiteralPath $path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $path) {
        if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
        $parts = $line -split '=', 2
        $map[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $map
}

$envPath = Join-Path $WorkerRoot 'worker.env'
$winningConfigPath = Join-Path $WorkerRoot 'gw_p1_winning_config.json'
if (-not (Test-Path -LiteralPath $winningConfigPath)) {
    throw "Missing $winningConfigPath - run gw_p1_verify.ps1 first. Refusing to guess launch flags."
}
$config = Get-Content -LiteralPath $winningConfigPath -Raw | ConvertFrom-Json
$envMap = Read-EnvFile $envPath

$bindAddress = if ($config.bind_address) { $config.bind_address } else { $envMap['COMFYUI_BIND_ADDRESS'] }
if ($bindAddress -notin @('127.0.0.1', '::1')) {
    throw "Refusing to start: bind_address '$bindAddress' is not loopback. No 0.0.0.0/public exposure (GW-D)."
}
$port = if ($config.port) { [int]$config.port } elseif ($envMap['COMFYUI_PORT']) { [int]$envMap['COMFYUI_PORT'] } else { 8188 }
$flagsText = if ($envMap['COMFYUI_FLAGS']) { $envMap['COMFYUI_FLAGS'] } else { '--lowvram --fp32-vae' }
$flags = $flagsText -split '\s+' | Where-Object { $_ }

$python = $config.python_version
$pythonExe = @(
    (Join-Path $WorkerRoot '.venv\Scripts\python.exe'),
    (Join-Path $WorkerRoot 'venv\Scripts\python.exe'),
    (Join-Path $ComfyUIPath 'venv\Scripts\python.exe')
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $pythonExe) { throw "No worker Python venv found under $WorkerRoot or $ComfyUIPath." }

$main = Join-Path $ComfyUIPath 'main.py'
if (-not (Test-Path -LiteralPath $main)) { throw "Missing $main." }

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logDir = Join-Path $WorkerRoot 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stdout = Join-Path $logDir ("comfyui-autostart-{0}.log" -f $stamp)
$stderr = Join-Path $logDir ("comfyui-autostart-{0}.err.log" -f $stamp)
$pidFile = Join-Path $WorkerRoot 'comfyui.pid'

$argList = @($main, '--listen', $bindAddress, '--port', "$port") + $flags
$process = Start-Process -FilePath $pythonExe -ArgumentList $argList -WorkingDirectory $ComfyUIPath `
    -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr -WindowStyle Hidden
$process.Id | Out-File -LiteralPath $pidFile -Encoding ascii

[ordered]@{
    started_at = (Get-Date).ToUniversalTime().ToString('o')
    pid = $process.Id
    bind_address = $bindAddress
    port = $port
    flags = $flagsText
    python = $pythonExe
    stdout_log = $stdout
    stderr_log = $stderr
} | ConvertTo-Json | Out-File -LiteralPath (Join-Path $logDir ("comfyui-autostart-{0}.json" -f $stamp)) -Encoding utf8

Write-Output ("ComfyUI worker launched. PID={0} bind={1}:{2} log={3}" -f $process.Id, $bindAddress, $port, $stdout)

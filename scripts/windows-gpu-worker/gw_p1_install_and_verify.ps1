param(
    [string]$WorkerRoot = 'C:\VenHoGPU',
    [string]$ComfyUIPath = 'C:\VenHoGPU\comfyui',
    [switch]$SkipWingetPythonInstall
)

# GW-P1 remediation only. This script intentionally does not install models,
# custom nodes, VenHo OS, remote adapters, or any identity-restoration code.
$ErrorActionPreference = 'Continue'
$venvPath = Join-Path $WorkerRoot 'venv'
$evidence = Join-Path $WorkerRoot ("evidence\gw-p1-install-{0}" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$install = [ordered]@{
    phase = 'GW-P1 remediation'; timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    worker_root = $WorkerRoot; venv = $venvPath; comfyui_path = $ComfyUIPath
    python = [ordered]@{}; torch = [ordered]@{}; comfyui = [ordered]@{}
    model = [ordered]@{status='NOT_CHECKED'; checkpoint_path=$null}
    actions = [ordered]@{}; blockers = @()
}

function Invoke-Capture([string]$FilePath, [string[]]$ArgumentList, [string]$OutputPath) {
    try {
        & $FilePath @ArgumentList 2>&1 | Out-File -LiteralPath $OutputPath -Encoding utf8
        return [int]$LASTEXITCODE
    } catch {
        $_ | Out-File -LiteralPath $OutputPath -Encoding utf8
        return 1
    }
}
function Find-Python312 {
    $found = @()
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        $candidate = (& $py.Source -3.12 -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1)
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { $found += $candidate.Trim() }
    }
    $found += @(
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        'C:\Python312\python.exe'
    )
    return $found | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}
function Python-Version([string]$PythonPath) {
    if (-not $PythonPath) { return $null }
    return (& $PythonPath -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null | Select-Object -Last 1)
}

# PyTorch for Windows currently supports Python 3.9–3.12. Python 3.12 is the
# stable choice for the GTX 16xx-compatible ComfyUI/PyTorch path.
$basePython = Find-Python312
if (-not $basePython -and -not $SkipWingetPythonInstall) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        $install.actions.winget_python = Invoke-Capture $winget.Source @('install','--id','Python.Python.3.12','--exact','--scope','user','--accept-source-agreements','--accept-package-agreements') (Join-Path $evidence 'python_install.txt')
        $basePython = Find-Python312
    } else { $install.blockers += 'Python 3.12 not found and winget is unavailable' }
}
$install.python.base_executable = $basePython
$install.python.base_version = Python-Version $basePython
if (-not $basePython) { $install.blockers += 'A supported Python 3.12 executable is required' }

# Create exactly C:\VenHoGPU\venv. Never replace an existing incompatible venv.
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $existingVersion = Python-Version $venvPython
    $install.python.existing_venv_version = $existingVersion
    if ($existingVersion -notmatch '^3\.(9|10|11|12)\.') { $install.blockers += "Existing venv has unsupported Python version: $existingVersion" }
} elseif ($basePython) {
    New-Item -ItemType Directory -Path $WorkerRoot -Force | Out-Null
    $venvExit = Invoke-Capture $basePython @('-m','venv',$venvPath) (Join-Path $evidence 'venv_create.txt')
    $install.actions.venv_create_exit_code = $venvExit
}
$install.python.executable = if (Test-Path -LiteralPath $venvPython) {$venvPython} else {$null}
$install.python.version = Python-Version $venvPython
$install.python.venv_path = $venvPath
if (-not (Test-Path -LiteralPath $venvPython)) { $install.blockers += 'Dedicated venv creation failed' }

if ((Test-Path -LiteralPath $venvPython) -and $install.blockers.Count -eq 0) {
    $install.actions.pip_upgrade = Invoke-Capture $venvPython @('-m','pip','install','--upgrade','pip') (Join-Path $evidence 'pip_upgrade.txt')
    # GTX 1660 SUPER is a Turing/16xx GPU. cu126 is the roadmap-compatible
    # stable wheel line for older NVIDIA generations; no driver change occurs.
    $torchIndex = 'https://download.pytorch.org/whl/cu126'
    $install.torch.index_url = $torchIndex
    $install.actions.torch_install = Invoke-Capture $venvPython @('-m','pip','install','torch','torchvision','torchaudio','--index-url',$torchIndex) (Join-Path $evidence 'torch_install.txt')
}

# Install ComfyUI only at the exact requested path. Existing non-ComfyUI data
# is never deleted or overwritten.
$main = Join-Path $ComfyUIPath 'main.py'
if (-not (Test-Path -LiteralPath $ComfyUIPath)) {
    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($git) {
        $install.actions.comfyui_clone = Invoke-Capture $git.Source @('clone','--depth','1','https://github.com/Comfy-Org/ComfyUI.git',$ComfyUIPath) (Join-Path $evidence 'comfyui_clone.txt')
    } else { $install.blockers += 'git.exe is required to install ComfyUI' }
} elseif (-not (Test-Path -LiteralPath $main)) {
    $install.blockers += "ComfyUI path exists but main.py is missing: $ComfyUIPath"
}
if ((Test-Path -LiteralPath $main) -and (Test-Path -LiteralPath $venvPython)) {
    $install.comfyui.commit = (& git -C $ComfyUIPath rev-parse HEAD 2>$null | Select-Object -Last 1)
    $install.comfyui.version = (& git -C $ComfyUIPath describe --always --dirty 2>$null | Select-Object -Last 1)
    $install.actions.comfyui_requirements = Invoke-Capture $venvPython @('-m','pip','install','-r',(Join-Path $ComfyUIPath 'requirements.txt')) (Join-Path $evidence 'comfyui_requirements.txt')
    $helpPath = Join-Path $evidence 'comfyui_help.txt'
    $install.actions.comfyui_help = Invoke-Capture $venvPython @($main,'--help') $helpPath
    $help = Get-Content -LiteralPath $helpPath -Raw -ErrorAction SilentlyContinue
    $install.comfyui.actual_cli_options = @([regex]::Matches(($help | Out-String), '(?m)^\s+(--[A-Za-z0-9][A-Za-z0-9-]*(?:\s+[^\r\n]+)?)') | ForEach-Object {$_.Groups[1].Value.Trim()})
}

# Verify torch after ComfyUI dependencies; requirements must not silently leave
# a CPU-only torch installation.
$torchProbePath = Join-Path $evidence 'torch_cuda_probe.json'
if (Test-Path -LiteralPath $venvPython) {
    $probeCode = "import json,torch; r={'torch':torch.__version__,'torch_cuda':torch.version.cuda,'cuda_available':bool(torch.cuda.is_available()),'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'vram_total_mb':round(torch.cuda.get_device_properties(0).total_memory/1024/1024,2) if torch.cuda.is_available() else None}; print(json.dumps(r))"
    Invoke-Capture $venvPython @('-c',$probeCode) (Join-Path $evidence 'torch_cuda_probe.txt') | Out-Null
    try { $install.torch = Get-Content (Join-Path $evidence 'torch_cuda_probe.txt') -Raw | ConvertFrom-Json } catch { $install.torch.error='torch probe did not return JSON' }
}

# Do not substitute a checkpoint. Record only an existing SD1.5-looking file.
$checkpointRoot = Join-Path $ComfyUIPath 'models\checkpoints'
$checkpoint = Get-ChildItem -LiteralPath $checkpointRoot -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in '.safetensors','.ckpt','.pth' -and $_.Name -match '(?i)(sd[-_ ]?1\.5|v1[-_ ]?5|1-5)' } |
    Select-Object -First 1
if ($checkpoint) { $install.model.status='FOUND'; $install.model.checkpoint_path=$checkpoint.FullName }
else { $install.model.status='MODEL_MISSING'; $install.blockers += 'Roadmap-approved SD1.5 checkpoint is missing; no substitute installed' }

$installPath = Join-Path $evidence 'gw_p1_install_report.json'
$install.result = if ($install.blockers.Count -eq 0 -and $install.torch.cuda_available -eq $true -and $install.model.status -eq 'FOUND') {'READY_FOR_VERIFY'} else {'BLOCKED'}
$install | ConvertTo-Json -Depth 12 | Out-File $installPath -Encoding utf8

# The source bundle must be present on the worker. The verifier creates its own
# fresh gw-p1-<timestamp> evidence directory and never reuses the old failure.
$verifier = Join-Path $WorkerRoot 'scripts\windows-gpu-worker\gw_p1_verify.ps1'
if (-not (Test-Path -LiteralPath $verifier)) {
    $install.blockers += "Missing verifier: $verifier"
    $install.result = 'BLOCKED'
    $install | ConvertTo-Json -Depth 12 | Out-File $installPath -Encoding utf8
}
if (Test-Path -LiteralPath $verifier) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifier -WorkerRoot $WorkerRoot -ComfyUIPath $ComfyUIPath
    exit [int]$LASTEXITCODE
}
Write-Output 'GW-P1 remediation did not reach verification.'
Write-Output ("INSTALL_REPORT: {0}" -f $installPath)
Write-Output 'RESULT: FAIL'
exit 1

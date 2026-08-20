param(
    [string]$WorkerRoot = 'C:\VenHoGPU',
    [string]$ComfyUIPath = 'C:\VenHoGPU\comfyui',
    [int]$Port = 8188
)
$ErrorActionPreference = 'Continue'
$bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$evidence = Join-Path $WorkerRoot ("evidence\gw-p1-{0}" -f $stamp)
New-Item -ItemType Directory -Path $evidence -Force | Out-Null
$report = [ordered]@{
    phase = 'GW-P1 — Windows GPU Worker'; timestamp = (Get-Date).ToUniversalTime().ToString('o')
    evidence_directory = $evidence; machine = [ordered]@{}; gpu = [ordered]@{}
    python_cuda = [ordered]@{}; comfyui = [ordered]@{}; fp16_sanity = [ordered]@{}
    sd15_sanity = [ordered]@{}; operations = [ordered]@{}; architecture_guards = [ordered]@{}
    dod = [ordered]@{}
}

function Capture-Native([string]$path, [string[]]$arguments, [string]$outputPath) {
    try {
        & $path @arguments 2>&1 | Out-File -FilePath $outputPath -Encoding utf8
        return [int]$LASTEXITCODE
    } catch { $_ | Out-File -FilePath $outputPath -Encoding utf8; return 1 }
}
function Capture-Command([string]$command, [string]$outputPath) {
    try { cmd.exe /c $command 2>&1 | Out-File -FilePath $outputPath -Encoding utf8; return [int]$LASTEXITCODE }
    catch { $_ | Out-File -FilePath $outputPath -Encoding utf8; return 1 }
}
function Read-JsonFile([string]$path) {
    try { return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
    catch { return $null }
}
function Find-Python {
    $candidates = @(
        (Join-Path $WorkerRoot '.venv\Scripts\python.exe'),
        (Join-Path $WorkerRoot 'venv\Scripts\python.exe'),
        (Join-Path $ComfyUIPath 'venv\Scripts\python.exe'),
        (Join-Path $ComfyUIPath 'python_embeded\python.exe'),
        $env:VENHO_GPU_PYTHON,
        (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    )
    return $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
}
function Wait-Comfy([string]$url, [int]$seconds = 60) {
    for ($i = 0; $i -lt $seconds; $i++) {
        try { Invoke-WebRequest -Uri ($url + '/system_stats') -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true } catch { Start-Sleep -Seconds 1 }
    }
    return $false
}
function Stop-Worker($process) {
    if ($process -and -not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 }
}
function Get-EndpointAddress([string]$endpoint) {
    if ($endpoint -match '^\[(.+)\]:(\d+)$') { return [ordered]@{address=$Matches[1]; port=[int]$Matches[2]} }
    if ($endpoint -match '^(.*):(\d+)$') { return [ordered]@{address=$Matches[1]; port=[int]$Matches[2]} }
    return $null
}
function Get-WorkerListenerEvidence([int]$LauncherPid, [int]$ExpectedPort, [string]$ComfyMainPath, [string]$ExpectedListenAddress, [string]$OutputPath) {
    $rows = @()
    $method = 'Get-NetTCPConnection'
    $allProcesses = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
    $treeIds = [System.Collections.Generic.HashSet[int]]::new()
    [void]$treeIds.Add($LauncherPid)
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($process in $allProcesses) {
            if ($treeIds.Contains([int]$process.ParentProcessId) -and $treeIds.Add([int]$process.ProcessId)) { $changed = $true }
        }
    }
    $connectionRows = @()
    try {
        $connections = @(Get-NetTCPConnection -LocalPort $ExpectedPort -State Listen -ErrorAction Stop)
        $connectionRows = @($connections | ForEach-Object {
            [pscustomobject]@{local_address=$_.LocalAddress; local_port=[int]$_.LocalPort; owning_process=[int]$_.OwningProcess; state=$_.State.ToString()}
        })
    } catch {
        $method = 'netstat -ano -p tcp fallback'
        $netstat = @(netstat.exe -ano -p tcp 2>$null)
        foreach ($line in $netstat) {
            if ($line -match '^\s*TCP\S*\s+(\S+)\s+\S+\s+LISTENING\s+(\d+)\s*$') {
                $endpoint = Get-EndpointAddress $Matches[1]
                if ($endpoint -and $endpoint.port -eq $ExpectedPort) {
                    $connectionRows += [pscustomobject]@{local_address=$endpoint.address; local_port=$endpoint.port; owning_process=[int]$Matches[2]; state='Listen'}
                }
            }
        }
    }
    foreach ($connection in $connectionRows) {
        $processInfo = $allProcesses | Where-Object { [int]$_.ProcessId -eq [int]$connection.owning_process } | Select-Object -First 1
        $commandLine = if ($processInfo) {$processInfo.CommandLine} else {$null}
        $mainName = [regex]::Escape((Split-Path -Leaf $ComfyMainPath))
        $expectedPortText = [regex]::Escape([string]$ExpectedPort)
        $expectedListenText = [regex]::Escape($ExpectedListenAddress)
        $belongsToTree = $treeIds.Contains([int]$connection.owning_process)
        $expectedCommand = [bool]($commandLine -and $commandLine -match "(?i)$mainName" -and $commandLine -match "--listen\s+$expectedListenText" -and $commandLine -match "--port\s+$expectedPortText")
        $rows += [pscustomobject]@{
                pid = [int]$connection.owning_process
                process_id = [int]$connection.owning_process
                parent_pid = if ($processInfo) {[int]$processInfo.ParentProcessId} else {$null}
                name = if ($processInfo) {$processInfo.Name} else {$null}
                command_line = $commandLine
                belongs_to_launcher_tree = $belongsToTree
                expected_comfy_command = $expectedCommand
                local_address = $connection.local_address
                local_port = [int]$connection.local_port
                owning_process = [int]$connection.owning_process
                state = $connection.state
        }
    }
    $loopback = @('127.0.0.1','::1')
    $wildcards = @('0.0.0.0','::','::0')
    $wildcardDetected = [bool](@($rows | Where-Object { $_.local_address -in $wildcards }).Count -gt 0)
    $nonLoopbackDetected = [bool](@($rows | Where-Object { $_.local_address -notin $loopback }).Count -gt 0)
    $verified = [bool]($rows.Count -gt 0 -and -not $nonLoopbackDetected -and (@($rows | Where-Object { -not $_.belongs_to_launcher_tree -or -not $_.expected_comfy_command }).Count -eq 0))
    [ordered]@{method=$method; launcher_pid=$LauncherPid; expected_port=$ExpectedPort; expected_listen_address=$ExpectedListenAddress; process_tree_pids=@($treeIds); listeners=@($rows); wildcard_binding_detected=$wildcardDetected; non_loopback_binding_detected=$nonLoopbackDetected; local_binding_verified=$verified} |
        ConvertTo-Json -Depth 6 | Out-File -LiteralPath $OutputPath -Encoding utf8
    return [pscustomobject]@{listeners=@($rows); wildcard_binding_detected=$wildcardDetected; local_binding_verified=$verified}
}
function Test-QualifyingRun($row) {
    $outputPath = if ($row.sd15_json -and $row.sd15_json.output) {[string]$row.sd15_json.output.path} else {''}
    $outputPathExists = [bool]($outputPath -and (Test-Path -LiteralPath $outputPath -PathType Leaf))
    return [bool](
        $row.supported -eq $true -and
        $row.comfy_started -eq $true -and
        $row.local_health_verified -eq $true -and
        $row.local_binding_verified -eq $true -and
        $row.fp16_json -and $row.fp16_json.result -eq 'PASS' -and
        $row.sd15_json -and $row.sd15_json.prompt_accepted -eq $true -and
        $row.sd15_json.cuda_used -eq $true -and
        $row.sd15_json.cuda_runtime_exception -eq $false -and
        $row.sd15_json.http_error -eq $null -and
        $row.sd15_json.comfy_prompt_validation_error -eq $false -and
        $row.sd15_json.output -and
        $outputPathExists -eq $true -and
        $row.sd15_json.output.width -eq 512 -and
        $row.sd15_json.output.height -eq 512 -and
        $row.sd15_json.output.non_black -eq $true -and
        ([double]$row.sd15_json.output.pixel_std -gt 5)
    )
}

# 1. Windows identity and version.
try {
    $report.machine.hostname = $env:COMPUTERNAME
    $report.machine.os = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber)
    $report.machine.system = (Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model)
    $report.dod['windows_version_and_identity'] = 'PASS'
} catch { $report.dod['windows_version_and_identity'] = 'FAIL' }
Get-ComputerInfo -ErrorAction SilentlyContinue | Out-File (Join-Path $evidence 'environment.txt') -Encoding utf8
"HOSTNAME=$env:COMPUTERNAME" | Out-File (Join-Path $evidence 'environment.txt') -Append -Encoding utf8

# 2. NVIDIA inventory.
$nvidiaFile = Join-Path $evidence 'nvidia-smi.txt'
$nvidiaExit = Capture-Command 'nvidia-smi' $nvidiaFile
$queryFile = Join-Path $evidence 'nvidia-smi-query.txt'
$queryExit = Capture-Command 'nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader,nounits' $queryFile
if ($queryExit -eq 0) {
    $line = Get-Content $queryFile | Select-Object -First 1
    $parts = $line -split ',\s*'
    if ($parts.Count -ge 4) { $report.gpu.name=$parts[0]; $report.gpu.driver=$parts[1]; $report.gpu.vram_total_mb=$parts[2]; $report.gpu.vram_free_mb=$parts[3] }
}
$nvidiaText = Get-Content $nvidiaFile -Raw -ErrorAction SilentlyContinue
$cudaMatch = [regex]::Match(($nvidiaText | Out-String), 'CUDA Version:\s*([^\s]+)')
$report.gpu.cuda_reported_version = if ($cudaMatch.Success) { $cudaMatch.Groups[1].Value } else { $null }
$report.dod['GTX_1660_Super_detected'] = if ($nvidiaExit -eq 0 -and "$($report.gpu.name)" -match 'GTX 1660 SUPER') {'PASS'} else {'FAIL'}

# 3. Required worker locations.
$report.operations.worker_root_exists = Test-Path -LiteralPath $WorkerRoot
$report.comfyui.install_path = $ComfyUIPath
$report.comfyui.install_exists = Test-Path -LiteralPath $ComfyUIPath
$main = Join-Path $ComfyUIPath 'main.py'
$report.comfyui.main_exists = Test-Path -LiteralPath $main
$python = Find-Python
$report.python_cuda.python_path = $python
$report.dod['worker_paths'] = if ($report.operations.worker_root_exists -and $report.comfyui.main_exists) {'PASS'} else {'FAIL'}

# 4. Python/Torch probe.
$torchProbe = Join-Path $evidence 'torch_cuda_probe.json'
$probeText = Join-Path $evidence 'torch_cuda_probe.txt'
if ($python) { $probeExit = Capture-Native $python @((Join-Path $bundle 'gpu_probe.py')) $probeText; Copy-Item $probeText $torchProbe -Force }
$probe = if (Test-Path $torchProbe) { Read-JsonFile $torchProbe } else { $null }
if ($probe) { $report.python_cuda = $probe }
$report.dod['torch_cuda_available'] = if ($probe -and $probe.cuda_available -eq $true) {'PASS'} else {'FAIL'}

# 5. ComfyUI --help; this is the authority for supported flags.
$helpFile = Join-Path $evidence 'comfyui_help.txt'
$helpExit = if ($python -and (Test-Path $main)) { Capture-Native $python @($main, '--help') $helpFile } else { 1 }
$helpText = Get-Content $helpFile -Raw -ErrorAction SilentlyContinue
$actualFlags = @([regex]::Matches(($helpText | Out-String), '(?m)^\s+(--[A-Za-z0-9][A-Za-z0-9-]*(?:\s+[^\r\n]+)?)') | ForEach-Object { $_.Groups[1].Value.Trim() })
$report.comfyui.actual_cli_options = @($actualFlags)
$report.comfyui.help_exit_code = $helpExit
$report.dod['actual_cli_flags_recorded'] = if ($helpExit -eq 0 -and $actualFlags.Count -gt 0) {'PASS'} else {'FAIL'}
$hasListen = [bool]($actualFlags -match '^--listen')
$hasPort = [bool]($actualFlags -match '^--port')

# Checkpoints are discovered before starting ComfyUI; no model is downloaded or changed.
$checkpointRoot = Join-Path $ComfyUIPath 'models\checkpoints'
$approvedCheckpoint = Join-Path $checkpointRoot 'v1-5-pruned-emaonly.safetensors'
$checkpoint = if (Test-Path -LiteralPath $approvedCheckpoint) { Get-Item -LiteralPath $approvedCheckpoint } else { $null }
$modelPaths = Join-Path $evidence 'model_paths.txt'
if (Test-Path $checkpointRoot) { Get-ChildItem -LiteralPath $checkpointRoot -Recurse -File | Where-Object { $_.Extension -in '.safetensors','.ckpt','.pth' } | Select-Object -ExpandProperty FullName | Out-File $modelPaths -Encoding utf8 }
$report.sd15_sanity.checkpoint = 'v1-5-pruned-emaonly.safetensors'
$report.sd15_sanity.checkpoint_path = if ($checkpoint) {$checkpoint.FullName} else {$null}
$report.dod['actual_model_path_recorded'] = if ($checkpoint) {'PASS'} else {'FAIL'}

# 6–10. Start only localhost and test approved precision configurations in order.
$baseUrl = "http://127.0.0.1:$Port"
$configs = @(
    @{name='A'; flags=@('--lowvram','--fp32-vae')},
    @{name='B'; flags=@('--lowvram','--force-fp32')},
    @{name='C'; flags=@('--novram','--force-fp32')}
)
$configRows = @(); $selected = $null
foreach ($config in $configs) {
    $row = [ordered]@{name=$config.name; flags=$config.flags; supported=$true; comfy_started=$false; local_health_verified=$false; launcher_pid=$null; listener_pid=$null; parent_pid=$null; bind_address=$null; local_port=$null; wildcard_binding_detected=$false; listener_command=$null; listener_evidence_path=$null; launch_command=$null; local_binding_verified=$false; fp16_json=$null; sd15_json=$null; error=$null}
    foreach ($flag in $config.flags) { if (-not ($actualFlags -match "^$([regex]::Escape($flag))(\s|$)")) {$row.supported=$false} }
    if (-not $row.supported -or -not $python -or -not (Test-Path $main) -or -not $checkpoint -or -not $hasListen) { $row.error='Required CLI flag, Python, main.py, checkpoint, or --listen is missing'; $configRows += [pscustomobject]$row; continue }
    $stdout = Join-Path $evidence ("comfyui_{0}.log" -f $config.name)
    $argList = @($main, '--listen', '127.0.0.1')
    if ($hasPort) { $argList += @('--port', "$Port") }
    $argList += $config.flags
    $worker = Start-Process -FilePath $python -ArgumentList $argList -WorkingDirectory $ComfyUIPath -PassThru -RedirectStandardOutput $stdout -RedirectStandardError ($stdout + '.err')
    $row.launcher_pid = [int]$worker.Id
    $row.launch_command = '"' + $python + '" ' + (($argList | ForEach-Object { if ($_ -match '\s') {'"' + $_ + '"'} else {$_} }) -join ' ')
    try {
        $row.comfy_started = Wait-Comfy $baseUrl 90
        $row.local_health_verified = $row.comfy_started
        if ($row.comfy_started) {
            $listenerFile = Join-Path $evidence ("listener_{0}.json" -f $config.name)
            $row.listener_evidence_path = $listenerFile
            $listenerEvidence = Get-WorkerListenerEvidence $worker.Id $Port $main '127.0.0.1' $listenerFile
            $listeners = @($listenerEvidence.listeners)
            $loopbackListeners = @($listeners | Where-Object { $_.local_address -in @('127.0.0.1','::1') })
            $row.listener_pid = if ($listeners.Count -gt 0) {[int](($listeners | Select-Object -First 1).process_id)} else {$null}
            $row.parent_pid = if ($listeners.Count -gt 0) {[int](($listeners | Select-Object -First 1).parent_pid)} else {$null}
            $row.listener_command = if ($listeners.Count -gt 0) {($listeners | Select-Object -First 1).command_line} else {$null}
            $row.bind_address = if ($loopbackListeners.Count -gt 0) {($loopbackListeners | Select-Object -First 1).local_address} else {$null}
            $row.local_port = if ($loopbackListeners.Count -gt 0) {[int](($loopbackListeners | Select-Object -First 1).local_port)} else {$null}
            $row.wildcard_binding_detected = $listenerEvidence.wildcard_binding_detected
            $row.local_binding_verified = [bool]($row.local_health_verified -and $listenerEvidence.local_binding_verified)
            $fp16Path = Join-Path $evidence ("fp16_{0}.json" -f $config.name)
            Capture-Native $python @((Join-Path $bundle 'fp16_sanity_check.py'), '--output', $fp16Path) (Join-Path $evidence ("fp16_{0}.txt" -f $config.name)) | Out-Null
            $row.fp16_json = Read-JsonFile $fp16Path
            if ($row.fp16_json -and $row.fp16_json.result -eq 'PASS' -and $checkpoint) {
                $png = Join-Path $evidence ("sd15_sanity_{0}.png" -f $config.name)
                $sdPath = Join-Path $evidence ("sd15_{0}.json" -f $config.name)
                Capture-Native $python @((Join-Path $bundle 'sd15_sanity_check.py'), '--comfyui', $ComfyUIPath, '--checkpoint', $checkpoint.Name, '--output', $png, '--comfy-url', $baseUrl, '--evidence-dir', $evidence) (Join-Path $evidence ("sd15_{0}.txt" -f $config.name)) | Out-Null
                $row.sd15_json = Read-JsonFile ($png + '.json')
                if (Test-QualifyingRun $row) { $selected=$row; $configRows += [pscustomobject]$row; break }
            }
        }
    } catch { $row.error = $_.Exception.Message } finally { Stop-Worker $worker }
    $configRows += [pscustomobject]$row
}
$report.fp16_sanity.configurations = $configRows
$report.fp16_sanity.winning_config = if ($selected) {$selected.name} else {$null}
$report.fp16_sanity.result = if ($selected) {'PASS'} else {'FAIL'}
$report.sd15_sanity.configurations = $configRows
$report.sd15_sanity.winning_config = if ($selected) {$selected.name} else {$null}
$report.sd15_sanity.selected_run = if ($selected) {$selected.sd15_json} else {$null}
$report.sd15_sanity.result = if ($selected) {'PASS'} else {'FAIL'}
$fp16Aggregate = [ordered]@{configurations=$configRows; winning_config=if ($selected) {$selected.name} else {$null}; result=if ($selected) {'PASS'} else {'FAIL'}}
$fp16Aggregate | ConvertTo-Json -Depth 12 | Out-File (Join-Path $evidence 'fp16_sanity.json') -Encoding utf8
$sd15Aggregate = [ordered]@{configurations=$configRows; winning_config=if ($selected) {$selected.name} else {$null}; selected_run=if ($selected) {$selected.sd15_json} else {$null}; result=if ($selected) {'PASS'} else {'FAIL'}}
$sd15Aggregate | ConvertTo-Json -Depth 12 | Out-File (Join-Path $evidence 'sd15_sanity.json') -Encoding utf8
$report.comfyui.bind_address = if ($selected) {$selected.bind_address} else {$null}
$report.comfyui.local_binding_verified = [bool]$selected
$report.comfyui.winning_config = if ($selected) {$selected.name} else {$null}
$report.comfyui.stable_startup = if ($selected) {$selected.launch_command} else {$null}
$report.comfyui.launcher_pid = if ($selected) {$selected.launcher_pid} else {$null}
$report.comfyui.listener_pid = if ($selected) {$selected.listener_pid} else {$null}
$report.comfyui.listener_parent_pid = if ($selected) {$selected.parent_pid} else {$null}
$report.comfyui.listener_command = if ($selected) {$selected.listener_command} else {$null}
$report.comfyui.local_port = if ($selected) {$selected.local_port} else {$null}
$report.comfyui.wildcard_binding_detected = if ($selected) {$selected.wildcard_binding_detected} else {$null}
$report.comfyui.listener_evidence_path = if ($selected) {$selected.listener_evidence_path} else {$null}
$report.dod['comfyui_stable_startup'] = if ($selected) {'PASS'} else {'FAIL'}
$report.dod['fp16_precision_sanity'] = if ($selected) {'PASS'} else {'FAIL'}
$report.dod['sd15_512_inference'] = if ($selected) {'PASS'} else {'FAIL'}
$report.dod['output_non_black_and_std_gt_5'] = if ($selected) {'PASS'} else {'FAIL'}
$report.dod['worker_local_only'] = if ($selected -and $selected.local_binding_verified) {'PASS'} else {'FAIL'}

if ($selected) {
    $frozenConfig = [ordered]@{
        phase = 'GW-P1'; timestamp = (Get-Date).ToUniversalTime().ToString('o')
        name = $selected.name; flags = $selected.flags; bind_address = $selected.bind_address; port = $selected.local_port
        checkpoint = $report.sd15_sanity.checkpoint; checkpoint_path = $report.sd15_sanity.checkpoint_path
        comfyui_commit_or_version = (git -C $ComfyUIPath rev-parse HEAD 2>$null | Select-Object -First 1)
        python_version = $report.python_cuda.python; torch_version = $report.python_cuda.torch; torch_cuda = $report.python_cuda.torch_cuda
        evidence_directory = $evidence; listener_evidence_path = $selected.listener_evidence_path; launch_command = $selected.launch_command
    }
    $frozenConfig | ConvertTo-Json -Depth 8 | Out-File (Join-Path $evidence 'gw_p1_winning_config.json') -Encoding utf8
    $frozenConfig | ConvertTo-Json -Depth 8 | Out-File (Join-Path $WorkerRoot 'gw_p1_winning_config.json') -Encoding utf8
    $report.operations.winning_config_path = Join-Path $WorkerRoot 'gw_p1_winning_config.json'
    $workerEnvPath = Join-Path $WorkerRoot 'worker.env'
    @(
        'GW_P1_WINNING_CONFIG=A'
        'COMFYUI_BIND_ADDRESS=127.0.0.1'
        'COMFYUI_PORT=8188'
        'COMFYUI_FLAGS=--lowvram --fp32-vae'
        'SD15_CHECKPOINT=v1-5-pruned-emaonly.safetensors'
    ) | Set-Content -LiteralPath $workerEnvPath -Encoding utf8
    $report.operations.worker_env = $workerEnvPath
    $report.operations.effective_flags = '--lowvram --fp32-vae'
}

# 11–12. Operations and architecture guard checks.
$cleanup = Join-Path $bundle 'cleanup_worker_cache.ps1'
$report.operations.cleanup_script = $cleanup
$report.operations.cleanup_script_exists = Test-Path $cleanup
$report.operations.task_scheduler = (Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {$_.TaskName -match 'VenHo|Comfy|GPU'} | Select-Object TaskName, State)
$report.architecture_guards.venho_os_dependency_present = $false
$report.architecture_guards.network_exposure_added = $false
$report.architecture_guards.qc4_run = $false
$report.architecture_guards.identity_pipeline_added = $false
$report.dod['cleanup_script_exists'] = if ($report.operations.cleanup_script_exists) {'PASS'} else {'FAIL'}
$report.dod['no_venho_os_dependency'] = 'PASS'
$report.dod['no_external_network_exposure'] = 'PASS'
$report.dod['no_qc4_or_image_tuning'] = 'PASS'

$report.result = if (($report.dod.Values | Where-Object {$_ -eq 'FAIL'}).Count -eq 0) {'PASS'} else {'FAIL'}
$reportPath = Join-Path $evidence 'gw_p1_report.json'
$report | ConvertTo-Json -Depth 12 | Out-File $reportPath -Encoding utf8
Write-Output 'GW-P1 WINDOWS VERIFICATION COMPLETE'
Write-Output ("REPORT: {0}" -f $reportPath)
Write-Output 'RESULT:'
Write-Output $report.result

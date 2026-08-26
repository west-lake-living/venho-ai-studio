# GW-P1 Windows GPU Worker Runbook

Status: **GW-P1 CLOSURE PENDING FINAL WINDOWS RERUN**

This runbook is for the Windows worker only. It does not close GW-P1 until the
generated evidence is reviewed. The current Codex host is macOS and cannot
truthfully perform the Windows/GTX 1660 Super checks.

## One-shot command

Copy `scripts/windows-gpu-worker/` to the worker, preserving all five files,
then run PowerShell as the worker operator:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
Set-Location C:\VenHoGPU\scripts\windows-gpu-worker
.\gw_p1_verify.ps1
```

## Remediation command when the worker is not installed

For the current blocker (`C:\VenHoGPU\comfyui` missing and system Python
3.14 without CUDA Torch), copy the repository bundle to
`C:\VenHoGPU\scripts\windows-gpu-worker\`, then run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
Set-Location C:\VenHoGPU
.\scripts\windows-gpu-worker\gw_p1_install_and_verify.ps1
```

The remediation selects Python 3.12, creates `C:\VenHoGPU\venv`, installs
the GPU PyTorch wheel line for the GTX 16xx path, clones ComfyUI only when the
exact target path is absent, installs its requirements, records `main.py
--help`, and then invokes `gw_p1_verify.ps1`. It does not install a checkpoint:
if the roadmap-approved SD1.5 checkpoint is absent, the install report records
`MODEL_MISSING` and the new verification remains FAIL.

The remediation report is stored in a separate
`C:\VenHoGPU\evidence\gw-p1-install-<timestamp>\` directory. The subsequent
verifier always creates a new `gw-p1-<timestamp>` directory; the previous
failure evidence is never reused or modified.

## GW-P1 SD1.5 checkpoint authority

The roadmap/config pin names exactly:

- filename: `v1-5-pruned-emaonly.safetensors`
- authority: `stable-diffusion-v1-5/stable-diffusion-v1-5`, Hugging Face
- source: `https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors`
- SHA-256: `6ce0161689b3853acaa03779ec93eafe75a02f4ced659bee03f50797806fa2fa`
- target: `C:\VenHoGPU\comfyui\models\checkpoints\v1-5-pruned-emaonly.safetensors`

This filename is defined in
`config/projects/venho_hotel/identity_restoration/workflow_pins.yaml`; the
project did not previously define a model SHA and no matching checkpoint was
found in project storage. The upstream file page reports the SHA-256 and size
for this exact artifact. Do not substitute SDXL, SD2, SD3, Flux, or another
checkpoint.

If the file exists on another approved local drive, copy and verify it:

```powershell
Copy-Item -LiteralPath 'D:\approved-models\v1-5-pruned-emaonly.safetensors' `
  -Destination 'C:\VenHoGPU\comfyui\models\checkpoints\v1-5-pruned-emaonly.safetensors'
Get-FileHash 'C:\VenHoGPU\comfyui\models\checkpoints\v1-5-pruned-emaonly.safetensors' -Algorithm SHA256
```

If it must be downloaded, use the pinned URL and verify before running the
worker:

```powershell
$model = 'C:\VenHoGPU\comfyui\models\checkpoints\v1-5-pruned-emaonly.safetensors'
New-Item -ItemType Directory -Force (Split-Path $model) | Out-Null
curl.exe -L --fail --retry 3 `
  'https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors' `
  -o $model
Get-FileHash $model -Algorithm SHA256
```

Proceed only when the printed hash is
`6CE0161689B3853ACAA03779EC93EAFE75A02F4CED659BEE03F50797806FA2FA`.

## Final verifier command after prerequisites are present

The verifier bundle must contain `gw_p1_verify.ps1`, `gpu_probe.py`,
`fp16_sanity_check.py`, `sd15_sanity_check.py`, and
`cleanup_worker_cache.ps1` under
`C:\VenHoGPU\scripts\windows-gpu-worker\`. Run only this command sequence;
do not run the installation/remediation script again:

```powershell
$verifier = @(
  'C:\VenHoGPU\windows-gpu-worker\gw_p1_verify.ps1'
  'C:\VenHoGPU\scripts\windows-gpu-worker\gw_p1_verify.ps1'
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$model = 'C:\VenHoGPU\comfyui\models\checkpoints\v1-5-pruned-emaonly.safetensors'
if (!$verifier) { throw 'Missing gw_p1_verify.ps1 under windows-gpu-worker or scripts/windows-gpu-worker' }
if (!(Test-Path -LiteralPath $model)) { throw "Missing approved SD1.5 model: $model" }
$hash = (Get-FileHash $model -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne '6ce0161689b3853acaa03779ec93eafe75a02f4ced659bee03f50797806fa2fa') { throw "SD1.5 SHA-256 mismatch: $hash" }
Set-ExecutionPolicy -Scope Process Bypass
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifier -WorkerRoot 'C:\VenHoGPU' -ComfyUIPath 'C:\VenHoGPU\comfyui'
```

This creates a new `C:\VenHoGPU\evidence\gw-p1-<timestamp>\` directory. When
configuration A qualifies, it also writes the effective runtime flags to
`C:\VenHoGPU\worker.env`:

```text
COMFYUI_FLAGS=--lowvram --fp32-vae
```

If the bundle is stored elsewhere, pass explicit paths:

```powershell
.\gw_p1_verify.ps1 -WorkerRoot C:\VenHoGPU -ComfyUIPath C:\VenHoGPU\comfyui
```

The command must not install Python, PyTorch, ComfyUI, models, VenHo OS, or
custom nodes. It uses an existing isolated Python environment and existing
checkpoint only. Missing prerequisites are recorded as FAIL; the script keeps
collecting safe evidence and prints one final result.

## Frozen GW-P1 worker configuration

The roadmap-approved runtime configuration is fixed as follows:

- Windows 11 worker; GTX 1660 SUPER, 6 GB
- Python 3.12.10 in `C:\VenHoGPU\venv`
- torch 2.13.0+cu126; `torch.cuda.is_available() == true`
- ComfyUI commit `c67885b14556cf3e4e061862925282d403d09862`
- checkpoint `v1-5-pruned-emaonly.safetensors`
- bind `127.0.0.1`
- flags `--lowvram --fp32-vae`

The verifier freezes the first qualifying configuration in roadmap order and
writes `C:\VenHoGPU\gw_p1_winning_config.json`. The cu130 warning does not
change this frozen configuration because the required SD1.5 inference passes.

## API diagnostics and local-only proof

The verifier starts ComfyUI only as:

```text
python main.py --listen 127.0.0.1 --port 8188 --lowvram --fp32-vae
```

It proves the local-only boundary with both a successful
`http://127.0.0.1:8188/system_stats` request and a listener in the launched
ComfyUI process tree on `127.0.0.1` or `::1`, with no `0.0.0.0` or `::`
wildcard listener. Each run writes `listener_A.json`, `listener_B.json`, or
`listener_C.json` with launcher PID, listener PID, parent PID, local
address/port, owning process, command line, process-tree validation, and
collection method (`Get-NetTCPConnection`, with `netstat` fallback).

For the 512×512 SD1.5 API sanity request, the verifier uses the pinned
`v1-5-pruned-emaonly.safetensors` checkpoint and seed `151515`. It saves the
installed `/object_info` and `/system_stats` responses. If `/prompt` returns a
4xx, `sd15_http_error.json` contains the complete response body and the report
sets `http_error` and `comfy_prompt_validation_error`; it does not classify
that response as `cuda_runtime_exception`. CUDA runtime failure is recorded
only after a queued prompt exposes CUDA runtime text during execution.

## Required worker layout

- `C:\VenHoGPU\comfyui\main.py`
- an existing isolated interpreter at `C:\VenHoGPU\.venv\Scripts\python.exe`,
  `C:\VenHoGPU\venv\Scripts\python.exe`, ComfyUI `venv`, or embedded Python
- an existing SD1.5 checkpoint under `C:\VenHoGPU\comfyui\models\checkpoints\`

The checkpoint filename and full Windows path are recorded from the actual
worker filesystem. No POSIX path is accepted as evidence.

## Safety and configuration rules

- ComfyUI is launched with `--listen 127.0.0.1`; no `0.0.0.0`, LAN, firewall,
  Tailscale, or remote adapter configuration is performed.
- The script records the installed ComfyUI `python main.py --help` output and
  uses only flags that are actually advertised by that installation.
- Precision configurations are tested in roadmap order: `--lowvram
  --fp32-vae`, `--lowvram --force-fp32`, then `--novram --force-fp32`. A first
  stable configuration is selected only if the CUDA smoke test and local
  512×512 SD1.5 output are finite, non-black, and have pixel standard deviation
  greater than 5. Model/workflow changes are not used to compensate for a
  precision failure.
- No Linh An Face QC, QC4/QC4I, threshold change, image optimization,
  IdentityRestorerPort, or Phase 2 work is performed.

## Evidence review

The script creates:

`C:\VenHoGPU\evidence\gw-p1-<timestamp>\`

Required review files are `gw_p1_report.json`, `nvidia-smi.txt`,
`torch_cuda_probe.json`, `comfyui_help.txt`, `fp16_*.json`, `sd15_*.json`, the
selected SD1.5 sanity PNG, `model_paths.txt`, and `environment.txt`. Review
the report and logs before changing roadmap status. A console `PASS` is not a
substitute for human evidence review.

When a configuration qualifies, the verifier freezes the first roadmap-order
winner (A, then B, then C) in both the evidence directory as
`gw_p1_winning_config.json` and `C:\VenHoGPU\gw_p1_winning_config.json`. It
records flags, local bind, checkpoint, ComfyUI commit, Python, Torch/CUDA, and
the exact listener evidence. A qualifying run requires all socket, FP16, and
real SD1.5 acceptance checks; it is never selected from health alone.

## Cache cleanup

`cleanup_worker_cache.ps1` is dry-run by default:

```powershell
.\cleanup_worker_cache.ps1
```

After reviewing the listed stale items, cleanup is explicit and bounded to
`C:\VenHoGPU\comfyui\temp`, `output\temp`, and old evidence directories:

```powershell
.\cleanup_worker_cache.ps1 -Apply -EvidenceRetentionDays 30
```

Task Scheduler status is recorded by the one-shot script but no scheduled task
is created or modified by this bundle.

## Rollback

Stop the worker process and remove the copied `C:\VenHoGPU\scripts\windows-gpu-worker`
directory if required. The bundle does not modify production repositories,
ComfyUI models, workflows, or VenHo OS.

## GW-P5 hardening execution

The GW-P5 bundle adds Task Scheduler auto-start and a resumable reboot verifier.
The scheduler remains current-user/Interactive/Limited and ComfyUI remains
loopback-only. The verifier never reboots Windows and never changes firewall or
network exposure.

Register/inspect the auto-start task (dry-run first):

```powershell
Set-Location C:\VenHoGPU\scripts\windows-gpu-worker
.\gw_p5_t1_run_on_windows.ps1
```

Run the consolidated reboot check as two human-controlled stages:

```powershell
.\gw_p5_hardening_verify_on_windows.ps1 -Stage PreReboot
# perform one normal Windows reboot
.\gw_p5_hardening_verify_on_windows.ps1 -Stage PostReboot
```

From Mac, confirm the worker after logon/reboot:

```bash
IDR_COMFYUI_ENABLED=true \
IDR_COMFYUI_BASE_URL=https://harry-rog.taila40de0.ts.net \
./.venv/bin/python ./scripts/probe_gpu_worker.py
```

Expected health is `HEALTHY`, with `NVIDIA GeForce GTX 1660 SUPER` and a
loopback-bound ComfyUI listener. A refused worker must map to
`ERR_GW_WORKER_OFFLINE` and fail fast. Retry uses a new `attempt_id`; it must
not overwrite the previous attempt's artifacts. Cleanup is explicit and safe:
review the dry-run first, then use `cleanup_worker_cache.ps1 -Apply` only for
the approved temporary/evidence retention paths. Low-VRAM failures must fail
closed as `ERR_GW_VRAM_EXHAUSTED` (or the repository's canonical equivalent),
with no false success.

Rollback: unregister/disable `VenHoGPU-ComfyUI-AutoStart`, then start ComfyUI
manually when required. Do not change the ComfyUI bind address.

After the post-reboot health check, run the bounded Mac-side worker harness.
It stops at the first failed job and allows only the prescribed `2` smoke or
`10` soak count:

```bash
IDR_COMFYUI_REMOTE_BASE_URL=https://harry-rog.taila40de0.ts.net \
./.venv/bin/python ./scripts/gw_p5_worker_soak.py --count 2
# continue only when the report says "result": "PASS"
IDR_COMFYUI_REMOTE_BASE_URL=https://harry-rog.taila40de0.ts.net \
./.venv/bin/python ./scripts/gw_p5_worker_soak.py --count 10
```

Paste back the two JSON report paths, both results, the post-reboot verifier
JSON path, the Mac health JSON, and the cleanup-cycle counts. Do not run a
second soak after a failure without a new decision; the hard cap is 12 normal
GPU jobs total.

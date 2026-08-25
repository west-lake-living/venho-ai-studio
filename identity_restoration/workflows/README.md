# identity_restoration/workflows/ — workflow JSON is source code (GW-D6)

A ComfyUI workflow JSON decides the output. It lives in Git, is pinned by
SHA-256 in `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml`,
and is deployed to the Windows worker one-way by
`scripts/deploy_workflows_to_worker.py` (GW-P3). **Never edit a workflow on
the worker itself** — pull the repo version down again instead.

## Where the workflows actually are right now

- **`comfyui-local`** wraps the legacy SDXL/PuLID workflow that
  `ComfyUIIdentityRestorer` already runs in production and that the
  GW-P0-T2 golden-master was frozen against. That file was archived at
  GW-P0 to the repo **top-level** `workflows/_archive/face_restore_v1_api.json`
  (not nested under this package) because it predates this bounded context —
  its pin in `workflow_pins.yaml` points there. `comfyui-local` reads it via
  `infrastructure/comfyui/workflow_repository.py::FileWorkflowRepository`,
  which resolves whatever `path`/`filename` the pin declares.
- **`face_restore_win_sd15_ipadapter_v1`** — the exact SD1.5 + IPAdapter
  FaceID API workflow from the successful HARRY-ROG GW-P3 run. Its SHA-256 is
  pinned in `workflow_pins.yaml` and must match byte-for-byte.

## Pinning a new or changed workflow

1. Export the workflow as **API format** JSON from ComfyUI (not the UI-format
   workflow — the API format is what `/prompt` accepts).
2. Every node this codebase binds to must have a `_meta.title` matching
   `infrastructure/comfyui/node_registry.py::NODE_TITLES` exactly. Binding is
   by title, never by numeric node id — ComfyUI renumbers ids every time the
   graph is re-saved from the UI (GW-D7).
3. Compute `shasum -a 256 <file>` and write the hash into
   `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml`.
4. A workflow file that changes without its pin changing is a hard fail at
   load time (`FileWorkflowRepository.load()` raises `ERR_GW_WORKFLOW_INVALID`),
   by design — reproducibility depends on it.

# GW-P0-T1 — Coupling Audit

**Audit date:** 2026-08-19 (evidence reconstruction against the current checkout)  
**Original roadmap date:** 2026-08-18  
**Mode:** read-only; no production code changed  
**Authority:** `VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` overrides v2.0 where conflicting.

## Purpose

Record the current coupling of the Action Composite identity-restoration path before any
Phase-2 port extraction or adapter refactor. This document is an evidence record, not a
remediation plan and not an architecture redesign.

## Scope

Audited the current Python image-plane implementation under
`image_studio_runtime/action_composite/`, its tests and scripts that invoke it, the local
ComfyUI workflow/config boundary, and the existing Golden-Master/roadmap evidence. The audit
covers the eight coupling suspects listed in v2.1 patch §3.1.

## Current call graph

```text
caller / test / script
  ├─ ProductionRunner.submit_and_run()
  │    ├─ ActionCompositeService.submit()/run()
  │    └─ ActionCompositePipeline.run(job, restorer, ...)
  └─ direct tests/scripts may call ActionCompositePipeline.run(...)

ActionCompositePipeline.run
  ├─ load_image(base_image)
  ├─ FaceDetector.detect() → FaceGeometry
  ├─ crop_for_identity() → crop + crop_box
  ├─ hierarchical_face_masks() → mask set
  ├─ identity_loader() or Path(identity_reference).read_bytes()
  ├─ restorer.restore(base, A2 bytes, mask, geometry, restore_options)
  ├─ unchanged_outside_mask() + Image.composite()
  ├─ optional RegionalScoreGateway / RegionalGate
  ├─ writes image.png + manifest.json
  └─ returns CompositeResult

ComfyUIIdentityRestorer.restore
  ├─ receives crop/mask in restore_options
  ├─ PNG-encodes and POSTs /upload/image for base, mask, A2
  ├─ inject_inputs() binds uploads by workflow _meta.title
  ├─ POSTs /prompt
  ├─ polls GET /history/{prompt_id}
  ├─ GETs /view for the first deterministic output
  └─ resizes/composites the returned crop into the original canvas
```

**Instantiation/injection:** `ProductionRunner` accepts an `IdentityRestorer` instance at
`image_studio_runtime/action_composite/production.py:27,33`; it does not instantiate
`ComfyUIIdentityRestorer`. Tests instantiate `ComfyUIIdentityRestorer` directly in
`tests/test_action_composite_comfyui.py:118,165`. The current seam is a structural
`IdentityRestorer` protocol, not yet the planned `IdentityRestorerPort` package interface.

**Upstream dependencies:** PIL images, `ActionCompositeJob`, `FaceDetector`, geometry/mask
helpers, identity-reference file or loader, optional candidate and regional-score inputs.  
**Downstream consumers:** `CompositeResult`, `image.png`, `manifest.json`, `AuditStore`/
`ActionCompositeService`, and test/script callers.

## Dependency/coupling matrix

| Area | Finding | Evidence | Risk |
|---|---|---|---|
| Absolute path passed into ComfyUI loader | **N** for the current restore payload: base and mask are uploaded and node inputs receive returned upload names. The A2 reference is uploaded as bytes. | `providers.py:70-83`, `inject_inputs()` `:24-42` | Low for current upload path |
| Read worker output from local `output/` | **N**; output is retrieved with `/view` after `/history`. | `providers.py:91-110,133-138` | Low |
| Write worker input into local `input/` | **N**; input/mask/reference use `/upload/image`. | `providers.py:78-83,140-163` | Low |
| Hardcoded localhost / `:8188` | **Y** as a default. Endpoint is configurable through `VENHO_COMFYUI_ENDPOINT`, but the adapter default is `http://127.0.0.1:8188`. | `providers.py:48`, `config.py:18,28`; `config/action_composite.env.example` | High for remote migration |
| Shared folder / symlink assumption | **N** in the ComfyUI transfer path. Local Python paths are used for source artifacts and workflow loading only. | `providers.py:78-83`; `config.py:37-48` | Low |
| Low-latency assumption | **Y/partial**: polling is fixed at 250 ms, uploads use one request each, and there is no exponential backoff. Timeout is configurable. | `providers.py:91-112`; `config.py:21,32` | Medium |
| POSIX path assumption on worker | **N** for uploaded worker filenames; **Y/partial** for local Python-side workflow/artifact paths using `pathlib`. No Windows worker path is sent in the current upload contract. | `providers.py:156-158`; `config.py:40-48`; `pipeline.py:161-182` | Medium when deployment paths are introduced |
| Output available immediately after completion | **N**; `/history` is polled and output is read only when present. | `providers.py:91-112` | Low |

Additional coupling found:

- ComfyUI HTTP routes, upload response fields, and output image metadata are embedded in
  `ComfyUIIdentityRestorer` (`providers.py:85-163`).
- Workflow JSON is loaded through `ComfyUIConfig`, but the current runtime code does not
  enforce the SHA-256 pin in `workflow_pins.yaml`; the pin is governance evidence/config,
  not an adapter runtime check (`config.py:37-48`).
- `ActionCompositeJob` defaults still name `face_restore_v1` (`models.py:80`), while the
  v1 workflow itself is archived. This is a compatibility/lineage coupling to preserve and
  review in Phase 2; it was not changed in this audit.
- `ProductionRunner.health_check()` assumes the injected restorer exposes `health_check()`
  (`production.py:27-31`), while the structural `IdentityRestorer` protocol only declares
  `restore()` (`providers.py:19-21`).

## Current contracts

### Request and result

`ActionCompositeJob` carries `job_id`, base image path, A2 identity-reference path, authority
`A2_FRONT`, optional face bounding box, workflow/provider metadata, optional expected A2 SHA-256,
and mask version (`models.py:74-103`). The identity reference filename must contain
`A2-FRONT`; if a hash is supplied, the pipeline hashes the loaded bytes and fails on mismatch
(`pipeline.py:59-62`).

`IdentityRestorer.restore()` receives `(base_image, identity_reference: bytes, face_mask,
geometry: dict, config: dict)` and returns a full-size PIL image (`providers.py:19-21`). The
pipeline rejects a size change (`pipeline.py:72-74`).

`CompositeResult` contains job ID, final state, output path, `FaceGeometry`, `RegionalQC`, and
metadata (`models.py:119-125`). `RegionalQC` records identity/geometry/regional scores, pixel
preservation, status, and failures (`models.py:106-116`).

### Crop, mask, transform, and pixel lock

`crop_for_identity()` produces the identity crop and serialized crop box. The pipeline passes
that crop, crop box, crop mask, and mask manifest to the restorer (`pipeline.py:48-70`). The
ComfyUI adapter returns a crop to the original canvas and composites it at the crop box
(`providers.py:102-109`). The pipeline then checks `unchanged_outside_mask()` on the raw
restorer output before `Image.composite()` (`pipeline.py:76-86`).

### Artifacts, manifest, ledger, and QC

The pipeline writes `output_dir/image.png` and `output_dir/manifest.json`; the manifest records
contract version, job, A2 hash, geometry lock, masks, regional evidence, workflow ledger,
reproducibility metadata, QC, and output SHA-256 (`pipeline.py:161-182`). `ActionCompositeService`
stores job status, idempotency, and audit trails; `ProductionRunner` verifies image and manifest
existence before returning (`service.py:32-143`, `production.py:89-102`).

## External boundaries

### Venho OS / TypeScript control plane

The current Python code owns the image plane and exposes service/runner objects; the roadmap
boundary assigns durable control-plane concerns to `venho-os` through the existing subprocess
and JSON contract. No Python file in the audited path calls a TypeScript module or creates a
second job store. `venho-os` must not access ComfyUI directly; that remains a v2.1 invariant
and is recorded in ADR-GW-003.

### ComfyUI boundary

Only `ComfyUIIdentityRestorer` contains the current ComfyUI HTTP coupling: `/system_stats`,
`/upload/image`, `/prompt`, `/history/{prompt_id}`, and `/view`. The current adapter uses
`urllib.request`, a configurable endpoint, a client ID, timeout, workflow object, and node
bindings. It uses `/history` polling rather than WebSocket, matching GW-D8.

### Configuration and workflow authority

`ComfyUIConfig.from_env()` reads `VENHO_COMFYUI_ENDPOINT`, `VENHO_COMFYUI_WORKFLOW_VERSION`,
`VENHO_COMFYUI_WORKFLOW_PATH`, `VENHO_COMFYUI_TIMEOUT_SECONDS`, `VENHO_COMFYUI_CLIENT_ID`,
and `VENHO_COMFYUI_NODE_BINDINGS`. The archived v1 workflow remains at
`workflows/_archive/face_restore_v1_api.json`; `workflow_pins.yaml` preserves its hash and
the current A2 authority hash. No new workflow was activated.

## Phase-2 extraction seams

These are observations for the locked plan, not implementation work in GW-P0:

1. The `restorer` parameter of `ActionCompositePipeline.run()` is the narrowest extraction
   seam (`pipeline.py:28-40`). Preserve the current structural method shape while introducing
   the planned port later.
2. Keep geometry detection, crop/mask construction, A2 hash verification, compositing, pixel
   lock, manifest, and QC in the existing pipeline/domain side; they must not move into a
   provider-specific adapter without an approved decision.
3. Keep HTTP routes, upload naming, workflow binding, polling, output download, and endpoint
   configuration behind the ComfyUI adapter.
4. Keep service idempotency, audit trail, artifact verification, and control-plane ownership
   outside the image adapter.
5. Preserve the single `ActionCompositePipeline` class. Repository search found one class
   definition in `image_studio_runtime/action_composite/pipeline.py`; callers/tests import or
   instantiate that class rather than a second pipeline.

## Behavior invariants

- A2-FRONT remains the sole identity authority and its pinned SHA-256 is unchanged.
- The pipeline returns the original canvas dimensions and composites only through the mask.
- Pixels outside the effective mask must remain byte-identical; pixel-lock failure is a QC
  failure even when identity scoring is high.
- Crop box, mask version, geometry lock, workflow version, ledger, QC, artifact paths, and
  artifact hashes remain represented in the manifest.
- The existing `ActionCompositePipeline` behavior is frozen by the three-case offline Golden
  Master under `tests/identity_restoration/golden/`.
- QC threshold authority remains external; this audit does not change ≥90.
- Offline/default tests use mock/frozen artifacts and do not call the network.

## Risks

### High

- Endpoint default and ComfyUI HTTP details are still embedded in the adapter and must be
  isolated before a remote Windows adapter is introduced.
- Workflow SHA-256 is pinned in governance/config but not runtime-enforced by this current
  adapter.
- `face_restore_v1` compatibility defaults remain after the v1 workflow was archived.

### Medium

- Fixed 250 ms polling and no backoff may be inefficient over Tailscale/remote links.
- Local path resolution and local workflow loading must not be confused with worker filesystem
  paths when remote deployment begins.
- `health_check()` is an implicit adapter capability rather than part of the current protocol.

### Low

- Upload names are namespaced with a UUID prefix and returned ComfyUI names are used for graph
  binding; no shared folder assumption was found.
- Output selection is deterministic by sorted output keys.

No risk remediation is performed in GW-P0.

## Evidence references

- `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` §3.1, §4, §5, §7, §13
- `docs/Image studio/VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md` §2.1, §3, §5, §6, §8, §13
- `image_studio_runtime/action_composite/pipeline.py`
- `image_studio_runtime/action_composite/providers.py`
- `image_studio_runtime/action_composite/production.py`
- `image_studio_runtime/action_composite/service.py`
- `image_studio_runtime/action_composite/config.py`
- `image_studio_runtime/action_composite/models.py`
- `tests/test_action_composite_v2.py`, `tests/test_action_composite_v21.py`,
  `tests/test_action_composite_comfyui.py`, `tests/test_action_composite_p6.py`
- `tests/test_gw_p0_t2_golden.py` and `tests/identity_restoration/golden/`
- `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml`
- `workflows/_archive/face_restore_v1_api.json`

## Conclusion

The current implementation has one Action Composite pipeline with an injected structural
restorer seam. ComfyUI coupling is concentrated in `ComfyUIIdentityRestorer`, but endpoint,
workflow-loading, polling, and compatibility defaults remain explicit Phase-2 extraction risks.
The audit is evidence-only: no fixes, port extraction, threshold changes, generation, or
architecture changes were performed.

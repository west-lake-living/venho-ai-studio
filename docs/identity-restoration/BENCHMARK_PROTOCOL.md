# GW-P4 Controlled A2 Benchmark Protocol

Status: **BENCHMARK DATASET COMPLETE — GW-P4-T0 remains BLOCKED pending physical branch/evidence executors**  
Authority: `VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md` plus
`VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`; v2.1 controls where the documents differ.

This document freezes the comparison contract before measurement. It does not
authorize generation, tuning, paid validation, or official promotion.

## Purpose

Measure the same authoritative base frame through four comparison branches:

1. `control` — the base frame without restoration.
2. `comfyui-local` — the existing local adapter/path.
3. `comfyui-remote` — the pinned Windows worker adapter/path.
4. `nano-banana-edit` — the existing Nano Banana/action-composite baseline path.

`nano-banana-edit` is not currently registered as an
`IdentityRestorerPort` adapter in this repository. It remains an external
comparison branch through the existing Venho OS / social-content-agent
baseline; no second pipeline is introduced here.

The single source of truth for the set contract is
`contracts/identity_restoration/benchmark_set.yaml`. No official benchmark run
is valid until every B01–B10 row has a real frozen base artifact and a runner
enforces that readiness gate.

## Frozen authority and configuration

| Item | Frozen value | Evidence |
|---|---|---|
| A2 authority | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png` | `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml` |
| A2 SHA-256 | `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d` | live file hash verified during GW-P4-T0 preflight |
| A2 dimensions | `580×860`, RGB | decoded from the authority file |
| Remote workflow ID | `face_restore_win_sd15_ipadapter_v1` | workflow pin / `identity_restoration/infrastructure/comfyui/node_registry.py` |
| Remote workflow SHA-256 | `7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8` | workflow pin and file hash verified during preflight |
| Local workflow ID | `face_restore_v1_api` | legacy local registration |
| Local workflow SHA-256 | `b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25` | archived workflow pin |

The legacy local workflow remains historical GW-P0 behavior. The remote
workflow remains the imported/pinned GW-P3 workflow. Neither is changed by
this protocol.

### Remote geometry-correction candidate

`face_restore_win_sd15_ipadapter_v2` is a versioned candidate workflow with
local SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`.
It preserves the v1 restoration graph but receives request-driven padding and
final-crop dimensions. The active benchmark authority remains v1 until the
identical Windows deployment SHA is physically verified; no benchmark source,
seed, or metric authority is changed by authoring this candidate.

## Geometry backend lineage

Geometry selection is explicit through `IDR_GEOMETRY_BACKEND`; no backend is
silently substituted. The existing production default remains `insightface`.
The approved YuNet compatibility candidate is selected with
`IDR_GEOMETRY_BACKEND=yunet` and is recorded in each generated request lineage
as `geometryBackend`, `geometryModel`, and `geometryModelSha256`.

The pinned offline artifact is
`models/geometry/yunet/face_detection_yunet_2023mar.onnx` with SHA-256
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`; its
OpenCV Zoo MIT license is retained at `models/geometry/yunet/LICENSE` and its
source/version record is `models/geometry/yunet/PROVENANCE.json`. Local and
remote requests must use the same selected backend/model/hash for a case.

## B01–B10 frozen dataset inventory

The authoritative manifest is
`contracts/identity_restoration/benchmark_set.yaml`; the discovery report is
`docs/identity-restoration/BENCHMARK_DATASET_V2_1.md`. Existing images were
not promoted into the dataset based on appearance or Face QC.

| ID | Taxonomy | Frozen base path | SHA-256 | Dimensions | Lineage | Readiness |
|---|---|---|---|---|---|---|
| B01 | Close-up Front | Frozen production artifact | `.../12-08-linh-an-a2-front-closeup-1k/.../image.png` | `e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9` | 1024×1024 | `run-202608121022` | FROZEN |
| B02 | Half-body | Frozen production artifact | `.../10-08-linh-an-official-library/.../step5-business/.../image.png` | `b3854325403c879693ab0f720aaf57a78da385ac6220acb59bd730b9d608d58f` | 1024×1280 | `run-20260810-step5-business` | FROZEN |
| B03 | Full-body Standing | Frozen production artifact | `.../07-08-hoang-hon-ho-tay-tu-rooftop/.../image.png` | `098e6816fc21631fe4cd3bbd34b718f04569f8684f5347ab78525faf7ce07d87` | 1088×1920 | `run-20260807130340020` | FROZEN |
| B04 | Running Front 3/4 | Frozen GW-P0 base | `.../assets/action-composite-live/action_01_jogging.png` | `bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0` | 1024×1280 | `gw-p0-t2-20260819-local-rerun` | FROZEN |
| B05 | Running Side | GW-P4-T0.4 generated source | `06f4b6b0b6ea47dee71a240065411899cb3fa2b84633dacddba4d232afce5492` | 1024×1280 | `gw-p4-t0-4-b05-running-side/run-001` | FROZEN |
| B06 | Walking | GW-P4-T0.4 generated source | `526190e3632d189d588dcdfda32f1d7930c449c8a6b2188961d7907ef7746d8e` | 1024×1280 | `gw-p4-t0-4-b06-walking/run-001` | FROZEN |
| B07 | Sitting | GW-P4-T0.4 generated source | `6a39787e5edf0d061d246d9af806ac82d7499429a104fd3f910708dc5718754e` | 1024×1280 | `gw-p4-t0-4-b07-sitting/run-001` | FROZEN |
| B08 | Hair Motion | GW-P4-T0.4 generated source | `e6303bb45121b6dd01f992d549d76668cf34b6b82828ffed87f3a65928c970c4` | 1024×1280 | `gw-p4-t0-4-b08-hair-motion/run-001` | FROZEN |
| B09 | West Lake | Frozen production artifact | `.../10-08-linh-an-official-library/.../step5-cafe/.../image.png` | `9351a446dec761fa733f049212f8d1d4b205a774e47f2a1be1bbd1f2067af912` | 1024×1280 | `run-20260810-step5-cafe` | FROZEN |
| B10 | Ven Ho Hotel Interior | Frozen production artifact | `.../smoke-20260811-171445/case-5/.../image.png` | `32c701012e40040772c69bff102719c5d48c9c046bad442f68f1bc520c5bc507` | 848×1264 | `smoke-20260811-171445/case-5` | FROZEN |

The four formerly missing rows were generated once through the existing
approved social-content-agent pipeline and accepted on taxonomy/technical
validity. Full prompt, provider, A2 reference, timestamp, attempt, and
unavailable-seed/request-ID fields are recorded in
`BENCHMARK_GENERATION_LINEAGE_V2_1.md`. No Face QC was used for selection.

## Comparison invariants

For each Bxx, every branch must use:

- the exact same base-frame bytes and base SHA-256;
- the exact same A2 authority and SHA-256 above;
- the exact same crop transform and crop box;
- the exact same mask version and corresponding mask geometry;
- the exact same composite canvas dimensions;
- the same benchmark seed for comparable restoration branches;
- a new `attempt_id` for every retry;
- retained failed outputs and error metadata;
- no official promotion during measurement.

`comfyui-local` and `comfyui-remote` must receive identical crop/mask/A2
geometry. Only editable output pixels may differ. Pixel preservation is
fail-closed: pixels outside the permitted full-canvas editable mask must remain
byte-identical, and output geometry must match the input contract.

## Crop, mask, and pixel-lock contract

The current production implementation is:

- crop calculation: `image_studio_runtime/action_composite/masks.py::crop_for_identity`,
  default context scale `2.5`;
- hierarchical mask: `hierarchical_face_masks`, version `hierarchical_face_v1`,
  with `core`, `shape`, and `boundary` regions;
- current dual-mask application contract: crop-local mask dimensions equal the
  crop; full-canvas preservation mask dimensions equal the base canvas;
- preservation predicate: `unchanged_outside_mask` / the equivalent domain
  pixel-preservation policy.

The per-case crop transform and mask hash must be captured from the frozen base
row. They must not be regenerated independently for different branches.

## Restoration parameter freeze

Benchmark seed policy is `seed=42`, inherited from the existing GW-P0 golden
contract. It must be explicit in every comparable restoration request and must
not be selected from Face QC.

| Branch | Parameters |
|---|---|
| `control` | no restoration; no restoration parameters |
| `comfyui-local` | legacy `face_restore_v1_api`; its frozen workflow values are seed `42`, steps `4`, CFG `1.2`, sampler `dpmpp_2m`, scheduler `sgm_uniform`, denoise `0.6` |
| `comfyui-remote` | pinned workflow values: denoise `0.35`, steps `20`, CFG `6.0`, sampler `euler`, scheduler `normal`; benchmark request seed `42` overrides the workflow's editable runtime seed field without changing workflow semantics |
| `nano-banana-edit` | use the existing baseline path and record its own existing request parameters/lineage; no new generation or tuning in T0 |

No model, workflow, prompt, sampler, denoise, Face QC threshold, or
architecture tuning occurs before the initial benchmark result.

## Validator and metrics contract

The production Face QC entry point is
`validator_studio.face_validator.validate_face()`. It supports explicit
`samples=3`; `_observe_face()` performs three observations and
`_merge_face_samples()` majority-votes gates and averages weighted scores.
The current general validation config default is `observe_samples: 1`, so a
benchmark caller must pass `samples=3` explicitly. No paid calls were made in
GW-P4-T0.

Each row must retain:

`faceQcBefore`, `faceQcAfter`, `identityScore`, `eyesBrowsScore`,
`geometryScore`, `anatomyScore`, `outfitScore`, `environmentScore`,
`globalScore`, `pixelPreservationResult`, `runtimeMs`, `retryCount`,
`workflowId`, `workflowSha256`, `seed`, `gpuName`, `vramPeakMb`, and
`restorerId`.

Regional scores must retain their producer/evidence provenance. UNKNOWN or
missing evidence is not converted into a pass.

## Current harness/schema preflight

- `contracts/identity_restoration/benchmark_row.schema.json` is now the v2.1
  contract and requires the canonical benchmark fields listed above.
- Legacy `caseId`, `faceScore`, `pixelLockPassed`, `samples`, and `notes` remain
  accepted as optional compatibility fields; new rows use `benchmarkId`,
  `faceQcBefore/After`, and `pixelPreservationResult`.
- `additionalProperties` remains `false`.
- `venho-restore benchmark validate|plan|run` and
  `identity_restoration.application.benchmark_runner.BenchmarkRunner` now
  provide the fail-closed benchmark contract/runner boundary. No official run
  has executed.
- `comfyui-local` is registered by the composition root when
  `IDR_COMFYUI_ENABLED=true`.
- `comfyui-remote` is registered when
  `IDR_COMFYUI_REMOTE_ENABLED=true` and the pinned remote workflow loads.
- `nano-banana-edit` is not registered in this bounded context; its comparison
  boundary is the existing external action-composite baseline described above.

## Retry and failure policy

Every attempt gets a unique attempt ID. Retries are recorded, including failed
outputs and structured errors; no failed output is hidden or overwritten. A
worker/VRAM failure may have at most the existing one retry policy. Pixel-lock,
A2-hash, geometry, empty-output, and schema/provenance failures are hard
failures. No automatic promotion is performed.

## Estimated validator calls

The v2.1 plan estimates `4 branches × 10 cases × 3 Face QC samples = 120`
vision-validator calls for the initial benchmark. This is an estimate only;
GW-P4-T0 made zero paid API calls and did not run Nano Banana or the GPU
benchmark.

## Decision rule

The initial result is a measurement, not a tuning exercise. Report all rows,
attempts, failures, regional outcomes, and pixel-lock outcomes. The phase
decision remains the v2.1 rule: median Face QC at least 90, no serious anatomy
regression, regional gate healthy, and pixel preservation passing. Official
promotion remains a separate human action.

## T0/T0.1 status

GW-P4-T0.1 contract closure is complete. GW-P4-T0 cannot be marked PASS until
all of the following are resolved without changing the invariants:

1. Physical branch executors and Validator Studio evidence wiring for all four
   branches. The runner accepts these only through an injected executor; it
   does not duplicate ActionCompositePipeline or call a backend directly.

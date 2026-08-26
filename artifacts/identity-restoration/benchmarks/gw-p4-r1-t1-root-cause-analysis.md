# GW-P4-R1-T1 — Root-cause analysis and tuning matrix

## 1. Executive conclusion

**Status: CLOSED / ANALYSIS COMPLETE.** Authority is
`gw-p4-t2-pilot-exhausted-checkpoint.json`: `GW-P4 = CLOSED / QUALITY FAIL`;
`GW-P5 = NOT STARTED`.

The provider transport is recovered. C1/C2/C3 failures are valid quality
results, but they do not establish a face-restoration defect: every executed
pilot passes Face-QC, identity, eyes/brows, geometry and Pixel Lock. Each
fails only `global_composite`, sourced directly from the generic Image
Validator overall score. B03 and B04 are frozen full-body/action cases, while
that validator used the default Linh An DNA with no scenario overlay and
reported `shot_distance`/`hairstyle` mismatches. Those decisive properties are
outside, or not reliably editable within, the locked face mask.

This is a **validation-authority/scope blocker to resolve offline**, not a
reason to lower a threshold or reopen GW-P4. A small conditional matrix is
provided, but no GPU pilot is justified until R1-T2 establishes that a
scenario-aware global authority is valid under the unchanged Regional
semantics.

## 2. Evidence inspected

- Authoritative state: `artifacts/identity-restoration/benchmarks/gw-p4-t2-pilot-exhausted-checkpoint.json`.
- Pilot Regional evidence: `gw-p4-t2h-c1-b03-regional-20260825-r15`,
  `gw-p4-t2h-c1-b04-regional-20260825-r16`,
  `gw-p4-t2j-c2-b03-regional-20260825-r18`, and
  `gw-p4-t2l-c3-b03-regional-20260825-r20`.
- Workflow and adapter: `identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json`, `comfyui_remote_restorer.py`, and `graph_binder.py`.
- Composite/mask/Pixel Lock: `identity_restoration/domain/compositing.py`, B03/B04 geometry manifests, and dual-mask/compositing tests.
- QC authority: `validator_studio/image_validator.py`, `validator_studio/scoring.py`, `image_studio_runtime/action_composite/regional_score_gateway.py`, `workflow_v2.py`.
- Frozen case taxonomy: `docs/identity-restoration/BENCHMARK_DATASET_V2_1.md` and `contracts/identity_restoration/benchmark_set.yaml`.

## 3. C1/C2/C3 comparison

| Candidate | Denoise | Case | Face-QC | Geometry | Global | Result |
|---|---:|---|---:|---:|---:|---|
| C1 | 0.30 | B03 | 90.98 | 97.80 | 86.61 | FAIL |
| C1 | 0.30 | B04 | 90.98 | 97.08 | 83.76 | FAIL |
| C2 | 0.25 | B03 | 91.05 | 97.44 | 84.66 | FAIL |
| C3 | 0.20 | B03 | 91.05 | 97.13 | 84.66 | FAIL |

All have identity >=90, eyes/brows >=90, anatomy/outfit/environment=100, and
Pixel Lock PASS. The only reported Regional failure is
`global_composite_below_threshold` (threshold 90).

1. **Why C1 is better on B03:** **CONFIRMED** only numerically: 86.61 exceeds
   84.66 by 1.95. C1 is the sole higher-denoise candidate; causal mechanism is
   **UNKNOWN — insufficient evidence**.
2. **Why C1/B04 is 83.76:** **CONFIRMED** Image-QC reports zero-score
   `earring_type`, `shot_distance`, and `hairstyle` mismatches.
3. **Lower denoise under-restoration:** **NOT SUPPORTED.** 0.25 and 0.20 did
   not improve either Face-QC or global score; no crop-level visual metric
   diagnoses under-restoration.
4. **C1 insufficient identity conditioning:** **NOT SUPPORTED.** Face-QC,
   identity and eyes/brows all meet thresholds.
5. **Same B03/B04 cause:** **LIKELY.** Both share default-DNA
   `shot_distance`/`hairstyle` penalties; B04 additionally has earring mismatch.
6. **Mask/crop/alignment bottleneck:** **NOT SUPPORTED.** Geometry is 97.08–
   97.80, crop/output geometry is enforced, and protected pixels changed = 0.
7. **Model/workflow conditioning bottleneck:** **NOT SUPPORTED as primary.**
   The quality failure is emitted by Image-QC, not face/geometry evidence.

## 4. Root-cause findings

- **CONFIRMED — sole failing Regional input:** `RegionalScoreGateway` maps
  `global_composite` directly from `image_report.overall_score`; the gate does
  not report any other failure.
- **CONFIRMED — rubric/case mismatch exists:** B03 is “Full-body Standing” and
  B04 “Running Front 3/4”; Image-QC flags their full-body framing against the
  default DNA `portrait_head_shoulders`, plus high ponytail against
  `elegant_low_bun`.
- **CONFIRMED — no executed scenario overlay:** `validate_image` can apply a
  `scenario_profile_id`, but no `linh_an.<scenario>.overrides.yaml` exists and
  the executed producer calls Image-QC without one.
- **LIKELY — workflow-only pass is blocked:** editable masks cover only a
  163×214 px B03 and 140×178 px B04 region around the face. They cannot change
  full-body shot distance; long-hair styling also extends outside the protected
  editable area.
- **POSSIBLE — local ear/hair detail contributes:** B04’s earring and part of
  hair may overlap the crop, but the mask evidence does not prove editable
  coverage of those pixels.
- **NOT SUPPORTED — over-restoration, under-restoration, sampler, scheduler,
  CFG, pose, face detector, or alignment as primary cause.**

## 5. Confirmed vs likely vs unknown

The classifications above are evidence-bound. In particular, whether use of a
scenario overlay is authority-equivalent under the locked Regional contract is
**UNKNOWN — insufficient evidence**. It is recorded as a blocker, not applied
as a QC change in this task.

## 6. Variables rejected from further tuning

- Denoise reduction below 0.30: C2/C3 already failed and did not improve B03.
- Crop padding, alignment, mask dilation, mask feather: healthy geometry and
  Pixel Lock provide no causal signal; changing them risks an invariant.
- CFG, sampler, scheduler: no evidence they can repair full-frame DNA
  mismatches outside the editable face region.
- Thresholds and Regional semantics: locked; not tunable.

## 7. Recommended tuning variables

Only after the R1-T2 authority audit clears the blocker:

1. Steps 20 -> 28: addresses only Face-QC technical-quality warning (85).
2. `weight_faceidv2` 1.0 -> 1.15: bounded identity-detail experiment.
3. FaceID LoRA strength 0.6 -> 0.75: bounded adapter-strength experiment.

Each is one variable in a content-addressed derived workflow. A2_FRONT,
denoise=0.30, seed, mask architecture, Pixel Lock, and all QC thresholds stay
unchanged.

## 8. Proposed candidate matrix

See `gw-p4-r1-t1-tuning-matrix.json` for machine-readable fields.

| Candidate | Primary variable | Baseline -> candidate | GPU executions | Main risk |
|---|---|---|---:|---|
| R1-C1 | steps | 20 -> 28 | 2 | reconstruction drift; cannot fix shot distance |
| R1-C2 | FaceID v2 weight | 1.0 -> 1.15 | 2 | pose/lighting drift |
| R1-C3 | FaceID LoRA strength | 0.6 -> 0.75 | 2 | plasticity/pose drift |

## 9. Pilot execution order

1. GW-P4-R1-T2 offline authority/scope audit — zero GPU/provider calls.
2. If it clears: R1-C1 on B03 then B04; stop on first failed gate.
3. If viable: R1-C2, then R1-C3, each B03 then B04.
4. Select only a full B03+B04 pass; otherwise `NO_WINNER`.

## 10. Stop conditions

- R1-T2 cannot establish a scenario-aware authority without changing locked
  Regional semantics: stop, `NO_WINNER`, no GPU.
- Any candidate fails valid Face-QC, Regional, Pixel Lock, or invariant: stop
  that candidate; no 10-case benchmark.
- No candidate passes both B03 and B04: `NO_WINNER`; do not start GW-P5.

## 11. Risks

- Running the matrix before authority clearance spends GPU while an immutable
  full-frame mismatch remains.
- Increasing conditioning can harm pose/lighting/technical quality.
- Altering masks or QC thresholds would violate locked invariants.

## 12. Exact next task

`GW-P4-R1-T2 — Offline scenario-authority and global-composite scope audit.`
It must prove or reject scenario-aware B03/B04 Image-QC authority equivalence,
without provider, GPU, Nano, benchmark, or production-architecture changes.

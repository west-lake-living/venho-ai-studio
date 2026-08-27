# Candidate v3 Phase 4 — Quality Authority Decision Pack

Status: `APPROVED`
Date: 2026-08-27

## Approved authority

Human authority approved the calibrated boundary policy, split-QC gate, and
quality-policy identity below. These values are CPU-only policy/configuration
authority; they do not enable Candidate v3 or authorize GPU/provider calls.

## Repository evidence

- `docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md` §5.5 requires
  inverse composite through `CanonicalFaceTransform`, editable-mask
  containment, hard pixel lock, and optional bounded luminance/chroma
  adjustment. §5.6 assigns seam/color/texture ownership to `BOUNDARY` QC.
- The same roadmap defines the quality merge precedence:
  `FAIL` → `UNVALIDATED` → `NEEDS_REVIEW` → `PASS` only when every required
  scope passes. A failed binary gate cannot be averaged away.
- Existing pixel lock is exact: changed pixels outside the full-canvas editable
  mask must equal `0`.
- Existing Face-QC `90` is explicitly only a necessary local criterion, not a
  production verdict, and no boundary threshold is present in
  `config/projects/venho_hotel/face_qc_rubric.yaml`.
- The roadmap names `restoration-v3-quality-policy-1`, but no authoritative
  v3 quality-policy file or SHA-256 exists in the repository.
- The specification explicitly authorizes no GPU/provider execution for this
  phase; this decision concerns CPU evaluation policy only.

## Approved Decision A — boundary seam policy

Choose one complete policy and provide the exact values where marked.

`SEAM_RING_OPTION = BOUNDARY-B`

`SEAM_RING_DEFINITION`:

- symmetric 3 px ring around the full-canvas editable-mask edge;
- inner and outer pixels are those within Euclidean distance `<= 3 px`;
- connectivity is 8-connected;
- image-border portions outside the canvas are ignored;
- the feather mask does not redefine the hard editable-mask boundary.

`BOUNDARY_METRICS`:

1. `PIXEL_LOCK_OUTSIDE_MASK`: changed pixels outside the editable mask == 0.
2. `MAX_CHANNEL_SEAM_DELTA`: maximum absolute RGB channel delta for
   corresponding nearest inner/outer samples on uint8 `[0,255]`.
3. `MEAN_SEAM_DELTA`: mean absolute RGB channel delta across valid sample
   pairs on `[0,255]`.
4. `LOCAL_TEXTURE_DISCONTINUITY`: absolute difference between mean grayscale
   Sobel gradient magnitudes, divided by `max(mean_outer_gradient, 1.0)`.

`BOUNDARY_THRESHOLDS`:

- `PIXEL_LOCK_OUTSIDE_MASK`: exact zero required.
- `MAX_CHANNEL_SEAM_DELTA`: PASS `<= 32`; NEEDS_REVIEW `> 32 and <= 48`;
  FAIL `> 48`.
- `MEAN_SEAM_DELTA`: PASS `<= 12`; NEEDS_REVIEW `> 12 and <= 20`;
  FAIL `> 20`.
- `LOCAL_TEXTURE_DISCONTINUITY`: PASS `<= 0.25`; NEEDS_REVIEW `> 0.25 and
  <= 0.40`; FAIL `> 0.40`.

`BOUNDARY_STATUS_MAPPING`:

- pixel-lock failure => FAIL;
- any boundary metric FAIL => FAIL;
- otherwise any boundary metric NEEDS_REVIEW => NEEDS_REVIEW;
- otherwise all required metrics PASS => PASS;
- otherwise => UNVALIDATED.

## Approved Decision B — v3 quality policy identity

- `QUALITY_POLICY_ID = restoration-v3-quality-policy-1`
- `QUALITY_POLICY_VERSION = 1.0`
- Face-local minimum: retain existing necessary `90` criterion: `YES`
- Missing/non-authoritative QC result: retain `UNVALIDATED`: `YES`
- `BOUNDARY_PRECEDENCE = FAIL > UNVALIDATED > NEEDS_REVIEW > PASS`
- `APPROVED_BY = Harry Pham`
- `APPROVED_AT = 2026-08-27`

## Required approval

```text
BOUNDARY_POLICY = BOUNDARY-B
BOUNDARY_RING_DEFINITION = symmetric 3 px; 8-connected; Euclidean; OOB ignored
SEAM_THRESHOLDS = max-channel 32/48; mean 12/20; pixel-lock exact zero
TEXTURE_DISCONTINUITY_RULE = normalized Sobel mean-gradient delta; 0.25/0.40
QUALITY_POLICY_ID = restoration-v3-quality-policy-1
QUALITY_POLICY_VERSION = 1.0
QUALITY_POLICY_SHA256 = recorded in the versioned policy artifact
APPROVED_BY = Harry Pham
APPROVED_AT = 2026-08-27
STATUS = APPROVED
```

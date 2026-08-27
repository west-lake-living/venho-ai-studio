# Candidate v3 Phase 2 — Transform Authority Decision Pack

Status: **APPROVED**

This pack records repository evidence and prepares the unresolved authority
decisions required to unblock P2-T3. It does not create an executable transform
implementation or approve production behavior.

## Evidence boundary

Sources inspected:

- `docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md` §5.3 and Phase 2.
- `task_status.md` and `task_memory.md`.
- `identity_restoration/application/face_observability.py`.
- `identity_restoration/domain/entities.py` and
  `identity_restoration/domain/policies/geometry.py`.
- `identity_restoration/domain/compositing.py` and existing transform/mask tests.
- Existing Candidate v3 transform schemas and v2 workflow JSON.
- Existing face geometry/QC evidence and tolerances, treated as evidence only.

## Known authoritative facts

- Canonical output size: `512×512`.
- Image padding: `REFLECT_101`.
- Image interpolation: `LANCZOS4`.
- Landmark order at the P2-T1 boundary: left eye, right eye, nose, left mouth
  corner, right mouth corner.
- No GPU, provider, network, production, or feature-flag behavior is authorized
  by this pack.

## 1. CANONICAL TEMPLATE

### Classification

`AUTHORITATIVE` — approved by Harry Pham on `2026-08-27`.

### Known facts

- The roadmap requires a fixed 512×512 five-point template but does not provide
  its coordinates, template ID, version, or hash.
- `canonical_face_transform_v1.schema.json` records five landmarks and model
  size but has no canonical template identity or template hash.
- Existing detector/geometry evidence records source landmarks only; it does
  not define a target template.
- Approved 512×512 target template:
  `left_eye=(192.0,208.0)`, `right_eye=(320.0,208.0)`,
  `nose=(256.0,272.0)`, `left_mouth=(208.0,336.0)`,
  `right_mouth=(304.0,336.0)`.
- Approved template ID/version: `candidate_v3_face_template` / `1.0`.

### Candidate options

- `CT-A`: approved five-point similarity template above with ID
  `candidate_v3_face_template` version `1.0`. Consequence: P2-T3 may use this
  target after deriving and recording its canonical template SHA-256.

The coordinates are human authority inputs, not values derived from repository
evidence.

### Human decision

`APPROVED_OPTION: CT-A`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 2. CROP PADDING

### Classification

`AUTHORITATIVE` — approved by Harry Pham on `2026-08-27`.

### Known facts

- The roadmap specifies `cropPaddingRatio: <calibrated-value>` and gives no
  numeric value, policy ID, version, or hash.
- The roadmap requires a calibrated crop expanded from the detected face and
  reflected handling when expansion crosses image bounds.
- Existing `CropTransform` is an integer source box/value object; it does not
  define a Candidate v3 padding ratio.
- Approved crop padding ratio: `0.20`.

### Candidate options

- `CP-A`: crop padding ratio `0.20`. The associated transform policy is
  `candidate_v3_canonical_transform_policy` version `1.0`; its SHA-256 is to be
  derived from the canonical policy serialization during P2-T3 implementation.

The ratio is a human authority input, not a value derived from repository
evidence.

### Human decision

`APPROVED_OPTION: CP-A — 0.20`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 3. MASK INTERPOLATION

### Classification

`AUTHORITATIVE` — approved by Harry Pham on `2026-08-27`.

### Known facts

- The roadmap requires editable and feather masks to follow the exact image
  geometry but does not specify mask interpolation.
- Existing Candidate v3 schemas carry mask artifacts but no interpolation mode.
- Existing `composite_crop_into_canvas` uses crop/paste and does not resample a
  mask.
- Existing v2 workflow nodes expose mask conversion/feathering, but no
  Candidate v3 mask interpolation authority for binary or feather masks.
- The repository contains an unrelated cubic analysis resize path; it is not a
  Candidate v3 mask policy and is not an option here.
- Approved mask rules: image `LANCZOS4`, binary `NEAREST`, feather `LINEAR`,
  binary threshold `0.5`.

### Candidate options

- `MI-A`: image `LANCZOS4`, binary `NEAREST`, feather `LINEAR`, and binary mask
  threshold `0.5`.

The approved mask modes are human authority inputs; they were not selected from
the prior absence of repository evidence.

### Human decision

`IMAGE: LANCZOS4`

`BINARY: NEAREST`

`FEATHER: LINEAR`

`POST_THRESHOLD: 0.5`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 4. ROUND-TRIP TOLERANCE

### Classification

`AUTHORITATIVE` — approved by Harry Pham on `2026-08-27`.

### Known facts

- Existing `CropTransform.round_trips()` checks exact equality for integer crop
  boxes; it does not define a floating-point similarity-transform tolerance.
- Existing pixel-preservation policy defaults to byte tolerance `0`, which is a
  pixel-lock rule, not a geometric point/matrix round-trip limit.
- Existing `2.0` tolerances in golden/QC evidence apply to Face QC values, not
  canonical transform geometry.
- No repository test defines an applicable landmark-point, matrix, or
  mask-coordinate round-trip tolerance for P2-T3.
- Approved scope: landmark point maximum Euclidean error.
- Approved limit: `0.5 px`.

### Candidate options

- `RT-A`: landmark point maximum Euclidean round-trip error `0.5 px`.
  Consequence: inverse verification must fail closed above this limit.

The tolerance is a human authority input, not a value derived from repository
evidence.

### Human decision

`APPROVED_OPTION: RT-A — 0.5 px, landmark point max Euclidean error`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 5. TRANSFORM POLICY ID / VERSION

### Classification

`AUTHORITATIVE` — approved by Harry Pham on `2026-08-27`.

### Naming evidence

- The approved route policy uses `candidate_v3_route_policy` version `1.0`.
- Approved Candidate v3 canonical transform policy ID/version is
  `candidate_v3_canonical_transform_policy` / `1.0`.

### Policy options

- `TP-A`: approved `candidate_v3_canonical_transform_policy`, version `1.0`.
  Its policy SHA-256 is to be derived from canonical policy serialization during
  P2-T3 implementation.
- `TP-HUMAN`: human supplies a different exact policy ID and version. Consequence:
  P2-T3 uses no transform policy identity until explicitly approved.

`TP-A` is approved by this pack; the policy contents and derived SHA-256 remain
an implementation output.

### Human decision

`APPROVED_POLICY_ID: candidate_v3_canonical_transform_policy`

`APPROVED_POLICY_VERSION: 1.0`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## HUMAN TRANSFORM AUTHORITY APPROVAL

CANONICAL_TEMPLATE = 5-point similarity template on 512x512 canvas: left_eye=(192.0, 208.0), right_eye=(320.0, 208.0), nose=(256.0, 272.0), left_mouth=(208.0, 336.0), right_mouth=(304.0, 336.0); TEMPLATE_ID=candidate_v3_face_template; TEMPLATE_VERSION=1.0
CROP_PADDING_RATIO = 0.20
MASK_INTERPOLATION_IMAGE = LANCZOS4
MASK_INTERPOLATION_BINARY = NEAREST
MASK_INTERPOLATION_FEATHER = LINEAR
BINARY_MASK_THRESHOLD = 0.5
ROUND_TRIP_ERROR_LIMIT = 0.5 px
ROUND_TRIP_SCOPE = landmark point max Euclidean error
TRANSFORM_POLICY_ID = candidate_v3_canonical_transform_policy
TRANSFORM_POLICY_VERSION = 1.0

APPROVED_BY = Harry Pham
APPROVED_AT = 2026-08-27
STATUS = APPROVED

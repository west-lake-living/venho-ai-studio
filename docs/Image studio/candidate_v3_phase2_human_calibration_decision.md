# Candidate v3 Phase 2 — Human Calibration Decision Pack

Status: **APPROVED**

This pack records the human authority decisions required to unblock P2-T2. It
does not authorize production cutover or feature-flag changes.

## Evidence boundary

Sources reviewed:

- `docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md` §5.1, §8, and
  Phase 2.
- `task_status.md` and `task_memory.md`.
- `docs/identity-restoration/BENCHMARK_DATASET_V2_1.md` and
  `docs/identity-restoration/BENCHMARK_PROTOCOL.md`.
- Frozen geometry manifests under
  `artifacts/identity-restoration/benchmark-geometry/v2.1/{B05,B06,B10}`.
- P2-T1 `FaceObservability` contract, implementation, and CPU tests.
- Existing geometry/QC reports, treated as evidence only; downstream Face QC
  thresholds are not observability recoverability authority.

The frozen geometry manifests use the pinned YuNet model and contain one
detection for each requested fixture. They are not P2-T1 service outputs and
do not contain Candidate v3 route labels.

## Locked measurements

| Fixture | BBox W×H px | Interocular px | Face area ratio | Face scale | Confidence | Yaw / pitch / roll (deg) | Reprojection error px |
|---|---:|---:|---:|---:|---:|---|---:|
| B05 | 74×114 | 21.936952 | 0.0064361572 | 0.072265625 | 0.9200561 | -49.077421 / -150.999298 / -12.795656 | 2.352526 |
| B06 | 82×111 | 36.791913 | 0.0069442749 | 0.080078125 | 0.9353456 | -7.586991 / -156.469397 / -3.786555 | 1.947409 |
| B10 | 43×76 | 5.927996 | 0.0030488715 | 0.0507075472 | 0.8542693 | 79.361665 / -141.704198 / 27.606772 | 0.987460 |

All three manifests record `detection_count=1`, five landmarks, and the same
YuNet model SHA. B05 and B06 have no authoritative route label. B10 is
authoritatively non-`ELIGIBLE` and is normally expected to use
`BASE_REGEN_REQUIRED` semantics.

## 1. B05 route label

### Known facts

- Frozen source: Running Side; visible lateral face.
- One YuNet detection; bbox `74×114`; interocular `21.936952 px`; area ratio
  `0.0064361572`; confidence `0.9200561`; yaw `-49.077421°`.
- No Candidate v3 route label is recorded.

### Safe human options

| Option | Candidate rule | Consequence |
|---|---|---|
| B05-A | `ELIGIBLE` only if every approved positive observability rule passes | B05 may proceed only after explicit positive proof; no implicit fallback |
| B05-B | `REVIEW_REQUIRED` for the lateral-pose class | B05 does not proceed automatically and remains auditable |
| B05-C | `BASE_REGEN_REQUIRED` if the authority treats its information as unrecoverable | B05 cannot consume restoration execution |

These are decision forms, not recommendations. The measurements alone do not
select one.

### Human decision

`APPROVED_OPTION: B05-A — ELIGIBLE only if every approved positive observability rule passes`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 2. B06 route label

### Known facts

- Frozen source: Walking; visible face and unambiguous walking gait.
- One YuNet detection; bbox `82×111`; interocular `36.791913 px`; area ratio
  `0.0069442749`; confidence `0.9353456`; yaw `-7.586991°`.
- No Candidate v3 route label is recorded.

### Safe human options

| Option | Candidate rule | Consequence |
|---|---|---|
| B06-A | `ELIGIBLE` only if every approved positive observability rule passes | B06 may proceed only after explicit positive proof |
| B06-B | `REVIEW_REQUIRED` for unresolved walking/quality ambiguity | B06 does not proceed automatically |
| B06-C | `BASE_REGEN_REQUIRED` if the authority treats its information as unrecoverable | B06 cannot consume restoration execution |

These are decision forms, not recommendations. The measurements alone do not
select one.

### Human decision

`APPROVED_OPTION: B06-A — ELIGIBLE only if every approved positive observability rule passes`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 3. B10 route label

### Known facts

- Frozen source: Ven Ho Hotel Interior; distant/full-body case.
- One YuNet detection; bbox `43×76`; interocular `5.927996 px`; area ratio
  `0.0030488715`; confidence `0.8542693`; yaw `79.361665°`.
- The roadmap explicitly requires B10-like input to remain non-`ELIGIBLE`; the
  microface edge case maps normally to `BASE_REGEN_REQUIRED`.

### Safe human options

| Option | Candidate rule | Consequence |
|---|---|---|
| B10-A | `BASE_REGEN_REQUIRED` for the microface/recoverability class | B10 is retained and audited but does not proceed as restoration |
| B10-B | `REVIEW_REQUIRED` for a human decision on the compound microface/pose case | B10 cannot proceed automatically |
| B10-C | Any other route | Not safe to select without an explicit authority amendment |

### Human decision

`APPROVED_OPTION: B10-A — BASE_REGEN_REQUIRED for the microface/recoverability class`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 4. Microface / recoverability rule

### Known facts

B10 is smaller than both B05 and B06 on every listed size proxy:

- interocular: `5.927996 < 21.936952 < 36.791913`
- face area ratio: `0.0030488715 < 0.0064361572 < 0.0069442749`
- bbox width: `43 < 74 < 82`
- bbox height: `76 < 111 < 114`

The evidence does not label B05 or B06 as recoverable/unrecoverable.

### Safe mathematical candidates

| Option | Exact derivation | B05 | B06 | B10 |
|---|---|---|---|---|
| M-A | `interocular <= 5.927996`, the observed B10 value | not flagged | not flagged | `BASE_REGEN_REQUIRED` |
| M-B | `face_area_ratio <= 0.0030488715`, the observed B10 value | not flagged | not flagged | `BASE_REGEN_REQUIRED` |
| M-C | Any threshold strictly inside the observed gap: `5.927996 < T < 21.936952` for interocular, or `0.0030488715 < T < 0.0064361572` for area ratio | not flagged | not flagged | `BASE_REGEN_REQUIRED` |

M-A and M-B use B10's boundary value. M-C is an evidence-derived interval,
not an approved numeric threshold. A composite AND/OR of these proxies would
change behavior for unseen inputs and therefore requires human approval. One
B10 point does not establish general recoverability semantics.

### Human decision

`APPROVED_OPTION: M-B — face_area_ratio <= 0.0030488715 => BASE_REGEN_REQUIRED`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 5. Extreme-pose rule

### Known facts

- B05 yaw `-49.077421°`, roll `-12.795656°`.
- B06 yaw `-7.586991°`, roll `-3.786555°`.
- B10 yaw `79.361665°`, roll `27.606772°`.
- Existing pitch values use the repository's PnP convention and are not a
  calibrated human pose scale.

### Safe mathematical candidates

| Option | Exact derivation | B05 | B06 | B10 |
|---|---|---|---|---|
| P-A | `abs(yaw) >= 79.361665°`, the observed B10 yaw magnitude | not flagged | not flagged | `REVIEW_REQUIRED` candidate |
| P-B | Any separator in `49.077421° < T < 79.361665°` for `abs(yaw)` | not flagged | not flagged | `REVIEW_REQUIRED` candidate |
| P-C | Human-reviewed pose class rather than a numeric threshold | human decision | human decision | human decision |

The route precedence means B10's approved microface rule takes precedence over
the extreme-pose review candidate, so B10 remains `BASE_REGEN_REQUIRED`.

### Human decision

`APPROVED_OPTION: P-A — abs(yaw) >= 79.361665° => REVIEW_REQUIRED`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 6. Landmark-uncertainty rule

### Known facts

- All locked manifests contain five finite landmarks and one detection.
- Reprojection error is B05 `2.352526 px`, B06 `1.947409 px`, and B10
  `0.987460 px`.
- P2-T1 validates landmark count, finite coordinates, bbox validity, and
  positive interocular geometry, but does not provide a calibrated uncertainty
  threshold or a labelled uncertain fixture.

### Safe mathematical candidates

| Option | Exact derivation | B05 | B06 | B10 |
|---|---|---|---|---|
| L-A | Structural only: exactly five finite landmarks and positive interocular | pass | pass | pass |
| L-B | `reprojection_error <= 2.352526 px`, the maximum observed locked error | pass | pass | pass |
| L-C | Human rule required for blur/occlusion/collinearity beyond structural validity | human decision | human decision | human decision |

L-A and L-B do not identify an uncertain fixture; selecting them as a
recoverability rule would require authority beyond these examples.

### Human decision

`APPROVED_OPTION: L-A — exactly 5 finite landmarks AND interocular_distance > 0`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## 7. Positive ELIGIBLE contract

### Known facts

The roadmap requires positive proof and prohibits `else -> ELIGIBLE`. The
following checklist is the minimum candidate contract:

- input decodes and mask is structurally valid;
- exactly one eligible target face is observed inside the editable region;
- detector ID, version, model/config hash, and measurement hash match;
- detector confidence meets the pinned detector minimum;
- bbox and exactly five landmarks are valid;
- all required measurements are finite;
- mask relation is valid;
- microface/recoverability rule passes;
- extreme-pose rule passes;
- landmark-uncertainty rule passes;
- no unresolved multiple-face or other ambiguity exists.

### Safe human-selectable candidate forms

| Option | Positive form | B05/B06/B10 consequence |
|---|---|---|
| E-A | The checklist above plus human-approved M/P/L rules; only an explicit all-pass result is `ELIGIBLE` | B05/B06 remain conditional; B10 remains non-`ELIGIBLE` unless authority explicitly changes its route |
| E-B | The checklist plus a closed positive allowlist of approved measurement intervals | Only fixtures inside the approved intervals can be `ELIGIBLE`; others fail closed |
| E-C | No positive route until labelled positive fixtures and all thresholds are approved | B05/B06/B10 cannot be `ELIGIBLE` yet |

No form supplies missing thresholds. No form authorizes an implicit fallback.

### Human decision

`APPROVED_OPTION: E-A — explicit all-pass positive observability contract`

`APPROVED_BY: Harry Pham`

`APPROVED_AT: 2026-08-27`

## HUMAN CALIBRATION APPROVAL

B05_ROUTE: ELIGIBLE_IF_ALL_POSITIVE_RULES_PASS
B06_ROUTE: ELIGIBLE_IF_ALL_POSITIVE_RULES_PASS
B10_ROUTE: BASE_REGEN_REQUIRED

MICROFACE_RULE: face_area_ratio <= 0.0030488715 => BASE_REGEN_REQUIRED
EXTREME_POSE_RULE: abs(yaw) >= 79.361665 => REVIEW_REQUIRED
LANDMARK_UNCERTAINTY_RULE: exactly 5 finite landmarks AND interocular_distance > 0

POSITIVE_ELIGIBLE_RULE: input structurally valid AND exactly one eligible face AND detector/config pin valid AND confidence valid AND bbox valid AND exactly 5 finite landmarks AND interocular_distance > 0 AND measurements finite AND mask relation valid AND face_area_ratio > 0.0030488715 AND abs(yaw) < 79.361665 AND no unresolved ambiguity => ELIGIBLE

POLICY_ID: candidate_v3_route_policy
POLICY_VERSION: 1.0

APPROVED_BY: Harry Pham
APPROVED_AT: 2026-08-27

STATUS: APPROVED

# Candidate v3 Phase 2 Route Calibration Authority Audit

Status: **BLOCKED** (`P2-T2-B1`)

This report records the repository-only authority review for the P2-T2
deterministic route policy. It does not define an executable route policy and
does not alter any benchmark fixture.

## Policy lock

- Policy ID: **NOT LOCKED**
- Policy version: **NOT LOCKED**
- Policy SHA-256: **NOT AVAILABLE**
- Executable authority complete: **NO**
- Reason: mandatory route dimensions remain unresolved.

The only canonical serialization convention available for a future policy is
the existing P2-T1 convention: UTF-8 JSON, recursively sorted object keys,
compact separators, ASCII escaping, `allow_nan=false`, then SHA-256 over the
serialized bytes. No route-policy bytes are being created here.

## Evidence sources

- `docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md` §5.1 and Phase 2:
  route codes, precedence, B10-like behavior, and the requirement for a
  versioned calibration policy calibrated on B05, B06, and B10.
- `docs/identity-restoration/BENCHMARK_DATASET_V2_1.md` and
  `docs/identity-restoration/BENCHMARK_PROTOCOL.md`: B05, B06, and B10 are
  frozen source artifacts with hashes and dimensions, but no Candidate v3
  route labels.
- Existing geometry manifests:
  `artifacts/identity-restoration/benchmark-geometry/v2.1/B05/geometry_manifest.json`,
  `B06/geometry_manifest.json`, and `B10/geometry_manifest.json`.
- P2-T1 implementation and tests:
  `identity_restoration/application/face_observability.py` and
  `tests/identity_restoration/application/test_face_observability.py`.
- Existing QC reports were reviewed but are not route authority. Their Face QC
  threshold is a downstream quality criterion, not an observability
  recoverability threshold.

## Locked fixture measurements

The following values are available from the frozen v2.1 YuNet geometry
manifests. They are evidence measurements, not a P2-T2 route result and not
P2-T1 service output.

| Fixture | Source SHA-256 | Source size | Detection count | BBox W×H px | Interocular px | Face area ratio | Face scale | Confidence | Yaw / pitch / roll (deg) | Reprojection error px |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| B05 | `06f4b6b0b6ea47dee71a240065411899cb3fa2b84633dacddba4d232afce5492` | 1024×1280 | 1 | 74×114 | 21.936952 | 0.0064361572 | 0.072265625 | 0.9200561 | -49.077421 / -150.999298 / -12.795656 | 2.352526 |
| B06 | `526190e3632d189d588dcdfda32f1d7930c449a6b2188961d7907ef7746d8e` | 1024×1280 | 1 | 82×111 | 36.791913 | 0.0069442749 | 0.080078125 | 0.9353456 | -7.586991 / -156.469397 / -3.786555 | 1.947409 |
| B10 | `32c701012e40040772c69bff102719c5d48c9c046bad442f68f1bc520c5bc507` | 848×1264 | 1 | 43×76 | 5.927996 | 0.0030488715 | 0.0507075472 | 0.8542693 | 79.361665 / -141.704198 / 27.606772 | 0.987460 |

The source hashes above are evidence pins only; they are not route-policy
inputs until a complete policy is authorized.

## Required route authority

### Invalid input

- Rule: malformed image, decode failure, unsupported image, no face, or invalid
  mask routes to `REJECTED_INVALID_INPUT`.
- Source: Candidate v3 roadmap §5.1 and §8; P2-T1 fail-closed evidence.
- Status: **AUTHORITATIVE**.

### Microface / B10-like

- Rule: microface or low interocular distance routes to
  `BASE_REGEN_REQUIRED`; B10-like input must not proceed as normal
  restoration.
- Available value: B10 has 43×76 px bbox, 5.927996 px interocular distance,
  and face area ratio 0.0030488715.
- Source: Candidate v3 roadmap §5.1, §8, and Phase 2 exit criteria; B10 frozen
  geometry manifest.
- Status: **UNRESOLVED** for a general executable boundary. B05/B06 have no
  authoritative expected route labels, so a boundary derived from their
  measurements would introduce an unproven semantic classification.

### Extreme pose

- Rule: extreme pose requires `REVIEW_REQUIRED` unless an authorized policy
  permits another route.
- Available values: existing manifests record pose proxies, but no calibrated
  extreme-pose threshold or expected B05/B06 route is recorded.
- Source: Candidate v3 roadmap §5.1 and §8; frozen geometry manifests.
- Status: **UNRESOLVED**.

### Landmark uncertainty

- Rule: uncertain or invalid landmarks cannot establish a positive route;
  canonicalization must fail closed.
- Available values: five landmarks and YuNet reprojection error are present in
  geometry manifests. P2-T1 has structural landmark validation, but no
  landmark-confidence/reprojection calibration threshold.
- Source: Candidate v3 roadmap §5.1 and §8; P2-T1 contract and implementation.
- Status: **UNRESOLVED**.

### Multiple face

- Rule: multiple candidates route to `REVIEW_REQUIRED` unless server-owned
  target association resolves exactly one face; no implicit largest-face
  selection is allowed.
- Source: Candidate v3 roadmap §5.1 and §8; P2-T1 multiple-face observation.
- Status: **AUTHORITATIVE**.

### ELIGIBLE

- Positive requirements: exactly one valid target face; valid image and mask;
  face inside the editable region; detector/config provenance matches; all
  required measurements are finite; every calibrated recoverability, pose,
  landmark, border, sharpness, and occlusion rule passes.
- Source: Candidate v3 roadmap §5.1 and P2-T1 output contract.
- Status: **UNRESOLVED** because the calibrated positive thresholds and locked
  positive examples are absent. No `else -> ELIGIBLE` rule is authorized.

## Fixture classification

| Fixture | Available evidence | Expected route class | Authority status |
|---|---|---|---|
| B05 | Frozen source and YuNet geometry; visible lateral face; no route label | UNRESOLVED | **UNRESOLVED** |
| B06 | Frozen source and YuNet geometry; visible walking face; no route label | UNRESOLVED | **UNRESOLVED** |
| B10 | Frozen source and YuNet geometry; microface/low interocular evidence | `BASE_REGEN_REQUIRED` / non-`ELIGIBLE` | **AUTHORITATIVE for B10-like behavior only** |

The measurements show B10 is smaller than B05/B06, but the repository does
not establish a general boundary, expected B05/B06 route classes, or calibrated
pose/landmark semantics. No midpoint, minimum, or other derived constant is
locked.

## Result and guardrails

`P2-T2-B1` remains **BLOCKED**. No executable policy config, route evaluator,
calibration tests, fixture mutation, generation, QC tuning, GPU call,
provider/network call, feature-flag change, or v2/v2.1 change is authorized by
this report.

# VENHO — Candidate v3: Technical Specification & Implementation Plan

**Status:** Proposed for implementation
**Date:** 2026-08-27
**Scope:** Linh An identity-restoration candidate only; no provider/GPU execution is authorized by this specification.
**Compatibility target:** Existing v2.0/v2.1 control plane, `StudioJobRecord`, restoration bridge, Python restoration application, and Manifest 1.3.

## 1. Decision and success definition

Candidate v3 is a new, versioned restoration candidate. It does **not** modify historical v2/v2.1 artifacts, overwrite the current workflow, alter benchmark images, lower a gate, or silently omit difficult cases.

The design keeps the GTX 1660 Super 6 GB as the local execution constraint. The quality improvement is expected to come from correcting input canonicalization, multi-pose identity authority, scenario-aware validation, and deterministic routing—not from an assumption that a larger GPU is required.

Candidate v3 may be promoted only when a locked, complete benchmark passes every required gate:

```text
promotion = complete_benchmark
         AND every_required_row_evaluated
         AND pixel_lock_passed
         AND transform_round_trip_passed
         AND local_face_qc_passed
         AND boundary_qc_passed
         AND scenario_global_qc_passed
         AND no_missing_authority_or_evidence
         AND human_approval_recorded
```

`Face-QC >= 90` is a necessary local criterion, not a production verdict by itself. Candidate v3 must not claim success for a face that is too small, occluded, blurred, or out-of-pose to contain recoverable identity signal. That input must be routed deterministically to base-image regeneration or review.

## 2. Evidence-derived problem statement

The reference reports are design evidence, not autonomous instructions. The following requirements are intentionally adopted into this plan.

| Observed issue | Technical cause | v3 corrective control |
|---|---|---|
| Distant/full-body faces fail identity and geometry | The active path sends native, non-canonical crops to diffusion. A B10-like crop can be approximately `107×190`; no restore model can reconstruct reliable personal identity from insufficient pixels. | Face-observability preflight; canonical 512-square model crop; `BASE_REGEN_REQUIRED` for unrecoverable microfaces. |
| Identity shifts across action/profile cases | One frontal A2 authority image is insufficient conditioning for all poses; existing crop/model conditioning is not pose-aware. | Versioned, human-approved `IdentityPack` with frontal, 3/4, and profile references; deterministic pose-aware selection. |
| Output can be cosmetically plausible but generic | Generic SD1.5 workflow, minimal conditioning prompt, and no explicit canonical transform make the restore task underspecified. | A pinned v3 graph with semantic bindings, fixed model-space input, explicit conditioning profile, and fully recorded effective configuration. |
| Global QC can reject a correct face for scenario traits outside the editable region | Face restoration and global image authority are conflated. Some actions require approved exemptions for distance, hairstyle, pose, or framing. | Three distinct QC scopes and a human-approved scenario authority binding for every scenario. |
| Current result is difficult to reproduce/audit at v3 granularity | Existing lineage records crop transform but does not represent input observability, identity-pack selection, model-space transform, or split QC bundle. | Additive v3 lineage, immutable artifacts, config hashes, and manifest 1.4. |

The P7 benchmark remains immutable evidence: it must not be retrospectively reclassified as a v3 pass. Authority-scope correction is only valid when the same image is replayed against an explicit, approved scenario profile; it is not a reason to waive genuine image defects.

## 3. Architectural constraints and invariants

### 3.1 Preserve these boundaries

```text
Browser/UI
  -> existing Next.js identity-restoration API
  -> existing StudioJobRecord / idempotency mechanism
  -> TypeScript restoration service + JSON bridge
  -> Python application use case + RestorerPort
  -> ComfyUI adapter / GPU worker
  -> immutable artifacts + Manifest 1.4
  -> validators + human decision
```

- Keep the TypeScript control plane and Python image-processing plane.
- Extend the existing `identity-restoration` job type. Do not create a second job store, queue, or parallel state machine.
- Keep the existing port/adapter boundary. Domain and application code must not contain ComfyUI node IDs, checkpoint paths, or vendor-specific graph terms.
- Create a new workflow file and a new candidate ID. Never mutate a promoted or benchmarked workflow in place.
- The source base image is immutable. Pixels outside the approved editable mask must remain identical after compositing.
- All decision-relevant inputs and outputs must have a SHA-256 hash and stable artifact path.
- Absence of an authority profile, reference pack, transform, or QC result is `UNVALIDATED`, never implicit pass.

### 3.2 Candidate profile

`candidate_profile_id` is the only selectable runtime profile. The browser never selects raw checkpoint, reference image path, denoise value, seed, or validator exemption.

```yaml
candidateProfileId: candidate-v3-sd15-faceid-canonical-512
candidateVersion: "3.0.0"
enabled: false
runtimeClass: gpu-6gb
workflow:
  id: face_restore_win_sd15_ipadapter_v3
  sha256: <pinned-at-release>
canonicalInput:
  size: 512
  cropPaddingRatio: <calibrated-value>
  alignment: similarity_landmark_5pt
  interpolation: lanczos4
conditioning:
  identityPackPolicy: pose_aware_v1
  baselineParams:
    denoise: 0.30
    steps: <pinned-value>
    cfg: <pinned-value>
    sampler: <pinned-value>
    scheduler: <pinned-value>
qualityPolicyId: restoration-v3-quality-policy-1
```

The numerical values marked `calibrated` or `pinned` are configuration data with their own hash. They are not mutable UI controls.

## 4. Persistence and data design

### 4.1 Storage strategy

The current service persists one JSON document per `StudioJobRecord` under the Studio jobs directory. Candidate v3 extends that record and the artifact manifest additively. This is appropriate at the present local-job scale; an additional database is not required for v3.

If job volume later makes directory scans unsuitable, introduce an indexed store only through a migration that preserves `jobId`, idempotency semantics, immutable manifests, and existing JSON export. That future migration is out of scope.

### 4.2 New immutable reference entities

#### `IdentityPack`

An identity pack is a human-approved set of references. It is not a folder that the system may auto-populate.

```ts
interface IdentityPackV1 {
  schemaVersion: "1.0";
  identityPackId: string;                  // e.g. linh-an-production-2026-08
  identitySubjectId: "linh-an";
  status: "DRAFT" | "APPROVED" | "RETIRED";
  approvedAt?: string;
  approvedBy?: string;
  references: IdentityReferenceV1[];
  sha256: string;                          // canonical JSON hash
}

interface IdentityReferenceV1 {
  referenceId: string;
  artifactPath: string;
  artifactSha256: string;
  role: "PRIMARY_FRONTAL" | "THREE_QUARTER" | "PROFILE";
  pose: { yawDeg: number; pitchDeg: number; rollDeg: number; toleranceDeg: number };
  faceBounds: { left: number; top: number; right: number; bottom: number };
  usableRegions: Array<"eyes" | "nose" | "mouth" | "jaw" | "hairline">;
  consentOrAuthorityRef: string;
  approved: boolean;
}
```

Rules:

1. Exactly one `PRIMARY_FRONTAL` reference is required and remains the root A2 authority.
2. Every reference must be human-approved, exist on disk, match its SHA-256, and contain one detectable face.
3. An `APPROVED` pack is immutable. Changing a reference creates a new `identityPackId` and hash.
4. A failed optional pose reference does not fall back silently. The route decision records use of the primary reference or moves to review according to policy.

#### `ScenarioAuthorityBinding`

Global validation requires a separately approved scenario authority profile.

```ts
interface ScenarioAuthorityBindingV1 {
  schemaVersion: "1.0";
  bindingId: string;
  scenarioId: string;
  imageQcProfileId: string;
  imageQcProfileSha256: string;
  allowedExclusions: Array<
    "shot_distance" | "camera_angle" | "hairstyle" | "pose" | "outfit" | "background"
  >;
  approvedBy: string;
  approvedAt: string;
  status: "APPROVED" | "RETIRED";
}
```

The binding is supplied by an approved server-side scenario registry. It must never be inferred from a prompt, filename, or model output.

### 4.3 Additive job record

Add `candidateV3?: StudioCandidateV3Record` to `StudioRestorationAttemptRecord.result` and to the durable manifest evidence. Historical jobs remain valid because the field is optional.

```ts
interface StudioCandidateV3Record {
  schemaVersion: "1.0";
  candidateProfileId: string;
  candidateVersion: string;
  effectiveConfigSha256: string;
  inputArtifact: ArtifactRef;
  identityPack: { id: string; sha256: string; selectedReferenceIds: string[] };
  scenarioAuthority: { id: string; sha256: string };
  route: RestorationRouteDecision;
  faceObservability: FaceObservability;
  transforms: CanonicalFaceTransform;
  artifacts: RestorationArtifactsV3;
  quality: RestorationQualityBundleV3;
  promotionEligibility: "PASS" | "FAIL" | "UNVALIDATED";
}

interface ArtifactRef {
  path: string;
  sha256: string;
  width: number;
  height: number;
  mimeType: "image/png" | "application/json";
}
```

Artifact names must include `runId`, `attemptId`, and a content/config suffix. A retry creates a new attempt and new artifacts; it never overwrites a prior result.

### 4.4 Manifest evolution

Create `manifest-1-4.ts` as a pure transformation from 1.3 to 1.4:

```text
Manifest 1.2 -> Manifest 1.3 (existing restoration evidence)
Manifest 1.3 -> Manifest 1.4 (candidateV3 evidence only)
```

The input and output paths must differ. Manifest 1.4 stores:

- existing 1.3 `restoration` unchanged;
- `restoration.candidateV3` with the record above;
- `qualityHistory[]` as append-only entries, never replacement of historical authoritative QC;
- workflow, model, validator, identity-pack, authority-profile, and threshold-config hashes.

### 4.5 Idempotency and consistency

Use two keys:

```text
clientReplayKey = existing API idempotency key
attemptFingerprint = SHA256(
  baseArtifactSha + editableMaskSha + identityPackSha + scenarioAuthoritySha
  + candidateProfileId + workflowSha + effectiveConfigSha
)
```

- A repeated request with the same `clientReplayKey` returns the existing job.
- A repeated execution attempt with the same `attemptFingerprint` may reuse a completed immutable result only if every artifact hash and all quality evidence exist. Otherwise it fails safe and creates an explicitly logged retry attempt.
- Job status transition and manifest write must use a temporary file then atomic rename. The job cannot be marked `COMPLETED` until manifest write and every required artifact verification succeed.

## 5. Core domain algorithms

### 5.1 Input verification and face observability

The preflight algorithm decides whether restoration is technically meaningful before GPU allocation.

```ts
type RouteCode =
  | "ELIGIBLE"
  | "REVIEW_REQUIRED"
  | "BASE_REGEN_REQUIRED"
  | "REJECTED_INVALID_INPUT";

interface FaceObservability {
  detectorId: string;
  detectorVersion: string;
  faceCount: number;
  bbox: { left: number; top: number; right: number; bottom: number };
  bboxWidthPx: number;
  bboxHeightPx: number;
  interocularDistancePx?: number;
  landmarkConfidence?: number;
  yawDeg?: number;
  pitchDeg?: number;
  rollDeg?: number;
  sharpness?: number;
  occlusionScore?: number;
  borderClipped: boolean;
  qualityTier: "HIGH" | "LIMITED" | "UNRECOVERABLE";
  measurementConfigSha256: string;
}
```

Algorithm:

1. Normalize EXIF orientation and decode into a known color space before detection.
2. Detect faces with the pinned detector. Do not use a detector’s result if confidence is below its configured minimum.
3. Require exactly one eligible target face inside the editable region. Multiple faces require explicit, server-side target association; otherwise return `REVIEW_REQUIRED`.
4. Compute bbox size, five-point landmark confidence, interocular distance, pose, border clipping, local sharpness (variance of Laplacian), and occlusion estimate.
5. Apply a **versioned calibration policy**, not ad-hoc hard-coded thresholds. The initial policy must be calibrated on locked examples including B05, B06, and B10.
6. Return a route and all measured values. Persist the first failing rule and all applicable failing rules.

Decision precedence:

```text
malformed image / no face / invalid mask                 -> REJECTED_INVALID_INPUT
face below recoverable information threshold             -> BASE_REGEN_REQUIRED
multiple candidates / extreme pose / uncertain landmarks -> REVIEW_REQUIRED
otherwise                                                -> ELIGIBLE
```

`BASE_REGEN_REQUIRED` means “generate a base image where the face is larger, visible, and adequately lit.” It is not a rejection of the person and not a failed face-repair output.

### 5.2 Pose-aware reference selection

The selector operates only over the approved identity pack.

```text
referenceDistance(r, face) =
  wYaw   * abs(r.pose.yawDeg   - face.yawDeg)
  + wPitch * abs(r.pose.pitchDeg - face.pitchDeg)
  + penalty(if required usable region is unavailable)

selected = approved references sorted by referenceDistance
```

Rules:

- The primary A2 frontal reference is always included as the root authority.
- Add the closest approved pose reference only if the pose distance is inside that reference’s tolerance and it has the required visible regions.
- The number of references is bounded by candidate configuration to protect VRAM.
- If no non-frontal reference matches, use A2 only when the route policy permits; otherwise return `REVIEW_REQUIRED`.
- Record candidate references, distances, selection reason, and rejected-reference reasons. Never select based on an embedding similarity computed from an unapproved file.

### 5.3 Canonical face transform

Candidate v3 separates **canvas space** from **model space**.

```text
base image (canvas space)
  -> padded canvas crop
  -> landmark similarity alignment
  -> 512×512 canonical model crop
  -> restoration model
  -> inverse warp
  -> canvas crop
  -> mask-constrained composite into base image
```

`CanonicalFaceTransform` is required for every eligible attempt:

```ts
interface CanonicalFaceTransform {
  version: "1.0";
  sourceImage: { width: number; height: number; sha256: string };
  canvasCropBox: { left: number; top: number; right: number; bottom: number };
  modelSize: 512;
  landmarkSet: Array<{ x: number; y: number; confidence: number }>;
  forwardMatrix3x3: number[];
  inverseMatrix3x3: number[];
  borderMode: "REFLECT_101";
  interpolation: "LANCZOS4";
  transformSha256: string;
}
```

Algorithm:

1. Expand the detected face to a calibrated crop, clamped to image bounds.
2. If expansion crosses image bounds, use reflected padding in model-space preprocessing. Do not distort aspect ratio by simple rectangular stretch.
3. Estimate a five-point similarity transform from detected landmarks to a fixed 512×512 template.
4. Reject if matrix condition number is invalid, landmarks are too weak, the transform maps the target face outside expected model bounds, or inverse round-trip error exceeds the configured limit.
5. Warp the image **and all editable/feather masks** with the same transform. Hash each transformed artifact.
6. Restore only the canonical image. Inverse warp the restored image and its alpha/mask before the final canvas composite.

Verification:

```text
base -> forward -> inverse -> compare inside a non-generated control region
max geometric error <= configured tolerance
mask dimensions and transform hashes match exactly
```

This corrects the current native-size crop limitation without pretending that interpolation creates identity information. Canonicalization gives the model stable input geometry; preflight guards the lower information boundary.

### 5.4 Candidate v3 restoration request

Create a domain request with candidate-neutral terms. The ComfyUI adapter maps it to a v3 graph.

```ts
interface CanonicalRestorationRequest {
  runId: string;
  attemptId: string;
  canonicalImage: ArtifactRef;
  canonicalEditableMask: ArtifactRef;
  canonicalFeatherMask: ArtifactRef;
  transform: CanonicalFaceTransform;
  selectedIdentityReferences: ArtifactRef[];
  candidateProfileId: string;
  seed: number;
  effectiveConfigSha256: string;
  timeoutSeconds: number;
}
```

Candidate adapter requirements:

- The v3 ComfyUI graph uses explicit semantic titles for every externally bound value. Binding must fail if a title is missing, duplicated, or resolves to an unexpected node type.
- The graph accepts only 512×512 canonical input. It must reject a different geometry rather than resize silently.
- The workflow hash, custom-node versions, model identifiers, and all bound values are reported back by the adapter.
- The adapter must execute exactly one restore operation per attempt. Any internal multi-pass behavior must be a separately named and benchmarked candidate profile.
- Use the existing 6 GB worker lease, health gate, cancellation checks, timeout, and OOM-safe cleanup.

The initial v3 profile starts from the evidence-supported `denoise: 0.30` baseline. It is a baseline, not a production guarantee. Any parameter change produces a new effective-config hash and requires the locked benchmark protocol.

### 5.5 Inverse composite and pixel lock

1. Inverse-warp the restored canonical crop into the canvas crop.
2. Intersect the inverse-warp alpha with the inverse-warp editable mask.
3. Apply feathering only inside the approved editable region.
4. Optionally apply a bounded luminance/chroma adjustment computed from a narrow ring immediately outside the mask. The adjustment must not alter pixels outside the editable mask.
5. Composite into a copy of the original base image.
6. Compute `diff(original, composite)` outside the full-canvas editable mask. Any changed pixel is a hard failure.

```text
pixel_lock_passed = changed_pixels(outside_editable_mask) == 0
```

The composite module must never rely on crop coordinates alone after canonicalization; it consumes the verified inverse transform and full-canvas mask.

### 5.6 Split quality evaluation

Each validation has a distinct input, authority, and failure meaning.

| QC scope | Input | Owns | Must not judge |
|---|---|---|---|
| `FACE_LOCAL` | canonical restored crop + selected identity refs | identity resemblance, eyes, face geometry, visible face anatomy | background, framing, scenario hairstyle/exclusions |
| `BOUNDARY` | canvas crop / seam ring / composite | mask containment, inverse-warp correctness, blend seam, color continuity, local texture discontinuity | global scenario compliance |
| `SCENARIO_GLOBAL` | final composite + approved scenario profile | composition traits explicitly owned by that profile | traits explicitly excluded by that profile or pixels outside restoration ownership |

```ts
interface RestorationQualityBundleV3 {
  faceLocal: ScopedQcResult;
  boundary: ScopedQcResult;
  scenarioGlobal: ScopedQcResult;
  merged: {
    status: "PASS" | "FAIL" | "UNVALIDATED" | "NEEDS_REVIEW";
    failedScopes: string[];
    decisiveReasons: string[];
  };
}

interface ScopedQcResult {
  status: "PASS" | "FAIL" | "UNVALIDATED" | "NEEDS_REVIEW";
  validatorId: string;
  validatorConfigSha256: string;
  authorityRef: { id: string; sha256: string };
  report: ArtifactRef;
  measuredAt: string;
  scores: Record<string, number>;
  binaryGates: Array<{ id: string; passed: boolean; reason?: string }>;
}
```

Merge rule:

```text
if any scope is FAIL             => FAIL
else if any scope UNVALIDATED    => UNVALIDATED
else if any scope NEEDS_REVIEW   => NEEDS_REVIEW
else if all required scopes PASS => PASS
else                              => UNVALIDATED
```

No weighted average may convert a failed binary gate into a pass. A global validator invocation without an approved scenario authority binding is `UNVALIDATED`.

## 6. Backend and contract implementation

### 6.1 Files and modules to add or extend

The following names align with the current project structure; exact file partitioning may be optimized without breaking the listed contracts.

| Layer | Change |
|---|---|
| TypeScript contracts | Add `candidate-v3-types.ts`; extend `restoration-types.ts` with optional v3 request/result/evidence fields. Keep v1.0 reader compatibility. |
| Candidate registry | Add immutable profile, identity-pack, and scenario-authority registries under a server-only config path. |
| Job persistence | Extend `StudioRestorationAttemptRecord` / `StudioRestorationRecord` in `src/lib/studio/job-store.ts` additively. |
| API service | Extend `restoration-service.ts` to run preflight, resolve approved authority, call bridge, persist evidence, and transition existing stages. |
| Bridge | Add a versioned v3 JSON request to the existing bridge; validate request/output with schemas on both sides. |
| Python domain | Add `FaceObservabilityService`, `CanonicalizationService`, `IdentityPackSelector`, `BoundaryQcPort`, and `QualityBundleMerger` under domain/application boundaries. |
| Python adapter | Add `ComfyUiCandidateV3Adapter` and a v3 workflow; leave v2 adapter and workflow untouched. |
| Manifest | Add `manifest-1-4.ts`, pure/immutable transformation from 1.3. |
| API tests | Add contract, route, idempotency, redaction, and stage-transition tests. |

### 6.2 API surface

Keep the existing route family. Add fields only; do not accept client-controlled internal model parameters.

#### `POST /api/v1/studio/identity-restoration`

Request:

```json
{
  "baseArtifactId": "...",
  "scenarioId": "...",
  "candidateProfileId": "candidate-v3-sd15-faceid-canonical-512",
  "idempotencyKey": "client-unique-key"
}
```

Server behavior:

1. Authenticate/authorize the artifact and scenario.
2. Resolve base/mask artifacts on the server; never accept arbitrary filesystem paths from the browser.
3. Resolve the approved identity pack and scenario authority binding.
4. Run CPU preflight before reserving GPU.
5. If not `ELIGIBLE`, create a completed, auditable restoration attempt with route/evidence but do not call GPU. Return the route action.
6. For eligible input, create the existing job and execute v3 through the existing stage machine.

Response includes redacted candidate ID, route code, route reasons, job ID, and high-level evidence status. It excludes local paths, raw model IDs, authority internals, and sensitive reference images.

#### `GET /api/v1/studio/identity-restoration/:jobId`

Return the existing redacted job plus:

```json
{
  "restoration": {
    "candidateV3": {
      "route": { "code": "ELIGIBLE", "reasons": [] },
      "quality": { "merged": { "status": "NEEDS_REVIEW" } },
      "evidenceAvailability": {
        "faceLocal": true,
        "boundary": true,
        "scenarioGlobal": true
      }
    }
  }
}
```

#### `POST /api/v1/studio/identity-restoration/:jobId/action`

Permitted actions remain explicit:

- `APPROVE`: only available after all required gates pass and policy allows human approval.
- `REJECT`: records a reason and preserves evidence.
- `RETRY_FACE`: creates a new attempt under an approved named profile; it cannot accept an arbitrary denoise/reference override.
- `REQUEST_BASE_REGEN`: hands off to the existing base-image generation workflow with an explicit route reason; it is not a hidden fallback.

#### `POST /api/v1/studio/identity-restoration/:jobId/validate`

Re-validates only server-owned artifacts for the named attempt. It cannot accept browser paths or replace current authoritative QC with a non-authoritative result. It appends `qualityHistory` and updates current QC only under the established authority rule.

### 6.3 State machine

Use current job status and restoration stages. Add substages in evidence, not a parallel state model.

```text
QUEUED
  -> BASE_READY
  -> PREFLIGHT_COMPLETE
  -> CANONICAL_INPUT_READY
  -> GPU_RESTORING
  -> COMPOSITING
  -> VALIDATING_FACE
  -> VALIDATING_BOUNDARY
  -> VALIDATING_SCENARIO
  -> COMPLETED | FAILED | CANCELLED
```

For compatibility, the new labels may be represented as `restoration.evidence.phase` until `StudioRestorationStage` is deliberately expanded in one migration. A terminal job always has a precise final `RestorationResultStatus`.

## 7. Frontend behavior

The frontend is a review/control surface, not a model tuning panel.

1. **Candidate selector:** show approved profile names such as “Candidate v3 (canonical face restoration)”; hide raw model parameters.
2. **Preflight panel:** before GPU start, show route: eligible, review required, or base regeneration required; show simple reasons such as “face too small” or “multiple faces detected.”
3. **Evidence panel:** show candidate/version, selected pack version, transform verified, pixel lock, each QC scope, final route, and timestamp. Evidence links must use server authorization.
4. **Action controls:** disable approval on `FAIL`, `UNVALIDATED`, or `NEEDS_REVIEW`; retry creates a visible new attempt. Base regeneration requires an explicit confirmation/action.
5. **No misleading score:** do not render one aggregate percentage as “production ready.” Render binary gate status plus local Face-QC score where available.
6. **Redaction:** never display local paths, model/vendor identifiers, raw reference authority records, or hidden validator prompts.

## 8. Edge cases and defensive behavior

| Case | Required behavior | Prevention/test |
|---|---|---|
| No face, decode failure, unsupported image | `REJECTED_INVALID_INPUT`; no GPU call | Decode/schema unit tests; EXIF and alpha fixtures. |
| More than one face | `REVIEW_REQUIRED` unless a server-owned target mapping resolves exactly one face | Group-photo fixtures; assert no implicit largest-face selection. |
| Microface or low interocular distance | `BASE_REGEN_REQUIRED`; retain benchmark row and report it, never fake a repair | Locked B10-like fixtures; threshold calibration report. |
| Face clipped by frame | Review or regeneration based on missing landmarks | Border-face fixtures. |
| Extreme profile/occlusion/motion blur | Use approved matching reference only if observability policy permits; otherwise review/regenerate | Pose, glasses, hand, hair, blur fixtures. |
| Low-confidence or collinear landmarks | Reject canonical transform; no fallback affine warp | Singular-matrix and bad-landmark tests. |
| Non-square crop / out-of-bounds padding | Reflect-pad in model preprocessing, retain true canvas bounds | Boundary coordinate/property tests. |
| Mask geometry mismatch | Fail before restore; mask and transform hash must match | Altered-mask negative tests. |
| Inverse warp changes unmasked pixels | Hard fail `PIXEL_LOCK_FAILED` | Pixel-diff fixture and property tests. |
| Seam or color discontinuity | Boundary QC fails or review; never accept based solely on face score | Synthetic seam/color-shift fixtures. |
| Missing/retired identity pack or scenario profile | `UNVALIDATED`; no production approval | Registry validation at startup and request time. |
| Reference hash changed after approval | Fail safe; do not load reference | Hash verification test. |
| Workflow title missing/duplicated or workflow hash differs | Adapter fails before GPU prompt | Graph semantic-binding tests. |
| GPU OOM / worker unreachable / timeout | `FAILED` with retryable code where appropriate; release lease and preserve diagnostics | 6 GB memory budget test/mocked worker failures. |
| Cancel during restore | Finish/abort according to existing cancel contract; never mark a partial result approved | Cancel race integration tests. |
| Server restart | Existing orphan reconciliation marks terminal failure; manifest never claims completion | Restart/orphan test. |
| Duplicate API retry | Return original idempotent job; do not spend/re-run | Concurrent replay test. |
| QC provider timeout or non-authoritative result | `UNVALIDATED` or `NEEDS_REVIEW`, never pass | Provider failure tests. |
| Scenario rule incorrectly excludes a real face defect | Exclusions are scoped by validator/category and approved by human; face-local and boundary gates remain non-excludable | Scope-leak regression tests. |
| Candidate output byte-identical to input | Fail as no effective restoration unless explicit no-op policy exists and is separately evaluated | Existing no-op invariant retained. |
| Model license/provenance missing | Candidate cannot be marked production eligible | Release checklist gate. |

## 9. Security, privacy, and release controls

- Identity references and generated face artifacts are sensitive project assets. Store paths server-side, authorize access, and do not expose absolute file paths or reference metadata in browser responses.
- Hash every reference, workflow, model identifier list, prompt/config artifact, QC report, and composite. Hash alone is not authorization; access control remains mandatory.
- The active FaceID stack’s model provenance/commercial-use evidence must be recorded before production promotion. If the selected dependency is not licensed for the intended use, replace it or obtain the required license before release. This is a release gate, not a runtime warning.
- Candidate v3 starts disabled behind a server-side feature flag. It is opt-in for test runs only until formal promotion.
- No automatic score-based promotion, no threshold reduction, and no deletion of failed attempts.

## 10. Sequential implementation plan

### Phase 0 — Freeze and contract baseline

**Goal:** establish reproducibility before modifying behavior.

1. Freeze current v2 workflow/artifact hashes and export the locked B01–B10 benchmark manifest.
2. Record current candidate results without overwriting historical reports.
3. Define JSON schemas for identity pack, authority binding, v3 request/result, transform, and quality bundle.
4. Add schema validation to both TypeScript and Python bridge edges.
5. Create the v3 feature flag disabled by default.

**Exit criteria:** v2 tests remain green; malformed v3 JSON is rejected on both sides; no v3 route is reachable when feature flag is off.

### Phase 1 — Authority data and registry

**Goal:** create trusted inputs before GPU work.

1. Create and human-approve `IdentityPackV1` with A2 frontal plus approved 3/4 and profile references.
2. Create one `ScenarioAuthorityBindingV1` for every benchmark and production scenario. Do not auto-map by scenario name.
3. Add startup and request-time registry checks: uniqueness, hashes, one primary, approved status, no retired references.
4. Add an authority audit view/report listing unmatched scenarios.

**Exit criteria:** every locked benchmark row resolves exactly one approved scenario binding; all selected references hash-verify.

### Phase 2 — CPU-only preflight and canonicalization

**Goal:** eliminate unrepairable input and define exact geometry.

1. Implement `FaceObservabilityService` with pinned detector/version and measurement config.
2. Implement route policy and serialize route reasons.
3. Implement landmark canonicalization, mask transformation, inverse transform, and round-trip verifier.
4. Add fixture tests for microface, multiple faces, border face, profile, blur, invalid landmarks, and EXIF orientation.
5. Calibrate thresholds on a fixed labelled dataset. Version and hash the policy; do not tune using only passing examples.

**Exit criteria:** no GPU dependency for this phase; all coordinate/mask property tests pass; B10-like fixture deterministically routes rather than proceeds as normal restoration.

### Phase 3 — Candidate v3 workflow adapter

**Goal:** run a pinned model-space restoration while preserving the current architecture.

1. Duplicate the workflow into a new v3 file and add mandatory semantic titles.
2. Implement `ComfyUiCandidateV3Adapter` behind `RestorerRegistry` with a distinct `restorerId`/candidate profile.
3. Bind only declared v3 inputs; verify graph title/type/cardinality before queueing.
4. Require 512×512 canonical images/masks; emit restored canonical image at the same geometry.
5. Return workflow hash, bound config, selected reference hashes, model identifiers, GPU evidence, and timing.
6. Keep v2 untouched and available for regression comparison.

**Exit criteria:** graph-binding contract tests pass; health/lease/cancel/OOM behavior is unchanged; a valid fixture can execute only when explicitly authorized to use GPU.

### Phase 4 — Composite and split QC

**Goal:** make correctness and quality independently explainable.

1. Implement inverse composite using `CanonicalFaceTransform` only.
2. Retain hard pixel lock and add seam/boundary evaluator.
3. Extend face QC to consume canonical crop plus selected pack references.
4. Extend global QC to require explicit scenario authority binding.
5. Implement `QualityBundleMerger` with fail-closed semantics.
6. Write immutable QC reports and Manifest 1.4 enrichment.

**Exit criteria:** synthetic seam, altered-mask, missing-profile, and failed-face tests cannot end in `PASS`; quality history remains append-only.

### Phase 5 — Service, bridge, and API integration

**Goal:** connect v3 without creating duplicated operational state.

1. Extend restoration service: resolve authority → preflight → canonicalize → bridge → composite → split QC → manifest → job transition.
2. Extend bridge contracts and output validation.
3. Extend existing job records additively with v3 evidence.
4. Implement idempotency fingerprint and atomic job/manifest handling.
5. Add API authorization, redaction, route responses, and controlled actions.

**Exit criteria:** end-to-end mocked integration test covers eligible, microface, validation failure, cancellation, duplicate retry, and orphaned job paths.

### Phase 6 — Frontend integration

**Goal:** make the operational decision understandable and safe.

1. Add profile selector, preflight status, scope-separated QC evidence, and controlled action states.
2. Ensure non-pass states cannot render an approval affordance.
3. Render base-regeneration route explicitly, never as an automatic retry.
4. Validate that all client payloads contain IDs only, not paths/config values.

**Exit criteria:** UI integration tests verify redaction, disabled approval, and retry/new-attempt behavior.

### Phase 7 — Technical validation and candidate evaluation

**Goal:** prove behavior before production consideration.

1. Run deterministic CPU/unit/contract tests first.
2. Run a small locked diagnostic set including B05, B06, B10 and known scope-sensitive action cases.
3. Inspect artifacts manually: selected reference, canonical transform, mask, restored crop, inverse composite, pixel diff, three QC reports.
4. Run complete B01–B10 benchmark with every row retained and no case substitution.
5. Compare v3 against frozen v2 using the same authorities where valid; report score distributions and fail reasons by scope.
6. Run adverse tests: missing pack, mismatched hash, stale scenario profile, GPU OOM, worker timeout, and concurrent retry.

**Exit criteria:** all promotion predicates in Section 1 are satisfied. If not, v3 remains non-production and the report identifies the failing route/cause; no score threshold is adjusted post hoc.

### Phase 8 — Controlled rollout and rollback

1. Enable v3 for a bounded, logged internal cohort only.
2. Require human approval per output during the pilot.
3. Monitor route distribution, GPU failures, QC scope failures, retries, and pixel-lock incidents.
4. Promote only through a release record that includes model license/provenance evidence and benchmark evidence.
5. Roll back by disabling the v3 feature flag. Preserve all jobs, manifests, and failed candidate evidence.

## 11. Test matrix

| Test class | Required assertions |
|---|---|
| Unit/domain | Policy precedence, pose selection, config hashing, transform inversion, mask intersection, quality merge. |
| Property/geometry | Random valid crop bounds round-trip within tolerance; transformed masks remain bounded; external pixels never change. |
| Contract | TS/Python schemas reject unknown/missing critical fields; historical v1.0 result reader remains functional. |
| Adapter | Semantic node title uniqueness/type match; 512 geometry contract; output size and workflow hash verified. |
| Integration | Existing route/job stages, idempotency, cancel, orphan recovery, manifest atomicity, redaction. |
| QC regression | Scope errors cannot be hidden by global average; exclusions cannot waive face-local/boundary failures. |
| GPU smoke | One approved fixture only; VRAM peak, worker health, timeout, and cleanup recorded. |
| Benchmark | All locked B01–B10 rows, including difficult/microface route outcomes, reported without row removal. |
| Security/release | Unauthorized artifact access denied; no absolute paths/model IDs in client JSON; license/provenance release gate blocks promotion. |

## 12. Acceptance criteria and handoff contract

An implementation is complete only when all statements below are true:

1. Candidate v3 is a distinct profile, workflow, and effective-config hash; v2 artifacts/workflow are unchanged.
2. Every v3 attempt stores observability, route, selected approved references, canonical transform, artifact hashes, pixel lock, three scoped QC reports, and final merged status.
3. No eligible attempt sends a native arbitrary-size crop to the restoration model; the model receives a verified 512×512 canonical input.
4. An unrecoverable small/occluded face does not consume GPU and does not receive an artificial `PASS`; it is routed and audited.
5. Global scenario validation cannot run without an approved binding; face-local and boundary validation cannot be waived by scenario exclusions.
6. No output with missing evidence, failed pixel lock, failed binary QC gate, unknown authority, or missing license/provenance can be approved or promoted.
7. Existing job store, idempotency behavior, redaction, and restore bridge remain the single operational path.
8. The complete locked benchmark has been run with every row retained, and the promotion record contains immutable evidence.

### Explicit non-goals

- Buying or requiring a new GPU as a prerequisite for v3.
- Recovering reliable identity from a face that has insufficient source pixels.
- Auto-generating identity references or authority exemptions.
- Adding user-facing sliders for denoise, references, workflow nodes, or validator rules.
- Treating a Face-QC score above 90 as the sole definition of production quality.

### Implementation order for a successor AI

Implement in this exact dependency order:

```text
schemas/registries
  -> preflight + canonical transform + tests
  -> v3 adapter/workflow binding + tests
  -> inverse composite + split QC + Manifest 1.4
  -> service/bridge/job integration
  -> API + frontend evidence/actions
  -> locked benchmark + release gate
```

Do not start parameter tuning or benchmark reruns before Phases 1–4 are complete. Otherwise the team will be measuring a model against unstable input geometry and unstable authority, which cannot yield a defensible production decision.

## References used as technical evidence

- `GW_P7_CANDIDATE_QUALITY_RESEARCH_REPORT_2026-08-27.md`
- `VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`
- `VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md`
- `task_memory.md`
- `task_status.md`

The design also follows the project’s existing Hotel DNA / Linh An identity-manifest and validator contract: authority is explicit, outputs are reproducible, and validation evidence must be retained.

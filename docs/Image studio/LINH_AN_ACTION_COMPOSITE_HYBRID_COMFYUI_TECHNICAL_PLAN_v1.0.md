# LINH AN ACTION-COMPOSITE HYBRID PIPELINE
## Nano Banana + ComfyUI Local
### Technical Implementation Plan for Face Identity >90

**Document purpose:**  
Thiết kế lại pipeline `action-composite` cho KOL Linh An nhằm vượt và duy trì ổn định Face Identity QC > 90 trong các ảnh có độ phức tạp cao: chạy/chuyển động, trang phục cụ thể, bối cảnh Hồ Tây, full-body hoặc medium-wide composition.

**Primary optimization target:**  
Giảm identity drift khi một model phải đồng thời xử lý quá nhiều ràng buộc trong một lần generate.

**Recommended architecture:**  
`Nano Banana = Creative / Scene / Action Generator`  
`ComfyUI Local = Precision Identity Finisher`

---

# 1. Problem Statement

Nano Banana hiện có thể đạt Face Identity >90 với:

- close-up;
- bố cục đơn giản;
- ít constraint;
- A2-front là face reference chính.

Tuy nhiên độ ổn định giảm rõ rệt khi cùng lúc phải giữ:

- Face A2;
- running pose / action pose;
- body anatomy;
- Nike outfit hoặc wardrobe cụ thể;
- Hồ Tây / Ven Hồ Hotel environment;
- hair;
- camera composition;
- lighting;
- photorealism.

Đây không nên được xem đơn thuần là lỗi prompt.

Vấn đề cốt lõi là **action-composite overload**: một generation pass đang phải giải đồng thời quá nhiều constraint có mức ưu tiên cạnh tranh nhau.

---

# 2. Architectural Decision

Không tiếp tục ép một image-generation call xử lý toàn bộ:

```text
Identity
+ Pose
+ Anatomy
+ Outfit
+ Hair
+ Environment
+ Lighting
+ Composition
+ Detail
```

Thay vào đó chuyển `action-composite` từ một image action sang một **orchestration workflow**.

Kiến trúc mục tiêu:

```text
A2 Identity Authority
        │
        ▼
[1] Scene / Action Generation
        │
        ▼
[2] Geometry Analysis + Lock
        │
        ▼
[3] Face Identity Restoration
        │
        ▼
[4] Local Blend / Harmonization
        │
        ▼
[5] Regional QC
        │
        ▼
[6] Selective Repair
        │
        ▼
      FINAL
```

---

# 3. Role Separation

## 3.1 Nano Banana

Nano Banana chịu trách nhiệm chính cho:

- Hồ Tây / environment;
- camera composition;
- running pose;
- body motion;
- body proportions;
- wardrobe;
- lighting;
- scene consistency;
- photorealistic rendering;
- global image aesthetics.

Nano Banana **không còn là identity authority cuối cùng** trong action-composite.

---

## 3.2 ComfyUI Local

ComfyUI chịu trách nhiệm:

- face detection;
- face crop;
- landmark extraction;
- face mask;
- mask feathering;
- A2 identity conditioning;
- face inpainting;
- localized face restoration;
- detail refinement;
- skin/light harmonization;
- face-to-hair blending;
- jaw-to-neck blending;
- localized retries;
- optional local QC.

---

# 4. Identity Authority Rules

## 4.1 Single Identity Authority

Chỉ sử dụng:

```text
A2-FRONT
```

làm **Identity Authority**.

Không gửi đồng thời:

- A2-front;
- Candidate 93.15;
- B3;
- nhiều face reference khác;

trong cùng identity conditioning pass nếu không có lý do kỹ thuật rõ ràng.

Mục tiêu là tránh:

```text
identity averaging
reference conflict
feature interpolation
face drift
```

Candidate đạt điểm cao chỉ nên dùng:

- benchmark;
- QC comparison;
- internal reference;
- regression test.

Không dùng làm đồng-authority mặc định.

---

# 5. Hybrid Production Workflow

## STEP 1 — Generate Action Candidate

Input:

```text
A2 reference
Pose instruction
Wardrobe specification
Environment specification
Camera specification
Lighting specification
```

Nano Banana tạo:

```text
3 candidates
```

khuyến nghị ở 2K để cân bằng:

- chất lượng;
- chi phí;
- downstream face crop resolution.

### Important

Ở bước này:

```text
Face accuracy = important but not absolute
Pose/anatomy/outfit/environment = primary
```

Không retry quá nhiều chỉ vì face chưa >90.

---

# 6. Candidate Selection

Chọn candidate dựa trên:

```text
Pose
Anatomy
Body proportions
Outfit
Environment
Composition
Lighting
Hair compatibility
Head pose compatibility
```

Không dùng Face Score làm yếu tố duy nhất.

Ví dụ:

```text
Candidate A
Face: 88.7
Pose: Excellent
Outfit: Excellent
Scene: Excellent

Candidate B
Face: 90.2
Pose: Weak
Anatomy: Weak
Scene: Average
```

Nên chọn:

```text
Candidate A
```

vì face có thể được repair local.

---

# 7. Geometry Lock Layer

Đây là layer quan trọng cần bổ sung.

Trước face restoration, hệ thống cần xác định:

```text
face_bbox
head_bbox
face_landmarks
yaw
pitch
roll
face_scale
eye_line
nose_axis
mouth_line
jaw_contour
hairline_boundary
neck_boundary
```

Mục tiêu:

Face repair phải giữ nguyên:

```text
head size
head orientation
face position
neck attachment
hairline
camera perspective
```

---

# 8. Lock Types

Pipeline cần ít nhất 4 lock.

## 8.1 Identity Lock

```text
Identity Authority = A2-front
```

---

## 8.2 Geometry Lock

Không cho face repair thay đổi đáng kể:

```text
head position
head size
head pose
jaw placement
eye line
face perspective
```

---

## 8.3 Pixel Preservation Lock

Pixel ngoài repair mask:

```text
must remain unchanged
```

hoặc chỉ cho phép:

```text
very small tolerance
```

Không regenerate lại:

- body;
- clothes;
- hands;
- Hồ Tây;
- architecture;
- sky;
- background.

---

## 8.4 Semantic Lock

Trong face repair stage:

```text
pose = locked
wardrobe = locked
environment = locked
hair style = locked
camera = locked
```

Model không được reinterpret scene.

---

# 9. Face Crop Strategy

Face trong full-body/action image thường quá nhỏ.

Nếu face chiếm ít pixel:

```text
eyes
nose
mouth
jaw
skin texture
```

sẽ không đủ dữ liệu để restoration chính xác.

Do đó:

```text
detect face
→ crop
→ upscale crop
→ repair face at higher effective resolution
→ composite back
```

Recommended concept:

```text
ACTION IMAGE
      │
      ▼
 Face Detect
      │
      ▼
 High-res Crop
      │
      ▼
 Identity Repair
      │
      ▼
 Local Blend
      │
      ▼
 Composite Back
```

---

# 10. Mask Hierarchy

Không nên ngay lập tức mask toàn bộ đầu.

Khuyến nghị hierarchical repair.

## PASS B1 — Core Features

Mask:

```text
eyes
eyebrows
nose
lips
central facial plane
```

Mục tiêu:

```text
identity structure first
```

---

## PASS B2 — Face Shape

Mask:

```text
cheeks
jaw
chin
outer facial contour
```

Mục tiêu:

```text
A2 facial geometry refinement
```

---

## PASS B3 — Boundary Repair

Chỉ chạy nếu cần:

```text
hairline
temples
ears
jaw-neck transition
```

Mục tiêu:

```text
blend consistency
```

---

# 11. Mask Feathering

Hard-edge face replacement dễ tạo:

```text
cutout face
halo
skin discontinuity
lighting discontinuity
jaw seam
```

Do đó cần:

```text
soft mask
feather
controlled expansion
boundary blending
```

Mask không nên rộng quá mức.

---

# 12. Face Conditioning Options in ComfyUI

Có thể thử nghiệm:

```text
IP-Adapter / FaceID
InstantID
identity-aware inpainting workflow
face detailer
custom face embedding workflow
```

Không lock implementation ngay từ đầu.

Codex nên xây abstraction:

```text
IdentityConditioningProvider
```

Ví dụ:

```text
IPAdapterProvider
InstantIDProvider
FutureFaceProvider
```

để không phụ thuộc một node ecosystem duy nhất.

---

# 13. Provider Abstraction

Recommended interface concept:

```text
interface IdentityRestorer {
    restore(
        baseImage,
        identityReference,
        faceMask,
        geometry,
        config
    ) -> RestoredImage
}
```

Implementation examples:

```text
ComfyUIIPAdapterRestorer
ComfyUIInstantIDRestorer
CloudFaceEditRestorer
```

---

# 14. Regional Validator Architecture

Không dùng một global Face Score duy nhất.

Validation cần chia theo vùng.

```text
Face Validator
Anatomy Validator
Wardrobe Validator
Environment Validator
Composition Validator
Global Composite Validator
```

---

# 15. Recommended QC Gates

## 15.1 Identity Crop QC

```text
Face Identity >= 90
```

đây là gate chính.

---

## 15.2 Facial Geometry QC

Recommended target:

```text
>= 92
```

hoặc PASS theo tolerance.

---

## 15.3 Anatomy QC

```text
PASS / FAIL
```

Kiểm tra:

- hands;
- arms;
- legs;
- joint bending;
- foot orientation;
- limb count;
- body balance.

---

## 15.4 Outfit QC

```text
PASS / FAIL
```

Kiểm tra:

- garment identity;
- color;
- shape;
- logo placement nếu cần;
- fabric consistency;
- no clothing mutation.

---

## 15.5 Environment QC

```text
PASS / FAIL
```

Đối với Hồ Tây:

- correct railing;
- shoreline;
- tree canopy;
- lake proportion;
- skyline;
- authentic Nguyễn Đình Thi context.

---

## 15.6 Global Composite QC

Kiểm tra:

```text
face-body harmony
skin-light consistency
head-body ratio
hair transition
neck transition
photorealism
```

---

# 16. Important QC Rule

Không dùng full-frame face similarity làm gate chính khi face nhỏ.

Ví dụ:

```text
Face crop score = 92
Full image identity estimate = 87
```

Nếu nguyên nhân là:

```text
small face size
```

thì không được kết luận:

```text
identity FAIL
```

Identity phải được đánh giá trên normalized crop.

---

# 17. Selective Repair Controller

Đây là thành phần quan trọng nhất của Action Composite v2.

Pseudo logic:

```text
if face_qc < 90:
    repair(face_region_only)

if facial_geometry_fail:
    repair(face_geometry_region_only)

if anatomy_fail:
    repair(failed_limb_only)

if outfit_fail:
    repair(clothing_region_only)

if environment_fail:
    repair(environment_region_only)

if composite_blend_fail:
    repair(boundary_region_only)
```

Không quay lại regenerate toàn bộ image nếu không cần.

---

# 18. Anti-Regression Rule

Sau mỗi repair:

```text
revalidate repaired region
+
regression-check locked regions
```

Ví dụ:

```text
Face repaired successfully
```

nhưng:

```text
hair changed
neck changed
Nike top changed
```

=> reject repair.

---

# 19. Action-Composite v2 Components

Recommended module tree:

```text
ACTION_COMPOSITE_V2
│
├── SceneComposer
│
├── ActionComposer
│
├── CandidateSelector
│
├── GeometryAnalyzer
│
├── GeometryLocker
│
├── FaceCropper
│
├── IdentityRestorer
│
├── MaskManager
│
├── LocalBlender
│
├── RegionalValidator
│
├── SelectiveRepairController
│
├── RegressionGuard
│
└── OutputFinalizer
```

---

# 20. State Machine

Recommended:

```text
INIT
 ↓
GENERATE_ACTION
 ↓
SELECT_CANDIDATE
 ↓
ANALYZE_GEOMETRY
 ↓
RESTORE_FACE
 ↓
VALIDATE_FACE
 ├── FAIL → REPAIR_FACE
 └── PASS
       ↓
VALIDATE_GLOBAL
 ├── FAIL → SELECTIVE_REPAIR
 └── PASS
       ↓
FINALIZE
```

---

# 21. Retry Policy

Không retry vô hạn.

Recommended:

```text
MAX_SCENE_GENERATION = 3
MAX_FACE_REPAIR = 5
MAX_BOUNDARY_REPAIR = 3
MAX_REGION_REPAIR = 3
```

Nếu Face QC không cải thiện sau:

```text
N retries
```

thì:

```text
stop
switch restoration strategy
```

Ví dụ:

```text
IP-Adapter → InstantID
```

thay vì tiếp tục brute-force cùng một workflow.

---

# 22. Score Improvement Tracking

Mỗi repair iteration nên lưu:

```text
iteration
provider
workflow_version
seed
identity_score
geometry_score
global_score
mask_version
parameters
```

Ví dụ:

```json
{
  "iteration": 3,
  "identity_score": 91.4,
  "geometry_score": 93.1,
  "workflow": "face_restore_v2",
  "provider": "comfyui_ipadapter",
  "mask": "core_face_v3"
}
```

---

# 23. Stop Condition

Không tiếp tục repair khi:

```text
Identity >= 90
AND
Geometry PASS
AND
Anatomy PASS
AND
Outfit PASS
AND
Environment PASS
AND
Global Composite PASS
```

---

# 24. Cost Architecture

Hybrid pipeline chuyển chi phí từ:

```text
Repeated Cloud Regeneration
```

sang:

```text
Limited Cloud Generation
+
Local Iteration
```

---

# 25. Recommended Cloud Usage

Per production image:

```text
Nano Banana
1–3 initial generations
```

Sau khi chọn base:

```text
stop cloud regeneration
```

trừ khi scene/action thực sự fail.

---

# 26. Local Cost Model

ComfyUI local:

```text
API cost ≈ 0
```

Chi phí còn lại:

- hardware;
- electricity;
- storage;
- maintenance;
- model download/storage;
- engineering time.

Do đó:

```text
Face repair ×3
Face repair ×5
Face repair ×10
```

không làm tăng trực tiếp API bill nếu toàn bộ local.

---

# 27. Hybrid Cost Advantage

Cloud-only pattern:

```text
generate
face fail
regenerate
outfit fail
regenerate
face fail
regenerate
...
```

Hybrid pattern:

```text
generate 1–3 strong base candidates
             ↓
        freeze scene
             ↓
       local convergence
```

Lợi ích:

```text
lower marginal retry cost
lower scene regression
lower wardrobe regression
better reproducibility
```

---

# 28. Hardware Strategy

Phase đầu:

```text
use existing local hardware
```

để validate pipeline.

Nếu workload tăng hoặc latency không phù hợp:

```text
move ComfyUI worker to NVIDIA GPU machine
```

Không nên mua GPU trước khi xác nhận:

```text
Face QC uplift
workflow stability
production throughput
```

---

# 29. Recommended Deployment Topology

```text
VENHO AI STUDIO
      │
      ▼
Action Composite Orchestrator
      │
      ├── Nano Banana API
      │
      └── ComfyUI Local API
                 │
                 ▼
           Local GPU Worker
```

---

# 30. ComfyUI as Service

Không nên phụ thuộc thao tác UI thủ công trong production.

ComfyUI nên được coi là:

```text
local inference service
```

Orchestrator gửi:

```text
workflow JSON
image
mask
A2 reference
parameters
```

và nhận:

```text
result image
metadata
```

---

# 31. Workflow Versioning

Mỗi ComfyUI workflow phải có version:

```text
face_restore_v1
face_restore_v2
face_restore_v3
```

Không overwrite workflow production mà không version.

---

# 32. Reproducibility

Lưu:

```text
seed
model
model hash/version
workflow version
node versions
strength
CFG
steps
sampler
denoise
mask parameters
identity weight
```

Nếu không lưu, QC benchmark sẽ không đáng tin cậy.

---

# 33. Recommended Data Structure

Example job:

```json
{
  "job_id": "linhan_action_0001",
  "identity": {
    "authority": "A2_FRONT"
  },
  "scene": {
    "provider": "nano_banana",
    "candidate_id": "candidate_02"
  },
  "geometry": {
    "face_bbox": [],
    "yaw": 0,
    "pitch": 0,
    "roll": 0
  },
  "restoration": {
    "provider": "comfyui",
    "workflow": "face_restore_v2"
  },
  "qc": {
    "identity": 0,
    "geometry": 0,
    "anatomy": "pending",
    "outfit": "pending",
    "environment": "pending"
  }
}
```

---

# 34. Failure Modes

## 34.1 Identity Averaging

Cause:

```text
too many face references
```

Fix:

```text
single A2 authority
```

---

## 34.2 Face Looks Correct but Head Wrong

Cause:

```text
no geometry lock
```

Fix:

```text
bbox + landmark + head pose preservation
```

---

## 34.3 Face Cutout Effect

Cause:

```text
hard mask
poor skin/light blending
```

Fix:

```text
feather mask
boundary pass
color/light harmonization
```

---

## 34.4 Hair Mutation

Cause:

```text
mask too large
semantic freedom too high
```

Fix:

```text
exclude hair from main face mask
repair hairline separately
```

---

## 34.5 Neck/Jaw Seam

Fix:

```text
dedicated boundary pass
```

---

## 34.6 Face Detail Good but Identity Low

Possible causes:

```text
wrong face geometry
wrong eye spacing
wrong jaw
wrong nose ratio
beautification drift
```

Do not simply increase sharpness.

---

## 34.7 Over-Beautification

Avoid:

```text
generic Korean face
symmetry correction
jaw narrowing
eye enlargement
nose beautification
skin plasticization
```

Identity fidelity has priority over beauty normalization.

---

# 35. Linh An Identity Preservation Rules

Preserve:

```text
natural asymmetry
soft elongated oval face
slightly fuller cheeks
warm brown almond eyes
horizontal eye emphasis
low soft brows
slim natural nose bridge
upper lip thinner than lower lip
soft feminine jawline
realistic skin pores
```

Do not allow generic model beautification to replace these traits.

---

# 36. Benchmark Dataset

Create standardized benchmark set:

```text
B01 Close-up Front
B02 Half-body
B03 Full-body Standing
B04 Running Front 3/4
B05 Running Side
B06 Walking
B07 Sitting
B08 Hair Motion
B09 West Lake
B10 Ven Ho Hotel Interior
```

Every Action Composite release must run regression against this set.

---

# 37. Acceptance Criteria for Action Composite v2

Minimum:

```text
Close-up identity success >= 95%
Action identity success >= 80%
Median Face QC >= 90
No major anatomy regression
No locked-region mutation
```

Later production target:

```text
Action identity success >= 90%
```

---

# 38. Phase 1 — Proof of Concept

Goal:

Verify that ComfyUI restoration can improve action face from approximately:

```text
87–89
```

to:

```text
>=90
```

without damaging body/background.

Tasks:

```text
1. Install ComfyUI
2. Select base model
3. Install identity conditioning workflow
4. Build face mask pipeline
5. Run A2 reference
6. Test 10 action images
7. Compare before/after Face QC
```

Do not build full orchestration yet.

---

# 39. Phase 2 — Geometry Lock

Implement:

```text
face detection
landmarks
head pose
bbox
mask auto-generation
crop normalization
```

Goal:

reduce geometry drift.

---

# 40. Phase 3 — Automated Restoration

Build:

```text
Action image
→ auto face detect
→ crop
→ mask
→ ComfyUI API
→ composite
→ QC
```

No manual ComfyUI interaction.

---

# 41. Phase 4 — Selective Repair

Add:

```text
Face repair
Anatomy repair
Wardrobe repair
Environment repair
Boundary repair
```

Each independently addressable.

---

# 42. Phase 5 — QC Feedback Loop

```text
Generate
→ Validate
→ Identify failed region
→ Repair only that region
→ Revalidate
```

---

# 43. Phase 6 — Production Integration

Integrate into:

```text
VENHO AI Studio
```

as:

```text
Action Composite v2
```

Possible UI states:

```text
Generating Scene
Selecting Candidate
Locking Geometry
Restoring Identity
Validating Face
Repairing Region
Finalizing
```

---

# 44. Recommended Implementation Priority

Priority P0:

```text
ComfyUI local POC
A2 single authority
face crop
mask
identity restoration
Face QC before/after
```

Priority P1:

```text
geometry lock
automatic mask
workflow API
metadata
```

Priority P2:

```text
regional validator
selective repair
regression guard
```

Priority P3:

```text
full orchestration
dashboard
analytics
cost tracking
```

---

# 45. Codex Optimization Tasks

Codex should review and improve:

## Architecture

- module boundaries;
- interfaces;
- dependency inversion;
- provider abstraction;
- Clean Architecture alignment.

## Workflow

- state machine;
- retry logic;
- idempotency;
- failure recovery;
- cancellation;
- resumability.

## Data

- job schema;
- QC schema;
- workflow metadata;
- reproducibility metadata;
- audit trail.

## Performance

- local GPU memory;
- crop resolution;
- batching;
- cache;
- model warm loading.

## Reliability

- node failure;
- ComfyUI unavailable;
- corrupt output;
- model mismatch;
- incompatible node version.

## Cost

- cloud generation cap;
- retry cap;
- local compute accounting;
- cost-per-approved-image.

---

# 46. Recommended Clean Architecture Layers

```text
domain/
├── entities
├── value_objects
├── qc_rules
└── policies

application/
├── generate_action
├── restore_identity
├── validate_image
├── selective_repair
└── finalize_asset

ports/
├── image_generator
├── identity_restorer
├── validator
├── geometry_analyzer
└── artifact_store

infrastructure/
├── nano_banana
├── comfyui
├── face_detector
├── local_qc
└── storage

interface/
├── api
├── worker
├── cli
└── dashboard
```

---

# 47. Core Principle

Do not solve the identity problem by repeatedly regenerating the whole image.

The new principle is:

```text
Generate globally.
Lock geometry.
Repair locally.
Validate regionally.
Retry selectively.
```

---

# 48. Final Recommended Pipeline

```text
A2 FRONT
   │
   │ Identity Authority
   ▼
NANO BANANA
   │
   │ Scene + Action + Body + Outfit + Environment
   ▼
BASE CANDIDATES
   │
   ▼
CANDIDATE SELECTOR
   │
   ▼
GEOMETRY ANALYZER
   │
   ├── face bbox
   ├── landmarks
   └── head pose
   │
   ▼
FACE CROP + MASK
   │
   ▼
COMFYUI LOCAL
   │
   ├── identity conditioning
   ├── face inpainting
   ├── detail refinement
   └── boundary blending
   │
   ▼
REGIONAL QC
   │
   ├── Identity >= 90?
   ├── Geometry PASS?
   ├── Anatomy PASS?
   ├── Outfit PASS?
   └── Environment PASS?
   │
   ├── FAIL → SELECTIVE REPAIR
   │
   └── PASS
          ▼
      FINAL IMAGE
```

---

# 49. Final Decision

Recommended production direction:

```text
Nano Banana
=
Creative Generator

ComfyUI Local
=
Precision Identity Finisher

VENHO AI Studio
=
Orchestrator + Validator
```

This architecture is preferred over:

```text
single-pass action composite
```

because it provides:

- better identity stability;
- lower marginal retry cost;
- better reproducibility;
- lower regression risk;
- provider independence;
- better QC observability;
- easier future upgrades.

---

# 50. Definition of Done for Initial POC

POC is considered successful when:

```text
1. Input = Nano Banana action image + A2-front
2. Face is automatically detected
3. Face crop is normalized
4. Face mask is generated
5. ComfyUI restores identity
6. Pixels outside face region remain effectively unchanged
7. Face QC improves versus original
8. At least several action samples cross >=90
9. Result remains photorealistic
10. Workflow can be called programmatically
```

Only after this POC passes should the system proceed to full Action Composite v2 integration.

---

**Recommended filename:**

`LINH_AN_ACTION_COMPOSITE_HYBRID_COMFYUI_TECHNICAL_PLAN_v1.0.md`

---

# Implementation Status — 2026-08-12

## Phase 1 — Proof of Concept (local vertical slice)

- [x] Create Action Composite v2 package under `image_studio_runtime/action_composite`.
- [x] Enforce `A2_FRONT` as the single identity authority at the job boundary.
- [x] Add geometry lock model with face/head bounding boxes and pose fields.
- [x] Add normalized face crop and feathered mask generation.
- [x] Add `IdentityRestorer` provider port and programmatic ComfyUI HTTP adapter.
- [x] Composite only inside the face mask and verify pixel preservation outside it.
      *(Corrected in P7 — as first written this gate was inert; see below.)*
- [x] Emit immutable `image.png` and `manifest.json` artifacts for each run.
- [x] Add regional QC result with identity threshold and pixel-preservation gate.
- [x] Add automated POC tests; targeted suite passes 9/9.
- [x] Add environment-driven ComfyUI endpoint/workflow configuration and health-check adapter.
- [x] Enforce immutable geometry lock metadata and pose/bounding-box regression checks.
- [x] Persist workflow reproducibility metadata (seed, model, node versions, parameters, mask settings).
- [x] Install ComfyUI 0.32.0 in `/Users/hanhpham/ComfyUI` with a Python 3.12 virtualenv.
- [x] Validate ComfyUI dependencies and CPU smoke-test startup (`--quick-test-for-ci`).
- [ ] Install/configure the selected identity-conditioning workflow and model files.
- [ ] Run the A2 benchmark against 10 real action images and record before/after Face QC.

The unchecked items require a configured local ComfyUI service, model files, and benchmark images; no paid or live image generation was executed in this implementation step.

## P2 — Regional QC and repair hardening

- [x] Add independent regional validators (identity, facial geometry, outfit/environment informational regions) with `PASS`/`FAIL`/`UNVALIDATED` states.
- [x] Add selective repair controller that routes only failed regions and enforces retry caps (face 5, boundary 3, region 3, scene 3 by default).
- [x] Add regression guard that rejects any pixel mutation outside the active repair mask.
- [x] Add P2 unit tests for isolated identity gating, missing-score handling, retry caps, and outside-mask regression detection.

## P3 — Orchestration, auditability and cost tracking

- [x] Extend the composite state machine for action generation, candidate selection, global validation and selective repair.
- [x] Add immutable iteration audit records with provider, workflow, seed, scores, mask version and parameters.
- [x] Add production stop-condition evaluation requiring identity, geometry, anatomy, outfit, environment and global gates.
- [x] Add idempotency key store for safe job resumption and duplicate-request suppression.
- [x] Add retry policy enforcement and provider-neutral local/cloud cost ledger.
- [x] Add P3 tests; targeted Action Composite suite passes 12/12.

## P4 — Production integration foundations

- [x] Add versioned ComfyUI workflow registry with reproducibility hash validation.
- [x] Add durable atomic JSON audit store for resumable job records.
- [x] Add analytics aggregation for approval rate, state counts and compute cost.
- [x] Add P4 integration tests; targeted Action Composite suite passes 14/14.

## P5 — Service and worker integration contract

- [x] Add application service boundary for API, worker and CLI callers.
- [x] Add lifecycle states for queued, running, completed, cancelled and failed jobs.
- [x] Add cancellation, resumability and duplicate-request idempotency handling.
- [x] Persist audit output for both successful and failed executions.
- [x] Add P5 service contract tests; targeted Action Composite suite passes 16/16.

## P6 — Production runner and artifact gate

- [x] Add production runner wiring service, pipeline and ComfyUI identity restorer.
- [x] Add pre-run ComfyUI health gate.
- [x] Add post-run artifact verification for non-empty image and valid manifest.
- [x] Add P6 production integration tests; targeted Action Composite suite passes 18/18.

## P7 — Hardening and optimization review (2026-08-12)

Full audit of the P1–P6 code. The 18 green tests were hiding two defects; both were
reproduced by running the code before being fixed.

### Corrected defects

- [x] **Pixel Preservation Lock (§8.3, §50.6) was inert.** The check compared only the
      **alpha** channel of the diff, and `load_image` always converts to RGBA, so alpha is
      constant at 255. Every RGB mutation outside the mask — body, wardrobe, hair, Hồ Tây,
      background — passed as clean. Replaced with the all-channel comparison in
      `regression_guard.unchanged_outside_mask`; the pipeline no longer keeps a second,
      divergent copy of the same rule.
- [x] **The locked region is `mask == 0`, not "outside the bbox".** A feathered mask blends
      over its own edge, so a naive strict guard fails every legitimate run. Added
      `regression_guard.protected_region(mask, epsilon=0)` as the single definition.
- [x] **The gate now judges the restorer's raw output, not the composite.** `Image.composite`
      discards everything outside the mask by construction, so validating the composite only
      confirmed a tautology while a restorer that regenerated the whole scene still reported a
      clean run (§18 Anti-Regression Rule, §34.3 face cutout).
- [x] **QC status reported failures as `UNVALIDATED`.** `not identity_score` treated a real
      `0.0` as "not measured", and a pixel-preservation failure with no identity score was
      reported as unscored rather than `FAIL`.
- [x] **ComfyUI adapter never sent the images.** It POSTed the workflow JSON alone — no base
      image, no mask, no A2 reference — so the POC could not have run. Added `/upload/image`
      for all three assets plus `inject_inputs()`, which wires them into loader nodes by
      `_meta.title` declared in config rather than by guessed node id.
- [x] Adapter fails fast on ComfyUI `status_str == "error"` instead of spinning to timeout;
      output selection is deterministic; `/view` query is URL-encoded; timeout comes from config.
- [x] **Service idempotency store was written but never read.** `submit` now replays a stored
      result, rejects a conflicting payload reusing a live `job_id` instead of silently
      overwriting it, refuses re-entry into a `RUNNING` job, and is lock-guarded.
- [x] **Resume destroyed the audit trail** (§22, §32): it wrote a fresh 2-record trail over the
      failed attempt. It now continues the stored trail with monotonic iterations.
- [x] `StopCondition` no longer hard-codes a second copy of the thresholds it just asked
      `RegionalValidator` for — a caller-supplied threshold was being silently overruled.
- [x] Retry caps tolerate a caps dict without a `region` key; `crop_for_identity` rejects
      `scale < 1` (inverted box); the A2 authority check matches the filename only, so a
      candidate parked in an `A2_benchmarks/` folder is no longer accepted (§4.1).
- [x] `ComfyUIConfig`: relative workflow paths resolve against the repo root instead of the
      cwd; a malformed env value names the variable at fault.
- [x] `action_composite/__init__.py` declared `__all__` twice, discarding the first (which held
      `ActionCompositePipeline`).

### Tests

- [x] `tests/test_action_composite_comfyui.py` — new; the adapter is exercised against a local
      fake ComfyUI HTTP server (uploads, node wiring, fail-fast on error, special characters in
      filenames). No ComfyUI install, no model files, **no paid API call**.
- [x] Regression tests for every defect above, using `pytest.raises` per repo convention.
- [x] Targeted suite: **77/77 pass**. Full suite: 812 pass; the 99 failures are pre-existing
      (verified by stashing this work and re-running: identical 99 failures at baseline) and
      belong to subject-resolver/validator/video-studio config, untouched here.

### Still open (unchanged from P1)

- [ ] Install/configure the identity-conditioning workflow and model files.
- [ ] Run the A2 benchmark against 10 real action images and record before/after Face QC.

The adapter is now complete enough to drive a real ComfyUI, but it has **never been run against
a live server** — the first real run is still the meaningful test.

## P8 — First live ComfyUI run: blocked by RAM, not by the pipeline (2026-08-12)

The "never been run against a live server" gap above was closed — with an honest negative
result. ComfyUI + PuLID (SDXL-Lightning) + AntelopeV2 were installed locally, a real API-format
workflow was written (`config/comfyui/face_restore_v1_api.json`, node titles matching
`DEFAULT_NODE_BINDINGS`, verified against the PuLID node's actual `INPUT_TYPES` before running),
and 2 real Linh An action images (gpt-image-2, paid, `--ref A2_Front.png`) were pushed through the
actual `ComfyUIIdentityRestorer.restore()` — not the fake HTTP server the test suite uses.

**Both jobs timed out at 240s.** Root cause, confirmed via `vm.swapusage` mid-run
(20.9GB / 21.5GB swap used) and `/queue` inspection: the host (Mac mini M4, 16GB unified memory)
cannot hold SDXL base (6.5G) + PuLID + EVA-CLIP (2G) + InsightFace simultaneously without severe
swap thrashing. PuLID was chosen earlier in this plan as the *lightest of three* identity-model
options (vs. IPAdapter FaceID SD1.5 and InstantID SDXL) — that was a relative comparison, not
confirmation it fits in 16GB, and the gap wasn't checked before the ~8GB of downloads. The upload
+ inject wiring itself was confirmed correct (health check passed, all 3 assets uploaded, the
queued graph matched the intended workflow exactly) — ComfyUI accepted and started the job, it
simply never finished a single sampling step. Server was killed once swap was confirmed
near-exhausted, to avoid crashing the host.

Harry's decision: stop here rather than retry with a longer timeout or switch identity model this
session. Recorded as a known issue.

**Still open, revised:**
- [ ] The identity-conditioning pipeline as configured does not fit in 16GB unified memory. Next
      attempt needs either a lighter stack (SD1.5 IPAdapter FaceID — untested, expected roughly
      ⅓ the checkpoint footprint of the SDXL path) or more memory (cloud GPU / larger machine).
- [ ] The 10-image A2 benchmark is still blocked behind the above — only 2 test images exist so
      far, and neither completed restoration.
- [ ] `face_restore_v1_api.json`'s node wiring has been verified by inspection, not by a
      finished image — that remains the actual open question about the graph itself.

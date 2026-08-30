# Candidate v3 Quality Remediation R1 — R1-P2 FACE_LOCAL Validation

**Status:** `BLOCKED`

## Baseline

The authoritative Phase 7 state was reconstructed without regenerating any image:

- expected FACE_LOCAL cases: `9` (B01–B09)
- placeholder reports: `9`
- valid evaluator results: `0`
- break point: `identity_restoration/application/phase7_candidate_v3_evaluation.py::_build_entrypoint`

The entrypoint constructs `CandidateV3RestorationService` with `face_qc=None`. In `_execute`, the service therefore sets `face_score=None`, writes a placeholder `FACE_LOCAL` report, and calls `face_local_qc_candidate_v3` with missing score evidence. That path deterministically returns `UNVALIDATED / MISSING_FACE_LOCAL_EVIDENCE`.

## Authoritative evaluator semantics

The real implementation is `validator_studio.face_validator.validate_face`. It consumes the candidate canonical crop, the approved IdentityPack reference image(s), the frozen 07F rubric, and a configured observation provider. It computes fixed weighted categories (`facial_shape`, `eyes_and_brows`, `nose`, `mouth_and_chin`, `technical_quality`), applies the existing binary gates, and produces the existing `ValidationReport`; the Candidate v3 scope gate accepts a score at or above the existing `90.0` minimum. No threshold or scoring logic was changed.

The current `provider=mock` branch is explicitly synthetic (`_mock_observe_face` emits fixed `88.0` weighted scores and fictional notes). It is not an evaluator result and is prohibited by the R1-P2 no-fake-validation rule. The authoritative real path calls `VisionClient` with a configured provider.

## Offline availability audit

All nine candidate artifacts and all nine canonical face inputs are present. The immutable validator cache was checked for exact candidate/canonical artifact hashes: `0` matches. Existing cache records that match frozen base-frame hashes cannot be reused for the candidate because their artifact hash and evaluation target differ.

Therefore the real evaluator cannot be executed offline without either a provider call or invalid evidence substitution. No GPU, provider, mock, synthetic score, threshold change, bypass, or artifact regeneration was used.

## Minimal remediation assessment

The missing dependency injection is the exact implementation defect: the Phase 7 builder supplies `face_qc=None`. Wiring a real `face_qc` callable would require a configured authoritative provider or an immutable exact-artifact evaluator cache, neither of which is available under this task's execution policy. Wiring the existing mock would violate the no-fake-validation rule and would not be accepted as FACE_LOCAL evidence.

R1-P2 is consequently recorded as `BLOCKED`, with the implementation path and blocker preserved for the next authorized run. No Phase 0–6, BOUNDARY, SCENARIO_GLOBAL, architecture, policy, workflow, IdentityPack, route, or canonical-transform state was changed.

# GW-P4-R1-T2 — Offline scenario-authority and global-composite scope audit

## 1. Executive decision

Status: CLOSED / AUDIT COMPLETE. Decision: AUTHORITY_UNRESOLVED.

B03/B04 Image-QC uses default Linh An DNA, not benchmark-case scenario authority. It penalizes full-body/action cases for portrait-head-shoulders and elegant-low-bun defaults. No executable, case-bound Linh An scenario profile exists for B03 or B04. The B04 historical human-approved record is a different project/subject and explicitly not historical generation provenance; B03 has no equivalent record. A replacement authority cannot be inferred. GW-P4-R1 is BLOCKED; GW-P4 remains CLOSED / QUALITY FAIL and GW-P5 remains NOT STARTED.

## 2. Evidence inspected

- gw-p4-t2-pilot-exhausted-checkpoint.json
- contracts/identity_restoration/benchmark_set.yaml and BENCHMARK_DATASET_V2_1.md
- B03/B04 C1 regional reports
- validator_studio/image_validator.py, scoring.py, config/validation.yaml
- benchmark_orchestration.py, regional_score_gateway.py, run_gw_p4_t2_regional_stage.py
- compositing.py, pipeline.py, B03/B04 geometry manifests, Linh An subject files, and B04 historical global-validation-authority.json

## 3. B03 authority chain

B03 → Full-body Standing / full body required on Ven Ho rooftop → no scenario mapping in benchmark contract → default VENHO_HOTEL_LINH_AN_DNA.json → no current Linh An scenario overlay → executed Image-QC call has project=venho_hotel, subject=linh_an, scenario_profile_id=null → overall_score=86.61 → RegionalScoreGateway copies it to global_composite → Regional fails only global_composite_below_threshold.

Default DNA expects portrait framing and a low bun. Image-QC reports full body / high ponytail. Face-QC=90.98 approve; identity=90.98; eyes/brows=90.0; geometry=97.80; anatomy/outfit/environment=100; Pixel Lock passes.

## 4. B04 authority chain

B04 → Running Front 3/4 locked GW-P0 action base → no scenario mapping in benchmark contract → same default DNA → no current Linh An scenario overlay → same no-profile Image-QC invocation → overall_score=83.76 → copied to global_composite → Regional fails only global_composite_below_threshold.

Mismatches: earring_type, shot_distance, hairstyle. Face-QC=90.98 approve; identity=90.98; eyes/brows=90.0; geometry=97.08; anatomy/outfit/environment=100; Pixel Lock passes.

The older B04-only record names venho_linh_an / linh_an_action_composite / outdoor_action_jogging_west_lake. It is not a file-backed Validator Studio DNA/overlay for current venho_hotel / linh_an, and says authority_is_historical_generation_provenance=false. It cannot be substituted.

## 5. Scenario overlay audit

Result: D — scenario overlay does not exist for current B03/B04 authority. validate_image supports a subject.scenario overrides file, but execution passes no profile. Current Linh An files are only linh_an.yaml and linh_an.overrides.yaml.

| Field | Classification | Evidence |
|---|---|---|
| shot_distance | SCENARIO-DEPENDENT / GLOBAL-GENERATION-SCOPE | Frozen taxonomy conflicts with portrait default. |
| hairstyle | SCENARIO-DEPENDENT | Schema declares it variable; executed DNA has a default. |
| pose/action/body/camera framing | SCENARIO-DEPENDENT / GLOBAL-GENERATION-SCOPE | Taxonomy provides semantics; Image-QC receives none. |
| face visibility/angle | SCENARIO-DEPENDENT / FACE-RESTORATION-SCOPE | Geometry and Face-QC own visible face. |
| outfit/background | GLOBAL-GENERATION-SCOPE | Locked source and Pixel Lock preserve them. |
| face identity, eyes, brows, nose, mouth, jaw, skin, boundary | AUTHORITATIVE / FACE-RESTORATION-SCOPE | A2 Face-QC and locked geometry are explicit sources. |

## 6. Scope ownership matrix

| Field | Can restorer modify? | Mask changes it? | Current penalty? | Restoration gate? | Evidence |
|---|---|---|---|---|---|
| shot_distance | No | No | Yes | No | Full-canvas framing is outside face-only composite. |
| hairstyle | Partial/unreliable | Head-local only | Yes | UNKNOWN | No action-profile authority. |
| body pose/full-body framing | No | No | No direct field | No | Pixel preservation and taxonomy own it. |
| background/outfit | No | No | No direct field | No | Pixel preservation=100. |
| earring_type | Possibly local | Unproven | B04 yes | UNKNOWN | Ear coverage is not recorded. |
| face identity/eyes/brows/nose/mouth/jaw/skin/boundary | Yes | Yes | Face-QC/generic DNA | Yes | Face-QC passes; paste-through-mask composite. |
| face geometry/angle/visibility | Bounded local | Yes | Not here | Yes | Geometry 97.80 / 97.08 passes. |

composite_crop_into_canvas pastes only through the editable mask, and the pipeline verifies unchanged pixels outside it. Full framing, body, outfit, and environment are not controllable Stage-B outputs.

## 7. global_composite failure reconstruction

| Case | Overall/global | Failed Image-QC fields | Face-QC / identity / geometry | Pixel / Regional |
|---|---:|---|---|---|
| B03 | 86.61 | hair_length 60; shot_distance 0; hairstyle 0 | 90.98 / 90.98 / 97.80 | PASS / only global fails |
| B04 | 83.76 | earring_type 0; shot_distance 0; hairstyle 0 | 90.98 / 90.98 / 97.08 | PASS / only global fails |

Current validation config deterministically weights dna_match=0.30; empty non-forbidden categories inherit it and forbidden=0.20. This explains the impact but does not authorize removing fields.

## 8. Offline re-score result

NOT RECOMPUTABLE FROM CURRENT ARTIFACTS. Parsed observations exist, but no authority-valid B03/B04 profile defines expected framing, action hair, or earring scope. Rewriting observations, creating an overlay, or selecting not_visible would create QC authority, not replay it.

## 9. Authority defect

Confirmed: benchmark executor and executed Regional script omit scenario_profile_id, discarding benchmark taxonomy/provenance at Image-QC invocation. Confirmed gap: no benchmark case-to-profile mapping or current B03/B04 Linh An overlay/reference-set binding exists. Historical B04 cannot fill B03 or establish executable current authority.

## 10. Final decision

AUTHORITY_UNRESOLVED. This does not prove restoration quality or present global score invalid; it proves a valid replacement scope cannot be derived offline. No tuning, GPU, provider call, threshold change, or production change is authorized.

## 11. Exact next task

GW-P4-R1-T3 — Authority completion: add human-approved, versioned B03/B04 case-to-scenario mappings and file-backed validator authority/reference sets; then perform an offline authority replay. No GPU.


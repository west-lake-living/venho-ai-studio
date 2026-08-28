# Candidate v3 Quality Remediation R1 — R1-P0 Reconstruction

**Status:** `CLOSED / PASS`
**Scope:** audit and reconstruction only; no generation, provider, GPU, policy,
workflow, architecture, or production changes.

## Executive result

`BOUNDARY 0/9` means **0 PASS among 9 valid BOUNDARY evaluations**. It does
not mean zero valid samples, nine missing samples, a skipped BOUNDARY validator,
or an aggregation/parser failure.

The nine eligible physical cases are B01–B09. B10 is not part of the nine
quality evaluations because its locked route is `BASE_REGEN_REQUIRED`; it has
only observability and route evidence and no output/QC manifest.

FACE_LOCAL and SCENARIO_GLOBAL each have nine placeholder report files, but no
evaluator result. The Phase 7 evaluation composition explicitly passes
`face_qc=None` and `scenario_validator=None`, so the service serializes
`score=null` / `passed=null` and fail-closes both lanes to `UNVALIDATED`.

## BOUNDARY

Expected cases: B01 Close-up Front, B02 Half-body, B03 Full-body Standing,
B04 Running Front 3/4, B05 Running Side, B06 Walking, B07 Sitting, B08 Hair
Motion, and B09 West Lake. Their frozen input SHA-256 values are recorded in
`contracts/identity_restoration/benchmark_set.yaml` and the Phase 7 summary.

Observed state for every expected case: `valid/fail`. All nine have:

| Case | max channel seam | mean seam | texture | Classification |
|---|---:|---:|---:|---|
| B01 | 106.0 FAIL | 6.626411 PASS | 0.130318 PASS | valid/fail |
| B02 | 182.0 FAIL | 14.328829 REVIEW | 0.153839 PASS | valid/fail |
| B03 | 164.0 FAIL | 16.533766 REVIEW | 0.010573 PASS | valid/fail |
| B04 | 148.0 FAIL | 15.979424 REVIEW | 0.078544 PASS | valid/fail |
| B05 | 200.0 FAIL | 17.961229 REVIEW | 0.200641 PASS | valid/fail |
| B06 | 177.0 FAIL | 19.720273 REVIEW | 0.108453 PASS | valid/fail |
| B07 | 184.0 FAIL | 15.683188 REVIEW | 0.145071 PASS | valid/fail |
| B08 | 186.0 FAIL | 11.552864 PASS | 0.094946 PASS | valid/fail |
| B09 | 174.0 FAIL | 11.457748 PASS | 0.057976 PASS | valid/fail |

The responsible implementation is `identity_restoration/application/phase4_quality.py::evaluate_boundary_qc`.
It executes the locked 3 px seam-ring policy and writes each result to the
case’s `qc/BOUNDARY.json`; `CandidateV3RestorationService` maps that result
into the BOUNDARY scope, and `QualityBundleMerger` receives `FAIL`.

The failure is therefore classified `TRUE_QUALITY_FAILURE` at the current
evidence boundary. The artifacts prove the output fails the approved seam
metric; they do not support reclassifying it as missing evidence, stale
evidence, lineage mismatch, transform failure, or aggregation failure.

Evidence root:
`artifacts/identity-restoration/phase7-candidate-v3/phase7-benchmark-20260828/`
for B01–B04/B07–B09 and
`artifacts/identity-restoration/phase7-candidate-v3/phase7-diagnostic-20260828/`
for B05/B06. Each eligible case also has a Phase 7 job record, route,
observability, canonical artifacts, restored canonical output, inverse
composite, pixel diff, three QC reports, and Manifest 1.4. The checkpoint
contains each BOUNDARY report SHA-256.

## FACE_LOCAL

Expected path for each eligible case:

`candidate output → canonical 512x512 crop → Face QC evaluator → FACE_LOCAL report → lane aggregation`

The actual entry point is
`identity_restoration/application/phase7_candidate_v3_evaluation.py::_build_entrypoint`.
It constructs the service with `face_qc=None`, explicitly documenting that
Phase 7 provider calls are zero. The service then calls
`face_local_qc_candidate_v3` with `score=None`, which returns
`UNVALIDATED` with `MISSING_FACE_LOCAL_EVIDENCE`.

Expected scope rows: 9 (one per B01–B09). The frozen benchmark manifest also
declares three underlying Face QC samples per case, so the nominal atomic
expectation is 27 samples / 9 aggregate scope rows. Actual atomic samples: 0;
actual aggregate evaluator results: 0.
Placeholder report files: 9. Every report has `scope=FACE_LOCAL`,
`score=null`, and the four selected approved reference IDs. None has a Face
QC score, evaluator output, validator version, run ID, case ID, candidate
output hash, or evaluator evidence. Thus the files are not valid Face QC
evaluations; the scope-result lineage is `LINEAGE_UNPROVEN`.

The root cause is `VALIDATOR_NOT_EXECUTED`, with secondary classification
`INSUFFICIENT_EVIDENCE`. It is not caused by the feature flag: the dedicated
evaluation-only entrypoint is allowed to run while the production flag remains
OFF. It is not caused by GPU execution: all nine eligible candidate outputs
completed. No provider output was available or consumed.

Evidence examples: each eligible case’s
`.../qc/FACE_LOCAL.json`, corresponding job record under
`artifacts/identity-restoration/phase7-candidate-v3/jobs/`, and the shared
composition code cited above. All nine placeholder reports have SHA-256
`76e31c86738eaf9ad4977d9a54b9804097dbf0d99ed5540b16e4eae92a8ef383`.

## SCENARIO_GLOBAL

Expected path for each eligible case:

`candidate output + resolved scenario binding → Scenario Global evaluator → SCENARIO_GLOBAL report → lane aggregation`

The actual entry point is the same Phase 7 composition function. It constructs
the service with `scenario_validator=None`. The service writes a report with
the resolved binding and `passed=null`, then creates an
`UNVALIDATED` scope with `MISSING_SCENARIO_QC_EVIDENCE`.

Expected scope rows: 9 (one per B01–B09). Actual evaluator results: 0.
Placeholder report files: 9. The scenario bindings themselves are correct:

- B03/B04 use `action_full_body@1.0` with only `shot_distance` and `hairstyle`
  excluded.
- B01/B02/B05–B09 use `canonical_default` with no exclusions.

There is no authority-resolution defect, exclusion propagation defect, stale
artifact selection, or generation/validator artifact mismatch in the current
records. The root cause is `VALIDATOR_NOT_EXECUTED`, with secondary
`INSUFFICIENT_EVIDENCE`. The scope-result lineage remains `LINEAGE_UNPROVEN`
because no evaluator result was emitted, although the parent job and binding
lineage are present.

Evidence root: each eligible case’s
`.../qc/SCENARIO_GLOBAL.json`, Manifest 1.4, job record, and the binding
construction in `_scenario_bindings()`.

## Dependency map and final decision

```text
candidate output
  → case job / canonical artifacts / composite
  → qc report + Manifest 1.4
  → scope validator
  → QualityBundleMerger
  → Phase 7 quality decision
```

- BOUNDARY breaks at a valid metric result: `FAIL`.
- FACE_LOCAL breaks before validator execution: `score=null` → `UNVALIDATED`.
- SCENARIO_GLOBAL breaks before validator execution: `passed=null` →
  `UNVALIDATED`.

The current aggregate `FAIL` is explained by the approved precedence
`FAIL > UNVALIDATED > NEEDS_REVIEW > PASS` and decisive reason
`SCOPE_FAIL:BOUNDARY`. No current Candidate v3 evidence was replaced with
historical v2/GW-P7 evidence.

Machine-readable checkpoint:
`r1-p0-checkpoint.json` in this directory.

Recommended next task: `R1-P1 Boundary Quality Remediation`.

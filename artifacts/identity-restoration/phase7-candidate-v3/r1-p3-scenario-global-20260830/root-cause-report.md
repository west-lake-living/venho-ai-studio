# Candidate v3 Quality Remediation R1 — R1-P3 SCENARIO_GLOBAL Validation

**Status:** `BLOCKED`

## Baseline

The Phase 7 population remains the nine eligible cases B01–B09. B10 is
excluded by the prior `BASE_REGEN_REQUIRED` terminal state and is not silently
counted as a missing validation result. The nine existing Candidate v3/R1-P1
artifacts have nine `SCENARIO_GLOBAL.json` placeholders with `passed=null` and
zero valid evaluator results.

The exact break point is
`identity_restoration/application/phase7_candidate_v3_evaluation.py::_build_entrypoint`:
it injects `scenario_validator=None`. In
`CandidateV3RestorationService._execute`, that leaves `global_pass=None`,
writes the placeholder report, and produces `SCENARIO_GLOBAL=UNVALIDATED`.

## Authoritative contract

The existing authoritative implementation is
`validator_studio.image_validator.validate_image`, backed by
`observe_image_against_dna` and deterministic `score_image_observation`.
Offline reconstruction is supported only from already parsed observation
evidence through `report_from_image_observations`; no parsed evidence matches
the nine current Candidate v3/R1-P1 artifact hashes. The validator's `mock`
branch is synthetic and cannot be accepted as evidence.

The Candidate v3 callback contract accepts `bool | None` for
`scenario_validator(binding, composite_bytes)`, but there is no existing
adapter that supplies the authoritative `validate_image` report into that
callback. The Phase 7 binding uses `action_full_body@1.0` for B03/B04 while
the Python file resolver expects the existing authority file ID
`action_full_body`; a direct lookup would fail closed. This is a secondary
mapping mismatch, not a license to create a fallback profile or alter the
locked authority.

Locked authority audit remains intact: B03/B04 use
`action_full_body@1.0` with only `shot_distance` and `hairstyle` excluded;
B01/B02/B05–B10 use `canonical_default` with no exclusions. Unknown profiles
fail closed. No exclusions were propagated into another lane.

## Offline/provider decision

The exact current candidate/composite hashes have zero matches in
`artifacts/identity-restoration/benchmarks/validator-cache`. Historical cache
records for frozen base frames are stale for this scope and cannot establish
Candidate v3 lineage. Running the real evaluator would require configured
provider access. Provider/GPU execution is prohibited by this task, and
`provider=mock` would be fake validation.

R1-P3 therefore closes as `BLOCKED`. No source code, threshold, authority,
workflow, IdentityPack, route policy, or canonical transform was changed; no
placeholder was promoted and no quality result was fabricated.

## Regression note

The two pre-existing `tests/test_validator_studio.py` failures for
`nguyen_dinh_thi_street_2026` remain unrelated: they exercise the West Lake
scenario overlay/authority fixture, not Candidate v3 B01–B09 and not either
locked Candidate v3 profile. Candidate v3/Phase 7/authority tests pass, and
the R1-P1 BOUNDARY regression remains 9/9 PASS.

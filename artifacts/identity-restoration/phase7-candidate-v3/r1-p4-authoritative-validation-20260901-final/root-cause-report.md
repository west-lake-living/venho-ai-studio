# Candidate v3 Quality Remediation R1 — R1-P4 Authoritative Provider Validation

**Status:** `PROVIDER_BLOCKED`

## Preflight and lineage

The repository identifies one authoritative provider path: `gemini` with
`gemini-flash-latest`, via `VisionClient -> GeminiVisionProvider`. The existing
Validator Studio entrypoints are `validate_face` for FACE_LOCAL and
`validate_image` for SCENARIO_GLOBAL. Credentials were present, the request
schemas and Gemini schema normalization passed, grounding was disabled, and
the existing retry policy allows two transport attempts for retryable 503/429/
timeout failures.

All nine B01–B09 candidate artifacts, canonical face inputs, workflow hash,
IdentityPack, A2 reference, scenario bindings, and placeholder reports passed
the lineage gate. B10 remains excluded by its prior `BASE_REGEN_REQUIRED`
state. B03/B04 remained `action_full_body@1.0` with only `shot_distance` and
`hairstyle` excluded; all other locked profiles remained `canonical_default`
with no exclusions.

## Provider execution

The first B01 FACE_LOCAL logical sample received `503 UNAVAILABLE` and then a
successful retry. The first harness attempt rejected the same raw response on
a duplicate newline comparison; that harness defect was corrected without
changing validator or quality semantics. Its successful raw response was
preserved and independently parsed as one valid atomic observation.

A second execution attempt then received `503 UNAVAILABLE` on both transport
attempts for the next required sample. Fail-closed policy stopped the batch
before any remaining FACE_LOCAL or SCENARIO_GLOBAL calls. Across both attempts
there were 4 provider transport calls, 1 successful response, and 3 failed
503 responses. Only one atomic FACE_LOCAL observation exists; no complete lane
case was accepted and no quality score was promoted.

The provider failure is not converted into a quality failure. No mock,
synthetic result, GPU/ComfyUI call, image regeneration, threshold change,
authority change, or production promotion occurred.

## Disposition

R1-P4 is `PROVIDER_BLOCKED`: the configured provider could not produce the
authoritative result set required for 9/9 FACE_LOCAL and 9/9 SCENARIO_GLOBAL.
BOUNDARY remains 9/9 PASS. Evidence from both attempts and the preserved raw
response are indexed without overwriting prior R1-P2/R1-P3 evidence.

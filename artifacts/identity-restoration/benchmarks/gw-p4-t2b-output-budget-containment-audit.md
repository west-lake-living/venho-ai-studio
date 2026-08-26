# GW-P4-T2B — Gemini Validator Output-Budget Containment Audit

## Decision

Primary classification: **R5 — NO_SAFE_OFFLINE_REMEDIATION**.

The current locked Gemini/model/rubric/thinking/samples/threshold contract does
not provide a proven semantic-preserving containment patch. `max_output_tokens`
remains **4096**. No provider, GPU, Nano, Face-QC, or readiness call was made.
GW-P4-T2 remains **PROVIDER_BLOCKED** and C1 remains **QUALITY UNKNOWN**.

## Exact data flow

| Layer | File | Symbol | Input → output | Authoritative? | Required downstream? |
|---|---|---|---|---|---|
| runner | `scripts/run_gw_p4_t2_c1_face_qc_gate.py` | `main` | candidate artifact → C1 sample/report | orchestration | yes |
| Face validator | `validator_studio/face_validator.py` | `validate_face` | project/image/provider → `ValidationReport` | yes | yes |
| Face observation | `validator_studio/face_validator.py` | `_observe_face` | image/DNA/rubric → `FaceValidationObservation` | yes | yes |
| request builder | `validator_studio/face_validator.py` | `_build_face_observe_prompt` | DNA/rubric → system prompt | rubric authority | yes |
| client | `shared/vision/client.py` | `VisionClient.analyze_images` | image parts/prompt/schema → provider result | transport | yes |
| Gemini adapter | `shared/vision/providers/gemini_vision.py` | `_generate_config`, `_generate` | prompt/schema → structured JSON text | transport | yes |
| parser | `shared/vision/structured.py` | `extract_json` | raw text → JSON or fail | fail-closed | yes |
| contract gate | `validator_studio/face_validator.py` | `_assert_face_observation_contract` | JSON → accepted observation or fail | yes | yes |
| scorer | `validator_studio/scoring.py` | `score_face_observation` | observation/rubric → Face-QC scores/verdict | yes | yes |
| Regional adapter | `image_studio_runtime/action_composite/regional_score_gateway.py` | `RegionalScoreGateway.build` | Face/Image/scene evidence → Regional scores | yes | yes |
| Regional gate | `image_studio_runtime/action_composite/workflow_v2.py` | `RegionalGate.evaluate` | Regional scores → pass/fail | yes | yes |

Consumed Face-QC authority is: exact gate identifiers and `passed`, all five
`weighted_scores` (`facial_shape`, `eyes_and_brows`, `nose`, `mouth_and_chin`,
`technical_quality`), then the scorer's `dna_match_score`, category scores,
verdict, and kill-switch. Regional consumes the resulting face report's
identity and `eyes_and_brows`, not provider prose. Raw response, parsed report,
provider/model/samples and hashes remain audit/lineage evidence.

## Contract audit

| Field | Classification | Reason |
|---|---|---|
| `gates[].gate` | A — AUTHORITY_REQUIRED | exact rubric criterion identity |
| `gates[].passed` | A — AUTHORITY_REQUIRED | binary gate and kill-switch input |
| `weighted_scores.*` | A — AUTHORITY_REQUIRED | all five numeric inputs to Face-QC scoring |
| `gates[].reason` | B — AUDIT_REQUIRED | retained in reports; not used for score calculation |
| `gates[].evidence` | B — AUDIT_REQUIRED | retained evidence; not used for score calculation |
| `notes` | B — AUDIT_REQUIRED | provider/configuration provenance |
| `FaceValidationObservation` DTO defaults | C — DERIVABLE_OFFLINE | DTO serialization defaults only; no provider score may be filled |
| output JSON example in prompt | D — NARRATIVE_OPTIONAL | instruction/example, not a score source |
| rubric descriptions repeated in prompt payload | E — DUPLICATE CANDIDATE | visibly repeated, but removal has not been proven behavior-preserving |
| `overall_score`, `verdict`, `recommendation`, `identity_match`, `celebrity_match` | F — UNUSED/FORBIDDEN | contract rejects them |

Current schema is `FaceValidationObservation` with `gates`,
`weighted_scores`, and `notes`; `FaceGateResult` has `gate`, `passed`, `reason`,
and `evidence`. The minimal authority subset is the three exact gates plus the
five exact weighted-score keys. It is not adopted as a provider patch because
the B audit fields and prompt grounding are part of the frozen Validator
evidence contract.

## Request and output measurements

Measured offline from the current source/configuration:

| Component | Bytes |
|---|---:|
| base face prompt | 3,346 |
| full system prompt without reference block | 10,426 |
| rubric/DNA validation payload | 6,947 |
| schema before Gemini adapter | 753 |
| adapted schema | 709 |
| adapted schema compact serialization | 644 |
| generic wrapper text (`Analyze these images...`) | 39 |

The schema is passed once through Gemini `config.response_schema`; the shared
client does not serialize a second schema. The prompt itself contains the
rubric payload and a JSON example, so duplication is present as instruction
content, but no offline replay proves that removing it preserves provider
structured-output behavior.

Historical stored Face-QC observations (50 cache entries) measure:

- minimum legal DTO JSON (authority fields only): **238 bytes**
- typical historical observation: **median 1,635 bytes**
- historical p95: **1,934 bytes**
- historical maximum: **1,982 bytes**
- 2048-attempt raw visible response: **1,091 bytes**, truncated
- 4096-attempt raw visible response: **1,096 bytes**, truncated
- 4096-attempt candidate output token count: **3,271**

Known: visible raw bytes, candidate tokens, cached tokens, prompt tokens,
finish reason. Unknown: `thoughtsTokenCount`, total token count, finish
message, HTTP status, candidate/parts counts in the frozen records. No claim is
made that thinking tokens caused the truncation.

## Minimal schema comparison

```text
CURRENT_SCHEMA
  gates[]: gate, passed, reason, evidence
  weighted_scores: five rubric keys
  notes[]

MINIMAL_AUTHORITY_SCHEMA (audit model only; NOT applied)
  gates[]: gate, passed
  weighted_scores: five rubric keys

DIFF
  removes reason/evidence/notes from provider output;
  authority values remain, but the frozen audit contract changes.
```

The output examples and rubric repetition are possible R1/R2 candidates, but
the evidence is insufficient to prove zero provider behavior drift. Therefore
no schema/prompt containment patch is safe under the current authorization.

## Offline verification

The existing provider-blocked freeze tests plus targeted transport, structured
response, Regional gateway, and paid-call guard tests pass with **34 passed**.
Malformed/incomplete JSON remains invalid; missing Regional evidence remains
blocked; `MAX_TOKENS` remains `PROVIDER_TRUNCATED_RESPONSE`; configuration stays
Gemini / `gemini-3.5-flash` / samples=3 / mock=false / fallback=false /
`max_output_tokens=4096`.

Network/provider calls: **0**. GPU jobs: **0**. Nano calls: **0**. Paid test
calls: **0**. `compileall` and `git diff --check`: **PASS**.

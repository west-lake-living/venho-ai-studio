# R1-P4-R5 Provider 503 Root-Cause Isolation

Observed repeated behavior: across R1-P4, R1-P4-R1, R1-P4-R2, and R1-P4-R4,
the same Gemini alias and validator transport path produced one successful
provider response followed by nine failed transport attempts. Every failed
attempt returned the same machine payload: `503 UNAVAILABLE`, code `503`,
status `UNAVAILABLE`, with the message that the model was experiencing high
demand and to try again later.

Evidence: the chronological ledger/attempt audit is preserved in
`attempt-audit.json` and `chronological-failure-table.md`. The local audit
verified `google-genai 1.47.0`, API-key authentication, the default Google
Generative Language endpoint, `client.models.generate_content`, the locked
`gemini-flash-latest` request value, valid structured-output configuration, and
the existing bounded retry/circuit-breaker behavior. Offline provider tests
passed, and the same path previously returned a response with input/output
usage `5254/340`. No 401/403, unsupported-model, schema, truncation, quota,
endpoint, or request-serialization error appears in the evidence.

Provider/API classification: `PROVIDER_SERVICE_UNAVAILABLE`, consistent with
provider-side transient capacity/availability. The payload supports external
service unavailability, but does not expose enough information to prove a
specific Google account, project, region, or quota cause.

Local configuration status: internally consistent. Gemini is configured with
`gemini-flash-latest`; API-key credentials are configured through the existing
environment lookup; endpoint/API method and structured request settings are
compatible with the installed SDK. No project ID is locally configured or
observable, and no secret is included in this evidence.

SDK/model compatibility: no deterministic incompatibility proven. The SDK
signature accepts the exact model/contents/config combination, image parts
are constructed through the supported SDK type, and the same path has
returned a valid response. The alias is passed verbatim; concrete model
resolution was not observable offline, but no invalid-model response was
captured.

Most likely root cause: external Gemini service availability/capacity,
classified as `PROVIDER_OUTAGE_CONFIRMED` for the recovery decision gate.

Confidence: `HIGH` for provider-side availability/capacity; `NOT PROVEN` for
any narrower account/project/quota/region attribution.

Validation can resume now: `NO`.

Required remediation before next validation: keep `PROVIDER_HOLD = ACTIVE`;
obtain a later explicitly authorized bounded recheck after provider
availability is independently restored. Do not switch provider/model, alter
validator or thresholds, or run the 18 pending evaluations in this task.

R1-P4-R5 made zero provider calls and did not clear the hold.

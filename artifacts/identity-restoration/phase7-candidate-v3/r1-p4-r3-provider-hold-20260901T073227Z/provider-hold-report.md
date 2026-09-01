# R1-P4-R3 Provider Blocker Hold & Recovery Gate

Status: `CLOSED / PASS`

`PROVIDER_HOLD = ACTIVE` for authoritative provider `Gemini` and model
`gemini-flash-latest`. The blocker is repeated retryable `503 UNAVAILABLE`
across R1-P4-R1 and R1-P4-R2. R1-P4-R3 made zero provider calls and did not
run a readiness probe, retry, GPU job, mock, synthetic evaluation, or
promotion.

The hold is deterministic and fail-closed. The existing runner has no
background scheduler or automatic retry loop, but a fresh invocation would
otherwise reset its per-run circuit breaker. The runner now checks the
authoritative hold gate before loading credentials or entering validator
execution. It refuses to start while the hold is active unless the next task
sets the explicit `RECOVERY_RECHECK_AUTHORIZED` transition.

Recovery is therefore:

```text
PROVIDER_HOLD = ACTIVE
  -> RECOVERY_RECHECK_AUTHORIZED
  -> bounded provider recheck
```

FACE_LOCAL has 9 pending evaluations and SCENARIO_GLOBAL has 9 pending
evaluations. No quality conclusion is available for either blocked lane.
BOUNDARY remains `9/9 PASS` from immutable R1-P1 evidence.

The candidate v3 feature flag remains `OFF`; production promotion remains
`NO`. Architecture, policies, workflow, IdentityPack, authority, and
thresholds are unchanged.

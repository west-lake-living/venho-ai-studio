# VENHO AI STUDIO — Task Memory

## 2026-09-02 — Candidate v3 R1-P7-R2 B05 FACE_LOCAL remediation ready

`Candidate v3 Quality Remediation R1 / R1-P7-R2-TARGETED-REMEDIATION-B05-FACE-LOCAL =
CLOSED / REMEDIATION_READY`; `TARGETED_REMEDIATION_R2_AUTHORIZED=TRUE` was used.

- Start state preserved from R1-P7-R1: Boundary `9/9 PASS`, FACE_LOCAL `8/9
  PASS`, SCENARIO_GLOBAL `9/9 PASS`, pending `0`, quality `FAIL`, feature
  `OFF`, promotion `NO`, architecture unchanged. Only B05/FACE_LOCAL was in
  scope.
- R1-P7-R1 B05 remains `88.50 / revise`; failed dimensions are
  eyes/brows `87` (`-3`), facial shape `88` (`-2`), and mouth/chin `89` (`-1`)
  against threshold `90`. Nose and technical quality are exactly `90`.
- Evidence supports `TRUE_LOCAL_FACE_QUALITY_FAILURE / FACE_DETAIL_FAILURE`
  with high confidence for the failure class: B05 has valid geometry but the
  smallest close-peer face (`0.072265625`, bbox `74x114`) and most extreme yaw
  (`-49.077°`). B07 uses the same workflow/reference/config and passes at
  `92.25`; B05 SCENARIO_GLOBAL passes at `93.79`. The exact provider-side
  parameter is unresolved and was not guessed.
- Added a B05-only targeted restore variant manifest, preserving all frozen
  inputs and approved quality policy. No live recheck, provider call, GPU,
  Nano, regeneration, threshold/rubric change, or production change occurred.
- Offline validation recorded `76 passed`, compileall PASS, diff check PASS;
  provider calls `0`. Final disposition is
  `FAIL_PENDING_B05_RECHECK`; next action is
  `R1-P7-R2-R1 B05 FACE_LOCAL AUTHORITATIVE RECHECK` under separate authority.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p7-r2-b05-face-local-remediation-20260902T033100Z/`.

## 2026-09-02 — Candidate v3 R1-P7-R1 targeted authoritative recheck completed

`Candidate v3 Quality Remediation R1 / R1-P7-R1-TARGETED-AUTHORITATIVE-RECHECK =
CLOSED / PASS` về execution; `TARGETED_RECHECK_AUTHORIZED=TRUE` đã được dùng.

- Chỉ chạy đúng 5 case: FACE_LOCAL B05/B07 và SCENARIO_GLOBAL B05/B06/B09.
  Tất cả `5/5` response valid, provider `5`, retries `0`, GPU/Nano/alternative
  provider `0`; lineage và raw/parsed hashes đều verified.
- FACE_LOCAL: B05 `88.50 / revise` vẫn fail; B07 `92.25 / approve` pass.
  SCENARIO_GLOBAL: B05 `93.79`, B06 `91.54`, B09 `92.40`, cả ba approve.
- Tổng authoritative sau khi thay thế đúng các failed baseline: Boundary
  `9/9 PASS`, FACE_LOCAL `8/9 PASS`, SCENARIO_GLOBAL `9/9 PASS`, pending `0`.
  Vì B05 FACE_LOCAL còn fail, `QUALITY_DISPOSITION = FAIL`; không set
  quality PASS và không promotion.
- Feature flag `OFF`, production promotion `NO`, architecture unchanged.
  Không rerun 13 passing baseline case và không sửa thêm remediation trong
  task này.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p7-r1-targeted-authoritative-recheck-20260902T032200Z/`.

Next action: `TARGETED_REMEDIATION_R2_REQUIRES_SEPARATE_AUTHORIZATION` cho B05
FACE_LOCAL còn lại.

## 2026-09-02 — Candidate v3 R1-P7 targeted quality remediation ready

`Candidate v3 Quality Remediation R1 / R1-P7-TARGETED-QUALITY-REMEDIATION =
CLOSED / REMEDIATION_READY`; explicit
`TARGETED_QUALITY_REMEDIATION_AUTHORIZED=TRUE` was used and
`TARGETED_RECHECK_AUTHORIZED=FALSE` remained enforced.

- R1-P6 authoritative baseline is preserved: Boundary `9/9 PASS`, FACE_LOCAL
  `7 PASS / 2 FAIL` (`B05`, `B07`), SCENARIO_GLOBAL `6 PASS / 3 FAIL`
  (`B05`, `B06`, `B09`), pending `0`, quality `FAIL`, provider hold
  `RECOVERED`, feature `OFF`, promotion `NO`.
- Root cause classification: B05/B07 FACE_LOCAL are valid true image/local
  face-detail failures; B05/B06 SCENARIO_GLOBAL were evaluated under the
  wrong `canonical_default` authority for action cases; B09 has a proven
  prompt-conditioning mismatch (medium/half-body and hair down instead of
  head-and-shoulders and elegant low bun). B05/B07 exact workflow parameter
  mechanism remains unresolved and was not guessed.
- Targeted implementation adds `action_full_body@1.0` authority mapping only
  to B05/B06. It prepares, but does not execute, targeted variants for B05,
  B07, and B09. Frozen historical artifacts and the R1-P6 evidence remain
  immutable.
- Existing authority replay passes without provider calls: B05 `97.74 approve`,
  B06 `91.47 approve`, while the historical quality result is not rewritten.
  Passing-case protection covers all 13 previously passing evaluator cases.
- Offline validation recorded `13 passed`, compileall PASS, and
  `git diff --check` PASS. Provider/GPU/Nano/alternative-provider calls are
  all `0`.
- Final state is `R1-P7 = CLOSED / REMEDIATION_READY`,
  `QUALITY_DISPOSITION = FAIL_PENDING_RECHECK`; next action is
  `R1-P7-R1 TARGETED AUTHORITATIVE RECHECK` under separate authorization.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p7-targeted-quality-remediation-20260902T030000Z/`.

## 2026-09-02 — Candidate v3 R1-P6 authoritative evaluation completed with quality FAIL

`Candidate v3 Quality Remediation R1 / R1-P6-AUTHORITATIVE-EVALUATION-RESUME =
CLOSED / PASS`; `QUALITY_DISPOSITION = FAIL`.

- Explicit human authorization `AUTHORITATIVE_EVALUATION_RESUME_AUTHORIZED=TRUE`
  was used. Start state was R1-P5-R4 PASS, Gemini
  `gemini-flash-latest`, provider hold RECOVERED, boundary 9/9 PASS, and 18
  pending authoritative evaluations.
- Offline preflight passed: focused evaluator, provider gate, schema/DTO,
  parser, lineage, invalid-response, failure-classification, partial-run, and
  aggregation tests recorded `81 passed`; compileall and `git diff --check`
  also passed.
- Evaluation ran sequentially. FACE_LOCAL completed 9 valid cases, the
  stability gate passed, and SCENARIO_GLOBAL completed 9 valid cases. Exactly
  18 Gemini calls were made with 0 retries; all 18 responses were valid and
  have separate raw/parsed evidence and verified hashes.
- Existing quality aggregation returned FACE_LOCAL `7 pass / 2 fail` and
  SCENARIO_GLOBAL `6 pass / 3 fail`, therefore overall quality is `FAIL`.
  This is a completed evaluation result, not a remediation decision.
- Pending authoritative evaluations are `0`; boundary remains 9/9 PASS.
  Provider hold remains RECOVERED, feature flag OFF, promotion NO, and
  architecture unchanged. No provider/model switch, fallback, GPU, Nano,
  generation, rubric, threshold, or schema change occurred.
- Evidence hashes verify `84/84` files:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p6-authoritative-evaluation-resume-20260902T024012Z/`.

Any remediation or production promotion requires a separate explicit
authorization.

## 2026-09-02 — Candidate v3 R1-P5-R4 provider recovery recheck passed

`Candidate v3 Quality Remediation R1 / R1-P5-R4-PROVIDER-RECOVERY-RECHECK =
CLOSED / PASS`.

- Explicit human authorization `PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE`
  was used. The start state was R1-P5 PASS, R1-P5-R1 through R1-P5-R3
  provider blocked, provider hold ACTIVE, boundary 9/9 PASS, and 18 pending
  authoritative evaluations.
- Offline preflight passed before execution: focused hold/authorization,
  one-call-limit, Gemini adapter, failure classification,
  truncation/malformed-output, schema/DTO, and evidence-lineage tests
  recorded `44 passed`; compileall and `git diff --check` also passed.
- Exactly one live Gemini `gemini-flash-latest` probe used the authoritative
  `FACE_LOCAL/B01/sample-1` fixture with one transport attempt and zero retry.
  Gemini returned a complete schema-valid and DTO-valid response without
  repair. The evaluator quality recommendation was `REVISE`; this is still a
  valid provider recovery response. Raw and parsed hashes were recorded.
- Recovery is proven: `RECOVERY_PROBE = PASS`,
  `PROVIDER_RECOVERY_STATUS = PASS`, and the provider hold is `RECOVERED`.
  No second probe, bulk evaluation, fallback, provider/model switch, GPU,
  Nano, generation, or promotion occurred.
- State integrity remains: `BOUNDARY = 9/9 PASS`, FACE_LOCAL `0/9`,
  SCENARIO_GLOBAL `0/9`, pending `18`, quality `UNVALIDATED`, feature flag
  `OFF`, promotion `NO`, architecture unchanged.
- Evidence hashes verify `24/24` files:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p5-r4-provider-recovery-recheck-20260902T010010Z/`.

Resume of the 18 authoritative evaluations requires separate explicit
authorization.

## 2026-09-02 — Candidate v3 R1-P5-R3 provider recovery recheck timed out

`Candidate v3 Quality Remediation R1 / R1-P5-R3-PROVIDER-RECOVERY-RECHECK =
CLOSED / PROVIDER_BLOCKED`.

- Explicit human authorization `PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE`
  was used. The start state was R1-P5 PASS, R1-P5-R1 and R1-P5-R2 provider
  blocked, provider hold ACTIVE, boundary 9/9 PASS, and 18 pending
  authoritative evaluations.
- Offline preflight passed before execution: focused gate/authorization,
  one-call-limit, Gemini adapter, schema/DTO, failure classification,
  truncation/malformed-output, and evidence-lineage tests recorded `40 passed`;
  compileall and `git diff --check` also passed.
- Exactly one live Gemini `gemini-flash-latest` probe used the authoritative
  `FACE_LOCAL/B01/sample-1` fixture with one transport attempt and zero retry.
  The provider response did not return before the runner ended, so the
  fail-closed classification is `PROVIDER_TIMEOUT`; no raw or parsed response
  was captured.
- The hold remains ACTIVE. No second probe, bulk evaluation, fallback,
  provider/model switch, GPU, Nano, generation, or promotion occurred.
  Final state remains FACE_LOCAL `0/9`, SCENARIO_GLOBAL `0/9`, pending `18`,
  quality `UNVALIDATED`, feature flag `OFF`, promotion `NO`, architecture
  unchanged.
- Evidence hashes verify `12/12` files:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p5-r3-provider-recovery-recheck-20260902T005205Z/`.

Keep the provider hold active; require new explicit authorization before any
future recovery probe.

## 2026-09-01 — Candidate v3 R1-P5-R2 provider recovery recheck blocked

`Candidate v3 Quality Remediation R1 / R1-P5-R2-PROVIDER-RECOVERY-RECHECK =
CLOSED / PROVIDER_BLOCKED`.

- Explicit human authorization `PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE`
  was used. The authoritative start state was verified as R1-P5 PASS,
  R1-P5-R1 provider-blocked, provider hold ACTIVE, boundary 9/9 PASS, and 18
  pending authoritative evaluations.
- Offline preflight passed before execution: the existing R1-P5 gate/recovery
  focused tests recorded `36 passed`, compileall PASS, and `git diff --check`
  PASS; the R2 harness suite recorded `38 passed` including its regression
  checks.
- Exactly one live probe ran against Gemini `gemini-flash-latest` using the
  existing authoritative `FACE_LOCAL/B01/sample-1` fixture. The transport cap
  was one attempt, so provider calls `1`, retries `0`; Gemini returned `503
  UNAVAILABLE`. No raw or parsed response exists because the provider failed
  before response generation.
- Recovery gate returned to ACTIVE after
  `ACTIVE -> RECOVERY_CHECK_AUTHORIZED -> RECOVERY_PROBE_IN_PROGRESS`; no
  recovery, quality verdict, bulk evaluation, second probe, fallback, model
  switch, GPU, Nano, generation, or promotion occurred.
- State integrity remains: `FACE_LOCAL = 0/9`, `SCENARIO_GLOBAL = 0/9`,
  `PENDING = 18`, `BOUNDARY = 9/9 PASS`, quality `UNVALIDATED`, feature flag
  `OFF`, promotion `NO`, architecture unchanged.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p5-r2-provider-recovery-recheck-20260901T104029Z/`.

Keep the provider hold active; require new explicit authorization before any
future recovery probe.

## 2026-09-01 — Candidate v3 R1-P5-R1 provider recovery probe blocked

`Candidate v3 Quality Remediation R1 / R1-P5-R1-PROVIDER-RECOVERY-PROBE =
PROVIDER_BLOCKED`.

- Explicit human authorization `PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE` was
  used. The first local preflight attempt correctly made zero provider calls
  but exposed an incorrect test filename in the new harness; its evidence is
  preserved. The corrected preflight passed `36` tests, compileall, and
  `git diff --check` before live execution.
- One and only one live probe ran on the existing authoritative Gemini
  `gemini-flash-latest` / `FACE_LOCAL/B01/sample-1` path. The probe was capped
  at one transport attempt and one paid-call budget; it returned `503
  UNAVAILABLE`. Provider calls `1`, retries `0`, successful responses `0`,
  failed responses `1`, with no raw or parsed response available.
- Recovery gate transitioned
  `ACTIVE -> RECOVERY_CHECK_AUTHORIZED -> RECOVERY_PROBE_IN_PROGRESS ->
  ACTIVE`. Recovery is not proven; hold remains active. No second probe, bulk
  evaluation, fallback provider/model, GPU, Nano, generation, or promotion was
  performed.
- State integrity remains: `BOUNDARY = 9/9 PASS`, FACE_LOCAL `0/9`,
  SCENARIO_GLOBAL `0/9`, pending `18`, quality `UNVALIDATED`, feature flag
  `OFF`, production promotion `NO`, architecture unchanged.
- Finalized evidence (copied without another provider call):
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p5-r1-provider-recovery-probe-20260901T095300Z/`.

Keep the provider hold active; a new explicit authorization is required for
any future recovery probe.

## 2026-09-01 — Candidate v3 R1-P5 provider recovery gate

`Candidate v3 Quality Remediation R1 / R1-P5 = CLOSED / PASS` for
control-plane hardening only.

- Added the fail-closed `ProviderRecoveryGate` using the existing authoritative
  provider-hold document. Its states are `ACTIVE`,
  `RECOVERY_CHECK_AUTHORIZED`, `RECOVERY_PROBE_IN_PROGRESS`, and `RECOVERED`.
- Recovery requires the strict human-controlled
  `PROVIDER_RECOVERY_RECHECK_AUTHORIZED=TRUE` value. Missing, false,
  malformed, or unknown authorization leaves `PROVIDER_HOLD = ACTIVE` and
  `PROVIDER_CALLS = 0`; authorization is never inferred from task status,
  retries, elapsed time, availability, test mode, or CLI invocation.
- The gate permits at most one logical recovery probe, locks provider/model to
  Gemini `gemini-flash-latest`, rejects fallback/model switching, and blocks
  both FACE_LOCAL and SCENARIO_GLOBAL bulk execution. Recovery PASS requires
  complete transport, parse, DTO/schema, raw-response hash, and lineage
  evidence; a complete quality FAIL response is still valid provider recovery.
- R1-P5 was executed offline with no probe: `28 passed`, compileall PASS,
  `git diff --check` PASS, provider calls `0`, GPU `0`, Nano `0`. Hold remains
  ACTIVE, FACE_LOCAL and SCENARIO_GLOBAL remain `0/9`, pending remains `18`,
  BOUNDARY remains `9/9 PASS`, quality remains `UNVALIDATED`, feature flag is
  OFF, and promotion is NO.
- The prior recovery wrapper no longer chains a successful probe into bulk
  evaluation. A separate authoritative resume task is required after a real
  recovery transition.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p5-provider-recovery-gate-20260901T091815Z/`.

## 2026-09-01 — Candidate v3 R1 recovery recheck blocked

`Candidate v3 Quality Remediation R1 / R1-RECOVERY-RECHECK = PROVIDER_BLOCKED`.

- Explicit authorization `RECOVERY_RECHECK_AUTHORIZED = TRUE` was recorded.
  Offline preflight passed with `58` focused tests, compileall PASS, and
  `git diff --check` PASS before any live provider call.
- Exactly one minimal probe was attempted against the existing authoritative
  Gemini `gemini-flash-latest` path: `FACE_LOCAL/B01/sample-1`. The existing
  two-attempt retry policy made `2` provider calls; both returned
  `503 UNAVAILABLE` with the same high-demand provider message.
- The probe produced no complete authoritative response: valid `0`, invalid
  `0`, and no raw response to parse. Fail-closed termination prevented bulk
  FACE_LOCAL and SCENARIO_GLOBAL execution. No second probe, speculative retry,
  provider switch, GPU job, Nano call, regeneration, or promotion occurred.
- Final state: `FACE_LOCAL = 0/9`, `SCENARIO_GLOBAL = 0/9`, `PENDING = 18`,
  `BOUNDARY = 9/9 PASS`, `PROVIDER_HOLD = ACTIVE`, feature flag `OFF`, and
  production promotion `NO`. No architecture or production behavior changed.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-recovery-recheck-20260901T090543Z/`.

Keep the provider hold active; a later recovery attempt requires a new explicit
authorization and must begin with another bounded probe.

## 2026-09-01 — Candidate v3 R1-P4-R5 provider 503 root-cause isolation

`Candidate v3 Quality Remediation R1 / R1-P4-R5 = CLOSED / PASS`.

- Offline audit covered every recorded provider transport from R1-P4,
  R1-P4-R1, R1-P4-R2, and R1-P4-R4: 10 transports total, one valid response
  and nine repeated `503 UNAVAILABLE` failures. Every failure carried the
  same machine status `UNAVAILABLE` and high-demand message.
- Local audit confirmed `google-genai 1.47.0`, API-key authentication, default
  `generativelanguage.googleapis.com/v1beta` endpoint,
  `client.models.generate_content`, locked `gemini-flash-latest`, structured
  JSON configuration, and bounded retry/circuit-breaker behavior. No
  deterministic local SDK, endpoint, schema, authentication-status, or invalid
  model defect was evidenced. No diagnostic provider call was made.
- Decision: `PROVIDER_OUTAGE_CONFIRMED` / `PROVIDER_SERVICE_UNAVAILABLE`, with
  high confidence for external availability/capacity but no unsupported claim
  about a specific account, project, quota, or region.
- Hold remains active. FACE_LOCAL and SCENARIO_GLOBAL remain `0/9 valid` with
  18 pending total; BOUNDARY remains `9/9 PASS`. No provider switch, GPU,
  generation, validator, threshold, authority, policy, workflow, IdentityPack,
  quality, or promotion change occurred.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-r5-provider-503-isolation-20260901T083517Z/`.

Next action is `KEEP HOLD`; any later resume requires a new explicit recovery
authorization after provider availability is restored.

## 2026-09-01 — Candidate v3 R1-P4-R4 recovery recheck blocked

`Candidate v3 Quality Remediation R1 / R1-P4-R4 = PROVIDER_BLOCKED`.

- Human authorization `RECOVERY_RECHECK_AUTHORIZED` was recorded and used for
  exactly one bounded authoritative Gemini recheck. The hold was active before
  and remains active after the recheck.
- The first pending request, FACE_LOCAL B01, received two retryable
  `503 UNAVAILABLE` responses. Provider calls `2`, successful `0`, failed `2`,
  503 `2`, reused `0`; input/output tokens were unavailable.
- Circuit breaker stopped execution before remaining samples. FACE_LOCAL and
  SCENARIO_GLOBAL remain `0/9 valid` and `UNVALIDATED / PROVIDER_BLOCKED`;
  BOUNDARY remains immutable `9/9 PASS`.
- No fallback provider, mock/synthetic output, GPU, promotion, validator,
  threshold, authority, architecture, policy, workflow, or IdentityPack
  change occurred. No automatic retry task was started.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-r4-recovery-recheck-20260901T082722Z/`.

Wait for a new explicit recovery authorization before any future recheck.

## 2026-09-01 — Candidate v3 R1-P4-R3 provider blocker hold

`Candidate v3 Quality Remediation R1 / R1-P4-R3 = CLOSED / PASS`.

- Provider hold is authoritative and active for Gemini
  `gemini-flash-latest`; reason is repeated retryable `503` availability
  failure across R1-P4-R1 and R1-P4-R2.
- R1-P4-R3 is offline-only: provider calls `0`, readiness probes `0`, GPU
  calls `0`, promotions `0`, and no synthetic/mock result.
- The existing runner had no background retry loop, but a new invocation could
  reset its per-run breaker. A minimal entrypoint guard now rejects execution
  before credential load/provider execution while the hold gate is active.
- Recovery requires the explicit transition
  `PROVIDER_HOLD_ACTIVE -> RECOVERY_RECHECK_AUTHORIZED -> bounded provider
  recheck`; there is no time-based or automatic transition.
- Pending manifest preserves exact artifact SHA and authority lineage for 18
  evaluations: FACE_LOCAL B01–B09 and SCENARIO_GLOBAL B01–B09. Both lanes are
  `UNVALIDATED_PROVIDER_BLOCKED`; BOUNDARY remains immutable `9/9 PASS`.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-r3-provider-hold-20260901T073227Z/`.

Do not start provider recheck until the next task explicitly authorizes
`RECOVERY_RECHECK_AUTHORIZED`.

## 2026-09-01 — Candidate v3 R1-P4-R2 provider availability recheck blocked

`Candidate v3 Quality Remediation R1 / R1-P4-R2 = PROVIDER_BLOCKED`.

- Gemini `gemini-flash-latest` remained correctly configured and authoritative.
  The bounded recheck made two transport calls; both returned `503 UNAVAILABLE`
  after the existing two-attempt retry policy.
- No R1-P4 or R1-P4-R1 response met the complete request/artifact/validator/
  authority lineage needed for reuse. No mock, synthetic, GPU, regeneration,
  quality change, or provider fallback was used.
- Execution stopped before both lanes: FACE_LOCAL `0/9`, SCENARIO_GLOBAL `0/9`;
  BOUNDARY remains `9/9 PASS`.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-r2-provider-recheck-20260901T072511Z/`.

## 2026-09-01 — Candidate v3 R1-P4-R1 provider execution remediation blocked

`Candidate v3 Quality Remediation R1 / R1-P4-R1 = PROVIDER_BLOCKED`.

- Gemini `gemini-flash-latest` remained the sole authoritative provider. The
  adapter audit confirmed `503 -> PROVIDER_503`, bounded two-attempt retry,
  `0.25s` backoff, no jitter, and fail-closed circuit behavior.
- The only deterministic defect found was in R1-P4 orchestration: reuse was
  hard-coded to B01/sample 1 and did not verify a complete request/artifact/
  validator/policy metadata tuple. A runner-only resumable harness now persists
  attempt history, schema-valid responses, request hashes, and checkpoints.
- R1-P4-R1 called Gemini twice for B01 FACE_LOCAL sample 1; both transport
  attempts returned 503. No valid response was produced or reused; execution
  stopped before all remaining Face and Scenario calls. FACE_LOCAL and
  SCENARIO_GLOBAL remain `0/9 valid`; BOUNDARY remains `9/9 PASS`.
- No quality logic, rubric, authority, threshold, architecture, workflow,
  IdentityPack, GPU, generation, mock, synthetic result, or promotion changed.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-r1-provider-remediation-20260901T065908Z/`.

## 2026-09-01 — Candidate v3 R1-P4 authoritative provider validation blocked

`Candidate v3 Quality Remediation R1 / R1-P4 = PROVIDER_BLOCKED`.

- Existing project config selected one provider only: Gemini with model
  `gemini-flash-latest`; the existing adapter/retry/schema path passed
  preflight and all nine B01–B09 artifact lineages were verified.
- The first B01 FACE_LOCAL sample had one valid provider response after a
  503 retry. The first attempt's evidence harness had a newline comparison
  defect, which was corrected without changing validator semantics. A second
  attempt then received 503 on both retry attempts. The batch stopped
  fail-closed before remaining FACE_LOCAL samples or any SCENARIO_GLOBAL
  call.
- Total R1-P4 provider transports: 4; successful: 1; failed: 3. Complete
  valid case evaluations: FACE_LOCAL 0/9, SCENARIO_GLOBAL 0/9. No provider
  failure was converted to a quality failure.
- BOUNDARY remains 9/9 PASS. GPU calls, mock calls, synthetic results,
  regeneration, promotion, threshold changes, and policy/authority/workflow/
  IdentityPack changes: 0/NO.
- Final evidence is under
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p4-authoritative-validation-20260901-final/`.

Do not start a quality remediation task until provider execution is available.

## 2026-08-30 — Candidate v3 R1-P3 SCENARIO_GLOBAL validation blocked

`Candidate v3 Quality Remediation R1 / R1-P3 = BLOCKED`.

- Baseline is 9 expected eligible cases B01–B09, 9 placeholder
  `SCENARIO_GLOBAL` reports, and 0 valid evaluator results. B10 remains
  excluded by the prior `BASE_REGEN_REQUIRED` state.
- The exact break point is `phase7_candidate_v3_evaluation.py::_build_entrypoint`,
  which constructs the service with `scenario_validator=None`.
- The existing authoritative implementation is
  `validator_studio.image_validator`; its live observation path requires a
  configured provider. `report_from_image_observations` can replay only
  parsed evidence, but no exact candidate/R1-P1 artifact cache matches exist.
  The mock evaluator is synthetic and was not used.
- Candidate authority assignments remain locked: B03/B04 are
  `action_full_body@1.0` with only `shot_distance` and `hairstyle` excluded;
  B01/B02/B05–B10 are `canonical_default` with no exclusions. The existing
  Python resolver uses the unversioned `action_full_body` file ID, so direct
  callback wiring would also fail closed; no fallback authority was created.
- The two historical `nguyen_dinh_thi_street_2026` test failures remain
  unrelated to this Candidate v3 lane. Candidate v3/Phase 7/authority tests
  pass; BOUNDARY regression is 9/9 PASS.
- R1-P3 made 0 GPU/provider calls, changed no source code or policy, and did
  not start R1-P4.
- Evidence:
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p3-scenario-global-20260830/`.

## 2026-08-30 — Candidate v3 R1-P2 FACE_LOCAL validation blocked

`Candidate v3 Quality Remediation R1 / R1-P2 = BLOCKED`.

- Baseline was `9` expected FACE_LOCAL cases, `9` placeholder reports, and
  `0` valid evaluator results. The exact break point is
  `phase7_candidate_v3_evaluation.py::_build_entrypoint`, which constructs the
  service with `face_qc=None`; `_execute` then writes `score=null` and
  `MISSING_FACE_LOCAL_EVIDENCE`.
- The authoritative evaluator is
  `validator_studio.face_validator.validate_face`. It requires the existing
  07F rubric, canonical crop, approved IdentityPack references, and a real
  configured provider. The `mock` branch emits synthetic fixed scores and is
  not valid evidence.
- All nine candidate artifacts and canonical face inputs are present. The
  immutable validator cache has zero exact matches for those candidate or
  canonical hashes; available records match frozen base frames and cannot be
  reused without violating lineage.
- No provider/GPU call, fake score, threshold change, validator bypass, or
  artifact regeneration was performed. BOUNDARY regression remains `9/9 PASS`.
- Evidence is under
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p2-face-local-20260830/`.

Next authorized task remains blocked pending an offline authoritative cache or
explicit provider authorization. Do not start R1-P3.

## 2026-08-28 — Candidate v3 R1-P1 boundary quality remediation

`Candidate v3 Quality Remediation R1 / R1-P1 = CLOSED / PASS`.
R1-P1 used only the nine existing B01–B09 Phase 7 outputs and made zero GPU
and provider calls. FACE_LOCAL and SCENARIO_GLOBAL were not changed.

- Baseline BOUNDARY was `PASS 0/9`, with valid samples in every case. The
  locked `maxChannelSeamDelta` threshold remained `32`; baseline statistics
  were min `106`, max `200`, mean `169`, median `177`. The nearest case was
  B01 (`106`); the worst was B05 (`200`).
- A no-op base-as-final experiment failed the same metric on all nine cases,
  proving the current boundary samples include pre-existing source edge
  contrast. The composite also had no local continuity postprocess, and the
  Phase 7 benchmark supplied a binary mask as its feather mask.
- `apply_boundary_color_continuity` now runs after inverse compositing and
  before pixel-lock evidence. It operates only on the authoritative inner
  3px ring, seeds from immutable outer samples, applies deterministic 3x3
  Gaussian softening, and bounds only editable ring pixels by the existing
  policy pass envelope. The validator and threshold are unchanged.
- Offline derived outputs from the same nine artifacts returned BOUNDARY
  `PASS 9/9`; all pixel-lock, mean-seam, and local-texture gates passed. Prior
  Phase 7 and R1-P0 directories were not overwritten.
- Evidence is under
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p1-boundary-remediation-20260828/`.

Recommended next task: `R1-P2 FACE_LOCAL Validation`.

## 2026-08-28 — Candidate v3 R1-P0 failure/evidence reconstruction

`Candidate v3 Quality Remediation R1 / R1-P0 = CLOSED / PASS`. This was an
offline, audit-only reconstruction; no code, policy, workflow, IdentityPack,
architecture, feature flag, production registry, GPU, or provider state was
changed.

- The nine BOUNDARY cases are B01–B09. All nine have valid final-composite
  BOUNDARY evaluations and all nine fail `maxChannelSeamDelta`, so the
  authoritative `BOUNDARY 0/9` means zero PASS among nine valid evaluations.
  B10 is `BASE_REGEN_REQUIRED` before bridge/composite/QC and is not part of
  the nine-case quality denominator.
- FACE_LOCAL expected nine eligible-case results but has zero evaluator
  results. The evaluation-only composition passes `face_qc=None`; nine
  placeholder reports contain `score=null` and are not valid QC evidence.
  Root cause: `VALIDATOR_NOT_EXECUTED`, secondary `INSUFFICIENT_EVIDENCE`.
- SCENARIO_GLOBAL expected nine eligible-case results but has zero evaluator
  results. The evaluation-only composition passes `scenario_validator=None`;
  nine placeholder reports contain `passed=null`. Root cause:
  `VALIDATOR_NOT_EXECUTED`, secondary `INSUFFICIENT_EVIDENCE`.
- Scenario authority resolution is correct: B03/B04 use
  `action_full_body@1.0` with only `shot_distance` and `hairstyle` excluded;
  B01/B02/B05–B09 use `canonical_default` with no exclusions. No historical
  v2 evidence was used and no lineage, transform, mapping, or aggregation
  defect was found.
- R1-P0 itself made `0` GPU calls and `0` provider calls. The prior physical
  run remains recorded as nine GPU jobs and zero provider calls. The immutable
  audit checkpoint and report are under
  `artifacts/identity-restoration/phase7-candidate-v3/r1-p0-reconstruction-20260828/`.

Recommended next task: `R1-P1 Boundary Quality Remediation`.

## 2026-08-28 — Candidate v3 final roadmap closure

The current Candidate v3 attempt is finalized as `REJECTED / NON-PRODUCTION`.
Phase 0 through Phase 6 remain `CLOSED / PASS`; Phase 7 is
`CLOSED / QUALITY FAIL` with final disposition `NO_PROMOTION_QUALITY`.

- Phase 8 exists in the authoritative roadmap, but its entry condition was
  not met and its tracking state is `BLOCKED / ENTRY CONDITION NOT MET`.
  No Phase 8 work was started.
- Remediation is `NOT AUTHORIZED / NOT SPECIFIED` by the current roadmap. No
  Candidate v4, quality tuning, threshold change, retry, or promotion was
  authorized.
- Final quality evidence: correctness `PASS 9/9`; outside-mask pixel lock
  `PASS 9/9`; BOUNDARY `PASS 0/9`; FACE_LOCAL `UNVALIDATED`;
  SCENARIO_GLOBAL `UNVALIDATED`; complete quality PASS `0/9`.
- Physical execution totaled `9` GPU jobs and `0` provider calls. The
  append-only evidence remains under
  `artifacts/identity-restoration/phase7-candidate-v3/`, with aggregate
  report `phase7-evaluation-summary-20260828.json`.
- Candidate v3 remains feature-gated `OFF` and promotion is `NO`. No
  threshold was changed post hoc. v2/v2.1 behavior and the existing
  architecture remain unchanged.

## 2026-08-28 — Candidate v3 Phase 7 closure

Phase 7 — Technical validation and candidate evaluation is `CLOSED / QUALITY
FAIL`, with final disposition `NO_PROMOTION_QUALITY`. The evaluation-only
authority was honored and no production promotion occurred.

- P7-T1 passed with the identity suite at `328 passed`; CPU B01–B10 retained
  all rows and routed B01–B09 `ELIGIBLE`, B10 `BASE_REGEN_REQUIRED`.
- P7-T2 passed through the dedicated exact-purpose entrypoint. It used the
  existing CandidateV3 service stack and ComfyUiCandidateV3Adapter, preserved
  workflow/route/transform/quality/IdentityPack/ScenarioAuthority lineage,
  rejected production or missing purpose, and never registered in production.
- HARRY-ROG preflight was HEALTHY with GTX 1660 SUPER 6GB and 5132 MiB free.
- P7-T3 technical diagnostic passed: B05 and B06 each consumed one GPU job;
  B10 consumed zero. Both B05/B06 correctness and pixel lock passed, while
  BOUNDARY failed. FACE_LOCAL and SCENARIO_GLOBAL were UNVALIDATED because
  provider calls remained zero.
- P7-T4 technical benchmark completed with seven additional GPU jobs for
  B01–B04 and B07–B09. B05/B06 were reused only as exact diagnostic evidence;
  total physical GPU jobs were `9`, all nine physical cases completed, and
  B10 remained terminal `BASE_REGEN_REQUIRED`.
- All nine physical cases had correctness/pixel-lock PASS but BOUNDARY FAIL;
  all FACE_LOCAL and SCENARIO_GLOBAL scopes were UNVALIDATED. The approved
  split-QC precedence therefore prevents quality PASS and promotion.
- Evidence is retained under
  `artifacts/identity-restoration/phase7-candidate-v3/`, with aggregate
  summary `phase7-evaluation-summary-20260828.json` and per-case manifests,
  QC reports, restored crops, inverse composites, and pixel diffs.
- No tuning, threshold changes, regeneration, v2 physical evidence reuse,
  production promotion, feature-flag change, or Phase 8 work occurred.
  Candidate v3 remains OFF; provider calls `0`; GPU jobs `9`.

## 2026-08-27 — Candidate v3 Phase 6 closure

Phase 6 — Frontend integration is `CLOSED / PASS`. The authoritative goal was
to make the operational decision understandable and safe. The minimal
sequential decomposition was P6-T1 → P6-T2 → P6-T3.

- P6-T1 adds `identity_restoration/interface/candidate_v3_frontend.py`, a
  deterministic frontend projection containing profile IDs, preflight status,
  and separate `FACE_LOCAL`, `BOUNDARY`, and `SCENARIO_GLOBAL` evidence. It
  strips paths/configuration and other internal lineage values before the
  client boundary and maps missing scope/correctness evidence to
  `UNVALIDATED`.
- P6-T2 adds fail-closed controlled action states: approval is not visible for
  any non-pass or incomplete state; `BASE_REGEN_REQUIRED` is explicit and is
  never an automatic retry; retry is explicit and requires a new attempt ID.
  The Phase 5 production-promotion block is preserved.
- P6-T3 adds `tests/identity_restoration/interface/test_candidate_v3_frontend.py`
  and validates redaction, scope separation, approval gating, base
  regeneration, retry/new-attempt behavior, and IDs-only client payloads.
  CandidateV3 service/API results expose only the safe additive frontend
  projection of scope evidence.

The Phase 6 work is CPU/code-only: no physical GPU execution, provider, or
network call was needed. Candidate v3 remains feature-gated `OFF`, production
promotion remains blocked, v2/v2.1 and architecture remain unchanged, and
Phase 7 was not started. Candidate v3 identity regression is `323 passed`;
compileall and all identity schemas pass.

## 2026-08-27 — Candidate v3 Phase 5 closure

Phase 5 — Service, bridge, and API integration is `CLOSED / PASS`. The
minimal execution order was P5-T1 → P5-T2 → P5-T3.

- P5-T1 composes the approved ScenarioAuthority/IdentityPack authorities,
  CPU FaceObservability and route policy, canonicalization, Candidate v3
  bridge, Phase 4 inverse composite/split QC, Manifest 1.4, and terminal job
  transition. Microface and other non-eligible routes stop before the bridge.
- P5-T2 adds a canonical `512x512` bridge result contract, pinned workflow
  lineage validation, atomic persistent job records, deterministic request
  fingerprints, same-request replay, cancellation, new-attempt retry, and
  orphan recovery. The existing v2 job/service path was not changed.
- P5-T3 adds an authenticated API façade with ID/status/route-only redacted
  responses. Cancel and retry are controlled actions; production promotion is
  explicitly rejected because Phase 5 does not authorize promotion.

The mocked end-to-end tests cover eligible, microface, validation failure,
cancellation, duplicate retry, and orphaned job paths, plus bridge lineage
failure and API authorization/redaction. Candidate v3 identity regression is
`318 passed`; all identity schemas and Python compileall pass. No Phase 6
work was started. Locked Phase 1–4 authority IDs/versions/hashes remain
unchanged; Candidate v3 remains feature-gated `OFF`; v2/v2.1 and architecture
remain unchanged; GPU calls `0`; provider/network calls `0`.

## 2026-08-27 — Candidate v3 Phase 4 closure

Human authority approved `BOUNDARY-B`: a symmetric 3 px seam ring around the
full-canvas editable-mask edge, 8-connected Euclidean geometry, image-border
portions ignored, and feathering unable to redefine the hard boundary. The
approved thresholds are max-channel `32/48`, mean seam `12/20`, normalized
Sobel texture discontinuity `0.25/0.40`, and exact-zero outside-mask pixel
lock. The policy is `restoration-v3-quality-policy-1@1.0`, approved by Harry
Pham on `2026-08-27`, with SHA-256
`49ff52fd48147c10ecd4076a9e0995bfa3eae2162010a483cef377f1066f2025`.

Phase 4 — Composite and split QC is `CLOSED / PASS`:

- P4-T1 inverse-composites only through the verified `CanonicalFaceTransform`,
  intersects inverse-warped editable masks with the full-canvas mask, applies
  feathering only inside that approved intersection, and retains exact
  outside-mask pixel lock.
- P4-T2 implements the approved boundary metrics and independent
  `FACE_LOCAL`, `BOUNDARY`, and `SCENARIO_GLOBAL` scopes. `QualityBundleMerger`
  is fail-closed with precedence `FAIL > UNVALIDATED > NEEDS_REVIEW > PASS`;
  missing scenario binding is `UNVALIDATED` and exclusions cannot waive local,
  boundary, or correctness gates.
- P4-T3 writes immutable QC reports once, appends QC history without rewriting
  prior entries, and emits additive Manifest 1.4 quality-policy/report/history
  evidence with a validating schema.

Focused Phase 4 and relevant Candidate v3 tests pass; the identity suite is
`313 passed`. Python compileall and Manifest 1.4 schema validation pass. No
provider/network or GPU execution occurred; Candidate v3 remains feature-gated
`OFF`; v2/v2.1 and architecture remain unchanged; Phase 5 was not started.

## 2026-08-27 — Candidate v3 Phase 4 authority blocker

Phase 4 — Composite and split QC is `BLOCKED / HUMAN DECISION REQUIRED` before
implementation. The authoritative roadmap defines inverse composite, hard
pixel lock, boundary ownership, three QC scopes, and the fail-closed merger,
but does not define the seam-ring geometry, boundary seam/color/texture
thresholds, boundary status mapping, or the contents/hash of the named
`restoration-v3-quality-policy-1`.

These are materially behavioral PASS/FAIL policy values and cannot be derived
from the existing exact pixel lock or the necessary-but-not-sufficient Face-QC
score of `90`. A single decision pack was created at
`docs/Image studio/candidate_v3_phase4_quality_authority_decision.md`.
P4-T1, P4-T2, and P4-T3 remain `NOT STARTED`; no Phase 4 code, schema,
manifest, provider, GPU, v2/v2.1, or prior-phase change was made.

Candidate v3 remains feature-gated `OFF`; Phase 3 remains `CLOSED / PASS`;
GPU calls `0`; provider/network calls `0`.

## 2026-08-27 — Candidate v3 Phase 3 closure

Phase 3 — Candidate v3 workflow adapter is `CLOSED / PASS`. The minimal
sequential decomposition was executed completely:

- P3-T1 — pinned Candidate v3 workflow artifact: duplicated the active v2
  graph into `face_restore_win_sd15_ipadapter_v3.api.json`, added the declared
  semantic titles, changed only the v3 output crop to canonical `512×512`, and
  pinned SHA-256
  `53dc090691b8feac2a8b8a4309d43af737e304b09330e072b4ab5632ed5aad91`.
- P3-T2 — graph contract and adapter: added exact title/type/cardinality
  validation, strict declared-input binding, `ComfyUiCandidateV3Adapter`
  behind `RestorerRegistry`, canonical 512×512 input/output enforcement,
  workflow/config/reference/model/GPU/timing evidence, and explicit GPU
  authorization fail-closed behavior.
- P3-T3 — closure validation: added CPU fake-backend contract tests and
  verified feature-flag registration, graph binding, malformed graph,
  geometry, health, lease, cancel, OOM mapping, schema, layering, and legacy
  workflow boundaries.

Execution order was P3-T1 → P3-T2 → P3-T3. Candidate v3 remains feature-gated
`OFF`; even an explicitly enabled configuration registers the adapter with GPU
execution authorization `false` unless a caller supplies explicit authority.
The active v2 workflow SHA remains unchanged and no Phase 4 work was started.
Candidate v3 identity tests passed `308`; the full repository run passed `1338`
with the known `77` unrelated legacy baseline failures. Python compileall and
both diff checks passed. GPU calls `0`; provider/network calls `0`.

## 2026-08-27 — Candidate v3 P1-T2 authority closure

Closed Candidate v3 Phase 1 authority work: P1-T2A, P1-T2B, and P1-T2C are
`CLOSED / PASS`, so P1-T2 is `CLOSED / PASS`. The deterministic audit and
closure gate verify the locked B01–B10 dataset at 10/10 approved and resolved,
with zero unmatched, unexpected, duplicate approved, missing profile, SHA
mismatch, or invalid exclusion findings.

B03/B04 remain explicitly bound to `action_full_body@1.0`, excluding only
`shot_distance` and `hairstyle`; B01/B02/B05–B10 remain bound to
`canonical_default` with no exclusions. Profile hashes are recomputed from
raw source bytes. Fail-closed audit tests cover missing/unexpected/duplicate/
missing-profile/tampered-SHA/invalid-exclusion/RETIRED cases, determinism, and
non-mutation.

Candidate v3 remains feature-gated `OFF`; v2/v2.1 behavior was not modified;
GPU calls `0`; provider/network calls `0`. No runtime QC integration, GPU job,
provider call, browser job, benchmark generation, or image generation was run.

## 2026-08-27 — Candidate v3 P2-T3-B2 crop padding semantics decision pack

P2-T3-B2 is now `CLOSED / PASS`; P2-T3 is `READY / NOT STARTED`; P2-T4 is
`NOT STARTED`. The approved transform authority supplies the scalar crop
padding ratio `0.20`, and human authority has now fixed its exact CP-B
interpretation and the associated out-of-bounds, transform-order, and
rasterization semantics.

The decision pack
`docs/Image studio/candidate_v3_phase2_crop_padding_semantics_decision.md`
records the prior evidence classification as `ABSENT` for the Candidate v3
convention and records the approved CP-B (square maximum dimension, per-side),
OOB-A, TO-A, and deterministic rasterization rule.
No crop implementation, executable configuration, schema mutation, feature-flag
change, v2/v2.1 change, GPU call, or provider/network call was made.

### P2-T3-B2 — Crop Padding Semantics Approval (2026-08-27)

- Result: `CLOSED / PASS`; P2-T3 is `READY / NOT STARTED`; P2-T4 is
  `NOT STARTED`.
- Human authority approved CP-B: square crop centered on the face bbox center,
  with side `1.40 × max(face_bbox_width, face_bbox_height)` (`0.20` per side).
- OOB-A is approved: preserve requested crop bounds, synthesize missing pixels
  with `REFLECT_101`, and do not clamp or shrink. TO-A is approved: source
  image → padded square crop → canonical `512×512` alignment.
- Continuous float bounds use deterministic `floor(min) / ceil(max)` raster
  bounds; the resulting extent, crop origin, and geometry are shared by image,
  binary mask, feather mask, and landmarks.
- Approval is recorded in
  `docs/Image studio/candidate_v3_phase2_crop_padding_semantics_decision.md`
  by Harry Pham on `2026-08-27`. No implementation, executable configuration,
  schema, feature-flag, v2/v2.1, GPU, or provider/network change was made.

## 2026-08-27 — Candidate v3 Phase 2 closure

Phase 2 is `CLOSED / PASS`. P2-T1, P2-T2, P2-T3-B1, P2-T3-B2, P2-T3, and P2-T4
are all `CLOSED / PASS`. P2-T3 implements the approved
`candidate_v3_canonical_transform_policy` v1.0 with policy SHA-256
`ebe134ca42cfc3066c24c04299e005f4a389c4037f57267201ceb2ff96d941c9` and the
`candidate_v3_face_template` v1.0 with template SHA-256
`de9d7616686086dbd217b1fbdb65c9c890a3e0bd086c4507328ba77562d96600`.

The CPU-only implementation uses 512×512 CP-B square crop semantics, 20%
padding per side, face-bbox center, OOB-A `REFLECT_101`, TO-A crop-first
ordering, deterministic `floor(min) / ceil(max)` rasterization, shared image
and mask geometry, `LANCZOS4`/`NEAREST`/`LINEAR` mask modes, binary threshold
`0.5`, and landmark round-trip limit `0.5 px`. Inverse artifact mapping and
lineage hashes are implemented and fail closed on tamper, invalid route,
invalid geometry, mask mismatch, and non-finite evidence.

The bounded Candidate v3 suite passed `303 tests`. Observability, route
determinism, canonical geometry, coordinate/mask properties, B05/B06 routes,
and B10-like non-eligible routing all pass. Candidate v3 remains feature-gated
`OFF`; v2/v2.1 is unchanged; GPU calls `0`; provider/network calls `0`. No
Phase 3 task was created or started. Full repository failures were unrelated
legacy fixture/environment failures outside this bounded context.

## 2026-08-27 — Candidate v3 Phase 2 approved decomposition

Phase 2 is `IN PROGRESS`; P2-T1 is `CLOSED / PASS`; P2-T2-B1 is `BLOCKED`, and
P2-T2 remains `BLOCKED / NOT STARTED`. P2-T3 and P2-T4 remain not started. The
minimal executable order is P2-T1 → P2-T2 → P2-T3 → P2-T4, directly matching the
authoritative Phase 2 bullets in
`docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md`.

### P2-T2-B1 — Calibration Authority Lock (2026-08-27)

- Result: `BLOCKED`. The frozen B05/B06/B10 geometry manifests contain
  deterministic YuNet measurements, but B05/B06 have no authoritative route
  labels. No general microface/recoverability, extreme-pose, landmark-
  uncertainty, or positive-`ELIGIBLE` threshold is pinned in the repository.
- Invalid input and multiple-face review are authoritative from the Candidate v3
  roadmap. B10-like behavior is authoritative as non-`ELIGIBLE` / base
  regeneration, but does not establish a general boundary.
- No executable policy config, route evaluator, calibration test, fixture
  mutation, GPU/provider/network call, feature-flag change, or v2/v2.1 change
  was made.
- Evidence report:
  `docs/Image studio/candidate_v3_phase2_route_calibration.md`.

### P2-T2-B2 — Human Calibration Approval (2026-08-27)

- Result: `CLOSED / PASS`. Human authority approved B05 and B06 as
  `ELIGIBLE_IF_ALL_POSITIVE_RULES_PASS`, B10 as `BASE_REGEN_REQUIRED`, M-B
  (`face_area_ratio <= 0.0030488715`), P-A (`abs(yaw) >= 79.361665°`), and
  L-A (exactly five finite landmarks and positive interocular distance).
- The approved positive contract is E-A: structurally valid input, exactly one
  eligible face, valid detector/config pin, confidence, bbox, five finite
  landmarks, positive interocular distance, finite measurements, valid mask
  relation, face area ratio above `0.0030488715`, absolute yaw below
  `79.361665°`, and no unresolved ambiguity.
- Approved policy is `candidate_v3_route_policy` version `1.0`, approved by
  Harry Pham on `2026-08-27`:
  `docs/Image studio/candidate_v3_phase2_human_calibration_decision.md`.
- `P2-T2-B1 = BLOCKED / evidence exhausted`; `P2-T2-B2 = CLOSED / PASS`;
  `P2-T2 = READY / NOT STARTED`; P2-T3 = `NOT STARTED`.
- This is policy authority only: no executable policy, route evaluator,
  implementation change, fixture mutation, GPU/provider/network call,
  feature-flag change, or v2/v2.1 change was made.

### P2-T2 — Deterministic Route Policy Implementation (2026-08-27)

- Result: `CLOSED / PASS`. Added the server-owned immutable policy config at
  `identity_restoration/config/candidate_v3_route_policy_v1.json` with policy
  ID `candidate_v3_route_policy`, version `1.0`, and SHA-256
  `171019b8fcf62449b3f5d6af37372f9861eb80bd21a7b621ae89c760199fdb33`.
- The pure evaluator at
  `identity_restoration/domain/policies/candidate_v3_route_policy.py` consumes
  only P2-T1 `FaceObservability`; policy file loading is isolated in the
  application layer. It performs no detector, I/O, network, provider, or GPU
  work during evaluation.
- Route precedence is invalid input → `REJECTED_INVALID_INPUT`, microface
  (`face_area_ratio <= 0.0030488715`) → `BASE_REGEN_REQUIRED`, unresolved
  multiple-face/extreme pose (`abs(yaw) >= 79.361665`) → `REVIEW_REQUIRED`, and
  explicit all-pass positive proof → `ELIGIBLE`.
- B05 and B06 route `ELIGIBLE` when all positive rules pass; B10 routes
  `BASE_REGEN_REQUIRED`, with microface taking precedence over extreme pose.
  Route results are immutable, schema-valid, measurement-linked, and decision
  hash-pinned with stable reason ordering.
- Focused P2-T2/P2-T1/schema/feature-flag tests passed (`72 passed` with
  layering); compileall passed; `git diff --check` passed. Phase 2 remains
  CPU-only with Candidate v3 feature flag `OFF`, v2/v2.1 unchanged, GPU calls
  `0`, and provider/network calls `0`.
- `P2-T3 = READY / NOT STARTED`; `P2-T4 = NOT STARTED`. No canonical transform,
  production cutover, QC scoring, GPU workflow, provider, or ComfyUI execution
  was added.

### P2-T3-B1 — Canonical Transform Authority Decision Pack (2026-08-27)

- Result: `HUMAN DECISION REQUIRED`; P2-T3 remains `BLOCKED / NOT STARTED` and
  P2-T4 remains `NOT STARTED`.
- Repository audit confirms the authoritative P2-T3 facts are canonical size
  `512×512`, image padding `REFLECT_101`, image interpolation `LANCZOS4`, and
  the P2-T1 landmark order. No authoritative five-point target template
  coordinates/ID/version/hash, crop padding ratio/policy hash, binary/feather
  mask interpolation policy, or floating-point round-trip tolerance exists.
- Existing integer `CropTransform` exact round-trip and pixel-lock tolerance
  `0` are not substitutes for a canonical similarity-transform tolerance. The
  existing QC `2.0` values are not transform authority.
- Decision pack created at
  `docs/Image studio/candidate_v3_phase2_transform_authority_decision.md`.
  It records evidence-only facts and human placeholders with status `PENDING`.
- No transform code, executable transform policy, schema mutation, production
  integration, feature-flag change, v2/v2.1 change, GPU call, or
  provider/network call was made.

### P2-T3-B1 — Canonical Transform Authority Approval (2026-08-27)

- Result: `CLOSED / PASS`; P2-T3 is now `READY / NOT STARTED` and P2-T4
  remains `NOT STARTED`.
- Human authority approved template `candidate_v3_face_template` v1.0 on a
  512×512 canvas with points `(192,208),(320,208),(256,272),(208,336),
  (304,336)`, crop padding ratio `0.20`, mask modes image `LANCZOS4`, binary
  `NEAREST`, feather `LINEAR`, binary threshold `0.5`, and landmark-point max
  Euclidean round-trip limit `0.5 px`.
- Approved transform policy identity is
  `candidate_v3_canonical_transform_policy` version `1.0`. Policy contents and
  its derived SHA-256 must be created and verified by P2-T3 implementation.
- Approval only unblocks implementation; no transform code, executable policy,
  schema mutation, production integration, feature-flag change, v2/v2.1
  change, GPU call, or provider/network call was made.

### P2-T1 — FaceObservabilityService / CPU observability contract

- Objective: normalize EXIF orientation and color space, run the pinned
  detector/version, and emit schema-compatible `FaceObservability` evidence.
- Inputs: immutable image bytes, editable-region mask, pinned detector/config,
  and measurement-config hash.
- Outputs: face count, bbox and dimensions, five-point landmark confidence,
  interocular distance, pose, border clipping, sharpness, occlusion, quality
  tier, and deterministic measurement evidence.
- Likely modules: `contracts/identity_restoration/face_observability_v1.schema.json`,
  `identity_restoration/domain/` or `application/`, a detector port/adapter,
  and focused CPU tests.
- Prerequisites: Phase 1 authority closure and a pinned detector/version plus
  versioned measurement configuration.
- Required tests: repeated-input determinism; malformed/no-face/multiple-face;
  low-confidence detection; invalid bbox/landmarks; target outside editable
  region; schema validation.
- Fail closed: malformed input, no eligible face, low detector confidence,
  invalid measurements, or unresolved target association cannot produce an
  eligible observation.
- DoD: complete deterministic observation evidence is emitted without GPU,
  provider, network, or production-runtime integration.
- Non-goals: route decisions, canonical warping, model execution, QC scoring,
  threshold tuning, and feature-flag changes.

### P2-T2 — Deterministic route policy

- Objective: map observability and input validity to a versioned `RouteCode`
  and serialized first/all applicable reasons.
- Inputs: P2-T1 observation, input/mask validity, and a versioned calibrated
  policy with its SHA-256.
- Outputs: `ELIGIBLE`, `REVIEW_REQUIRED`, `BASE_REGEN_REQUIRED`, or
  `REJECTED_INVALID_INPUT`, with deterministic reasons and policy evidence.
- Likely modules: `identity_restoration/domain/policies/`, Candidate v3 route
  DTO/contract, and route-policy tests.
- Prerequisites: P2-T1; locked calibration examples including B05, B06, and a
  B10-like case must be available to the policy work.
- Required tests: precedence and repeatability for malformed/no-face,
  unrecoverable microface, multiple candidates, extreme pose, uncertain
  landmarks, and eligible input.
- Fail closed: malformed/no-face/invalid-mask input routes to rejection;
  below-threshold information routes to base regeneration; ambiguity routes
  to review; no implicit eligible fallback is allowed.
- DoD: route and reasons are reproducible, version/hash-pinned, and serialized
  without allocating GPU or calling a provider.
- Non-goals: base-image generation, GPU routing, production cutover, and
  score-based promotion.

### P2-T3 — Canonical face transform and mask mapping

- Objective: implement the roadmap's canvas-space → padded crop → five-point
  similarity alignment → 512×512 model-space mapping and verified inverse.
- Inputs: P2-T1 landmarks, immutable source image, editable/feather masks,
  calibrated crop padding, and the fixed 512×512 template.
- Outputs: `CanonicalFaceTransform`, canonical image and both masks, inverse
  mapping, artifact hashes, and round-trip verification evidence.
- Likely modules: `contracts/identity_restoration/canonical_face_transform_v1.schema.json`,
  `identity_restoration/application/dto/candidate_v3.py`,
  `identity_restoration/domain/`, geometry/mask policies, and CPU transform tests.
- Prerequisites: P2-T1 observations and P2-T2 `ELIGIBLE` route; fixed
  interpolation `LANCZOS4` and border mode `REFLECT_101`.
- Required tests: matrix invertibility, landmark/template mapping, reflected
  border padding, identical image/mask transforms, dimension/hash agreement,
  and inverse round-trip error.
- Fail closed: weak landmarks, invalid matrix/condition number, out-of-bounds
  target mapping, excessive round-trip error, mask mismatch, or silent resize/
  aspect-ratio distortion.
- DoD: transform and masks are schema-valid, deterministic, hashable, and
  verified entirely on CPU.
- Non-goals: restoration model/workflow, ComfyUI, compositing production
  integration, QC evaluation, and GPU execution.

### P2-T4 — CPU fixtures, property validation, calibration, and closure gate

- Objective: validate the complete Phase 2 path on a fixed labelled CPU-only
  fixture set and calibrate/version/hash thresholds without tuning only on
  passing examples.
- Inputs: P2-T1/T2/T3 outputs and fixtures for microface/B10-like, multiple
  faces, border clipping, profile/extreme pose, blur, invalid landmarks, and
  EXIF orientation.
- Outputs: reproducible fixture/property test results, versioned calibration
  policy and hash, deterministic route evidence, and the Phase 2 closure
  report.
- Likely modules: `tests/identity_restoration/`, `identity_restoration/domain/`
  policy tests, calibration/config storage, and the existing Candidate v3
  feature-flag tests.
- Prerequisites: P2-T1, P2-T2, and P2-T3 all locally validated; no live
  benchmark or provider prerequisite.
- Required tests: all named fixtures; coordinate/mask property tests;
  transform round-trip; repeated-run determinism; feature flag remains OFF;
  and regression checks showing v2/v2.1 files and behavior are unchanged.
- Fail closed: any property failure, nondeterminism, missing evidence, or
  B10-like fixture proceeding as normal restoration blocks Phase 2 closure.
- DoD: no GPU dependency; coordinate/mask properties PASS; every named fixture
  routes deterministically; B10-like input does not proceed as normal
  restoration; closure gate records zero provider/network calls and unchanged
  v2/v2.1 behavior.
- Non-goals: GPU jobs, providers, image generation, workflow adapter,
  production integration, quality-score tuning, or advancing Phase 3.

## 2026-08-27 — Candidate v3 P2-T1 implementation closure

P2-T1 is `CLOSED / PASS`; Phase 2 is `IN PROGRESS`. P2-T2 is now
`READY / NOT STARTED`; P2-T3 and P2-T4 remain `NOT STARTED`. The implementation
stays inside the existing Python `identity_restoration` bounded context and
does not alter v2/v2.1 execution.

Added the CPU-only `FaceObservabilityService` and immutable evidence DTO. It
normalizes EXIF orientation before RGB decoding, hashes raw image/mask bytes,
validates mask dimensions and grayscale semantics, preserves all detector
candidates for multiple-face observation, validates bbox/landmarks/confidence,
and measures bbox/mask intersection, overlap ratio, mask coverage, and center
containment. It emits no P2-T2 route code.

The concrete adapter uses the existing pinned YuNet authority: OpenCV
`FaceDetectorYN`, method `opencv-zoo-yunet-2023mar-pnp-v1`, model
`face_detection_yunet_2023mar.onnx`, model SHA
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`, input
`320×320`, confidence `0.6`, and NMS `0.3`. Detector configuration and
measurement content are canonical-hash pinned; mismatches fail closed.

The observability contract and Candidate v3 result schema now carry image/mask
identity, detector/config hashes, selected/all detections, measurements,
validity state, machine-readable failure reasons, and measurement SHA. Focused
P2-T1/schema/Phase 0 validation passed: `40 passed`; compileall and
`git diff --check` passed. GPU calls `0`, provider/network calls `0`, and the
Candidate v3 feature flag remains `OFF`.

## 2026-08-27 — Growth Agent v3.1 reliability repair (steps 1–6)

Completed and pushed the six-step Growth Agent repair across `venho-ai-studio`
and `venho-os`. Weekly generation now checkpoints partial Registry state even
when a provider fails; Claude requests retry transient 429/5xx/529/transport
errors per content item with bounded jitter; rejected and stale approvals get
fresh drafts in the same or nearest future OPEN slot; and the Registry enforces
one active publication per `(slot_id, platform)` to prevent duplicate posts and
images. VENHO OS now reads the Git-backed Registry as source of truth and
separates the approval queue, publishing incidents, and audit history.

Google Drive uploads retry transient TLS/connection failures before falling
back to the rotated hotel image. Make posts that report `PUBLISHED` without a
Post ID can be reconciled from the Dashboard without re-sending the webhook.
The Dashboard Registry sync was also hardened against `spawnSync gh ENOBUFS`
by increasing GET buffer capacity and suppressing the large PUT response body.

Commits pushed: AI Studio `2dcd6f6`; VENHO OS `5225d63` (plus prior step
commits `a8d688e`, `6a3218b`, `64df499`, `3470f14`, `1d408c2`, `fff7f02`).
Validation: AI Studio focused Growth tests passed; VENHO OS Vitest 450/450 and
TypeScript passed. Runtime Registry changes from the approval action are
preserved in this checkpoint.

## 2026-08-27 — GW-P7-T3-R1 evidence lineage repair and final closure

Repaired the proven metadata-only lineage defect for candidate
`comfyui-remote-face_restore_win_sd15_ipadapter_v2`. Source Run 6
`benchmark-20260825T160000Z-gw-p4-t1` → GW-P7-T1 report
`de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6` → T2
classification `d2379e39c562e742c47e9546210bc302bcdae81ce17764aea7f7b987334a8f5c`,
whose source SHA field had the transposed value
`de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99cf4bf37632ee90b14d6`.
→ physical smoke manifest
`0b8b09647b32573df1db61e67f454422819920b342c6a036e784da4bded20c2d`.

The immutable post-remediation benchmark remains 30/30 valid with 8 quality
passes and 22 deterministic `RC1_TRUE_OUTPUT_QUALITY_FAILURE` rows; no RC2–RC5
defect is evidenced. Regional gate is `FAIL`, so the candidate is
`REJECTED_QUALITY`. Physical HARRY-ROG smoke remains `PASS` and is preserved as
runtime evidence only; it cannot promote a failed regional candidate.

Safe-default audit found no regression: AI Studio selection is
environment-controlled with version-controlled `mock` fallback,
`comfyui-remote` is opt-in, and `IDR_DEFAULT_RESTORER=comfyui-local` remains a
one-step rollback setting. VenHo OS RestorerSelector defaults to explicit
`none`; GPU selection requires conscious user action. Promotion policy remains
human-only and the registry records `BLOCKED` / `NOT_REQUESTED`.

Created corrective artifact
`artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json`
with SHA
`15d2afde5310e1cbcb4c6317f5eb8d6335d9deeb0a6641e59d33203fa8986834`.
The original T2 classification and all historical evidence remain immutable.
T3-R1 made no production-behavior, workflow, model, A2, QC-threshold, benchmark,
GPU, provider, or historical-evidence changes. Offline targeted tests,
compile/type/lint checks, registry/promotion checks, and diff checks were run;
execution counts for T3 are GPU jobs `0`, provider calls `0`, production
promotions `0`, new benchmark runs `0`, and new production candidates `0`.
The corrected evidence chain is PASS; GW-P7 closes as quality fail with no
promotion.

## 2026-08-26 — GW-P7-T1 production evidence & registry reconciliation

Run 6 (`benchmark-20260825T160000Z-gw-p4-t1`) was reconciled against the
GW-P4-R1 authority-only profile using cached validator observations only. The
immutable post-remediation artifact is
`artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/`
(`reportSha256=de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`).
Generation, workflow, seed, A2 lineage, and original Run 6 files were
unchanged; provider calls and GPU jobs are zero. The replay remains
`QUALITY_FAIL`: 30/30 decision-valid rows, treatment median `91.335`,
regionalHealthy false, anatomy and pixel-preservation true, 22 quality fails
and 8 passes.

Created the minimum auditable `PRODUCTION_REGISTRY.md`. The canonical
`comfyui-remote` candidate is recorded `QUALITY_FAIL / BLOCKED`, with human
approval not requested and no official-production state. The stale B01 remote
smoke is classified `CURRENT_ARTIFACT_NOT_PHYSICALLY_PROVEN` because the
manifest SHA (`f30a1ee4...15ce4b1`) differs from the current mutable artifact
(`919e20a8...08fa7be9`); the manifest was not rewritten and original bytes were
not recoverable from immutable evidence.

GW-P7-T1 is blocked by the measured regional quality failure and missing
physical proof of the remote smoke artifact. No production behavior changed;
all validation was offline/read-only.

## 2026-08-26 — GW-P6 human approval and phase closure

Human `APPROVE` was executed through the existing VENHO OS action API/service
for job `job-1787733824684-fzrqsi`, without directly editing the JSON record.
Disk reload confirms `decision=APPROVED` on the same Attempt 2
(`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc`), attempt count remains 2,
and Manifest 1.3/EvidencePanel authority remains Gemini / 91.05 / approved /
no-kill / Pixel Lock PASS. All prior attempt, failure, mock, transient, and
Q7-R2/Q7-R3 evidence remains preserved.

No provider, network, GPU, restoration, new attempt, or QC cycle occurred;
ledger remains unchanged at `23/24` with one call reserved. Offline approval,
reload, manifest, EvidencePanel, no-direct-ComfyUI, typecheck, compile, lint,
and diff checks pass. GW-P6 is closed `CLOSED / PASS`; GW-P7 is ready but not
started.

## 2026-08-26 — GW-P6 Q7-R3 offline persistence/promotion repair

Audited the durable Attempt 2 record before repair. The authoritative Gemini
aggregate was present in `StudioJobRecord` (`result.qc`, attempt evidence, and
restoration evidence): provider `gemini`, `samples=3`, `faceScore=91.05`, all
validators approved, kill switch false, and quality acceptance eligible. The
historical mock marker and earlier validation records were retained; no missing
Q7-R2 cycle ID or sample checkpoints were recreated.

The first failing boundary was `enrichExistingManifest13Qc`: it treated any
existing QC object as an idempotency lock, so stale mock QC prevented promotion.
The repair adds deterministic authoritative selection and same-attempt offline
promotion. A valid authoritative Gemini QC now supersedes stale/non-authoritative
QC, while prior QC remains in `qcHistory`; the EvidencePanel reads the explicit
`currentAuthoritativeQc` field. Manifest 1.3 was repaired and reloaded with the
authoritative Q7-R2 values (`91.05`, approve, no kill, Pixel Lock PASS).

No provider, network, GPU, new attempt, or ledger mutation occurred. Ledger is
unchanged at `23/24` (one remaining). Q7-R2 cycle/checkpoint absence remains a
non-blocking historical audit gap because the aggregate itself is durable and
acceptance-sufficient. Q7-R3 is `PASS`; GW-P6 quality gate is passed and awaits
human review. GW-P7 remains not started.

## 2026-08-26 — GW-P6 Q7-R2 authoritative QC cycle (blocked on persistence contract)

Executed exactly one authenticated production `validate-existing` request for
Attempt 2 (`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc`) through the VENHO OS
API → RestorationBridge → `venho-restore validate` → ValidatorStudio → Gemini
path. The cycle used provider `gemini`, model `gemini-3.5-flash`, and exactly
three logical samples with one transport request each; no retry, restoration,
GPU job, or ComfyUI submission occurred. Ledger accounting is append-only and
now `23/24` (three Q7-R2 provider requests consumed; one reserved; no bypass).

The live aggregate is numerically and semantically passing: `faceScore=91.05`,
all binary validators approved, `killSwitchTriggered=false`,
`qualityAcceptanceEligible=true`, Geometry PASS, and Pixel Lock PASS. The
restored crop remains byte-different from the input and the authority hashes
remain unchanged. However, the production validate-existing path persisted no
`QC_CYCLE_ID` or per-sample durable checkpoints/evidence sink, and the
Manifest 1.3 enrichment short-circuited because an older QC object already
existed. Therefore Q7-R2 cannot claim the required persistence/reload or
EvidencePanel authority contract. This is a persistence-contract blocker, not
a provider-quality failure. No second cycle or rerun is permitted under the
authorization.

## 2026-08-26 — GW-P6 Q7-R1 production QC authority hardening

Q7-R1 completed offline only. VENHO OS `.env.local` now persists
`IDR_QC_ENABLED=true`, `IDR_QC_PROVIDER=gemini`, and `IDR_QC_SAMPLES=3` beside
the existing server-only Gemini credential resolution; no secret was printed,
committed, exposed to the client, or passed in argv. The composition boundary
now returns structured `QC_AUTHORITY_UNAVAILABLE` for required validation when
QC is disabled or the provider is not Gemini. Explicit mock remains available
for unit/offline paths, but its source authority is marked
`authority=non-authoritative` / `qualityAcceptanceEligible=false`, and the
promotion policy rejects it regardless of numeric score.

The invalid Q7 mock result on Attempt 2 was preserved and classified in-place
as `MOCK_CONFIGURATION_FAILURE`; historical evidence was not deleted or
overwritten. Existing-artifact selection ignores explicitly non-authoritative
mock QC while retaining legacy records without provenance. Offline Q7-R1
matrix and Q3/Q6 regressions pass. No provider, network, GPU, restoration,
Attempt 3, or ledger mutation occurred. Ledger remains 20/24 (4 reserved).
Next is the separately authorized GW-P6 Q7-R2 authoritative Gemini cycle.

## 2026-08-26 — GW-P6 Q7 blocked before authoritative provider cycle

Q7 authorization was recorded append-only on the Validator ledger, extending
the ceiling from 21 to 24 with consumed count unchanged at 20 (remaining 4;
GPU authorization false). Pre-gates for Attempt 2 lineage, workflow/A2 hashes,
Geometry, Pixel Lock, byte-different crop, bridge, CLI JSON, and server/child
secret presence passed. The first unauthenticated API probe was rejected by
the VENHO OS proxy (401) before route execution and made no cycle or provider
request.

One authenticated production `validate-existing` request then ran through the
VENHO OS API → RestorationBridge → `venho-restore validate` path, but the
fresh process did not carry `IDR_QC_ENABLED=true` and
`IDR_QC_PROVIDER=gemini`. The composition root therefore selected the default
mock gateway. It returned `provider=mock`, `samples=1`, `faceScore=88`,
`verdict=revise`; no Gemini transport occurred and the ledger remained 20/24.
This result is invalid for Q7 and is recorded only as a configuration
blocker—not authoritative quality evidence. No restoration, GPU, ComfyUI,
Attempt 3, second QC cycle, or provider retry was made. Q7 is closed
`BLOCKED / MOCK_QC_CONFIGURATION`; do not rerun under this authorization.

## 2026-08-26 — GW-P6 Q6 offline transient provider hardening

Implemented prospectively at the existing Gemini transport/evidence boundary;
no live provider, network, GPU, QC cycle, restoration attempt, or ledger
mutation occurred. Each logical Validator sample now has a strict maximum of
two transport attempts. Only `PROVIDER_503`, `PROVIDER_429`, and
`PROVIDER_TIMEOUT` are retryable, with deterministic 0.25s linear backoff;
schema/parser/QC/rejection/DTO failures are not retried. `PaidCallGuard` runs
before every request, including a retry, preserving paid-call accounting.

`samples=3` semantics are unchanged: retrying sample 2 retains logical sample
index 2, failed transports are excluded from aggregation, and an exhausted
retry closes the cycle without an aggregate. The existing raw evidence sink
now receives sanitized transport diagnostics (cycle/sample/transport-attempt,
attempt ID, provider, model, timestamps, status, parse/schema state, finish
reason, token usage, and error code) plus a parsed `checkpointed=true` observation before the next
sample starts. Cycle IDs are generated per validation call or accepted via
`validation_cycle_id`; Q4 remains non-resumable and no cross-cycle evidence is
fabricated or mixed.

`ValidatorStudioQcGateway` can pass the existing evidence sink and cycle ID;
source authority projection remains unchanged and additive. Added
`tests/test_q6_transient_provider_hardening.py` covering first-try success,
503 retry success/exhaustion, non-retryable no-retry, ledger blocking before a
retry, and durable logical-sample transport events. Q6 focused tests and
existing Q5/Q3 regressions pass; Python compile and `git diff --check` pass.

Ledger remains consumed `20`, authorized max `21`, remaining `1`. For a future
authorized live cycle, recommend four new calls (`AUTHORIZED_MAX=24`): three
normal logical samples plus one bounded transient retry. Do not authorize or
run it in Q6. Next is GW-P6 Q7 final authoritative three-sample QC cycle.

## 2026-08-26 — GW-P6 Q5 offline provider-resume / 503 forensics

Q4's single authorized 3-sample validation cycle consumed calls 19 and 20 of
the `18 -> 21` ceiling: sample 1 completed, sample 2 returned `503 UNAVAILABLE`,
and sample 3 was not called. No aggregate report was produced. The ledger
records transport metadata only (`callNumber`, `sampleIndex`, model/tokens or
error); Q4 sample 1 has no parsed observation, source verdict/kill-switch, or
other authority payload persisted in the StudioJobRecord, Manifest 1.3,
ValidatorStudio evidence, or a raw/parsed evidence path.

Offline code tracing confirms `ValidatorStudioQcGateway.validate` calls
`validate_face(samples=3)`, whose `_observe_face` appends successful
`FaceValidationObservation` values to a process-local list and invokes
`_merge_face_samples` only after all samples return. The gateway does not wire
`raw_response_sink`. A sample-2 exception therefore discards sample 1 when the
invocation exits; the current implementation has no sample checkpoint or
resume path. Q4 classification is **C — SAMPLE_1_NOT_PERSISTED; FULL 3-SAMPLE
RESTART REQUIRED**.

`classify_gemini_failure(RuntimeError("503 UNAVAILABLE"))` returns
`PROVIDER_503`; it is transport-retryable in classification, but current
production policy has no automatic or bounded retry. One request is issued per
sample and any exception aborts the whole aggregate. Under current contracts,
retrying sample 2 is a **new QC cycle**, not continuation; mixing it with Q4
sample 1 would change the locked three-sample statistical meaning. Consumed
ledger is `20`, authorized max `21`, remaining `1`; a fresh internally
consistent cycle needs up to `3` calls and therefore a later ceiling of `23`
(`+2` authorization). Q5 did not consume the remaining call or alter the
ledger.

Transient hardening is recommended but deliberately not implemented: future
work should persist sanitized per-sample events before/after transport and
define a separately authorized bounded retry/checkpoint protocol at the
provider/evidence boundary. No provider, network, GPU, QC cycle, new attempt,
authority, denoise, or job-state mutation occurred in Q5.

Added offline regression `tests/test_q5_provider_resume_forensics.py`, which
simulates sample 1 success followed by sample 2 503 and proves no aggregate is
created while process-local sample evidence is only observable through the
optional callback. Focused tests passed: AI Studio `19` identity tests plus
`18` provider/forensics tests; VENHO OS `38`; Python compile, TypeScript
typecheck, changed-scope lint, and `git diff --check` all passed.

## 2026-08-26 — GW-P6 Q4 final QC blocked by provider 503

Q4 applied the authorized append-only ledger extension 18→21 and verified the
corrected gateway mapping, source-authority persistence code, CLI/bridge
contracts, and fresh server/child secret presence offline. One production
validation cycle was started for existing Attempt 2. Gemini sample 1 succeeded;
sample 2 returned `503 UNAVAILABLE`; sample 3 was not called. Provider calls in
Q4: 2. No aggregate report, source verdict, source kill-switch field, or
corrected projection was produced, so no QC values were fabricated or mixed
with the historical 91.05 result.

Attempt 2 remains unchanged at two attempts with prior evidence. No GPU,
restoration retry, second QC cycle, Attempt 3, approval, rejection, or GW-P7
action occurred. Next state is blocked on a separately authorized final QC
execution after provider availability is restored.

## 2026-08-26 — GW-P6 Q3 projection fixed; offline re-projection unavailable

Fixed only `ValidatorStudioQcGateway`: typed `Recommendation.APPROVE` replaces
the uppercase string comparison, and `report.kill_switch.triggered` replaces
truthiness of the Pydantic model. Rubric, gates, scoring, aggregation,
threshold, samples, Recommendation, and KillSwitch semantics remain unchanged.
Added offline regression coverage for approval, rejection, real kill switch,
and false kill-switch model truthiness.

Attempt 2 persists `faceScore=91.05` and the old projected booleans, but the
original `report.verdict`, `report.kill_switch.triggered`, per-sample
observations, and full aggregate report were not persisted. Historical manifest
verdicts are unrelated records and cannot be attributed to Attempt 2. Offline
re-projection is therefore unavailable; no values were fabricated and the same
Attempt 2 was not rewritten. Provider calls, GPU jobs, attempts, and QC cycles
remain zero for Q3. Next step requires one separately authorized final QC
verification after the mapping fix; no automatic execution or GW-P7.

## 2026-08-26 — GW-P6 Q2 authority mapping root cause found

Offline inspection of Attempt 2 (`faceScore=91.05`, Geometry PASS, Pixel Lock
PASS) found no evidence of an image-derived failure. Individual Attempt-2 raw
validator observations were not persisted; the paid-call ledger contains only
transport metadata. The aggregate score itself is decisive because
`score_face_observation` returns `overall_score=0` and a real kill switch when
any binary face gate fails; 91.05 therefore implies the merged binary gates did
not fail.

The production gateway is the remaining failure: it compares the enum
`Recommendation.APPROVE` to uppercase `"APPROVED"` even though its value is
lowercase `"approve"`, forcing `all_validators_approved=false`. It also uses
`bool(report.kill_switch)` instead of `report.kill_switch.triggered`; a
Pydantic `KillSwitch(triggered=False)` object is truthy, forcing
`kill_switch_triggered=true`. The persisted `false/true` is therefore a
VALIDATOR_CONTRACT/MAPPING_FAILURE, not a face, identity, geometry, or pixel
failure.

Acceptance remains `face_score >= threshold AND all_validators_approved AND
not kill_switch_triggered AND pixel.passed`. Face identity objective is PASS;
global validator objective is FAIL. Historical B08 (95.4) and B03 (90.6) face
reports have all binary gates true, `verdict="approve"`, and
`kill_switch.triggered=false`. Recommendation: no GPU retry; fix the authority
mapping first, then obtain separate authorization for verification. Q2 made no
provider calls, GPU jobs, attempts, QC cycles, or code changes.

## 2026-08-26 — GW-P6 Attempt 2 final QC quality fail

The missing-credential blocker was resolved without code or secret-file changes:
the existing AI Studio server-side `.env.local` supplied `GEMINI_API_KEY` to a
fresh VENHO OS process, and the existing bridge inherited `process.env` into its
CLI child. Presence was verified only; the value stayed server-only and was not
printed, persisted, client-exposed, or committed.

Exactly one production QC cycle ran on existing Attempt 2, using three
`gemini-3.5-flash` samples. Ledger history was preserved and the authorized
ceiling remained 18; consumed calls moved from 15 to 18 with no bypass or
additional authorization. Persisted authoritative QC is `faceScore=91.05`,
`allValidatorsApproved=false`, `killSwitchTriggered=true`. Attempt 2 therefore
fails the hard quality gate despite improving over Attempt 1 (`89.45`) by
`+1.60`; no Attempt 3 or second QC cycle is allowed.

Attempt 2 remains the active persisted attempt with Geometry PASS, Pixel Lock
PASS, byte-different crop, unchanged workflow/A2 authority, effective config
hash, runtime `46780 ms`, manifest 1.3, and matching EvidencePanel reload.
Job state is `succeeded / COMPLETED`; no new GPU/restoration action occurred.

## 2026-08-26 — GW-P6 Attempt 2 QC ledger authorization blocked before provider

The append-only validator ledger at
`artifacts/identity-restoration/benchmarks/validator-paid-call-ledger.jsonl`
contained 15 consumed intent calls and a prior ceiling of 15. Human
authorization for exactly one Attempt 2 QC cycle was recorded append-only,
raising the runtime ceiling to 18 without changing consumed history. Prechecks
passed for the CLI success/failure JSON contract, no-debug stdout, bridge parse,
and Attempt 2 restoration invariants.

Exactly one validation API invocation was made for
`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc`; no GPU or restoration path was
called. The fresh VENHO OS process did not have `GEMINI_API_KEY`, so execution
failed closed before Gemini transport. Ledger intent count remains 15 and
validator provider calls for this task are 0. Attempt 2 remains persisted with
`qcValidation=QC_FAILED`, job `validating / VALIDATING`, and no authoritative
Face QC. No QC rerun, Attempt 3, approval, rejection, or GW-P7 action is
authorized by this task.

## 2026-08-26 — GW-P6 Controlled Retry Attempt 2 blocked at QC gate

Exactly one production `RETRY_FACE` action created attempt
`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc` with only KSampler denoise
changed from `0.35` to `0.30`. Attempt 1 remains preserved with Face QC
`89.45`, runtime `96989 ms`, prior QC history, and unchanged authority. Attempt
2 persisted the same workflow ID/A2 hash, frozen workflow SHA
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`, effective
config SHA `45f4bbd50810e967f05c484166ca4bdb8e44cd57157fca6b1cd0af0bbbc4956f`,
and params `denoise=0.30`, CFG 6, 20 steps, Euler/normal, seed 123456.

The sole new GPU run completed in `46780 ms` on the healthy NVIDIA GeForce GTX
1660 SUPER worker. Restored crop differs from input; Geometry and Pixel Lock
PASS. No automatic retry or attempt 3 occurred. The one authorized QC cycle
was invoked through the existing validation route but failed closed before any
provider request because the locked validator paid-call ledger had
`budgetRemaining=0` after call 15. New validator provider calls: `0`; no ledger
or threshold bypass was made. Attempt 2 has no Face QC score and remains
`qcValidation=QC_FAILED`, job state `validating / VALIDATING`; this is an
infrastructure block, not a quality result.

Offline checks passed: VENHO OS focused suite `37`, integration `6`, AI Studio
pytest `31`, Python compile, TypeScript typecheck, changed-scope lint, and
git diff checks. Stop: no QC rerun, no attempt 3, no approve/reject, and no
GW-P7.

## 2026-08-26 — GW-P6 Quality Remediation Q1 analysis-only

R8 remains the sole real T4 attempt and its authoritative QC is a valid quality
failure: `faceScore=89.45`, `allValidatorsApproved=false`,
`killSwitchTriggered=true`. Geometry and Pixel Lock are PASS and the restored
crop differs byte-for-byte from the input crop. R7/R8 evidence proves the
bridge/CLI JSON path is now valid, so the deficiency is not a transport,
serialization, or validator-contract defect.

Read-only inspection of the current restored crop versus input/A2 and the
frozen workflow history supports a bounded identity hypothesis: v2
`denoise=0.35` over-reconstructs facial texture, producing overly smooth,
symmetric/generic appearance and possible eye-shape/proportion drift. Proposed
controlled Attempt 2 (not executed): change only KSampler `denoise` to `0.30`;
keep seed `123456`, CFG `6.0`, steps `20`, Euler/normal, FaceID Plus V2 and
all adapter weights, crop/masks/topology, workflow/A2 authority, and hard
`FACE_QC >= 90` threshold unchanged. Existing C1 local artifacts do not have
authoritative Face-QC, so no C1 score is claimed. Historical remote B08 (`95.4`)
and B03 (`90.6`) are different benchmark artifacts and are supporting context,
not proof for this case.

Q1 performed no GPU/provider/QC action, created no attempt, and did not mutate
the real job. State: `READY_FOR_CONTROLLED_RETRY`; GW-P6 remains
`OPEN / QUALITY_BLOCKED` until a future explicitly authorized retry satisfies
the unchanged hard gate.

## 2026-08-26 — GW-P6-T4-R8 final authoritative QC (quality fail)

R8 pre-call serialization gate passed entirely offline: mocked validate success
and failure produced exactly one JSON document, debug/provider text was absent
from stdout and routed to stderr, and the bridge parsed structured nonzero JSON
while failing closed on malformed/noisy output. The existing T4 attempt still
had one attempt/GPU attempt, unchanged workflow/A2 hashes, runtime `96989 ms`,
geometry PASS, Pixel Lock PASS, and a byte-different restored crop.

One final production VENHO OS validation cycle ran through the existing bridge
and `venho-restore validate` with Gemini. Exactly three calls were made using
`gemini-3.5-flash`; all ended `FinishReason.STOP`, input tokens were `5238`
each, outputs were `498`, `498`, `388` (totals `15714`/`1384`; cost not
exposed). The CLI/bridge produced valid structured `QC_VALIDATED` output.

Persisted authoritative QC: `faceScore=89.45`,
`allValidatorsApproved=false`, `killSwitchTriggered=true`. This is a valid
quality failure (`QUALITY_RESULT=FAIL / NEEDS_REVIEW`), not a transport block.
The validator did not supply Eyes/Brows, Anatomy, Outfit, Environment, or
Regional/Global metrics; those remain `NOT_PROVIDED_BY_AUTHORITY`. Geometry and
Pixel Lock remain PASS from restoration evidence. The same attempt and
manifest 1.3 were enriched; R4/R6 failures were retained additively in
`qcValidationHistory`. Job status/stage is `succeeded` / `COMPLETED` and the
panel reload matches persisted evidence. Human review is READY and human
action is REQUIRED; no approve/reject/retry action was taken.

Post-run offline checks passed: AI Studio `37`, VENHO OS `33`, Python
compileall, TypeScript typecheck, lint, and diff-check. R8 used no GPU,
restoration, base-generation, direct ComfyUI, or additional QC cycle. Stop at
human decision and do not start GW-P7.

## 2026-08-26 — GW-P6-T4-R7 CLI JSON serialization hardening

R7 was offline-only. The first failing serialization boundary was
`shared.logging.log()`: it printed provider diagnostics to stdout. During live
Gemini validation this appended lines such as the provider sample diagnostic
after the CLI JSON, so `RestorationBridge` correctly classified the combined
stream as `CLI_OUTPUT_INVALID`. Independently, `venho-restore health` used
`gpu_name!r`, which emitted Python repr instead of JSON string syntax.

The minimum fix routes shared diagnostics to stderr and adds a single
interface-level JSON writer/normalizer. It explicitly normalizes enums,
dataclasses, `Path`, date/time values, nested collections, Unicode, quotes, and
newlines; unsupported values fail closed. `run`, `health`, and `validate` now
write exactly one JSON document, including structured `QC_FAILED` output on
exit 1. No bridge heuristic scraping was added: structured nonzero JSON is
parsed, while malformed/empty/debug-prefixed stdout remains rejected.

Raw subprocess tests prove valid JSON and one-document stdout for validate
success, validate failure, and health; a logger test proves diagnostics appear
on stderr. Offline results: AI Studio interface/validate/composition/validator
tests `35 passed`; VENHO OS bridge/service/API/manifest/panel/no-direct `32
passed`; Python compileall, TypeScript typecheck, lint, and diff checks passed.
No provider/network/GPU call occurred and the real T4 job was not modified.
Authority, sample count, thresholds, workflow, A2, and QC semantics remain
unchanged. Next action requires explicit `GW-P6-T4-R8` authorization.

## 2026-08-26 — GW-P6-T4-R6 authoritative QC cycle blocked

The immutable precheck for the existing T4 job passed: one attempt and one
GPU attempt only, `comfyui-remote`, workflow
`face_restore_win_sd15_ipadapter_v2` with SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`, A2
SHA-256 `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`,
runtime `96989 ms`, geometry PASS, Pixel Lock PASS, and a byte-different
restored crop. The prior R4 failure was retained as `priorQcValidation`.

One and only one authorized QC validation cycle then ran through the
production VENHO OS API/service → restoration bridge → `venho-restore
validate --request` → existing ValidatorStudio gateway. Gemini made exactly
three calls (`gemini-3.5-flash`, samples 1–3); all finished
`FinishReason.STOP`, with input `5238` each and output `498`, `388`, `498`
(totals `15714`/`1384`; cost not exposed). The validator CLI result was
malformed JSON, so the persisted authoritative result is structured
`QC_FAILED`, code `CLI_OUTPUT_INVALID`, `retryable=false`; no QC metrics were
inferred. Existing ledger diagnostics contain sample index, model, finish
reason, success, and token usage; raw and parsed response paths are null.
The preceding idempotency preflight was a no-op (no bridge/provider call) and
is not counted as a validation cycle.

The same attempt, output, manifest 1.3, lineage, workflow/A2 hashes, runtime,
geometry, and Pixel Lock were preserved. Job status/stage is `validating` /
`VALIDATING`; human review is blocked. GPU jobs, restoration attempts, direct
ComfyUI access, base-generation provider calls, retries, and GW-P7 actions are
all zero. Offline checks passed: VENHO OS focused `31`, AI Studio R3 `8`,
validator/schema/structured-response `20`, TypeScript typecheck, changed-scope
lint, Python compileall, and git diff checks. Next is blocked pending explicit
validator/CLI remediation; do not rerun QC or start GW-P7.

## 2026-08-26 — GW-P6-T4 one real initial attempt

Exactly one initial GPU restoration was submitted through the production VENHO
OS endpoint `/api/v1/studio/identity-restoration` with explicit
`restorerId=comfyui-remote`; no CLI/direct ComfyUI submission, retry, benchmark,
tuning, or manual queue was used.

Case and lineage:

- `CASE_ID=gw-p0-t2-case-01`
- `JOB_ID=job-1787733824684-fzrqsi`
- `RUN_ID=gw-p6-t4-case-01-20260826`
- `ATTEMPT_ID=gw-p6-t4-case-01-20260826-attempt-1-mt9uk7fw`
- `BASE_ARTIFACT=assets/action-composite-live/action_01_jogging.png`
- `WORKFLOW_ID=face_restore_win_sd15_ipadapter_v2`
- `WORKFLOW_SHA256=1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`
- `A2_SHA256=1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`

The persisted job completed through all stages:
`QUEUED → BASE_READY → CROP_READY → GPU_RESTORING → COMPOSITING → VALIDATING → COMPLETED`.
Real worker evidence: `HEALTHY`, GPU `cuda:0 NVIDIA GeForce GTX 1660 SUPER :
cudaMallocAsync`, `vramFreeMb=5132`, remote host
`https://harry-rog.taila40de0.ts.net`, runtime `96989 ms`.

The result is `NEEDS_REVIEW` with `HUMAN_REVIEW=READY` and
`HUMAN_ACTION=REQUIRED`. Restored crop differs byte-exactly from input; both
are `687×659`. Pixel Lock is `PASS`, `mutatedPixelCount=0`; geometry is PASS
because the production restorer enforced exact dimensions. QC is `null` because
the production use case has no validator gateway wired, so Face QC, Eyes/Brows,
Anatomy, Outfit, Environment, and Regional/Global quality decision are `N/A`,
not fabricated.

Manifest 1.3 was written to
`staging/gw-p6-t4-real-20260826/manifest-1-3.json`. The durable StudioJobRecord
was reloaded from the existing social-manager store with one attempt; no second
job store exists. Evidence-panel fields are sourced from and match this
persisted record. Base-generation provider calls `0`; validator provider calls
`0`; GPU attempts `1`.

Post-run checks passed: focused bridge/service/API/manifest/no-direct tests
`18/18`, TypeScript typecheck, changed-scope lint, and `git diff --check`.
Stop at human review; do not approve, reject, retry, or start GW-P7.

## 2026-08-26 — GW-P6-T4-R1 persistent runtime closure

The proven root cause was missing persistent loading of the approved remote
Tailscale Serve endpoint; the runtime fell back to `127.0.0.1:8188`.
The smallest safe fix was persisted in the existing VENHO OS dotenv mechanism,
`/Users/hanhpham/Developer/Claude-Workspace/projects/venho-os/.env.local`:

- `IDR_COMFYUI_ENABLED=true`
- `IDR_COMFYUI_BASE_URL=https://harry-rog.taila40de0.ts.net`
- `IDR_COMFYUI_REMOTE_ENABLED=true`
- `IDR_COMFYUI_REMOTE_BASE_URL=https://harry-rog.taila40de0.ts.net`
- `IDR_DEFAULT_RESTORER=mock`

No Python source was hardcoded, no secrets were added, and no Windows/network
configuration was changed. A fresh Next environment loaded `.env.local`, then
spawned the resolved project CLI
`/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/.venv/bin/venho-restore`.
Health returned `HEALTHY`, GPU `NVIDIA GeForce GTX 1660 SUPER`,
`vramFreeMb=5132`; the composition registry was `mock, comfyui-local,
comfyui-remote`, with ordinary jobs still defaulting to mock.

Authority remained unchanged: workflow
`face_restore_win_sd15_ipadapter_v2`, SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`; A2
SHA-256 `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
Validation passed: focused bridge/API/security tests 13/13, Python health/
remote regression tests 7/7, TypeScript typecheck, Python compile check, and
`git diff --check`. `GPU_JOBS=0`, `PROVIDER_CALLS=0`; no restoration was
submitted. Next is one controlled real T4 initial attempt only. Do not start
GW-P7.

## 2026-08-26 — GW-P6-T4-R3 same-attempt QC gateway implementation

R3 is implementation-complete and offline-only. The existing
`ValidatorStudioQcGateway` is now composed through
`identity_restoration_module.py`; `venho-restore validate --request` calls a
new validate-existing-artifact use case that checks run/attempt ownership and
artifact/A2 presence, calls only `QcGatewayPort`, never invokes a restorer or
ComfyUI, and returns a structured QC result/failure. The explicit validate
command requires the gateway through the composition root while legacy `run`
remains opt-in for QC and ordinary default restoration remains unchanged.

VENHO OS gained typed validation over the existing shell-free bridge, a
same-attempt enrichment service/API route, and atomic manifest 1.3 QC merge.
Existing attempt fields, workflow/A2 lineage, runtime, geometry, artifact
references, Pixel Lock, and attempt count are preserved. Existing QC is
idempotent; a QC failure persists structured `qcValidation`, preserves the
completed artifact, and blocks human review without creating a retry attempt.

Offline evidence: R3 Python tests `8 passed`; VENHO OS focused bridge/service/
API/manifest/no-direct tests `26 passed`; TypeScript typecheck, changed-scope
lint, Python compileall, and diff checks passed. The real T4 job
`job-1787733824684-fzrqsi` / attempt
`gw-p6-t4-case-01-20260826-attempt-1-mt9uk7fw` was not read, validated, or
mutated. Network calls, GPU jobs, and provider calls remain zero. Next:
`GW-P6-T4-R4` authoritative QC on the existing T4 attempt only.

## 2026-08-26 — GW-P6-T4-R4 authoritative QC blocked

The hard precheck passed for job
`job-1787733824684-fzrqsi`, run `gw-p6-t4-case-01-20260826`, and the sole
attempt `gw-p6-t4-case-01-20260826-attempt-1-mt9uk7fw`. The completed
composite, manifest 1.3, ownership, workflow SHA, A2 SHA, runtime `96989 ms`,
geometry, and Pixel Lock were intact; QC was absent and attempt count was 1.

The production VENHO OS validation endpoint was invoked once through the R3
bridge and `venho-restore validate --request` using Validator Studio Gemini
with `samples=3`. Exactly three provider calls were recorded: model
`gemini-3.5-flash`, input tokens `5238` per sample, output tokens `388`, `388`,
and `498`; cost was not exposed. Transport completed, but the CLI exited
nonzero without a structured QC result (`CLI_EXIT_NONZERO`). No provider
retry, GPU call, restoration attempt, or ComfyUI access occurred.

The same job/attempt was preserved and atomically marked `VALIDATING` with
structured `QC_FAILED` evidence; manifest 1.3, output, lineage, runtime,
geometry, and Pixel Lock remain unchanged. Human review is blocked. Offline
post-QC checks passed: VENHO OS `30` focused tests, AI Studio R3 `8` tests,
TypeScript typecheck, changed-scope lint, Python compileall, and diff checks.
Next action requires explicit Validator remediation; do not retry automatically
and do not start GW-P7.

## 2026-08-26 — GW-P6-T4-R5 offline Validator contract forensics

R5 made no provider/network/GPU calls and did not modify the real T4 attempt.
The three R4 ledger entries prove Gemini transport completed with
`FinishReason.STOP`; however, `rawResponsePath` and `parsedEvidencePath` are
null for all three samples, so no exact provider body or underlying validator
exception can be recovered. No response was recreated.

The first reproducible failure is **H — CLI/bridge structured-error
normalization**. The validate CLI emits structured `QC_FAILED` JSON with exit
code 1, but the bridge rejected nonzero exit before parsing stdout and surfaced
opaque `CLI_EXIT_NONZERO`. The minimal fix is validate-only parsing of
structured stdout on nonzero exit; restoration `run`, timeout, malformed output,
and shell-free behavior remain unchanged. A synthetic fixture from the
observed R4 CLI result shape covers this case; no QC score was fabricated.

Offline checks: VENHO OS focused `31` passed; AI Studio R3 `8` passed;
Validator Studio/schema/structured-response `20` passed; typecheck, lint,
compileall, and diff-check passed. R6 requires either offline replay (no raw
responses exist) or explicit authorization for one minimum authoritative
3-sample rerun.

## 2026-08-26 — GW-P6-T4-R1 final Mac remote health check (historical pre-fix blocker)

T4-R1 was limited to closing the two T4 pre-flight blockers; no restoration
job, GPU job, provider call, QC run, network-topology change, or Windows
configuration change was permitted.

B1 is closed. The VENHO OS bridge no longer resolves the unrelated global
Python 3.9 bin. It now resolves the explicit `VENHO_RESTORE_EXECUTABLE`
override or the checked-out project venv, currently:
`/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/.venv/bin/venho-restore`.
The resolver regression test covers project/configured selection, missing
executable classification, shell-free argv, and deterministic `CLI_NOT_FOUND`.
The resolved CLI health command executes successfully in offline default mode.

Windows-local recovery was provided and verified externally: loopback
`127.0.0.1:8188` is listening, `/system_stats` returns HTTP 200, GPU is
`NVIDIA GeForce GTX 1660 SUPER`, ComfyUI is `0.33.0`, flags are
`--lowvram --fp32-vae`, and `GPU_JOBS=0`.

The final Mac-side approved remote health check used the frozen
`comfyui-remote` Tailscale configuration and the resolved CLI. It returned
`{"status":"OFFLINE"}`. Tailscale peer reachability and Windows-local health
therefore do not yet establish an end-to-end Mac application-health PASS.
Classification remains transient runtime / Windows-local inspection required;
no frozen authority regression was demonstrated.

Authority remains unchanged:

- Workflow: `face_restore_win_sd15_ipadapter_v2`
- Workflow SHA-256: `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`
- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`

T4-R1 validation: focused restoration bridge/API/service/manifest/security
tests `18 passed`; TypeScript typecheck PASS; changed-scope lint PASS; diff
check PASS. Next: keep T4 blocked until Mac remote health is HEALTHY, then
run exactly one controlled initial restoration attempt. Do not start P7.

## 2026-08-25 — GW-P4 dual-layer status clarified · GW-P5 execution starts

Two status layers on GW-P4 must not be conflated:
- **GW-P4 (historical, frozen)** = `CLOSED / QUALITY FAIL` — the original
  Regional-gate run (2/10 pass) stands unmodified as evidence.
- **GW-P4-R1 (remediation)** = `CLOSED / PASS` — root cause was QC
  **authority/scope** (B03/B04 scored against canonical default DNA instead of
  the human-approved `action_full_body@1.0` profile), not a real Identity
  Restoration defect. After correcting authority, B03/B04 replay deterministically
  to **97.51/PASS** and **94.14/PASS**.

Net effect: **no outstanding work remains under GW-P4.** The historical FAIL
label stays as frozen evidence (do not edit it), but it no longer blocks
downstream phases — GW-P4-R1's PASS is the operative decision for anything
that reads "is GW-P4 done."

GW-P5 (Worker Hardening) now begins execution, task by task, per the readiness
review already completed (GW-P5-T0). Order: T1 (Task Scheduler auto-start prep)
→ T3 (timeout verification) → T5 (safe retry on job interruption) →
remaining tasks that require physical Windows access (T2/T4/T6–T8 partially
blocked pending hands-on-hardware time).

## 2026-08-25 — GW-P5-T1 prepared + GW-P5-T5 verified offline

**T1 (Task Scheduler auto-start):** added `start_comfyui_worker.ps1` (reads
GW-P1-verified launch config, refuses non-loopback bind) and
`gw_p5_t1_register_autostart.ps1` (dry-run-by-default `AtLogOn` task
registration, `Limited` run level). Not yet run — needs the physical Windows
worker. T3's premise was checked and corrected: no real latency/duration
data exists anywhere in the repo (`artifacts/identity-restoration/`,
`staging/gw-p3/`), so timeout verification also needs a real Windows GPU
job and is blocked the same way.

**T5 (interrupted-job retry safety):** added
`tests/identity_restoration/infrastructure/test_gw_p5_t5_interrupted_job_retry.py`
against the real `FileConcurrencyLease`/`JsonlRestorationLedger` (not the
`FakeLease` the use-case tests use) — covers the crash path that was
previously untested: stale-lock reclaim after `ttl_seconds`, live-lock
fail-fast (`ERR_GW_LEASE_UNAVAILABLE`, retryable), and two ledger entries
under different `attempt_id` for the same `run_id` both surviving (no
overwrite). 3/3 new tests pass; full `tests/identity_restoration` 160/160,
0 regression. No production code changed. 0 network/GPU/provider calls.

Do next: **GW-P5-T2/T4/T6/T7/T8** all require physical Windows access to
close (health-from-Mac end-to-end after a real logon trigger, timeout
tuning against real measured latency, error-fail-fast under a real ComfyUI
error, reboot-safety of job records, one real cleanup-script cycle, typical
runtime + VRAM-shortage failure mode capture). None of these can proceed
further from Mac alone.

## 2026-08-26 — GW-P5 consolidated hardening preparation

T1 is recorded as `CLOSED / PASS` from the user-provided external Windows
registration evidence and human-captured real logon/Mac health output. The
repository now has a static bundle regression test and
`gw_p5_hardening_verify_on_windows.ps1`, which records a pre-reboot checkpoint
and validates post-reboot task/loopback/health without rebooting automatically.
T2 dead-worker fail-fast mapping is covered offline; T3 retry/attempt lineage
remains `PASS`. T2 final timeout measurement, T4 reboot/cleanup, and T5
2+10 sequential GPU soak are still human-execution blockers. GW-P5 stays
`IN PROGRESS`; GW-P6 remains `NOT STARTED`.

## 2026-08-25 — GW-P4-R1-T4 remediation closure

GW-P4-R1 is **CLOSED / PASS** with decision **REMEDIATION_PASS**. B03/B04
explicitly resolve `action_full_body@1.0`; deterministic replay still produces
**97.51/PASS** and **94.14/PASS**. B01/B02/B05–B10 retain canonical default
DNA; no automatic action/full-body mapping exists. Unknown explicit profiles
now fail closed, while absent mappings follow default-DNA governance. Tests
prove excluded global fields do not score for B03/B04 and face identity/
geometry failures remain enforced. R1-C1/C2/C3 are cancelled/not required.

Historical GW-P4 stays **CLOSED / QUALITY FAIL**; GW-P5 stays **NOT STARTED**.
No provider/network/GPU/Nano/Gemini/OpenAI-image/ComfyUI calls occurred. Next:
**GW-P5-T0 — Hardening readiness / entry-gate review.**

## 2026-08-25 — GW-P4-R1-T3 authority completion and offline replay

GW-P4-R1-T3 is **CLOSED / AUTHORITY COMPLETE** with decision
**AUTHORITY_CORRECTED_QUALITY_PASS**. Human-approved, file-backed
`action_full_body@1.0` authority is mapped explicitly from B03 and B04. It
removes only `shot_distance` and non-face-mask `hairstyle` from the face-only
Identity Restoration gate; all retained face fields are still scored.

Deterministic replay from saved parsed Image-QC evidence changes B03 global
score **86.61 -> 97.51** and B04 **83.76 -> 94.14**. B03 retains a partial
`hair_length` diagnostic and B04 retains `earring_type` mismatch; neither
violates a relevant gate threshold. Face-QC, identity, eyes, geometry, and
Pixel Lock remain PASS. The score change is authority ownership, not image
improvement. No provider/network/GPU/Nano/image-generation calls occurred.

GW-P4 remains **CLOSED / QUALITY FAIL** and GW-P5 remains **NOT STARTED**.
GW-P4-R1 is **IN PROGRESS**. Do next: **GW-P4-R1-T4 — Validate corrected
authority across benchmark fixtures / determine GW-P4 remediation closure.**

## 2026-08-25 — GW-P4-R1-T2 authority audit complete

GW-P4-R1-T2 is **CLOSED / AUDIT COMPLETE** with decision
**AUTHORITY_UNRESOLVED**. GW-P4 remains **CLOSED / QUALITY FAIL** and GW-P5
remains **NOT STARTED**; GW-P4-R1 is **BLOCKED**.

B03/B04 valid C1 Regional failures are solely Image-QC global_composite
(86.61 / 83.76). The benchmark invokes Image-QC with venho_hotel / linh_an
and no scenario_profile_id, so default DNA penalizes frozen full-body/action
cases for portrait framing and low-bun hair. Face-QC, identity, geometry and
Pixel Lock pass. No human-approved B03/B04 case-to-scenario mapping or
file-backed Linh An scenario overlay exists. The historical B04-only human
recovery record cannot be used as current Validator Studio authority and does
not cover B03. No offline re-score is valid.

Do next: **GW-P4-R1-T3 — Authority completion: add human-approved, versioned
B03/B04 case-to-scenario mappings and file-backed validator authority/reference
sets; then perform an offline authority replay. No GPU.**


## 2026-08-25 — GW-P4-R1-T1 root-cause analysis complete

Authoritative state is `artifacts/identity-restoration/benchmarks/gw-p4-t2-pilot-exhausted-checkpoint.json`:
GW-P4 is **CLOSED / QUALITY FAIL** and GW-P5 is **NOT STARTED**. GW-P4-R1 is
**IN PROGRESS**; GW-P4-R1-T1 is **CLOSED / ANALYSIS COMPLETE**.

All valid C1/C2/C3 failures are solely `global_composite_below_threshold`; Face
QC, identity, eyes/brows, geometry, and Pixel Lock pass. `global_composite`
comes directly from generic Image-QC. B03/B04 are full-body/action cases, but
the executed Image-QC uses default Linh An DNA without a scenario overlay and
penalizes default `portrait_head_shoulders`/`elegant_low_bun` expectations.
Those properties are not reliably editable by the locked face mask. This is an
authority/scope blocker, not evidence to lower thresholds or retune masks.

Do next: **GW-P4-R1-T2 — offline scenario-authority/global-composite scope
audit**, with no provider/GPU/Nano calls. The conditional three-candidate matrix
is `artifacts/identity-restoration/benchmarks/gw-p4-r1-t1-tuning-matrix.json`.

## 2026-08-25 — GW-P4-T2D final provider blocker closure

GW-P4-T2 is formally frozen as **PROVIDER_BLOCKED**. The authoritative C1/B03
Face-QC transport history is complete: `2048 → MAX_TOKENS`, `4096 →
MAX_TOKENS`, and `8192 → MAX_TOKENS`; all produced `0/3` valid samples. The
8192 response was 9,856 bytes, parser-invalid (`Truncated JSON response`), and
its raw SHA256 is
`e332b982cdd71e5c83110a19b6ca3ca9b3b17b8e442f303a3f3abf304ba1f50e`.

What is proven: the locked Gemini Face-QC transport cannot currently produce
the authoritative structured sample; RegionalScoreGateway correctly cannot
derive Regional authority without it; roadmap execution stops at GW-P4. What
is not proven: C1 denoise `0.30` quality. C1 remains **UNKNOWN**, not PASS,
FAIL, or PILOT_FAIL. This is not a GPU, Anatomy, Pixel Preservation, or
Lineage failure. B04 is not validated; C2/C3 were not advanced; GW-P5 was not
started.

Do not repeat Gemini recovery at 2048/4096/8192. Do not increase the output cap
without a new roadmap decision. Do not classify C1 as quality fail, validate
B04, advance C2/C3, or start GW-P5. Final checkpoint:
`artifacts/identity-restoration/benchmarks/gw-p4-final-provider-blocker-checkpoint.json`.

## 2026-08-25 — GW-P4-T2C controlled 8192 output-cap recovery

Offline preflight passed with the frozen provider `gemini`, model
`gemini-3.5-flash`, samples `3`, mock=false, fallback=false, temperature `0.0`,
rubric 07F, structured Face DTO schema, C1/B03 artifact SHA
`b395fc209939a0b5054092a4fdd9979afbfebf16d59b040a291c7aa07bd98a62`, and A2
authority SHA `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
The only request semantic change was `max_output_tokens` 4096 → 8192.

Exactly one live Gemini request was made for C1/B03 Face-QC sample 1. Gemini
returned `FinishReason.MAX_TOKENS`; input tokens `5265`, candidate output tokens
`7367`, cached/thinking/total unavailable, raw response `9856` bytes, SHA256
`e332b982cdd71e5c83110a19b6ca3ca9b3b17b8e442f303a3f3abf304ba1f50e`. Strict
parsing failed with `Truncated JSON response`; valid authoritative samples remain
`0/3`, classified `PROVIDER_TRUNCATED_RESPONSE`.

GW-P4-T2 remains **PROVIDER_BLOCKED** and C1 quality remains **UNKNOWN**.
This is not `PILOT_FAIL`; no score was created or inferred. B04 was not called,
C2/C3 remain untouched, GPU/Nano calls were zero, and GW-P5 remains NOT STARTED.
Evidence: `artifacts/identity-restoration/benchmarks/gw-p4-t2c-output-cap-8192-recovery.json`.

## 2026-08-25 — GW-P4-T2 PROVIDER_BLOCKED evidence freeze

Authoritative state: GW-P4-T2 **PROVIDER_BLOCKED**, GW-P4 **IN PROGRESS /
QUALITY GATE FAILED**, GW-P5 **NOT STARTED**. Run 6 remains 30/30 terminal and
decision-valid; Remote Regional PASS is only B01/B08 (2/10), while Face QC
median is 91.335 PASS and Anatomy/Pixel/Lineage are 10/10 PASS.

C1 denoise is 0.30. B03/B04 artifacts and local evidence remain available, but
C1 quality is UNKNOWN and B04 was not validated. C2/C3 are untouched. The
2048 and exactly one 4096 C1/B03 attempts are frozen raw, both T1
`MAX_TOKENS`/`PROVIDER_TRUNCATED_RESPONSE`, with zero valid samples. This is
not `PILOT_FAIL`; no quality conclusion, JSON repair, inferred score, retry,
provider call, GPU/Nano job, or GW-P5 start is permitted.

## 2026-08-25 — GW-P4-T2B output-budget containment audit

Offline trace confirmed the exact Face-QC → Gemini adapter → parser → scorer →
RegionalScoreGateway chain and the five authoritative weighted scores plus
three exact gate IDs. Historical valid observations are 1,337–1,982 bytes
(median 1,635; p95 1,934), while both frozen attempts truncate near 1.1 KB.
Thinking-token usage remains unknown and was not inferred.

Primary result: **R5 — NO_SAFE_OFFLINE_REMEDIATION**. The current prompt has
duplicated rubric/example instruction, but removal is not proven behaviorally
safe; narrative fields are audit evidence in the frozen contract. No patch,
provider call, cap increase, GPU/Nano job, B04/C2/C3 continuation, or GW-P5
start occurred. Status remains **PROVIDER_BLOCKED**.

## 2026-08-25 — GW-P4-T2 offline truncation audit

The persisted C1/B03 response was inspected without network access: raw and
parser input are both 1091 bytes, ending inside `weighted_scores`; the parser
fails at byte 1091. The ledger records `FinishReason.MAX_TOKENS`, prompt/input
5265 and candidate output 1173. Unpersisted HTTP, finish message,
candidate/parts, thoughts, total, and cached-content fields are null; no
semantic repair was performed. Root cause is **T1**.

Only Gemini `max_output_tokens` changed from 2048 to 4096. Offline regression
coverage passes with zero paid test calls. One recovery request is authorized
for C1/B03 sample 1 only; B04 and downstream stages remain blocked.

## 2026-08-25 — GW-P4-T2 C1 Face-QC transport checkpoint

## 2026-08-25 — GW-P4-T2 evidence-producing provider probe

Removed the separate live model-readiness HTTP request. Offline schema,
serialization, frozen provider/model, credentials, artifact SHA, local
evidence, cache, and budget checks passed. The first real C1/B03 request was
used as the readiness probe and sample 1. Gemini returned one `Truncated JSON
response`, now classified as `PROVIDER_TRUNCATED_RESPONSE`. Evidence was
persisted; no retry, sample 2, B04, Regional, C2/C3, GPU, or Nano call was
made. Calls attempted `1`, valid samples `0`, failed provider calls `1`, paid
test calls `0`. Status: **GW-P4-T2 = PROVIDER_BLOCKED**.

## 2026-08-25 — GW-P4-T2 hardened transport checkpoint

Added a zero-network production DTO/schema serialization gate. The exact
internal SDK cause was `additionalProperties` rejected by Gemini structured
output; only that unsupported keyword is stripped. Structured output remains
authoritative and bounded to 2048 output tokens. Added explicit failure
classes and a 503/429 provider circuit breaker; focused tests pass with zero
paid calls.

Readiness probe passed for Gemini `gemini-3.5-flash` with credentials,
samples=3, mock=false, fallback=false. One authorized resumed C1/B03 batch
then received `503 UNAVAILABLE` on sample 1. The batch stopped immediately;
B04, Regional, C2/C3, GPU, and Nano were not called. Valid Face-QC samples=0,
provider availability=DEGRADED, and C1 remains **PROVIDER_BLOCKED** with no
winner or quality-fail classification.

C1/B03 and C1/B04 passed the pre-call local artifact gate. Cache lookup found
no matching three-sample evidence for either SHA/configuration. The existing
Gemini structured-output adapter rejected `additionalProperties` locally; the
shared transport was minimally corrected to strip only that unsupported SDK
keyword while retaining JSON output and DTO validation.

The authorized C1-only run then recorded three paid-call intents: one local
schema rejection before HTTP and two Gemini `503 UNAVAILABLE` transport
failures. Valid Face-QC samples completed: `0`; remaining budget intents: `3`,
insufficient to complete both C1 candidates, so execution stopped fail-closed.
Image Validator, RegionalScoreGateway, C2/C3, GPU, and Nano calls: `0`.
No winner or Regional PASS is claimed. Status: **GW-P4-T2 = SCOPED BLOCKER —
C1 Face-QC transport unavailable**; do not resume with quality retries or
advance to C2 without a new authorized run/budget decision.

## 2026-08-25 — GW-P4-T2 staged Regional selection boundary

The staged-selection task requires C1/B03 and C1/B04 to be evaluated first
through authoritative RegionalScoreGateway evidence, with zero Face-QC
Validator calls and zero Nano calls. Repository inspection shows that the
current production gateway is only an adapter: identity/eyes/global values
come from upstream `validator_studio.face_validator` and
`validator_studio.image_validator`; no Regional-only producer exists.

Therefore no paid or invalid substitute call was made. C1/B03 and C1/B04
retain local PASS evidence (Pixel, Anatomy, geometry `97.80`/`97.08`) but
semantic Regional remains `UNVALIDATED`. C2/C3 and Group A were not evaluated
or generated. Cost ledger for this checkpoint: Regional `0`, Face-QC `0`,
Nano `0`, paid test calls `0`, new GPU jobs `0`.

Status is **GW-P4-T2 = PILOT AWAITING REGIONAL DECISION**, not globally
RUNTIME_BLOCKED: the current `3433 MiB` physical VRAM condition is not needed
for the immediate selection step. No pilot winner or Group-A expansion may be
claimed until an authorized Regional-only evidence path is available.

## 2026-08-20 — GW-P1 aggregation-only verifier repair

- GW-P1 runtime evidence tại `C:\VenHoGPU\evidence\gw-p1-20260820-173407` đã chứng minh
  CUDA/Torch, GTX 1660 SUPER, ComfyUI localhost health, SD1.5 512×512 CUDA inference,
  A/B/C sanity, non-black và `pixel_std ≈ 61.68`.
- Root cause của `winning_config=null` là verifier yêu cầu
  `$row.sd15_json.output.exists -eq $true`, trong khi `sd15_sanity_check.py` sở hữu
  contract `sd15_json.output.path`; field `output.exists` không tồn tại.
- Đã sửa duy nhất aggregation predicate trong
  `scripts/windows-gpu-worker/gw_p1_verify.ps1`: kiểm tra `output.path` bằng
  `Test-Path`, cùng `http_error=null`, `comfy_prompt_validation_error=false`,
  `cuda_runtime_exception=false`, resolution 512×512, non-black và `pixel_std > 5`.
- Winner vẫn phải được chọn theo thứ tự A→B→C; với evidence hiện tại A là
  `--lowvram --fp32-vae`. Khi A qualify, verifier ghi `C:\VenHoGPU\worker.env` với
  `COMFYUI_FLAGS=--lowvram --fp32-vae` và populate `winning_config`/`selected_run`.
- Không rerun installer, không đổi runtime/model/socket verification/SD1.5 workflow,
  không QC4/QC4I, không threshold/image tuning, không bắt đầu GW-P2.
- Trạng thái: **GW-P1 vẫn PENDING** cho đến khi Human chạy verifier một lần trên Windows
  và cung cấp report mới với `local_binding_verified=true` và overall PASS.

## 2026-08-20 — GW-P2 Extract Port CLOSED + GW-P3 Remote Adapter code PARTIAL

- Task giao (Harry): "Phase 1 sẽ giao cho Codex làm tiếp. Tôi muốn bạn bắt đầu làm từ
  roadmap phase 2 đến kết thúc." → không đụng GW-P1 (Windows GPU worker vật lý), thực
  thi GW-P2 (Extract Port) đầy đủ và bắt đầu GW-P3 (Remote Adapter) tới giới hạn không cần
  máy Windows thật.

**Kiến trúc mới `identity_restoration/`** (bounded context, `MODULE_ID = "IDR"`, KHÔNG phải
M-module theo GW-D2): domain (entities/value_objects/errors/compositing + 3 policy thuần) →
application (9 Port, DTO, registry, `RestoreFaceCropUseCase`) → infrastructure (3 restorer,
persistence, health, comfyui client stack, composition root) → interface (`cli.py`,
`json_bridge.py`). Chi tiết đầy đủ + rationale từng quyết định: patch doc PHẦN 4 "GW-P2"/
"GW-P3", cũng đã cập nhật checklist trong cả patch doc lẫn v2.0 plan gốc.

**2 quyết định lệch có chủ đích khỏi patch (ghi rõ để không bị coi là bỏ sót)**:
1. KHÔNG sửa `ProductionRunner` để gọi qua `RestorerRegistry` (T4 của GW-P2) —
   `image_studio_runtime/action_composite/production.py` không bị đụng. Lý do: đổi caller
   thật của pipeline production là hành động không thể rollback rẻ nếu sai, trong khi patch
   tự đặt tiêu chí "risk = 0" cho GW-P2. Hệ quả: `identity_restoration/` là con đường kiến
   trúc sạch đã kiểm chứng đầy đủ nhưng SONG SONG, chưa phải con đường
   `ActionCompositePipeline` thật đang chạy. Hợp nhất 2 đường — đổi `ProductionRunner` thật
   — là quyết định cần Harry chốt trước, không tự quyết.
2. KHÔNG di chuyển vật lý `CropTransform`/pixel preservation/compositing ra khỏi
   `action_composite/` kèm import shim (T6 của GW-P2, đúng chữ patch là "◐ DI CHUYỂN").
   Thay vào đó: `domain/policies/pixel_preservation.py` IMPORT trực tiếp hàm thuần
   `action_composite.regression_guard.protected_region` (không I/O, an toàn để tái dùng
   qua boundary); `domain/compositing.py` và `domain/entities.py` là code mới nhưng pixel
   math giống hệt logic paste-qua-mask đã có trong `ComfyUIIdentityRestorer.restore()` khi
   nhận `crop`/`crop_box` và trong `ActionCompositePipeline.run()`
   (`Image.composite(restored, base, mask)`) — copy hành vi, không sáng tác logic mới.
   Lý do không move+shim: `action_composite/` có 2537 dòng, di chuyển một phần và để lại
   shim rủi ro cao hơn giá trị kiến trúc thu được trong một phiên làm việc, trong khi
   `action_composite/` **0 dòng bị sửa** giữ nguyên vẹn con đường production đang chạy.

**`ComfyUILocalRestorer`** (`infrastructure/restorers/comfyui_local_restorer.py`) bọc
`ComfyUIIdentityRestorer` hiện có, gọi ở chế độ KHÔNG truyền `crop`/`crop_box` trong config
(chỉ truyền `crop` đã cắt sẵn làm `base_image`) — khiến adapter cũ đi nhánh trả về ảnh
restored thô đúng kích thước, không tự composite; composite chuyển hẳn sang domain layer
mới (`compositing.py`). Verify bằng test monkeypatch (`test_comfyui_local_restorer.py`) —
không gọi ComfyUI thật.

**Con số**: 53 test mới trong `tests/identity_restoration/`, 100% pass, 0 network call
(recorded fixture ở `contracts/identity_restoration/fixtures/comfyui/` hoặc monkeypatch
`urlopen`). Suite cũ: baseline GW-P0 951 pass/70 fail → nay 1005 pass/69 fail — **69 lỗi
còn lại y hệt baseline cũ** (đã đối chiếu từng dòng `FAILED`, tất cả thuộc nhóm missing DNA
fixture / subject-resolver schema mismatch có sẵn từ trước, không liên quan
`identity_restoration`); `tests/test_action_composite*.py` + `test_gw_p0_t2_golden.py`
50/50 pass nguyên trạng — golden-master GW-P0-T2 KHÔNG bị ảnh hưởng vì `action_composite/`
không đổi.

**Contracts**: 5 schema mới đặt ở `contracts/identity_restoration/` (KHÔNG phải
`contracts/` phẳng như patch viết) — lý do: `tests/test_growth_phase1_contracts.py`
enumerate `contracts/*.schema.json` bằng whitelist đúng 17 schema Growth Phase 1; thêm
schema GW vào đó làm 2 test của file này FAIL ngay (`22 == 17` và extra items) — phát
hiện + sửa trong phiên này bằng cách tách thư mục, không sửa test cũ.

**Smoke test thủ công (không phải pytest)**: `venho-restore run --restorer mock` và
`venho-restore health` chạy end-to-end ngoài suite test, output JSON đúng shape
`restoration_result.schema.json`/`worker_health.schema.json`. Lưu ý: composition root nạp
A2 authority từ `IDR_A2_PATH` (env, cố định theo cấu hình), KHÔNG phải từ field `a2Path`
trong từng request JSON — field đó trong request chỉ mang tính tài liệu/lineage, khớp đúng
thiết kế use case ở PHẦN 7.3 (`a2 = self._a2_repo.load()`, không đọc theo `cmd.a2_path`).

**GW-P3 (Remote Adapter) — chỉ phần không cần máy Windows**: `node_registry.py`,
`http_client.py`, `graph_binder.py`, `error_mapper.py`, `ComfyUIRemoteRestorer`, 2 script
(`deploy_workflows_to_worker.py`, `probe_gpu_worker.py`) — viết xong, test offline qua 7
fixture soạn TAY dựa theo tài liệu ComfyUI API (KHÔNG PHẢI ghi lại từ lần chạy thật — patch
muốn "ghi lại từ lần chạy thật đầu tiên", việc đó cần T2/T12 trước). **CHƯA làm và không
làm được trong sandbox này**: Tailscale probe (T2), tác giả + pin workflow SD1.5+IPAdapter
FaceID thật (T10), một crop Linh An thật đi hết chuỗi (T12) — cả 3 cần máy Windows thật.
GW-P3 CHƯA CLOSED, EXIT GATE (một ảnh thật đi hết chuỗi) chưa đạt.

**Việc còn lại theo roadmap, theo thứ tự ưu tiên**:
1. Harry chốt có hợp nhất `ProductionRunner`/`ActionCompositePipeline` vào
   `identity_restoration/` hay giữ 2 đường song song vĩnh viễn (ảnh hưởng GW-P6 dọn dẹp).
2. GW-P1 (Codex) xong máy Windows → chạy `scripts/probe_gpu_worker.py`, tác giả workflow,
   `venho-restore run --restorer comfyui-local` để verify TRÙNG golden-master byte-exact
   (chưa verify được vì không có ComfyUI server local trong sandbox này).
3. GW-P3 T2/T9(ghi lại thật)/T10/T12 sau khi có Windows worker.
4. GW-P4 Controlled A2 Benchmark — chưa bắt đầu, phụ thuộc GW-P3 CLOSED.

## 2026-08-19 — GW-P0 A2-FRONT SHA-256 pinned (VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md)

- Task giao: "Pin A2 SHA-256", tiếp theo sau GW-P0-T2 PASS/CLOSED trong roadmap GW plan v2.1.
- File thật đang giữ vai trò A2 identity authority cho golden-master (GW-P0-T2) là
  `venho-social-content-agent/assets/face-plates/A2_Front_plate.png`, **không phải**
  `assets/linh_an/A2_Front.png` mà `IDR_A2_PATH` trong plan v2.0 nêu — xác nhận bằng cách đối
  chiếu `shasum -a 256` với `identity_reference_sha256` ghi trong 3 case của
  `tests/identity_restoration/golden/index.json`, khớp cả 3.
  `sha256 = 1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
  `assets/raw/linh_an/A2_Front.png` (repo này) và `venho-social-content-agent/assets/A2_Front.png`
  có cùng sha256 với nhau (cùng ảnh gốc chưa crop) nhưng khác sha256 với plate đã dùng đóng băng
  golden-master — ghi rõ trong file pin để không nhầm 2 ảnh khi Phase GW-P2 rút Port ra.
- Tạo mới `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml` theo đúng template
  ở v2.0 §"ENV vars"/PHẦN 10.1 — pin `a2_authority` (path/sha256/repo/verified_at/note), giữ
  placeholder `face_restore_win_sd15_ipadapter_v1.sha256 = "<điền ở GW-P3"` (chưa có workflow),
  và pin thêm `face_restore_v1_api.json` (sha256 `b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25`,
  đã có sẵn từ `tests/identity_restoration/golden/index.json::lineage.workflow_sha256`, status SUPERSEDED).
- Chỉ tạo config + cập nhật doc/checklist (patch doc PHẦN 4 + v2.0 plan §Phase 0), **không đụng
  production code**, đúng scope "chỉ đọc và ghi tài liệu" của GW-P0.
- Còn lại của GW-P0: TASK 1 Coupling Audit (chưa làm, ưu tiên cao nhất theo patch), TASK 2
  Golden-master test file thật để chạy lại 3 fixture đã đóng băng (fixtures đã có, test chưa viết),
  đánh dấu v1.0 SUPERSEDED, move `face_restore_v1_api.json` → `workflows/_archive/`, viết 8 ADR.

## 2026-08-13 — Action Composite v2.1.1 face-crop correction

- Root cause of the 88.2/88.1 plateau was confirmed in the live route: the provider still received the full 1024×1280 action canvas, where the feathered face mask occupied only 3.99% of pixels. Resizing the provider's full-canvas response also introduced spatial distortion before compositing.
- Venho OS now derives a square crop from the real mask bounds, adds 1.7× context, upscales the current 454×454 crop to 1024×1024, sends only crop + crop-mask + one A2-FRONT authority, then composites the result at the original coordinates.
- The final composite is PNG and pixels outside the black mask are regression-locked. Manifest records crop bounds, provider size, mask bounds and coverage.
- Prompt priority is explicitly eyes/eyebrows → nose → mouth, with identity averaging and beautification forbidden. Scene, body, outfit and background are not sent into the restoration canvas.
- Offline verification: image-generation 140/140; full Venho OS 384/384; TypeScript, lint and production build pass. No paid call was made for v2.1.1; Face >90 remains unverified until one controlled live run.
- Controlled live v2.1.1 run `run-202608132052` completed at estimated $0.07056. Face remained **88.1 / revise**, while the final artifact retained the locked 1024×1280 base and the manifest recorded the 454×454→1024 crop transform. This rules out full-canvas face resolution as the only blocker; the remaining gap is identity synthesis/eye geometry fidelity, not scene compositing. No retry was made.

## 2026-08-13 — Nano Banana masked-edit provider contract

- ComfyUI is intentionally STOPPED. The canonical Nano Banana provider lives in Venho OS, so v2.1 now uses a shared `operation: masked_edit` contract rather than a second Gemini client in AI Studio.
- Trusted reference roles now include `base` and `mask`; server preflight requires exactly one base canvas, one repair mask, and one A2 face authority. Normal generation rejects these roles.
- Gemini request mapping is image-first: locked base canvas, white-editable mask, then A2 authority, followed by a strict instruction to preserve all pixels outside the mask.
- Verification: Venho OS image-generation tests 138/138 pass and TypeScript compile is clean. Live calls are recorded below; no Face QC >90 claim has been made.
- Live masked-edit tests (2026-08-13): two Nano Banana 1K calls, estimated total $0.14112; Face 88.2 and 88.1, both needs_review. First run still returned a full regenerated canvas; second route version added server-side mask composite but exposed a dimension bug (provider 848x1264 replacing base 1024x1280). Fixed after the run: composite now takes base canvas dimensions as canonical. No >90 claim.

## 2026-08-13 — Action Composite v2.1 offline implementation

- Root cause confirmed as staged-pipeline gap: the old path constructed a face crop but still sent the full canvas to restoration, used one ellipse mask, and did not bind the A2 asset hash.
- Implemented `hierarchical_face_masks()` with core/shape/boundary regions, normalized crop metadata, A2-FRONT SHA-256 lock, and v2.1 manifest lineage.
- ComfyUI adapter now uploads the normalized crop/mask and composites the returned crop back into the locked base canvas. Existing legacy restorers remain compatible.
- Added provider-neutral `SceneCandidate`, weighted candidate selection (pose/anatomy/outfit/environment first), fail-closed `RegionalGate`, and `WorkflowLedger`.
- Verification: `tests/test_action_composite_v21.py` + existing targeted suites = 23/23 new/critical tests pass; full action-composite group = 51/52, with the single failure in an old config assertion that expects a missing workflow despite the fixture now existing. Full AI Studio suite = 875 pass / 70 unrelated pre-existing fixture/schema failures.
- No official asset promotion and no A2 reference change. ComfyUI GPU/provider benchmark remains pending.
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-08-12 (A2 diagnostic V4 closeout và provider cost review) · **Đọc bởi:** AI Engine, Claude Code sessions

## Growth Agent — Wednesday room-DNA republish (2026-08-12)

- Đã nạp DNA riêng cho `lake_view_room_1` và `lake_view_room_2`; M04/M05 và daily cycle ưu tiên đúng room DNA theo rotation key, không còn dùng canonical room DNA cũ.
- Đã tạo lại batch Wednesday theo room DNA. Instagram đã nhận receipt hợp lệ `17926512171404301`, dùng ảnh `lake-view-1.jpg`; bài cũ đã được người dùng xoá trước đó.
- Facebook không được đánh dấu đã đăng: Make trả `PUBLISHED` nhưng chỉ trả placeholder/không có post ID hợp lệ, nên M07 fail-closed thành `GATEWAY_ERROR` để tránh ghi nhận sai.
- Các thay đổi DNA/validator và baseline ngày 2026-08-12 đang được đưa vào commit/push hiện tại.
- Cần sửa mapping Webhook Response của Make để Facebook trả post ID thật trước lần publish kế tiếp. Một số test cũ còn tham chiếu file canonical DNA đã xoá; đây là việc cần xử lý riêng, không coi là bằng chứng publish thành công.

## Image Generation — A2 diagnostic V4 và provider cost review COMPLETE (2026-08-12)

- A2-front tiếp tục là face reference authoritative; không thay thế bằng candidate.
- Diagnostic close-up 1K V4 đạt **Face QC 93.15 / APPROVED**: facial shape 95, eyes & brows 90, nose 92, mouth & chin 93, technical quality 98; không retry, ước tính **$0.06832**.
- Artifact gốc: `photos-ai/2026/12-08-linh-an-a2-diagnostic-v4-1k/run-202608121115/variant-001/image.png` kèm `manifest.json`.
- Candidate bổ sung: `venho-social-content-agent/assets/face-plates/candidates/A2_Diagnostic_V4_1K_candidate.png`; chưa promoted thành authoritative reference.
- Provider cost review: Imagen 4 Fast/Standard/Ultra khoảng **$0.02/$0.04/$0.06 mỗi ảnh**; GPT Image 1 Mini High khoảng **$0.036 output 1K**, image-input token có thể tính thêm. Chưa benchmark identity fidelity với A2.
- Kết luận: Nano Banana V4 là baseline duy nhất đã chứng minh Face QC >90; provider rẻ hơn chỉ thay thế sau benchmark A2 1K cùng prompt/reference/QC. Không phát sinh paid call sau V4.

---

## 1. Mục tiêu hệ thống

Biến ảnh thực và Brand DNA thành nội dung marketing chất lượng cao — hoàn toàn trên nền tảng tri thức chuẩn hóa, có approval gate trước khi phân phối, không tự publish khi chưa được duyệt.

Pipeline tổng quát:

```
Ảnh thực → [M01] DNA JSON → [M02] Prompt → [AI Engine ngoài tạo ảnh/video] → [M03] Validate
                           → [M05] Content prose → [M03] Validate
                           → [M06] Video storyboard → [AI Engine ngoài render video]
[M09] nhận goal tự nhiên → lập plan/risk/module requests → [M04] điều phối + approval gate → [M07] Publishing Gateway dry-run/publish receipt → [M08] Analytics Feedback
[M10] VENHO OS Home Workspace đọc artifacts/config của M01-M09 → hướng founder tới đúng việc cần làm ngay bây giờ
```

---

## 2. Kiến trúc tổng thể

### Growth Agent v3.0 Phase 1 Baseline (2026-08-03)

Phase 1 is complete in `venho-ai-studio`.

- Contract-first baseline is in `contracts/` with 15 schemas and pass/fail fixtures.
- Growth policy registry is in `config/projects/venho_hotel/growth/`.
- Research policy registry is in `config/projects/venho_hotel/research/`.
- Durable local state foundation is `shared/jobs/` + `shared/budget/` using SQLite.
- Real providers remain feature-flagged off by default; tests stay offline/mock.
- Full verification after Phase 1: `465/465` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 1.5 + Phase 2 Baseline (2026-08-03)

Phase 1.5 and Phase 2 are complete in `venho-ai-studio`.

- Research OS now supports validated vault frontmatter, R0/R1 collection, R2 synthesis, NotebookLM manual handoff verification, and controlled R2 -> R3 promotion.
- R2-T remains context-only and cannot become R3.
- Stale R3 facts can be detected and can revoke approvals that reference expired facts.
- M01 Knowledge Facts has a seed loader and resolver with validity-window handling.
- M03 Claim Validator blocks unsupported critical claims and distinguishes missing vs expired evidence.
- M09 can compile and lock CreativeBriefs only when proof points resolve to active R3 facts.
- M05 can generate three distinct mock/provider candidates and select one using a rubric.
- Full verification after Phase 2: `477/477` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 3 Baseline (2026-08-03)

Phase 3 is complete in `venho-ai-studio`.

- `agent_studio/growth/scenario_registry.py` resolves Visual DNA v2.7 scenario profiles from `config/projects/venho_hotel/growth/scenario_registry.yaml`.
- `image_studio_runtime` now creates immutable image run folders with complete paid manifests, mock-provider artifacts, DNA/reference trace, and no overwrite path.
- Paid image policy is enforced: maximum one paid generation plus one targeted repair; after that the package remains `NEEDS_REVIEW`.
- 429/5xx provider failures back off without creating any variant artifact.
- M03 alignment and derivative validators cover required-subject omission, forbidden entities, alignment score, crop safety, and OCR/critical text gates.
- Full verification after Phase 3: `482/482` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 4 Baseline (2026-08-03)

Phase 4 is complete in `venho-ai-studio`.

- M04 approval snapshots now bind exact package versions by checksum: copy, asset, validation snapshot, fact versions, and brief version.
- Dispatch is blocked if any approved package version changes after approval; Final Review state can present approved/pending/blocked without duplicating M03 logic.
- M07 keeps a local `PublicationRegistry` for idempotent publication reservation and status updates.
- Make.com remains only an M07 adapter; `GATEWAY_ACCEPTED` is not published.
- Callbacks require signed payloads and a post ID for `PUBLISHED`; reconciliation can close unknown states with proof.
- Duplicate chaos test reserves exactly one publication for repeated idempotency key/platform attempts.
- Full verification after Phase 4: `493/493` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 5 Baseline (2026-08-03)

Phase 5 is complete in `venho-ai-studio`.

- `shared/jobs/JobStore` supports idempotent dispatch triggers, worker heartbeat/lease extension, expired lease recovery, retryable-failure requeue, and terminal failure after max attempts.
- `shared/jobs/scheduler.py` can enqueue daily dispatch idempotently and emit structured late-run alerts.
- `shared/budget/BudgetLedger` now supports policy evaluation, budget override audit records, and paid-call reservation through `BudgetPolicy`.
- Budget policy alerts fire at 70/85/100%; 100% cap blocks paid calls unless an override with reason and approver is recorded.
- Full verification after Phase 5: `498/498` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 6 Baseline (2026-08-03)

Phase 6 is complete in `venho-ai-studio`.

- M08 attribution resolves inquiries through `utm_content=publication_id`, direct/assisted windows, policy dedupe fields, and SHA-256 pseudonymized contacts.
- Metric observations preserve semantic state: real value, zero, null, and provider-unavailable are not collapsed together.
- Sample metrics are asserted against raw source values before downstream reporting.
- Meta Insights remains feature-flagged off; mock metrics adapter is still the default in tests and local execution.
- Analytics collection windows are now `1h`, `24h`, `72h`, `7d`, and `28d`.
- M10 content performance projection reads M08 snapshot/score outputs only and does not recalculate analytics.
- Full verification after Phase 6: `504/504` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 7 Baseline (2026-08-03)

Phase 7 is complete in `venho-ai-studio`.

- `strategy_memory/` now supports Bayesian-smoothed QBSR pattern inference with confidence, scope, evidence, limitations, expiry, and approval-gated promotion.
- Strategy memories from insufficient samples return `INCONCLUSIVE` and cannot be promoted.
- Weekly strategy briefs are advisory-only, `pending_approval`, and suppress recommendations if QBSR drops below guardrail.
- M08 can generate a written research question into Research OS through `M08SignalBridge`, closing the analytics -> research loop.
- Every recommendation in the weekly brief must carry evidence and limitations.
- Full verification after Phase 7: `510/510` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 8 Baseline (2026-08-03)

Phase 8 is complete in `venho-ai-studio`.

- `controlled_rollout/` evaluates versioned golden scorecards, confirms 90-day baseline/candidate metrics readiness, manages rollout stage decisions, enforces rollback sequencing, and validates rollout runbook docs.
- P8 scorecard requires `>=9.3/10` on a versioned golden set; duplicate publication and unplanned empty days remain hard gates.
- Rollout stage progression is `shadow -> pilot_25 -> pilot_50 -> pilot_100`; human approval remains required, and trend lane is blocked from auto-approval.
- Rollback code requires dispatch disabled first, forward-only migrations, compatible reads, and immutable approved artifacts.
- First `_productize` skill is present: `.claude/skills/_productize/hotel-content-engine/SKILL.md`; `productize/hotel_content_engine.py` runs for hotel #2 from config only without core changes.
- Runbook docs are present under `docs/growth/controlled_rollout_runbook.md` and `docs/growth/eval_golden_sets.md`.
- `pyproject.toml` now packages `controlled_rollout*`, `productize*`, and `strategy_memory*`.
- Full verification after Phase 8: `517/517` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 QC Pass on Phase 1–3 (2026-08-03)

Senior QC review of all Codex-authored Growth Agent code. Fixed and regression-tested:

- `JobStore.claim()` was SELECT-then-UPDATE (non-atomic across two implicit transactions) — two concurrent workers could claim the same job. Now a single atomic `UPDATE ... RETURNING`.
- `publishing_gateway/callback_receiver.py` signed only `body`, leaving `timestamp` unauthenticated — defeated the "replay window" guard it was supposed to enforce. `timestamp` is now part of the signed message.
- `fact_key` / `rs_id` / `domain` / `title` / `topic_slug` were used unvalidated as filesystem path components (path traversal risk) in `FactStore`, `NotebookLMHandoff`, `collect_source_note`, `collect_structured_note`, `synthesize_notes`. Added `shared/security.py::ensure_safe_slug()` at each sink.
- `growth_orchestrator/` and `research_engine/trend_radar/` are untested scaffolding (stub bridges, e.g. `M07PublishingBridge` always fakes `GATEWAY_ACCEPTED`) — not yet wired to the real M03/M05/M07/M08 pipelines despite `pyproject.toml` exposing `venho-growth` as a live CLI entrypoint. Do not treat as production-ready; next phase must wire these bridges to the real modules instead of reimplementing simplified logic.
- Verify: `488/488` AI Studio tests pass (482 prior + 6 new in `tests/test_growth_qc_hardening.py`), 0 API calls, `compileall` clean.

### Growth Agent v3.0 QC Pass on Phase 4–8 (2026-08-03)

Senior QC review of all Codex-authored Phase 4–8 code (job/budget extensions, publication registry, approval snapshot, controlled rollout, strategy memory, productize, analytics attribution). Fixed and regression-tested:

- `publishing_gateway/publication_registry.py` did an unlocked JSON load → modify → save in `reserve()`/`update()` — two concurrent callers (retried dispatch vs. inbound webhook) could both read stale state and the second writer would silently clobber the first, breaking the idempotency guarantee the registry exists for. The existing "duplicate chaos" test only ran sequentially in one thread, so it never caught this. Fixed with an `fcntl.flock` exclusive lock around both methods; added a real 20-thread `ThreadPoolExecutor` regression test in `tests/test_growth_qc_hardening.py`.
- Everything else in Phase 4–8 reviewed clean: `JobStore` heartbeat/lease-recovery/retry-requeue extensions stayed single-atomic-statement SQLite (consistent with the earlier `claim()` fix), `BudgetLedger`/`BudgetPolicy` SQLite-backed with no cross-process race, `approval_snapshot.py` pure deterministic logic, `controlled_rollout/*` and `strategy_memory/*` pure functions, and `analytics_feedback/research_question_generator.py` already reuses `shared/security.py::ensure_safe_slug()` from the Phase 1–3 QC pass.
- `growth_orchestrator/` re-confirmed still zero references anywhere (`grep -rln growth_orchestrator` outside its own package) — unchanged from the prior QC finding, no new risk from Phase 4–8.
- `productize/hotel_content_engine.py` builds a path from a `project` string with no `ensure_safe_slug` guard, same shape as the fixed sinks — left as-is because `project` is currently a deploy-time config identifier, not attacker-controlled input; revisit if `project` ever becomes agent-/user-suppliable.
- Verify: `518/518` AI Studio tests pass (517 prior + 1 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Delta vs v3.0 (2026-08-03)

Read `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` and diffed it against everything Codex already built for v3.0. Most of v3.1's architecture already existed (contracts, jobs, budget, facts, image runtime, approval, scheduler, analytics, strategy memory, controlled rollout, and `research_engine/trend_radar/` with a real brand-safety gate + relevance scorer + 5 empty collector stubs). The actual delta implemented this pass:

- **Cadence 4 posts/week (TR-D2, PB-001):** `cadence_policy.yaml` v1->v2 -- removed the A(3)->B(5)->C(7) ramp entirely, fixed Mon/Wed/Fri (regular) + Sat (special) + Tue blog SEO. New `growth_orchestrator/domain/publishing_slot.py::PublishingSlot` state machine (`OPEN->DRAFT_ASSIGNED->PENDING_APPROVAL->FILLED->DISPATCHED->COMPLETED`, plus `EVERGREEN_FALLBACK` and a `MISSED` path that asserts the evergreen pool was actually exhausted first). New `growth_orchestrator/application/manage_slots.py::generate_slots()` -- deterministic, idempotent slot IDs from `(date, weekday)` so re-running over an overlapping horizon is safe.
- **Slot-based runway (PB-003):** `queue_policy.yaml` `runway_days` -> `runway_slots` (healthy>=6, warning 4-5, critical 2-3, empty 0-1 per §9.2); `manage_queue.runway_status()` updated, with a fallback read of the old `runway_days` key in case anything else still uses it.
- **Special lane T3->T7 with mandatory fallback (PB-008):** `growth_orchestrator/application/special_lane.py` -- priority order seasonal_nature > cultural_event (only if `verified_by_human`) > lifestyle_trend > feature_story (mandatory fallback, raises if absent -- this is what stops the Saturday slot from ever going empty or bending brand safety to force a trend). `special_lane_timeline_state()` enforces the hard Friday 20:00 cutoff -> `fallback_evergreen` if not yet approved.
- **Pre-flight check (PB-005):** `growth_orchestrator/application/preflight.py::run_preflight_check()` -- fact expiry, approval validity, asset reachability/hash match, event `verified_by_human` + not-yet-passed, weather R2-T not expired. Returns every failing reason, not just a boolean.
- **Weather signal is R2-T only, never a claim (§5.5, §6.6):** `research_engine/trend_radar/domain/weather_signal.py::WeatherSignal.fact_key` is typed `Literal[None]` -- Pydantic itself rejects any attempt to set it, enforced at the type level rather than only in a validator function. `contracts/weather_signal.schema.json` mirrors this with `fact_key: const null`. `scan_weather()` always derives `expires_at` from `weather_policy.yaml["expiry_hours"]`, never from the provider payload, so a provider can't hand back a signal that outlives policy. `weather_api.py` collector is an empty stub matching the existing 5.
- **`shared/notify/telegram.py` (IN-D4):** `MockTelegramNotifier` (default everywhere) + real `TelegramNotifier` requiring an injected `http_post` (never called anywhere in this repo). `send_alert()` resolves severity/channel from `shared/notify/alert_policy.yaml`, raises on an unknown event name.
- **`publishing_gateway/adapters/zalo_oa.py` (IN-D5):** mirrors `make_gateway.py` exactly -- disabled by default returns `DISABLED`, enabled returns `GATEWAY_ACCEPTED` (never `PUBLISHED`).
- **New `infra/` package (§10, IN-001/002/003):** `heartbeat.py` (payload builder + injected-`http_post` sender + staleness check), `deadman_config.yaml` (5-min heartbeat / 15-min stale / 09:15-09:30-10:00 dispatch-check thresholds), `cloud_fallback/export_approved.py` (only exports packages already `approval_status: approved`, HMAC-signs, and -- critically -- has no parameter or code path that can set `approval_status`, so the security invariant "cloud never creates an approval" is structural, not just documented), `backup.sh`, 5 `launchd/*.plist` templates, `setup_macmini.md` runbook. `infra*` added to `pyproject.toml` package discovery.
- **Contracts:** added `weather_signal.schema.json` + `publishing_slot.schema.json` + fixtures -> 17 schemas total. (The plan's own §5.10 header says "16" but its enumerated list has 17 entries -- a typo in the master plan itself, not a miscount here.)
- New test file `tests/test_growth_v3_1_cadence_infra.py`, 31 tests covering every item above.
- **Explicitly NOT done this pass (needs Harry, outside code scope):** buying/configuring a physical Mac Mini M4, running real `pmset`/`launchd`/Tailscale, registering real API keys (Tavily, Exa, Weather API, YouTube Data API, Telegram bot token, Zalo OA app), standing up a real healthchecks.io or Make.com data-store endpoint for heartbeat/cloud-fallback. Everything above is mock/stub/flag-off until those exist.
- Verify: `549/549` AI Studio tests pass (518 prior + 31 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Real provider wiring: Tavily + Telegram + Zalo token refresh (2026-08-03)

Harry now has `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, `ZALO_ACCESS_TOKEN` + `ZALO_REFRESH_TOKEN` + `ZALO_APP_ID` + `ZALO_APP_SECRET` in `.env.local`. **Security gap found and fixed immediately:** `.env.local` was never actually covered by `.gitignore` (it only matched the literal name `.env`) -- confirmed via `git log` it was never committed, but the next `git add -A` would have leaked all 5+ secrets. Fixed `.gitignore` to `.env.*` + `!.env.example`. Also renamed 2 typo'd keys Harry had pasted in (`zalo_appp_id`, `app_secret_key`) to `ZALO_APP_ID`/`ZALO_APP_SECRET` -- renamed the key only, never read/echoed the actual secret values into the transcript.

- **`shared/http.py` (new):** `urllib_post`/`urllib_post_form`/`urllib_get` -- stdlib-only transport (`urllib`), no new dependency (repo had zero HTTP libraries before this). Every adapter takes an injectable transport param (`http_post=None` -> defaults to the real one); tests always inject a fake, so the suite stays at 0 API calls even though real network code now exists.
- **`shared/notify/telegram.py`:** `TelegramNotifier` now defaults `http_post` to the real `urllib_post` instead of requiring injection; added `telegram_notifier_from_env(env)` reading `TELEGRAM_BOT_TOKEN`, raises `KeyError` if missing.
- **`research_engine/trend_radar/collectors/tavily_search.py`:** added `collect_tavily_search(query, api_key=..., http_post=...)` -- real call to `https://api.tavily.com/search`, normalizes into R0 entries (`id`/`title`/`source_uri`/`snippet`/`relevance_hint`). Classification into geographic/thematic/actionability/brand_safety_category deliberately stays downstream in `scan_trends`, not guessed here. Old `collect_tavily_search_stub()` left in place.
- **`publishing_gateway/adapters/zalo_oa.py`:** added `refresh_zalo_access_token(app_id, app_secret, refresh_token)` -- correct Zalo OAuth v4 shape (`POST https://oauth.zalo.me/v4/oa/access_token`, `x-www-form-urlencoded` body, `app_secret` in a `secret_key` header, not JSON/query string -- this project had no form-encoded POST helper before, added `urllib_post_form`). **`ZaloOAAdapter.send()` real path intentionally NOT implemented** -- Zalo OA has no public "feed post" API like Facebook Pages; real sending targets a specific follower `user_id` (7-day consultation window) or an approved broadcast template. Guessing the endpoint/payload risks burning real OA quota or messaging the wrong audience -- left as a documented open question for Harry: is Zalo meant as an internal alert channel (like Telegram, to Harry's own `user_id`) or a guest/follower content channel?
- **No feature flags flipped** (`trend_radar_enabled`, `zalo_enabled`, `real_meta_insights_enabled`, etc.) -- real keys now exist but turning a flag on means real API calls / real messages start firing, left for Harry to decide after review.
- New test file `tests/test_growth_v3_1_real_providers.py`, 8 tests -- Telegram default transport identity check + correct URL/payload via injected fake + `from_env` missing-token raises; Tavily missing-key raises + result normalization; Zalo refresh missing-credential raises + correct form-body/header shape.
- Verify: `557/557` AI Studio tests pass (549 prior + 8 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Zalo OA publish via Make.com webhook (2026-08-03)

Harry's integration decision: `ZaloOAAdapter` does not call the Zalo API directly -- it fires a webhook to Make.com, and Make's own HTTP / Custom API Request module (Harry configures this in the Make UI) makes the real Zalo OA call right after "Approve" is clicked on VENHO OS Dashboard. This resolves the endpoint ambiguity flagged in the prior pass -- Zalo OA has no public feed-post API, so picking the exact endpoint (broadcast/article/consultation message) is Harry's call inside Make.com, not a guess in code.

- **`publishing_gateway/adapters/zalo_oa.py`:** `ZaloOAAdapter` gained `webhook_url`, `webhook_secret` (optional, HMAC-SHA256 signs an `X-Venho-Signature` header, same convention as `approval_verifier.build_approval_signature`), `access_token_provider` (called once per `send()` to fetch a live Zalo token, meant to wrap `refresh_zalo_access_token` -- keeps all OAuth refresh logic in Python instead of duplicating it in Make.com), and `http_post` (injectable). **No `webhook_url` -> old mock behavior unchanged**, so the existing `tests/test_growth_v3_1_cadence_infra.py` assertions still pass untouched. With `webhook_url` set, POSTs `{publication_id, idempotency_key, platform: "zalo_oa", content, access_token?}` to Make.com; an `HttpError` from the webhook returns `GATEWAY_ERROR` rather than raising, consistent with the existing accept-async-then-callback pattern in `callback_receiver.py`.
- `.env.example`: added `ZALO_APP_ID`/`ZALO_APP_SECRET` (missed in the prior pass) + new `MAKE_ZALO_WEBHOOK_URL`/`MAKE_ZALO_WEBHOOK_SECRET`.
- 4 new tests in `tests/test_growth_v3_1_real_providers.py`.
- **Real remaining gap, not glossed over:** `growth_orchestrator/bridges/m07_publishing_bridge.py::M07PublishingBridge.dispatch()` is still a pure stub that returns a fake `GATEWAY_ACCEPTED` -- it does not call `ZaloOAAdapter` or any adapter, and there is no platform-based routing yet. The "Approve" button itself lives in `venho-os` (a separate TS/Next.js repo) and it's unconfirmed how/whether it calls into this Python M07 bridge at all. So "clicking Approve auto-posts to Zalo" is NOT true end-to-end yet -- only the adapter's webhook-trigger capability is real and tested. No Make.com scenario has been created/tested against a live `MAKE_ZALO_WEBHOOK_URL` either.
- Verify: `561/561` AI Studio tests pass (557 prior + 4 new), 0 API calls, `compileall` clean.

### Content Studio — Zalo platform rules + dedicated hotline CTA (2026-08-03)

Harry: Vietnamese Zalo users want short, direct copy with a clear contact/booking line -- specifically "Liên hệ Hotline/Zalo 0936871234 để đặt phòng view Hồ Tây ngay hôm nay." Instead of a one-off manual instruction to an AI agent (easy to forget, inconsistent run to run), wired this into config + the M02 Prompt Studio pipeline so it's deterministic and test-covered -- consistent with the project's config-first principle.

- **`content_studio/schemas/content_request.py`:** added `"zalo_post"` to the `ContentType` Literal -- `ContentRequest` could not represent Zalo at all before this.
- **`content_studio/content_engine.py::_builder_for`:** routes `zalo_post` to `build_social_draft` (same social group as facebook/instagram/threads/tiktok).
- **`config/projects/venho_hotel/content/platform_rules.yaml`:** added `zalo:` -- `max_length: 300` (shorter than `threads`'s 500, per "shorter than Facebook"), `max_hashtags: 0` (Zalo culture doesn't hashtag-search like FB/IG).
- **`config/projects/venho_hotel/prompt_rules.yaml`:** added `platform_cta_overrides.zalo` with Harry's exact CTA text + phone number. Deliberately placed in the prompt layer, not `content/` -- `load_content_config()` already hard-forbids a `content/cta_rules.yaml` existing (raises `ContentConfigError`), so CTA wording has to live here.
- **`prompt_studio/builders/content_prompt_builder.py`:** `render_final_prompt()`/`build_content_prompt()` gained an optional `platform` param; the `Call-to-action:` line in `final_prompt` now checks `platform_cta_overrides[platform]` first, falling back to the global `cta_rule` -- fully backward compatible (omitting `platform` reproduces the old behavior exactly, no existing test needed changes).
- **`content_studio/prompt_bridge.py`:** now passes `platform=request.platform` (existing derived property) through to `build_content_prompt`.
- Checked `validator_studio/content_validator.py::_score_cta` -- it scores on generic `CTA_TERMS` keywords ("liên hệ", "đặt phòng"), not an exact match against `cta_rule`, so the new Zalo CTA text scores correctly without touching the validator.
- 3 new tests: 2 in `test_content_prompt_builder.py` (platform="zalo" gets the override + phone number; other platforms keep the generic rule, no phone number), 1 end-to-end in `test_content_studio.py` (generating a `zalo_post` produces empty hashtags, a shorter `max_length` than facebook, and the phone number in `final_prompt`).
- **Scope note:** this only affects the new M02/M05 content-generation layer (Growth Agent v3.1 pipeline, this repo). The older `VenHoSocialManager` system (separate `venho-os` repo, GitHub Actions T2/T4/T6 for FB/IG/Threads) is a different pipeline that does not read `platform_rules.yaml`/`prompt_rules.yaml` here -- applying the Zalo CTA there would need a separate change in `venho-os`.
- Verify: `564/564` AI Studio tests pass (561 prior + 3 new), 0 API calls, `compileall` clean.

### Module Roles (KHÔNG chồng lấn)

| Module | Vai trò | KHÔNG làm |
|--------|---------|-----------|
| **M01** Knowledge Studio | Ảnh → DNA JSON (structured observation) | Viết content, tạo prompt |
| **M02** Prompt Studio | DNA → Prompt JSON (structured, deterministic) | Gọi AI viết prose |
| **M03** Validator Studio | Kiểm output (ảnh, prompt, face, content) | Tạo output |
| **M04** Automation Studio | Điều phối M01–M03 thành workflow | Chứa business logic module khác |
| **M05** Content Studio | Thực thi content-prompt M02 → prose | Dựng prompt lại, tự parse DNA |
| **M06** Video Studio | DNA + character → storyboard + engine prompt package | Render video, publish video |
| **M07** Publishing Gateway | Phân phối package đã duyệt, dry-run/publish receipt cho M08 | Tạo/sửa content, tự quyết giờ đăng, phân tích performance |
| **M08** Analytics & Feedback Loop | Đo metrics, score performance, sentiment guardrail, sinh feedback advisory | Đăng bài, tự sửa Knowledge/Content Strategy, tự apply advisory |
| **M09** Agent Studio | Cognitive interface: goal → request validation → persona/context → task plan/risk/module requests qua M04 | Tự publish, tự sửa Knowledge, tự tính metrics, gọi M07 trực tiếp |
| **M10** VENHO OS Home Workspace | Founder-first UI đọc M01-M09 artifacts/config, hiển thị Today's Focus, Current Work, Needs Review, Ready to Publish, Quick Actions, Recent Activity | Lưu DB nghiệp vụ, tính lại score/HMAC, build prompt/ModuleRequest, render/upload/publish, đưa raw JSON/pipeline/analytics/system health lên Home |

### Nguyên tắc bất biến

1. **M02 dựng prompt, M05 thực thi** — không hoán đổi vai.
2. **M04 chỉ điều phối qua adapter** — không import sâu logic module con.
3. **Archive thuộc module con** — M04 không overwrite file production.
4. **Draft/approval first** — mọi output là draft cho tới khi M04 approval hợp lệ; M07 chỉ thực thi package đã duyệt.
5. **0 API call trong tests** — tất cả offline/mock.
6. **Config-first** — workflow/rule khai báo YAML, không hard-code.
7. **Project-agnostic core** — Ven Hồ là project đầu tiên, không phải core.
8. **Kết thúc task = cập nhật memory/status** — khi người dùng nói "kết thúc task", Codex tự động cập nhật `task_memory.md` và `task_status.md` trước khi chốt.
9. **M10 presentation-only** — Operating Center degrade bằng advisory khi module con thiếu artifact; không làm sập toàn UI và không sao chép business logic.
10. **M10 Home Workspace v1.0** — Home trả lời “What should I do now to move my business forward?”; Home chỉ có Today's Focus, Current Work, Needs Review, Ready to Publish, Quick Actions, Recent Activity. Pipeline nằm ở Workbench; raw JSON/token/cache/runtime internals nằm trong Settings, không nằm ở Home.
11. **M10 action-first** — Status quan trọng phải dẫn tới contextual action label/button; button MVP chỉ điều hướng/placeholder, không chạy live workflow ngầm.
12. **M05 real generator = claude_longform_generator** — inject qua `generator_fn` param; `None` → template mock (tests an toàn); chỉ dùng cho non-social (blog/OTA/FAQ/email/website); social posts thuộc VenHoSocialManager.
13. **VenHoSocialManager QC gate (2026-07-15)** — `generate_image_with_qc()` dùng GPT-4o-mini vision (score 1–10, ngưỡng 7); max 2 retry với tightened prompt; fail sau retry → skip Drive+Make.com, gửi `send_qc_alert()`; không thay đổi social posting logic.
14. **AI Studio v1.5 Phase 0 baseline (2026-07-16)** — historical baseline: AI Studio `424/424` pass; VenHo OS `54/54` pass + build pass; roadmap v1.5 và Phase 0 baseline note đã commit/push; exposed API key phải revoke/rotate ngoài repo.
15. **AI Studio v1.5 Phase 1 Mode C data integrity (2026-07-16)** — Mode C tách `outfit_id/schema_subject/display_label`; `mint_green` và `nike_pink_running` dùng schema canonical `outfit_e_sport`; universal fallback bị hard-fail; OS status dùng `since` để tránh stale artifact false success; upload trùng tên bị chặn; `wardrobe_manifest.json` quarantine Nike Pink artifact cũ và đánh dấu `sport_active` là legacy upload alias.
16. **AI Studio v1.5 Phase 2 Image QC contract (2026-07-16)** — Face Validator hard-fail nếu thiếu 3 gate hoặc 5 score keys; face score scale phải là 0–100; VenHo OS manifest `1.1` ghi prompt hash, outfit requested/effective, scenario profile, face reference set, validator contract, latency/retry.
17. **AI Studio v1.5 Phase 3 Durable Jobs (2026-07-16)** — VenHo OS image generation dùng file-backed job store, `/api/v1/studio/jobs`, status/cancel/polling, audit `queued→generating→validating→succeeded/failed/cancelled`.
18. **AI Studio v1.5 Phase 4 Wardrobe Index (2026-07-16)** — Linh An `wardrobe_index.json` contract 1.0 là source of truth cho outfit selector; OS đọc `/api/v1/studio/wardrobe-index`; user-selected outfit thắng default; AI auto-selection mặc định off.
19. **AI Studio v1.5 Phase 5 Contract Refs (2026-07-16)** — M02/M03/M05/M06 dùng optional `contract_refs` để trace `character_id/outfit_id/scenario_profile`; M05/M06 không tự chọn outfit; Claude adapter có fake-client test, không gọi API thật trong pytest.
20. **AI Studio v1.5 Phase 6 Ops/Living Lab (2026-07-16)** — M04 có `wardrobe_ingest` + `wardrobe_index_update` với validation/human-review gate; M09 hard-stop khi thiếu knowledge; `JobContract 1.0` tách `approved→executed→published`; Living Lab đo output used/approval/retry/time/cost/decision.
21. **AI Studio v1.5 Phase 7 QA/DOC closeout (2026-07-16)** — v1.5 không có Phase 7 chính thức; closeout map vào `QA-01/DOC-01`. Controlled matrix canonical ở `config/quality/controlled_live_matrix.json`; OS expose `/api/v1/studio/quality-matrix`; production-ready cần 2 approved runs liên tiếp/case.
22. **Current verification baseline (updated 2026-07-20)** — AI Studio `454/454` pass, 0 API call; VenHo OS `65/65` pass + lint + TypeScript + build pass. Build warning Turbopack NFT trace ở `upload-images/route.ts` là known issue, không phải failure.
23. **VAL-01 + LOC-01 real-run fixes (2026-07-17)** — Audit 16 run thật (2026-07-15/16) cho thấy 0/16 đạt `approved`. Root cause 1 (VAL-01): `observe_face_against_dna.md` chỉ ví dụ 1/3 gate → LLM luôn bỏ sót `eye_ratio`/`forbidden_traits` → `Face gates mismatch` chặn cứng mọi run. Root cause 2 (LOC-01): `westlake.overrides.yaml` curated stale ("green lamp posts/railing") trong khi thực tế 2026 (Harry xác nhận) là lan can trắng ngà, không cột đèn — validator chấm sai so với `constants.ts` thật. Sửa cả 2 (chỉ code/data, không API call để fix); thêm cơ chế scenario-aware overlay merge-at-validate-time (`image_validator.py::_apply_scenario_overlay`, tham số mới `scenario_profile_id`, threaded qua CLI/OS) để scenario Nguyễn Đình Thi có wording cây/lan can riêng, không đụng overlay chung. Live-verify case E1 thật: Image/DNA score 84.91→**100 approve**; Face không còn lỗi contract, score 80→**85** (vẫn dưới ngưỡng approve 90 — chưa xong). Case E5 vướng bug riêng, đã fix cùng phiên: `assets/Rooftop-Panorama-view.jpeg` là MPO container (ảnh iPhone portrait/burst nhiều frame) khiến `openai.images.edit` reject khi dùng làm ref-env thứ 2 (`400 invalid_image_file`). Convert sang PNG đơn-frame sạch (`Rooftop-Panorama-view.png`, giữ file gốc), cập nhật `constants.ts`. Live-verify lại: HTTP 200, Image/DNA 100/approve, Face 83.5/revise. **SEC-01 xác nhận done** (Harry đã tự rotate key lộ). OUTFIT-01 xác nhận đã xong từ Phase 4 (không phải làm mới). Kết luận trung thực: cả E1 và E5 đạt Image/DNA 100/approve nhưng Face score (85, 83.5) đều dưới ngưỡng approve 90 — production-ready gate (2 run approved liên tiếp/case E1–E6) vẫn chưa đạt; Face QC là gap lớn nhất còn lại (có thể cần VAL-02 — so khớp ảnh master thật — thay vì chỉ prompt contract).
25. **Prompt quality tuning + validator scoring reliability concern (2026-07-17)** — Sửa prompt-builder.ts (Living Expression rõ hơn cho running shot, thêm anti-artifact/sharpness cues) để cải thiện expression/technical_quality. Live-verify E1: 5 category score ra **giống hệt tuyệt đối** lần chạy VAL-02 trước đó (90/85/80/75/70) dù ảnh và prompt khác nhau — nghi ngờ Face Validator chấm theo khuôn mẫu mặc định, chưa chắc nhạy với input thật. Harry quyết định debug sau, không đốt thêm phí thử prompt cho tới khi rõ nguyên nhân.
26. **Git hygiene + backlog re-verification (2026-07-17)** — Commit toàn bộ thay đổi phiên này theo nhóm scope rõ ràng (không gộp bừa): `venho-ai-studio` 4 commit (VAL-01+LOC-01, VAL-02, docs, +1 MAN-01 gap không áp dụng ở repo này), `venho-os` 5 commit (LOC-01 threading, VAL-02 default refs, MPO image fix, prompt tuning, MAN-01 gap fix). Verify lại các mục task_status.md từng ghi "done": DATA-01/MODEC-01/MODEC-02 **CONFIRMED chính xác** bằng code thật, không cần sửa. JOB-01 **phần lớn đúng nhưng có gap thật**: server restart giữa lúc generate làm job kẹt vĩnh viễn ở `generating` (chưa có reconcile/resume, chưa có test cancel) — chưa fix, cần Harry quyết định ưu tiên. MAN-01 **tìm ra 1 bug thật và đã fix**: `faceReferenceSetVersion` là literal hardcode không liên kết với 4 ảnh reference VAL-02 thật, và gate sai theo `effectiveUseRef` thay vì `hasLinhAn` — đã sửa (commit `f15da8a` venho-os), thêm field `faceReferenceImages`, cập nhật test.
27. **JOB-01 gap fix (2026-07-17, commit `85785b5` venho-os)** — Harry yêu cầu fix gap đã tìm ra ở mục 26. Thêm `job-store.ts::reconcileOrphanedJobs()`, gọi 1 lần lúc `jobs/route.ts` module load (an toàn vì `controllers` map chắc chắn rỗng lúc đó) — mọi job còn `queued/generating/validating` trên đĩa được đánh dấu `failed`/`orphaned_by_restart` thay vì treo vô thời hạn. Khi viết test phát hiện thêm bug thật thứ 2: `cancelJob()` fallback path ép status thành `cancelled` vô điều kiện kể cả khi job đã `succeeded` — DELETE lên job đã xong sẽ phá hỏng kết quả đã ghi; đã sửa chỉ cancel job còn in-progress, trả 409 nếu đã terminal. Test mới: `job-store.test.ts` + 2 case cancel trong `jobs-route.test.ts`. 78/78 pass, build clean (NFT warning cũ không đổi).
30. **Full matrix v2 với sampling — kết quả cuối, sự cố bảo mật, khuyến nghị ngưỡng (2026-07-17/18)** — Chạy lại E1-E6 với sampling 3x. Kết quả: E1/E3/E4/E6 Image 100/approve; E2 lần 1 và E5 reject vì lý do thật khác nhau (green railing ngẫu nhiên, modern high-rise — bỏ ref-env chỉ giảm chứ không hết xu hướng model tự thêm nhà cao tầng ở góc panorama). Face score toàn bộ ~13 run thật trong phiên **chưa từng đạt 90** (dao động 0-85). Giữa chừng: (a) sự cố bảo mật — lệnh `source <(grep ... .env.local)` của tôi vô tình dump toàn bộ env ra output, làm lộ `OPENAI_API_KEY` trong transcript; đã dừng ngay, yêu cầu Harry rotate key; (b) tài khoản chạm billing hard limit thật giữa lúc chạy E4-E6, phải dừng và đợi Harry xử lý billing. Cả 2 đã được Harry xử lý xong, resume thành công. Kết luận cuối: khuyến nghị Harry xem xét lại ngưỡng `face_identity_min: 90` — có thể không thực tế với khả năng hiện tại của gpt-image-2, chưa tự ý đổi.
29. **Face Validator non-determinism xác nhận thật + fix bằng sampling (2026-07-17)** — Xem trực tiếp ảnh E3/E4/E6 (Read tool, không tốn phí) và ảnh master face — bằng mắt thường không thấy khác biệt rõ ràng giải thích được vì sao E3=82.5 còn E4/E6=0. Làm thí nghiệm rẻ: chạy lại Face Validator qua CLI trực tiếp (không tạo ảnh mới) 3 lần/ảnh trên 3 ảnh có sẵn. Kết quả: E3, E4 ổn định qua các lần lặp. **E6 "lật kèo" thật** — cùng ảnh, cùng reference, cùng code, nhưng run gốc cho 0/reject còn 3 lần lặp lại ngay sau đó đều cho 82.5/revise. Xác nhận đây là non-determinism thật của model ở temperature=0, không phải templating hay bug input. Fix: thêm `samples` param vào `validate_face()`, sample N lần + `_merge_face_samples()` (majority-vote gates, average weighted_scores, cùng pattern với `observe_adapter.py::_merge_samples` đã có cho Image Validator). `venho-os/validate_generated.py` mặc định `samples=3` cho production. Cũng fix E6 vấn đề Image: env-ref `Rooftop-Panorama-view.png` thực chất là ảnh 1 sân thượng cụ thể (xem bằng Read tool), làm ảnh AI lẫn chi tiết sai (lan can đen/gạch nung/cục nóng + nhà cao tầng thật) → bỏ ref-env cho scenario này (commit `531571c` venho-os). 451/451 test pass. Live-verify qua CLI thật: sampling hoạt động đúng thiết kế.
28. **Face Validator caching điều tra + full E1–E6 matrix live run (2026-07-17)** — Điều tra kỹ hiện tượng điểm giống hệt: rà toàn bộ call path, xác nhận **không có bug cache** (0 kết quả grep cache/lru_cache/memoiz trong `shared/vision/`, `validator_studio/`), mỗi lần gọi đều tạo client mới và gọi API OpenAI thật. Sau đó chạy đủ 6/6 case E1–E6 thật (trước đó mới có E1/E5): E1/E3/E5 approve Image, Face 82.5–85/revise; **E2 ban đầu 40/reject** vì DNA cấm cột đèn nhưng prompt sinh ảnh chưa từng cấm — **đã fix** (thêm "no lamp posts" vào `ENV_BLOCKS`/`SCENARIO_LOCATION_QC`/`NEGATIVE_BLOCK`, verify lại 40→100/approve, commit `88c19c6` venho-os); **E4 Face 0/reject đúng như kỳ vọng** (cycling tự tắt face-ref theo D-04 → mất identity thật, không phải bug); **E6 vẫn reject cả Image (postcard aesthetic) lẫn Face (identity fail dù có đủ reference) — CHƯA fix**, cần điều tra riêng. Phát hiện quan trọng nhất: report Face của E4 (không ref) và E6 (có đủ ref) cho **weighted_scores + văn bản lý giải giống hệt gần như từng chữ** dù input khác biệt cực lớn — bằng chứng mạnh Face Validator's `weighted_scores` có tính templating thật, trong khi `gates` (True/False) vẫn phân biệt đúng. Cũng phát hiện `controlled_matrix.py` không thể tính production-ready vì validator hiện tại thiếu field `outfit_match`/`actor_geometry_ok` mà matrix yêu cầu. Kết luận: production-ready vẫn chưa đạt ở bất kỳ case nào.
24. **VAL-02 implemented (2026-07-17, cùng phiên)** — Face Validator giờ so trực tiếp với 4 ảnh reference thật (B3_Hero primary, A2_Front, C_LeftProfile, D_RightProfile) thay vì chỉ text DNA. Thêm multi-image vision support (`shared/vision/providers/openai_vision.py::analyze_many`, `VisionClient.analyze_images`) — OpenAI chat API vốn hỗ trợ N ảnh/message, không cần workaround. `face_validator.py::validate_face` nhận `reference_image_paths` optional, `None` giữ nguyên hành vi cũ; thiếu file reference → raise lỗi rõ ràng trước khi gọi API (Harry chọn "fail loud", không âm thầm fallback, cùng nguyên tắc với fix universal_schema trước đó). `venho-os/validate_generated.py` tự truyền 4 path chuẩn khi có `--face`, không cần sửa route.ts. 450/450 test pass. **Live-verify E1:** report xác nhận thật sự dùng 4 ảnh reference (note + lý giải model trích dẫn "Comparison with reference images"), nhưng Face score = 82.5 (so với 85 không-reference trước đó) — **không cải thiện, giảm nhẹ**. Kết luận trung thực: điểm số giờ đáng tin cậy hơn (có căn cứ so ảnh thật) nhưng chưa đủ để đạt ngưỡng 90 — gap còn lại là chất lượng ảnh sinh ra thật (expression/technical_quality thấp), không còn là lỗi validator/contract. Đã verify 3/6 case-run tổng cộng (E1 x2, E5 x1); E2–E4/E6 chưa chạy.

---

## 3. Quy ước kỹ thuật

### Naming
- **Brand trong AI prompt:** `"Ven Ho Hotel"` (không dấu) — áp dụng toàn bộ prompt/instruction sinh bởi hệ thống.
- **Brand trên website/content hiển thị:** `"Ven Hồ Hotel"` (có dấu) — không đổi.
- **Hashtag:** không dấu (`#HoTay`, không phải `#HồTây`).

### Contract versions
| Module | Contract | Ghi chú |
|--------|----------|---------|
| M01 DNA | `contract_version = "1.1"` | M02 accept `[1.1, 2.0)` |
| M02 Prompt | `contract_version = "1.0"` | Per prompt type |
| M05 Content output | `contract_version = "1.0"` | |
| M06 Video package | `contract_version = "1.0"` | Pre-render package only |
| M07 Publishing request/receipt | `contract_version = "1.0"` | Dry-run/publish receipt cho M08 |
| M08 Analytics outputs | `contract_version = "1.0"` | Raw metrics, unified snapshot, score, alert, advisory |
| M09 Agent request/response | `contract_version = "1.0"` | Plan/module request/risk/approval contract |
| M10 Home Workspace snapshot | `contract = "presentation_only"` | Read-only normalized view over module artifacts + founder-first home workspace snapshot |

### DNA subjects (venho_hotel)
`lake_view_room` · `deluxe_double` · `lobby` · `facade` · `linh_an` · `westlake` · `outside`

Mỗi subject có: `_DNA.md` + `_DNA.json` + `_DNA_COMPACT.md` + `overrides.yaml` + `dna_manifest_*.json`

### DNA subjects (linh_an) — Mode C Wardrobe Studio
`wardrobe` (base/custom) · `outfit_a_cafe` · `outfit_b_west_lake` · `outfit_c_street` · `outfit_d_business` · `outfit_e_sport`

Configs: `config/projects/linh_an/subjects/{subject}.yaml` — 22 aggregation keys: brand, garment_category, color_primary/secondary, top/bottom/dress description, fit, logo_branding, signature_design_elements, footwear, accessories, hair_style_suggestion, occasion_context, content_pillar_fit, **prompt_snippet**
Output: `data/projects/linh_an/knowledge/LINH_AN_{SUBJECT_UPPER}_DNA.md`
UI: Workbench → Tab "Linh An DNA — Mode C"

Mode C variant routing:
- `outfit_id = mint_green` → `schema_subject = outfit_e_sport` → `LINH_AN_MINT_GREEN_DNA.*`
- `outfit_id = nike_pink_running` → `schema_subject = outfit_e_sport` → `LINH_AN_NIKE_PINK_RUNNING_DNA.*`
- Không cho fallback `config/universal_schema.yaml` trong Mode C.
- `config/projects/linh_an/wardrobe_manifest.json` là registry tạm cho Phase 1: quarantine artifact cũ và ghi legacy aliases trước khi có Wardrobe Index 1.0 ở Phase 4.

### CLI commands (venho global PATH: `/Users/hanhpham/Library/Python/3.9/bin`)
```bash
venho vision observe --mode b --project venho_hotel --subject {subject} --input {dir}
venho vault search "từ khóa"
venho prompt --type {image,video,content,seo} --project venho_hotel --subject ... --brief "..."
venho validate image|prompt|face|content ...
venho auto run {workflow_id}
venho auto resume {run_id}
venho content --project venho_hotel --type {facebook,blog,...} --topic "..." --lang vi
venho content campaign --project venho_hotel --topic "..." --channels facebook,instagram,threads
venho content calendar --project venho_hotel --month 2026-08
venho-video generate --topic "lake view room morning" --duration 15 --type social_reel --subjects lake_view_room,westlake
python3 -m publishing_gateway.cli publish --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --approval-secret test-secret --dry-run
python3 -m publishing_gateway.cli retry --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --platform instagram --approval-secret test-secret --dry-run
python3 -m agent_studio.cli --agent marketing_agent --project venho_hotel --goal "Tạo campaign trải nghiệm mùa hè Hồ Tây" --plan-only
# VenHo OS UI (Next.js — Streamlit đã xóa 2026-07-13)
npm run dev   # → localhost:3000/os
```

### Integration seams đã verify (2026-07-09)
- M01→M02: DNA contract 1.1 nằm trong range M02 chấp nhận `[1.1, 2.0)` ✅
- M02→M05: `prompt_bridge` import `build_content_prompt` — signature khớp ✅
- M03→M05: `content_validator_bridge` gọi `validate_content` có degradation ✅
- M04 adapters → M01/02/03: cả 3 adapter gọi đúng public API ✅
- M02→M06: `prompt_bridge` gọi `build_video_prompt` cho từng scene prompt ✅
- M05→M06: `content_bridge` gọi Content Studio để lấy hook/caption/CTA ✅
- M03→M06: `validator_bridge` dùng prompt validation per scene; video-package validation degrade advisory ✅
- M04→M07: M07 kiểm `package_status=approved`, HMAC approval signature và TTL trước khi publish/dry-run ✅
- M07→M08: delivery receipt contract có `platform_results`, `public_url/post_id/status`, circuit breaker info và `analytics_handoff.ready_for_m08=true` ✅
- M08 loop: receipt → mock metrics → unified snapshot → score → sentiment → advisory/report chạy offline ✅
- M09→M04: goal → TaskPlan → ModuleRequest package luôn target `M04_AUTOMATION_STUDIO`; external impact cần manual gate, không gọi M07 trực tiếp ✅
- M10 Home Workspace v1.0: `dashboard.gateway` đọc config/artifacts của M01-M09, Face Lock display threshold, graceful advisory khi thiếu dữ liệu; Home dùng Today's Focus + Current Work + Needs Review + Ready to Publish + Quick Actions + Recent Activity; pipeline chuyển vào Workbench, system/debug chuyển vào Settings; không gọi API và không mutate data ✅

---

## 4. Cấu trúc thư mục chính

```
venho-ai-studio/
├── knowledge_studio/vision/   ← M01 core engine
├── prompt_studio/             ← M02 prompt builders + pipeline
├── validator_studio/          ← M03 validators + scoring
├── automation_studio/         ← M04 workflow runner + adapters
│   └── adapters/              ← lớp cô lập interface M01/M02/M03
├── content_studio/            ← M05 content builders + manifest
│   └── builders/              ← social, blog, website, OTA, FAQ, email
├── video_studio/              ← M06 video package pipeline
│   └── builders/              ← character, lifestyle, reel, explainer, hero
├── publishing_gateway/        ← M07 publishing guardrails, adapters, receipt
│   ├── adapters/              ← facebook, instagram, threads, google_business, mock
│   ├── schemas/               ← publishing request, delivery receipt, approval, result
│   ├── renderers/             ← receipt JSON/Markdown
│   └── utils/                 ← idempotency, time, URL, media upload helpers
├── shared/vision/             ← VisionClient, MockVisionClient, image_loader
├── agent_studio/              ← M09 request validation, routing, personas, planning, risk, M04 bridge
│   ├── agents/                ← base + generic agents
│   ├── schemas/               ← request/response/persona/task/module/risk contracts
│   ├── renderers/             ← response Markdown/JSON
│   └── templates/             ← persona/agent templates
├── [dashboard/ — DELETED 2026-07-13, thay bởi Next.js VenHo OS]
├── config/
│   ├── settings.yaml
│   ├── validation.yaml
│   └── projects/venho_hotel/
│       ├── subjects/          ← subject YAML + overrides.yaml
│       ├── content/           ← content_pillars, tone, platform_rules, SEO, calendar
│       ├── video/             ← camera_rules, character_rules, motion_rules...
│       ├── publishing/        ← platforms, approval, brand display, schedule, rate limit
│       ├── analytics/         ← metrics mapping, schedule, scoring, sentiment, feedback policy
│       ├── agents/            ← M09 personas + agent_policy
│       └── prompt_rules.yaml
├── data/projects/venho_hotel/ ← .gitignore (output data)
│   ├── knowledge/             ← DNA files
│   ├── prompts/               ← prompt JSON per type
│   ├── content/               ← draft content per channel
│   ├── video/                 ← video packages + video_manifest
│   ├── publishing/            ← fixture package + receipt store
│   ├── analytics/             ← raw metrics, snapshots, scores, advisories, alerts, reports
│   └── validation/            ← validation reports
├── tests/                     ← 430 tests, 0 API call
├── docs/                      ← plan docs + how-to guides
├── task_memory.md             ← file này — context chung AI Engine
└── task_status.md             ← status từng module
```

---

## 5. Linh An — AI KOL (quan trọng với M05/M06)

**Face Lock v3.1 (dùng khi không có `--ref`):**
```
Linh An, Vietnamese female influencer, 24 years old,
soft elongated oval face, slightly fuller cheeks, balanced facial proportions,
slim natural nose bridge, long almond eyes, horizontal eye emphasis,
slightly narrow eye opening, thin upper eyelid, warm brown irises,
very subtle outer corner lift, natural eye asymmetry,
low-position eyebrows, minimal arch, close eye-brow distance,
natural full lips with slightly thinner upper lip and slightly fuller lower lip,
very subtle upward lip corners, slightly shorter philtrum,
soft feminine jawline, delicate chin,
fair warm ivory skin, healthy natural glow, realistic skin texture, natural pores,
long dark chocolate brown layered wavy hair, natural center part,
small pearl drop earrings,
gentle feminine beauty, elegant Vietnamese appearance,
luxury lifestyle creator, consistent facial identity,
photorealistic, natural beauty,
no plastic skin, no doll face, no exaggerated makeup
```

**Reference images:** `ops/VenHoSocialManager/assets/` (trong Ven Ho Hotel repo)
- `B3_Hero.png` — 3/4 trái, score 9.4–9.5 **(PRIMARY)**
- `linh-an-master-face.png` — Master Face #001, lifestyle

**QC threshold:** ≥ 9.0 APPROVED · 8.0–8.9 CONDITIONAL · < 8.0 REJECT

---

## 6. Test discipline

- **KHÔNG BAO GIỜ** gọi real API trong pytest.
- Prompt Studio: luôn truyền `optimize_fn=optimize_mock` trong tests (default gọi Claude API thật, tốn tiền).
- Validator Studio: provider schema guards — test dùng fake clients.
- Content Studio: prose generator ở mock/deterministic mode trong tests.
- Video Studio (M06): prompt/content/validator bridges đều chạy offline/mock trong tests.
- Publishing Gateway (M07): pytest chỉ dùng dry-run/mock adapters; không đọc real token, không gọi platform API.
- Analytics Feedback (M08): pytest chỉ dùng `MockMetricsAdapter`; không gọi insights API thật.

---

## 7. Quyết định thiết kế quan trọng (không thay đổi)

| Quyết định | Lý do |
|-----------|-------|
| Pass 2A tất định (code-only) | Nếu LLM quyết định cấu trúc DNA → không tái lập được |
| Forbidden ở curated overlay | Single source, không bị overwrite khi regenerate |
| M05 prose dùng temperature > 0 | Module DUY NHẤT cho phép AI sáng tạo câu chữ |
| Manual gate trong M04 | Ảnh sinh bởi Flow/GPT Image (ngoài hệ thống) — không thể tự động hóa khâu này |
| M07 idempotency theo package/project/platform/content/schedule | Chặn duplicate publish; partial success chỉ retry failed platform |
| M07 adapters dry-run trước live | Bảo toàn 0 API call trong tests và tránh publish nhầm |
| Threads/Google Business feature-flag off mặc định | Conditional MVP cho tới khi đủ API access |
| M08 advisory-only | Feedback không tự apply vào M01/M05; luôn qua M04/M09 approval route |
| M08 raw/unified tách riêng | Audit được provenance và tránh mất raw platform metrics |
| M09 plans, M04 executes | Agent Studio chỉ tạo TaskPlan/ModuleRequest qua M04; không tự publish, không sửa Knowledge, không gọi M07 trực tiếp |
| M09 approval policy tập trung | Risk rules đọc từ `config/projects/<project>/agents/agent_policy.yaml`; destructive blocked, external impact approval |
| Staleness advisory (không auto-regen) | Nội dung theo ngày vẫn dùng được dù DNA nguồn cập nhật |
| Archive thuộc module con | M04 không biết format file của module khác |
| M06 storyboard templates theo video_type | character/social_reel/website_hero/explainer cần scene arc khác nhau — không dùng generic |
| M06 engine templates = AI-facing notes | Templates `video_studio/templates/{engine}.yaml` được embed vào engine prompt; không chứa nội bộ "Module XX" |
| M06 validator bridge dùng primary env subject | Lấy source_knowledge đầu tiên không phải linh_an/character để xác định subject cho M03 |

---

## 8. M07 Publishing Gateway — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline dry-run MVP  
**Plan:** `VENHO_AI_STUDIO_Module_07_Publishing_Gateway_Development_Plan_v1_2_QC.md`  
**Tests:** `python3 -m pytest` → 406/406 pass, 0 API call  
**Module tests:** 19 tests — `tests/test_publishing_gateway.py`, `tests/test_publishing_gateway_scaffold.py`

### Luồng M07 chính

```
PublishingRequest
→ Contract Validator
→ Approval Verifier
→ Brand Guard
→ Platform Capability Check
→ Idempotency / Receipt Store
→ Queue + Rate Limit + Circuit Breaker
→ Platform Adapter
→ Delivery Receipt
→ M08 Analytics Handoff
```

### Core files

- `publishing_gateway/gateway_router.py` — orchestrates guardrails, adapters, queue, receipt.
- `publishing_gateway/schemas/` — request/receipt/result/approval contracts.
- `publishing_gateway/approval_verifier.py` — HMAC-SHA256 signature + TTL.
- `publishing_gateway/receipt_store.py` — persistence source for idempotency and receipts.
- `publishing_gateway/adapters/` — Facebook, Instagram, Threads, Google Business, Mock.
- `publishing_gateway/cli.py` — `publish`, `retry`, `receipt`, `queue`, `version`.
- `config/projects/venho_hotel/publishing/` — platform flags, approval policy, brand display, schedule, rate limits.
- `docs/contracts/m07_to_m08_delivery_receipt.md` — M08 handoff contract.
- `docs/how_to_run_publishing_gateway.md` — dry-run and controlled live checklist.

### M07 boundaries

- M07 không tạo caption, hashtag, metadata, ảnh hoặc video.
- M07 không sửa nội dung đã duyệt.
- M07 không tự quyết định giờ đăng; MVP mặc định `publish_now=true`, scheduled execution là hậu-MVP.
- M07 không phân tích performance; chỉ ghi receipt cho M08.
- Real API publish chỉ là controlled manual test, không nằm trong pytest.

---

## 9. M08 Analytics & Feedback Loop — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline MVP  
**Plan:** `VENHO_AI_STUDIO_Module_08_Analytics_Feedback_Development_Plan_v1_2_QC.md`  
**Tests:** `python3 -m pytest` → 413/413 pass, 0 API call  
**Module tests:** 7 tests — `tests/test_analytics_feedback.py`

### Luồng M08 chính

```
M07 Delivery Receipt
→ Ingestion Router
→ Collection Scheduler
→ Mock Metrics Adapter
→ Raw Metrics Store
→ Unified Metrics Standardizer
→ Stats Calculator
→ Snapshot Store
→ Baseline Calculator
→ Performance Scorer
→ Sentiment Guardrail
→ Alert / Feedback Advisory / Report
```

### Core files

- `analytics_feedback/schemas/` — delivery receipt ref, raw metrics, unified metrics, score, alert, advisory.
- `analytics_feedback/adapters/mock_metrics.py` — deterministic offline metrics/comments.
- `analytics_feedback/ingestion_router.py` + `collection_scheduler.py` — M07 receipt to collection tasks.
- `analytics_feedback/metrics_standardizer.py` + `utils/stats_calculator.py` — raw to unified + derived metrics.
- `analytics_feedback/baseline_calculator.py` + `performance_scorer.py` — baseline group and labels.
- `analytics_feedback/sentiment_scorer.py` + `alert_generator.py` — vi/en keyword guardrail and critical alerts.
- `analytics_feedback/feedback_advisory_generator.py` + `report_generator.py` — pending approval advisory/report outputs.
- `config/projects/venho_hotel/analytics/` — schedule, mapping, scoring, sentiment, feedback policy.

### M08 boundaries

- M08 không publish, không sửa content đã đăng, không gọi M07 để publish lại.
- M08 không tự ghi M01 Knowledge hoặc M05 Content Strategy.
- M08 chỉ tạo advisory/alert/report; apply phải qua M04 Manual Gate hoặc M09 workflow có approval.
- Real platform insights adapters là phase sau; pytest giữ offline 100%.

---

## 10. M09 Agent Studio — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline planning/orchestration MVP, reviewed  
**Plan:** `VENHO_AI_STUDIO_Module_09_Agent_Studio_Development_Plan_v2_2_QC.md`  
**Tests:** `python3 -m pytest` → 423/423 pass, 0 API call  
**Module tests:** 10 tests — `tests/test_agent_studio.py`

### Luồng M09 chính

```
AgentRequest
→ Request Validator
→ Agent Router
→ Persona Resolver
→ Context Loader
→ Missing Knowledge Detector
→ Task Planner
→ Risk Classifier
→ Module Request Builder
→ M04 Automation Bridge
→ Result Aggregator
→ Markdown / JSON Response
```

### Core files

- `agent_studio/schemas/` — request/response/persona/task/module/risk/execution contracts.
- `agent_studio/request_validator.py` — validates required request fields and contract shape.
- `agent_studio/agent_router.py` — routes generic/project-specific agent ids.
- `agent_studio/persona_resolver.py` — loads persona config from project YAML.
- `agent_studio/context_loader.py` — loads knowledge, analytics, prompt refs without inventing missing data.
- `agent_studio/missing_knowledge.py` — detects required knowledge gaps and returns `ERR_MISSING_KNOWLEDGE`.
- `agent_studio/task_planner.py` — deterministic goal-to-task-plan MVP.
- `agent_studio/risk_classifier.py` — reads `agent_policy.yaml`, marks approval gates, blocks destructive actions.
- `agent_studio/module_request_builder.py` — packages every task as M04-targeted `ModuleRequest`.
- `agent_studio/automation_bridge.py` — offline/mock M04 bridge for MVP.
- `agent_studio/result_aggregator.py` + `renderers/` — AgentResponse Markdown/JSON.
- `agent_studio/cli.py` — `python3 -m agent_studio.cli --agent marketing_agent --project venho_hotel --goal "..." --plan-only`.
- `config/projects/venho_hotel/agents/` — `agent_policy.yaml`, `marketing_agent.yaml`, `linh_an_brand_agent.yaml`, `hotel_ops_agent.yaml`.

### M09 boundaries

- M09 là cognitive interface / orchestration layer, không phải execution engine.
- M09 không tự publish, không gọi Meta/Google/Threads API, không gọi M07 trực tiếp.
- M09 không tự sửa Knowledge hoặc Content Strategy.
- M09 chỉ đọc M08 advisory; không tự thu thập hoặc tính metrics.
- M09 luôn đóng gói execution intent qua M04.

### Review notes / follow-up

- Review 2026-07-09: MVP đạt, module tests 10/10 và full suite 423/423 pass.
- **Fixed (373b1cc):** execute mode bị block khi missing_knowledge (fallback dry_run); gate task không bị slice; status đổi thành `PARTIAL` thay vì `FAILED` khi plan vẫn valid.
- **Superseded by Phase 6 (2026-07-16):** missing knowledge giờ hard-stop trước M04 dispatch; không còn fallback/dry-run dispatch khi thiếu required knowledge.
- Follow-up execution: `--execute` hiện vẫn là prepared/mock M04 bridge; khi chuyển sang execution thật phải nối qua public API của M04, vẫn giữ approval gate.

---

## 11. M10 VENHO OS Home Workspace — historical Streamlit milestone, superseded 2026-07-13

**Status:** HISTORICAL. Runtime hiện tại là Next.js `venho-os`; block này giữ lại để truy vết trước khi Streamlit bị xóa.
**Tên chính thức:** **Mother Dashboard** — đặt bởi Harry 2026-07-13
**Plan:** `VENHO_AI_STUDIO_Module_10_Dashboard_Plan_v1_2.md`  
**Design:** `/Users/hanhpham/Developer/VENHO_OS_HOME_WORKSPACE_UI_SPEC_v1.0.md` + `/Users/hanhpham/Developer/VENHO_OS_UI_DESIGN_SPEC_v1.0.md`
**Tests:** `python3 -m pytest -q` → 430/430 pass, 0 API call
**Module tests:** 7 tests — `tests/test_dashboard.py`

### Quyết định kiến trúc

M10 mở rộng Studio Shell Streamlit hiện có (`ui/studio_app.py`) thay vì tạo Next/Nuxt/Vite app riêng. Lý do: repo đã có local-first Studio Shell tại `localhost:8501`, nên M10 giữ một entrypoint duy nhất và tránh thêm stack mới.

Sau bản `VENHO_OS_HOME_WORKSPACE_UI_SPEC_v1.0.md` và `VENHO_OS_UI_DESIGN_SPEC_v1.0.md`, M10 không được xem là technical dashboard nữa. M10 là Business Operating Workspace cho founder: workspace-first, execution-first, one primary mission, giảm tải nhận thức, Home ưu tiên việc cần làm tiếp theo thay vì module internals.

### Core files

- `dashboard/gateway.py` — read-only adapter đọc M01-M09 config/artifacts và tạo `DashboardSnapshot` + `operating_center` workspace fields (`header`, `today_focus`, `current_focus`, `needs_review`, `ready_to_publish`, `quick_actions`).
- `dashboard/__init__.py` — module metadata (`MODULE_ID = "M10"`).
- `ui/studio_app.py` — render `VENHO OS — Home Workspace` với navigation Home Workspace, Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports, Settings; đồng thời giữ Studio Shell Mode A / Mode B.
- `docs/how_to_run_studio_ui.md` — hướng dẫn chạy shell + dashboard.

### Home Workspace UI v1.0

- Header: `VENHO OS (Home Workspace)`, project `Ven Hồ Hotel`, last sync, notifications/user affordances, build Home Workspace v1.0.
- Sidebar label: `VENHO OS` / `Business Operating Workspace`.
- Sidebar navigation: Home Workspace, Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports, Settings.
- Priority order: Today's Focus → Current Work → Needs Review + Ready to Publish → Quick Actions → Recent Activity.
- Home không hiển thị pipeline, analytics, system health, large KPI counters, raw JSON.
- Pipeline/workflow nằm trong Workbench; raw JSON/debug/system tools nằm trong Settings.
- Quick Actions: Build DNA, Generate Prompt, Validate, Publish, Video, Automation.

### Studio Shell upload/output UX

- Mode A có `Nguồn ảnh input`: Folder có sẵn hoặc Upload ảnh; upload lưu vào `data/projects/_inbox/media`.
- Mode B có `Nguồn ảnh input`: Folder có sẵn hoặc Upload ảnh; upload lưu vào `data/projects/{project}/media/{subject}`.
- Mode A/B provider mặc định là `mock` để test offline, không cần `OPENAI_API_KEY`; `openai`, `claude`, `config mặc định` vẫn chọn được khi có credentials.
- Mode A hiển thị output path và nút `Mở folder output`; mặc định `data/projects/_inbox/output`.
- Mode B hiển thị output path và nút `Mở folder output`; mặc định `data/projects/{project}/knowledge`.
- Nút mở folder tự tạo folder nếu chưa có và mở Finder trên macOS.

### Workflow pages v2.0

- Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports dùng card-based panels thay vì dense tables.
- Workbench ưu tiên Continue Working, Pending Reviews, Draft Outputs, Ready To Publish, Failed Items.
- Publishing tách Ready, Waiting Approval, Scheduled, Published, Failed dưới dạng cards.
- Insights giữ advisory-only; khi có dữ liệu hiển thị Overview + Recommendations cards, khi chưa có dữ liệu hiển thị empty state rõ ràng.
- Raw JSON và dataframes chỉ còn trong `System` developer area.

### M10 boundaries

- Không có DB nghiệp vụ riêng; chỉ đọc `config/projects/`, `data/projects/`, `data/automation_runs/`.
- Không tính lại score/verdict/HMAC; chỉ hiển thị output do module core tạo.
- Không build prompt, không build ModuleRequest, không render/upload/publish.
- Missing artifact tạo advisory theo module thay vì làm sập dashboard.
- Face Lock gate chỉ là display mapping theo plan: `>=9.0 APPROVED`, `8.0-8.9 CONDITIONAL`, `<8.0 REJECT`; score 0-100 được normalize để hiển thị.
- Quick actions trong Workbench là UI entrypoints/disabled placeholders ở MVP; không kích hoạt business logic hay external workflow trực tiếp.
- Phase 5 Command Palette (`Cmd+K`) là follow-up của Streamlit MVP cũ, không còn là acceptance gate của runtime Next.js hiện tại.

---

## 12. Creative Studio — M10 Extension (2026-07-09)

**Status:** ✅ COMPLETE — 3 modes tích hợp vào `ui/studio_app.py`

### Các mode

| Mode | Chức năng |
|------|----------|
| **Tạo Ảnh AI** | Topic/scenario/outfit/action → assemble prompt → `generate_image.py` subprocess → hiển thị ảnh trong UI |
| **Tạo Social Post** | Content Strategy v2.0 analysis (persona/funnel/golden rule) → caption prompt template → tạo ảnh AI + lưu `meta.json` |
| **Tạo Video Script** | Auto-number → sinh script 3 scene × Seedance prompt → preview + Lưu `.md` vào `scripts/` |

### Path constants (đầu `studio_app.py`)
```python
VENHO_HOTEL_DIR = BASE_DIR.parent.parent / "Ven Ho Hotel"   # projects/Ven Ho Hotel/
SOCIAL_MANAGER_DIR = VENHO_HOTEL_DIR / "ops" / "VenHoSocialManager"
VIDEO_SCRIPTS_DIR = VENHO_HOTEL_DIR / "local-generated" / "social-video" / "scripts"
```

### Fix quan trọng

1. **`Path(__file__).resolve()`** — Streamlit đôi khi truyền `__file__` = `ui/studio_app.py` (relative). Không có `.resolve()` → `SOCIAL_MANAGER_DIR` = `Ven Ho Hotel/ops/...` (relative, không tồn tại). Bắt buộc dùng `.resolve()`.

2. **Timeout 300s** — gpt-image-2 + `--ref` (image editing) thường mất 90–150s. 120s không đủ.

3. **Action prompt formula v2 (2026-07-10)** — single integrated sentence, NO `\n\n` break. gpt-image-2 treats `\n\n` as paragraph separator → renders two separate entities → character disappears. Công thức: `"Linh An {action}, she is a Vietnamese female lifestyle influencer, 24 years old, ... wearing {outfit}, ... she is the MAIN SUBJECT in the foreground, full body visible, no conical hat, photorealistic."` — tất cả một câu liên tục. Thêm `"MAIN SUBJECT in the foreground, full body visible"` để AI giữ nhân vật ở foreground. Lens: 35mm (không phải 85mm portrait) cho full-body action shots.

4. **`use_ref` toggle** — gpt-image-2 `--ref` dùng image editing từ ảnh gốc (Linh An đứng) → không thể thay đổi toàn bộ body pose (đạp xe, chạy, ngồi). Bỏ `--ref` = text-to-image mode → AI tự do tạo bất kỳ pose.

5. **Outfit E — Nike AeroSwift** (cập nhật 2026-07-13 từ ảnh thật) — `"mint-green Nike racerback loose crop tank top, dual Swoosh logos at collar, perforated ventilation panels on chest and back, mint-green Nike running shorts (3-inch inseam) with mesh waistband and small Swoosh logo on leg, white Nike running shoes, white ankle socks, sleek high ponytail"`. Khi outfit_key bắt đầu bằng "E — Sport", hair tự động đổi sang `"tied back in a sporty ponytail"`.

6. **Textarea cache bug (fix 2026-07-13)** — `st.text_area(key="tai_prompt")` khiến Streamlit cache giá trị cũ khi user thay inputs (checkbox/outfit/action). Fix: bỏ `key` khỏi textarea. Prompt luôn reflect trạng thái inputs hiện tại.

7. **Prompt structure action mode (fix 2026-07-13)** — Character + environment giờ join `\n` (1 dòng) thành 1 block duy nhất thay vì `\n\n` riêng. Format mới: `"Linh An {action} in the scene, she is the MAIN SUBJECT prominently in the foreground...\nSetting: {env}"` — gpt-image-2 không còn coi character/env là 2 entity độc lập.

8. **Quick Actions nav pattern (fix 2026-07-13)** — Không thể set `st.session_state["m10_section"]` sau khi sidebar radio widget đã instantiate (StreamlitAPIException). Fix: dùng `_m10_nav_pending` key trung gian; apply vào `m10_section` ở đầu `_render_dashboard()` TRƯỚC khi sidebar radio được tạo.

### Quy tắc `use_ref`

| Checkbox | Dùng khi | Face score | Kết quả |
|----------|----------|-----------|---------|
| ✅ Có ref | Portrait / Standing / Leaning / Tựa lan can | ~9/10 | Linh An đúng khuôn mặt ✅ |
| ☐ Không ref | Full-body action (đạp xe, chạy, ngồi, nhảy) | 7–8.5/10 | Action đúng, nhân vật xuất hiện ✅, face generic |

### Outfit mapping

| Key | Mô tả | Hair tự động | Dùng khi |
|-----|-------|-------------|---------|
| A — Cafe Girl | cream knit top, beige A-line skirt | wavy | Cafe, lifestyle |
| B — West Lake Sunset | flowing white dress, minimal gold jewelry | wavy | Hoàng hôn, lãng mạn |
| C — Street Style | white button-up, high-waist trousers, denim jacket | wavy | Phố phường |
| D — Business Travel | light beige blazer, white blouse | wavy | Professional |
| E — Sport & Active | mint-green Nike racerback crop tank + running shorts (3-inch), white Nike shoes | ponytail | Cycling, running, active |

### Caption generation decision

`/tao-social-post` trong UI **không** gọi AI API trực tiếp để viết caption — sinh sẵn prompt template để Harry copy sang ChatGPT. Lý do: M05 Content Studio dùng mock prose generator, không nối API thật; tránh thêm API key/cost vào Streamlit UI.

---

## 13. VenHo OS — Next.js Dashboard (2026-07-13)

**Status:** ✅ Stage A+B+C COMPLETE · Build 34/34 pages, 0 TS error
**Location:** `Ven Ho Hotel/src/app/os/` + `src/components/os/` + `src/app/api/v1/studio/`
**URL:** `localhost:3000/os` (chạy bằng `npm run dev` hoặc `run-venho-os.command`)

### Architecture
- RSC page `src/app/os/page.tsx` reads `?section=` query param, routes to section components
- Section routing via `<Link href="/os?section=xxx">` — no `useSearchParams()` in client components
- `src/lib/studio/paths.ts` — path constants (venho-ai-studio, VenHoSocialManager, video scripts)
- `src/lib/studio/constants.ts` — Python constants ported to TS (outfits, env blocks, pillars, scenes)
- `src/lib/studio/prompt-builder.ts` — pure TS port of 3 Python functions (assembleImagePrompt, buildCaptionPrompt, generateVideoScript)
- `src/components/os/shared/ui.tsx` — shared UI primitives (SectionHeader, Field, PrimaryBtn, CopyBtn, TabBar)

### API Routes (`/api/v1/studio/`)
| Route | Method | Chức năng |
|-------|--------|-----------|
| `observe` | POST | SSE stream `venho vision observe` (Mode A/B) |
| `generate-image` | POST | `generate_image.py` subprocess → imagePath |
| `file` | GET | Serve local files (generated images) — whitelist dirs + exts |
| `save-script` | GET/POST | Next script number / save `.md` to scripts dir |
| `dna` | GET | List DNA subjects + read COMPACT content |
| `vault-search` | POST | Full-text search across all `*_DNA*.md` files |
| `social-index` | GET | Read `database/index.json` → social post history |

### Sections implemented
| Section | Tabs |
|---------|------|
| Workbench | Mode A (Observe) · Mode B (Build DNA) — SSE live log |
| Creative Studio | Tạo Ảnh AI · Tạo Social Post · Tạo Video Script |
| Knowledge | DNA Library · Vault Search · Mode C — Linh An |
| Reports | DNA Status · Social Content Log |
| Others (8) | PlaceholderSection — Projects, Tasks, Agents, Operations, Publishing, Settings |

### Quan trọng
- `venho` CLI path: `/Users/hanhpham/Library/Python/3.9/bin` phải inject vào `PATH` trong spawn
- DNA content dir: `data/projects/venho_hotel/knowledge/` trong venho-ai-studio
- Social post index: `ops/VenHoSocialManager/database/index.json` trong Ven Ho Hotel repo
- File API whitelist: `SOCIAL_MANAGER_DIR`, `VIDEO_SCRIPTS_DIR`, `STUDIO_DIR`
- Next.js 16: `searchParams` là `Promise<{section?: string}>` — bắt buộc `await`

### Cleanup 2026-07-13 — Xóa Streamlit
- `ui/studio_app.py` + `ui/` — DELETED (2.335 dòng)
- `dashboard/gateway.py` + `dashboard/__init__.py` + `dashboard/` — DELETED (774 dòng)
- `tests/test_dashboard.py` — DELETED (149 dòng); test suite giảm từ 430 → 423
- `docs/how_to_run_studio_ui.md` — DELETED
- Next.js VenHo OS (`localhost:3000/os`) là entrypoint UI duy nhất

---

## 14b. Growth Agent v3.1 — Cutover thay VenHoSocialManager (2026-08-04)

Harry chốt: Growth Agent v3.1 (repo này) sẽ **thay thế hoàn toàn** `VenHoSocialManager` (repo `venho-os`, GitHub Actions T2/T4/T6 8AM, đăng thẳng FB/IG/Threads qua Make.com không qua duyệt thủ công) — không chạy song song. Thêm T7 (nội dung đặc biệt) cùng giờ.

**Đã nối trong repo này (2026-08-04):** `M07PublishingBridge.dispatch()` route theo `command["platform"]` → `ZaloOAAdapter` (zalo) hoặc `MakeGatewayAdapter` (facebook/instagram/threads). Cả hai adapter dùng chung 1 pattern: bắn webhook có ký HMAC, không gọi API platform trực tiếp, trả `GATEWAY_ACCEPTED`/`GATEWAY_ERROR` ngay — trạng thái `PUBLISHED` thật đến sau qua `callback_receiver.py` hoặc `reconciliation.py`. `daily_dispatch()` nhận `bridge` tiêm được.

**Sửa 2026-08-06 — tách webhook Make (Harry chọn phương án A):** việc "tái dùng scenario Make.com cũ" ở trên là **sai thiết kế và đã gỡ**. Legacy `post_to_make.py` gửi payload phẳng có `url`/`photo_url`/`image_public_url`/`message`; `MakeGatewayAdapter` gửi `content` lồng + `image_url` (thường = `null` vì Content Studio không tạo ảnh) và **không có** field `url`. Dùng chung 1 webhook → module `HTTP - Download a file` của scenario legacy báo `BundleValidationError: Missing value of required parameter 'url'`. Thực tế 2026-08-04 19:47–19:49 (giờ VN) Growth Agent đã bắn 12 request thật (`GATEWAY_ACCEPTED`, `image_url=None`) vào webhook legacy → tất cả fail phía Make. Nay `m07_publishing_bridge_from_env()` đọc `MAKE_GROWTH_WEBHOOK_URL`/`MAKE_GROWTH_WEBHOOK_SECRET`, **không fallback** về `MAKE_WEBHOOK_URL` — chưa cấu hình thì adapter `enabled=False`, không gửi gì. Có test hồi quy `test_m07_bridge_from_env_ignores_legacy_social_agent_webhook`. Việc còn lại của Harry: tạo scenario Make riêng cho Growth (clone scenario legacy, đọc caption từ `content.text`, filter router theo `platform` thay vì `publish_to_facebook`) rồi điền URL vào `.env.local`.

**Sửa tiếp 2026-08-06 — ảnh fallback (`publishing_gateway/fallback_images.py`):** `image_url = null` là nguyên nhân *thứ hai* độc lập — kể cả có scenario riêng, module `HTTP - Download a file` vẫn bắt buộc có `url`, và FB "Create a Post with Photos" / IG "Create a photo post" đều bắt buộc có ảnh. Growth phần lớn chạy không sinh ảnh (Content Studio chỉ ra `visual_note`) nên `null` là trường hợp thường, không phải ngoại lệ. Nay: `daily_cycle` thay bằng ảnh khách sạn thật theo `dna_subject` khi không có ảnh sinh ra, và ghi `content.image_is_fallback = true` để người duyệt phân biệt được; `MakeGatewayAdapter` có thêm 1 lớp chặn cuối (`or fallback_image_url()`) cho các row cũ đã lưu `null`. Bộ ảnh tái dùng đúng `ref_image` của `venho-social-content-agent/pillars.json`, re-encode 1440px JPEG và host công khai trên website: `Ven Ho Hotel/public/images/Social-fallback/{hotel-front-view,lobby,reception,lake-view-room}.jpg` → `https://venhohotel.com/images/Social-fallback/...`. Harry đã push repo `Ven Ho Hotel` (commit `871d7bd`) — cả 4 URL đã verify sống thật (HTTP 200, `image/jpeg`). Test: `test_make_adapter_never_sends_null_image_url`, `test_run_daily_cycle_falls_back_to_hotel_photo_when_no_image_generated`.

**3 gap kiến trúc thật còn lại trước khi cutover được (không phải việc nhỏ, cần thiết kế riêng từng cái):**
1. **Không có orchestrating command nào** nối `preflight → trend_lane/special_lane → run_content_pipeline → manage_queue → daily_dispatch` thành 1 lệnh chạy được — cần cho lịch T2/T4/T6/T7.
2. **Approve trên VENHO OS Dashboard chưa nối vào đây.** Section "Publishing & Schedule" hiện tại (`venho-os/src/components/os/sections/PublishingSection.tsx` + API `/api/v1/studio/topic-schedule`) là hệ thống cũ — duyệt **topic** cho VenHoSocialManager, ghi thẳng vào 1 file JSON + `git commit`, hoàn toàn không đụng tới `PublicationRegistry`/M07 của repo Python này. Cần route/section mới ở `venho-os` gọi ngược vào Python (shell-out CLI hoặc API nội bộ) mới có "bấm Approve → dispatch thật".
3. **Chưa có tạo ảnh thật.** `content_studio/builders/social_builder.py::mock_social_generator` là mock thuần. M02 Prompt Studio đã build prompt ảnh thật từ DNA (`venho prompt --type image`, complete) — còn thiếu đúng adapter gọi OpenAI images API (gpt-image-2 + ref ảnh), theo pattern dependency-injected-HTTP giống Tavily/Telegram/Zalo (§ test discipline).

**Cập nhật 2026-08-04 — cả 3 gap đã có glue thật (chi tiết đầy đủ: `task_status.md` mục cùng ngày):**
1. `growth_orchestrator/application/daily_cycle.py::run_daily_cycle(day)` + CLI `venho-growth daily-cycle` + `.github/workflows/growth-daily-cycle.yml` (cron Mon/Wed/Fri/Sat 08:00 ICT) — sinh draft thật qua `content_studio.generate_content()`, queue `PENDING_APPROVAL` trong `PublicationRegistry`, KHÔNG dispatch.
2. `growth_orchestrator/application/approve_and_dispatch.py` + CLI `venho-growth approve-and-dispatch` — Approve gọi `M07PublishingBridge.dispatch()` thật. Nối sang `venho-os` qua 2 route mới (`/api/v1/studio/growth/pending`, `/api/v1/studio/growth/[id]/approve`) shell-out `venho-growth` (pattern có sẵn từ `generate-image`/`observe`), UI thêm vào `PublishingSection.tsx`. **venho-os hiện có rất nhiều uncommitted WIP không liên quan (~60 file, có vẻ refactor design-token) — code mới nằm trong working tree đó nhưng CHƯA được `git add`/commit, cố tình để Harry tự commit.**
3. `image_studio_runtime/adapters/gpt_image_provider.py::GPTImageProvider.generate()` hết `NotImplementedError` — gọi thật `client.images.generate()`/`.edit()` (dependency-injected client, mặc định `openai.OpenAI()`). Còn thiếu: resolve `reference_asset_ids` → file ảnh thật (ref ảnh nằm ở `venho-os/ops/VenHoSocialManager/assets/`, cross-repo, chưa nối), và `generate_image_run()` chưa được gọi từ `daily_cycle.py` (pipeline hàng ngày chưa tự sinh ảnh).

Chỉ tắt workflow `venho-os/.github/workflows/social-content.yml` sau khi 3 gap trên hoàn thiện thật (đặc biệt: ref ảnh thật + daily_cycle gọi image gen + venho-os UI test qua browser) và test tay ít nhất 1 chu kỳ thật.

**Cập nhật 2026-08-04 — audit theo 27 DoD của `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` Phần 18 + việc 1-5 (chi tiết: `task_status.md` mục cùng ngày):**
- **Phát hiện gốc:** `daily_cycle.py` (bản 2026-08-04 sáng) bỏ qua toàn bộ safety rail v3.1 thật — không CreativeBrief, không qua M03, không khoá exact-version khi duyệt. Đã sửa: giờ build `CreativeBrief` LOCKED thật (contract-validated) → `run_content_pipeline` → `M05ContentBridge` (thật, gọi `content_studio`) → `M03ValidatorBridge` (claim + alignment gate) → chỉ queue khi `READY_FOR_REVIEW`. `approve_and_dispatch()` giờ dùng `automation_studio/approval_snapshot.py` thật (đã có sẵn từ trước, chưa ai dùng) để khoá exact-version tại thời điểm duyệt.
- **Research OS:** không dùng weather để demo R3 (R2-T theo thiết kế KHÔNG BAO GIỜ lên R3 — xem Phần 6.6 "Ranh giới quyết định", đây là hành vi đúng không phải bug). Thay vào đó phát hiện `seed_facts.json` đã có 4 fact `approved_by: harry` từ trước nhưng chưa từng persist — thêm CLI `venho-research load-seed-facts`, đã chạy thật. KHÔNG tự ý promote fact mới nào (founder gate, DoD #13 cấm auto-promote) — cần Harry xác nhận trước.
- **Ảnh:** ref ảnh thật hoá ra nằm ngay trong repo này (`assets/raw/`), không phải `venho-os` như ghi nhận cũ ở trên (đã kiểm tra lại). `agent_studio/growth/reference_asset_resolver.py` + `config/projects/venho_hotel/growth/reference_assets.yaml` map ID → file thật (chọn tạm, Harry nên duyệt lại). `daily_cycle.py` giờ sinh 1 ảnh thật/ngày qua M02 (`build_image_prompt`) → `GPTImageProvider`/`MockImageProvider`. Còn thiếu: ảnh chưa gắn vào payload webhook Make.com (cần bước upload lấy URL công khai, kiểu Google Drive upload cũ của VenHoSocialManager).
- **M08 Analytics:** `observe()` hết trả `pending_observation` giả — chạy chain thật (standardize/baseline/score/sentiment/advisory/report, lưu store thật) khi publication có `platform_post_id`. `metrics_adapter_factory` mặc định `MockMetricsAdapter` — chưa có adapter thật gọi FB/IG Insights hay Zalo OA (việc riêng, cần credentials).
- **Rủi ro thật phát hiện, CHƯA sửa (ngoài phạm vi việc 1-5):** `providers/openai_provider.py` gọi `load_dotenv(BASE_DIR / ".env")` ở top-level module import — bất kỳ test nào import module này rò `OPENAI_API_KEY` thật (từ file `.env` gốc, khác `.env.local`) vào `os.environ` cho cả tiến trình pytest. Đã tự vệ trong test của mình (luôn tiêm provider/`generate_image=False` tường minh, không dựa vào env default), nhưng bug gốc vẫn còn đó — bất kỳ ai thêm code mới đọc `os.environ` cho default nhạy cảm sẽ dính lại.
- **Audit tổng:** ~3/27 DoD đạt chắc chắn sau việc 1-5, phần lớn (Research OS 8/9 domain thật, hạ tầng Mac Mini/deadman switch, Analytics thật, blog SEO T3, 16-slot/4-tuần) vẫn chưa chạm — hệ thống ở khoảng Phase 3-4/8 theo roadmap gốc, không phải "growth agent hoàn chỉnh".
- **Quyết định của Harry (2026-08-04):** (1) Hạ tầng — **giữ GitHub Actions**, không xây Mac Mini 24/7 + deadman switch như plan gốc v3.1 §10 (đơn giản hơn, chấp nhận không có heartbeat/cloud-fallback tự động — rủi ro chấp nhận được vì publish vẫn qua bước Approve thủ công). (2) Research OS — **không promote fact mới nào lúc này**, 4 fact seed hiện có (room_count/address/website/review.agoda_overall) là đủ cho content hiện tại; quay lại khi có nghiên cứu thật (guest_voice/competitor/...).

## 14c. Growth Agent v3.1 — Review lần 2: đóng 7/8 gap DoD (2026-08-04)

Harry: "Review lại task đang làm so với plan v3.1. Phần nào chưa làm xong, hoàn thiện nốt." Trước khi sửa, dùng 1 agent Explore verify lại 8 điểm còn mập mờ từ audit trước bằng đọc code thật (không tin note cũ) — full chi tiết từng gap + số dòng: `task_status.md` mục cùng ngày "Review lần 2".

**Đóng được 7/8 (đều là glue code có sẵn từng phần, chưa nối, không cần dữ liệu kinh doanh mới):**
1. `tests/test_growth_brand_safety_gate.py` — 24 test cho `BrandSafetyGate` (trước đó là 0, DoD #19 yêu cầu ≥15).
2. `daily_cycle._pick_topic()` nối thật `special_lane.select_special_lane_candidate()` cho Thứ 7 — loại-4 fallback giờ chạy thật mỗi tuần (mặc định `feature_story` vì chưa có nguồn trend thật), không còn là code chết chỉ có test riêng.
3. `package_snapshot["asset_version_ids"]` giờ lấy `run_folder.name` (run_id thật) thay vì luôn `[]`.
4. `M08AnalyticsBridge.observe()` giờ gọi `generate_research_question_from_analytics()` thật sau advisory — ghi câu hỏi vào `research/questions/` (vault thật).
5. `_generate_topic_image()` nối `validator_studio.image_validator.validate_image()` (DNA-match, provider mock mặc định) — kill_switch loại ảnh vi phạm, report ghi cạnh artifact.
6. **Phát hiện quan trọng:** pipeline thật không bao giờ đạt status `PUBLISHED` (Make.com adapter fire-and-forget) → M08 Analytics nối ở lượt trước **không chạy được ngoài test**. Thêm `reconcile_publication()` + CLI `venho-growth reconcile` — thao tác tay của Harry sau khi kiểm tra bài đăng thật, chuyển GATEWAY_ACCEPTED → PUBLISHED. Đây là "reconciliation evidence" DoD #3 chấp nhận.
7. `run_blog_pipeline()` mới + CLI `venho-growth blog` — nối `content_studio` blog builder với `knowledge_studio.facts.FactResolver` thật (4 fact seed đã duyệt), chỉ trích fact đã approved+còn hạn, không bịa. Verify chạy tay thật, không chỉ test.

**KHÔNG làm — DoD #26 (golden-set scorecard):** cơ chế tính điểm đã thật (`controlled_rollout/scorecard.py`), nhưng không có bộ dữ liệu golden thật nào — cần Harry tự chọn bài/ảnh đã publish làm chuẩn, không phải việc code tự bịa được, khác các gap khác.

**Verify:** 636/636 pass (598 + 38 mới), 0 API call, compileall sạch, `venho-growth --help` có `blog`+`reconcile`, chạy tay `venho-growth blog` ra bài thật trích đúng 4 fact.

## 14d. Growth Agent v3.1 — Model switch gpt-5.5, Validator gate thật, fix hex-code leak, lên lịch tuần (2026-08-04)

Chuỗi yêu cầu liên tiếp của Harry: bài chờ duyệt sơ sài → sinh lại theo prompt mới + lên lịch tuần (giống content agent cũ, duyệt 1 lần/tuần); chuyển generator từ `claude-sonnet-5` sang `gpt-5.5` ("Sonnet 5 đang viết ở mức trung bình không đạt"); lỗi bấm Phê Duyệt (`JSONDecodeError`); Validator phải chấm điểm thật cả bài viết lẫn ảnh, không pass phải tự làm lại; bài viết lộ mã màu hex + tiếng Anh kỹ thuật; nạp thêm credit sau khi hết billing.

1. **Generator đổi sang gpt-5.5** — `content_studio/generators/gpt_social_generator.py` mới là `generator_fn` mặc định trong `M05ContentBridge` (`chat.completions.create(model="gpt-5.5", response_format={"type":"json_object"}, max_completion_tokens=4096)`). 3 system prompt dùng chung (`content_studio/generators/social_prompts.py`) — `claude_social_generator.py` giữ lại làm fallback/A-B, không còn default.
2. **Validator gate thật cho text** — `M03ValidatorBridge.validate_package()` giờ gọi `validator_studio.content_validator.validate_content()` thật (không chỉ claim/alignment như trước); chỉ `Recommendation.APPROVE` mới `READY_FOR_REVIEW`. `daily_cycle.run_daily_cycle()` retry tối đa `MAX_TEXT_ATTEMPTS=3` lần/platform nếu không pass, bỏ qua platform đó nếu vẫn fail sau 3 lần (không queue nội dung dưới chuẩn).
3. **Validator gate thật cho ảnh** — `_generate_topic_image()` retry `MAX_IMAGE_ATTEMPTS=2`, chỉ giữ ảnh khi `not kill_switch.triggered and verdict == APPROVE`; hết lượt thì bỏ ảnh (bài vẫn queue, không có ảnh) thay vì giữ ảnh không đạt.
4. **`_score_brand_fit` sửa gốc (`validator_studio/content_validator.py`)** — trước tính overlap token với `dna["invariant"]` (English/hex kỹ thuật cho ảnh AI) → xung đột trực tiếp với rule "không copy hex/tiếng Anh kỹ thuật vào content": bài viết càng đúng chuẩn (paraphrase hết) càng bị điểm thấp. Giờ chỉ tính overlap với `prompt_rules.brand_dna` (ngôn ngữ định vị thương hiệu thật: tên khách sạn, tagline...), hex đã strip khỏi nguồn, baseline 70 thay vì 45. Đã verify bằng script thật: 1 mẫu real content tăng từ overall 81.59/brand_fit 57.86 → overall 91.12/brand_fit 95.0, state `NEEDS_REVISION` → `READY_FOR_REVIEW`.
5. **Fix leak hex-code/tiếng Anh kỹ thuật vào content** — root cause là `prompt_studio/builders/content_prompt_builder.py::render_final_prompt()` liệt kê `required_dna` (bao gồm hex + English visual descriptors) mà không cấm copy nguyên văn. Thêm dòng chỉ dẫn "never copy hex codes or raw English descriptors literally — paraphrase in the target language" (ngắn gọn để không vượt giới hạn 2000 ký tự faithfulness validation của prompt_studio). Đồng thời 3 system prompt trong `social_prompts.py` đều thêm bullet cấm hex/tiếng Anh kỹ thuật tương tự.
6. **Fix lỗi bấm Phê Duyệt (root cause)** — `shared/http.py::urllib_post()` từng `json.loads()` thẳng response webhook Make.com, nhưng Make trả plain-text "Accepted" (không phải JSON) → `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`, đúng y lỗi Harry báo. Sửa: bắt `JSONDecodeError`, trả `{"raw": raw}` thay vì crash. **Không sửa** `urllib_post_form` (chỉ dùng cho Zalo OAuth, luôn trả JSON thật — crash ở đó là đúng, không che lỗi).
7. **Fix ảnh MPO không edit được** — `agent_studio/growth/reference_asset_resolver.py` re-encode mọi ref ảnh qua PIL thành PNG single-frame (`_load_as_png()`) trước khi gửi `images.edit()` — ảnh gốc iPhone portrait-mode là MPO container, OpenAI reject `BadRequestError: Invalid image file or mode`.
8. **Lên lịch tuần** — `growth_orchestrator/application/weekly_cycle.py` mới (`run_weekly_cycle()`), CLI `venho-growth weekly-cycle`. `.github/workflows/growth-daily-cycle.yml` đổi tên "Growth Agent Weekly Cycle", cron `0 1 * * 1` (Thứ 2 duy nhất, thay vì 4 lần/tuần) — Harry duyệt cả tuần 1 lần giống content agent cũ. `--image/--no-image` flag thêm cho cả `daily-cycle`/`weekly-cycle`; CLI dùng `image_validation_provider="openai"` thật (vision QC thật), hàm-level default vẫn `"mock"` để test không tốn phí.
9. **Registry rows thêm `day`/`pillar`/`topic`** — `daily_cycle.py`'s `registry.update()` giờ ghi kèm 3 field này (trước chỉ có trong `package_snapshot`/nội bộ), để `venho-os` group được publication theo ngày/pillar/chủ đề mà không cần parse content.
10. **Batch cuối cùng của phiên** — 15 publication cũ (thiếu `day`/`pillar`/`topic`, generator Claude, chưa qua validator gate mới) bị `SUPERSEDED`; chạy `venho-growth weekly-cycle` lại → 16 publication mới (4 ngày × 4 platform) `PENDING_APPROVAL`, đã verify: đủ `day`/`pillar`/`topic`, 0 hex-code, qua Validator thật.

**Verify:** 655/655 pass sau toàn bộ thay đổi trên. Batch thật cuối cùng verify qua `venho-growth list-pending` + grep hex-code trực tiếp trên `publication_registry.json` (0 match trong các entry `PENDING_APPROVAL`, chỉ còn trong entry `SUPERSEDED`/`DISABLED` cũ).

**Việc liên quan ở `venho-os` (repo khác, xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04):** redesign `GrowthApprovalQueue` trong `PublishingSection.tsx` — bảng gộp Ngày/Pillar/Chủ đề thay flat card list, expand xem chi tiết per-platform, nút Duyệt tất cả + Duyệt riêng.

## 14e. Growth Agent v3.1 — Audit đối chiếu master plan CONSOLIDATED, sửa lỗi + Từ chối (2026-08-04)

Harry: "Review và audit growth content agent đối chiếu với plan v3.1. Nếu tìm ra lỗi, sửa ngay. Bổ sung nút Từ chối/Sửa. Xoá file lỗi/temp/nháp." Đọc toàn bộ `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` (1823 dòng) + dùng 1 agent con audit code thật (`growth_orchestrator/`, `agent_studio/growth/`, `publishing_gateway/`, `venho-os/src/components/os/sections/PublishingSection.tsx`).

**Kết luận scope-reality:** plan v3.1 mô tả kiến trúc mục tiêu rất lớn (SQLite state machine, Obsidian Research OS đủ 9 domain, Trend Radar chạy thật, HMAC callback tự động...). Thực tế đã build là một MVP nhỏ hơn nhiều bên trong kiến trúc Studio hiện có (M01–M10) — nhiều mảnh hạ tầng plan mô tả (SQLite job queue, PublishingSlot state machine, HMAC callback receiver) **đã có code** nhưng **chưa được `daily_cycle.py`/`weekly_cycle.py` gọi tới** — không phải thiếu code, mà là code có sẵn chưa nối dây vào pipeline thật đang chạy cron. Đây không phải việc cần sửa trong phiên này (không phải bug, là gap kiến trúc lớn ngoài scope "audit + sửa lỗi") — chỉ ghi nhận.

**5 lỗi thật đã sửa trong code đang chạy production:**

1. **Race condition double-publish** — `approve_and_dispatch()` cũ là check-then-act không atomic (`registry.find()` đọc không khoá → check status → gọi webhook → `registry.update()` khoá riêng). Hai lần bấm Duyệt gần nhau (double-click, 2 tab) có thể cả hai đều đọc thấy `PENDING_APPROVAL` trước khi bên nào ghi lại → bắn webhook Make.com 2 lần thật. Sửa: thêm `PublicationRegistry.claim(expected_status, claimed_status)` — test-and-set atomic trong cùng 1 khoá `fcntl`; `approve_and_dispatch`/`retry_dispatch`/`reject_publication` đều claim trước khi làm bất cứ điều gì khác, bên thua cuộc raise `ValueError` ngay lập tức thay vì cùng dispatch. Test: `test_approve_and_dispatch_second_concurrent_call_cannot_double_dispatch`.
2. **Dispatch fail = kẹt vĩnh viễn** — trước đây nếu Make.com webhook lỗi mạng thoáng qua, hàm `approve_and_dispatch` raise exception giữa chừng (status kẹt ở giá trị cũ hoặc lỗi không rõ), không có đường quay lại vì hàm chỉ chấp nhận `PENDING_APPROVAL`. Sửa: dispatch lỗi giờ luôn hạ cánh về `GATEWAY_ERROR` (bắt exception trong `_dispatch_claimed`), và thêm `retry_dispatch()` (CLI `venho-growth retry-dispatch --publication-id X`, tái dùng approval cũ, không hỏi lại approved_by).
3. **1 platform lỗi sập cả ngày, 1 ngày lỗi sập cả tuần** — `run_daily_cycle()`'s vòng lặp per-platform và `run_weekly_cycle()`'s vòng lặp per-day trước đây không có try/except: một lỗi OpenAI rate-limit ở Instagram xoá luôn draft Facebook/Threads/Zalo cùng ngày; một lỗi ở thứ Tư xoá luôn thứ Sáu/Bảy. Sửa: mỗi platform/day giờ cô lập bằng try/except, lỗi ghi vào `DailyCycleResult.errors`/CLI JSON output, các platform/day khác vẫn chạy tiếp.
4. **M03ValidatorBridge không fail-closed khi crash** — plan Part 2.1 quyết định #8: "Validator fail/timeout/malformed → fail-closed UNVALIDATED, không bao giờ APPROVED". Code thật: nếu `validate_content()` throw exception (network, markdown hỏng...), exception văng thẳng ra ngoài, không map về `UNVALIDATED` — vi phạm invariant (dù hậu quả thực tế là crash cả cycle chứ không phải APPROVE sai, vẫn sai theo đúng thiết kế). Sửa: bọc try/except quanh `validate_content()`, exception → `verdict="UNVALIDATED"`.
5. **Nút Từ chối (reject) hoàn toàn chưa tồn tại** — trước đây `PENDING_APPROVAL` chỉ có action Approve; không có cách nào loại một bài sai chủ đề khỏi hàng chờ mà không tự tay sửa `publication_registry.json`. Thêm full-stack: `reject_publication()` (application layer, atomic claim giống approve) → CLI `venho-growth reject --publication-id X --rejected-by Y --reason "..."` → API `POST /api/v1/studio/growth/[id]/reject` (venho-os) → nút "Từ chối"/"Từ chối tất cả" trong `GrowthApprovalQueue` (per-platform + group-level, giống layout nút Duyệt). Rejected rows tự động rớt khỏi `list-pending` (chỉ filter `PENDING_APPROVAL`), không cần logic ẩn riêng.

**"Sửa" (edit) — cố tình KHÔNG làm trong phiên này:** theo plan, sửa nội dung sau khi đã có `package_snapshot` phải tự động revoke approval cũ và chạy lại M03 validation trước khi cho vào hàng chờ lại (không được "sửa xong tự động duyệt lại"). Đây là 1 luồng lớn hơn (cần quyết định UX: sửa inline trên dashboard hay mở lại content_studio pipeline?) — để Harry quyết định approach trước khi build, tránh build sai hướng.

**Đã điều tra, không phải lỗi:** `venho-os/src/bff/growth/growth-agent.client.ts` trỏ `http://127.0.0.1:8011` từng nghi là dead/legacy code (audit ban đầu đoán vậy) — xác minh lại: đây là client thật cho `venho-quangcao-agent` (repo riêng, FB/Google/TikTok paid-ads agent, `make run` → uvicorn port 8011 thật), khác hoàn toàn với Growth Content Agent v3.1 (`venho-growth` CLI) đang audit. Không đụng vào.

**Gap đã biết, chưa làm (flag cho Harry, không tự ý xây):** ảnh generate ra (`image_run_path`, local file) không bao giờ được đính vào payload dispatch — `MakeGatewayAdapter.send()` chỉ gửi `{publication_id, idempotency_key, platform, content}`, không có URL ảnh. Toàn bộ pipeline generate + validate ảnh (gọi OpenAI thật, tốn phí) hiện sản xuất ra artifact không bao giờ lên bài thật. Cần một bước upload ảnh lên nơi có public URL (Google Drive như `venho-social-content-agent` legacy đã làm, hoặc nơi khác) để Make.com fetch được — quyết định kiến trúc cần Harry chốt trước khi build (secrets mới, chọn nhà cung cấp lưu trữ), không tự làm trong phiên audit này.

**File lỗi/temp/nháp:** kiểm tra cả 2 repo — `git status --short` sạch cả trước và sau audit, không có `.orig`/`.bak`/`_old.`/`_draft.`/`.log` tracked, không `__pycache__` tracked, không file `/tmp/` nào bị commit nhầm, `data/` toàn bộ đã gitignore đúng. Không có gì cần xoá.

**Verify:** 667/667 pytest pass (12 test mới: `test_growth_approve_and_dispatch.py` +8, `test_growth_m03_validator_bridge.py` mới +2, `test_growth_weekly_cycle.py` mới +1, `test_growth_daily_cycle.py` +1).

**Việc liên quan ở `venho-os`:** xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04 (audit) — API route `reject`/`retry-dispatch` mới, nút Từ chối trong `GrowthApprovalQueue`.

## 14f. Growth Agent v3.1 — Nút Sửa đúng theo plan + upload ảnh lên Google Drive (2026-08-04)

Harry, sau khi xem báo cáo audit mục 14e, chốt luôn 2 gap còn treo: "Nút Sửa: Làm đúng theo Plan." và "Ảnh generate ra không lên bài: Lưu vào Google drive."

**1. `edit_publication()` — full-stack, đúng theo invariant Part 2.1/4.3 của plan:**
- Editable từ `PENDING_APPROVAL` hoặc `GATEWAY_ERROR` (claim atomic qua `registry.claim()` mở rộng nhận `set[str]` thay vì chỉ 1 status). `DISPATCHING`/`GATEWAY_ACCEPTED`/`PUBLISHED` không sửa được (bài đã/đang đăng thật, phải Từ chối + để cycle mới sinh lại).
- Text sửa được chấm lại bằng đúng rubric `validator_studio.content_validator.validate_content()` thật (brand_fit/tone/clarity/cta/language_fit) mà `M03ValidatorBridge` dùng để gate draft gốc — ghi tạm ra file `.md` (`tempfile.NamedTemporaryFile`) vì `validate_content()` đọc file, không nhận raw string. Chỉ `Recommendation.APPROVE` mới quay lại `PENDING_APPROVAL`; không đạt → `NEEDS_REVISION`, tự rớt khỏi hàng chờ giống draft gốc fail.
- **Bất kỳ approval cũ nào cũng bị xoá vô điều kiện** khi sửa (`approval_snapshot`/`approved_by`/`gateway_status` = None) — kể cả khi bản sửa lại pass — đúng theo "sửa sau approval → tự revoke" của plan; lần Duyệt tiếp theo luôn build snapshot mới từ nội dung đã sửa.
- Cần thêm `dna_subject` vào registry row (`daily_cycle.py`'s `registry.update()`, cạnh `day`/`pillar`/`topic`) — trước đây không có field này nên không biết chấm ảnh/text theo DNA nào khi sửa mà không giữ lại `CreativeBrief` gốc.
- **Giới hạn đã ghi rõ trong docstring, không giấu:** chỉ chấm lại content rubric (chất lượng bài viết), KHÔNG chấm lại claim/alignment validator (2 validator đó cần `CreativeBrief` gốc với `proof_points`/`scene_summary` — registry không lưu lại brief đầy đủ; lưu cả brief là thay đổi lớn hơn phạm vi tính năng Sửa, để dành nếu Harry cần sau).
- CLI: `venho-growth edit --publication-id X --edited-by Y --text-file path.md`. API: `POST /api/v1/studio/growth/[id]/edit` (venho-os) — ghi text vào file tạm rồi shell-out CLI, không truyền raw text qua argv (tránh escaping/giới hạn độ dài shell).
- UI: nút "Sửa" mở textarea inline ngay trong hàng chi tiết per-platform (không phải modal riêng) — "Lưu và chấm lại" gọi API, "Huỷ" đóng không lưu. Có ghi chú cảnh báo Harry: lưu sẽ chấm lại qua Validator thật, không đạt sẽ rớt khỏi hàng chờ chứ không tự động giữ nguyên.

**2. Upload ảnh lên Google Drive — gap "ảnh generate ra không lên bài" đã đóng:**
- `shared/storage/google_drive.py` mới — `MockDriveUploader` (mặc định test/dev, 0 network call) + `GoogleDriveUploader` thật (import `googleapiclient`/`google.oauth2` trễ trong `__init__`, không bắt buộc cài cho test suite) + `google_drive_uploader_from_env()` (thật nếu có `GOOGLE_DRIVE_TOKEN_JSON`, không thì Mock). **Tái dùng đúng contract OAuth của `venho-social-content-agent/google_drive.py`** — `GOOGLE_DRIVE_TOKEN_JSON` là token JSON đầy đủ (`authorized_user` format, KHÔNG phải client secret), refresh qua `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` — Harry dùng lại đúng Google Cloud OAuth app cũ, không cần tạo app mới, chỉ cần chạy lại flow `python3 google_drive.py` (repo cũ) một lần để lấy token dán vào secret mới.
- `daily_cycle.py`: sau khi ảnh qua validator thật (kill-switch=false, verdict=APPROVE), upload luôn file artifact (`generated.png`) lên Drive (`_upload_image_to_drive()`, best-effort — lỗi mạng/token hết hạn/quota không chặn queue text, giống triết lý generate ảnh). URL public lưu vào `content.image_public_url` (field mới cạnh `image_run_path` cũ — `image_run_path` là path local, không dùng được cho Make.com).
- `MakeGatewayAdapter.send()` giờ copy `content.image_public_url` ra field top-level `image_url` trong payload gửi Make.com — dễ map field trong Make scenario hơn path lồng nhau. Payload cũ (chỉ có `content` object) vẫn giữ nguyên, chỉ thêm field mới.
- `run_weekly_cycle()` share 1 `drive_uploader` cho cả 4 ngày (giống `content_bridge`/`registry`) — auth Google 1 lần/tuần, không phải 1 lần/ngày.
- Deps: `pyproject.toml` optional group `drive` (`google-api-python-client`, `google-auth-oauthlib`, `google-auth`) — không phải core dependency vì `MockDriveUploader` không cần chúng. `.github/workflows/growth-daily-cycle.yml` đổi `pip install -e .` → `pip install -e ".[drive]"` + 3 env mới (`GOOGLE_DRIVE_TOKEN_JSON`/`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`) từ GitHub Secrets — **Harry cần tự thêm 3 secret này vào repo `venho-ai-studio` trên GitHub** (chưa set = uploader tự fallback Mock, không lỗi, chỉ không có ảnh thật).
- **Phát hiện phụ, chưa sửa vì ngoài yêu cầu:** `.env.local` cục bộ có `GOOGLE_DRIVE_TOKEN_JSON=GOCSPX-...` — giá trị này giống client secret (không phải JSON token object), sẽ không hoạt động với uploader thật nếu Harry chạy local. Không tự sửa file (gitignored, chứa secret thật, không chắc Harry có đang dùng giá trị này cho việc khác) — Harry cần tự dán đúng token JSON vào đó nếu muốn chạy Drive upload thật ở local.
- **Phát hiện phụ khác, chưa sửa:** `.github/workflows/growth-daily-cycle.yml` có bước `git add -f data/projects/*/publishing/publication_registry.json ... && git push` — nghĩa là `publication_registry.json` (chứa toàn bộ hàng chờ duyệt) commit thẳng vào git sau mỗi lần weekly-cycle chạy trên GitHub Actions runner. `venho-os`'s approve/reject/edit routes chạy `venho-growth` cục bộ (shell-out, xem `STUDIO_DIR`) — nếu chạy trên máy khác/checkout khác chưa `git pull` sau lần chạy Actions gần nhất, sẽ thao tác trên bản registry cũ. Không phải bug mới phát sinh từ session này, không thuộc phạm vi "Sửa"/"Google Drive" Harry vừa yêu cầu — chỉ ghi nhận để theo dõi nếu sau này registry "không khớp" giữa dashboard và Actions.

**Verify:** 677/677 pytest pass (10 test mới: `test_growth_approve_and_dispatch.py` +6 cho edit, `test_growth_google_drive_uploader.py` mới +3, `test_growth_daily_cycle.py` +1, `test_growth_v3_1_real_providers.py` +1 mới/1 sửa). `tsc --noEmit`/`eslint` sạch, 127/127 vitest pass (venho-os).

**Việc liên quan `venho-os`:** route mới `POST /api/v1/studio/growth/[id]/edit`, UI textarea inline "Sửa" trong `GrowthApprovalQueue` — xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04.

## 14g. Growth Agent v3.1 — 6 hạng mục còn lại từ audit 14e (2026-08-05)

Harry: "Làm tất cả" 6 gap còn treo sau câu hỏi "growth plan v3.1 đã hoàn thành 100% chưa?". Mỗi mục lớn đều dừng lại hỏi Harry trước khi code khi phát hiện xung đột kiến trúc thật (không đoán mò).

**1. Retry UI cho GATEWAY_ERROR** — `list_pending()` giờ trả cả `PENDING_APPROVAL` lẫn `GATEWAY_ERROR` (trước chỉ pending, nên bài kẹt dispatch lỗi vô hình trên dashboard). `venho-os`: badge đỏ "Lỗi gửi" + nút "Thử lại gửi" (per-item + gộp nhóm) trong `GrowthApprovalQueue`, gọi route `/retry-dispatch` đã có sẵn từ 14f nhưng chưa có UI.

**2. SQLite JobStore + PublishingSlot — nối vào `weekly_cycle` thật (không phải plan gốc):**
- Phát hiện xung đột: plan v3.1 Phần 10 thiết kế cho **Mac Mini M4 24/7 + launchd worker daemon + deadman switch** — hạ tầng hoàn toàn khác GitHub Actions ephemeral cron đang chạy thật (Harry chọn GitHub Actions có chủ ý, "không cần Mac bật"). Hỏi Harry → **giữ GitHub Actions, thiết kế lại cho ephemeral** (không xây `worker.py`/`scheduler.py`/`launchd` — sẽ là code chết).
- `shared/jobs/slot_store.py` mới — SQLite persist `PublishingSlot`, `ensure_slots()` idempotent, `transition()` optimistic.
- `weekly_cycle.py`: ensure 4 slot/tuần trước khi chạy; **JobStore idempotency guard theo ISO week** (`job_id=f"{project}-weekly-{year}-W{week}"`) — chạy lại workflow thủ công trong cùng tuần sẽ SKIP (không sinh trùng batch, không tốn budget lần 2) thay vì âm thầm generate lại.
- `daily_cycle.py`: slot OPEN→DRAFT_ASSIGNED→PENDING_APPROVAL/MISSED theo kết quả platform loop; publications giờ có `slot_id`.
- `approve_and_dispatch.py`: dispatch thành công → slot PENDING_APPROVAL→FILLED→DISPATCHED (best-effort, không bao giờ chặn dispatch thật).
- `publishing_slot.py`: thêm transition `DRAFT_ASSIGNED→MISSED` (đường thật khi mọi platform fail, evergreen_pool.py chưa nối nên chưa có fallback evergreen).
- CLI `venho-growth slots`. `venho-os`: panel "Slot tuần này" read-only trong Publishing section (`/api/v1/studio/growth/slots`).

**3. HMAC callback receiver — quyết định KHÔNG xây (giữ reconcile thủ công):**
- Phát hiện: `venho-os` chưa deploy công khai (`localhost:3000` cục bộ) — Make.com (cloud) không gọi được vào endpoint local. Xây callback receiver trong `venho-os` sẽ là code chết y hệt lỗi Research Vault panel trước đó.
- Hỏi Harry → giữ nguyên `venho-growth reconcile` thủ công. Không code gì thêm, chỉ ghi nhận quyết định để không bị hiểu nhầm là "chưa làm".

**4. Sửa chấm lại claim/alignment (không chỉ content quality):**
- `daily_cycle.py` giờ lưu thêm `creative_brief`/`claims`/`scene_summary` vào registry row lúc tạo (trước chỉ có `dna_subject`).
- `edit_publication()`: re-run `ClaimValidator`/`validate_alignment` thật với `claims`/`scene_summary`/`creative_brief` đã lưu (không phải regenerate CreativeBrief) — kill-switch (claim không có fact_key hợp lệ, scene thiếu/có entity cấm) vẫn chặn quay lại `PENDING_APPROVAL` dù content-quality rubric pass. Field `edit_validation.claim_alignment_skipped=true` cho row cũ (trước 2026-08-05) không có brief lưu lại.
- **Giới hạn còn ghi rõ:** `claims`/`scene_summary` là metadata GỐC từ lúc generate, không re-derive từ bản text Harry sửa tay — không bắt được claim bịa MỚI Harry tự gõ thêm, chỉ bắt được claim gốc mất fact support.

**5. Trend Radar thật (Tavily + AI classifier) nối vào chọn Thứ 7:**
- Phát hiện gap thật: `scan_trends.py` cần input đã phân loại sẵn (`geographic`/`thematic`/`actionability`/`brand_safety_category`/`intersections`) nhưng comment "downstream, not here" — downstream cũng chưa ai viết. `collect_tavily_search()` chỉ trả raw title/snippet.
- Hỏi Harry → xây bộ phân loại thật bằng AI. `fetch_saturday_candidates.py` — Tavily collect (dedupe theo id) → AI classify → `scan_trends` score/gate, tất cả injectable cho test.
- `trend_candidate_store.py` — JSON store, enforce `brand_safety.yaml`'s `human_approval: mandatory` bằng CODE (không chỉ docs): `merge_new()` không bao giờ ghi đè `verified_by_human` đã approve; chỉ candidate đã `approve()` + chưa `mark_used()` mới vào pool Saturday.
- `daily_cycle._pick_topic`: candidate Trend Radar đã duyệt tham gia cùng rotation pool với `content_pillars.yaml`'s special_topics hand-curated; pick xong tự `mark_used()` để không lặp lại mãi.
- CLI: `venho-growth trend-scan` / `trend-list` / `trend-approve`.
- **2026-08-05 — classifier đổi từ Claude sang Gemini Flash** (Harry: "Dùng Anthropic chi phí cao, không phù hợp cho startup"). Xoá `classifiers/claude_classifier.py`, thêm `classifiers/gemini_classifier.py` — cùng interface (`classify_candidates(candidates, *, api_key, model, client_fn)` / `classify_candidates_from_env`), cùng taxonomy/system prompt, chỉ đổi client: `google-genai` SDK (`from google import genai`), `client.models.generate_content(model=..., contents=..., config=types.GenerateContentConfig(system_instruction=..., temperature=0, response_mime_type="application/json"))`. Model mặc định `gemini-flash-latest`, override qua env `GEMINI_TREND_MODEL` (đặt tên model chính xác của Google có thể đổi theo thời gian — Harry nên xác nhận lại tên model hiện hành trước lần chạy thật đầu tiên). Env key mới: `GEMINI_API_KEY` (chưa có trong `.env.local`, Harry cần tự điền — không tự ý ghi placeholder vào file secrets thật). Optional dependency mới trong `pyproject.toml`: `pip install "venho-ai-studio[gemini]"`. Đã cài `google-genai` vào interpreter test (`/Library/Developer/CommandLineTools/usr/bin/python3`). Content generation ở các module khác (content_studio, prompt_studio optimizer, v.v.) **không đổi** — vẫn dùng Claude, đổi này chỉ giới hạn trong Trend Radar classification (workload phân loại text ngắn, không cần model mạnh/đắt).
- **2026-08-05 — nối cron GitHub Actions + UI duyệt (Harry yêu cầu trực tiếp, đã làm):**
  - `.github/workflows/growth-trend-scan.yml` — `cron: "0 1 * * 5"` (Thứ 6 08:00 Asia/Ho_Chi_Minh) + `workflow_dispatch`, chạy sớm hơn `growth-daily-cycle.yml`'s Monday 08:00 (`0 1 * * 1`) để Harry có cả cuối tuần duyệt trước khi `weekly-cycle` chọn chủ đề Thứ 7. `pip install -e ".[gemini]"`, secrets `TAVILY_API_KEY`/`GEMINI_API_KEY`, commit `trend_candidates.json` với cùng pattern `git add -f` (data/ gitignored) như `growth-daily-cycle.yml`.
  - Set secret thật qua `gh secret set GEMINI_API_KEY`/`TAVILY_API_KEY` (đọc trực tiếp từ `.env.local` bằng `grep | sed`, không bao giờ in giá trị ra terminal).
  - `venho-os`: panel "Trend Radar — Chờ duyệt xu hướng" mới trong `PublishingSection.tsx`, mount giữa `SlotWeekPanel` và `ResearchVaultPanel`. Routes mới: `GET /api/v1/studio/growth/trend-candidates` (shells `venho-growth trend-list`), `POST /api/v1/studio/growth/trend-candidates/approve` (shells `venho-growth trend-approve`, `approved_by` lấy từ session email thật qua `getCurrentSession()` — cùng pattern route `growth/[id]/approve` có sẵn).
  - **Quyết định thiết kế:** `candidate_id` truyền qua JSON body (không phải route param `[id]`) vì Tavily-derived id là 1 URL đầy đủ (`/`, `:`, `%XX`) — không nhét vừa route segment và không khớp regex `^[a-zA-Z0-9_-]+$` route approve publication đang dùng. `execFile` không qua shell nên không có injection risk, chỉ cap độ dài làm sanity check.
  - **Test thật end-to-end qua HTTP** (không chỉ CLI): login bằng `VENHO_OS_BOOTSTRAP_EMAIL`/`PASSWORD` lấy cookie session thật, `curl` GET trend-candidates thấy đúng 26 candidate thật đã scan trước đó, POST approve 1 candidate → `approved_by` ghi đúng `hpham1504@gmail.com` (không phải "unknown"). tsc/eslint/vitest (127/127) sạch.
  - **Known gap kế thừa, không mới:** `venho-os` chạy CLI cục bộ trên checkout local (`STUDIO_DIR`), còn Actions runner checkout/commit/push riêng trên GitHub — cùng vấn đề `git pull`/`git push` thủ công đã ghi nhận cho `publication_registry.json` (dòng ~856 file này), giờ áp dụng thêm cho `trend_candidates.json`: sau lần scan Thứ 6 tự động, Harry cần `git pull` trước khi mở panel; sau khi duyệt trên dashboard, cần `git push` để `weekly-cycle` (chạy trên Actions runner khác, không thấy local) nhận được approval trước Thứ 2. Không tự động hoá 2 chiều — nằm ngoài phạm vi yêu cầu lần này, chỉ ghi nhận để theo dõi.

**6. Research OS 9 domain — khung, không bịa nội dung (theo đúng quyết định của Harry):**
- Phát hiện gap thật: `domains.yaml` chỉ có 8 domain, thiếu `weather_signal` (plan v3.1 gọi là domain mới) — và `ResearchNote`'s `ResearchDomain` Literal hardcode độc lập cùng 8 domain đó, 2 nguồn sự thật đã lệch nhau. Đã sửa cả 2 + thêm test regression khoá đồng bộ.
- `collect_source_note`/`collect_structured_note` (`research_engine/application/collect_sources.py`) vốn đã domain-agnostic nhưng KHÔNG có CLI nào gọi tới — không có cách ingest note vào vault ngoài `load-seed-facts`/`notebook-inbox`. Thêm `venho-research collect-source` (R0) + `collect-note` (R1), validate `--domain` theo `domains.yaml`, từ chối domain không đăng ký.
- **Không tự bịa nội dung domain nào** — vẫn chỉ ~2/9 domain (guest_voice, competitor) có note thật trong vault, đúng quyết định Harry chọn ("Anh cung cấp dần từng domain").

**Verify tổng:** 706/706 pytest pass (33 test mới cả 6 mục), tsc/eslint sạch, 127/127 vitest (venho-os). Commit riêng từng mục, đã push cả 2 repo.

## 14h. Post-audit follow-up: Phần 10/18 rewrite, dọn code chết, phát hiện audit trước sai về Image runtime (2026-08-05)

Sau khi công bố audit hoàn thành v3.1 (artifact `growth-v31-audit.html`), Harry giao 3 việc trong 1 tin nhắn: (1) viết lại DoD Phần 10/18 khớp kiến trúc thật; (2) dọn code chết; (3) "Làm Image runtime + Multimodal QC".

**1. Phần 10 + DoD 21–24 viết lại** trong `VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`. Xoá mô tả Mac Mini 24/7/launchd/pmset/deadman switch/HMAC cloud fallback/Tailscale — chưa từng có máy nào chạy nó. Thay bằng kiến trúc thật đang chạy: bảng phân chia trách nhiệm GitHub Actions cron / local `venho-os`, cơ chế git-sync 2 chiều (đã build ở phiên trước — merge rule "local luôn thắng"), bảng rủi ro thật (khác hẳn rủi ro Mac Mini: risk giờ là "Harry không mở dashboard", không phải "máy ngủ"), backup thật (chỉ git, chưa có backup artifacts ảnh — ghi rõ là gap chưa làm, không tự nhận đã xong), và trung thực ghi §10.5 "truy cập mobile: CHƯA GIẢI QUYẾT". DoD #21–24 viết lại tương ứng — #24 (backup + verify-restore) explicit đánh dấu **chưa đạt**.

**2. Dọn code chết — quyết định xoá vs đánh dấu dựa trên grep thật, không đoán:**
- Trước khi động tay, `grep -rln` từng module ứng viên để xác nhận có/không caller thật ngoài chính nó và test của nó.
- `infra/` (Mac Mini): **0 caller** ngoài `tests/test_growth_v3_1_cadence_infra.py` → xoá hẳn (`git rm -r infra/`), gỡ `"infra*"` khỏi `pyproject.toml`. Test file đó có 28/32 test không liên quan gì Mac Mini (cadence/slot/special-lane/preflight/weather/zalo — test code thật) nên **không xoá cả file**, chỉ cắt 4 test cuối (heartbeat + cloud_fallback export) và 2 dòng import `infra.*`.
- `evergreen_pool.py`: **0 import** thật, chỉ 1 dòng comment nhắc tới trong `publishing_slot.py`. Giữ lại + thêm header comment giải thích rõ trạng thái "implemented, chưa wired" — đây là code thật cho Phase 4.5, khác hẳn tính chất `infra/` (thiết kế đã bị bỏ hoàn toàn).
- `analytics_feedback/meta_insights.py` + `attribution.py`: **0 caller** từ `m08_analytics_bridge.py` hay `cli.py` (chỉ dùng `MockMetricsAdapter` trực tiếp) — giữ + header comment. Đây là Phase 6 chưa tới lượt, không phải lỗi.
- `strategy_memory/*`: chỉ được import bởi test file riêng (`test_growth_phase7_strategy_memory.py`), 0 caller thật — giữ + header comment, Phase 7 chưa tới lượt.
- **Không đụng** `image_studio_runtime/` — grep xác nhận `gpt_image_provider.py` (real GPT-image-2) ĐANG được `daily_cycle.py` import và gọi thật, không phải dead code như audit trước ghi.
- `python3 -m pytest -q` sau khi xoá `infra/`: 702 passed (giảm đúng 4 so với 706 trước, không có test nào fail bất ngờ).

**3. "Image runtime + Multimodal QC" — quyết định KHÔNG làm gì mới, sau khi tự phát hiện lỗi trong chính audit trước đó:**
- Trước khi build bất cứ gì, dùng `AskUserQuestion` hỏi Harry scope cụ thể — vì audit trước (mục "Đã viết code, nhưng chưa nối") ghi "Image runtime thật (Phase 3) — vẫn chỉ có Mock provider". Câu hỏi lần 1 dựa trên phát hiện `alignment_validator.py` (dùng trong `M03ValidatorBridge`) chỉ so sánh entity list (copy vs brief), không có ảnh thật, không phải AI vision — Harry chọn "làm vision QC thật".
- Trước khi code, đi tìm chỗ nối image validation vào `daily_cycle.py` thật (`_generate_image_for_topic`) để biết chèn code mới ở đâu — và phát hiện **đã có sẵn một pipeline vision QC khác, thật**, không liên quan `alignment_validator`: `validate_image()` (`validator_studio/image_validator.py`) → `observe_image_against_dna()` (`validator_studio/observe_adapter.py`) → khi `provider != "mock"`, gọi `VisionClient(image_provider=provider)` (`shared/vision/client.py`) → `OpenAIVisionProvider` model `gpt-4o` — **API call GPT-4o vision thật**, so ảnh sinh ra với DNA subject (dna_matches/forbidden/allowed_imperfections), không phải mock, không phải chỉ metadata.
- Đi tiếp một bước: `growth_orchestrator/cli.py` — lệnh `daily-cycle` và `weekly-cycle` (chính là lệnh mà `.github/workflows/growth-daily-cycle.yml` chạy thật mỗi Thứ 2) **hardcode `image_validation_provider="openai"`** ở cả 2 command. Nghĩa là: real gpt-image-2 generation + real GPT-4o vision QC đã chạy production từ commit `ab2b1de` (2026-08-03/04), tốn phí thật mỗi tuần — không phải "chưa làm" như câu hỏi lần 1 tôi đặt cho Harry ngụ ý.
- Quay lại hỏi Harry lần 2, trình bày rõ sai lầm trong câu hỏi lần 1 (đã lẫn 2 validator khác nhau: `alignment_validator` thật là entity-based, nhưng `image_validator`/`VisionClient` mới là cái quyết định câu hỏi và nó ĐÃ real). Harry chọn "Dừng — không xây gì thêm".
- **Sửa artifact audit đã publish** (`growth-v31-audit.html`, URL giữ nguyên `.../22e15a4a-...`): xoá mục sai trong "Đã viết code, nhưng chưa nối", thêm mục correction trong "Đang chạy thật, đã verify", đổi phase-status-table Phase 3 từ "Chưa đạt" → "Đạt", đổi DoD #5 (cross-modal validation) từ "Chưa rõ" → "Đạt", cập nhật stat tile 6–7/27 → 7–8/27, thêm correction log rõ ràng ở footer thay vì âm thầm sửa. **Bài học tự áp dụng cho chính mình:** cùng nguyên tắc grep-trước-khi-kết-luận mà audit gốc tự đặt ra ("không dựa vào task_memory.md của phiên trước mà không đối chiếu code thật") lại chính là thứ audit gốc đã vi phạm ở mục Image runtime — vì đã dừng lại ở `generate_image.py`/`repair_image.py` import `MockImageProvider` mà không grep tiếp xem `daily_cycle.py` có dùng provider khác hay không.

**Verify:** `python3 -m pytest -q` → 702 passed, 0 fail. Không chạm `venho-os` lần này.

## 14i. Rà soát Phase 1–3 v3.1 + hoàn thiện Phase 4/4.5 (2026-08-06)

Harry: "Rà soát lại phase 1,2,3. Nếu đã xong hết thì chuyển sang hoàn thiện Phase 4 và 4.5" (đối chiếu `VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`, không phải roadmap OTA).

**Rà soát Phase 1–3: xác nhận XONG bằng code + test thật (702/702 pass trước khi sửa gì).** Không dựa lại note cũ — check trực tiếp: 16 contract schema, 9 YAML `growth/` + 7 YAML `research/`, `shared/{budget,jobs,notify}/`, `knowledge_studio/facts/`, `validator_studio/claim_validator.py`, `content_studio/generators/gpt_social_generator.py` (real), `image_studio_runtime/` + `alignment_validator.py`/`derivative_validator.py` — tất cả tồn tại và wired vào `daily_cycle.py`.

**Rà soát Phase 4/4.5: Phase 4 (approval/publishing) về cơ bản xong. Phase 4.5 phát hiện 3 module có code + unit test riêng nhưng KHÔNG có caller thật (orphaned) -- claim "unit-tested" trong status comment cũ của `evergreen_pool.py` sai, grep xác nhận 0 test import nó.** PB-006/PB-007 trong bảng roadmap Phần 12 vẫn ghi "launchd 09:00"/"deadman switch cloud" dù Phần 10 đã đổi kiến trúc sang GitHub Actions từ 2026-08-05 -- tài liệu chưa đồng bộ.

Hỏi Harry 1 quyết định trước khi code (AskUserQuestion): khi evergreen fallback lấp 1 slot mất trắng nội dung, có tự DISPATCHED luôn hay vẫn cần 1 click Duyệt? **Harry chọn: vẫn cần 1 click** (giữ đúng bất biến DoD #23 "publish chỉ khi Harry chủ động duyệt" đã chốt 2026-08-05) -- khác nguyên văn plan gốc §9.3 (evergreen coi như đã duyệt sẵn, auto-dispatch).

**Việc đã làm (tất cả có test mới, 709/709 pass tổng, +7 test):**

1. **Doc:** Phần 12 Phase 4.5 viết lại — PB-006/PB-007 đổi thành "superseded", giải thích tại sao (không có tiến trình 24/7 để launchd/deadman canh, idempotency đạt qua `registry.claim()` atomic). Thêm dòng CHANGELOG "v3.1 (2026-08-06 revision)".

2. **PB-005 pre-flight = claim/alignment revalidation thật ngay trước dispatch** (`approve_and_dispatch.py::_preflight_claim_alignment`, gọi từ `_dispatch_claimed` trước khi `bridge.dispatch()`). Trước đây chỉ `edit_publication()` mới re-run `ClaimValidator`/`validate_alignment` -- một publication CHƯA edit, đã approve nhưng dispatch trễ (batch duyệt cả tuần) có thể publish 1 claim dựa trên fact đã hết hạn giữa lúc sinh nội dung và lúc Harry bấm Duyệt. Giờ kill-switch → `NEEDS_REVISION`, không gọi webhook thật, không dispatch. Rows không có `creative_brief` (trước 2026-08-05 hoặc evergreen) skip gracefully (`claim_alignment_skipped`), không coi là pass ngầm.

3. **`PublishingSlot` state machine sửa 2 lỗi thật:**
   - `assert_missed_only_after_evergreen_exhausted` chỉ guard `status=="OPEN"` — nhưng path MISSED thật trong `daily_cycle.py` luôn đi từ `DRAFT_ASSIGNED`, nên guard này **chưa bao giờ fire trong production** dù unit test của nó pass. Sửa để guard cả `DRAFT_ASSIGNED`.
   - `EVERGREEN_FALLBACK -> DISPATCHED` (transition trực tiếp, đúng plan gốc) đổi thành `EVERGREEN_FALLBACK -> PENDING_APPROVAL` theo quyết định Harry ở trên; test cũ `test_publishing_slot_evergreen_fallback_path` cập nhật theo full funnel (`DRAFT_ASSIGNED → EVERGREEN_FALLBACK → PENDING_APPROVAL → FILLED → DISPATCHED`).

4. **PB-004 Evergreen Pool nối thật:**
   - `shared/storage/evergreen_pool_store.py` mới (JSON, cùng convention với `TrendCandidateStore`) — chỉ nạp item qua `add_from_publication()`, không tự bịa nội dung.
   - `daily_cycle.py::_fill_slot_from_evergreen` — gọi khi mọi platform sinh nội dung thất bại hoàn toàn cho 1 slot, trước khi cho phép MISSED. Đọc `evergreen_reuse_cooldown_days` từ `queue_policy.yaml` (mặc định 90). Item chọn ra chưa có `creative_brief`/`claims` → preflight/edit đều skip gracefully, không coi là đã verify.
   - CLI `venho-growth evergreen-add --publication-id X --added-by harry` / `evergreen-list`.
   - Pool trống mặc định (Harry chưa curate gì) — cơ chế chạy thật nhưng không kích hoạt cho tới khi có item.

5. **PB-003 Runway + Telegram alert nối thật (trước đây `runway_status()`/`send_alert()` có code, 0 caller thật ngoài test):**
   - `manage_queue.py::check_runway` — đếm slot còn `OPEN` trong horizon 14 ngày (không phải "generated nhưng chưa duyệt") — chủ đích: `run_weekly_cycle` luôn ensure lại horizon 14 ngày mỗi lần chạy thật, nên số OPEN chỉ tụt về 0 nếu chính job đó NGỪNG chạy (cron chết, token hết hạn) → đây là canary hạ tầng thật, không chỉ đếm backlog nội dung.
   - Gọi best-effort ở cuối `run_weekly_cycle` (đã ensure_slots xong). CLI `check-runway` để check tay.
   - `shared/notify/telegram.py::telegram_notifier_or_mock_from_env` mới (cùng convention `google_drive_uploader_from_env`) — trả Mock nếu thiếu `TELEGRAM_BOT_TOKEN`, không raise.
   - Bắn thêm `evergreen_used`/`slot_missed` alert trong `daily_cycle.py` (2 event đã định nghĩa sẵn trong `shared/notify/alert_policy.yaml` từ trước nhưng chưa ai gọi) — best-effort, no-op nếu thiếu `TELEGRAM_CHAT_ID`.
   - **Chưa có ai set `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` thật** — cơ chế live nhưng hiện tại luôn no-op (Mock). Cần Harry set 2 secret này (local `.env.local` + GitHub Actions secret) để alert thật chạy.

**Chủ động không làm (ngoài phạm vi câu hỏi, cần quyết định riêng của Harry hoặc cần thời gian thật):**
- DoD #24 (backup ảnh + verify-restore) — vẫn ghi nhận chưa làm, không đụng.
- DoD #26 (golden-set scorecard ≥9.3/10) — cần dataset thật, không tự chấm giả.
- "4 tuần liên tục đủ 16 slot 0 duplicate" (Exit Phase 4.5) — cần thời gian vận hành thật, không code được.
- `preflight.py` (asset/event/weather check tổng quát) — vẫn KHÔNG wire thêm ngoài phần claim/alignment: registry hiện chưa track `event_claims`/`weather_context` per publication, wire nó vào giờ sẽ luôn trả "pass" giả (không có dữ liệu thật để check) — để dành khi Trend Radar/weather content thật bắt đầu publish (Phase 6/7 territory).

**Verify:** `/usr/bin/python3 -m pytest -q` → 709/709 pass (702 + 7 test mới: evergreen fallback wiring, DRAFT_ASSIGNED guard, check_runway ×2, preflight blocks dispatch ×2). 0 API call. Chưa chạm `venho-os` (không cần đổi UI cho lượt này). Commit local, **chưa push** (Harry tự quyết định khi nào đẩy lên, vì thay đổi chạm publish path thật).

## 14j. Phase 5 Durable Ops — audit + nối thật (2026-08-06)

Harry: "Tiếp tục làm Phase 5. Sẽ commit và push khi nào hoàn thành tất cả." (tiếp nối 14i, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i (grep caller thật ngoài test, không tin note cũ):** Phase 5 được Codex build 2026-08-03, `task_status.md` ghi "DONE" với 498/498 test pass. Grep thật phát hiện `BudgetLedger`/`BudgetPolicy` (`shared/budget/ledger.py`) và `JobStore.recover_expired_leases()`/`heartbeat()` **0 caller thật** ngoài chính chúng và test riêng — cùng loại lỗ hổng đã tìm thấy ở Phase 4.5 (evergreen_pool/preflight/runway) lần trước. Hệ quả thật: mọi real OpenAI call (gpt-5.5/gpt-image-2/GPT-4o vision) trong `daily_cycle.py` chạy hoàn toàn không đo/không chặn budget — `budget_policy.yaml` có cap 2,000,000,000 VND/tháng (không ai từng chỉnh, cao tới mức vô nghĩa). Và: `weekly_cycle`'s job claim dùng `lease_seconds` mặc định 300s (5 phút) trong khi 1 run thật (4 ngày × N platform × real LLM/image/vision call) có thể mất lâu hơn nhiều — nếu 1 run bị crash/cancel giữa chừng (GitHub Actions timeout) thì job kẹt `RUNNING` vĩnh viễn vì không có gì gọi `recover_expired_leases()`, khoá cứng idempotency guard của tuần đó mãi mãi.

Hỏi Harry 1 quyết định thật cần trước khi code (AskUserQuestion, vì đụng tiền thật): mức trần chi tiêu AI/tháng bao nhiêu? **Harry chọn 500,000 VND/tháng.**

**Việc đã làm (tất cả có test mới, 714/714 pass tổng, +4 test):**

1. **Stale-job recovery + heartbeat nối thật vào `run_weekly_cycle`:**
   - `job_store.recover_expired_leases()` gọi trước `claim()` — job kẹt RUNNING từ lần chạy crash trước được giải phóng về READY trước khi thử claim tuần này.
   - `claim(..., lease_seconds=3600)` thay mặc định 300s (run thật có thể lâu hơn nhiều).
   - `job_store.heartbeat(week_key, owner="weekly-cycle", lease_seconds=3600)` gọi sau mỗi ngày trong loop 4 ngày — gia hạn lease liên tục để 1 run đang thật sự tiến triển không bị 1 trigger đồng thời tưởng nhầm là chết.
   - Test mới: `test_run_weekly_cycle_recovers_a_week_stuck_running_from_a_crashed_prior_attempt` — giả lập job bị claim rồi bỏ dở (không complete/fail), lease đã hết hạn, xác nhận lần chạy tiếp theo tự phục hồi và chạy bình thường thay vì `skipped_already_run=True` mãi mãi.
   - Retry matrix (`requeue_retryable_failures()`) đã nối sẵn từ trước — không cần sửa.

2. **`BudgetGate` (mới, `growth_orchestrator/application/budget_gate.py`) — chặn cứng real OpenAI call khi chạm cap:**
   - Bọc reserve→commit (thành công)/release (lỗi) quanh đúng 3 điểm gọi API thật trong `daily_cycle.py`:
     - `_run_content_pipeline_budgeted()` (mới) quanh mỗi lần `run_content_pipeline()` trong retry loop text (tối đa `MAX_TEXT_ATTEMPTS`).
     - `_generate_topic_image()` — quanh mỗi `generate_image_run()` VÀ mỗi `validate_image()` (chỉ khi `image_validation_provider != "mock"`, vì mock không tốn tiền thật) trong retry loop ảnh (tối đa `MAX_IMAGE_ATTEMPTS`).
   - Reservation bị chặn → `RuntimeError` → rơi vào except handler có sẵn của từng platform/ngày (không crash cả pipeline, xử lý y hệt 1 lỗi generation thật khác).
   - `config/projects/venho_hotel/growth/budget_policy.yaml`: `monthly_cap_minor: 500000` (Harry chốt), version bump 1→2, comment giải thích tại sao đổi từ 2 tỷ.
   - `config/projects/venho_hotel/growth/paid_call_costs.yaml` (mới, file thứ 11 trong `growth/`) — ước tính thô 300/1200/400 VND cho text/ảnh/vision, ghi rõ là estimate chưa đối chiếu hoá đơn thật, không phải per-call accounting chính xác. `tests/test_growth_phase1_policy_registry.py`'s file-registry test cập nhật theo (set required files +1).
   - `_alert_on_budget_threshold()` (mới) — bắn `budget_threshold_crossed` Telegram alert (event đã định nghĩa sẵn trong `alert_policy.yaml` từ trước, chưa ai gọi) mỗi khi 1 reservation cán mốc 70/85/100%, không dedupe (chấp nhận trade-off ở tần suất hiện tại — vài chục call thật/tuần).
   - Test mới (`tests/test_growth_budget_gate.py`, 4 test): block khi chạm cap, release giải phóng cho lần thử lại, commit giữ nguyên đã tính vào spend, và 1 test end-to-end qua `run_daily_cycle` xác nhận cap=0 khiến mọi platform rơi vào `errors` với message "budget cap reached" thay vì crash.
   - **Chưa có UI/CLI riêng cho override vượt cap** — dùng thẳng `BudgetLedger.record_override(reservation_id, amount, reason=..., approved_by=...)` nếu Harry cần vượt cap có ghi nhận lý do.

3. **`Worker` class + `shared/jobs/scheduler.py` — đánh dấu superseded, không ép nối:** cả hai giả định kiến trúc worker 24/7 + cửa sổ dispatch cố định 09:00 (`next_dispatch_at`) — đúng thiết kế Mac Mini đã bị thay bởi GitHub Actions on-demand (Phần 10, 2026-08-05). `weekly_cycle`/`approve_and_dispatch` đã dùng thẳng `JobStore`/`PublicationRegistry`, không qua `Worker`, nên nối `Worker` vào giờ sẽ không khớp với cách hệ thống thật đang chạy. Giữ code (đã có test riêng từ 2026-08-03), không xoá, không ép nối — chỉ đánh dấu trong doc.

4. **Chủ động không làm (cần thời gian/hạ tầng thật, không phải quên):**
   - Lateness alert (`scheduler.lateness_alert()`) — cần 1 vòng polling "giờ này lẽ ra chạy xong chưa", kiến trúc push-based hiện tại (cron kích hoạt, không có gì đứng canh) không có chỗ tự nhiên để gắn mà không thêm hẳn 1 tiến trình giám sát riêng.
   - Backup tự động verify được — cùng gap với DoD #24 (Phần 10/18, 2026-08-05), chưa đụng.

5. **Doc:** Phần 12 Phase 5 viết lại đầy đủ (rewrite section + audit note), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 5)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 714/714 pass (710 + 4 test mới). 0 API call. Chưa push — Harry: "sẽ commit và push khi nào hoàn thành tất cả" (đang giữa Phase 5, chưa xong toàn bộ roadmap).

## 14k. Phase 6 Analytics + Attribution — audit + attribution tối thiểu qua Zalo (2026-08-06)

Harry: "ok, làm tiếp P[hase 6]" (tiếp nối 14j, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i/14j:** Phase 6 Codex build 2026-08-03, `task_status.md` ghi "DONE". Grep caller thật phát hiện `analytics_feedback/meta_insights.py` và `analytics_feedback/attribution.py` **0 caller thật** (cả hai đã có status comment tự nhận từ 1 audit trước đó ngày 2026-08-05 xác nhận đúng điều này — không phải phát hiện mới của phiên này, mà là confirm lại + hành động). Khác Phase 4.5/5 (chỉ cần nối dây), đào sâu thêm phát hiện: **grep `utm_content`/`build_utm_content` toàn repo → chỉ xuất hiện trong chính `attribution.py`, không đâu khác** — nghĩa là không có bài đăng nào từng mang link có gắn utm cả. Kiểm tra tiếp `_content_payload()` (nơi build text bài đăng): CTA chỉ là câu chữ LLM sinh ra ("soft call-to-action sentence"), không có URL nào được chèn. Kiểm tra chéo sang repo `Ven Ho Hotel` (`grep utm_source/utm_content src/`) — chỉ có utm cho link ra Agoda (`ota.ts`), không có gì bắt utm vào từ traffic bên ngoài. Kết luận: attribution DoD #25 cần xây mới thật sự (link tracking + nơi nhận sự kiện), không phải chỉ nối `attribute_conversion_event()` đã có sẵn.

Hỏi Harry phạm vi (AskUserQuestion, 3 lựa chọn: hoãn / xây tối thiểu qua Zalo / để anh quyết sau). **Harry chọn: xây tối thiểu qua Zalo.** Lý do hợp lý về mặt kỹ thuật: Zalo OA publish qua Make.com webhook (`ZaloOAAdapter`) — message thật do Make.com tự soạn dựa trên `content` payload gửi từ đây, nên đây là kênh duy nhất có thể mang 1 URL click được thật (Facebook/Instagram feed post trong pipeline này không hề có link, chỉ text).

**Việc đã làm (717/717 pass, +3 test mới):**

1. **`meta_insights.build_metrics_adapter` nối thật vào `M08AnalyticsBridge`:**
   - Trước đây bridge hardcode `metrics_adapter_factory = MockMetricsAdapter` trực tiếp trong `__init__`, bỏ qua hoàn toàn `meta_insights.py::build_metrics_adapter()` (hàm factory tôn trọng flag `meta_insights_enabled`/`real_meta_insights_enabled`). Đổi default thành `build_metrics_adapter` — flag giờ thật sự có tác dụng: tắt (mặc định) → vẫn Mock (đúng trạng thái thật, chưa có real Graph API client); bật mà chưa implement real adapter → raise `RuntimeError` rõ ràng thay vì âm thầm return Mock (đúng fail-mode mong muốn, tránh Harry tưởng nhầm real data đang chạy).
   - Cập nhật status comment đầu file `meta_insights.py` phản ánh đã nối.

2. **Attribution tối thiểu qua Zalo:**
   - `attribution_policy.yaml` version 1→2, thêm `tracking_base_url: "https://venhohotel.com/lien-he"` (route `/lien-he` xác nhận có thật trong `Ven Ho Hotel/src/app/lien-he/`).
   - `attribution.py::build_tracking_url(publication_id, base_url, platform)` (mới) — tái dùng `build_utm_content()` sẵn có, sinh `{base_url}?utm_source={platform}&utm_medium=social&utm_content={publication_id}`. `AttributionPolicy` dataclass thêm field `tracking_base_url`.
   - `daily_cycle.py::_content_payload()` — thêm param `publication_id`/`platform`; khi `platform=="zalo"` và có `tracking_base_url` trong policy, nối link vào cuối `text` + lưu riêng field `content["tracking_url"]` (để Make.com/Harry lấy ra làm URL nút bấm thật trong Zalo message — bản thân code này không cấu hình message Zalo, Make.com scenario làm việc đó, xem `ZaloOAAdapter`'s docstring). Bọc try/except best-effort — thiếu/hỏng `attribution_policy.yaml` không được chặn queue bài text.
   - `growth_orchestrator/cli.py`'s call site truyền `publication_id=publication_id, platform=platform` vào `_content_payload()`.
   - CLI mới `venho-analytics attribute <events.json>` (`analytics_feedback/cli.py`) — đọc publication đã **RECONCILED thật** (`published_at` có giá trị thật, set bởi `venho-growth reconcile` sau khi Harry xác nhận bài đã lên thật) từ `PublicationRegistry`, pseudonymize contact nếu có, dedupe theo policy, chạy `attribute_conversion_event()` thật, in JSON kết quả. Đây là nửa "chạy được thật" của DoD #25.
   - **Gap còn lại, ghi rõ ràng không giả vờ đã xong:** không có nguồn sự kiện chuyển đổi tự động nào feed vào CLI `attribute` — Harry phải tự cung cấp `events.json` (export tay từ GA4/hộp thư/Zalo). Tự động hoá thật cần 1 trong 2: (a) GA4 Data API pull (cần service account credentials, quota, quyết định riêng) hoặc (b) sửa form đặt phòng trên `Ven Ho Hotel` website để bắt `utm_content` từ query string và forward vào booking API — đây là thay đổi **production website đang chạy thật** (`venhohotel.com`), thuộc phạm vi CLAUDE.md riêng của repo đó ("Hỏi trước khi làm"), không tự ý đụng vào trong phiên này.
   - `test_end_to_end_report_and_cli_stay_offline` (test cũ) phải sửa: `runner.invoke(app, [...])` không còn tự động chọn lệnh `collect` nữa vì app giờ có 2 lệnh (Typer/Click chỉ auto-invoke khi app chỉ có đúng 1 command) — thêm `"collect"` làm arg đầu.

3. **M10 performance view** (`build_content_performance_view`) — đã real từ trước (đọc M08 output, không tính lại), không cần sửa.

4. **Doc:** Phần 12 Phase 6 viết lại đầy đủ (audit note + phạm vi Harry chốt + gap còn lại), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 6)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 717/717 pass (714 + 3 test mới: `build_tracking_url` + attribution nối tiếp thật, Zalo có link/FB không có link qua `run_daily_cycle` thật, CLI `attribute` end-to-end qua `PublicationRegistry` thật). 0 API call. Chưa push (Harry: "sẽ commit và push khi nào hoàn thành tất cả").

## 14l. Phase 7 Growth Intelligence pilot — strategy_memory nối thật (2026-08-06)

Harry: "làm tiếp P7" (tiếp nối 14k, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i/14j/14k:** `strategy_memory/` (Codex build 2026-08-03) có status comment tự nhận từ 1 audit trước (2026-08-05, không phải phiên này) xác nhận `pattern_inference.py` "implemented + unit-tested but NOT called from any CLI, cron, or bridge" — confirm lại bằng grep thật: đúng, 0 caller ngoài chính module và test riêng. Khác biệt so với việc chỉ "nối dây": package `strategy_memory` **chưa từng có CLI nào cả** (không có trong `[project.scripts]`), nên phải xây cả entry point mới, không chỉ đổi 1 default factory như Phase 6.

**Thiết kế trước khi code:** `infer_strategy_pattern(snapshots, ...)` tính `min_sample_size` bằng `len(snapshots)` — nghĩa là hàm collect evidence PHẢI trả về 1 dòng/publication (sample thống kê thật), không được gộp tổng trước rồi coi là "1 sample" (lỗi thiết kế suýt mắc phải ở bản nháp đầu). Sửa `collect_pilot_snapshots()` để trả về list theo publication, filter theo (pillar, platform) ở tầng CLI trước khi truyền vào `infer_strategy_pattern`.

**Việc đã làm (724/724 pass, +7 test mới):**

1. **CLI mới `venho-strategy`** (`strategy_memory/cli.py`, thêm script entry `venho-strategy = "strategy_memory.cli:app"` vào `pyproject.toml` — package này chưa có script entry nào từ trước):
   - `weekly-brief --week-id ... [--baseline-qbsr] [--min-sample-size] [--questions-root]` — chạy `collect_pilot_snapshots()` → group theo scope → `infer_strategy_pattern()` từng scope → `qbsr_rate()` tổng → `build_weekly_strategy_brief()` → lưu `StrategyBriefStore` (mới, `strategy_memory/stores.py`, JSON dưới `data/projects/{project}/strategy/weekly_briefs/`) → in JSON.
   - `promote --week-id ... --pattern ... --approved-by ...` — chỉ promote được recommendation đã tồn tại thật trong 1 brief đã lưu (không nhận pattern tự bịa), gọi `promote_strategy_memory()` thật, lưu `PromotedStrategyStore` (mới).
   - `list-promoted` — liệt kê những gì đã thật sự được duyệt, tách biệt khỏi brief hàng tuần (brief có thể chứa recommendation chưa/không được promote).

2. **`strategy_memory/collect_pilot_evidence.py::collect_pilot_snapshots()` (mới)** — join thật `PublicationRegistry` + M08 `SnapshotStore` (đọc field `metrics.reach` thật) + `AttributionEventStore` (mới, xem mục 3) qua `content_package_id`/`publication_id`. Trả về **1 dòng/publication** (không gộp tổng), mỗi dòng có `pillar`/`platform`/`qualified_booking_signals`/`eligible_reach`. `qualified_booking_signals` chỉ đếm attribution status `direct`/`assisted` (bỏ `unattributed` — không chứng minh được gì về 1 publication cụ thể).

3. **`AttributionEventStore` (mới, `analytics_feedback/stores/attribution_event_store.py`)** — Phase 6's CLI `venho-analytics attribute` (mục 14k) trước đây chỉ in kết quả JSON ra màn hình rồi bỏ, không có nơi nào đọc lại. Giờ mỗi kết quả attribute lưu qua store này (`overwrite=True`, key = event id) để `collect_pilot_snapshots()` đọc lại được. Thêm `JsonDirectoryStore.list_all()` (generic, dùng chung cho `SnapshotStore` + `AttributionEventStore`).

4. **Vòng phản hồi `INCONCLUSIVE` → `research/questions/` cho strategy pattern:** `analytics_feedback/research_question_generator.py::generate_research_question_from_analytics()` đã có sẵn + đã có test đúng shape strategy pattern (`test_analytics_signal_generates_research_question`) từ trước — nhưng grep xác nhận **chỉ `M08AnalyticsBridge.observe()` gọi nó**, chưa ai gọi cho strategy-pattern-level "tại sao vẫn INCONCLUSIVE". `weekly-brief` giờ gọi hàm này cho mọi scope INCONCLUSIVE (best-effort, không chặn brief nếu ghi file lỗi).

5. **Gap phụ phát hiện + sửa trong lúc nối:** `M08AnalyticsBridge.observe()` build `DeliveryReceiptRef` chưa từng truyền `pillar` — `daily_cycle.py` đã ghi field `pillar` vào registry row từ 2026-08-04, nhưng `observe()` không đọc lại, nên mọi snapshot thật trước đây có `pillar="unknown"` (default của schema), khiến group theo pillar bất khả thi. Sửa 1 dòng: `pillar=publication.get("pillar") or "unknown"`. Test mới `test_observe_carries_the_publication_pillar_onto_the_saved_snapshot` xác nhận.

6. **Tự phát hiện + tự sửa 1 lỗi test của chính mình:** viết xong `test_weekly_brief_cli_produces_a_real_recommendation_once_sample_size_is_met` và chạy full suite — pass, nhưng `git status research/` cho thấy 1 file thật `research/questions/m08_strategy-lake_view_rooms-zalo.md` đã bị tạo ra trong repo thật (vì test không truyền `--questions-root`, CLI dùng default `Path("research/questions")` = thư mục thật của repo). Xoá file rác, sửa toàn bộ 4 lời gọi CLI trong test file để truyền `--questions-root` trỏ vào `tmp_path`, verify lại `git status research/` sạch trước khi tiếp tục. Bài học: mọi CLI test có ghi file với default path trỏ vào thư mục thật của repo phải luôn override path đó trong test, không giả định best-effort try/except đủ để an toàn.

7. **Doc:** Phần 12 Phase 7 viết lại đầy đủ (audit note + thiết kế + trạng thái thật), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 7)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 724/724 pass (717 + 7 test mới: `collect_pilot_snapshots` join thật ×2 (bao gồm loại bỏ unattributed + snapshot mồ côi), CLI `weekly-brief` đủ mẫu → có recommendation thật + ghi research question, CLI `weekly-brief` thiếu mẫu → INCONCLUSIVE + vẫn ghi research question, `promote`→`list-promoted` round-trip, `promote` từ chối pattern bịa, `observe()` gán pillar thật). 0 API call. `git status research/` sạch. Chưa push (Harry: "sẽ commit và push khi nào hoàn thành tất cả").

## 14m. Phase 8 Rollout + Productize — venho-rollout CLI + scorecard thật (2026-08-06)

Harry: "Tôi muốn hoàn thành tất cả để đưa vào vận hành thật" (tiếp nối 14l, cùng phiên) — đây là phase cuối cùng của roadmap 0→8.

**Audit trước khi code — cùng phương pháp 14i–14l:** `controlled_rollout/` (4 file: `metrics_window.py`, `rollout_policy.py`, `runbook_validator.py`, `scorecard.py`) + `productize/hotel_content_engine.py` (Codex build 2026-08-03) có code + unit test đầy đủ (`tests/test_growth_phase8_controlled_rollout.py`, dùng fixture `_golden_metrics()` bịa sẵn) nhưng grep xác nhận 0 caller thật ngoài test riêng, không CLI, không có trong `pyproject.toml`. Cùng loại lỗ hổng như mọi phase trước.

**Khác biệt so với Phase 4.5/5/6/7:** ở đây "nối dây thật" không chỉ là gọi hàm có sẵn — `evaluate_golden_set()` cần một golden-set dict với 9 chỉ tiêu numeric, và **không có nơi nào trong hệ thống lưu lại các con số đó theo lịch sử thật**. `package["validation"]` (kết quả M03 chấm mỗi bài) chỉ được hash hoá thành `validation_snapshot_id` rồi vứt — số điểm thật biến mất ngay sau khi dùng xong. Phải làm 2 việc, không chỉ 1: (a) bắt đầu **giữ lại** số điểm thật từ nay trở đi, (b) build bộ tổng hợp đọc lại số đã giữ.

**Việc đã làm (736/736 pass, +12 test mới):**

1. **`daily_cycle.py::_scorecard_signals()` (mới)** — trích từ `package["validation"]["reports"]` (shape `[claim_report, alignment_report, content_report?]`): `claim_kill_switch_triggered` (bool, từ claim_report — proxy thật cho "critical factual precision") + `content_brand_fit`/`content_overall_score` (từ content_report's `dna_match_score`/`overall_score` — proxy thật cho "brand adherence", không phải công cụ đo giống hệt bản gốc plan hình dung là reviewer-scored, nhưng là số thật M03 đã tính trên mọi bài thật). Gọi tại điểm `registry.update()` trong `daily_cycle.py`, field mới `scorecard_signals` trên mỗi publication row.
2. **`SlotStore.list_all(status=...)` (mới)** — trước đây chỉ có `list_for_week()`; cần đọc MISSED slot trên toàn bộ lịch sử cho `unplanned_empty_days`, không chỉ tuần hiện tại.
3. **`controlled_rollout/collect_real_scorecard_metrics.py` (mới)** — join thật `PublicationRegistry.load()` + `SlotStore.list_all()`:
   - Chấm được thật 6/9 chỉ tiêu: `critical_factual_precision` (tỉ lệ PUBLISHED không có claim kill-switch), `brand_adherence` (trung bình `content_brand_fit`), `duplicate_publication` (đếm thật cặp idempotency_key+platform trùng — về lý thuyết kiến trúc luôn 0 vì `reserve()` test-and-set trong file lock, verify chứ không giả định), `publication_post_id_rate` (PUBLISHED có `platform_post_id`/tổng PUBLISHED), `human_acceptance_no_major_edit` (PUBLISHED không có `edited_by`/tổng), `unplanned_empty_days` (đếm slot MISSED thật).
   - 3/9 chỉ tiêu ảnh (`copy_image_alignment`/`hotel_dna_pass`/`linh_an_identity_pass`) **không có nguồn thật** — cần `validator_studio.image_validator` chạy thật (Vision QC trả phí), nhưng `daily_cycle` mặc định `image_validation_provider="mock"` để giữ ngân sách 500k/tháng (14j). Trả về thiếu (không có key trong `metrics`), liệt kê lý do cụ thể trong `data_gaps` — không tự tính hay giả định số.
4. **`controlled_rollout/rollout_state_store.py` (mới)** — JSON store `data/projects/{project}/rollout/rollout_state.json`, mặc định `current_stage="shadow"` (đúng trạng thái thật — Growth Agent chưa từng tiến stage). `record_decision()` chỉ advance stage khi `decision["allowed"]=True`; decision bị chặn vẫn ghi vào `history` để có audit trail.
5. **CLI mới `venho-rollout`** (`controlled_rollout/cli.py`, script entry mới trong `pyproject.toml`): `scorecard --version` (chạy `collect_real_scorecard_metrics` + `evaluate_golden_set` thật), `rollout-status`, `rollout-advance --scorecard-version --metrics-days --lane` (luôn chấm điểm thật trước khi quyết định, exit code 1 nếu bị chặn — đúng hành vi, không phải lỗi), `rollback-plan --disable-dispatch-done`, `runbook-validate`, `productize-run --project --brief-json` (chạy `hotel_content_engine` thật cho 1 project id bất kỳ, chỉ đọc config).
6. **`.claude/skills/_productize/hotel-content-engine/SKILL.md`** — thêm CLI trigger + mục "Known limitation" ghi rõ engine hiện là bản rút gọn (đọc `tone_of_voice.yaml`+`taxonomy.yaml` build headline/body), chưa chạy qua pipeline M02 prompt/M05 copy-candidate đầy đủ như `daily_cycle.py` production.
7. **Gap phụ phát hiện + sửa — không phải việc dự kiến ban đầu:** trong lúc kiểm tra vì sao test cũ `test_productize_skill_and_runbook_docs_exist` pass nhưng `git status .claude/` không hiện gì, phát hiện `.gitignore` có dòng `.claude/` chặn **toàn bộ** thư mục `.claude/` từ trước tới giờ — nghĩa là 10 skill trong `.claude/skills/` (kể cả `hotel-content-engine`, tồn tại từ 2026-08-03, RS-F1 quyết định năm 3.1 đã ghi rõ vị trí đúng là `.claude/skills/`) **chưa từng được commit vào repo**, chỉ tồn tại trên máy local. Sửa `.gitignore`: đổi `.claude/` → `.claude/*` + `!.claude/skills` + `!.claude/CLAUDE.md.proposed` (giữ nguyên phần còn lại — ví dụ `settings.local.json` nếu có sau này — bị ignore, tránh lộ state cá nhân). Kiểm tra nội dung `.claude/CLAUDE.md.proposed` trước khi add — chỉ có "No pending changes.", không có gì nhạy cảm. `git add` 10 skill + file này.
8. **Doc:** `docs/growth/controlled_rollout_runbook.md` + `docs/growth/eval_golden_sets.md` viết lại toàn bộ — khớp kiến trúc GitHub Actions thật (không còn Mac Mini), có bảng 9 chỉ tiêu ghi rõ nguồn dữ liệu thật/thiếu cho từng chỉ tiêu, cách chạy CLI thật. Phần 12 Phase 8 trong master plan viết lại thành `[x]` (cơ chế hoàn thành, rollout stage thật vẫn `shadow` chờ dữ liệu). Thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 8 — ROADMAP HOÀN THÀNH)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 736/736 pass (724 + 12 test mới: `_scorecard_signals` extract có/không content_report, `collect_real_scorecard_metrics` trên registry rỗng (data_gaps đúng) + trên 3 publication seed thật (số trung bình đúng), CLI `scorecard` end-to-end trên dữ liệu rỗng, `RolloutStateStore` mặc định shadow + chỉ advance khi allowed, CLI `rollout-advance` bị chặn trên dữ liệu rỗng + vẫn bị chặn khi 6/9 chỉ tiêu tốt nhưng thiếu 3/9 ảnh (chứng minh gate không thể bị "chơi" bằng cách chỉ có phần dữ liệu dễ), CLI `rollback-plan` enforce thứ tự, CLI `runbook-validate` pass trên file thật, CLI `productize-run` build draft cho hotel #2 config-only, `unplanned_empty_days` đọc MISSED slot thật). 0 API call. `git status --short` sạch (chỉ các file dự kiến sửa/mới + `.claude/skills/`+`.claude/CLAUDE.md.proposed` mới add). Chưa push — chờ Harry xác nhận cuối vì đây là điểm "hoàn thành tất cả" theo lời Harry, cần Harry biết rõ những gì vẫn còn là gap vận hành thật (không phải gap code) trước khi đẩy lên remote.

**Ý nghĩa thật của "hoàn thành roadmap":** 9/9 phase (0→8) giờ có code thật + CLI thật + dữ liệu thật, không còn phase nào ở dạng "code+test cô lập, 0 caller thật". Việc còn lại — rollout stage tiến lên `pilot_25` thật, xây golden eval set >=100 case reviewer-scored theo đúng plan gốc, bật Vision QC thật thường xuyên, backup verify-restore, lateness alert, GA4/FB attribution tự động — là **việc vận hành theo thời gian thật + quyết định sản phẩm của Harry**, không phải code còn thiếu. Liệt kê đầy đủ trong `docs/growth/controlled_rollout_runbook.md`'s "Trạng thái thật hôm nay".

## 14n. Scenario Make riêng cho Growth + cổng rollout stage thật (2026-08-06, chiều)

Tiếp nối hai ghi chú "Sửa 2026-08-06" trong mục 14b (tách webhook + ảnh fallback). Ba việc, làm cùng buổi với Harry ngồi thao tác trên Make.

**1. Scenario Make riêng — ĐÃ CHẠY THẬT.** Webhook mới `https://hook.us2.make.com/jw62ijj38t2r9prls12dj9cx537fwfo2`, đã điền vào `.env.local` → `MAKE_GROWTH_WEBHOOK_URL` (secret để trống, adapter không ký HMAC). Scenario là bản clone của legacy, giữ nguyên 5 module: `Webhooks 2` → `HTTP - Download a file 4` → `Router 5` → `Facebook Pages 3` / `Instagram for Business 6`. Mapping đã đổi sang schema Growth: HTTP URL = `{{2.image_url}}`, FB "Post caption" = `{{2.content.text}}`, IG Caption = `{{2.content.text}}`, filter 2 nhánh đổi từ `publish_to_facebook`/`publish_to_instagram` (field legacy, Growth không có) sang `{{2.platform}}` Equal to `facebook`/`instagram`. Thêm điều kiện AND thứ hai trên **cả hai** nhánh: `{{2.publication_id}}` **Does not contain** `test` — chốt an toàn vĩnh viễn, mọi payload thử nghiệm bị chặn ở Router.

**Sự cố trong lúc làm (2 lần đăng nhầm lên trang thật):** payload smoke-test `platform: "threads"` được cho là an toàn vì "không nhánh nào khớp", nhưng cả FB lẫn IG đều đăng thật — filter cũ của scenario legacy cho qua (nhiều khả năng điều kiện phủ định, hoặc route đặt `fallback = Yes`). Lần thứ hai lọt tiếp vì Harry đã sửa filter nhưng **chưa bấm nút Save của scenario** (nút 💾 dưới đáy canvas — khác nút Save trong panel filter); scenario đang ON vẫn chạy bản deploy cũ. Harry đã xoá cả 4 bài test. Lần thứ ba mới đúng: `The bundle did not pass through the filter` ở cả 2 module. **Bài học ghi lại:** (a) không suy đoán logic filter của scenario có sẵn — mở ra đọc trước; (b) sửa Make xong bắt buộc Save scenario rồi hard-refresh verify; (c) phiên bản Make hiện tại **không có** mục Disable trong menu chuột phải của module, nên không thể vô hiệu hoá module đích khi test — phải dựa vào filter.

**Chưa kiểm được:** bundle `platform: "facebook"` thật có đi đúng nhánh FB không — về bản chất không thể kiểm mà không đăng thật. Lần đăng thật đầu tiên nên là một bài Growth Harry duyệt có chủ ý.

**2. Cổng rollout stage — `shadow` giờ chặn thật trong code.** Trước đây `RolloutStateStore` chỉ là governance record (docstring của nó nói rõ "does not change behaviour by itself"), nên thứ duy nhất ngăn agent stage-shadow đăng lên Facebook thật là `MAKE_GROWTH_WEBHOOK_URL` để trống — cấu hình, không phải logic. Từ lúc điền URL vào, lớp đó biến mất. Nay `approve_and_dispatch._dispatch_claimed()` đọc stage ngay trước `bridge.dispatch()`:
- stage = `shadow` → **không gọi webhook**, row đậu ở status mới `SHADOW_HELD`, kèm `rollout_stage` + `shadow_held_reason`. Approval/snapshot vẫn được ghi đầy đủ → toàn bộ pipeline (sinh bài, validate, duyệt, snapshot) vẫn chạy, chỉ giữ lại cú gọi ra ngoài. Đúng nghĩa "shadow".
- `_rollout_stage()` **fail closed**: state file hỏng/không đọc được → coi như `shadow`, giữ bài lại chứ không đăng.
- `SHADOW_HELD` nằm trong `list_pending()` (row không biến mất khỏi dashboard) và trong `EDITABLE_STATUSES`.
- Thoát cổng có 2 đường: `venho-rollout rollout-advance` (tiến stage thật, phải qua scorecard) — sau đó row đã giữ được thả bằng `retry_dispatch` (approval cũ vẫn còn hiệu lực, không duyệt lại); hoặc `venho-growth approve-and-dispatch --allow-shadow` cho một bài cụ thể, ghi `shadow_override_by` lên chính row đó để có audit trail.
- Test cũ về đường dispatch phải seed stage qua helper `_past_shadow(tmp_path)` — nếu không chúng đang assert cái cổng chứ không phải hành vi chúng đặt tên.

**Lưu ý vận hành:** stage thật hiện vẫn là `shadow` và `data/projects/venho_hotel/rollout/rollout_state.json` chưa tồn tại (mặc định). Nghĩa là **bấm Approve trên dashboard sẽ KHÔNG đăng** — muốn đăng bài đầu tiên phải dùng `--allow-shadow` từ terminal.

**3. 12 publication kẹt đã sửa trạng thái.** 12 row `GATEWAY_ACCEPTED` ngày 2026-08-04 thực chất fail phía Make (xem 14b) — đã đổi sang `GATEWAY_ERROR` + `gateway_error` ghi rõ nguyên nhân và ngày sửa, nên `list_pending()` hiện lại được và `retry_dispatch` gửi lại được. Chúng đều có `image_public_url = None`, nhưng lớp chặn cuối trong `MakeGatewayAdapter` sẽ thay bằng ảnh mặc định khi gửi lại. Backup registry trước khi sửa để ở scratchpad phiên làm việc.

**Verify:** `PYTHONPATH=. pytest -q` → **744 passed** (737 + 5 test cổng shadow + 2 test ảnh fallback đã có). 0 API call.

## 14o. Research OS chạy thật lần đầu — URL đích danh + tách domain + lọc ngày cũ (2026-08-06 → 07)

Cả arc từ commit `8b36845` → `f6599a0`. Điểm chung của mọi lỗi trong mục này: **mỗi lớp đều trả về "một cái gì đó", nên không lớp nào trông hỏng** — hệ thống chạy đủ chu kỳ, ghi note vào vault, sinh proposal, mà nội dung thì rỗng.

**1. Chu kỳ nghiên cứu tự động + collector URL đích danh.** `run_research_cycle` đọc `config/projects/venho_hotel/research/research_questions.yaml`: domain có `queries:` → Tavily Search (quét rộng); domain có `urls:` → `collectors/tavily_extract.py` (đọc đúng trang Harry đưa). Kết quả → R0 source note + R2 synthesis trong vault → `ProposedFactStore` `pending_approval` → Harry duyệt trên VenHo OS. **DoD #13 giữ nguyên:** không code path nào promote R2→R3 tự động.

**2. Ba lỗi làm đường URL đích danh chưa từng thật sự hoạt động** (phát hiện khi guest_voice đọc 3 trang tốt mà ra 0 proposal):
- `extract_depth` mặc định `"basic"` → Agoda trả `Failed to fetch url`. Đổi sang `"advanced"`.
- Cap `MAX_CONTENT_CHARS = 6000` cắt **markdown thô**, mà 60–75% ký tự là cú pháp link/ảnh → 6000 ký tự đầu chỉ toàn nav chrome. Thêm `strip_markdown_noise()` (bỏ `![]()`, giữ text trong `[]()`, bỏ URL trần) **trước** khi cắt, nâng cap → 32000.
- `_MAX_SNIPPET_CHARS = 1200` trong `extract_facts` cắt tiếp lần hai trước khi Gemini nhìn thấy. Thêm `_MAX_SNIPPET_CHARS_PER_SOURCE = 30000` + tham số `per_source=True` (bật khi domain có `urls` và không có `queries`): mỗi trang đích danh đi **một prompt riêng**, không gộp 4 trang vào một prompt 48k.

**3. Dạng URL không suy đoán được.** Agoda `/vi-vn/` chạy với trang này, hỏng với trang khác; Booking cần `.vi.html` cho Ven Hồ nhưng `.en-us.html` cho An Homestay. YAML có comment "**do not 'normalise' them**" — URL Harry đưa phải giữ nguyên xi.

**4. Tách `competitor` → thêm domain `competitor_rating`.** Phát hiện thật: trang OTA **có điểm đánh giá nhưng không bao giờ có giá** (cả Agoda lẫn Booking render giá client-side theo ngày). Một domain không thể trả lời cả hai câu dưới luật "một câu hỏi trả lời được". `competitor` giữ câu hỏi giá + search queries (cố ý không có `urls`), `competitor_rating` giữ 4 URL đối thủ. Kèm theo: `ResearchDomain` Literal thêm `competitor_rating`, `domains.yaml` thêm cadence biweekly/90 ngày. Test đếm domain đổi 9→10 — chốt chống trôi này bắt đúng việc nó sinh ra để bắt.

**5. Dedupe không phụ thuộc cách đặt tên** (`proposed_fact_store.is_same_finding`). Gemini gọi cùng một con số là `review.overall_rating` lần này, `agoda.customer_rating` lần sau → trùng lặp tràn hàng đợi duyệt. Rule: cùng `(domain, source_uri, value)` **và** tập token của `fact_key` (sau khi bỏ `_KEY_NOISE`) là tập con của nhau. Hai bẫy đã dính rồi sửa: (a) chỉ so `(domain, uri, value)` thì `value_for_money=7.9` bị nuốt vì `cleanliness` cũng 7.9 cùng trang; (b) sau khi thêm `overall` vào noise, `overall_rating` rút về tập rỗng — mà tập rỗng là tập con của mọi thứ → thêm guard `if not tokens_a or not tokens_b: return tokens_a == tokens_b`.

**6. `TrendCandidateStore.reject()` + CLI `venho-growth trend-reject` + nút "Từ chối" trên VenHo OS** (route mới `api/v1/studio/growth/trend-candidates/reject`, mirror của approve). **Cố ý làm khác lời Harry ("bấm Cancel thì xoá luôn"): ghi tombstone `status: rejected`, không xoá dòng** — `merge_new` dedupe theo id, nên dòng bị xoá thật sẽ quay lại ở lần quét Thứ 6 kế tiếp và Harry phải từ chối cùng một lễ hội cũ mỗi tuần. Nhìn từ dashboard là biến mất như nhau. Panel cũng lọc luôn 17 candidate do brand-safety tự loại.

**7. Lọc ngày cũ ở `scan_trends` (2026-08-07).** Luật `is_stale_dated` trước chỉ nối vào fact proposal của `local_events`, nên Trend Radar tích Lễ hội Sen 26-28/6/2026, bài Trung thu 2024, trang tin có headline mới nhất 2021 — tất cả brand-safe, điểm cao, chờ Harry từ chối tay hàng tuần. **Gốc rễ không nằm ở chỗ nối dây mà ở bộ đọc ngày:** dạng tiếng Việt thật hoặc không có năm (`ngày 26-28/6`) hoặc viết chữ (`17 Tháng Mười Một 2021`) → `dates_in` khớp 0 → không gì trông cũ. Bổ sung: khoảng ngày `dd-dd/mm[/yyyy]`, `ngày dd/mm` (**bắt buộc có chữ "ngày"** — nếu không `8/10` trong đoạn review khách sạn thành ngày 8/10), tháng viết chữ + tháng số `dd tháng M năm yyyy`. Ngày thiếu năm quy về năm **gần hôm nay nhất** (đọc tháng 8/2026 thì `26/6` = 2026, đã qua). **Tháng trần vẫn là mùa, không phải ngày** — `"Tháng 10 đến tháng 2"` phải giữ nguyên non-stale, có test riêng. `scan_trends(..., today=)` nhận `today` inject được; đọc cả `title` lẫn `snippet` (tiêu đề hiếm khi tự ghi ngày); brand-safety vẫn được báo trước `stale_dated` khi một candidate dính cả hai.

**Backfill + xung đột với quyết định của người.** Lọc chỉ chạy lúc quét, mà `merge_new` bỏ qua id đã có → 3 dòng cũ sẽ nằm mãi. Chạy backfill một lần. Trong lúc đó Harry duyệt trên dashboard đúng một bài mà backfill vừa loại (Lễ hội Sen đã kết thúc) → rebase xong **khôi phục lại approval của Harry**: quyết định của người thắng bộ lọc tự động, không phải ngược lại. Đã báo Harry để tự quyết.

**Giới hạn thật, không phải sót:** bài *"Cuối tuần này ghé hồ Tây trải nghiệm Lễ hội sen"* không ghi ngày nào trong toàn bộ nội dung → bộ lọc ngày không thể bắt. Vẫn cần mắt người ở khâu duyệt.

**Verify:** `PYTHONPATH=. pytest -q` → **834 passed**. 0 API call. `npx tsc --noEmit` sạch bên `venho-os`.

## 14p. Audit closeout — Research OS/Trend Radar (2026-08-07)

- **Architecture:** audit toàn bộ arc `8b36845`→`f6599a0` và các route UI tương ứng trong `venho-os`. `run_research_cycle` chỉ ghi R0/R2 và proposal `pending_approval`; không có đường tự R2/R2-T→R3. M04 không tự sinh content; M10 chỉ đọc/đồng bộ artifact và gọi CLI có policy, không có DB riêng; publish vẫn thuộc M07 sau quyết định người duyệt.
- **Data contract cần nhớ:** proposal tiếp tục là JSON artifact id-keyed ở `data/projects/{project}/research/proposed_facts.json`, local decision thắng khi git-sync conflict. Trend reject là tombstone `status: rejected`, không được xoá record vì scan sau sẽ re-propose. `competitor_rating` là domain riêng (biweekly, expiry 90 ngày), tách khỏi `competitor` pricing.
- **Verification closeout:** `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **834/834 pass**, 0 API call; `venho-os: npm test -- --run` → **150/150 pass**; `npx tsc --noEmit` pass.
- **Cleanup:** xoá cache/dev artifacts không track (`__pycache__`, `.pytest_cache`, `.DS_Store`, `.log`, `.tmp`); không xoá docs/config hay JSON trong `data/`/knowledge stores. Không phát hiện unused import trong Python thay đổi (trừ `from __future__ import annotations`).

## 14q. DoD 11/24/25/26 follow-up (2026-08-07)

- **DoD #11:** `.github/workflows/growth-blog-seo.yml` mới chạy thứ 3 08:00 ICT. Workflow chỉ sinh/commit blog draft qua `venho-growth blog`; không có Make webhook hay dispatch path, nên không bypass editorial approval.
- **DoD #24:** audit phát hiện implementation đã tồn tại trong commit `b7409a3` nhưng roadmap/status cũ chưa phản ánh: `shared/backup/growth_backup.py` snapshot SQLite online, copy registry/facts/research, artifact CAS, restore vào scratch + `PRAGMA integrity_check` + row-count/checksum; CLI backup verify mặc định. Còn điều kiện vận hành: `VENHO_BACKUP_DIR` phải được Founder trỏ ra storage ngoài máy và job phải chạy định kỳ.
- **DoD #25/#26 không được làm giả:** code attribution/scorecard đã có. Hoàn tất đòi GA4 credential hoặc event feed từ booking form, một golden set do người review chấm và Vision QC thật; repo website đang có dirty changes nên không được tự ý sửa. Rollout giữ `shadow` đúng fail-closed.
- **Verify:** `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **835/835 pass**, 0 API call.

## 14r. FORBIDDEN = policy, và face gate không xét tóc/biểu cảm (2026-08-07)

- **FORBIDDEN chỉ nhận câu phủ định.** `knowledge_studio/vision/forbidden_policy.py`:
  rule phải bắt đầu bằng no/not/never/without/avoid/exclude. Model khi được hỏi "thứ rõ ràng
  KHÔNG có trong ảnh" trả về tên feature trần cũng nhiều như trả về lệnh cấm — DNA `outside`
  từng liệt `lake view`, `railing`, `Rooftop terrace`, `Cityscape` làm FORBIDDEN, tức là cấm
  đúng những thứ làm nên chủ thể. Sanitizer chạy ở 2 chỗ: `pass2_consolidate` (lúc build) và
  `overlay_merge` (lúc render — cứu các DNA sinh trước khi có policy này).
- **Validator chỉ dùng rule `curated`.** `validator_studio/observe_adapter.py::_forbidden_rules_for_validation`.
  Trước đó toàn bộ rule kể cả `observed` được gửi sang validator, nên `outside` đang cấm
  `No visible lake or cityscape` và `No visible railing` — đúng ngữ pháp nên sanitizer không bắt
  được. Một rule bị vi phạm = severity high = kill-switch = tốn thêm nguyên một ảnh. Subject
  không có overlay (không có rule curated nào) mới rơi về `observed`.
- **`venho vision clean-forbidden --project venho_hotel [--subject X] [--apply]`** — dry-run mặc
  định, tất định, 0 vision call, không bump version; re-render .md/.json/_COMPACT.md từ object đã
  dọn. Đã dọn 21 mục (outside 12, linh_an 4, room_1 3, lake_view_room 2).
- **Rule viết sai dạng nhưng đúng ý thì MIGRATE, đừng xoá.** 4 mục của `linh_an`
  (`glasses`, `hat`, `visible tattoos`, `visible piercings other than earrings`) là chính sách
  thật — đã viết lại thành rule curated trong `linh_an.overrides.yaml` trước khi cho sanitizer xoá.
- **Face gate không được trượt vì tóc hoặc biểu cảm.** `prompts/observe_face_against_dna.md`:
  `identity_structure` chỉ xét xương và ngũ quan. DNA duyệt nhiều kiểu tóc và nhiều biểu cảm, nên
  xét chúng như tín hiệu nhận dạng là sai theo chính DNA — bằng chứng: `linh-an-master-face.png`
  (ảnh gốc dùng để sinh mọi ảnh Linh An) bị chính gate của nó hard-reject 0.0 chỉ vì để tóc xoã.
  Sau khi sửa: master face 0.0 → 88.26, ảnh rooftop 0.0 → 84.83. Đây cũng là nguồn của hiện tượng
  "không tất định" từng phải băng bó bằng sampling 3 lần trong `validate_generated.py`.
- **Overlay theo scenario:** `config/projects/venho_hotel/subjects/<subject>.<scenario_profile_id>.overrides.yaml`,
  merge in-memory lúc validate, không ghi đè DNA. **Bắt buộc khai lại `forbidden:`** — `apply_overlay`
  dựng lại danh sách từ overlay hiện tại + observed, nên overlay thiếu `forbidden:` sẽ làm rơi sạch
  rule curated (đo được: forbidden 100 → 0 trên một ảnh rooftop tốt).

## 14s. Linh An official-asset readiness — Steps 1–3 (2026-08-10)

- **Hai generation lane là contract chung UI/prompt/API.** `identity` dùng standing face reference cho portrait, standing, leaning và pose tĩnh. `action` áp dụng cho running, cycling, sitting, jumping, dancing, swimming, climbing và dynamic pose khác; bắt buộc text-to-image để standing reference không khóa sai body geometry. Manifest phải ghi `generationLane`, `requestedUseRef`, `effectiveUseRef`, và `references.mode`.
- **Prompt người dùng vẫn được giữ, nhưng policy không thể bị xoá bằng textarea.** `linh_an_generation_protocol_v1` được append ở server-side spend boundary, sau prompt đã submit. Protocol mang scenario lock, exact effective outfit, pose/action, reference policy và yêu cầu Linh An là physical actor. Manifest ghi cả `userPrompt`, `serverPrompt`, `generationProtocol`, prompt effective và hash.
- **CLI/test QC phải tách khỏi audit live.** `venho validate image|prompt|face|content --output-root <dir>` ghi report/manifest vào root chỉ định. Test CLI bắt buộc truyền temporary output root; không được sinh report mock vào `data/projects/venho_hotel/validation/`.
- **Chưa có approval mới.** Không chạy generation trả phí trong Steps 1–3. Asset official vẫn yêu cầu image-DNA pass + face-QC ≥90 + không kill-switch + human review; artifact `revise` không được xem là approved.
- **Verify closeout:** AI Studio `841/841` pytest pass; Venho OS `191/191` vitest pass, TypeScript/build pass. Lint OS vẫn có 2 lỗi sẵn có trong `design_handoff_venho_os_cockpit/support.js`.

## 14t. Google Gemini Image Provider option — handoff to implementation (2026-08-10)

- Chi tiết triển khai nằm tại `venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md`. Gemini phải đi qua API/provider adapter của Venho OS, không qua Google Flow UI, để tất cả artifact tiếp tục có immutable run/variant + manifest + QC report.
- Preserve Validator Studio as independent judge. Không sửa DNA/prompt/threshold để làm provider mới pass; official vẫn Face `>=90`, image/intent approve (nơi áp dụng), no kill-switch, rồi human review.
- Provider candidates: Nano Banana 2 (`gemini-3.1-flash-image`) cho volume/lifestyle; Nano Banana Pro (`gemini-3-pro-image`) cho reference/identity phức tạp. `gemini-2.5-flash-image` legacy, không dùng cho đường mới; Nano Banana 2 Lite không dùng làm official asset vì không tối ưu multi-reference.
- Bước 5 đã tạo hero/café/business nhưng Face QC chỉ 84.03–88.8; West Lake bị provider safety block; không asset nào official. Benchmark Gemini phải diễn ra trước khi tạo tiếp library: 6 scenario static × Flash/Pro, same prompt/reference/QC, manifest riêng. Chỉ chạy paid benchmark khi user authorize.

## 14. Task Closing Protocol

Khi người dùng nói **"kết thúc task"**, Codex phải tự động:

1. Cập nhật `task_memory.md` nếu có quy ước, kiến trúc, contract, CLI, hoặc integration seam mới.
2. Cập nhật `task_status.md` nếu module/stage/test count/commit/package mẫu thay đổi.
3. Ghi rõ commit hash, test command/kết quả, output mẫu nếu có.
4. Kiểm tra `git status --short` và báo working tree còn sạch hay còn thay đổi.

## 14u. Một lần duyệt theo lịch — Bước 1: canonical pipeline (2026-08-10)

- Growth Agent được chốt là pipeline production duy nhất cho nội dung Facebook/Instagram.
- `legacy_agent_active: false` trong Growth feature flags.
- GitHub Actions của `venho-social-content-agent` đã bỏ trigger cron; chỉ còn `workflow_dispatch` để khôi phục dữ liệu lịch sử có chủ đích. Nó không còn được phép tự tạo hoặc gửi bài theo lịch production.
- Chưa bật dispatch/scheduler Growth ở bước này; các bước sau phải sửa OAuth, chuyển approval thành scheduled state và hoàn thiện dispatcher trước khi bật đăng tự động.

## 14v. Một lần duyệt theo lịch — Bước 2: Google Drive OAuth (2026-08-10)

- Đã sửa Growth `GoogleDriveUploader`: client ID/secret từ GitHub Secrets được đưa vào authorized-user payload trước khi tạo Google credentials; không còn gán vào thuộc tính chỉ đọc `Credentials.client_id`/`client_secret`.
- Đây là nguyên nhân trực tiếp làm GitHub Actions `Growth Agent Weekly Cycle` thất bại trong 25 giây khi refresh token hết hạn.
- Regression test tái hiện token hết hạn, xác nhận credentials nhận đúng client config và gọi refresh thành công mà không có network call.

## 14w. Một lần duyệt theo lịch — Bước 3: Duyệt toàn bộ tuần (2026-08-10)

- `venho-growth approve-week --approved-by <email> [--week-start YYYY-MM-DD]` là thao tác duy nhất duyệt tất cả bản ghi `PENDING_APPROVAL` có `slot_id` trong cùng tuần ISO. Default là tuần hiện tại theo giờ Việt Nam.
- Mỗi bài được chuyển atomically sang `APPROVED_SCHEDULED`, có `approved_at`, `approved_by`, `approval_scope: weekly_schedule` và immutable `approval_snapshot`; tuyệt đối không khởi tạo Make bridge hay gọi webhook trong thao tác này.
- `PublicationRegistry.update_many_if_status()` kiểm tra toàn bộ batch dưới một file lock trước khi ghi, nên nếu một bài đổi trạng thái trong lúc duyệt thì không bài nào của tuần bị duyệt nửa chừng.
- VENHO OS có `POST /api/v1/studio/growth/approve-week` và nút **Duyệt toàn bộ tuần**; endpoint đồng bộ registry lên GitHub sau khi CLI thành công.

## 14x. Một lần duyệt theo lịch — Bước 4: Scheduler xuất bản độc lập (2026-08-10)

- Đường production bắt buộc là `PENDING_APPROVAL` → `APPROVED_SCHEDULED` (Duyệt toàn bộ tuần) → `DISPATCHING` → gateway. `approve-and-dispatch` đã bị retire ở CLI để tab cũ hoặc API cũ không thể đăng ngay sau duyệt.
- `venho-growth dispatch-due` là entrypoint scheduler: chỉ claim bản ghi `APPROVED_SCHEDULED` có `slot_id` đến hạn theo `growth/cadence_policy.yaml` (09:00, Asia/Ho_Chi_Minh). Claim có điều kiện đảm bảo hai tick trùng nhau không thể cùng gọi Make cho một bài.
- VENHO OS có hook `POST /api/v1/studio/growth/scheduler/dispatch`, chỉ nhận `Authorization: Bearer $GROWTH_SCHEDULER_TOKEN`; hook refresh/sync registry Git rồi gọi `dispatch-due`. Scheduler bên ngoài cần poll hook này mỗi 5 phút; approval không gọi hook.
- Dashboard đã bỏ toàn bộ nút duyệt riêng và duyệt từng nhóm; chỉ còn **Duyệt toàn bộ tuần**. Giữ reject/edit trước khi duyệt và retry dispatch khi gateway lỗi.

## 14y. Một lần duyệt theo lịch — Bước 5: Hợp đồng Scheduler rollout (2026-08-10)

- Scheduler cloud chỉ được gọi `POST /api/v1/studio/growth/scheduler/dispatch` mỗi 5 phút, với `Authorization: Bearer $GROWTH_SCHEDULER_TOKEN`; tuyệt đối không gọi Make publishing webhook trực tiếp.
- Đã thêm `venho-os/docs/GROWTH_SCHEDULER_ROLLOUT.md` và khai báo biến môi trường trong `.env.example`. Chưa kích hoạt scheduler: VENHO OS chưa có URL public và runtime secret chưa được cấu hình; cloud scheduler không gọi được `localhost`.
- Không được thử gọi endpoint production cho tới khi có hai giá trị trên, vì mọi publication đã duyệt và quá giờ sẽ được dispatcher xử lý ngay theo contract.

## 14z. Một lần duyệt theo lịch — Bước 5: GitHub Actions Scheduler (2026-08-10)

- Quyết định vận hành Startup: dùng GitHub Actions, không phụ thuộc Mac Mini hay VENHO OS public endpoint. Workflow `.github/workflows/growth-publish-scheduler.yml` chạy best-effort mỗi 5 phút, gọi trực tiếp `venho-growth dispatch-due`, rồi commit `publication_registry.json` và `growth.db`.
- Workflow scheduler và `growth-daily-cycle.yml` dùng cùng concurrency group `growth-publication-state`; không thể ghi đồng thời state Git-backed.
- Secrets bắt buộc tại GitHub repository: `MAKE_GROWTH_WEBHOOK_URL` và (nếu Make xác thực) `MAKE_GROWTH_WEBHOOK_SECRET`. Các secrets Zalo chỉ cần khi có publication Zalo. Không dùng `GROWTH_SCHEDULER_TOKEN` trong phương án GitHub Actions.
- Workflow không dùng `--allow-shadow`: rollout state `shadow` vẫn fail-closed và giữ bài, không tự đăng. Chỉ khi rollout được advance theo quy trình mới gửi Make.
- GitHub Repository Secret `MAKE_GROWTH_WEBHOOK_URL` đã được cấu hình ngày 2026-08-10. Make không có webhook secret ở cấu hình hiện tại, nên không cần `MAKE_GROWTH_WEBHOOK_SECRET`.

## 14aa. Một lần duyệt theo lịch — Bước 6: Migration, kiểm thử và rollout gate (2026-08-10)

- Không có publication `APPROVED_SCHEDULED` trong registry hiện tại. Các bản ghi chưa kết thúc thuộc cơ chế cũ (`GATEWAY_*`/`SHADOW_HELD`), không được migrate về lịch mới vì có thể đăng lại bài đã quá hạn.
- Scorecard thật `growth-scheduler-2026-08`: 2.22/10, sample `PUBLISHED=0`; thiếu telemetry post, brand/claim và Vision QC thật. Gate chặn `shadow → pilot_25` đúng thiết kế; không thay đổi rollout state và không chạy dispatch.
- Runbook rollout hợp lệ. Test regression gồm scheduler, weekly approval, OAuth, policy và rollout: 69/69 pass. `git diff --check` pass.

## 14ab. Khắc phục Dashboard approval queue — Bước 7a: trạng thái rỗng rõ ràng (2026-08-10)

- VENHO OS luôn hiển thị một nút **Duyệt toàn bộ tuần** duy nhất; khi không có `PENDING_APPROVAL`, nút bị vô hiệu với lý do rõ ràng thay vì biến mất.
- `POST /api/v1/studio/growth/approve-week` nhận diện structured error của CLI khi queue rỗng và trả HTTP 409 / `NO_PENDING_APPROVAL` với thông báo tiếng Việt; không còn báo sai là `Command failed`/lỗi hạ tầng.
- ESLint hai file thay đổi và `git diff --check` đã pass.

## 14ac. Khắc phục Dashboard approval queue — Bước 7b: chẩn đoán lệch Slot (2026-08-10)

- Ảnh Dashboard được đối chiếu với state thật: tuần 2026-08-10 có Slot T2/T6/T7 là `OPEN`, Slot T4 là `PENDING_APPROVAL` nhưng không có `content_package_id`; không có publication nào ở `APPROVED_SCHEDULED`.
- Các bài đang hiện ở bảng trên là publication cũ của tuần 2026-08-03, đều `SHADOW_HELD`; chúng không phải hàng chờ duyệt của tuần hiện tại. State `shadow` chủ động chặn webhook Make.
- Kết luận: thao tác Duyệt không thành công, Slot không đổi là đúng với state hiện tại, và không bài nào sẽ được đăng.

## 14ad. Khắc phục tuần 2026-08-10 — Bước 7c: đồng bộ Slot và lọc queue (2026-08-10)

- Đã chạy `venho-growth ensure-slots --horizon-days 14`: thêm 2 Slot còn thiếu trong horizon, không ghi đè Slot tuần hiện tại.
- `list-pending` chỉ trả `PENDING_APPROVAL` và `GATEWAY_ERROR`; các bài `SHADOW_HELD` cũ không còn xuất hiện trong bảng duyệt, vì đã được duyệt từ trước và không có thao tác Duyệt/Từ chối.
- Kiểm thử: `tests/test_growth_approve_and_dispatch.py` 38/38 pass; `git diff --check` pass. Tuần hiện tại vẫn chưa có content package; T4 còn orphan `PENDING_APPROVAL`, sẽ được tuần-cycle xử lý ở bước tạo content.

## 14ae. Khắc phục tuần 2026-08-10 — Bước 7d: Weekly Cycle tự phục hồi (2026-08-10)

- Workflow `Growth Agent Weekly Cycle` được lập lịch thử lại tự động vào 08:00, 10:00 và 12:00 thứ Hai (Asia/Ho_Chi_Minh). `JobStore` chỉ cho một run thành công mỗi ISO week; các lần còn lại tự bỏ qua, còn run lỗi sẽ được thử lại mà không cần thao tác Dashboard.
- Nguyên nhân run 10/08 thất bại: GitHub chạy SHA `4287651` chứa lỗi Google Drive OAuth cũ. Bản sửa OAuth và lịch retry đang ở working tree local, chưa có trên nhánh GitHub để Action sử dụng.
- Xác minh YAML schedule và `tests/test_growth_weekly_cycle.py`: 5/5 pass; `git diff --check` pass.

## 14af. Khắc phục tuần 2026-08-10 — Bước 7e: phát hành Automation Cycle (2026-08-10)

- Đã push Automation Cycle vào `west-lake-living/venho-ai-studio` commit `f3ae89f`; `venho-os` commit `db6db53`; đồng thời tắt cron legacy tại `venho-social-content-agent` commit `cda5641`.
- AI Studio remote có phát sinh state commits đồng thời; Automation commit được rebase/cherry-pick an toàn trên remote HEAD để không ghi đè publication registry hoặc research state mới.
- GitHub Actions từ nay dùng workflow Weekly Cycle có retry tự động; chỉ việc chờ lịch Monday tiếp theo hoặc kích hoạt workflow_dispatch để tạo batch tuần hiện tại.

## 14ag. Bàn giao debug tiếp theo (2026-08-10)

- Remote `main` đã chứa Growth Automation ở HEAD `9792244` (workflow chính `f3ae89f`), VENHO OS `db6db53`, legacy manual-only `cda5641`. GitHub xác nhận `Growth Agent Weekly Cycle` và `Growth Agent Publish Scheduler` đang active.
- Chưa tạo batch content tuần 2026-08-10 sau khi phát hành. Việc debug tiếp theo: trigger `Growth Agent Weekly Cycle` trên GitHub từ source mới, kiểm tra 4 Slot T2/T4/T6/T7 có `content_package_id` và publication `PENDING_APPROVAL`, rồi xác nhận Dashboard hiển thị các thao tác Duyệt/Từ chối.
- Không dispatch/publish trong bước bàn giao này. Rollout vẫn `shadow`; không được dùng `--allow-shadow`.

## 14ah. Growth Agent — two-week cycle, rejected replacement và Monday recovery (2026-08-10)

- Weekly Cycle production chạy Chủ nhật **20:00 Asia/Ho_Chi_Minh**, có fallback **22:00**. Chu kỳ được neo theo từng 2 tuần và idempotent: mỗi batch tạo **8 content slots/lần đăng** (T2/T4/T6/T7 × 2 tuần), mỗi slot có biến thể Facebook + Instagram, tổng **16 publication records**.
- `venho-growth approve-week` duyệt atomically toàn bộ publication trong cửa sổ 14 ngày; một lần **Duyệt tất cả** đủ lịch đăng hai tuần.
- Publication bị từ chối được thay bằng content mới cho đúng platform và đúng slot. VENHO OS gọi workflow `growth-replace-rejected.yml` ngay sau reject; cron 15 phút là fallback. Bản cũ và bản thay thế liên kết bằng `replacement_publication_id` / `replaces_publication_id` để giữ audit trail.
- Scheduler dùng `--allow-shadow` trong production workflow sau approval gate; manual `catch_up_today` chỉ giải phóng slot bị lỡ trong ngày hiện tại theo giờ Việt Nam, không phát hành backlog cũ.
- Khôi phục lịch T2 2026-08-10 qua GitHub run `31389624111`: Make trả `PUBLISHED` cho Facebook và Instagram; Instagram media ID `17929423083379767`. Facebook trả placeholder `3. Post ID` / `3.permalink_url`, nên trạng thái gateway đã thành công nhưng chưa có permalink thật để kiểm chứng trực quan.
- Đã sửa thứ tự persistence của scheduler thành stage/commit trước, rồi pull-rebase/push; run kiểm chứng `31389945843` hoàn tất toàn bộ và không dispatch trùng.
- AI Studio production commits: `fc6d291` và `a04f09b`. VENHO OS reject-trigger commit: `2632537`.
- Verify: `pytest -q tests/test_growth_weekly_cycle.py tests/test_growth_approve_and_dispatch.py tests/test_growth_replace_rejected.py` → **48/48 passed**; VENHO OS `npx tsc --noEmit` pass và publication-registry sync tests **9/9 passed**.

## 14ai. Master System Prompt — Factual Safety Rules (2026-08-11)

- Đã bổ sung vào `content_studio/generators/prompts/venho_content_generator_master_prompt.md` bộ quy tắc bắt buộc: không social proof gián tiếp khi thiếu bằng chứng; không giả định thời gian hiện tại; không negative positioning; kiểm tra negative interpretation; caption publishing phải là plain text với URL/hashtag thuần.
- `social_prompts.MASTER_SYSTEM_PROMPT` đã nạp và kiểm tra đủ 5 nhóm rule.
- Commit đã push lên `west-lake-living/venho-ai-studio`: `dc4b398` (`feat: add factual safety rules to master prompt`).
- Kiểm tra targeted prompt: PASS. Bộ test legacy `tests/test_claude_social_generator.py` còn 3 lỗi baseline do tham chiếu hằng/chuỗi prompt cũ, không phát sinh từ thay đổi factual-safety.

## Action Composite v2 — P7 hardening (2026-08-12)

Reviewed and optimized the Codex-authored `image_studio_runtime/action_composite/` (P1–P6).
Plan: `docs/Image studio/LINH_AN_ACTION_COMPOSITE_HYBRID_COMFYUI_TECHNICAL_PLAN_v1.0.md`.
Full detail in `task_status.md`. The parts worth remembering:

- **18 green tests were hiding an inert Pixel Preservation Lock.** The check diffed only the
  alpha channel of an image the loader always converts to RGBA — so alpha never varies and every
  RGB mutation outside the mask passed. Reproduced by running the code, not by reading it.
- **The composite step made the gate a tautology.** `Image.composite` discards outside-mask pixels
  by construction, so checking its output proves nothing. The gate must judge the restorer's raw
  output; that is what catches a ComfyUI workflow that regenerated the whole scene and left a face
  pasted onto the original body.
- **The locked region is `mask == 0`, not "outside the bbox"** — feathered masks blend over their
  own edge, so the naive strict guard fails every valid run. `regression_guard.protected_region()`.
- **The ComfyUI adapter never sent the images** (workflow JSON only, no base/mask/A2). A "complete"
  P1–P6 with a checked box for a POC that could not physically have run.
- Workflow node wiring is declared in config by `_meta.title` (`VENHO_COMFYUI_NODE_BINDINGS`), never
  guessed from node ids.
- AVIF intake was writing converted JPEGs into Harry's photo folders and reusing an unrelated
  same-stem `.jpg`. Converted images now live in content-hashed `data/.cache/avif/`.
- Baseline discipline: before blaming this work for the 99 full-suite failures, stashed everything
  and re-ran — identical 99 at baseline, all in subject-resolver/validator/video-studio config.

Targeted suite 77/77. **Never run against a live ComfyUI** — model files and the 10-image A2
benchmark are still open, and the first real run is the only meaningful test of the adapter.

## Action Composite v2 — P8 first live run: RAM, not code (2026-08-12)

Installed ComfyUI + PuLID node + SDXL base + AntelopeV2 locally, wrote
`config/comfyui/face_restore_v1_api.json` (verified against the PuLID node's real `INPUT_TYPES`,
not guessed), generated 2 real Linh An action test images (gpt-image-2, paid, `data/` gitignored,
not brand wardrobe), ran the actual adapter against the actual server for the first time.

**Both jobs timed out — but the cause is the Mac mini M4's 16GB RAM, not a pipeline bug.**
`vm.swapusage` mid-run: 20.9/21.5GB swap used. SDXL base (6.5G) + PuLID + EVA-CLIP (2G) +
InsightFace together don't fit in 16GB unified memory. `/upload/image`, `inject_inputs()`, and the
queued graph were all confirmed correct via `/queue` inspection — ComfyUI accepted and started the
job, it just never finished a single sampling step in 8.6 minutes. The P7 fail-fast path never
fired because ComfyUI itself never reported an error status; the process was alive, just thrashing.

Harry's call: stop here, don't retry with a longer timeout or a different model this session.
Still open: a lighter stack (SD1.5 IPAdapter FaceID, untested) or more RAM/cloud GPU before the
next live attempt; the 10-image benchmark is still blocked behind that; the workflow JSON has
never actually completed end-to-end. Full detail: `task_status.md` P8 section.

## Growth Agent — per-topic Duyệt + real slot_date exposed (2026-08-13)

Requested from the `venho-os` side of a dashboard debugging session (full context, screenshot,
and Harry's clarifying answers live in `venho-os/task_memory.md` under the same date). Only the
`venho-ai-studio` side is recorded here.

- `growth_orchestrator/application/approve_and_dispatch.py`:
  - Refactored `_scheduled_week_start()` to use a new `_slot_date(publication)` helper that
    parses the real calendar date out of `slot_id` (`slot-2026-08-14-...`).
  - `list_pending()` now includes `slot_date` (ISO string or `null`) on every row, so the
    dashboard can tell two same-weekday topics from different weeks apart — previously it only
    exposed `day` (the weekday name), and `approve_week` scans a **two-week** window, so this was
    a real ambiguity, not just a display nit.
  - New `approve_publications(publication_ids, approved_by, project, data_root, registry)`:
    approves an exact, caller-given set of `PENDING_APPROVAL` publication_ids atomically (reuses
    `PublicationRegistry.update_many_if_status`, so a status race on any one id fails the whole
    batch, same guarantee `approve_week` already had). Sets `approval_scope: "topic_group"` to
    distinguish it from `approve_week`'s `"weekly_schedule"` in the registry. `approve_week`
    itself is untouched.
- `growth_orchestrator/cli.py`: new `approve-group` command (`--publication-id` repeatable,
  `--approved-by`), same error-handling pattern as `approve-week`/`reject`. Verified live:
  `venho-growth --help` lists it (editable pip install picks up the change with no reinstall).
- Tests added to `tests/test_growth_approve_and_dispatch.py`: `slot_date` exposure, approving
  only the given topic (sibling topic in the same slot stays untouched), unknown id raises
  `KeyError`, atomicity when one id in the batch changed status underneath the call. 45/45 pass
  in that file.
- Confirmed the 30 pre-existing failures in `test_growth_daily_cycle.py`/
  `test_growth_weekly_cycle.py` are unrelated: `git stash`'d this change and reran — identical
  failure list on the unmodified code.
- `data/projects/venho_hotel/publishing/publication_registry.json` was dirty in the working tree
  before this — Harry's own real "Sửa" edit from the dashboard earlier that day, not test
  fallout. Stashed just that file around `git pull --rebase` (origin had an unrelated CI
  `chore: publication registry update` commit), popped after — came back as "nothing to commit",
  meaning the CI commit already carried the same edit forward. No data lost, no manual merge
  needed.
- Committed `58ad88d`, pushed to `origin/main`.

## Growth Agent — diversify 4 weekly posts by cadence-day topic lanes (2026-08-13)

Harry's complaint, verified in code: all 4 weekly posts read as the same post (Hồ Tây, mặt
nước, buổi sáng). `content_pillars.yaml` held exactly 5 near-synonymous topics
(`morning at West Lake` / `lake view room` / `quiet Hanoi stay` / `lake view morning` /
`simple hotel comfort`) shared across Mon/Wed/Fri, picked by `_pick_topic`'s bare
`flat[index % len(flat)]` off a `rotation_state.json["regular"]` cursor already at **41**
(~8 repeats each). Meanwhile the research pipeline was already producing real material
(21 approved facts, 8 verified Trend Radar candidates, a 7-day weather forecast) but
`_pick_topic`/`_build_creative_brief` only ever wired it into the **Saturday** special lane —
`proof_points` on every Mon/Wed/Fri brief was hardcoded `[]`. Image scenario was a 1:1
`SCENARIO_BY_DNA_SUBJECT` map, so every "outside" post rendered the identical rooftop-sunrise
concept even though the registry has 3 "outside" scenarios (sunrise/sunset/shade).

Design chosen with Harry (AskUserQuestion): hybrid pool (curated + research) · only
`status=approved` facts (never `pending_approval`) · a lane with no fresh fact/event falls back
to its curated topics rather than leaving a slot empty · scenario pool now varies by lane +
weather, not just dna_subject.

**What changed:**
- `content_pillars.yaml`: new `lanes.<day>` shape — `monday`→`west_lake_life` (10 topics),
  `wednesday`→`local_discovery` (8 topics + `research_domains: [local_events, local_intel]`),
  `friday`→`hotel_experience` (10 topics), `saturday`→`local_guide_trend` (special_topics moved
  under `lanes.saturday`, same shape as before). Old top-level `pillars`/`special_topics` kept
  as a documented deprecated fallback so anything still reading that shape doesn't break.
- `growth_orchestrator/application/topic_selector.py` (new): `select_from_candidates()` —
  cooldown (default 60d, reads `PublicationRegistry`'s `topic`+`created_at`) + rotation among
  the fresh subset; if every candidate is still in cooldown, picks the least-recently-used one
  instead of raising or leaving a slot empty. With an empty registry (fresh state, most tests)
  this reduces to the exact old `flat[index % len(flat)]` — verified byte-for-byte against the
  pre-existing special-lane unit tests, all passed unmodified. Also exports `advance_rotation()`
  (renamed from a private `_advance_rotation`) for `daily_cycle._pick_scenario`'s own cursor.
- `growth_orchestrator/application/local_intel.py` (new): `approved_local_facts()` reads
  `ProposedFactStore.list_items(status="approved")` **only** (Harry's explicit call), filters
  `local_events` facts whose `DD/MM/YYYY[-DD/MM/YYYY]` value has already ended.
  `local_intel_topic_entries()` shapes them into topic candidates with
  `proof_points: [{"text", "fact_key"}]` — exactly `contracts/creative_brief.schema.json`'s
  required shape, which `_build_creative_brief` had never populated before.
- `daily_cycle.py`:
  - `_pick_topic` dispatches to `_pick_regular_topic` (Mon/Wed/Fri: research entries take
    priority over curated when any exist and pass cooldown) or `_pick_special_topic`
    (Saturday: unchanged mechanism, just cooldown-aware now).
  - New `_pick_scenario`: rotates a lane's `scenario_pool` (declared per-lane in
    content_pillars.yaml) instead of the old 1:1 `SCENARIO_BY_DNA_SUBJECT` map. A topic that
    already names its own `dna_subject` (Saturday curated/trend entries, legacy shape) keeps
    deciding the subject, only the scenario *within* it varies; a topic with none (new
    Mon/Wed/Fri lanes) lets the scenario decide the subject and writes it back onto
    `topic["dna_subject"]`. Weather override (previously Saturday-only) now applies to every
    day via generalized `_weather_context_for_date` / `_next_cadence_date`.
  - `_build_creative_brief` gained optional `scenario_key=`/`prompt_rules=`/`recent_topics=`
    kwargs, all defaulting to the old behaviour when omitted — the 4 direct-call weather tests
    in `test_research_weather_and_sources.py` needed zero changes.
  - New `_recent_topics()` — last 6 distinct posted topics, fed into every brief as an
    anti-repeat hint (0 extra API cost, the cheapest diversity lever available).
- `content_studio/generators/social_prompts.py`: `select_system_prompt` now branches on a new
  `ContentRequest.prompt_rules` field (`west_lake_life`/`local_discovery`/`weekend_events`/
  `default`) rather than only `lane`/`dna_subject`; added `_LOCAL_DISCOVERY_RULES` ("only name
  places/events actually supplied, never invent one" — mirrors `_WEEKEND_EVENTS_RULES`'s proven
  shape) and a `_SEO_KEYWORDS_BLOCK` naming Harry's exact 4 keywords ("Ven Hồ Hotel", "khách sạn
  view Hồ Tây", "Nguyễn Đình Thi", "hoàng hôn Hồ Tây"). `lane` itself stays the closed
  `daily`/`saturday_trend` enum creative_brief.schema.json requires — `prompt_rules` is a
  separate, schema-permitted (`additionalProperties: true`) extension.
- `growth_orchestrator/bridges/m05_content_bridge.py`: passes `brief["proof_points"]` →
  `ContentRequest.research_facts`, `brief["recent_topics"]` → `.recent_topics`,
  `brief["prompt_rules"]` → `.prompt_rules`.
- `growth_orchestrator/application/weekly_cycle.py`: `WEEKLY_CYCLE_JOB_VERSION` **"3" → "4"**
  (topic-selection contract changed; skipping the bump would make the next fortnight run
  silently no-op as already-`SUCCEEDED` under v3 — same reasoning as the v1→v2 bump's own
  comment). Two hardcoded `fortnight-v3-...` test job keys updated to `v4` accordingly.
- Fixed a **pre-existing, unrelated** bug blocking verification: `test_growth_daily_cycle.py`/
  `test_growth_weekly_cycle.py`/`test_growth_budget_gate.py`'s `_tmp_data_root()` fixture copied
  `VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json`, a filename that no longer exists on disk (split into
  `_1_DNA.json`/`_2_DNA.json` at some earlier point) — every test in those 3 files failed at
  fixture setup regardless of this change (confirmed via `git stash` baseline: same failures on
  unmodified code). Fixed by copying the real `_1`/`_2` files plus `VENHO_HOTEL_LOBBY_DNA.json`
  (newly needed since Friday's scenario_pool can pick `venho_lobby_cozy`).
- 20 new tests (`tests/test_topic_selector.py` ×8, `tests/test_local_intel.py` ×7,
  `tests/test_growth_daily_cycle.py` ×6: four different pillars across a week, Wednesday
  fact-backed vs curated-fallback, proof_points reaching the generator, scenario variety across
  4 Friday runs, recent_topics reaching the generator) + 3 stale tests corrected (fallback-image
  test's hardcoded literal topic string, two job-version-3 test literals). Full suite: 863 pass
  (up from 843 baseline-with-the-fixture-fix), the 70 remaining failures are pre-existing and
  unrelated (Video Studio/Validator/subject_resolver — confirmed identical failure list via
  `git stash` baseline diff, none touch anything this change modified).

**Live production verification (Harry approved via AskUserQuestion, chose "reject old, run
all 4"):** rejected the 4 stale near-duplicate `PENDING_APPROVAL` rows
(`pub-wednesday-facebook-{582e1b20,25e2b050,45aa268d,42f9e395}`, all "lake view"/"morning at
West Lake" topics), then ran real `venho-growth daily-cycle --day {monday,wednesday,friday,
saturday} --no-image` against production data (`ANTHROPIC_API_KEY` had to be sourced from
`.env.local` manually — not exported by default in this shell). Monday's first attempt hit the
Bash tool's 2-minute default timeout mid-run (3/4 platforms had already queued before the kill);
subsequent days ran with an explicit longer timeout. Result — 4 genuinely distinct topics now
in the real queue: Monday "người Hà Nội tập thể dục quanh Hồ Tây lúc 6h sáng" (curated,
westlake), Wednesday "Chợ Hoa Quảng Bá, 236 Âu Cơ" (**research-backed**, from an approved
`local_intel` fact), Friday "góc đọc sách ở lobby ngày mưa" (curated, lobby — first time this
dna_subject has ever been used, was unreachable before this fix), Saturday "Sen Tây Hồ: Tinh
hoa văn hoá Việt" (**Trend Radar**, `special_lane_type: cultural_event`/`lifestyle_trend`).
Facebook draft for Wednesday and Facebook+Zalo for Saturday were silently dropped by the
existing content-validator retry-then-drop path (pre-existing behavior, unrelated to this
change) — Instagram/Threads queued fine for both.

Also answered a follow-up: Trend Radar cannot and does not search Facebook/TikTok directly —
`research_engine/trend_radar/collectors/` has no FB/IG/TikTok collector at all, only Tavily
search + a named-URL extractor. This is a deliberate policy line (§7.2 in the plan, quoted
verbatim in `tavily_extract.py`'s docstring): "reverse-engineered wrappers driving a personal
account's session cookie, and harvesting competitors' Facebook/Instagram/TikTok" is exactly what
is forbidden — the risk being losing the account, not a technical limitation.

Rebasing onto `origin/main` before push required no manual conflict resolution — 3 unrelated CI
commits landed while this session ran (`chore: research cycle 2026-08-13` + 2×
`chore: publication registry update [skip ci]`), `git pull --rebase` merged them cleanly since
the touched JSON regions didn't overlap. Committed `843a273`, pushed to `origin/main`.
## Gemini Flash latest — DNA pipeline smoke test COMPLETE (2026-08-13)

- `.env.local` contains `GEMINI_API_KEY`; key value was never printed or committed.
- Mode A/B/C provider path now uses `gemini-flash-latest` for image observation and DNA synthesis.
- Real API smoke test passed on a Ven Ho room image: valid JSON returned (`subject`, `confidence`).
- Offline targeted tests: **64 passed**. Two existing subject-resolver/schema tests remain unrelated failures.
- No full Mode B/C live regeneration was run; this avoided unnecessary multi-image API spend.
- Local implementation changes remain uncommitted and require review before release.

## Growth Agent — "Replace Rejected Content" all-jobs-failed fix (2026-08-13)

Github notified 2 consecutive failed runs of the `growth-replace-rejected.yml` workflow
(06:06 and 04:31 UTC). Log showed: `{"ok": false, "error": "Replacement generation
incomplete: [{'platform': 'facebook', 'error': \"BadRequestError: Error code: 400 -
{'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'model: String
should have at least 1 character'}...\"}]"}`.

Root cause: `growth-replace-rejected.yml` (and `growth-daily-cycle.yml`,
`growth-blog-seo.yml`) all set `env: CLAUDE_CONTENT_MODEL: ${{ vars.CLAUDE_CONTENT_MODEL }}`.
No repo-level variable `CLAUDE_CONTENT_MODEL` exists (`gh variable list` confirmed empty), so
GitHub Actions resolves the expression to `""` — but the `env:` key is still *set*, just to an
empty string, not omitted. `content_studio/generators/claude_social_generator.py` and
`claude_generator.py` both read it via `os.environ.get("CLAUDE_CONTENT_MODEL",
DEFAULT_CLAUDE_CONTENT_MODEL)`. `dict.get(key, default)` only falls back when the key is
**absent** — a key present with value `""` returns `""` unchanged. Every Claude call in CI was
therefore sent `model=""`, which Anthropic rejects with the 400 above. This runs on every
scheduled `daily-cycle`/`replace-rejected`/`blog-seo` invocation, so this was silently breaking
content generation broadly, not just the one workflow Github happened to notify about first.

Fix: both call sites changed from `.get("CLAUDE_CONTENT_MODEL", DEFAULT)` to
`os.environ.get("CLAUDE_CONTENT_MODEL") or DEFAULT_CLAUDE_CONTENT_MODEL` — `or` treats
both "key absent" and "key present but falsy" the same way. Added regression test
`test_content_model_falls_back_when_env_var_is_set_but_empty` in
`tests/test_claude_social_generator.py` (`monkeypatch.setenv("CLAUDE_CONTENT_MODEL", "")`,
asserts the fake Anthropic client received `DEFAULT_CLAUDE_CONTENT_MODEL`). Targeted suite
(`test_claude_social_generator.py`) 9/9 passed; the one unrelated failure seen in
`test_phase5_contract_refs.py` during verification is the already-documented pre-existing
stale-DNA-filename fixture bug, not caused by this change.

Committed `b351b19`, pushed directly to `origin/main` (no unrelated files staged — an
in-progress, uncommitted Gemini-vision WIP already sitting in the working tree at commit time
was stashed before the push and popped back afterward, untouched).
## Growth Agent — missing future slots after approval audit (2026-08-13)

- [x] Confirmed the 2026-08-10 weekly run created only 4 slots (10/08, 12/08, 14/08,
  15/08), so 21/08, 22/08 and 24/08 did not exist to approve.
- [x] Manually dispatched corrected weekly cycle `31695771922`; GitHub Actions completed
  successfully, including registry commit.
- [x] Verified remote registry/snapshot contain Facebook + Instagram rows for 21/08 (Friday),
  22/08 (Saturday) and 24/08 (Monday), all `PENDING_APPROVAL`.
- [x] Root cause recorded: approval cannot create a slot that was never generated; the corrected
  two-week horizon now creates the missing dates.

## VENHO GPU Identity Restoration v2.1 — GW-P0 closeout (2026-08-19)

GW-P0-T2 is closed PASS against the original v2.1 Golden-Master DoD. The authoritative
golden set contains exactly three fixed crop cases under
`tests/identity_restoration/golden/`. The regression harness compares restored-crop and
composite SHA-256 values exactly, enforces the serialized cropTransform and seed `42`,
requires `mutatedPixelCount=0`, verifies restored crop bytes differ from input, and checks
three frozen Face QC values within ±2.0. Regression is offline with zero network calls and
is reusable after the planned Phase 2 refactor steps.

The remaining GW-P0 commit-hash item was completed and recorded in
`docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`:

- `venho-ai-studio` HEAD: `f3cf924920812e6591f9c11b5e009fd36b610416`
- `venho-os` HEAD: `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3`

The next roadmap item was **Ghi kết quả test hiện tại (Python + OS)**; that baseline is now
completed and recorded below. Do not start GW-P2-T1 or later. Full-suite failures outside the
identity-restoration scope are not a GW-P0-T2 closure criterion.

## VENHO GPU Identity Restoration v2.1 — GW-P0 test baseline (2026-08-19)

Recorded the current test state exactly as executed, without remediation:

- `venho-ai-studio` commit `f3cf924920812e6591f9c11b5e009fd36b610416` —
  `PYTHONPATH=. /usr/bin/python3 -m pytest -q` — **951 passed, 70 failed, 0 skipped, 0 errors**.
  Existing failures cluster around the missing Lake View Room DNA fixture, subject-resolver/
  schema/overlay expectation mismatches, one Action Composite config expectation, and missing
  raw asset fixture(s).
- `venho-os` commit `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3` —
  `npm test -- --run` — **400 passed, 0 failed, 0 skipped, 0 errors** across 71 test files.

Evidence is recorded in `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`.
No production code, dependency, or configuration was changed. A2 SHA-256 was subsequently
pinned in `workflow_pins.yaml`; next roadmap task is **Đánh dấu v1.0 SUPERSEDED**.

## VENHO GPU Identity Restoration v2.1 — GW-P0 Nano Banana baseline (2026-08-19)

Recorded the strongest existing Nano Banana masked-edit baseline without rerunning generation:

- Run/case: `run-202608132052/variant-001`
- Provider/mode: Nano Banana 2 (`gemini-3.1-flash-image`) / `masked-edit`
- Face QC: **88.1 / revise**
- A2 authority: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png`
- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`
- Manifest: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/13-08-action-composite-v21-nano-crop/run-202608132052/variant-001/manifest.json`
- Output: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/13-08-action-composite-v21-nano-crop/run-202608132052/variant-001/image.png`
- Face report: `/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/data/projects/venho_hotel/validation/reports/face_linh_an_1d64fd2b6281_20260813-204931.json`
- Timestamp: `2026-08-13T13:47:18.610Z` → `2026-08-13T13:49:43.327Z`; prompt hash and protocol are preserved in the manifest; no seed was recorded.

This is comparison/fallback evidence only, not the production winner and not a new acceptance threshold. No new image was generated, no API cost was incurred, and no production code changed. Evidence is also recorded in `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`.

Next roadmap task: **Đánh dấu v1.0 SUPERSEDED**.

## VENHO GPU Identity Restoration v2.1 — GW-P0 v1.0 superseded (2026-08-19)

Marked `config/comfyui/face_restore_v1_api.json` with a clear `SUPERSEDED` status. The marker
names the current v2.x authority and states that the v2.1 patch overrides v2.0 wherever they
conflict. The workflow remains in place with its historical content preserved; archive/move is
deferred to the next roadmap task.

The v2.0 plan references `VENHO_LINH_AN_WINDOWS_COMFYUI_GPU_WORKER_ROADMAP_v1_0.md`, but that
markdown file is absent from the workspace. No historical content was fabricated, deleted, or
rewritten. No production code changed.

Next roadmap task: **Archive workflow cũ**.

## VENHO GPU Identity Restoration v2.1 — GW-P0 legacy workflow archived (2026-08-19)

Archived the superseded workflow non-destructively:

- Original: `config/comfyui/face_restore_v1_api.json`
- Archive: `workflows/_archive/face_restore_v1_api.json`
- SHA-256: `f7d04802135eb06db94e6b096b0dc269a644c3bebe90ec61f3855567dde32361`

Updated `workflow_pins.yaml`, the example config, and all Golden-Master lineage records to
point to the archive path. The workflow content and v1.0 relation remain preserved for audit;
it is not active/current authority. Reason: superseded by the current v2.x architecture and
the v2.1 patch, which overrides v2.0 where conflicting. Production behavior was not changed.

Next roadmap task: **ADR set**.

## VENHO GPU Identity Restoration v2.1 — GW-P0 ADR set and phase audit (2026-08-19)

Created exactly eight ADRs under `docs/identity-restoration/`, mapped to the locked v2.0
decisions: ADR-001(D1,D11), ADR-002(D2,D12), ADR-003(D3,D4), ADR-004(D5), ADR-005(D6,D7),
ADR-006(D8), ADR-007(D9), ADR-008(D10). No new architecture or ADR-GW-009 was created.

Offline Golden Master remains green (`python3 -m pytest -q tests/test_gw_p0_t2_golden.py` →
2 passed), with A2 authority, archive, baseline docs, and golden artifacts traceable.

The missing T1 evidence gap was closed by a read-only reconstruction at
`docs/identity-restoration/COUPLING_AUDIT_2026-08-18.md`, based on the current implementation,
roadmap notes, tests, and existing baseline artifacts. No production code or architecture was
changed.

Re-audit passed: T0/T1/T2, commit/test baselines, A2 pin, Nano Banana baseline, v1 supersession,
workflow archive, exactly eight ADRs, Golden Master offline regression (`2 passed`), one pipeline
definition, and no direct ComfyUI references in `venho-os/src` TypeScript sources.

GW-P0 is **CLOSED/PASS**. Next roadmap phase: **GW-P1 — Windows GPU Worker**. Do not start it
without an explicit next-phase task instruction.
## 2026-08-24 — GW-P4-T0 Controlled A2 Benchmark Freeze & Preflight

GW-P4 mở ở trạng thái **IN PROGRESS**; GW-P0..P3 giữ nguyên **CLOSED/PASS**.
Đã kiểm tra hai plan authority v2.0/v2.1, A2 pin, workflow pin, validator,
registration và crop/mask/pixel-lock contract. A2 authority là
`venho-social-content-agent/assets/face-plates/A2_Front_plate.png`, SHA-256
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
Remote workflow là `face_restore_win_sd15_ipadapter_v1`, SHA-256
`7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8`; params
đóng băng theo pin: denoise 0.35, steps 20, CFG 6, euler/normal; benchmark
seed 42 kế thừa Golden Master.

Tạo `docs/identity-restoration/BENCHMARK_PROTOCOL.md`. Kết quả fail-closed:
chưa có `benchmark_set.yaml`, benchmark runner, hoặc binding authoritative cho
B01–B10; chỉ thấy candidate lineage B04 là
`assets/action-composite-live/action_01_jogging.png`. Schema benchmark hiện
chỉ có contract rút gọn và thiếu các field v2.1 yêu cầu. Không generate ảnh,
không gọi Nano Banana/Face QC trả phí, không chạy GPU benchmark, không tune.
GW-P4-T0 = **FAIL/BLOCKED** cho tới khi bổ sung dataset authority và contract/
harness phù hợp bằng task riêng.
## 2026-08-24 — GW-P4-T0.1 Benchmark Contract + Manifest Closure

GW-P4-T0.1 **PASS**. Tạo authoritative
`contracts/identity_restoration/benchmark_set.yaml` với benchmarkVersion 2.1,
seed 42, Face QC samples 3, A2/workflow authority, bốn branch và B01–B10.
B01–B03/B05–B10 vẫn `MISSING`; B04 chỉ `CANDIDATE_NOT_FROZEN`, không promote.

Nâng `benchmark_row.schema.json` lên v2.1, yêu cầu canonical benchmark fields,
giữ `additionalProperties: false`, giữ legacy fields optional để đọc tương thích.
Thêm fixtures bốn branch + missing-required + unknown-property và validator thuần
`identity_restoration.application.benchmark_contract`; official readiness fail-closed
khi chưa đủ case `FROZEN`. Tests offline, không runner/API/GPU/Face QC paid.
GW-P4-T0 vẫn **FAIL/BLOCKED** vì chưa có runner/CLI và frozen source frames.

## 2026-08-24 — GW-P4-T0.2 Benchmark Runner / CLI

GW-P4-T0.2 **PASS**. Added the fail-closed
`identity_restoration.application.benchmark_runner` and
`venho-restore benchmark validate|plan|run` commands. `validate` distinguishes
structural contract validity from official readiness; `plan` emits 40
deterministic rows; `run` refuses before composition-root/executor creation
unless every B01–B10 case is `FROZEN`, with no bypass flag. Future execution
uses an injected branch executor and the existing restoration-port boundary;
no direct ComfyUI calls or second pipeline were added. Result rows are
schema-validated and failed attempts remain explicit in append-only run
artifacts.

Offline validation only: runner/CLI tests, identity-restoration tests,
compileall, and `git diff --check` are required; no image generation, network,
GPU, paid API, or live benchmark execution. GW-P4 remains IN PROGRESS and
GW-P4-T0 remains FAIL/BLOCKED pending frozen B01–B10 source frames and real
branch/evidence executors.

## 2026-08-24 — GW-P4-T0.3 B01–B10 Authoritative Dataset Freeze

GW-P4-T0.3 **FAIL/BLOCKED**. Repository and production-artifact lineage search
verified six real source frames without using Face QC for selection: B01
Close-up Front, B02 Half-body, B03 Full-body Standing, B04 Running Front 3/4,
B09 West Lake, and B10 Ven Ho Hotel Interior. Their paths, SHA-256 values,
dimensions, and source lineage are recorded in
`contracts/identity_restoration/benchmark_set.yaml` and
`docs/identity-restoration/BENCHMARK_DATASET_V2_1.md`.

Added fail-closed physical dataset validation for existence, decode integrity,
SHA-256, dimensions, exact B01–B10 IDs, and undocumented duplicate paths.
B05 Running Side, B06 Walking, B07 Sitting, and B08 Hair Motion remain
`MISSING`; no arbitrary or Face-QC-selected substitute was promoted.
`officialBenchmarkReady=false`. No benchmark execution, paid API, live Face QC,
generation, tuning, or architecture change occurred.

## 2026-08-24 — GW-P4-T0.4 Generate & Freeze Missing B05–B08 Sources

GW-P4-T0.4 **PASS**. Created exactly one accepted source frame for each missing
taxonomy: B05 Running Side, B06 Walking, B07 Sitting, and B08 Hair Motion.
Generation used the existing approved `venho-social-content-agent/generate_image.py`
pipeline with `gpt-image-2`, quality `high`, portrait `1024x1280`, and the
canonical A2 reference SHA-256
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.

The accepted output hashes are B05
`06f4b6b0b6ea47dee71a240065411899cb3fa2b84633dacddba4d232afce5492`, B06
`526190e3632d189d588dcdfda32f1d7930c449c8a6b2188961d7907ef7746d8e`, B07
`6a39787e5edf0d061d246d9af806ac82d7499429a104fd3f910708dc5718754e`, and B08
`e6303bb45121b6dd01f992d549d76668cf34b6b82828ffed87f3a65928c970c4`.
All are `1024x1280`, one attempt each, with no replacement. Prompts and exact
lineage are recorded in
`docs/identity-restoration/BENCHMARK_GENERATION_LINEAGE_V2_1.md` and the
authoritative YAML manifest.

Acceptance used taxonomy and technical validity only; no IdentityRestorer,
official benchmark, paid Face QC, or candidate ranking was run. The existing
pipeline did not expose deterministic generation seeds or provider request IDs;
both are explicitly unavailable rather than fabricated. Dataset readiness is
now true for all B01–B10, but GW-P4-T0 remains **FAIL/BLOCKED** pending physical
branch/evidence executors. GW-P4 remains **IN PROGRESS**.

## 2026-08-24 — GW-P4-T0.5 Physical Branch & Evidence Executor Readiness

GW-P4-T0.5 **FAIL/BLOCKED** and GW-P4-T0 remains **FAIL/BLOCKED**. Added the
zero-cost `venho-restore benchmark preflight` command and a fail-closed
`BenchmarkPreflight` capability boundary. The preflight checks all four branch
IDs, frozen dataset readiness, benchmark-row evidence properties, and the
remote workflow file/pin SHA (`7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8`).

Control is implemented as a no-provider `ControlBenchmarkExecutor`: it reads
the frozen base, verifies its SHA, references the same source as output, and
emits explicit output/hash/status/provider/request/run/backend/host evidence.
The existing comfyui-local and comfyui-remote classes remain only
`IdentityRestorerPort` adapters; no benchmark executor/evidence writer is
wired, and the current preflight environment has both ComfyUI flags disabled.
Remote health/output was not probed because no benchmark executor is present.
Nano Banana is not registered in this bounded context; the smallest required
future change is one adapter around the existing action-composite/Nano Banana
provider path, not a second pipeline.

`benchmark run` now gates on both `officialBenchmarkReady` and
`officialExecutionReady` before creating an official run directory. Schema
support was added for explicit branch evidence fields while retaining
`additionalProperties: false`. No full benchmark, Face QC sweep, paid call,
GPU/ComfyUI smoke, tuning, or promotion was performed.

## 2026-08-24 — GW-P4-T0.5.1 ComfyUI-Local Executor + Evidence Writer

GW-P4-T0.5.1 **PASS**. Added
`identity_restoration.application.benchmark_executor.ComfyUILocalBenchmarkExecutor`.
It wraps the existing `RestoreFaceCropUseCase`, which owns the registered
`IdentityRestorerPort` call, A2 verification, compositing, pixel preservation,
artifact persistence, and restoration ledger. The benchmark executor only
adapts one injected `RestoreCommand` factory and serializes evidence; it has no
ComfyUI HTTP imports and no independent crop/mask implementation.

The local executor validates the frozen base SHA, A2 SHA, seed 42, crop/mask
dimensions, output decode, output hashes, workflow lineage, and pixel-lock
evidence. It returns final composite and restored-crop paths/hashes, runtime,
workflow, backend/host, provider/request/run identifiers, and explicit nulls
where the local adapter does not expose GPU or provider request metadata.
Failure is raised to the benchmark runner for retained failed-row evidence.

Preflight now reports `control=READY`, `comfyui-local=READY`,
`comfyui-remote=NOT_READY`, `nano-banana-edit=NOT_READY`; global
`officialExecutionReady` remains false. No physical ComfyUI smoke, full
benchmark, Face QC, paid call, tuning, or promotion was performed. Remaining
blockers are exactly the remote executor and Nano Banana adapter.

## 2026-08-24 — GW-P4-T0.5.2 ComfyUI-Remote Executor + Windows Evidence

Implemented `ComfyUIRemoteBenchmarkExecutor` around the existing
`RestoreFaceCropUseCase` and `ComfyUIRemoteRestorer` port adapter. It enforces
the frozen remote workflow `face_restore_win_sd15_ipadapter_v1` SHA
`7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8`, seed 42,
remote params, A2 authority, identical crop/mask geometry, output hash,
byte-difference, and pixel-lock evidence. The benchmark layer has no
transport code. Remote adapter execution metadata and use-case worker-health
metadata are persisted through lineage when available; unavailable GPU/VRAM/
request fields remain null.

## 2026-08-24 — GW-P4-T0.5.2a Windows Physical Remote Smoke

T0.5.2a is **FAIL/BLOCKED**. The pre-smoke probe to
`http://127.0.0.1:8188/system_stats` returned connection refused from the
Mac/repository environment. No HARRY-ROG worker/tunnel was reachable; no
ComfyUI prompt was submitted, no inference was run, and no evidence bundle was
fabricated. The remaining prerequisite is one real NON_BENCHMARK B01 smoke
through `ComfyUIRemoteBenchmarkExecutor` with the frozen authority.

## 2026-08-24 — GW-P4-T0.5.2b HARRY-ROG ComfyUI Reachability

T0.5.2b is **FAIL/BLOCKED** from the Mac environment. `tailscale ping
harry-rog` succeeded, but Mac localhost `127.0.0.1:8188/system_stats` was
connection-refused, direct Tailscale `100.71.167.98:8188/system_stats` timed
out, and `tailscale serve status` reported no Serve config on Mac. No Windows
process was started or modified, no `/prompt` was submitted, and no evidence
was fabricated. This is insufficient to classify a GW-P1 runtime regression;
Windows-local process/port/log evidence is still required.

Remote readiness is smoke-gated. No physical HARRY-ROG run was possible from
the Mac/repo environment, so T0.5.2 is **FAIL/BLOCKED** pending one real
non-benchmark Windows smoke evidence bundle. `comfyui-remote` and
`nano-banana-edit` remain NOT_READY; global official execution remains false.

## 2026-08-24 — GW-P4-T0.5.2a-RERUN B01 Physical Remote Smoke

Precheck reached HARRY-ROG: remote `/system_stats` HTTP 200, ComfyUI 0.33.0,
frozen localhost argv, and GTX 1660 SUPER. B01 SHA
`e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9`, A2 SHA,
and workflow SHA all matched authority. No prompt was submitted because the
existing remote executor requires a prior PASS smoke evidence file before
running the first smoke, and current free VRAM was about 1,988 MiB versus the
frozen 4,200 MiB health threshold. This is **FAIL/BLOCKED**, with no fabricated
evidence and no code/threshold/workflow changes.

## 2026-08-24 — GW-P4-T0.5.2d First-Smoke Circular Readiness Gate

T0.5.2d **PASS**. Added `benchmark smoke` as a dedicated
`NON_BENCHMARK/PREFLIGHT` bootstrap path and
`ComfyUIRemoteBenchmarkExecutor.execute_bootstrap_smoke()`. It permits the
first B01 smoke without an existing smoke file, while retaining dataset,
authority, workflow, remote registration, and live worker-health/VRAM gates.
It writes a smoke manifest whose top-level authority/status fields can later be
validated by the official executor.

`benchmark run` and normal `execute()` remain fail-closed until the smoke
manifest is PASS; no `--force`, direct HTTP path, benchmark, Face QC, or
physical smoke was run. Remote is not marked READY from unit tests.

## 2026-08-24 — GW-P4-T0.5.2f Canonical B01 Smoke Request Builder

T0.5.2f **PASS**. Added `build_benchmark_restore_command()` and made
`benchmark smoke --request` optional. Canonical B01 requests derive geometry
and both mask spaces through the existing production
`InsightFaceGeometryExtractor`, `crop_for_identity()`, and
`hierarchical_face_masks()` implementations. Authority validation covers the
frozen B01 source, A2 SHA, remote workflow ID/params, seed 42, crop/mask/base
dimensions, and transform bounds. Optional request overrides must match the
canonical production-derived transform. Offline identity-restoration tests:
105 passed; focused builder/remote/contract tests: 27 passed; compileall and
git diff --check passed. No network, ComfyUI, benchmark, Face QC, or physical
smoke execution occurred. `comfyui-remote` remains NOT_READY.

## 2026-08-24 — GW-P4-T0.5.2g Mac Geometry Runtime Dependency Closure

T0.5.2g **FAIL/BLOCKED at model provenance gate**. The extractor is pinned to
`buffalo_l` and CPU ONNX Runtime. Local files exist at
`~/.insightface/models/buffalo_l`, but there is no `MODEL.LICENSE`, signed
manifest, artifact provenance record, or approved commercial license in the
workspace. No install, model initialization, download, ComfyUI call, or Face
QC was performed. B01 SHA/dimensions and canonical A2 SHA were verified.
Zero-cost checks: focused benchmark/remote/preflight/contract tests `33
passed`; compileall and `git diff --check` passed. The smoke CLI help confirms
`--request` is optional. InsightFace/onnxruntime remain unavailable in the
Mac `.venv`; geometry and physical smoke remain blocked fail-closed.

## 2026-08-24 — GW-P4-T0.5.2h YuNet Commercial Geometry Compatibility Gate

T0.5.2h **PASS**. The existing contract consumes exactly one bbox and five
ordered landmarks; existing PnP, crop, mask, and request schemas remain
unchanged. Added explicit `YuNetGeometryExtractor` and backend selection via
`IDR_GEOMETRY_BACKEND=yunet`; InsightFace remains available/default and there
is no silent fallback. The official OpenCV Zoo `face_detection_yunet_2023mar`
artifact is retained at `models/geometry/yunet/`, SHA-256
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`, with
MIT `LICENSE` and pinned `PROVENANCE.json`. Real B01 offline detection found
one face at confidence `0.9136796594` with five landmarks; production crop and
hierarchical masks produced a `830x1003` crop, matching crop-local mask, and
`1024x1024` full-canvas mask. OpenCV headless was installed only in the
project `.venv`; no InsightFace/buffalo_l package/model was installed.
Focused tests: `37 passed`; full `tests/identity_restoration`: `106 passed`;
compileall and `git diff --check` passed. No ComfyUI, restoration, Face QC, or
official benchmark ran; physical B01 smoke remains the next gated action.

## 2026-08-24 — GW-P4-T0.5.2i Remote Workflow Output Geometry Diagnosis

T0.5.2i **PASS**. The frozen workflow hash
`7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8` contains
node `16 ImagePadForOutpaint` (`right=1`, `bottom=5`), then VAE encode/sample/
decode, then node `19 ImageCrop` with literal `width=687`, `height=659`,
`x=0`, `y=0`; node `14 SaveImage` writes node `19`. This is the exact
dimension-changing point. The available persisted prompt/history is
`0ce26c1e-b28c-4cda-8dd2-aa07ca8be37e` at
`staging/gw-p3/mac-final-20260824/remote_history_response.json`; it records the
same fixed crop/output and is not the newer `830x1003` attempt, whose physical
prompt/history is not present in this repository. Remote input binding and
output selection were verified; no adapter resize exists. Classification:
`WORKFLOW_FIXED_SIZE_DESIGN_INCOMPATIBLE_WITH_PORT`. Added diagnosis tests
(`13 passed`); no workflow, adapter, benchmark, Face QC, or ComfyUI changes.

## 2026-08-24 — GW-P4-T0.5.2j Versioned Dimension-Preserving Workflow

T0.5.2j **FAIL/BLOCKED pending Windows deployment SHA verification**. Created
`identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json`
with local SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`.
The active v1 file/SHA and benchmark authority were not changed. v2 keeps the
same SD1.5/IPAdapter restoration graph, replaces fixed padding with runtime
`padRight=(8-W%8)%8`, `padBottom=(8-H%8)%8`, and injects final crop W/H from
the request as `finalCropWidth`/`finalCropHeight`. The same values are bound to image and mask padding nodes; the
remote adapter has no resize path and validates returned dimensions fail-closed.
Candidate pin and registry entry were added. Focused v2/binder/remote tests:
`22 passed`; compileall and `git diff --check` passed. Physical HARRY-ROG copy
and SHA equality cannot be verified here, so benchmark_set.yaml and active
benchmark constants remain on v1; no ComfyUI, Face QC, or benchmark ran.

## 2026-08-24 — GW-P4-T0.5.2k Remote Smoke Evidence Acceptance

Accepted the persisted physical `NON_BENCHMARK/PREFLIGHT` smoke manifest:
`evidence/gw-p4-t0-5-2d-20260824T134922Z-5325a724/smoke_manifest.json`.
It records `status=PASS`, `executorStatus=COMPLETED`, prompt ID
`c0710730-28d1-4af5-b642-dbc46d2b4a28`, host/GPU evidence for HARRY-ROG,
`mock_used=false`, `local_fallback=false`, and `silent_fallback=false`.

The active remote authority is `face_restore_win_sd15_ipadapter_v2`, SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`.
B01 SHA, canonical A2 SHA
`1e0c9720087d4bab4b1ab5d65d31827aba99ccf4c696c1a72570ed4114dca2c5d`, and
workflow SHA match. The restored crop is `830x1003`; the production-derived
input crop bytes differ from restored bytes, and pixel-lock is `PASS`.

Status updates: `GW-P4-T0.5.2a=PASS`, `GW-P4-T0.5.2=PASS`,
`comfyui-remote=READY`. Preflight with the persisted smoke evidence reports
`control=READY`, `comfyui-local=READY`, `comfyui-remote=READY`,
`nano-banana-edit=NOT_READY`, `officialBenchmarkReady=true`, and
`officialExecutionReady=false`. Remaining blocker: no Nano Banana benchmark
executor. No rerun, Face QC, benchmark, tuning, or architecture change.

## 2026-08-24 — GW-P4-T0.5.3 Nano Banana-Edit Benchmark Executor

T0.5.3 **FAIL/BLOCKED**. Added a fail-closed
`NanoBananaEditBenchmarkExecutor` wrapper and explicit `NanoBananaEditPort`
seam. It delegates generation to the existing production path, validates
base/A2 authority and `masked_edit`, records provider/model/request/run IDs,
truthful seed support, retry/runtime, lineage, and explicit
`mock_used/local_fallback/silent_fallback` flags. It persists append-only
success/failure evidence and never creates a second ActionCompositePipeline or
vendor client.

The existing Nano Banana path is in sibling Venho OS:
`GenerateStudioImageUseCase` → `GeminiImageProvider`, using
`prepareMaskedFaceEdit()` and `compositeMaskedFaceCrop()`. This Python repo has
no registered callable adapter to that path, so preflight remains fail-closed:
control/local/remote READY, nano-banana-edit NOT_READY,
officialBenchmarkReady=true, officialExecutionReady=false. No paid provider
call, Face QC, benchmark, or tuning was performed.

## 2026-08-24 — GW-P4-T0.5.3b One Physical Nano Banana-Edit Smoke

T0.5.3b **FAIL/BLOCKED before provider execution**. B01 authority matched
`e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9`; canonical
A2 matched
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
Provider configuration was present without exposing secrets
(`IMAGE_GENERATION_GOOGLE_ENABLED=true`, Gemini credential resolvable from
the existing social-agent dotenv path), with model
`gemini-3.1-flash-image`.

The frozen B01 artifact has no authoritative mask or edit-region/crop lineage.
The existing production `masked_edit` path requires base + mask + A2, so the
smoke could not be built without fabricating or substituting geometry. No
provider call, output, or fake evidence was produced; paid call count: `0`.

## 2026-08-24 — GW-P4-T0.5.3a Register Nano Banana Benchmark Adapter

T0.5.3a **PASS**. Added
`NanoBananaEditAdapter` and optional composition-root registration via
`build_nano_banana_benchmark_executor()`. Registration is enabled only when
the existing provider capability, `IDR_NANO_BANANA_ENABLED`, injected
production path, canonical A2, request factory, and evidence root are all
available. Missing configuration remains NOT_READY.

The adapter delegates to the already-composed Venho OS path
`GenerateStudioImageUseCase` → `GeminiImageProvider` and does not create a
second client/pipeline, tune prompts, retry/select candidates, or fallback.
Offline verification passed: `137 passed`, compileall, and `git diff --check`.
T0.5.3 remains FAIL/BLOCKED pending exactly one allowed NON_BENCHMARK physical
Nano Banana smoke. Paid calls: 0.

## 2026-08-24 — GW-P4-T0.5.3c B01 Nano Banana Mask Lineage Freeze

T0.5.3c **PASS for offline evidence/lineage preparation only**. Verified the
locked B01 SHA and canonical A2 SHA, then ran the existing production YuNet
geometry path to create the authorized B01 mask artifacts. The persisted
authority records one face, crop transform `(119, 0, 949, 1003)`, crop-local
mask `830x1003`, full-canvas mask `1024x1024`, and the full provenance chain:
`YuNetGeometryExtractor -> crop_for_identity -> hierarchical_face_masks`.

The real local YuNet model SHA is
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`. The
implementation lock was corrected to the supplied authoritative 64-character
value; existing production code and the file itself agree on the same SHA. No
model or image source bytes were changed.

`build_frozen_b01_nano_request()` now binds the full-canvas mask as the Nano
masked-edit input while retaining crop-local mask lineage. The Nano benchmark
executor validates this authority and fails closed before provider execution
when it is absent or inconsistent. Identity-restoration tests: `141 passed`.
No Nano Banana call, Face QC, benchmark, or network call was made. The next
required step remains exactly one physical NON_BENCHMARK/PREFLIGHT Nano Banana
smoke; T0.5.3 remains blocked until that evidence exists.
## 2026-08-24 — GW-P4-T0.5.3d Nano Banana Physical Smoke CLI

T0.5.3d **PASS for offline CLI wiring only**. Extended `venho-restore
benchmark smoke` to accept `--branch nano-banana-edit` for B01. The command
loads the frozen B01 geometry authority, builds the request through
`build_frozen_b01_nano_request()`, validates B01/A2/mask lineage before any
provider call, then dispatches only through the existing
`NanoBananaEditBenchmarkExecutor` -> `NanoBananaEditAdapter` composition seam.
The result is explicitly `NON_BENCHMARK` / `PREFLIGHT`; the CLI does not
create an official benchmark run, aggregate metrics, or invoke Face QC.

Offline Nano CLI/executor/geometry/registration tests: `15 passed`; full
identity-restoration suite: `134 passed`; compileall and `git diff --check`
passed. No network, provider, paid call, benchmark, or Face QC was executed.
The existing production Nano port remains required at the composition seam and
continues to fail closed when not injected; `nano-banana-edit` is not READY,
and T0.5.3 remains blocked pending one physical B01 smoke.

## 2026-08-24 — GW-P4-T1 Official Branch Correction and Execution Blocker

Corrected the official benchmark decision contract from the earlier four-branch
model to the authoritative three branches: `control`, `nano-banana-edit`, and
`comfyui-remote`. `comfyui-local` remains in the architecture, registry, and
capability/preflight surface, but is excluded from official decision rows.
`EXPECTED_BRANCHES`, `benchmark_set.yaml`, the CLI plan text, and the runner
regression expectations now produce exactly 30 rows. The row schema continues
to accept local adapter evidence for compatibility fixtures.

Static validation and plan pass, but the official CLI run remains blocked
before run-directory creation: `BenchmarkRunner` is instantiated without a
composite executor, per-case geometry/request factories, and existing
Validator Studio evidence wiring. No paid Nano calls, GPU jobs, validator
calls, official outputs, or fabricated rows were made. GW-P4-T1 is BLOCKED;
GW-P4 remains IN PROGRESS. Report:
`docs/identity-restoration/GW_P4_CONTROLLED_A2_BENCHMARK_REPORT.md`.

## 2026-08-24 — GW-P4-T0.5.3 Physical Nano Banana Readiness Closure

Completed exactly one real NON_BENCHMARK/PREFLIGHT B01 provider smoke through
the existing chain `NanoBananaEditBenchmarkExecutor -> NanoBananaEditAdapter ->
VenHo OS GenerateStudioImageUseCase -> GeminiImageProvider`. The internal
transport bridge only connects the existing use-case composition; it creates
no Gemini client, provider, fallback, or second pipeline.

Physical evidence is at
`evidence/gw-p4-t0-5-3b-20260824T142500Z/preflight-b01-nano-smoke-20260824T142530242068Z/b01-nano-smoke-1/`:
provider `nano-banana-2`, model `gemini-3.1-flash-image`, one paid call,
retry `0`, seed metadata `42` with `seedSupported=false`, B01/A2/YuNet/mask
authorities exact, output `1024x1024` PNG SHA
`d5ed883ef12166bd9da313252854e832eb74016528d754bd5d1c37f6669af17c`,
`executorStatus=COMPLETED`, and all mock/fallback flags false. Face QC and
official benchmark execution were not run.

Preflight now accepts only self-verifying persisted physical smoke evidence.
Final matrix is control/local/remote/nano all READY;
`officialBenchmarkReady=true`, `officialExecutionReady=true`. Regression suite:
`150 passed`, TypeScript typecheck passed, compileall and `git diff --check`
passed. GW-P4-T0.5.3, T0.5, and T0 are PASS/CLOSED; GW-P4-T1 is not started.

## 2026-08-24 — GW-P4-T1 Orchestration Implementation

Internal T1 wiring is implemented in `benchmark_orchestration.py` and the
infrastructure composition root: `OfficialBenchmarkCompositeExecutor`
dispatches exactly `control`, `nano-banana-edit`, and `comfyui-remote`; the
case context derives/persists YuNet geometry and both mask spaces for B01–B10;
the existing Validator Studio face/image entry points are wrapped with a
SHA/configuration cache at `samples=3`; and the runner now creates official
artifact directories, writes `summary.json`, and computes the Phase-4 quality
decision.

Focused orchestration tests pass. Identity-restoration plus relevant
action-composite regression tests pass (`166 passed`); compileall and
`git diff --check` pass. The official CLI command was attempted after wiring
and fails before run creation because the existing VenHo OS Nano endpoint at
`127.0.0.1:3000` is connection-refused. This is an external runtime blocker,
not an internal executor/factory/validator implementation blocker. No
official rows, validator sweep, GPU job, or additional paid call was created.

## 2026-08-24 — GW-P4-T1 Nano Transport Recovery and Remote Gate

Root cause proven: `127.0.0.1:3000` is the existing Venho OS Next.js local
service (`npm run dev`), not a new provider proxy. Its existing route is
`/api/v1/identity-restoration/nano-banana-smoke`, composing
`GenerateStudioImageUseCase -> GeminiImageProvider`. The service was started
using the canonical script; zero-cost GET returned ready/configured,
provider `nano-banana-2`, model `gemini-3.1-flash-image`, no mock/fallback.

The first official attempt (`benchmark-20260824T150014Z-94c8cb21`) created 30
terminal failures before valid decision evidence: control lacked the existing
production dotenv credential in the Python process, Nano received a relative
A2 path rejected by the Venho OS trusted-root guard, and remote health was
offline. Internal fixes: load credentials using the existing production dotenv
search order; resolve canonical A2 to an absolute path; preserve Nano
`providerConfigured`/fallback flags; and make composite remote capabilities
probe WorkerHealth before official execution. No Nano provider call occurred
in that invalid attempt.

Corrected zero-cost composition reports Nano READY and remote `OFFLINE`.
HARRY-ROG Tailscale HTTPS health access is currently unreachable. The runner
therefore refuses a new official run before paid rows. T1 remains BLOCKED only
by this external worker/runtime dependency; do not classify the retained first
attempt as QUALITY FAIL.

## 2026-08-25 — GW-P4-T1 corrected attempt and external health gate

The recovered Venho OS Nano route was corrected to validate the source/mask/crop
authority supplied by each B01–B10 case instead of hard-coded B01 hashes. The
runner also flushes each JSONL row after writing. Python transport,
orchestration, contract, and infrastructure regressions passed: 80 tests;
compileall passed.

Corrected run `benchmark-20260825T015837Z-7d0e4f0d` is retained as invalid
infrastructure evidence: B01 Nano completed through the real provider with no
fallback, B02–B10 failed on the old B01-only route guard, and persistence was
incomplete before the flush fix. It is not a quality decision. A subsequent
official invocation was correctly refused before run creation because
HARRY-ROG health is `DEGRADED`: `/system_stats` is reachable, but free VRAM is
approximately 2.69 GiB, below the existing 4200 MB healthy threshold. Do not
lower the threshold or bypass the gate; resume the official 30-row run only
when the worker is HEALTHY.

## 2026-08-25 — GW-P4-T1 official run after HARRY-ROG VRAM recovery

Implemented the smallest pre-case remote hygiene policy in the existing
ComfyUI path: probe health; when DEGRADED only because free VRAM is below
4200 MB, POST `/free` with `unload_models=true, free_memory=true`, invalidate
the cached health result, re-probe, and execute only when HEALTHY. The
threshold remains 4200 MB, concurrency remains 1, and no prompt is submitted
when recovery fails. Focused tests including recovery policy: 48 passed;
compileall and diff check passed.

The approved `/free` call recovered HARRY-ROG from approximately 2.69 GiB to
5067 MB free. New official run
`benchmark-20260825T021915Z-157c9b14` completed all 30 terminal rows: 10
completed and 20 failed. Branch completed-row stats: control 7 rows,
median 93.85; Nano 0 rows; remote 3 rows, median 91.85. Treatment median
clears 90, but hard gates fail due incomplete execution/validator evidence,
regional/anatomy metrics, pixel preservation, and lineage. Decision:
`QUALITY_FAIL`. Do not rerun or tune under this task; prior invalid run
`benchmark-20260825T015837Z-7d0e4f0d` remains preserved and excluded.

## 2026-08-25 — GW-P4-T1 validity audit and recovery run

The recorded decision for `benchmark-20260825T021915Z-157c9b14` was audited
row-by-row before acceptance. The immutable run proved Nano provider execution
for B01–B10 with 10 output artifacts. Five Nano rows failed only because the
local composite treated `pixelPreservationResult=UNKNOWN` as failure before
offline mask comparison; five more had Validator Studio JSON failures. Remote
produced physical outputs for B01/B03/B05/B07/B09; B02/B04/B06/B08/B10 were
blocked by the frozen VRAM gate. The historical remote median 91.85 is exactly
B05=88.00, B07=92.28, B09=91.85, N=3; it is a partial population and cannot
support a final quality decision. The audited run was not modified.

Internal fixes: Nano UNKNOWN pixel evidence is recomputed from frozen
base/mask/output bytes; `BenchmarkRunner` records explicit classifications
(`VALID_QUALITY_PASS`, `VALID_QUALITY_FAIL`, `INFRA_EXECUTION_FAIL`,
`VALIDATOR_FAIL`, `EVIDENCE_PIPELINE_FAIL`, `AUTHORITY_FAIL`), reports valid
QC N, and returns `INELIGIBLE` when any official branch lacks ten valid
comparable rows. Explicit prior-run artifact reuse was added for Nano and
remote evidence; verified output hashes skip provider recall.

New run `benchmark-20260825T030340Z-df1d875a` used the frozen 30-row plan and
completed all rows: 18 completed, 12 failed. Nano reused all ten prior
provider artifacts with zero new Nano calls; three remote rows reused verified
prior evidence. Final counts: `EVIDENCE_PIPELINE_FAIL=18`,
`VALIDATOR_FAIL=8`, `INFRA_EXECUTION_FAIL=4`, valid quality rows 0/30,
`decisionEligible=false`, `decision=INELIGIBLE`. Remaining external block:
malformed Validator Studio responses and HARRY-ROG remaining DEGRADED below
4200 MB after the frozen single `/free` recovery attempt. GW-P4-T1 is
EXTERNAL BLOCKED / INELIGIBLE; GW-P4 remains IN PROGRESS. No quality tuning,
retry, fallback, mock, or best-of-N.

## 2026-08-25 — GW-P4-T1 Run 3 validity recovery execution

Implemented and verified branch-specific evidence classification, SHA/config/
samples-aware Validator cache migration, explicit Nano/Remote artifact reuse
lineage, and restoration-ledger rehydration for outputs persisted before a
Validator failure. Focused benchmark tests: 34 passed; compileall passed.

Run `benchmark-20260825T033150Z-aea9d71a` is the new immutable 30-row recovery
run: `21 completed / 9 failed`, classification counts
`EVIDENCE_PIPELINE_FAIL=21`, `VALIDATOR_FAIL=5`, `INFRA_EXECUTION_FAIL=4`.
Nano provider calls were 0. Six Remote outputs were reused; four missing
Remote cases failed closed after HARRY-ROG returned OFFLINE. Five Validator
responses remained malformed JSON.

The 21 evidence failures are concrete missing regional evidence: current
Validator Studio outputs expose Face QC/identity/eyes/global only, while the
benchmark requires authoritative geometry/anatomy/outfit/environment evidence.
The implementation keeps those values null and fail-closed; no quality score
was fabricated. Run 3 has valid quality rows 0/30 and no decision median.
Run 1 and Run 2 remain immutable. GW-P4-T1 remains EXTERNAL BLOCKED /
DECISION INELIGIBLE; GW-P4 remains IN PROGRESS.

## 2026-08-25 — GW-P4-T1 Run 4 and validity-recovery hardening

Traced the single production Regional authority:
`ActionCompositePipeline -> RegionalScoreGateway -> RegionalGate`. Added a
benchmark adapter that rehydrates only a complete persisted `regional_scores`
Gateway envelope. It does not infer anatomy/outfit/environment from
face/image scores, intent metadata, or pixel preservation. No complete
Regional envelope exists in Runs 1–3, so those rows remain fail-closed and no
thresholds changed.

Hardened Validator Studio response handling: the JSON normalizer now handles
fenced/wrapped JSON with string-aware balancing and rejects empty, truncated,
malformed, or schema-invalid content. Provider raw response text is exposed
before parsing; face/image validators persist raw text, sample index, parse
status, parsed evidence, and parse errors when the benchmark sink is
configured. Historical Run 3 malformed responses have no raw payload and thus
cannot be safely reparsed. Run 4's three Nano Validator calls failed with
`429 RESOURCE_EXHAUSTED` before a raw response existed.

Fixed reuse preparation so Nano scans immutable provider evidence even when a
completed provider artifact was followed by a downstream Validator failure;
Run 4 made zero new Nano calls and recovered the full 10/10 provider artifact
inventory. Remote reuse now scans all immutable Run 1–3 ledger records rather
than only the selected reuse run. Run 4 itself remains immutable.

Tailscale ping to `harry-rog` succeeded at 1 ms, but the peer's ComfyUI
`/system_stats` endpoint timed out over both hostname and IP. Classification:
`COMFYUI_PROCESS_DOWN`; no startup, port exposure, or VRAM-threshold change
was attempted.

Run 4: `benchmark-20260825T041020Z-0c7002c0`, 30/30 terminal, 21 completed,
9 failed, `EVIDENCE_PIPELINE_FAIL=21`, `VALIDATOR_FAIL=3`,
`INFRA_EXECUTION_FAIL=6`, valid quality rows 0/30, decision INELIGIBLE. No
treatment median or final quality decision was asserted. GW-P4-T1 remains
EXTERNAL BLOCKED / DECISION INELIGIBLE; GW-P4 remains IN PROGRESS; GW-P5 was
not started.

Verification: identity-restoration 146 passed; Action Composite/regional 53
passed; structured-response recovery tests passed; compileall and git
diff-check passed.

## 2026-08-25 — GW-P4-T1 Run 5 and validity-dimension correction

Run `benchmark-20260825T042453Z-b86d8854` is immutable and contains 30/30
terminal rows (`21 completed / 9 failed`). The runner now separates
`decisionValidity` from `qualityGatePass`: complete evidence with low Face QC,
Regional FAIL, or Pixel FAIL remains a valid observation; missing/corrupt
output, QC, Regional authority, pixel evidence, or lineage is invalid.
Control has no provider/workflow/GPU/restored-crop requirement; Nano has no
ComfyUI/workflow/GPU requirement; Remote keeps its pinned workflow/crop/mask
contract.

Run 5 remains `INELIGIBLE`: Control `0/10` decision-valid despite 10/10
completed; Nano `0/10` despite 7/10 completed and 10/10 reused output
artifacts; Remote `0/10` with 4 completed rows, 4 Validator failures, and 2
infra failures. The completed rows lack a complete authoritative
`RegionalScoreGateway` envelope. Face/image QC and intent/pixel metadata are
not converted into anatomy/outfit/environment scores. Nano made zero new
provider calls; three Validator failures were `429 RESOURCE_EXHAUSTED`.

HARRY-ROG is reachable through Tailscale and HTTPS `/system_stats` is healthy
when free VRAM is about 5067 MiB, with the pinned GTX 1660 SUPER and unchanged
4200 MiB threshold. Run 5 produced only two new Remote GPU outputs (B02/B08);
B03/B06 were reused and B04/B10 were blocked by the normal VRAM gate. No
fallback/mock/tuning/public exposure occurred. Since Control and Nano are not
10/10 decision-valid, the task's condition for a genuine `EXTERNAL_BLOCKED`
final status is not met; no quality decision or median is asserted. GW-P4 is
still IN PROGRESS; GW-P5 was not started.

## 2026-08-25 — GW-P4-T1 Regional authority resolution / R3 alignment

The authoritative trace is `ActionCompositePipeline ->
RegionalScoreGateway -> RegionalGate`. `RegionalScoreGateway.build()` accepts
only explicit face/image, geometry, scene-candidate, and preservation evidence;
`replay()` persists the resulting `scores/sources/provenance`. `RegionalGate`
is the production PASS/FAIL evaluator. The roadmap's GW-P4 acceptance wording
requires a healthy Regional/pixel gate, and the Action Composite plan defines
anatomy/outfit/environment as PASS/FAIL checks. The benchmark's unconditional
requirement for seven numeric Regional fields was therefore **R3 —
CONTRACT_OVERREACH**.

Implemented the minimum alignment: `regionalGateEvidence` is a schema-supported
authority-bound envelope. A complete Regional gate PASS or FAIL is
decision-valid; missing, malformed, or fake authority remains invalid. Numeric
Gateway envelopes remain compatible. No second Regional implementation was
created and no score was inferred from Face QC, geometry, pixel preservation,
intent metadata, or averages.

Offline scan of Runs 1–5 found zero benchmark gate envelopes and zero complete
production Regional manifests attached to benchmark artifacts. Thus no
Control/Nano/Remote decision-valid rows were recoverable and Run 6 was not
created. Status remains GW-P4-T1 INELIGIBLE, GW-P4 IN PROGRESS, with no
PASS/QUALITY_FAIL/genuine EXTERNAL_BLOCKED decision and no GW-P5.

Verification: focused 48 passed; Action Composite/regional 63 passed;
identity-restoration 152 passed; full suite 1116 passed and 76 unrelated
environment/fixture failures; compileall and diff-check passed.

## 2026-08-25 — GW-P4-T1 Regional evidence materialization and Remote completion

Implemented `BenchmarkRegionalEvidenceAdapter` in
`identity_restoration/application/benchmark_orchestration.py`. It is a thin
benchmark boundary over the existing production chain
`RegionalScoreGateway -> RegionalGate`; it does not implement a second scorer,
fabricate numeric values, or mutate Runs 1–5. It combines persisted
three-sample Validator Studio reports, frozen YuNet expected geometry, fresh
production geometry observation, and the existing
`StagePreservationEvidenceAdapter`, then persists immutable evidence under
`artifacts/identity-restoration/benchmarks/regional-evidence/`.

Materialization run: `materialized-20260825T054205Z`.

- Control: 10/10 Regional evidence and 10/10 decision-valid; 2 Regional PASS, 8 valid Regional FAIL quality observations.
- Nano: 7/10 evidence and decision-valid; B02/B04/B05 lack matching Validator cache by output SHA. Nano provider calls remain 0.
- Remote: reusable output inventory now includes B01/B02/B03/B05/B06/B07/B08/B09. Only missing B04/B10 were executed through the existing remote executor, with workflow SHA pinned and VRAM about 5065 MiB. Validator-backed Regional evidence exists for B01/B05/B07/B09 only, so Remote is 4/10 decision-valid.

Validator recovery probe for Nano B02 returned the external
`429 RESOURCE_EXHAUSTED` / prepayment credits depleted error. No repeated paid
call or fabricated evidence was used. Dry-run with the same runner validity
logic is Control `10/10`, Nano `7/10`, Remote `4/10`; Run 6 was not created.
The task's genuine EXTERNAL_BLOCKED rule is not satisfied because Control and
Nano are not both 10/10. Status remains T1 **INELIGIBLE**, P4 **IN PROGRESS**,
P5 not started.

Verification: identity-restoration 153 passed; Action Composite/regional 77
passed; full suite 1117 passed / 76 unrelated pre-existing failures;
compileall and diff-check passed.

## 2026-08-25 — GW-P4-T1 Validator credit-recovery resume preflight

The smallest legitimate post-recovery readiness check ran through the existing
`BenchmarkValidatorAdapter` against the frozen Nano B01 artifact using the
unchanged Gemini Validator identity
`validator-studio-face-image-v1:gemini:rubric=07F:samples=3`. The first live
request still returned `429 RESOURCE_EXHAUSTED` with the provider message
`Your prepayment credits are depleted.` No raw response or score existed to
persist; no repeated paid call was issued. The immutable check record is
`artifacts/identity-restoration/benchmarks/validator-preflight-20260825T055001Z/result.json`.

No Nano generation, Remote GPU job, or Run 6 was created. Existing recovery
truth remains Control `10/10`, Nano `7/10`, Remote `4/10` decision-valid.
Status is `GW-P4-T1 = EXTERNAL_BLOCKED / INELIGIBLE`, `GW-P4 = IN PROGRESS`,
and `GW-P5 = NOT STARTED`; provider credits/quota still require human recovery.

## 2026-08-25 — GW-P4-T1 resume after Validator READY

Validator readiness was confirmed with unchanged `gemini`,
`gemini-3.5-flash`, `samples=3`, `mock=false`, and `fallback=false`. Runs 1–5
remain immutable. The reuse index now includes all Remote B01–B10; B04/B10
reuse the already-completed recovery artifacts under
`recovery-remote-20260825TB04` and `recovery-remote-20260825TB10`. No Nano
generation and no Remote GPU job occurred during this recovery.

Production Regional materialization reached Control 10/10, Nano 8/10, and
Remote 8/10 decision-valid. Historical Validator evidence covered 21 branch
rows; five new complete three-sample evaluations were added (Nano B05 and
Remote B02/B03/B04/B10). Nano B02/B04 and Remote B06/B08 remain unvalidated
after controlled recovery attempts: Gemini returned truncated JSON. Raw
responses were persisted before parse and rejected fail-closed.

Pre-run-6 gate is false at 10/10, 8/10, 8/10. Run 6 was not created. Final
state: GW-P4-T1 EXTERNAL_BLOCKED/INELIGIBLE, GW-P4 IN PROGRESS, GW-P5 NOT
STARTED. Verification: focused identity-restoration/reuse 57 passed, Action
Composite/regional 97 passed, identity-restoration 153 passed, full suite
1117 passed / 76 pre-existing failures, compileall and diff check passed.
## 2026-08-25 — GW-P4-T1 paid-call guardrails and missing Validator recovery

Installed a single fail-closed `PaidCallGuard` at the existing Gemini vision
transport. Pytest processes are blocked before SDK transport; production live
calls require `VALIDATOR_LIVE_ENABLED=true`; the recovery ledger enforces a
maximum of 12 new sample calls and records sanitized intent/result, model,
sample, token, finish-reason, and error metadata. No provider/model/rubric,
threshold, or thinking configuration changed.

The four-target historical audit found complete face samples for Nano B02/B04
and Remote B06/B08. Only image samples missing after raw/cache recovery were
eligible for live calls: Nano B02 3, Nano B04 3, Remote B06 3, Remote B08 1.
Eleven new transport attempts were recorded: ten parsed successes and one
initial `MAX_TOKENS` malformed response, which was retried once under the
invalid-schema rule. Raw responses were persisted before parse; no quality
retry occurred. No Nano generation or Remote GPU job was run.

The existing structured Validator DTO schemas are now passed as Gemini JSON
response schemas; the output ceiling is 8192 to accommodate unchanged model
thinking behavior without requesting narrative output. The four target caches
now contain 3/3 face and 3/3 image samples. Regional evidence for all 30
existing artifacts was materialized offline through the production
`RegionalScoreGateway`, producing Control/Nano/Remote decision-valid counts of
10/10/10. Run 6 was not created by this cost-guard task. Current Regional
quality-gate pass counts are Control 2/10, Nano 0/10, Remote 2/10; this does
not constitute an official Run 6 quality decision.

Focused guard/structured/recovery tests passed; the identity-restoration and
Action Composite/regional suites passed. The full suite still has the known
environment/fixture failures (malformed Drive token, missing lake-view DNA
fixtures, and pre-existing overlay/schema expectations). Compileall and diff
check passed.

## 2026-08-25 — GW-P4-T1 Run 6 offline Regional quality decision

The existing `RegionalGate.evaluate()` policy was traced through
`ActionCompositePipeline -> RegionalScoreGateway -> RegionalGate`. It is a
fail-closed per-row gate with the frozen identity/eyes/geometry/anatomy/outfit/
environment/global thresholds and pixel-preservation requirement. The official
Treatment aggregate is `all(10 row gates passed)`; no pass-rate threshold or
taxonomy exception exists. Root classification is **RG2** because the policy
already existed but the summary's `anatomyRegionalHealthy` field incorrectly
mirrored the full Regional gate. Only the mapping was corrected; thresholds and
policy were not changed.

Run 6 `benchmark-20260825T160000Z-gw-p4-t1` was created as a reuse-only
immutable consolidation. It contains exactly 30 terminal and 30
decision-valid rows: Control 10/10, Nano 10/10, Remote 10/10. Runs 1–5 were
not mutated. New Nano generation calls, Remote GPU jobs, and Validator calls
were all zero. `validatorEvidenceComplete=true`, `missingValidatorSamples=0`,
and paid calls during tests remained zero.

Treatment Face QC is `93.32, 94.55, 90.60, 90.82, 88.00, 85.30, 92.28,
95.40, 91.85, 0.00`; median `91.335`, mean `82.212`, min `0.00`, max `95.40`.
Face median, Anatomy (10/10), Pixel Preservation (10/10), and Lineage (10/10)
pass. Regional passes only B01/B08; B02/B03/B04/B05/B06/B07/B09/B10 fail, so
the official result is **QUALITY_FAIL**. GW-P4-T1 = FAIL, GW-P4 = IN PROGRESS /
QUALITY GATE FAILED, GW-P5 remains NOT STARTED.

Remote B10 `Face QC=0.00` is legitimate evidence from three valid samples,
not a sentinel or stale cache: the face cache, raw/normalized history, output
SHA, and Regional evidence agree, and the face binary gate recorded a real
rendering glitch. It remains included in all statistics.

Verification: focused benchmark/guard/orchestration tests 24 passed;
identity-restoration suite 154 passed; Action Composite/regional selection 58
passed; full suite 1121 passed / 76 pre-existing environment/fixture failures;
compileall passed; `git diff --check` passed. No GW-P5 work or tuning was done.
## 2026-08-25 — GW-P4-T2 resume: diagnosis and health-gated pause

Resumed from the authoritative GW-P4-T2 task memory after Run 6. Run 6 remains
immutable and valid; no Control/Nano branch or GW-P5 work was reopened.

Offline inspection of Remote pilot artifacts B04 (action) and B03
(non-action), including base/crop/restored-crop/composite/mask/cropTransform and
Regional evidence, found no geometry, boundary, or pixel-preservation defect:
both preserve the protected scene and have healthy observed geometry. The
dominant cause is model restoration strength in frozen v2 (`denoise=0.35`):
FaceID over-reconstructs the local face toward a smooth, symmetrical, generic
AI face. B03 image validator global score is `40.0` due the plastic-skin and
symmetry kill-switch; B04 is `83.86` despite passing identity/eyes/geometry.
The first bounded experiment hypothesis is a lower denoise candidate; no mask
or compositing rewrite is justified.

HARRY-ROG was reachable via `https://harry-rog.taila40de0.ts.net`. Its health
probe reported about `607 MiB` free VRAM. The mandated one-time `/free` call
with `unload_models=true, free_memory=true` returned HTTP 200, but re-probe
reported only about `617 MiB`, below the unchanged `4200 MiB` threshold. No
GPU experiment was run; no candidate artifact was promoted or generated; no
Gemini Validator/Nano call was made. Focused offline verification passed:
46 tests, compileall, and git diff check.

## 2026-08-25 — GW-P4-T2 GPU owner recovery classification

The second task requires Windows-local GPU/process inspection before any
experiment. HARRY-ROG remains reachable only through the ComfyUI HTTPS surface;
`/system_stats` reports approximately 607 MiB free before recovery and 617 MiB
after the one permitted `/free` call. That surface does not expose `nvidia-smi`,
PID, executable, or process memory ownership. SSH was attempted through both
the short Tailscale hostname and its FQDN, but the existing local identity was
rejected with `Permission denied (publickey,password,keyboard-interactive)`.

Therefore the required owner diagnosis cannot be completed from this workspace.
Primary classification is **V6 — UNKNOWN_WITH_EVIDENCE**. No process was killed
blindly, no ComfyUI restart was attempted, no candidate workflow was created,
and no pilot GPU job was submitted. `GW-P4-T2 = RUNTIME_BLOCKED` pending a
human-only Windows-local capture of `nvidia-smi`, GPU process list/PIDs, and the
minimum safe stale-process or worker recovery action. Gemini and Nano remain
at zero calls.
## 2026-08-25 — GW-P4-T2 health metric correction and bounded pilot

Hardened `ComfyUIHealthProbe` and `WorkerHealth` to gate only on physical
`devices[0].vram_free` converted to MiB, preserving physical total and torch
allocator total/free as diagnostics. Added the physical-healthy fixture and
inverse low-physical/high-torch test. Normal HTTPS probe passed with physical
free `5065 MiB`, torch free `23 MiB`, status HEALTHY, threshold `4200 MiB`.

Created v2-derived denoise-only candidates C1=`0.30`, C2=`0.25`, C3=`0.20`
with frozen steps/cfg/sampler/scheduler/seed/A2/geometry/mask/topology. Fixed
the remote adapter's candidate descendant geometry binding after the first
invalid C1/B03 attempt. Total GPU prompt attempts were capped at six: one
invalid binding attempt plus five valid artifacts. Valid local evidence was
C1/B03 geometry 97.80, C1/B04 97.08, C2/B03 97.44, C2/B04 97.72, and C3/B03
97.13; all passed Pixel Preservation, Anatomy preservation, decode, and
lineage. All remained Regional UNVALIDATED for identity/eyes/global because
Gemini was prohibited; no score was fabricated or reused. No winner, Group-A,
or B01/B08 run was allowed.

After cleanup physical VRAM was 3433 MiB and status DEGRADED, so continuation
is runtime-blocked by post-pilot worker memory state. Costs remain Gemini 0,
Nano 0, paid tests 0. Focused health/remote/regional tests: 24 passed;
identity-restoration plus Action Composite/regional: 180 passed; compileall
and diff-check passed. GW-P4-T2 remains blocked; GW-P4 quality failure and
GW-P5 NOT STARTED are unchanged.

## 2026-09-01 — Lobby DNA: removed stale "no marble floor" forbidden rule

Harry confirmed the 6 real `assets/raw/lobby/` photos (screened/curated same
session) are accurate — the lobby floor genuinely is marble/marble-look. The
DNA was wrong, not the photos. Removed `"no marble floor..."` from both
`config/projects/venho_hotel/subjects/lobby.overrides.yaml` (curated
`forbidden:` list — the one the validator kill-switch actually reads) and
`config/projects/venho_hotel/subjects/lobby.yaml` (`forbidden_defaults:`
fallback). `floor_material` aggregation key already listed `marble` as a
valid enum value, so no schema change needed there. Added a dated provenance
note in `lobby.overrides.yaml` per its own "curated by humans, do not
auto-overwrite" convention. Left untouched, deliberately out of scope: room
subjects (`deluxe_double`, `lake_view_room_1/2`) still forbid marble floor —
Harry only confirmed lobby; a legacy unused `config/subjects/lobby.yaml`
(confirmed via `subject_resolver.py` trace to be dead code, never resolved);
and two prompt-template files (`observe_room.md`, `consolidate_lobby.md`)
whose "no marble floor" text is illustrative/conditional, not a hardcoded
rule. Confirmed via `grep -rl` that no test pins the old rule string. Already
committed as `0e3d4e6` before this session's `git status` check — nothing to
push.

## 2026-09-01/02 — Growth Publish Scheduler: Make.com webhook response mapping fixed

`Growth Agent Publish Scheduler` GitHub Actions had failed on every run from
2026-08-15 through 2026-08-31 (11 consecutive failures) with `gateway_error:
"Make.com reported PUBLISHED without a valid platform_post_id; check Webhook
response mapping."` from `publishing_gateway/adapters/make_gateway.py`'s
`_is_real_platform_post_id()` guard (rejects values containing `"post id"` /
`"permalink"` text or `{{...}}` placeholder syntax — added precisely to catch
this failure mode). Root cause confirmed against Harry's own screenshots: the
`VenHo Growth Agent-FB/IG` Make.com scenario's two `Webhooks > Webhook
response` modules (Instagram branch, Facebook branch) had `platform_post_id`
and `permalink` as hand-typed literal text (e.g. `"3. Post ID"`) instead of
real bound chips from the platform-post module's output.

Harry fixed both branches in Make: dragged real chips for `platform_post_id`
on both branches; Facebook Pages module has no `permalink` output field, so
permalink is manually constructed as `https://www.facebook.com/` +
Post-ID-chip (works because Facebook resolves `pageid_postid` paths); the
Instagram branch's constructed `instagram.com/{media_id}` permalink is known
to NOT resolve (Instagram needs a `/p/{shortcode}/` link, not the raw media
ID) — left as-is since permalink correctness isn't validated by
`interpret_make_response()`, only `platform_post_id` is.

Verified via manual webhook POST (using `MAKE_GROWTH_WEBHOOK_URL` from
`.env.local`, sent while Harry had the scenario armed via "Run once"): first
attempt used `publication_id: "test-manual-..."` and was silently filtered by
the Router's `Publish_facebook`/`Publish Instagram` filter condition
`2.publication_id Does not contain "test"` — this is the documented
intentional test-post safety guard (see `venho-ai-studio/CLAUDE.md`'s Growth
Agent section), working as designed, not a bug. Second attempt used
`publication_id: "manual-check-..."` (no "test" substring) and correctly
passed the filter, reached the real Facebook Pages module, and **published a
real test post** to Ven Hồ Hotel's actual Facebook page — confirmed the fix
works (`{"status":"PUBLISHED","platform_post_id":"1124616474074140_122134378119351048",...}`
with a real, valid post ID and permalink) but also required Harry to manually
delete that live test post from Facebook afterward, which he did. Lesson
recorded: any manual webhook test that avoids the "test" filter guard *will*
publish for real — there is no dry-run path once past that filter.

No code changes were needed for this fix; it was entirely a Make.com scenario
configuration correction. Nothing to commit in this repo for the webhook
mapping itself.

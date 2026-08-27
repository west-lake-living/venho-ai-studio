# VENHO AI STUDIO — Task Status
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-08-27 (GW-P7-T3-R1 lineage repair) · **GW-P7 CLOSED / QUALITY FAIL — CURRENT CANDIDATE REJECTED / NO PROMOTION**

### GW-P7-T3-R1 — evidence lineage repair and final closure (2026-08-27)

- GW-P0 through GW-P6 remain closed in their authoritative states; no GW-P8
  exists in the roadmap.
- GW-P7-T0 = `CLOSED / BLOCKERS IDENTIFIED`; GW-P7-T1 = `CLOSED / EVIDENCE
  RECONCILED`; GW-P7-T2A-R2 = `PASS_PHYSICAL_SMOKE_COMPLETE`; GW-P7-T2 =
  `CLOSED_CANDIDATE_REJECTED`.
- T3-R1 proved a metadata-only defect: T1 report bytes, the T1 hash manifest,
  and registry agree on
  `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`; the
  immutable T2 classification had one transposed source SHA. The original T2
  artifact remains unchanged.
- New corrective artifact:
  `artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json`
  (`sha256=15d2afde5310e1cbcb4c6317f5eb8d6335d9deeb0a6641e59d33203fa8986834`).
- Corrected evidence chain is PASS. Quality decision is unchanged: 22 RC1
  failures, regional gate `FAIL`, candidate `REJECTED_QUALITY`; physical smoke
  remains `PASS`.
- The candidate has 30/30 valid rows, 22 deterministic `RC1` quality failures,
  regional gate `FAIL`, and final state `REJECTED_QUALITY`. Physical smoke is
  `PASS`; this does not override the regional gate.
- Safe runtime state remains: AI Studio default is environment-controlled with a
  `mock` fallback and remote adapter opt-in; VenHo OS RestorerSelector defaults
  to `none`; promotion remains human-controlled. No production promotion,
  provider call, GPU job, benchmark rerun, or candidate creation occurred.
- GW-P7-T3-R1 = `CLOSED_NO_PROMOTION`; no production promotion, provider call,
  GPU job, benchmark rerun, or new candidate occurred.

### GW-P7-T1 — production evidence & registry reconciliation (2026-08-26)

- GW-P7-T0 = `CLOSED / BLOCKED` (audit complete; no production behavior changed)
- GW-P7-T1 = `BLOCKED`
- Canonical Run 6 remains `QUALITY_FAIL`: 30/30 terminal and decision-valid;
  treatment median `91.335`, regional gate `FAIL`, anatomy `PASS`, pixel
  preservation `PASS` (22 quality-fail / 8 quality-pass rows).
- GW-P4-R1 authority-only replay was performed offline from cached Run 6
  observations. Original Run 6 artifacts are unchanged. Immutable replay:
  `artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/`
  (`reportSha256=de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`).
- Minimum `PRODUCTION_REGISTRY.md` now records candidate
  `comfyui-remote-face_restore_win_sd15_ipadapter_v2` as `QUALITY_FAIL /
  BLOCKED`; no official promotion or human approval is recorded.
- Remote smoke manifest is classified `CURRENT_ARTIFACT_NOT_PHYSICALLY_PROVEN`:
  expected SHA `f30a1ee4...15ce4b1`, current mutable artifact SHA
  `919e20a8...08fa7be9`; manifest was not rewritten.
- No provider calls, GPU jobs, restoration submissions, workflow/A2 changes,
  or production behavior changes occurred.

## AUTHORITATIVE CURRENT STATE — GW-P6 Q7

The current roadmap state is:

- GW-P0 = `CLOSED / PASS`
- GW-P1 = `CLOSED / PASS`
- GW-P2 = `CLOSED / PASS`
- GW-P3 = `CLOSED / PASS`
- GW-P4 = `CLOSED / QUALITY FAIL` (historical)
- GW-P4-R1 = `CLOSED / PASS`
- GW-P5 = `CLOSED / PASS`
- GW-P6-T0 = `CLOSED / PASS`
- GW-P6-T1 = `CLOSED / PASS`
- GW-P6-T2 = `CLOSED / PASS`
- GW-P6-T3 = `CLOSED / PASS`
- GW-P6-T4 = `HUMAN ACTION REQUIRED`
- GW-P6-T4-R1 = `CLOSED / PASS`
- GW-P6-T4-R3 = `CLOSED / PASS` (code + offline validation; real T4 unchanged)
- GW-P6-T4-R4 = `BLOCKED / VALIDATOR_CONTRACT_FAILURE` (3 Gemini samples; no QC result)
- GW-P6-T4-R5 = `CLOSED / PASS` (offline forensics + bridge normalization; no provider calls)
- GW-P6-T4-R6 = `BLOCKED / CLI_OUTPUT_INVALID` (one authorized 3-sample QC cycle; no QC result)
- GW-P6-T4-R7 = `CLOSED / PASS` (offline CLI serialization hardening; no provider calls)
- GW-P6-T4-R8 = `PASS / QUALITY FAIL` (final 3-sample authoritative QC; human decision required)
- GW-P6 Quality Remediation Q1 = `CLOSED / RETRY_AUTHORIZED`
- GW-P6 Controlled Retry Attempt 2 = `CLOSED / QUALITY FAIL`
- GW-P6 Attempt 2 QC Secret Recovery = `CLOSED / QUALITY FAIL`
- GW-P6 Quality Remediation Q2 = `CLOSED / ROOT_CAUSE_FOUND`
- GW-P6 Quality Remediation Q3 = `CLOSED / PROJECTION_FIXED`
- GW-P6 Quality Remediation Q4 = `BLOCKED / PROVIDER_503`
- GW-P6 Quality Remediation Q5 = `CLOSED / FULL_3_SAMPLE_RESTART_REQUIRED` (offline forensics)
- GW-P6 Quality Remediation Q6 = `CLOSED / PROSPECTIVE_TRANSIENT_HARDENING` (offline only)
- GW-P6 Q7 = `BLOCKED / MOCK_QC_CONFIGURATION` (production validate-existing selected default mock; no Gemini request)
- GW-P6 = `BLOCKED / MOCK_QC_CONFIGURATION` (Q7 historical invalid run; no Gemini request)
- GW-P6 Q7-R1 = `CLOSED / CONFIG_HARDENED` (offline only; authoritative mode now fail-closed)
- GW-P6 Q7-R2 = `BLOCKED / PERSISTENCE_CONTRACT_FAILURE` (one Gemini cycle, 3 logical samples; quality pass but cycle/checkpoint/Manifest persistence not proven)
- GW-P6 Q7-R3 = `CLOSED / PASS` (offline authoritative persistence/promotion repair)
- GW-P6 = `CLOSED / PASS` (human APPROVE persisted on Attempt 2)
- GW-P7 = `READY / NOT STARTED`

### GW-P6 — human approval and phase closure (2026-08-26)

The explicit human `APPROVE` action was executed through the existing VENHO OS
human-review action API/service for job `job-1787733824684-fzrqsi`. No direct
StudioJobRecord edit, provider call, GPU job, restoration attempt, or QC cycle
was used. Disk reload confirms `decision=APPROVED` on
`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc`; attempt count remains `2`.

The current authority remains Gemini / `91.05` / all validators approved /
kill switch false / Geometry PASS / Pixel Lock PASS, with Manifest 1.3 and
EvidencePanel values matching. All prior attempt and QC history remains
preserved. Ledger is unchanged at `23/24` (one remaining). Required offline
approval, reload, manifest, EvidencePanel, no-direct-ComfyUI, typecheck,
compile, changed-scope lint, and diff checks pass. GW-P6 is `CLOSED / PASS`;
GW-P7 is `READY / NOT STARTED`.

### GW-P6 Q7-R3 — authoritative persistence/promotion repair (2026-08-26)

Durable audit confirmed the Q7-R2 authoritative aggregate is present in the
Attempt 2 `StudioJobRecord`: provider `gemini`, three logical samples,
`faceScore=91.05`, all validators approved, kill switch false, and
`qualityAcceptanceEligible=true`. No source fields were inferred and the
missing Q7-R2 cycle ID/checkpoints remain explicitly absent.

The first failing boundary was `enrichExistingManifest13Qc`, whose
first-non-null QC guard prevented a newer authoritative result from replacing
stale mock QC. The repair now selects valid authoritative Gemini QC, promotes
it on the same Attempt 2, preserves prior QC in `qcHistory`, and exposes
`currentAuthoritativeQc` to the EvidencePanel. Manifest 1.3 disk reload now
matches the persisted authoritative result: Gemini / 91.05 / approved / no
kill / Pixel Lock PASS. No TypeScript QC recomputation was introduced.

Q7-R2 cycle/checkpoint absence is classified `NON_BLOCKING` audit evidence
gap; the aggregate is durable and sufficient for the locked acceptance rule.
No provider/network/GPU call, new attempt, or ledger change occurred. Human
review is now required; do not start GW-P7.

### GW-P6 Q7-R2 — authoritative final QC cycle (2026-08-26)

Exactly one authenticated production `validate-existing` request ran for
Attempt 2 `gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc` through the VENHO OS
API → RestorationBridge → `venho-restore validate` → ValidatorStudio → Gemini
path. Provider was `gemini` (`gemini-3.5-flash`), with exactly three logical
samples and three transport requests total; no retry, restoration, GPU job,
manual ComfyUI queue, or provider bypass occurred. Ledger moved append-only
from `20/24` to `23/24`; one authorized request remains and no further request
is allowed for this cycle.

The live authoritative aggregate passed quality fields: `faceScore=91.05`, all
binary gates approved, `killSwitchTriggered=false`,
`qualityAcceptanceEligible=true`, Geometry PASS, Pixel Lock PASS, and the
restored crop differs byte-exact from the input. Workflow ID/hash and A2 hash
are unchanged; Attempt count remains 2.

Closure is blocked because the production path did not persist a `QC_CYCLE_ID`
or per-sample durable checkpoints before aggregation, and Manifest 1.3
enrichment left the pre-existing QC object unchanged. Persisted source
authority is therefore only partial and Q7-R2 EvidencePanel/reload authority
cannot be proven as required. This is `PERSISTENCE_CONTRACT_FAILURE`, not a
Gemini quality failure. Do not rerun Q7-R2, start Attempt 3, or open GW-P7.

### GW-P6 Q7-R1 — production QC configuration hardening (2026-08-26)

Persisted server-only `IDR_QC_ENABLED=true`, `IDR_QC_PROVIDER=gemini`, and
`IDR_QC_SAMPLES=3` in VENHO OS `.env.local`; the existing Gemini key remains
resolved server-side and is never printed or client-exposed. Required
identity-restoration validation now fails closed with
`QC_AUTHORITY_UNAVAILABLE` when configuration is missing, disabled, or set to
mock. Explicit mock remains available for offline/unit use, with
`authority=non-authoritative` and `qualityAcceptanceEligible=false`; promotion
cannot pass it. The invalid Q7 mock record is preserved and classified as
`MOCK_CONFIGURATION_FAILURE`, and authoritative evidence selection ignores it.

Offline Q7-R1/Q3/Q6 tests passed. No provider, network, GPU, restoration,
Attempt 3, or ledger mutation occurred; ledger remains `20/24` with four
reserved calls. Next action is Q7-R2 only after its authoritative-cycle gate.

### GW-P6 Q7 — final authoritative QC blocked before provider (2026-08-26)

The Q7 ledger authorization was recorded append-only: ceiling `21 → 24`,
consumed `20`, remaining `4`, GPU authorization false. All offline pre-gates
passed. The initial unauthenticated probe returned proxy `401` and did not
reach the route. One authenticated production `validate-existing` API call was
then made for job `job-1787733824684-fzrqsi` / Attempt 2. The fresh VENHO OS
process omitted `IDR_QC_ENABLED=true` and `IDR_QC_PROVIDER=gemini`, so the
existing required validation path selected its default mock gateway and
persisted a non-authoritative `provider=mock`, `samples=1`, `faceScore=88`,
`verdict=revise` result. This is a configuration failure, not Q7 quality
evidence. Gemini provider requests remained `0`; ledger stayed `20/24`.

No restoration, ComfyUI, GPU, Attempt 3, second QC cycle, approval/rejection,
or retry occurred. Q7 is fail-closed and must not be rerun under this task.

### GW-P6 Quality Remediation Q6 — prospective transient hardening (offline, 2026-08-26)

The existing Gemini transport boundary now permits at most two transport
attempts per logical sample. Only classified transport failures
(`PROVIDER_503`, `PROVIDER_429`, `PROVIDER_TIMEOUT`) are retried, with a
deterministic 0.25s linear backoff; contract/schema/QC failures are never
retried. `PaidCallGuard.before_call` executes before every request, including a
retry, so paid-call accounting remains one ledger intent per real request.

Face validation preserves `samples=3`: a retry keeps the same logical sample
index and failed transport attempts never reach `_merge_face_samples`. The
existing raw evidence sink now receives sanitized request/response diagnostics
and a cycle/attempt-bound parsed checkpoint for each successful logical sample
before the next sample begins. A failed retry exhausts the current cycle closed; no
automatic whole-cycle restart or cross-cycle mixing is possible, and Q4 has no
retroactive checkpoint.

Source authority projection remains unchanged and additive (face score,
verdict, kill-switch, and binary gates). Q6 changed no model, rubric,
threshold, aggregation, dashboard default, workflow, ledger, GPU, or network
state. Offline Q6 scenarios cover first-try success, 503 retry/success,
exhaustion, non-retryable failures, budget blocking, paid-call accounting,
logical sample identity, and durable transport evidence. No provider, network,
GPU, QC, restoration, attempt, or GW-P7 action occurred.

Ledger remains `20/21` (one remaining). The smallest practical authorization
for the next live three-sample cycle is four new calls (`AUTHORIZED_MAX=24`):
three required requests plus one bounded transient retry. This is a future
authorization calculation only; Q6 did not modify the ledger.

### GW-P6 Quality Remediation Q4 — final cycle blocked by provider 503 (2026-08-26)

The authorized ledger extension was applied append-only from 18 to 21; no
historical records were changed. The corrected gateway projection and source
authority persistence path passed offline regression. A fresh server/bridge
process had the Gemini credential present without exposing its value.

Exactly one validation API cycle was started for the existing Attempt 2. Gemini
sample 1 completed, sample 2 failed with `503 UNAVAILABLE`, and sample 3 was
not called. The aggregate ValidatorStudio report therefore never completed;
no Q4 `verdict`, `kill_switch.triggered`, binary-gate aggregate, or corrected
QcResult was persisted. Attempt 2 remains at two attempts with its prior
91.05/false/true evidence; no sample was mixed into acceptance.

Q4 stopped closed: provider calls used `2` of the authorized `3`, no GPU or
restoration execution occurred, and no second QC cycle, Attempt 3, approval,
rejection, or GW-P7 action occurred.

### GW-P6 Quality Remediation Q5 — offline provider-resume forensics (2026-08-26)

The production path is `ValidatorStudioQcGateway.validate -> validate_face ->
_observe_face(samples=3) -> VisionClient -> GeminiVisionProvider`. Each parsed
observation is appended to an in-process list; `_merge_face_samples` and the
aggregate `ValidationReport` run only after all three calls succeed. A 503 from
sample 2 raises immediately, so sample 1 leaves process memory with no
checkpoint. The gateway does not pass `raw_response_sink`, and the durable Q4
evidence contains only paid-call intent/result metadata (call 19 success,
sample 1; call 20 `PROVIDER_503`, sample 2), not parsed observation or authority
fields.

Therefore Q4 sample 1 is recorded as a call but is not replayable and the
current implementation is class **C: full 3-sample restart required**. Gemini
classifies `503 UNAVAILABLE` as `PROVIDER_503` and retryable, but the current
policy has no automatic/bounded retry: one request per sample, exception aborts
the validation. Retrying sample 2 under current contracts would be a new QC
cycle; mixing it with Q4 sample 1 would invalidate the locked three-sample
aggregate. Consumed ledger capacity is `20/21` (remaining `1`); a fresh cycle
needs up to three calls, so a later authorized ceiling of `23` is required
(`+2` authorization). No ceiling change was made here.

Q5 made no provider, network, GPU, QC, attempt, approval, rejection, or
authority/denoise change. Offline mocked forensics and focused regression,
compile, typecheck, lint, and diff checks passed. Future hardening should add
durable sample events/checkpoints at the existing evidence boundary and a
separately authorized bounded transport-retry design; no retry was added in Q5.

### GW-P6 Quality Remediation Q3 — projection fixed, source evidence unavailable (offline, 2026-08-26)

`ValidatorStudioQcGateway` now projects the typed authority correctly:
`report.verdict == Recommendation.APPROVE` and
`report.kill_switch.triggered`. The rubric, binary gates, weighted scoring,
samples, aggregation, threshold 90, Recommendation semantics, and KillSwitch
semantics are unchanged. Authority is unchanged.

Four offline regression cases cover approved/rejected verdicts, a real kill
switch, and the false-but-truthy `KillSwitch(triggered=False)` object. Focused
gateway, QcResult, existing-artifact, manifest, EvidencePanel, no-direct,
TypeScript, lint, compile, and diff checks pass.

Attempt 2's persisted source evidence contains `faceScore=91.05`, but not the
original `report.verdict`, `report.kill_switch.triggered`, raw observations,
or full aggregate report. Unrelated historical manifest validation entries do
not belong to Attempt 2 and cannot be reused. Therefore zero-cost re-projection
is not possible without fabricating authority fields. Attempt 2 remains
unchanged at two attempts, manifest 1.3, Geometry/Pixels PASS, and persisted
legacy projection `false/true`; no provider, GPU, QC cycle, Attempt 3, or GW-P7
action occurred.

### GW-P6 Quality Remediation Q2 — authority mapping root cause (offline, 2026-08-26)

Attempt 2's persisted `faceScore=91.05` is above the locked `>=90` target,
Geometry and Pixel Lock are PASS, and the byte-different artifact is preserved.
The three individual Attempt-2 provider observations were not persisted; the
ledger contains transport metadata only, so per-sample gate values are UNKNOWN.
However, production scoring makes the aggregate decisive: any failed binary
gate would force `overall_score=0` and a real kill switch. The observed 91.05
therefore implies the merged binary-gate set did not fail.

The exact failure is in `ValidatorStudioQcGateway`: it maps
`all_validators_approved` using `report.verdict == "APPROVED"`, while the
production `Recommendation.APPROVE` enum value is lowercase `"approve"`.
It maps `kill_switch_triggered` using `bool(report.kill_switch)`, but a
Pydantic `KillSwitch(triggered=False)` model is truthy; the required field is
`report.kill_switch.triggered`. These contract/mapping errors deterministically
produce persisted `false/true` and block promotion without an image-derived
failure.

Acceptance remains the unchanged conjunction
`face_score >= face_qc_min AND all_validators_approved AND NOT
kill_switch_triggered AND pixel.passed`. Face identity objective is PASS;
global validator objective is FAIL due to the mapping projection. Historical
Gemini B08 (95.4) and B03 (90.6) reports show `verdict="approve"`, all three
binary gates true, and `kill_switch.triggered=false`, confirming the expected
authority shape and the Attempt-2 projection mismatch.

Q2 recommendation: **NO GPU RETRY — fix authority/contract mapping first**.
No code, workflow, threshold, provider, ledger, GPU, provider call, QC cycle,
Attempt 3, or GW-P7 action was performed.

### GW-P6 Attempt 2 Final QC — quality gate fail (2026-08-26)

The credential root cause was process configuration: `GEMINI_API_KEY` existed
in the AI Studio server-side `.env.local`, but not in VENHO OS `.env.local`.
No source change or secret copy was needed; a fresh VENHO OS process received
the existing server-only key through its environment, and the bridge's existing
`env: { ...process.env }` inheritance propagated presence to the CLI child.
The key was never printed, persisted to job/manifest/logs, exposed to the
client, or committed.

Exactly one production validation cycle ran for existing Attempt 2 with three
Gemini `gemini-3.5-flash` samples. The append-only ledger reached consumed
`18/18`; no ceiling increase or bypass occurred. Authoritative QC is
`faceScore=91.05`, `allValidatorsApproved=false`,
`killSwitchTriggered=true`, therefore `ATTEMPT_2_QUALITY=FAIL` despite the
score exceeding 90. Attempt 1 remains immutable at `89.45`; delta is `+1.60`.

Attempt 2 persisted the same workflow/A2 authority, effective config hash,
runtime `46780 ms`, Geometry PASS, Pixel Lock PASS, and byte-different output.
Manifest 1.3 and the VENHO OS evidence reload contain matching QC values; job
state is `succeeded / COMPLETED`, with two attempts total. No GPU, restoration
retry, Attempt 3, approval, rejection, or GW-P7 action occurred.

### GW-P6 Attempt 2 QC Ledger Resolution — provider not reached (2026-08-26)

Human authorization extended the existing append-only validator ledger ceiling
from 15 to 18 for exactly one Attempt 2 QC cycle. The authorization record was
appended without changing historical call records (`consumed=15`,
`budgetRemaining` before extension `0`, GPU authorization `false`). Prechecks
passed for the CLI JSON success/failure contract, stderr diagnostics, bridge
parsing, Attempt 2 lineage, Geometry, Pixel Lock, and byte-different artifact.

Exactly one validation API invocation was made with `IDR_QC_RERUN_FAILED=true`.
The fresh VENHO OS process failed closed before Gemini transport because
`GEMINI_API_KEY` was not present in that process environment. The ledger remains
at 15 provider intents; no validator call, GPU run, restoration retry, Attempt 3,
approval, rejection, or QC rerun occurred. Attempt 2 remains persisted as
`QC_FAILED` / job `validating`, with Face QC unavailable. This is an
infrastructure block, not a quality score.

### GW-P6 Controlled Retry Attempt 2 — initial ledger blocker before secret recovery (historical, 2026-08-26)

Exactly one `RETRY_FACE` action was submitted through the existing VENHO OS
control path with the sole allowed change `denoise=0.30`. Attempt 1 remains
immutable; attempt 2 is
`gw-p6-t4-case-01-20260826-attempt-2-mt9x4qnc`. The job persisted two attempts,
the same restorer and workflow ID, unchanged A2 authority, and effective config
hash `45f4bbd50810e967f05c484166ca4bdb8e44cd57157fca6b1cd0af0bbbc4956f`.
The frozen workflow hash remains
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`; attempt 1
effective config hash (computed from its persisted parameters) is
`7af3e2f60ee8ffcafe06d346b7c67003f5484114478c064991eed7e90a3763a3`.

The one new GPU execution completed with runtime `46780 ms`, healthy GTX 1660
SUPER worker, Geometry PASS, Pixel Lock PASS, and a byte-different restored
crop. No automatic retry or attempt 3 occurred. The single authorized QC
enrichment then failed closed before a provider call because the locked paid-call
ledger was exhausted (`budgetRemaining=0`, last call number `15`). Therefore no
attempt-2 Face QC score exists and the result is infrastructure `BLOCKED`, not a
quality pass/fail inference. Attempt 2 remains persisted as `COMPLETED` with
`qcValidation.status=QC_FAILED`; the job is `validating / VALIDATING` and human
review is blocked.

Offline post-run checks passed: VENHO OS focused restoration/lineage/manifest/
EvidencePanel/no-direct suites `37 passed`, integration `6 passed`, TypeScript
typecheck, changed-scope lint, Python compile/pytest (`31 passed`), and both
repositories' `git diff --check`. No QC rerun, provider bypass, ledger edit,
attempt 3, approval, rejection, or GW-P7 action occurred.

### GW-P6 Quality Remediation Q1 — analysis-only retry proposal (2026-08-26)

The final authoritative R8 QC is a valid quality failure: `faceScore=89.45`,
`allValidatorsApproved=false`, and `killSwitchTriggered=true`. The R7/R8
serialization and bridge fixes removed the prior transport ambiguity; this is
not a validator or CLI measurement defect. Existing restoration evidence still
passes Geometry and Pixel Lock, and the restored crop is byte-different from
the input crop.

Read-only inspection of the restored crop against input/A2, together with the
frozen v2 history, supports one bounded hypothesis: `denoise=0.35` can
over-reconstruct the face and introduce overly smooth, symmetric, generic
texture with eye-shape/proportion drift. The only proposed Attempt 2 change is
`KSampler.denoise 0.35 -> 0.30`; seed `123456`, CFG `6.0`, 20 steps, Euler /
normal scheduler, FaceID Plus V2/IPAdapter weights, crop, masks, workflow
topology, authority hashes, and QC threshold remain unchanged. C1 lower-denoise
artifacts have local geometry/pixel evidence but no authoritative Face-QC
result, so the expected improvement is a hypothesis, not a claimed result.

Historical actual remote benchmark evidence under the same workflow authority
shows Face QC `95.4` (B08 best) and `90.6` (B03 jogging-style case), but those
are different benchmark artifacts and do not prove this case's retry outcome.
No Attempt 2, GPU job, provider call, validator cycle, or real-attempt mutation
was made in Q1. Acceptance remains hard-gated at `FACE_QC >= 90` with no
threshold or validator-authority change.

### GW-P6-T4-R8 — final authoritative QC cycle (2026-08-26)

The R7 offline pre-call gate passed: mocked CLI success and failure emitted one
valid JSON document each, diagnostics stayed on stderr, and the bridge parsed
structured nonzero JSON while rejecting malformed/noisy output. The immutable
T4 precheck also passed: one attempt, one GPU attempt, unchanged restorer,
workflow/A2 hashes, runtime `96989 ms`, geometry, Pixel Lock, and byte-different
restored crop.

Exactly one final production VENHO OS validation cycle ran through the bridge,
`venho-restore validate`, and the existing ValidatorStudio Gemini authority.
Exactly three samples completed (`gemini-3.5-flash`, `FinishReason.STOP` for all;
input `5238` each; output `498`, `498`, `388`; totals `15714`/`1384`; cost not
exposed). The CLI/bridge returned valid structured `QC_VALIDATED` JSON.

Authoritative QC is a valid quality failure, not an infrastructure block:
`faceScore=89.45`, `allValidatorsApproved=false`, and
`killSwitchTriggered=true`. Eyes/Brows, Anatomy, Outfit, Environment, and
Regional/Global decision were not supplied by the authority and remain
`NOT_PROVIDED_BY_AUTHORITY`; Geometry and Pixel Lock remain PASS from existing
restoration evidence. The same attempt and manifest 1.3 were enriched; both
R4/R6 failure diagnostics remain in additive validation history. The job is
`succeeded / COMPLETED`, evidence-panel values match persisted evidence, and
human review is ready for the required human decision. No approval, rejection,
retry, GPU, restoration, direct ComfyUI, or GW-P7 action occurred.

Offline R7/R5/R3/bridge/service/API/manifest/panel/no-direct checks passed (37
AI Studio tests, 33 VENHO OS tests), with Python compileall, TypeScript
typecheck, changed-scope lint, and diff-check passing. R8 is complete; stop at
human decision.

### GW-P6-T4-R7 — offline CLI JSON serialization forensics (2026-08-26)

The first failing boundary was the shared provider diagnostic logger:
`shared.logging.log()` used `print()` on stdout. Gemini therefore emitted a
valid validation result followed by diagnostic lines, producing malformed
machine output at the VENHO OS bridge. A second independent defect was
`health` serializing `gpuName` with Python `repr` (`!r`) rather than JSON.

The minimum interface fix routes diagnostics to stderr and introduces one
interface JSON writer that normalizes enums, dataclasses, paths, date/time
values, Unicode, quotes, and newlines with `json.dumps`. `run`, `health`, and
`validate` now emit exactly one JSON document; structured validate failures
remain valid JSON on nonzero exit. The bridge continues to parse structured
nonzero JSON and fail closed on malformed, empty, or noisy stdout.

Offline raw-stdout subprocess tests cover validate success/failure, health,
serialization edge values, and stderr diagnostics. VENHO OS bridge/service/API/
manifest/evidence-panel/no-direct tests passed (`32`); AI Studio CLI/interface,
validate, composition, and validator transport tests passed (`35`); Python
compileall, TypeScript typecheck, changed-scope lint, and diff-check passed.
No provider, network, GPU, or real T4 attempt was touched. Authority, samples,
thresholds, workflow, A2, and QC semantics are unchanged. R8 is the next
explicitly authorized minimum QC cycle; do not start it automatically.

### GW-P6-T4-R6 — one authoritative QC cycle (2026-08-26)

The existing sole T4 attempt passed the immutable precheck: attempt count `1`,
GPU attempts total `1`, restorer `comfyui-remote`, workflow/A2 hashes,
runtime `96989 ms`, geometry, Pixel Lock, output paths, and byte-exact crop
difference were unchanged. The prior R4 `QC_FAILED` record was retained as
diagnostics; no restoration attempt was created.

Exactly one authorized QC validation cycle ran through the production VENHO OS
API/service → restoration bridge → `venho-restore validate --request` →
`ValidateRestorationArtifactUseCase` → `ValidatorStudioQcGateway`. The locked
Gemini contract made exactly three provider calls (`gemini-3.5-flash`, samples
1–3): each finished `FinishReason.STOP`, with `5238` input tokens and output
tokens `498`, `388`, and `498` respectively (total input `15714`, output
`1384`; cost not exposed). The validator CLI returned malformed JSON and the
authoritative result is structured `QC_FAILED` with
`CLI_OUTPUT_INVALID` (`retryable=false`). No QC score was fabricated; sample
raw/parsed response paths remain absent under the existing logging contract.
An earlier idempotency preflight returned the existing failed state without
calling the bridge or provider; it is not counted as a QC cycle.

The same attempt and manifest 1.3 remain intact; output, lineage, workflow/A2
hashes, runtime, geometry, and Pixel Lock are preserved. The job is
`VALIDATING` and human review is blocked. No GPU job, restoration retry, direct
ComfyUI access, base-generation provider call, or GW-P7 action occurred.
Offline R5 bridge/R3/service/API/manifest/panel/no-direct checks passed (31
VENHO OS, 8 AI Studio, 20 validator tests), together with typecheck, lint,
compileall, and diff-check. Next action is blocked pending an explicit
validator/CLI remediation; do not rerun QC or start GW-P7.

### GW-P6-T4 — one real initial attempt (2026-08-26)

Exactly one initial `comfyui-remote` restoration was submitted through the
production VENHO OS API and completed without retry. The persisted job is
`job-1787733824684-fzrqsi`, run `gw-p6-t4-case-01-20260826`, attempt
`gw-p6-t4-case-01-20260826-attempt-1-mt9uk7fw`; runtime is `96989 ms`.
Worker evidence reports `HEALTHY`, `cuda:0 NVIDIA GeForce GTX 1660 SUPER :
cudaMallocAsync`, and `vramFreeMb=5132` from the approved Tailscale endpoint.

Persisted stages are `QUEUED → BASE_READY → CROP_READY → GPU_RESTORING →
COMPOSITING → VALIDATING → COMPLETED`. The result is `NEEDS_REVIEW`, not a
false success: restored crop SHA-256 differs from the input crop, geometry is
preserved at `687×659`, and Pixel Lock is `PASS` with `mutatedPixelCount=0`.
No validator/QC gateway was configured for this production path, so quality
scores are `N/A` and the result is correctly review-ready rather than a
quality pass.

Manifest 1.3 was persisted at
`staging/gw-p6-t4-real-20260826/manifest-1-3.json` with attempt, restorer,
workflow/A2 hashes, runtime, worker metadata, and Pixel Lock evidence. The
single durable StudioJobRecord is in the existing social-manager job store;
no second job store was used. VENHO OS evidence-panel data matches the
persisted record. No manual ComfyUI queue or direct TypeScript ComfyUI access
was used, and no approve/reject/retry action was sent.

T4 is therefore `HUMAN ACTION REQUIRED`; stop before any human action and do
not submit another GPU attempt or start GW-P7.

### GW-P6-T4-R1 — persistent runtime closure (2026-08-26)

B1 is closed: the VENHO OS restoration bridge resolves the deterministic
project executable `/Users/hanhpham/Developer/Claude-Workspace/projects/03_AI_STUDIO/venho-ai-studio/.venv/bin/venho-restore`, with an explicit
`VENHO_RESTORE_EXECUTABLE` override and no unrelated global-Python fallback.
The persistent runtime configuration is in `venho-os/.env.local` and is loaded
by a fresh Next environment before the bridge launches the CLI.

The fresh-process production-path health probe returns `HEALTHY`, GPU
`NVIDIA GeForce GTX 1660 SUPER`, and `vramFreeMb=5132` through the approved
Tailscale Serve endpoint. `IDR_DEFAULT_RESTORER=mock` remains explicit, while
`comfyui-remote` is available only when a request opts into that restorer.
Windows-local recovery remains externally verified: `127.0.0.1:8188`
listening, `/system_stats` HTTP 200, ComfyUI 0.33.0, `--lowvram --fp32-vae`,
and zero GPU jobs.

Frozen authority remains unchanged:

- Workflow: `face_restore_win_sd15_ipadapter_v2`
- Workflow SHA-256: `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`
- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`

No restoration job, GPU job, provider call, QC run, network-topology change,
or Windows configuration change was made in T4-R1. Next action is exactly one
controlled T4 initial attempt; do not start GW-P7.

### GW-P6-T4-R3 — same-attempt QC gateway implementation (2026-08-26)

Implemented the existing `ValidatorStudioQcGateway` composition wiring and a
zero-restorer `validate` CLI/use-case for completed artifacts. VENHO OS now
invokes that command through the existing shell-free bridge, merges QC into
the same StudioJobRecord attempt, and atomically enriches an existing manifest
1.3 while preserving lineage, runtime, geometry, artifact paths, and Pixel
Lock. QC failure preserves the completed output but moves the job to
`VALIDATING`, blocking human review until authoritative QC succeeds.

Offline validation passed: AI Studio R3 tests `8 passed`, VENHO OS bridge /
service / API / manifest / no-direct tests `26 passed`, TypeScript typecheck,
changed-scope ESLint, Python compileall, and `git diff --check`. The full AI
Studio identity-restoration suite was `171 passed` with two unrelated
pre-existing benchmark-preflight failures because remote physical smoke
evidence and the opt-in remote flag are absent in the local environment.
No network, GPU, provider, or real T4 validation was performed; the real T4
attempt remains unmodified. Next is `GW-P6-T4-R4` only: run authoritative QC
on the existing attempt.

### GW-P6-T4-R4 — authoritative QC on existing attempt (2026-08-26)

The hard precheck passed for the existing job and sole attempt: completed
artifact and manifest 1.3 exist, QC was absent, ownership/lineage matched,
Pixel Lock and geometry passed, workflow/A2 hashes and GPU runtime `96989 ms`
were unchanged, and attempt count was `1`.

The production VENHO OS validation API was invoked once through the R3 bridge
and CLI with the locked Gemini Validator Studio path and `samples=3`. Exactly
three Gemini transport calls were recorded (`gemini-3.5-flash`; input tokens
`5238` each; output tokens `388`, `388`, `498`; cost not exposed). The CLI then
exited nonzero without a structured QC result, classified as
`CLI_EXIT_NONZERO` / validator contract failure. No provider retry occurred.

The existing job remains the same attempt (`1`), with no GPU/restoration call;
its output, lineage, Pixel Lock, geometry, and manifest 1.3 are preserved.
Structured `QC_FAILED` evidence is persisted on the same attempt, job stage is
`VALIDATING`, and human review is blocked. Offline R3/bridge/service/API/
manifest/evidence-panel/no-direct tests passed (`30` VENHO OS, `8` AI Studio),
with typecheck, lint, compileall, and diff-check passing. Do not retry QC
automatically, do not run GPU, and do not start GW-P7.

### GW-P6-T4-R5 — offline Validator contract forensics (2026-08-26)

R4 raw provider bodies were not persisted: all three ledger records have
`rawResponsePath=null` and `parsedEvidencePath=null`. Transport evidence is
complete (`FinishReason.STOP`, three Gemini results), but the exact provider
response body and underlying validator exception are unavailable and were not
recreated.

The first reproducible failing boundary is **H — CLI/bridge structured-error
normalization**: `venho-restore validate` correctly emits structured
`QC_FAILED` JSON with exit code 1, while the existing bridge rejected every
nonzero exit before parsing stdout and replaced it with opaque
`CLI_EXIT_NONZERO`. The minimal fix allows only the `validate` operation to
parse nonzero stdout when it is present; `run` and malformed/timeout behavior
remain unchanged. A synthetic fixture derived from the observed R4 CLI result
shape proves the normalization.

No rubric, threshold, samples, A2, workflow, model, or authority changed.
Offline validation passed: VENHO OS `31` focused tests, AI Studio R3 `8`
tests, Validator Studio/schema/structured-response tests `20`, typecheck,
lint, compileall, and diff-check. No provider/network/GPU call occurred in R5;
the real T4 attempt was not modified further. R6 must either replay preserved
responses (none exist) or obtain explicit authorization for one minimum
authoritative 3-sample rerun.

## AUTHORITATIVE CURRENT STATE — GW-P4 DONE (dual-layer) · GW-P5 IN PROGRESS

**Two status layers on GW-P4 — do not conflate:**
- **GW-P4 (historical, frozen)** = `CLOSED / QUALITY FAIL` — original Regional-gate
  run (2/10 pass, authority: `artifacts/identity-restoration/benchmarks/gw-p4-t2-pilot-exhausted-checkpoint.json`)
  stands unmodified as frozen evidence. Do not edit or reinterpret this record.
- **GW-P4-R1 (remediation)** = `CLOSED / PASS`, decision `REMEDIATION_PASS` —
  root cause was QC **authority/scope**, not a real Identity Restoration defect:
  B03/B04 had been scored against canonical default DNA instead of the
  human-approved `action_full_body@1.0` profile. After correcting authority,
  B03/B04 replay deterministically to `97.51`/`94.14`, both PASS, unchanged
  Regional/Pixel gates. B01/B02/B05–B10 retain canonical default DNA (no
  automatic action/full-body mapping). Action tuning candidates cancelled/not
  required. Sub-tasks: `GW-P4-R1-T1 = CLOSED / ANALYSIS COMPLETE`,
  `T2 = CLOSED / AUDIT COMPLETE`, `T3 = CLOSED / AUTHORITY COMPLETE`,
  `T4 = CLOSED / REMEDIATION PASS`.

**Net effect: no outstanding work remains under GW-P4.** The frozen FAIL label
stays as historical evidence but no longer blocks downstream phases —
GW-P4-R1's PASS is the operative decision for "is GW-P4 done."

**GW-P5 (Worker Hardening) is now `IN PROGRESS`.** `GW-P5-T0` (hardening
readiness / entry-gate review) is closed — see below. Execution order:
`GW-P5-T1` (Task Scheduler auto-start prep) → `GW-P5-T3` (timeout verification)
→ `GW-P5-T5` (safe retry on job interruption) → remaining tasks requiring
physical Windows hands-on time (`T2`/`T4`/`T6`–`T8`).

### GW-P5 consolidated execution checkpoint (2026-08-26)

The GW-P5 execution directive is now the operative scope. T1 is
`CLOSED / PASS` from external Windows registration evidence plus human-captured
real logon and Mac Tailscale health evidence; the Windows JSON remains external
and is not fabricated in this repository. T3 retry lineage is
`CLOSED / PASS` offline (3/3 targeted tests). The repository now contains a
static Windows bundle regression test, an ASCII/mojibake guard, and the
resumable `gw_p5_hardening_verify_on_windows.ps1` (`PreReboot`/`PostReboot`, no
automatic reboot).
The bounded `scripts/gw_p5_worker_soak.py` harness is also ready; it accepts
only `--count 2` or `--count 10`, stops on first failure, and hard-caps the
normal GPU budget at 12 jobs.

T2 fail-fast mapping is `PASS` offline, but final timeout verification remains
pending real Windows GPU measurements. T4 reboot durability/cleanup and T5
2-job smoke + 10-job soak remain `HUMAN EXECUTION REQUIRED`; GW-P5 therefore
remains `IN PROGRESS`. Do not open GW-P6 until all 11 final requirements pass.

### GW-P5-T0 — Hardening readiness / entry-gate review (2026-08-25)

Reviewed all 8 GW-P5 tasks against existing repo infra. Result: 0/8 fully
done, 4/8 have reusable foundation from GW-P1–P4 (`probe_gpu_worker.py` +
`cached_worker_health.py` with 3-strike/5-min circuit breaker for health/
fail-fast; `error_mapper.py` for error mapping; VRAM failure-mode data
already captured in `GW_P4_CONTROLLED_A2_BENCHMARK_REPORT.md`), 4/8 not
started. Three tasks (Task Scheduler auto-start, reboot-safety, cleanup
script real-run) require physical Windows access and cannot be completed
from Mac. No code changed in this review; 0 network/GPU/provider calls.
**Correction:** initial review claimed real benchmark latency data existed
for timeout tuning (task #3) — checked, this is false. No `duration_seconds`/
`elapsed`/timing field exists anywhere in `artifacts/identity-restoration/`
or `staging/gw-p3/`. Timeout verification against real measured latency
needs an actual Windows GPU job and cannot be done from Mac either.

### GW-P5-T1 — Task Scheduler auto-start (prepared, not deployed) (2026-08-25)

Added `scripts/windows-gpu-worker/start_comfyui_worker.ps1` (launcher: reads
the GW-P1-verified `gw_p1_winning_config.json`/`worker.env` — does not
re-derive flags; refuses to start if bind address is not loopback),
`scripts/windows-gpu-worker/gw_p5_t1_register_autostart.ps1` (registers an
`AtLogOn` Scheduled Task, `Limited` run level, no elevation, no
network-exposure change; dry-run by default, `-Apply` to register), and
`gw_p5_t1_run_on_windows.ps1` (single entry point wrapping dry-run →
confirm → apply for Harry to run directly on the worker).

**2026-08-26 — registered on real hardware.** Harry ran
`gw_p5_t1_run_on_windows.ps1` on HARRY-ROG. Dry-run plan matched expectations;
`YES` confirmed; task `VenHoGPU-ComfyUI-AutoStart` registered successfully
(trigger `AtLogOn (Admin)`, no elevation, no network change). Evidence:
`C:\VenHoGPU\evidence\gw-p5-t1-20260826-092745\gw_p5_t1_report.json`.
The user-provided human capture also records a real logoff/logon cycle and a
Mac Tailscale probe returning `HEALTHY` with the GTX 1660 SUPER; this external
Windows JSON is referenced but not fabricated in the repo. T1 is therefore
`CLOSED / PASS`. Cosmetic-only console encoding remains non-blocking; the
repo bundle regression test rejects the known mojibake token (`â€`).

### GW-P5-T5 — Interrupted-job retry safety (verified offline) (2026-08-25)

Added `tests/identity_restoration/infrastructure/test_gw_p5_t5_interrupted_job_retry.py`
exercising the real (not fake) `FileConcurrencyLease` and
`JsonlRestorationLedger` implementations already in the codebase — the
crash path (`kill -9`/reboot, no `finally` ever runs) was previously
untested; only the clean-exception release path had coverage. Confirms: a
stale lock (older than `ttl_seconds`) is reclaimed by a new attempt (job
crash does not permanently deadlock retries); a live lock fails fast with
`ERR_GW_LEASE_UNAVAILABLE` (retryable) instead of hanging; two ledger
entries with different `attempt_id` for the same `run_id` both persist —
retry never overwrites the failed attempt. **3/3 new tests pass; full
`tests/identity_restoration` suite 160/160 pass, 0 regression.** 0 network/
GPU/provider calls. Task #5 DoD is satisfied by existing architecture plus
this new test coverage — no production code changed.

## AUTHORITATIVE CURRENT STATE — GW-P4-T2 PROVIDER_BLOCKED EVIDENCE FROZEN

GW-P0/P1/P2/P3 and GW-P4-T0 are CLOSED/PASS. GW-P4-T1 is CLOSED/QUALITY
FAIL. GW-P4-T2 is **PROVIDER_BLOCKED**; GW-P4 is **IN PROGRESS / QUALITY GATE
FAILED**; GW-P5 is **NOT STARTED**.

Run 6 remains authoritative: 30/30 terminal and decision-valid; Remote Face QC
median 91.335 PASS, Anatomy/Pixel/Lineage 10/10 PASS, Regional 2/10 PASS
(B01, B08), with Regional FAIL on B02/B03/B04/B05/B06/B07/B09/B10. The tuning
diagnosis is denoise-only: prior 0.35 over-reconstructed face texture; C1 is
0.30. C1/B03 and B04 artifacts have local evidence PASS, but C1 quality is
UNKNOWN and B04 was not validated. C2/C3 are untouched.

Both C1/B03 raw responses are frozen without JSON repair or inferred scores.
The 2048 attempt and the single 4096 recovery attempt both ended with
`MAX_TOKENS`, classified **T1 — FINISH_REASON_MAX_TOKENS** and
`PROVIDER_TRUNCATED_RESPONSE`. `PROVIDER_BLOCKED` is explicitly not
`PILOT_FAIL`; no C1 quality conclusion is claimable. No further provider,
GPU, Nano, B04, C2/C3, or GW-P5 activity is authorized in this freeze.

### GW-P4-T2B — Gemini output-budget containment audit (2026-08-25)

Offline data-flow, schema, request-composition, historical-output, and
authority-equivalence audit completed. Primary classification: **R5 — NO SAFE
OFFLINE REMEDIATION**. The minimal authority subset is known, but removing
narrative fields or duplicated prompt instructions would change the frozen
audit/prompt contract without proof of zero provider behavior drift. No code
semantics or output cap changed; `4096` remains locked. Verification: **37
passed**, compileall PASS, diff-check PASS; provider/network/GPU/Nano/paid-test
calls all `0`. GW-P4-T2 remains **PROVIDER_BLOCKED** and C1 remains **QUALITY
UNKNOWN**.

### GW-P4-T2C — Controlled Gemini output-cap recovery (2026-08-25)

The mandatory offline preflight passed: provider/model, samples, mock/fallback,
temperature, thinking configuration, rubric hash, structured schema hash, C1/B03
artifact hash, and A2 authority hash were unchanged. The only request change was
`max_output_tokens` **4096 → 8192**. One live Gemini request was then made for
C1/B03 Face-QC sample 1; no readiness probe, retry, B04, C2, or C3 call occurred.

Gemini returned `FinishReason.MAX_TOKENS`; raw output was 9,856 bytes and the
strict parser returned `Truncated JSON response`. Token evidence is input `5265`,
candidate output `7367`, cached/thinking/total unavailable. Valid authoritative
samples remain `0/3`. Classification is **PROVIDER_TRUNCATED_RESPONSE**; final
state remains **GW-P4-T2 = PROVIDER_BLOCKED**, not `PILOT_FAIL`, and C1 quality is
UNKNOWN. Evidence is frozen at
`artifacts/identity-restoration/benchmarks/gw-p4-t2c-output-cap-8192-recovery.json`.
GPU jobs `0`, Nano calls `0`, B04 not called, C2/C3 untouched, GW-P5 not started.

### GW-P4-T2D — Final provider blocker closure and roadmap freeze (2026-08-25)

The three authoritative C1/B03 transport attempts are frozen: `2048`, `4096`,
and `8192` all ended in `MAX_TOKENS`, with `0/3` valid Face-QC samples. The
8192 attempt is preserved with raw SHA256
`e332b982cdd71e5c83110a19b6ca3ca9b3b17b8e442f303a3f3abf304ba1f50e`. The final
classification is **GW-P4-T2 = PROVIDER_BLOCKED**. This is not `PILOT_FAIL`;
C1 quality remains **UNKNOWN**, so no authoritative Regional result or C1 pilot
result exists. The blocker is transport-only, not ComfyUI/GPU, Anatomy, Pixel
Preservation, or Lineage failure.

The repository has no separate `BLOCKED / QUALITY GATE UNRESOLVED` taxonomy, so
the existing GW-P4 status remains **IN PROGRESS / QUALITY GATE FAILED** with
`execution_blocker = GW-P4-T2 PROVIDER_BLOCKED`, `quality_result = UNRESOLVED`,
and `ROADMAP_EXECUTION = STOPPED_AT_GW_P4_PROVIDER_BLOCKER`. B04 is not
validated; C2/C3 remain untouched after the C1 blocker; GW-P5 is **NOT STARTED**.
No further roadmap execution is authorized under the locked validator contract.
Checkpoint: `artifacts/identity-restoration/benchmarks/gw-p4-final-provider-blocker-checkpoint.json`.

### GW-P4-T2 — Exploratory diagnosis checkpoint (2026-08-25)

### GW-P4-T2 — Staged Regional selection checkpoint (2026-08-25)

### GW-P4-T2 — C1 authoritative Face-QC gate (2026-08-25)

### GW-P4-T2 — Hardened C1 transport and provider circuit-breaker (2026-08-25)

### GW-P4-T2 — Evidence-producing provider probe (2026-08-25)

The separate live model-readiness HTTP probe was removed. Offline schema,
serialization, frozen provider/model, credentials, artifact SHA, local
evidence, cache, and budget checks passed. The first real C1/B03 Face-QC
request was therefore the readiness probe and sample 1. Gemini returned one
`Truncated JSON response`; it was persisted and classified as
`PROVIDER_TRUNCATED_RESPONSE`. No retry, sample 2, B04, Regional, C2/C3,
GPU, or Nano call was made. Calls attempted `1`, valid samples `0`, failed
provider calls `1`; paid test calls `0`. Status remains **GW-P4-T2 =
PROVIDER_BLOCKED**.

The production Face DTO now has a zero-network SDK serialization gate. The
exact root cause of the earlier local failure was Gemini SDK rejection of the
JSON-Schema `additionalProperties` keyword; the compatibility adapter removes
only that keyword and keeps the semantic DTO, rubric, thresholds, and
structured JSON output unchanged. The response ceiling is bounded at 2048
tokens. Focused transport/guard tests pass with no paid calls.

Provider readiness passed by HTTP model probe with `VALIDATOR_READY=true`,
Gemini `gemini-3.5-flash`, credentials available, samples `3`, mock=false,
fallback=false. The resumed C1-only batch started B03 and received one
`PROVIDER_503` (`UNAVAILABLE`) on its first sample. The circuit breaker
persisted the failure, marked provider availability `DEGRADED`, and stopped
the batch; B04 was not called. No valid Face-QC sample was obtained and no
Regional result or winner can be claimed. C2/C3, Image Validator, GPU, and
Nano remain untouched. Current status: **GW-P4-T2 = PROVIDER_BLOCKED**.

The authorized C1-only stage was started against exactly C1/B03 and C1/B04
after zero-cost artifact checks passed. No cache entry matched the candidate
SHA plus frozen Gemini configuration. The existing shared Gemini transport was
fixed to remove the SDK-unsupported `additionalProperties` schema keyword;
structured output and downstream DTO validation remain unchanged.

The production paid-call guard recorded three C1/B03 transport intents: one
SDK schema rejection before HTTP and two `503 UNAVAILABLE` responses from
Gemini. No valid Face-QC sample was parsed (`validatorSamples=0`), so neither
candidate reached three samples. The hard stage budget was not exceeded, but
the remaining three intents cannot complete both candidates; execution stopped
fail-closed. No Image Validator, RegionalScoreGateway, C2/C3, GPU, or Nano call
was made. No winner is selected. Status: **GW-P4-T2 = SCOPED BLOCKER — C1
Face-QC transport unavailable**; GW-P5 remains NOT STARTED.

The staged-selection task was resumed without new GPU work. The required
first stage is C1/B03 and C1/B04 only, but the current production
`RegionalScoreGateway` is an evidence adapter: it requires upstream
`Validator Studio` face/image reports for identity, eyes, and global scores.
There is no separate Regional-only Gemini producer in this repository.

Because this task explicitly requires `faceQcValidatorCalls=0`, evaluating
those two candidates through the existing producer would violate the cost
mode. Their existing local evidence remains valid (Pixel PASS, Anatomy PASS,
geometry C1/B03 `97.80`, C1/B04 `97.08`), but both semantic Regional results
remain `UNVALIDATED`; no winner can be selected and Group A must not start.

Staged calls made: `0` Regional, `0` Face-QC, `0` Nano, `0` paid test calls.
No additional GPU job was required. Current worker physical VRAM remains a
real `3433 MiB`/`DEGRADED` condition, but it is not the immediate blocker.
Status: **GW-P4-T2 = PILOT AWAITING REGIONAL DECISION**. GW-P4 remains
QUALITY GATE FAILED; GW-P5 remains NOT STARTED.

Task memory `GW-P4-T2` was resumed without reopening Run 6 validity. Offline
inspection of the immutable Remote artifacts identified the first pilot root
cause: B03/B04 geometry, mask boundary, crop transform, and pixel preservation
are healthy; the v2 `denoise=0.35` FaceID restoration over-reconstructs the
face, producing plastic/symmetrical/generic facial texture (B03 image global
score `40.0`, B04 `83.86`). The first bounded hypothesis is lower denoise;
mask/composite architecture remains unchanged.

No candidate workflow, benchmark output, Gemini Validator call, Nano call, or
GPU experiment was created. HARRY-ROG was reached through its HTTPS Tailscale
hostname; the required single `/free` recovery returned HTTP 200 but VRAM
remained about `617 MiB`, below the unchanged `4200 MiB` gate. Execution is
therefore paused before the first GPU job, fail-closed. Zero-cost verification:
focused tests `46 passed`, compileall passed, and `git diff --check` passed.

### GW-P4-T2 — GPU owner recovery gate (2026-08-25)

The worker remains below the frozen VRAM gate after the single permitted
`/free` call: approximately `607 MiB` before and `617 MiB` after. The available
ComfyUI HTTPS surface exposes `/system_stats` and `/free`, but no process/PID
or `nvidia-smi` data. SSH to HARRY-ROG was attempted with the existing host
identity and was rejected (`Permission denied (publickey,password,keyboard-interactive)`).

Primary classification: **V6 — UNKNOWN_WITH_EVIDENCE**. A duplicate/stale
ComfyUI process, another GPU application, unreleased ComfyUI cache, or driver
state cannot be distinguished without Windows-local `nvidia-smi` and process
inspection. No process was killed, no worker was restarted, no candidate
workflow was created, and no pilot GPU job was submitted. Status:
**GW-P4-T2 = RUNTIME_BLOCKED** pending the human-only Windows inspection and
safe recovery action. GW-P4 remains QUALITY GATE FAILED; GW-P5 NOT STARTED.

### GW-P4-T2 — Health metric fix and bounded pilot execution (2026-08-25)

Fixed WorkerHealth to gate on physical `devices[0].vram_free`; torch allocator
values are diagnostics only. Added healthy/low-physical regression fixtures and
inverse allocator-decoy coverage. Re-probe passed with GTX 1660 SUPER,
physical free `5065 MiB`, torch free `23 MiB`, threshold `4200 MiB`.

Created denoise-only v2 descendants C1=`0.30`, C2=`0.25`, C3=`0.20`, preserving
all other parameters/topology. Fixed candidate geometry binding after one
invalid C1/B03 attempt. The bounded cap consumed six GPU prompt attempts total:
one invalid binding attempt and five valid artifacts. Valid local evidence all
passed decode, Pixel Preservation, Anatomy preservation, geometry sanity, and
lineage: C1/B03 `97.80`, C1/B04 `97.08`, C2/B03 `97.44`, C2/B04 `97.72`,
C3/B03 `97.13`.

All valid outputs remained Regional `UNVALIDATED` for identity/eyes/global
because Gemini was forbidden during pilot tuning. No winner, Group-A expansion,
or B01/B08 preservation run was authorized. Gemini `0`, Nano `0`, paid tests
`0`. Focused tests `24 passed`; identity-restoration plus Action
Composite/regional suites `180 passed`; compileall and diff-check passed. After
cleanup physical VRAM was `3433 MiB` and worker DEGRADED, so no further GPU job
was submitted. **GW-P4-T2 = RUNTIME_BLOCKED** for continuation; GW-P4 remains
QUALITY GATE FAILED and GW-P5 NOT STARTED.

### GW-P4-T1 — Run 6 regional quality decision (2026-08-25)

**GW-P4-T1 = FAIL. GW-P4 = IN PROGRESS / QUALITY GATE FAILED. GW-P5 = NOT
STARTED.** Run 6 `benchmark-20260825T160000Z-gw-p4-t1` is the canonical
reuse-only consolidation of the complete existing evidence. Runs 1–5 remain
unchanged.

- Run 6 contains exactly 30/30 terminal and 30/30 decision-valid rows:
  Control 10/10, Nano 10/10, Remote 10/10.
- New paid work in this task: Nano generation `0`, Remote GPU jobs `0`,
  Validator calls `0`, paid calls during tests `0`.
- `validatorEvidenceComplete=true`; `missingValidatorSamples=0`; provider,
  model, samples, rubric, thresholds, and thinking configuration remain
  frozen.
- Regional policy is existing `RegionalGate` fail-closed evaluation per row;
  the Treatment aggregate is `all(10 row gates passed)`. Root classification
  is **RG2**: the aggregate policy existed, while the summary's Anatomy alias
  incorrectly mirrored the full Regional gate. Only that mapping was corrected.
- Treatment Regional evidence: PASS B01/B08; FAIL B02/B03/B04/B05/B06/B07/B09/B10.
  Anatomy is PASS for all 10 rows (`anatomyScore=100`); Pixel Preservation and
  Lineage are PASS for all 10 rows.
- Treatment Face QC median is `91.335` (threshold `>=90`, PASS), but the
  hard Regional gate fails. Final official result is **QUALITY_FAIL**.
- Remote B10 `Face QC=0.00` is a legitimate score from three valid samples,
  not a sentinel or stale value: the cache/raw evidence, output SHA, and
  Regional evidence agree, and the Validator recorded a real face-binary-gate
  failure caused by a severe face rendering glitch.
- No tuning, retry, regeneration, fallback, mock, cherry-picking, or GW-P5
  work was performed. Smallest next tuning target: the frozen Remote
  workflow's `global_composite` Regional failures, beginning with B02/B03/B04/
  B05/B07/B08/B09; B06 and B10 additionally have identity/eyes failures.

### GW-P4-T1 — Paid-call guardrails and missing Validator evidence (2026-08-25)

**Pre-run validity gate: OPEN.** Control, Nano, and Remote each have 10/10
decision-valid rows after offline RegionalScoreGateway materialization. No Run 6
was created in this cost-guard task; GW-P4 remains IN PROGRESS and GW-P5 is
NOT STARTED.

- Paid transport is fail-closed in tests and requires `VALIDATOR_LIVE_ENABLED=true` in production. The current recovery ledger capped new calls at 12 and recorded 11 attempts: 10 parsed samples succeeded and 1 initial `MAX_TOKENS`/malformed sample was retried once under the invalid-schema retry rule.
- Frozen Validator authority is unchanged: provider `gemini`, model `gemini-3.5-flash`, samples `3`, rubric/thresholds/thinking configuration unchanged. Structured JSON output is enabled with the existing Face/Image DTO schemas and an 8192 output ceiling.
- Historical audit recovered face samples for all four targets. New image samples were required only for Nano B02 (3), Nano B04 (3), Remote B06 (3), and Remote B08 (1); Remote B08's other two image samples were reused from raw history. No Nano generation or Remote GPU job was run.
- Regional evidence was materialized offline for 30 existing artifacts through the production `RegionalScoreGateway`; no numeric scores were fabricated. Quality-gate pass counts remain Control 2/10, Nano 0/10, Remote 2/10, so this is evidence-valid readiness, not an official quality decision.
- `paidCallsDuringTests=0`; no fallback or mock was used in the live recovery.

### GW-P4-T1 — Controlled A2 Benchmark Execution and Decision (2026-08-24)

**GW-P4-T1 = EXTERNAL BLOCKED / DECISION INELIGIBLE. GW-P4 = IN PROGRESS.** The
official contract is exactly three branches and 30 rows; `comfyui-local`
remains adapter/rollback only. Internal T1 orchestration is implemented:
composite dispatch, B01–B10 YuNet geometry/request contexts, Validator Studio
adapter, SHA/configuration cache, runner injection, row assembly, artifact
directories, summary and quality decision.

The Nano root cause was `EXPECTED_SERVICE_NOT_RUNNING`: `127.0.0.1:3000` is the
existing Venho OS Next.js service. It was recovered with canonical `npm run dev`
and zero-cost GET confirms provider/model/configuration with no fallback.

The first official attempt created run `benchmark-20260824T150014Z-94c8cb21`
with 30 terminal failures, but it is invalid infrastructure evidence: two
internal mapping bugs were fixed afterward (relative A2 path and dropped
`providerConfigured`). A corrected run
`benchmark-20260825T015837Z-7d0e4f0d` retained one successful real B01 Nano
output, but exposed the existing Venho OS route's B01-only authority check and
incomplete row persistence; the route now validates each case's authority and
row writes flush. That run is also retained as invalid infrastructure
evidence, not a quality result. The next official attempt is refused because
HARRY-ROG reports `DEGRADED` with 2.69 GiB free VRAM, below the existing
4200 MB health threshold. `/free` was then called with
`unload_models=true, free_memory=true`; HARRY-ROG recovered to 5067 MB free,
above the unchanged gate. New official run
`benchmark-20260825T021915Z-157c9b14` completed all 30 terminal rows: 10
completed and 20 failed. The row-level audit found 10 real Nano outputs, 5
real remote outputs, 10 validator failures, 5 remote VRAM failures, and 15
evidence-pipeline failures. Its historical remote median 91.85 used only
B05/B07/B09 (N=3), so the recorded `QUALITY_FAIL` is not eligible.

After internal classification/pixel-evidence/reuse fixes, validity run
`benchmark-20260825T030340Z-df1d875a` completed all 30 rows: 18 completed,
12 failed, `decision=INELIGIBLE`. Nano reused all 10 prior provider outputs
with zero new provider calls. Final counts are
`EVIDENCE_PIPELINE_FAIL=18`, `VALIDATOR_FAIL=8`,
`INFRA_EXECUTION_FAIL=4`, with zero valid quality rows. The remaining block is
external Validator Studio malformed JSON plus HARRY-ROG remaining below the
frozen 4200 MB gate after one `/free` attempt per case. No quality tuning,
retry, fallback, mock, or best-of-N was used.

### GW-P4-T0 — Controlled A2 Benchmark Freeze & Preflight (2026-08-24)

**GW-P4 = IN PROGRESS. GW-P4-T0 = FAIL/BLOCKED.** GW-P0, GW-P1, GW-P2 và
GW-P3 vẫn CLOSED/PASS; không có regression được chứng minh.

- [x] A2 authority resolved and hash verified:
  `venho-social-content-agent/assets/face-plates/A2_Front_plate.png` ·
  `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
- [x] Four v2.1 branches and same-input/pixel-lock invariants documented.
- [x] Face QC `samples=3` behavior verified in `validator_studio.face_validator`;
  benchmark must pass it explicitly because general config default remains 1.
- [x] Remote workflow ID/SHA and current restoration parameters frozen in
  `docs/identity-restoration/BENCHMARK_PROTOCOL.md`.
- [x] Protocol created without generation, tuning, paid calls, or promotion.
- [x] Dataset manifest and physical-source validation are present; B01–B10 are
  verified `FROZEN` with hash/dimension/provenance.
- [x] B05, B06, B07, and B08 each have one accepted real source frame with
  generation lineage; official dataset readiness is true. This does not run
  the official benchmark or imply Face QC success.
- [x] `benchmark_row.schema.json`: v2.1 metric/provenance fields are required
  and unknown properties remain rejected.
- [x] Benchmark CLI/runner implemented with structural validation, deterministic
  40-row planning, and fail-closed official execution gating.

Evidence/protocol: `docs/identity-restoration/BENCHMARK_PROTOCOL.md`.
No benchmark, Nano Banana generation, or paid Face QC sweep was executed.

### GW-P4-T0.1 — Benchmark Contract + Manifest Closure (2026-08-24)

**GW-P4-T0.1 = PASS.** GW-P4 remains **IN PROGRESS** and GW-P4-T0 remains
**FAIL/BLOCKED** because B05/B06/B07/B08 are not frozen.

- [x] Created authoritative `contracts/identity_restoration/benchmark_set.yaml`.
- [x] Preserved dataset readiness truthfully: B01/B02/B03/B04/B09/B10 are
  `FROZEN`; B05/B06/B07/B08 remain `MISSING`.
- [x] Frozen four branches, A2 SHA, remote workflow ID/SHA, seed `42`, and
  remote parameters.
- [x] Upgraded `benchmark_row.schema.json` to v2.1 with
  `additionalProperties: false`.
- [x] Added four valid branch fixtures and missing/unknown-property invalid
  fixtures.
- [x] Added fail-closed manifest readiness validation without implementing a
  benchmark runner.

No generation, network call, paid API, Face QC sweep, tuning, workflow change,
or architecture change was performed.

### GW-P4-T0.2 — Benchmark Runner / CLI (2026-08-24)

**GW-P4-T0.2 = PASS.** The runner consumes the authoritative benchmark
manifest/schema and uses an injected branch executor boundary; it does not
duplicate `ActionCompositePipeline` or call ComfyUI directly.

- `venho-restore benchmark validate` reports structural validity separately
  from `officialBenchmarkReady`.
- `venho-restore benchmark plan` emits exactly 40 deterministic rows (10 cases
  × 4 branches); with the current manifest all are non-executable.
- `venho-restore benchmark run` refuses before executor/composition-root
  creation until every case is `FROZEN`; no bypass flag exists.
- Future result writes are append-only under a unique run directory and each
  row is schema-validated; failed attempts are retained as explicit rows.
- Zero network, GPU, paid API, image generation, or live benchmark execution.

GW-P4-T0 remains **FAIL/BLOCKED** because physical branch/evidence executors
remain a later execution prerequisite.

### GW-P4-T0.4 — Generate & Freeze Missing B05–B08 Benchmark Sources (2026-08-24)

**GW-P4-T0.4 = PASS.** B05 Running Side, B06 Walking, B07 Sitting, and B08
Hair Motion were each generated exactly once through the existing approved
`venho-social-content-agent/generate_image.py` pipeline using the canonical A2
authority. Each accepted frame is `1024×1280`, has a verified SHA-256, and is
recorded in `contracts/identity_restoration/benchmark_set.yaml` with provider,
model, prompt lineage, A2 hash, artifact/run ID, attempt, and timestamp.

Acceptance was taxonomy/technical validity only: no IdentityRestorer, official
benchmark, paid Face QC, candidate ranking, workflow tuning, or branch executor
was run. Provider request IDs and deterministic source seeds were unavailable
from the existing pipeline and are explicitly recorded as unavailable; no
values were fabricated. The detailed lineage is in
`docs/identity-restoration/BENCHMARK_GENERATION_LINEAGE_V2_1.md`.

The dataset validator now reports all ten cases `FROZEN` and official dataset
readiness true. GW-P4-T0 remains **FAIL/BLOCKED** until the physical branch and
evidence executors are available. GW-P4 remains **IN PROGRESS**; do not mark
T0 or start GW-P4-T1 from this task.

### GW-P4-T0.5 — Physical Branch & Evidence Executor Readiness (2026-08-24)

**GW-P4-T0.5 = FAIL/BLOCKED. GW-P4-T0 remains FAIL/BLOCKED.** The zero-cost
`venho-restore benchmark preflight` now reports deterministic branch capability,
evidence-schema, workflow-authority, and official-execution readiness.

- `control`: READY through
  `identity_restoration.application.benchmark_executor.ControlBenchmarkExecutor`;
  it only verifies/references the frozen base bytes and performs no provider or
  GPU call.
- `comfyui-local`: NOT_READY. The existing
  `ComfyUILocalRestorer` is an `IdentityRestorerPort` adapter, not a benchmark
  executor/evidence writer; `IDR_COMFYUI_ENABLED=false` in this environment.
- `comfyui-remote`: NOT_READY. The pinned workflow SHA is verified, but no
  benchmark executor/evidence writer is wired and
  `IDR_COMFYUI_REMOTE_ENABLED=false`; no worker health/output smoke was run.
- `nano-banana-edit`: NOT_READY. No `IdentityRestorerPort` or benchmark
  executor is registered. The smallest fix is one adapter around the existing
  action-composite/Nano Banana path; no second pipeline was introduced.

The benchmark row schema now permits explicit output path/hash, executor
status/error, provider/request/run IDs, backend, and host evidence without
weakening `additionalProperties: false`. `benchmark run` refuses before run
directory creation unless both dataset and executor readiness are true.
No full benchmark, Face QC sweep, paid call, GPU/ComfyUI smoke, tuning, or
production promotion occurred.

### GW-P4-T0.5.1 — ComfyUI-Local Benchmark Executor + Evidence Writer (2026-08-24)

**GW-P4-T0.5.1 = PASS.** `ComfyUILocalBenchmarkExecutor` now wraps the
existing `RestoreFaceCropUseCase` and reaches the existing `IdentityRestorerPort`
without adding ComfyUI HTTP logic or a second pipeline. The injected request
factory preserves normal crop/mask/A2/cropTransform ownership; the executor
does not recrop or rebuild masks.

It fail-closes on base/A2/seed mismatch, request/result errors, missing or
undecodable outputs, missing hashes, missing workflow lineage, and missing
pixel-preservation evidence. It emits output path/hash, workflow lineage,
runtime/retry, backend/host, explicit null provider/request IDs, A2/crop/mask
lineage, and restored-crop path/hash.

Preflight reports `control=READY`, `comfyui-local=READY`, while
`comfyui-remote` and `nano-banana-edit` remain `NOT_READY`; therefore
`officialExecutionReady=false` and GW-P4-T0.5/T0 remain **FAIL/BLOCKED**.
No physical ComfyUI smoke was run because the local runtime is not enabled in
this environment; structural/mock-port tests prove the callable path without
paid/network execution.

### GW-P4-T0.5.2 — ComfyUI-Remote Benchmark Executor + Windows Evidence (2026-08-24)

**GW-P4-T0.5.2 = FAIL/BLOCKED.** Added
`ComfyUIRemoteBenchmarkExecutor` around the existing
`RestoreFaceCropUseCase` and `ComfyUIRemoteRestorer`/`IdentityRestorerPort`.
The benchmark layer adds no ComfyUI HTTP, upload, polling, download, recrop,
or second pipeline. Frozen remote workflow/parameter, A2, seed, crop/mask
geometry, output hash, byte-difference, and pixel-lock contracts fail closed.

Remote adapter execution metadata (`promptId`, output reference, remote host)
and existing worker-health metadata flow through restoration lineage when
available; unavailable GPU/VRAM values remain null. A real non-benchmark
Windows smoke evidence JSON is mandatory before remote reports READY. It was
not run from this Mac/repo environment because HARRY-ROG is unavailable;
therefore remote and Nano remain NOT_READY and `officialExecutionReady=false`.
No full benchmark, Face QC, paid call, tuning, or promotion occurred.

### GW-P4-T0.5.2a — Windows Physical Remote Smoke Evidence (2026-08-24)

**GW-P4-T0.5.2a = FAIL/BLOCKED.** The required pre-smoke health probe to
`http://127.0.0.1:8188/system_stats` failed with connection refused from the
Mac/repository environment. HARRY-ROG or its SSH/Tailscale tunnel is not
reachable, so no physical restoration, `/prompt` submission, output artifact,
or smoke evidence bundle was created. No manual ComfyUI submission or fake
evidence was used. T0.5.2 remains FAIL/BLOCKED pending one real Windows smoke.

### GW-P4-T0.5.2b — Restore HARRY-ROG ComfyUI Reachability (2026-08-24)

**GW-P4-T0.5.2b = FAIL/BLOCKED.** Mac-side read-only checks found the
`harry-rog` Tailscale peer reachable (`tailscale ping` succeeded), but no
listener on Mac `127.0.0.1:8188`; the direct peer request to
`100.71.167.98:8188/system_stats` timed out, and Mac reported no Tailscale
Serve configuration. HARRY-ROG local process/port/startup logs could not be
verified or changed from this environment. No `/prompt`, inference, or
benchmark artifact was created. This does not yet demonstrate a GW-P1 runtime
regression; the exact Windows-side root cause remains unresolved.

### GW-P4-T0.5.2a-RERUN — One B01 Physical Remote Smoke (2026-08-24)

**FAIL/BLOCKED before prompt submission.** Remote `/system_stats` returned
HTTP 200 from HARRY-ROG and confirmed ComfyUI `0.33.0`, frozen argv, and
`cuda:0 NVIDIA GeForce GTX 1660 SUPER`; B01, A2, and workflow SHA authorities
also matched. Execution was stopped fail-closed for two demonstrated blockers:
the current `ComfyUIRemoteBenchmarkExecutor` requires a pre-existing PASS smoke
evidence file before it will execute, making the first smoke circular, and the
worker reported only about 1,988 MiB free VRAM, below the frozen 4,200 MiB
health threshold. No `/prompt` was submitted, no output/evidence bundle was
created, and no executor or threshold change was made.

### GW-P4-T0.5.2d — Fix First-Smoke Circular Readiness Gate (2026-08-24)

**GW-P4-T0.5.2d = PASS.** Added the dedicated
`venho-restore benchmark smoke --branch comfyui-remote --case B01 --request ...`
path. It calls `ComfyUIRemoteBenchmarkExecutor.execute_bootstrap_smoke()`
exactly once, marks evidence `NON_BENCHMARK/PREFLIGHT`, and writes a dedicated
smoke manifest. Bootstrap does not require prior smoke evidence, but still
requires the frozen dataset/B01, A2/workflow/seed/parameter/geometry
contracts, registered remote port, and `WorkerHealthPort=HEALTHY` including the
existing VRAM gate.

The normal executor path still requires a validated PASS smoke manifest, and
`benchmark run` remains gated by `officialExecutionReady`; no `--force` or
direct HTTP bypass exists. This task did not run the physical smoke, so
`comfyui-remote` is not promoted to READY.

### GW-P4-T0.3 — B01–B10 Authoritative Dataset Freeze (2026-08-24)

**GW-P4-T0.3 = FAIL/BLOCKED.** Six existing source frames were independently
verified and frozen in `benchmark_set.yaml`: B01, B02, B03, B04, B09, B10.
The dataset validator checks file existence, decode integrity, SHA-256, and
dimensions, and rejects undocumented duplicate source paths.

B05 Running Side, B06 Walking, B07 Sitting, and B08 Hair Motion remain
`MISSING`; no arbitrary or Face-QC-selected substitute was promoted. The
dataset report is `docs/identity-restoration/BENCHMARK_DATASET_V2_1.md`.

No benchmark execution, paid API, live Face QC, generation, tuning, or
architecture change was performed. `officialBenchmarkReady=false`.

### GW-P3 Final Closure — corrected dual-mask Mac application path (2026-08-24)

**GW-P3 = CLOSED / PASS.**  **GW-P4 = IN PROGRESS (GW-P4-T0 BLOCKED).**

- One real `comfyui-remote` application-path execution completed after HEALTHY
  preflight (`5132 MB` free VRAM); no second prompt was submitted.
- Worker prompt: `be054dd8-da3e-4f54-acdc-4dadb5db99ca`; workflow
  `face_restore_win_sd15_ipadapter_v1`; workflow SHA-256
  `7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8`.
- Canonical A2 SHA-256:
  `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
- Crop-local mask sent to ComfyUI: `687×659`; full-canvas preservation mask:
  `1024×1280`; remote output: valid PNG `687×659`; final composite: valid PNG
  `1024×1280`.
- Remote output SHA-256:
  `517ed75962bbf8dea230863aaa8da6936fe0c576426b251d8f8ff73a4985fef0`.
  Final composite SHA-256:
  `e7c3c0dafc905bc3a165289a63d25cae84f312bb9f85ae5373ccbd3e68d1294d`.
- Byte-difference gate PASS; pixel preservation PASS with `0` changed pixels
  outside the permitted full-canvas restoration region.
- `mock_used=false`, `local_fallback=false`, `silent_fallback=false`.
- Evidence bundle:
  `staging/gw-p3/mac-final-20260824-dual-mask/evidence/`.
- The application result remains truthfully `NEEDS_REVIEW` because the CLI
  composition root has no `QcGatewayPort`; this does not fail the GW-P3 remote
  adapter/application-path gates recorded above.

### GW Plan v2.1 — GW-P1 verifier aggregation repair (2026-08-20)

**Status: CLOSED / PASS (2026-08-20).**
Evidence: `C:\VenHoGPU\evidence\gw-p1-20260820-210513` (Windows host, do Codex/Harry
tạo và xác nhận trực tiếp trên máy `HARRY-ROG` — phiên Mac này không có quyền truy
cập ổ đĩa Windows nên không tự verify được nội dung evidence, ghi nhận theo xác nhận
của Harry ngày 2026-08-20).

Runtime đã chốt (frozen):
- Host: `HARRY-ROG` · Windows 11 · GPU: GTX 1660 SUPER 6GB
- ComfyUI: `C:\VenHoGPU\comfyui` · Endpoint: `127.0.0.1:8188`
- Checkpoint: `v1-5-pruned-emaonly.safetensors` · Flags: `--lowvram --fp32-vae`

- [x] Xác định verifier source hiện tại: `scripts/windows-gpu-worker/gw_p1_verify.ps1`;
  runbook hỗ trợ cả `C:\VenHoGPU\windows-gpu-worker\` và
  `C:\VenHoGPU\scripts\windows-gpu-worker\` trên worker.
- [x] Sửa qualification predicate để dùng đúng contract `sd15_json.output.path` +
  filesystem existence; không còn yêu cầu field không tồn tại `output.exists`.
- [x] Giữ các điều kiện evidence-backed: `http_error=null`,
  `comfy_prompt_validation_error=false`, `cuda_runtime_exception=false`, 512×512,
  non-black và `pixel_std > 5`.
- [x] Cấu hình A vẫn là winner đầu tiên theo roadmap: `--lowvram --fp32-vae`.
- [x] Khi A qualify, verifier ghi `C:\VenHoGPU\worker.env` với flags hiệu lực và
  report `winning_config`/`selected_run`.
- [x] Windows verifier rerun hoàn tất trên `HARRY-ROG`; evidence tại
  `C:\VenHoGPU\evidence\gw-p1-20260820-210513`. GW-P1 PASS. GW-P2 đã mở tiếp theo.

### GW Plan v2.1 — GW-P2 Extract Port + GW-P3 Remote Adapter code (2026-08-20)

**Status: GW-P2 CLOSED/DONE · GW-P3 PARTIAL (phần mềm phía Mac xong, hạ tầng Windows chưa)**

Giao bởi Harry: "Phase 1 sẽ giao cho Codex làm tiếp. Tôi muốn bạn bắt đầu làm từ roadmap
phase 2 đến kết thúc." GW-P1 (Windows GPU Worker vật lý) không đụng tới, để Codex.

**GW-P2 — Extract Port: CLOSED.**
- `identity_restoration/` bounded context mới, đầy đủ domain/application/infrastructure/
  interface theo v2.0 PHẦN 10.1: 9 Port thuần, 1 use case trung tâm
  (`RestoreFaceCropUseCase`, thuật toán rút gọn từ PHẦN 7.3 cho crop-based contract),
  registry, DTO, Composition Root (`identity_restoration_module.py`) + `env.py`
  (nguồn duy nhất đọc `os.environ`), CLI `venho-restore run|health`
  (entrypoint `pyproject.toml`).
- 3 restorer: `mock` (deterministic, seed-keyed nudge, không network), `comfyui-local`
  (bọc `ComfyUIIdentityRestorer` hiện có — **0 dòng trong `image_studio_runtime/
  action_composite/` bị sửa**), `comfyui-remote` (GW-P3, xem dưới).
- 5 JSON Schema + 4 fixture pass/fail tại `contracts/identity_restoration/` (chuyển khỏi
  `contracts/` phẳng vì `test_growth_phase1_contracts.py` enumerate whitelist 17 schema
  Growth Phase 1 — schema GW không thuộc nhóm đó).
- **2 quyết định lệch có chủ đích khỏi patch v2.1 §GW-P2** (ưu tiên rủi ro=0 cho production
  path hơn đúng chữ patch): KHÔNG sửa `ProductionRunner` gọi qua `RestorerRegistry` (T4) —
  `identity_restoration/` hiện là con đường SONG SONG đã test đầy đủ nhưng CHƯA phải con
  đường `ActionCompositePipeline` thật đang gọi; KHÔNG di chuyển vật lý domain logic ra
  khỏi `action_composite/` (T6) — thay vào đó `domain/policies/pixel_preservation.py`
  IMPORT trực tiếp hàm thuần `action_composite.regression_guard.protected_region`.
  **Hợp nhất 2 con đường này là quyết định kiến trúc cần Harry chốt, chưa tự làm.**
- 53 test mới trong `tests/identity_restoration/`, 100% pass, 0 network call (recorded
  fixture / monkeypatch `urlopen`). Bao gồm đủ 9 test bắt buộc PHẦN 12.3 (single provider
  call, lease released on exception, cancel before spend, pixel lock gate, upload
  server-returned-name, graph binder survives renumbering, manifest additive, `is_official`
  luôn raise).
- 0 regression: suite cũ 951/70 (baseline GW-P0) → nay 1005 pass / 69 fail — **69 fail y
  hệt danh sách lỗi baseline cũ** (missing DNA fixture, subject-resolver schema mismatch,
  không liên quan `identity_restoration`); `test_action_composite*.py` +
  `test_gw_p0_t2_golden.py` 50/50 pass nguyên trạng.
- `venho-restore run --restorer mock` smoke-tested thủ công end-to-end (không phải trong
  pytest) — output JSON đúng shape `restoration_result.schema.json`.

**GW-P3 — Remote Adapter: PARTIAL, chưa CLOSED.**
- Xong + test offline: `node_registry.py` (NODE_TITLES/WORKFLOWS, cưỡng chế bằng
  `test_no_comfyui_string_leakage.py`), `http_client.py` (upload namespaced đọc `name` từ
  response — GW-E9, poll backoff 2s×1.5 trần 10s, download, interrupt), `graph_binder.py`
  (bind theo `_meta.title`, sống sót renumbering), `error_mapper.py` (phủ bảng §8.5),
  `cached_worker_health.py` (tái dùng từ GW-P2, TTL + circuit breaker 3-lần→mở mạch 300s),
  `ComfyUIRemoteRestorer` (implements cùng Port với `ComfyUILocalRestorer`),
  `scripts/deploy_workflows_to_worker.py` (verify SHA-256 trước/sau copy),
  `scripts/probe_gpu_worker.py` (health CLI một phát).
- 7 fixture `contracts/identity_restoration/fixtures/comfyui/` — **soạn tay theo tài liệu
  ComfyUI API, KHÔNG PHẢI ghi lại từ lần chạy thật.** Phải thay bằng bản ghi thật ở T9 khi
  có worker.
- **CHƯA làm được (cần máy Windows + Tailscale + ComfyUI thật, ngoài khả năng sandbox
  này):** Tailscale probe từ Mac (T2), tác giả workflow SD1.5+IPAdapter FaceID + pin
  SHA-256 (T10), một crop Linh An thật đi hết chuỗi (T12). Đây là bàn giao rõ ràng cho
  GW-P1 (Codex/Harry), không phải việc bỏ sót.
- Chi tiết đầy đủ từng task T1–T12: `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`
  PHẦN 4 "GW-P3 — Remote Adapter".

### GW Plan v2.1 — GW-P3 blocker patch (2026-08-21)

**Status: 4 blocker đã sửa, GW-P3 VẪN OPEN/PARTIAL — chưa live-validate, chưa được đóng.**

- [x] **FACT 1 — golden-master archive bị mutate:** commit `81bd38e` chèn khoá
  `"_roadmap_status": "SUPERSEDED ..."` vào `workflows/_archive/face_restore_v1_api.json`,
  đổi sha256 từ `b232b18d...f9c3e25` (pin gốc) sang `f7d04802...67dde323`. Đã khôi phục
  byte-for-byte từ `git show eac1b05:config/comfyui/face_restore_v1_api.json`; sha256 khớp
  lại pin trong `workflow_pins.yaml` (không sửa file pin). `tests/test_gw_p0_t2_golden.py`
  2/2 PASS.
- [x] **FACT 2 — `venho-restore health` nạp workflow suy luận trước khi probe:** tách
  `build_worker_health(env)` ra khỏi `build_identity_restoration_module()` trong
  `identity_restoration/infrastructure/composition/identity_restoration_module.py` — hàm
  mới chỉ đọc env, không đụng `FileWorkflowRepository`/workflow JSON. `interface/cli.py`
  (lệnh `health`) và `scripts/probe_gpu_worker.py` gọi thẳng `build_worker_health()`.
  Verify thủ công: `IDR_COMFYUI_ENABLED=true IDR_COMFYUI_BASE_URL=http://127.0.0.1:1
  IDR_COMFYUI_TIMEOUT_SECONDS=1 venho-restore health` → trả `OFFLINE` thật (network call
  thật, không crash vì thiếu workflow file).
- [x] **FACT 3 — `comfyui-remote` có code nhưng chưa wire vào composition root:** thêm
  `_try_load_remote_restorer()` trong cùng file composition root (không tạo root thứ hai),
  đăng ký `restorers["comfyui-remote"]` khi `IDR_COMFYUI_REMOTE_ENABLED=true` **và**
  workflow `face_restore_win_sd15_ipadapter_v1` đã authored+pinned. Fail-soft có chủ đích:
  vì workflow này CHƯA tồn tại trong repo (sha256 pin vẫn là placeholder `<điền ở GW-P3>`),
  bật cờ env hôm nay vẫn chỉ cho registry = `{mock}` hoặc `{mock, comfyui-local}` — không
  crash, không đăng ký giả. Env mới trong `env.py`: `IDR_COMFYUI_REMOTE_ENABLED`,
  `IDR_COMFYUI_REMOTE_BASE_URL`, `IDR_COMFYUI_REMOTE_TIMEOUT_SECONDS` (tách khỏi
  `IDR_COMFYUI_*` của comfyui-local/health để 2 backend không dùng chung base_url).
- [x] **FACT 4 — thiếu dependency `numpy`:** `identity_restoration/domain/policies/
  pixel_preservation.py` import `numpy` nhưng `pyproject.toml` chưa khai; thêm
  `numpy>=1.24` vào `[project].dependencies`.
- [x] Regression: `tests/identity_restoration` 53/53 PASS · `tests/test_gw_p0_t2_golden.py`
  2/2 PASS (golden master không đổi) · `tests/test_action_composite*.py` 48/48 PASS ·
  full suite **1005 pass / 69 fail** — khớp baseline pre-existing trong dòng "Cập nhật"
  phía trên, không đổi · `git diff --check` PASS · 0 network call trong pytest (suite chạy
  10.7s, không treo — health/remote-restorer thật chỉ gọi network khi chạy CLI/script trực
  tiếp ngoài pytest).
- **Env vars cần cho lần probe health thật tiếp theo (GW-P3, qua Tailscale khi Mac đã
  cài):** `IDR_COMFYUI_ENABLED=true` + `IDR_COMFYUI_BASE_URL=http://<tailscale-ip-hoặc-MagicDNS
  của HARRY-ROG>:8188`. Không cần bật `IDR_COMFYUI_REMOTE_ENABLED` cho việc probe health —
  cờ đó chỉ liên quan tới đăng ký restorer `comfyui-remote` để CHẠY inference thật, việc vẫn
  đang bị chặn vì workflow SD1.5+IPAdapter FaceID chưa được author+pin (T10, chưa làm trong
  patch này — ngoài phạm vi, không tự tạo workflow giả).
- Không đổi: `ActionCompositePipeline`, `ProductionRunner`, QC threshold, Golden Master
  pin, `action_composite/`, `workflow_pins.yaml`. GW-P3 vẫn OPEN — patch này chỉ dọn 4
  blocker repo-level, KHÔNG chạy inference thật, KHÔNG đóng GW-P3.

### GW Plan v2.1 — GW-P0 Baseline Freeze (2026-08-19)

**Status: CLOSED/PASS — GW-P0 Baseline Freeze complete**

- [x] GW-P0-T0 baseline probe PASS/CLOSED, Python + OS test baseline ghi nhận (951 Python / 400 OS, chi tiết ở patch doc PHẦN 4).
- [x] **A2-FRONT SHA-256 pinned:** `config/projects/venho_hotel/identity_restoration/workflow_pins.yaml` (mới) — `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d` cho `venho-social-content-agent/assets/face-plates/A2_Front_plate.png`, verify bằng `shasum -a 256` khớp `identity_reference_sha256` cả 3 case trong `tests/identity_restoration/golden/index.json`. Kèm pin `face_restore_v1_api.json` (SUPERSEDED) và placeholder workflow SD1.5 cho GW-P3.
- [x] GW-P0-T1 — Coupling Audit reconstructed/read-only tại
  `docs/identity-restoration/COUPLING_AUDIT_2026-08-18.md`; không sửa production code.
- [x] GW-P0-T2 — Golden-master test cho pipeline hiện tại: 3 case authoritative và offline regression đã PASS/CLOSED.
- [x] GW-P0 — Current Python + OS test baseline đã ghi nhận trong patch doc.
- [x] GW-P0 — Nano Banana masked-edit Face QC baseline `88.1 / revise` đã ghi nhận trong patch doc.
- [x] v1.0 SUPERSEDED marking: `config/comfyui/face_restore_v1_api.json` đã có marker; nội dung lịch sử giữ nguyên.
- [x] Di chuyển `face_restore_v1_api.json` → `workflows/_archive/` nguyên vẹn; giữ SHA-256 và lineage.
- [x] Viết đúng 8 ADR: `docs/identity-restoration/ADR-GW-001.md` … `ADR-GW-008.md`.
- [x] GW-P0 phase closure audit: all baseline artifacts traceable; Golden Master offline `2 passed`.

Chi tiết đầy đủ + rationale: `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` PHẦN 4/7.

### Action Composite v2.1 — staged identity finishing (2026-08-13)

**Status: v2.1.1 CROP PIPELINE COMPLETE OFFLINE — one controlled live face benchmark pending**

- [x] Phase A: khóa A2-FRONT là identity authority duy nhất; ghi SHA-256 vào job/manifest và từ chối hash mismatch.
- [x] Phase A: thêm hierarchical masks `core/shape/boundary`, crop context 2.5x và metadata mask version.
- [x] Phase B: ComfyUI adapter nhận normalized face crop + crop mask, phục hồi local rồi composite ngược vào canvas gốc; pixel ngoài vùng sửa được regression-guard.
- [x] Phase C: thêm `SceneCandidate`/`CandidateSelector` không dùng face score để chọn scene, `RegionalGate` fail-closed cho identity/eyes/geometry/anatomy/outfit/environment/global, và `WorkflowLedger`.
- [x] Phase D: ProductionRunner truyền regional scores; manifest ghi contract `action_composite_v2.1`, identity authority, mask và regional gate.
- [x] Phase E offline: action-composite tests mới **23/23 pass**; toàn nhóm action-composite **51/52 pass**, 1 failure là assertion cũ trong `test_action_composite_config.py` không còn phù hợp với workflow fixture hiện hữu.
- [x] Không có paid image/API call; chưa promote asset hay thay đổi A2 authoritative reference.
- [ ] Live POC ComfyUI/IPAdapter/InstantID và mini benchmark 3–10 ảnh chưa chạy vì cần worker GPU/provider thực tế; không đánh dấu Face QC >90 khi chưa có validator output.
- [x] Nano Banana masked-edit provider contract đã được triển khai ở Venho OS: `base` + `mask` + A2-front, image-first mapper, fail-closed preflight; không tạo client Gemini song song trong AI Studio.
- [x] Live masked-edit Nano Banana đã chạy và có artifact/validator output; kết quả chưa vượt 90.
- [x] Live verification đã chạy 2 lần Nano Banana 1K (`masked-edit`), chi phí ước tính tổng **$0.14112**; Face 88.2 và 88.1, cả hai `NEEDS REVIEW`, chưa đạt >90.
- [x] Live run phát hiện composite giữ sai kích thước provider output; đã sửa route dùng kích thước base canvas làm chuẩn. Cần test paid tiếp theo nếu muốn xác nhận pixel-lock sau bản sửa.
- [x] Debug tiếp xác nhận face mask chỉ chiếm 3.99% full canvas; đây là nguyên nhân provider không có đủ effective pixels để vượt plateau 88.x.
- [x] Venho OS v2.1.1 chuyển bước B thành mask-derived square crop: crop 454×454 hiện tại → upscale 1024×1024 → Nano Banana edit với duy nhất A2-FRONT → composite về đúng tọa độ trên base.
- [x] Output composite dùng PNG; test khóa pixel ngoài mask. Manifest ghi crop transform/mask coverage. Prompt ưu tiên mắt/lông mày trước các vùng nhận dạng khác.
- [x] QA offline: image-generation 140/140, full Venho OS 384/384, TypeScript/lint/build pass; không phát sinh paid call v2.1.1.
- [x] Live verification v2.1.1: `run-202608132052`, Nano Banana 1K, estimated **$0.07056**, output 1024×1280, Face **88.1 / revise**; crop/composite contract hoạt động đúng, không retry.
- [ ] Face QC >90 vẫn chưa đạt; blocker còn lại là identity/eye geometry synthesis của Nano Banana, không phải mất pixel ngoài mask.

### Growth Agent — republish Wednesday bằng DNA phòng mới (2026-08-12)

**Status: PARTIAL — Instagram đã đăng; Facebook bị chặn an toàn do Make receipt sai**

- [x] Tích hợp DNA mới cho Lake View Room 1/2 vào room rotation và content bridge.
- [x] Tạo lại bài Wednesday theo room DNA; Instagram receipt hợp lệ: `17926512171404301`.
- [x] Không ghi nhận Facebook giả thành công; M07 giữ `GATEWAY_ERROR` vì Make trả placeholder/thiếu post ID thật.
- [x] Ghi lại baseline DNA và thay đổi validator trong task memory/status.
- [!] Make cần trả Facebook post ID thật trong Webhook Response; nếu không, lịch publish tiếp theo tiếp tục fail-closed.

### Image Generation — A2 diagnostic V4 / cost review (2026-08-12)

**Status: CLOSED — Face QC đạt ngưỡng; candidate đã lưu; chưa đổi authoritative reference**

- [x] A2-front giữ làm reference chính thức. Diagnostic close-up 1K V4 đạt **93.15 / APPROVED** (shape 95, eyes/brows 90, nose 92, mouth/chin 93, technical 98).
- [x] Artifact + manifest: `photos-ai/2026/12-08-linh-an-a2-diagnostic-v4-1k/run-202608121115/variant-001/`; estimated cost **$0.06832**, không retry.
- [x] Lưu candidate: `venho-social-content-agent/assets/face-plates/candidates/A2_Diagnostic_V4_1K_candidate.png` (không promote, không publish).
- [x] Ghi nhận lựa chọn rẻ hơn Nano Banana để benchmark: Imagen 4 Fast/Standard/Ultra khoảng **$0.02/$0.04/$0.06**; GPT Image 1 Mini High khoảng **$0.036 output 1K + input-image tokens nếu có**.
- [ ] Chưa benchmark provider thay thế; cần ủy quyền paid test riêng. Nano Banana V4 vẫn là baseline identity đã chứng minh.
- [x] Task đóng. Không có paid image call sau V4.

### Growth Agent — automation recovery (2026-08-10)

**Status: DEPLOYED; batch approval queue is being regenerated**

- [x] Weekly Cycle fail-closed: thiếu ngày/platform FB/IG không thể được ghi `SUCCEEDED`; retry dùng idempotency v2 (`e5a5e30`).
- [x] DNA cần thiết cho Growth CI đã được track trong repo (`f63d11e`).
- [x] VENHO OS registry sync chọn `updated_at` mới nhất, không còn local ghi đè CI scheduler (`venho-os@0d06281`).
- [x] Publish Scheduler chạy 09:00 ICT T2/T4/T6/T7, có Make preflight và chặn slot trễ quá 30 phút (`355a25f`).
- [!] Rollout giữ `shadow`; không dùng `--allow-shadow`, không có publish thật trong đợt recovery.

### Google Gemini Image Provider option (2026-08-10)

**Status: READY FOR IMPLEMENTATION — documentation only; no Gemini API call, no official asset approval**

- [x] Handoff document: `venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md`.
- [x] Direction: Gemini API provider adapter (not manual Google Flow), retain immutable artifacts/manifests and use existing Validator Studio unchanged.
- [ ] Implement Gemini Flash/Pro generation selection in Venho OS with server-only credential, provider/model/cost trace in manifest and regression tests.
- [ ] Run a paid 6-scenario benchmark only with explicit authorization. Bước 5 remains blocked: current live Face QC 84.03–88.8 < official `>=90`; no asset may be promoted.

### Linh An official-asset readiness — Steps 1–3 (2026-08-10)

**Status: DONE — code/configuration readiness only; no paid image generation or official asset approval**

- [x] Identity/action lanes are now explicit at the Venho OS generation boundary. Static poses may use the approved standing face reference; dynamic poses (including running, cycling, sitting, jumping, dancing, swimming, and climbing) force text-to-image so the standing reference cannot corrupt body geometry.
- [x] Generation manifests now preserve `generationLane`, effective reference mode, exact submitted prompt, server-added prompt, scenario/outfit/action protocol, DNA version, and validator result for reproducible review.
- [x] `linh_an_generation_protocol_v1` is appended server-side after any editable user prompt. It keeps the scenario lock, selected wardrobe, actor requirement, and lane/reference policy at the spend boundary.
- [x] Validator CLI supports `--output-root`; CLI tests now write reports into `tmp_path` instead of the live `data/projects/venho_hotel/validation/` store.
- [x] Verify: AI Studio `/usr/bin/python3 -m pytest -q` → **841/841 pass**. Venho OS `npm test -- --run` → **191/191 pass**; `npx tsc --noEmit` and `npm run build` pass.
- [ ] No current live Linh An generation has passed the ≥90 face-QC approval threshold. Steps 4–5 live generation/QC ran, but Face results remain 84.03–88.8; do not classify existing `revise`/`usable` artifacts as official assets.
- [!] `npm run lint` remains blocked only by two pre-existing errors in `venho-os/design_handoff_venho_os_cockpit/support.js`; no changed Linh An file is implicated.

### FORBIDDEN hygiene + face gate (2026-08-07)

- [x] `knowledge_studio/vision/forbidden_policy.py` — chỉ câu phủ định mới là FORBIDDEN; sanitize ở `pass2_consolidate` và `overlay_merge`.
- [x] `validator_studio/observe_adapter.py` — validator chỉ dùng rule `curated`; fallback sang `observed` nếu subject không có rule curated nào.
- [x] `venho vision clean-forbidden` — dọn 21 mục rác trên 4 subject (dry-run mặc định, `--apply` mới ghi). 4 mục của `linh_an` được migrate sang overlay curated trước khi xoá.
- [x] `prompts/observe_face_against_dna.md` — `identity_structure` không xét tóc/biểu cảm. Master face 0.0 → 88.26.
- [x] Overlay scenario `outside.venho_rooftop_terrace_2026.overrides.yaml` — nới `street_trees_visible`, `sky_condition`, `lighting_condition` cho rooftop.
- [x] Siết instruction `forbidden_hints` trong `observe_universal.md` / `observe_face.md` / `observe_linh_an.md` (`prompt_version` lấy từ config nên không kích hoạt regenerate).
- [x] Verify: `/usr/bin/python3 -m pytest -q` → **841/841 pass**, 0 API call. Ảnh rooftop thật validate lại sau khi dọn DNA: **100/approve**, prompt validate 3056 → 2303 token.

### DoD 11/24/25/26 follow-up (2026-08-07)

- [x] **DoD #11:** thêm GitHub Actions `growth-blog-seo.yml`, chạy thứ 3 08:00 ICT, chỉ sinh và commit blog draft từ R3 facts; không có dispatch/publish path.
- [x] **DoD #24 — mechanism:** re-verified `shared/backup/growth_backup.py` từ commit `b7409a3`: online SQLite snapshot, artifact CAS, checksum + `PRAGMA integrity_check` restore, CLI `venho-growth backup`/`backup-verify`, giữ 30 snapshot. Trạng thái DR chỉ đạt khi `VENHO_BACKUP_DIR` trỏ tới storage ngoài máy và có lịch chạy thật.
- [ ] **DoD #25:** không có code gap ở phía Growth (UTM, attribution CLI, store đã có). Còn thiếu source event production: GA4 Data API credential hoặc booking-form event feed. Không tự sửa repo website đang dirty hay bịa credentials.
- [ ] **DoD #26:** scorecard/rollout code đã có; golden set reviewer-scored và 3 signal Vision QC thật không thể tạo bằng code. Rollout giữ `shadow` đến khi có data đạt gate.
- [x] Verify: `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **835/835 pass**, 0 API call.

### Audit closeout — Research OS/Trend Radar (2026-08-07)

**Status: CLOSED**

- [x] Architecture boundary clean: Research chỉ R0/R2 + `pending_approval`; M04 không viết content; M10 không có DB riêng; publish giữ tại M07 sau human approval.
- [x] Studio: `834/834` pass, 0 API call. VenHo OS: `150/150` pass; `npx tsc --noEmit` pass.
- [x] Đã dọn cache/log/tmp không track; không đụng docs/config/data JSON.

### Research OS chạy thật lần đầu + Trend Radar lọc ngày cũ (2026-08-06 → 07)

**Status: DONE — commit `f6599a0`, đã push**

Arc từ `8b36845` → `f6599a0`. Điểm chung mọi lỗi: mỗi lớp đều trả về "một cái gì đó" nên không lớp nào trông hỏng.

- [x] **Chu kỳ nghiên cứu tự động** — `run_research_cycle`: `queries:` → Tavily Search, `urls:` → `tavily_extract`; ra R0 note + R2 synthesis trong vault + proposal `pending_approval`. DoD #13 nguyên vẹn (không auto-promote R2→R3).
- [x] **Đường URL đích danh sửa 3 lỗi chồng nhau** (trước đó chưa từng thật sự hoạt động): `extract_depth` `basic`→`advanced` (Agoda trả `Failed to fetch url`); `strip_markdown_noise()` trước khi cắt + cap 6000→32000 (60–75% ký tự là cú pháp link/ảnh, 6000 đầu chỉ là nav chrome); `per_source=True` + `_MAX_SNIPPET_CHARS_PER_SOURCE=30000` (1200 cắt lần hai trước khi Gemini nhìn thấy — điểm của An Homestay ở ký tự 859 lọt, của Lake View ở 24985 không bao giờ).
- [x] **URL giữ nguyên xi** — Agoda `/vi-vn/` chạy trang này hỏng trang kia; Booking cần `.vi.html` cho Ven Hồ nhưng `.en-us.html` cho An Homestay. YAML ghi rõ "do not normalise them".
- [x] **Domain mới `competitor_rating`** — trang OTA có điểm nhưng không bao giờ có giá (render client-side theo ngày), một domain không trả lời được cả hai câu. `competitor` giữ câu hỏi giá + search; `competitor_rating` giữ 4 URL đối thủ. `ResearchDomain` + `domains.yaml` (biweekly/90d) cập nhật theo.
- [x] **`is_same_finding()` — dedupe không phụ thuộc tên** (`(domain, source_uri, value)` + tập token `fact_key` là tập con của nhau, sau khi bỏ `_KEY_NOISE`). Gemini đặt tên cùng một con số khác nhau mỗi lần. Có guard cho tập rỗng: `overall_rating` rút hết token thì không được nuốt mọi thứ.
- [x] **Nút "Từ chối" trên Trend Radar** — `TrendCandidateStore.reject()` + CLI `venho-growth trend-reject` + route `api/v1/studio/growth/trend-candidates/reject` (venho-os). Ghi tombstone, **không xoá dòng** — `merge_new` dedupe theo id nên dòng xoá thật sẽ quay lại lần quét sau. Panel cũng ẩn 17 candidate brand-safety đã tự loại.
- [x] **Lọc ngày cũ áp vào `scan_trends`** — gốc rễ ở bộ đọc ngày, không ở chỗ nối dây: dạng tiếng Việt thật không có năm (`ngày 26-28/6`) hoặc viết chữ (`17 Tháng Mười Một 2021`) đều không khớp gì. Thêm 4 pattern; `dd/mm` trần bắt buộc có chữ "ngày" (không thì `8/10` trong đoạn review thành ngày); ngày thiếu năm quy về năm gần hôm nay nhất; tháng trần vẫn là mùa. Trên 24 bài chờ thật: bắt 3, giữ 21 bài không hạn dùng.
- [x] Verify: `PYTHONPATH=. pytest -q` → 834/834 pass, 0 API call. `npx tsc --noEmit` sạch bên `venho-os`.

**Xung đột đã xử lý:** backfill 3 dòng cũ chạy đúng lúc Harry duyệt trên dashboard một bài mà nó vừa loại (Lễ hội Sen đã kết thúc) → rebase xong **khôi phục approval của Harry**. Quyết định của người thắng bộ lọc tự động, không phải ngược lại.

**Giới hạn thật:** bài không ghi ngày nào trong nội dung ("cuối tuần này ghé hồ Tây…") thì bộ lọc ngày bó tay — vẫn cần mắt người ở khâu duyệt.

Chi tiết đầy đủ: `task_memory.md` mục 14o.

---

### Growth Agent v3.1 — Scenario Make riêng + cổng `shadow` chặn thật + dọn 12 row kẹt (2026-08-06, chiều)

**Status: DONE — Growth đã có đường ra Make riêng, chạy thật, nhưng cổng rollout đang giữ mọi bài lại**

Tiếp nối việc tách webhook + ảnh fallback cùng ngày. Harry thao tác trực tiếp trên Make, Claude sửa code + hướng dẫn.

- [x] **Scenario Make riêng cho Growth — verify chạy thật.** Webhook `hook.us2.make.com/jw62ij…` (đã điền `MAKE_GROWTH_WEBHOOK_URL` trong `.env.local`). Clone scenario legacy, giữ 5 module, đổi mapping sang schema Growth: HTTP URL `{{2.image_url}}`, FB Post caption + IG Caption `{{2.content.text}}`, filter router đổi từ `publish_to_facebook`/`publish_to_instagram` sang `{{2.platform}}` = `facebook`/`instagram`, thêm chốt AND `{{2.publication_id}}` **Does not contain** `test` trên cả 2 nhánh.
- [x] **Lỗi `BundleValidationError: url` đã hết** — module `HTTP - Download a file` tải được ảnh fallback từ `venhohotel.com`, verify bằng execution thật.
- [x] **Cổng rollout stage.** `shadow` giờ chặn thật trong `_dispatch_claimed()`: không gọi webhook, row đậu ở status mới `SHADOW_HELD` (vẫn ghi approval + snapshot, vẫn hiện trong `list_pending`). Fail closed khi state file hỏng. Thoát cổng: `venho-rollout rollout-advance` rồi `retry_dispatch`, hoặc `venho-growth approve-and-dispatch --allow-shadow` (ghi `shadow_override_by` lên row).
- [x] **12 row `GATEWAY_ACCEPTED` sai từ 2026-08-04 → `GATEWAY_ERROR`** kèm `gateway_error` ghi rõ nguyên nhân; gửi lại được qua `retry_dispatch`.
- [x] Verify: `PYTHONPATH=. pytest -q` → 744/744 pass (+5 test cổng shadow, +6 test cũ seed stage qua helper `_past_shadow`), 0 API call.

**Sự cố cần nhớ:** 4 bài test đã đăng nhầm lên Facebook/Instagram thật trong lúc dò scenario (đã xoá). Nguyên nhân: (1) suy đoán logic filter của scenario legacy thay vì mở ra đọc; (2) sửa filter nhưng chưa bấm Save của **scenario** (nút 💾 dưới đáy canvas, khác Save trong panel filter) nên bản đang chạy vẫn là bản cũ. Phiên bản Make hiện tại không có mục Disable module trong menu chuột phải → không thể tắt module đích khi test.

**Chưa kiểm được:** bundle `platform: "facebook"` thật có vào đúng nhánh FB không — không thể kiểm mà không đăng thật. Lần đăng đầu nên là bài Growth Harry duyệt có chủ ý, chạy `--allow-shadow`.

Chi tiết đầy đủ: `task_memory.md` mục 14n.

---

### Growth Agent v3.1 — Phase 8 Rollout + Productize: venho-rollout CLI + scorecard thật + fix .gitignore skills (2026-08-06)

**Status: DONE — toàn bộ roadmap 0→8 hoàn thành theo cơ chế — commit local, chờ Harry xác nhận trước khi push**

Tiếp nối Phase 7 cùng phiên, theo yêu cầu "hoàn thành tất cả để đưa vào vận hành thật". Audit `controlled_rollout/`+`productize/` (Codex build 2026-08-03) — cùng lỗ hổng như mọi phase trước: code+test đầy đủ, 0 caller thật, không CLI.

- [x] `daily_cycle.py::_scorecard_signals()` (mới) — trích claim kill-switch + content_validator brand_fit thật từ `package["validation"]`, persist lên mỗi registry row qua `scorecard_signals` field (trước đây dữ liệu này bị vứt ngay sau khi hash hoá vào `validation_snapshot_id`).
- [x] `SlotStore.list_all(status=...)` (mới) — đọc tất cả slot MISSED trong toàn bộ lịch sử, không chỉ tuần hiện tại.
- [x] `controlled_rollout/collect_real_scorecard_metrics.py` (mới) — join thật `PublicationRegistry`+`SlotStore` thành golden-set shape cho `evaluate_golden_set()`. Chấm được 6/9 chỉ tiêu (`critical_factual_precision`/`brand_adherence`/`duplicate_publication`/`publication_post_id_rate`/`human_acceptance_no_major_edit`/`unplanned_empty_days`); 3/9 chỉ tiêu ảnh thiếu thật vì Vision QC mặc định `mock` (giữ ngân sách 500k/tháng) — ghi rõ trong `data_gaps`, không giả số.
- [x] `controlled_rollout/rollout_state_store.py` (mới) — JSON store, mặc định `"shadow"`, chỉ advance khi decision `allowed=True`.
- [x] CLI mới `venho-rollout` (`scorecard`/`rollout-status`/`rollout-advance`/`rollback-plan`/`runbook-validate`/`productize-run`), script entry mới trong `pyproject.toml`.
- [x] `.claude/skills/_productize/hotel-content-engine/SKILL.md` gắn CLI trigger + ghi rõ giới hạn (chưa chạy full M02/M05 pipeline).
- [x] **Gap phụ phát hiện + sửa:** `.gitignore` chặn toàn bộ `.claude/` từ trước tới giờ — 10 skill trong `.claude/skills/` (kể cả `hotel-content-engine`, tồn tại từ 2026-08-03) **chưa từng được commit vào repo** dù plan §8.1/RS-F1/RS-F4 yêu cầu. Sửa `.gitignore` thành `.claude/*` + negate `!.claude/skills` + `!.claude/CLAUDE.md.proposed`, giữ nguyên phần còn lại (settings local) bị ignore. Đã `git add` + commit 10 skill + `CLAUDE.md.proposed`.
- [x] Runbook (`docs/growth/controlled_rollout_runbook.md`) + eval docs (`docs/growth/eval_golden_sets.md`) viết lại khớp kiến trúc GitHub Actions thật (không còn Mac Mini), ghi rõ bảng 9 chỉ tiêu — nguồn nào có thật, nguồn nào thiếu.
- [x] **Trạng thái thật hiện tại (chạy tay xác nhận qua CLI):** rollout stage vẫn `shadow`, `rollout-advance` bị chặn đúng thiết kế (scorecard chưa qua gate ≥9.3/10 vì thiếu 3/9 chỉ tiêu ảnh + sample size còn nhỏ) — cùng kiểu honest gate như Phase 7's `INCONCLUSIVE`, không phải bug.
- [x] Verify: `/usr/bin/python3 -m pytest -q` → 736/736 pass (724 + 12 test mới), 0 API call.

**Ý nghĩa "hoàn thành":** cả 9 phase roadmap (0→8) giờ có code thật, CLI thật, nối dây thật tới dữ liệu thật — không còn phase nào ở trạng thái "code+test cô lập, 0 caller". Việc còn lại (rollout stage tiến lên `pilot_25`, golden eval set >=100 case reviewer-scored, Vision QC thật, backup verify-restore, lateness alert, GA4/FB attribution) là **vận hành theo thời gian thật + quyết định của Harry**, không phải việc code còn thiếu — liệt kê đầy đủ trong runbook.

Chi tiết đầy đủ: `task_memory.md` mục 14m.

---

---

### Growth Agent v3.1 — Phase 7 Growth Intelligence pilot: strategy_memory nối thật (2026-08-06)

**Status: DONE — commit local, chưa push**

Tiếp nối Phase 6 cùng phiên. Audit `strategy_memory/` (Codex build 2026-08-03) — cùng lỗ hổng như Phase 4.5/5/6: `pattern_inference.py`/`weekly_brief.py`/`qbsr_guardrail.py` có code + unit test đầy đủ nhưng 0 caller thật, và package này chưa từng có CLI nào cả.

- [x] CLI mới `venho-strategy` (`strategy_memory/cli.py`, script entry mới trong `pyproject.toml`): `weekly-brief`, `promote`, `list-promoted`.
- [x] `strategy_memory/collect_pilot_evidence.py::collect_pilot_snapshots()` (mới) — join thật `PublicationRegistry` + M08 `SnapshotStore` (reach thật) + `AttributionEventStore` (mới) theo (pillar, platform), một dòng/publication (đúng "sample size" thống kê, không gộp tổng trước).
- [x] `AttributionEventStore` (mới) — Phase 6's CLI `venho-analytics attribute` giờ **lưu lại** kết quả attribution thật thay vì chỉ in ra rồi bỏ.
- [x] Vòng phản hồi `INCONCLUSIVE` → `research/questions/` mở rộng cho strategy pattern (hàm `generate_research_question_from_analytics` đã có test đúng shape từ trước, chưa ai gọi ngoài M08's per-publication path).
- [x] **Gap phụ phát hiện + sửa:** `M08AnalyticsBridge.observe()` chưa từng đọc `pillar` thật từ publication row (dù `daily_cycle.py` ghi field này từ 2026-08-04) → mọi snapshot trước đây có `pillar="unknown"`, group theo pillar bất khả thi. Đã sửa.
- [x] Verify: `/usr/bin/python3 -m pytest -q` → 724/724 pass (717 + 7 test mới), 0 API call. Đã tự phát hiện + sửa 1 lỗi trong lúc viết test — test đầu chạy CLI `weekly-brief` không truyền `--questions-root`, vô tình ghi file thật vào `research/questions/` của repo → sửa test truyền `--questions-root` trỏ `tmp_path`, xoá file rác đã lỡ tạo, xác nhận `git status research/` sạch.
- [x] **Trạng thái thật hiện tại (chạy tay xác nhận):** `weekly-brief` trả về 0 recommendation — đúng thiết kế `INCONCLUSIVE`, không phải bug, vì Growth Agent mới chạy thật từ 2026-08-03/04, chưa đủ `min_sample_size` publication có cả snapshot thật lẫn sự kiện attribute thật ở bất kỳ scope nào.

Chi tiết đầy đủ: `task_memory.md` mục 14l.

---

### Growth Agent v3.1 — Phase 6 Analytics + Attribution: meta_insights flag thật + attribution tối thiểu qua Zalo (2026-08-06)

**Status: DONE (phạm vi Harry chốt) — commit local, chưa push**

Tiếp nối Phase 5 cùng phiên. Audit Phase 6 (Codex build 2026-08-03) — cùng loại lỗ hổng: `meta_insights.py`/`attribution.py` có code + unit test nhưng 0 caller thật. Đào sâu hơn phát hiện: bài đăng Growth Agent hiện **không có link nào cả** (FB/IG chỉ có CTA chữ, form đặt phòng trên website chưa bắt utm param) — nghĩa là attribution end-to-end thật cần **xây mới**, không chỉ nối dây có sẵn như Phase 4.5/5. Hỏi Harry phạm vi (AskUserQuestion) — Harry chọn: xây tối thiểu qua kênh Zalo (kênh duy nhất có deep-link click được thật, khác FB/IG).

- [x] `meta_insights.build_metrics_adapter` nối vào `M08AnalyticsBridge` default factory — flag `meta_insights_enabled` giờ có tác dụng thật (trước đó bridge hardcode Mock, bỏ qua flag hoàn toàn). Vẫn Mock khi flag tắt (đúng trạng thái thật hiện tại).
- [x] `attribution.py::build_tracking_url()` (mới) + `tracking_base_url` trong `attribution_policy.yaml` — sinh link `venhohotel.com/lien-he?utm_source=zalo&utm_medium=social&utm_content=<publication_id>`.
- [x] `daily_cycle.py::_content_payload()` nhúng link này vào cuối bài **Zalo** (chỉ Zalo — FB/IG/Threads vẫn không có link, đúng thực tế content hiện tại).
- [x] CLI mới `venho-analytics attribute <events.json>` — chạy attribution thật trên publication đã **reconciled** (có `published_at` thật) từ `PublicationRegistry`.
- [ ] **Gap còn lại, không giả vờ đã xong:** không có nguồn sự kiện chuyển đổi tự động — Harry vẫn phải tự cung cấp `events.json` bằng tay. Tự động hoá cần GA4 Data API (credentials + quyết định riêng) hoặc sửa form đặt phòng trên website `Ven Ho Hotel` để bắt utm (chạm production website, cần approval riêng của dự án đó — không tự làm).
- [x] Verify: `/usr/bin/python3 -m pytest -q` → 717/717 pass (714 + 3 test mới: build_tracking_url + attribution end-to-end, Zalo content có link/FB không có, CLI attribute end-to-end).

Chi tiết đầy đủ: `task_memory.md` mục 14k.

---

### Growth Agent v3.1 — Phase 5 Durable Ops: stale-job recovery + budget cap thật (2026-08-06)

**Status: DONE — commit local, chưa push (Harry: "sẽ commit và push khi nào hoàn thành tất cả")**

Tiếp nối rà soát Phase 1-3/4/4.5 cùng phiên. Audit Phase 5 (Codex build 2026-08-03, "DONE" theo note cũ) bằng grep caller thật — cùng phát hiện như Phase 4.5: `BudgetLedger`/`BudgetPolicy`/`JobStore.recover_expired_leases`/`heartbeat` có code + unit test nhưng 0 caller thật, nghĩa là mọi real OpenAI call (gpt-5.5/gpt-image-2/GPT-4o vision) chạy không đo/không chặn budget, và 1 run bị crash giữa chừng có thể kẹt job `RUNNING` vĩnh viễn.

- [x] **Stale-job recovery + heartbeat:** `run_weekly_cycle` gọi `recover_expired_leases()` trước `claim()`, lease tăng lên 3600s (từ 300s mặc định), `heartbeat()` gia hạn sau mỗi ngày trong tuần. Test mới xác nhận 1 job kẹt từ lần chạy crash trước tự phục hồi thay vì khoá `skipped_already_run=True` vĩnh viễn.
- [x] **`BudgetGate` (mới) chặn cứng real OpenAI call:** wrap reserve/commit/release quanh 3 điểm gọi API thật trong `daily_cycle.py` (text gen, image gen, vision QC). Chạm cap → `RuntimeError` → platform đó rơi vào `errors`, không crash cả pipeline. Cap thật **500,000 VND/tháng** (Harry chốt qua AskUserQuestion, thay giá trị cũ 2 tỷ VND vô nghĩa) trong `budget_policy.yaml`. Chi phí ước tính/lệnh gọi trong `paid_call_costs.yaml` (mới) — 300/1200/400 VND cho text/ảnh/vision, ghi rõ là estimate thô chưa đối chiếu hoá đơn thật.
- [x] Alert Telegram `budget_threshold_crossed` (event có sẵn, chưa ai gọi trước đây) bắn khi cán mốc 70/85/100%.
- [x] **`Worker` class + `scheduler.py` đánh dấu superseded** (không xoá, không ép nối) — giả định worker 24/7 + cửa sổ dispatch cố định 09:00, không khớp kiến trúc GitHub Actions on-demand thật.
- [ ] **Chủ động không làm** (cần hạ tầng/thời gian riêng): lateness alert (cần 1 vòng polling, kiến trúc push-based hiện tại không có chỗ tự nhiên gắn vào), backup tự động verify-restore (cùng gap DoD #24 cũ).
- [x] Doc: Phần 12 Phase 5 viết lại + CHANGELOG "v3.1 (2026-08-06 revision, Phase 5)".
- [x] Verify: `/usr/bin/python3 -m pytest -q` → 714/714 pass (710 + 4 test mới), 0 API call.

Chi tiết đầy đủ: `task_memory.md` mục 14j.

---

### Growth Agent v3.1 — Rà soát Phase 1–3 (xác nhận xong) + hoàn thiện Phase 4/4.5 (2026-08-06)

**Status: DONE — commit local, chưa push**

Harry: "Rà soát lại phase 1,2,3. Nếu đã xong hết thì chuyển sang hoàn thiện Phase 4 và 4.5" (đối chiếu `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`).

- [x] **Rà soát Phase 1–3:** xác nhận xong bằng code + test thật (16 contract schema, 9+7 YAML policy, `shared/{budget,jobs,notify}`, `knowledge_studio/facts`, `claim_validator.py`, generator thật gpt-5.5, `image_studio_runtime/` + alignment/derivative validator — tất cả wired vào `daily_cycle.py`, 702/702 pass trước khi sửa gì).
- [x] **Doc fix:** Phần 12 Phase 4.5 (PB-006/PB-007) viết lại — "launchd 09:00"/"deadman switch cloud" đánh dấu superseded, khớp với kiến trúc GitHub Actions Phần 10 đã đổi từ 2026-08-05.
- [x] **PB-005 pre-flight thật:** `approve_and_dispatch._dispatch_claimed` giờ re-run `ClaimValidator`/`validate_alignment` ngay trước khi gọi webhook thật — trước đây chỉ `edit_publication()` mới revalidate, một publication chưa sửa nhưng approve trễ (batch cả tuần) có thể publish claim dựa trên fact đã hết hạn. Kill-switch → `NEEDS_REVISION`, 0 dispatch.
- [x] **`PublishingSlot` domain — sửa 2 lỗi thật:** `assert_missed_only_after_evergreen_exhausted` trước chỉ guard `status=="OPEN"`, nhưng path MISSED thật luôn từ `DRAFT_ASSIGNED` — guard chưa từng fire trong production dù test riêng pass. `EVERGREEN_FALLBACK -> DISPATCHED` đổi thành `-> PENDING_APPROVAL` (Harry chốt qua AskUserQuestion: evergreen fallback vẫn cần 1 click Duyệt, không auto-publish, giữ đúng DoD #23).
- [x] **PB-004 Evergreen Pool nối thật:** `shared/storage/evergreen_pool_store.py` mới + CLI `evergreen-add`/`evergreen-list`, wired vào `daily_cycle.py::_fill_slot_from_evergreen` (gọi khi mọi platform sinh nội dung thất bại, trước khi cho MISSED). Pool trống mặc định — cơ chế chạy thật, chưa kích hoạt vì Harry chưa curate item nào.
- [x] **PB-003 Runway + Telegram alert nối thật:** `manage_queue.check_runway` đếm slot `OPEN` trong horizon 14 ngày (canary hạ tầng — chỉ tụt nếu chính job `weekly-cycle` ngừng chạy), gọi best-effort cuối `run_weekly_cycle` + CLI `check-runway`. `evergreen_used`/`slot_missed` alert cũng bắn từ `daily_cycle.py` (event đã định nghĩa sẵn trong `alert_policy.yaml`, chưa ai gọi trước đây).
- [ ] **Cần Harry set 2 secret** để alert Telegram chạy thật: `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (local `.env.local` + GitHub Actions secret) — hiện tại cơ chế live nhưng luôn no-op (Mock) vì thiếu token.
- [ ] **Chủ động không làm** (cần quyết định/thời gian riêng, không phải quên): DoD #24 (backup ảnh + verify-restore), DoD #26 (golden-set scorecard — cần dataset thật), "4 tuần liên tục 16 slot 0 duplicate" (cần thời gian vận hành thật), `preflight.py` asset/event/weather tổng quát (registry chưa track event_claims/weather_context per publication — để dành Phase 6/7 khi Trend Radar content thật bắt đầu publish).
- [x] Verify: `/usr/bin/python3 -m pytest -q` → 709/709 pass (702 + 7 test mới: evergreen wiring, DRAFT_ASSIGNED guard, check_runway ×2, preflight blocks dispatch ×2), 0 API call. Không đổi `venho-os` lượt này.

Chi tiết đầy đủ: `task_memory.md` mục 14i.

---

### Growth Agent v3.1 — Post-audit follow-up: viết lại Phần 10/18, dọn code chết, soi lại "Image runtime + Multimodal QC" (2026-08-05)

**Status: DONE (2/3 việc Harry yêu cầu) — việc 3 hoá ra không cần làm, xem correction bên dưới**

Sau khi báo cáo audit hoàn thành v3.1 (mục ngay dưới), Harry yêu cầu 3 việc: (1) viết lại DoD Phần 10/18 cho đúng kiến trúc GitHub Actions; (2) dọn code chết; (3) "Làm Image runtime + Multimodal QC".

- [x] **1) Viết lại Phần 10 + DoD 21–24** trong `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` — xoá toàn bộ thiết kế Mac Mini 24/7/launchd/pmset/deadman switch/HMAC cloud fallback/Tailscale (chưa từng triển khai), thay bằng kiến trúc thật: GitHub Actions cron (`growth-daily-cycle.yml` T2, `growth-trend-scan.yml` T6) + git-sync 2 chiều qua GitHub Contents API (local luôn thắng khi merge) + duyệt/dispatch on-demand trên `venho-os` local, không có cửa sổ đăng cố định 09:00. Ghi rõ 2 gap thật chưa làm: backup artifacts + verify-restore (DoD #24), truy cập mobile (§10.5). Thêm dòng CHANGELOG "v3.1 (2026-08-05 revision)".
- [x] **2) Dọn code chết:**
  - **Xoá hẳn `infra/`** (`heartbeat.py`, `deadman_config.yaml`, `cloud_fallback/`, `backup.sh`, `launchd/*.plist`, `setup_macmini.md`) — 0 caller thật ngoài 1 file test của chính nó, thiết kế đã bị thay thế hoàn toàn ở việc (1). Gỡ `"infra*"` khỏi `pyproject.toml` package discovery. Test file `tests/test_growth_v3_1_cadence_infra.py` (293 dòng) **không xoá** — chỉ cắt 4 test cuối (heartbeat + cloud_fallback export), 28 test còn lại (cadence/slot/special-lane/preflight/weather/alert/zalo) vẫn test code thật đang chạy, giữ nguyên.
  - **Đánh dấu "chưa nối" bằng comment đầu file** (không xoá — code thật, test thật, dành cho phase sau, chỉ chưa có caller): `growth_orchestrator/application/evergreen_pool.py` (Phase 4.5, DoD #10), `analytics_feedback/meta_insights.py` + `analytics_feedback/attribution.py` (Phase 6, DoD #25), `strategy_memory/pattern_inference.py` (Phase 7).
  - **Xác nhận KHÔNG phải dead code** (sửa nhầm lẫn từ audit trước): `image_studio_runtime/` — xem việc 3.
  - Verify: `python3 -m pytest -q` toàn bộ → 702 passed (từ 706, giảm đúng 4 test bị cắt), 0 lỗi.
- [x] **3) "Làm Image runtime + Multimodal QC" — kết luận: KHÔNG cần làm, đã live từ trước.** Trước khi build, hỏi lại Harry 2 vòng và phát hiện báo cáo audit trước đó (mục "Đã viết code, nhưng chưa nối" → "Image runtime thật (Phase 3) — vẫn chỉ có Mock provider") **sai**. Kiểm tra lại code thật: `image_studio_runtime/adapters/gpt_image_provider.py` (gpt-image-2 thật, `images.generate`/`images.edit`) đã nối vào `daily_cycle.py`; QC ảnh dùng `validator_studio/image_validator.py` → `observe_adapter.py` → `shared/vision/client.py::VisionClient` gọi **GPT-4o thật** để so ảnh sinh ra với DNA (không phải mock, không phải chỉ entity/OCR như tôi nhầm tưởng ban đầu khi hỏi Harry lần 1). `growth_orchestrator/cli.py` (`daily-cycle`/`weekly-cycle` — chính lệnh GitHub Actions cron đang chạy thật) hardcode `image_validation_provider="openai"` — nghĩa là **QC ảnh thật đã chạy và tốn phí thật mỗi tuần từ 2026-08-03/04**, không phải chưa làm. Harry xác nhận "Dừng — không xây gì thêm" sau khi nghe correction. Đã sửa artifact audit đã publish trước đó (URL không đổi, có correction log ở footer).

Chi tiết đầy đủ: `task_memory.md` mục 14h.

### Growth Agent v3.1 — 6 hạng mục còn lại từ audit (2026-08-05)

**Status: DONE (Trend Radar cron + Research OS content vẫn cần Harry quyết/điền tiếp)**

Harry: "Làm tất cả" sau khi hỏi growth v3.1 có 100% chưa. Chi tiết đầy đủ từng mục: `task_memory.md` mục 14g.

- [x] 1) Retry UI cho `GATEWAY_ERROR` (`list_pending()` trả cả GATEWAY_ERROR, nút "Thử lại gửi" trên `venho-os`).
- [x] 2) `SlotStore` (SQLite) + `JobStore` idempotency theo ISO week nối vào `weekly_cycle` thật — **thiết kế lại cho GitHub Actions ephemeral**, không phải Mac Mini 24/7 của plan gốc (Harry xác nhận giữ GitHub Actions). CLI `venho-growth slots`, panel "Slot tuần này" trên dashboard.
- [x] 3) HMAC callback — **quyết định giữ `reconcile` thủ công** (Harry xác nhận), không xây endpoint vì `venho-os` chưa deploy công khai, Make.com không gọi được vào localhost.
- [x] 4) `edit_publication()` giờ re-run claim/alignment validator thật (không chỉ content rubric) — cần `daily_cycle.py` lưu thêm `creative_brief`/`claims`/`scene_summary` vào registry row.
- [x] 5) Trend Radar thật: xây bộ phân loại + `fetch_saturday_candidates.py` + `trend_candidate_store.py` (enforce human-approval mandatory bằng code) + nối vào `_pick_topic` Thứ 7. CLI `trend-scan`/`trend-list`/`trend-approve`.
  - [x] **2026-08-05 — chuyển classifier từ Claude sang Gemini Flash** (Harry: chi phí Anthropic cao, không phù hợp startup). `classifiers/claude_classifier.py` đã xoá, thay bằng `classifiers/gemini_classifier.py` — cùng interface/taxonomy, dùng `google-genai` SDK (`pip install "venho-ai-studio[gemini]"`), model mặc định `gemini-flash-latest` (override qua `GEMINI_TREND_MODEL`), env `GEMINI_API_KEY` (Harry cần tự điền vào `.env.local`, chưa có). Content generation ở nơi khác trong repo vẫn dùng Claude — đổi chỉ giới hạn trong Trend Radar classification.
  - [x] **2026-08-05 — nối cron thật:** `.github/workflows/growth-trend-scan.yml` mới, Thứ 6 08:00 ICT (`0 1 * * 5` UTC) + `workflow_dispatch`. Secrets `GEMINI_API_KEY`/`TAVILY_API_KEY` đã set qua `gh secret set` (đọc từ `.env.local`, không in ra giá trị). Chạy trước Thứ 2 (khi `weekly-cycle` chọn chủ đề Thứ 7) để Harry có cả cuối tuần duyệt.
  - [x] **2026-08-05 — UI duyệt trên `venho-os`:** panel "Trend Radar — Chờ duyệt xu hướng" trong `PublishingSection.tsx`, route `GET /api/v1/studio/growth/trend-candidates` (`trend-list`) + `POST .../trend-candidates/approve` (`trend-approve`, `approved_by` = session email thật). Test thật qua HTTP với session cookie thật — `approved_by` ghi đúng `hpham1504@gmail.com`.
  - **Known gap kế thừa (không mới do việc này):** `trend_candidates.json` (như `publication_registry.json` của daily/weekly-cycle) được Actions runner `git add -f` + push sau mỗi lần chạy — venho-os chạy CLI cục bộ trên checkout local của Harry (`STUDIO_DIR`), nên sau lần chạy Thứ 6 tự động, Harry cần `git pull` trong `venho-ai-studio` trước khi mở panel để thấy candidate mới; sau khi duyệt, cần `git push` để `weekly-cycle` (chạy trên Actions runner riêng, checkout fresh từ git) thấy được approval trước khi chọn chủ đề Thứ 2. Đã ghi nhận từ trước cho `publication_registry.json` (task_memory dòng ~856); chưa tự động hoá sync 2 chiều này.
- [x] 6) Research OS: đăng ký domain thứ 9 (`weather_signal`, thiếu ở cả `domains.yaml` lẫn `ResearchNote`'s Literal — 2 nguồn sự thật đã lệch nhau, đã đồng bộ + test khoá). Thêm CLI `venho-research collect-source`/`collect-note` (trước đây không có cách ingest note nào ngoài `load-seed-facts`).
  - [ ] **Không bịa nội dung** — vẫn ~2/9 domain có note thật (đúng quyết định Harry: cung cấp dần từng domain).
- [x] Verify: 706/706 pytest pass (33 test mới), `tsc`/`eslint` sạch, 127/127 vitest pass (venho-os).

---

### Growth Agent v3.1 — Nút Sửa đúng theo plan + upload ảnh lên Google Drive (2026-08-04)

**Status: DONE (cần Harry set 3 GitHub Secrets để bật upload ảnh thật)**

Harry chốt 2 gap từ báo cáo audit trước: "Nút Sửa: Làm đúng theo Plan." + "Ảnh generate ra không lên bài: Lưu vào Google drive."

- [x] `edit_publication()` — editable từ `PENDING_APPROVAL`/`GATEWAY_ERROR`, chấm lại bằng content_validator thật, không đạt → `NEEDS_REVISION`, approval cũ luôn bị xoá vô điều kiện (đúng invariant "sửa sau approval → tự revoke" của plan).
- [x] `registry.claim()` mở rộng nhận `set[str]` (không chỉ 1 status) để hỗ trợ edit từ 2 trạng thái.
- [x] Thêm `dna_subject` vào registry row (`daily_cycle.py`) để edit biết chấm theo DNA nào.
- [x] CLI `venho-growth edit --publication-id --edited-by --text-file`; API `POST /api/v1/studio/growth/[id]/edit` (venho-os); UI textarea inline "Sửa"/"Lưu và chấm lại"/"Huỷ" trong `GrowthApprovalQueue`.
- [ ] **Giới hạn đã ghi rõ:** chỉ re-run content rubric, không re-run claim/alignment validator (cần persist CreativeBrief gốc — ngoài phạm vi tính năng này).
- [x] `shared/storage/google_drive.py` — `MockDriveUploader` (test/dev mặc định) + `GoogleDriveUploader` thật (tái dùng OAuth app của `venho-social-content-agent`) + `google_drive_uploader_from_env()`.
- [x] `daily_cycle.py` upload ảnh đã qua validator lên Drive, lưu `content.image_public_url`; `MakeGatewayAdapter` copy ra field `image_url` top-level trong payload gửi Make.com.
- [x] `pyproject.toml` optional group `drive` + workflow `growth-daily-cycle.yml` cài `.[drive]` + 3 env secret mới.
- [ ] **Cần Harry tự làm:** thêm 3 GitHub Secrets (`GOOGLE_DRIVE_TOKEN_JSON`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`) vào repo `venho-ai-studio` — chưa set thì uploader tự fallback Mock (không lỗi, chỉ không có ảnh thật lên bài).
- [ ] **Phát hiện phụ, chưa sửa (ngoài yêu cầu):** `.env.local` cục bộ có giá trị `GOOGLE_DRIVE_TOKEN_JSON` sai định dạng (giống client secret, không phải token JSON) — sẽ không hoạt động nếu Harry chạy Drive upload ở local, cần Harry tự dán lại đúng token.
- [x] Verify: 677/677 pytest pass (10 test mới), `tsc`/`eslint` sạch, 127/127 vitest pass.

Chi tiết đầy đủ: `task_memory.md` mục 14f. Việc liên quan `venho-os`: `task_status.md`/`CHANGELOG.md` mục cùng ngày.

---

### Growth Agent v3.1 — Audit đối chiếu master plan CONSOLIDATED, sửa lỗi + Từ chối (2026-08-04)

**Status: DONE**

Harry yêu cầu: review/audit Growth Agent đối chiếu `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`, sửa lỗi tìm được, thêm nút Từ chối/Sửa, dọn file rác.

- [x] Sửa race condition double-publish trong `approve_and_dispatch()` — `PublicationRegistry.claim()` mới (atomic test-and-set trong khoá `fcntl`), 2 lần bấm Duyệt đồng thời chỉ 1 bên thắng.
- [x] Sửa dispatch fail kẹt vĩnh viễn — lỗi mạng/webhook giờ hạ cánh `GATEWAY_ERROR` đúng cách + `retry_dispatch()` mới (CLI `retry-dispatch`) để thử lại không cần duyệt lại.
- [x] Cô lập lỗi theo platform (`run_daily_cycle`) và theo ngày (`run_weekly_cycle`) — 1 platform/ngày lỗi không còn xoá các platform/ngày khác trong cùng batch; lỗi ghi vào `.errors`.
- [x] `M03ValidatorBridge` fail-closed đúng thiết kế — exception trong `validate_content()` → `UNVALIDATED`, không văng ra ngoài (Part 2.1 quyết định #8 của plan).
- [x] Nút **Từ chối** full-stack: `reject_publication()` → CLI `venho-growth reject` → API `POST .../[id]/reject` (venho-os) → UI "Từ chối"/"Từ chối tất cả" trong `GrowthApprovalQueue`. Rejected rows tự rớt khỏi `list-pending`.
- [ ] **"Sửa" (edit) cố tình chưa làm** — cần chốt UX trước (inline edit vs mở lại content_studio pipeline) + phải tự động revoke approval + rerun M03 theo plan; để Harry quyết định approach.
- [x] Điều tra `bff/growth/growth-agent.client.ts` (127.0.0.1:8011, nghi dead code) — xác nhận là client thật cho `venho-quangcao-agent` (agent quảng cáo trả phí, repo khác), không phải lỗi, không đụng vào.
- [ ] **Gap đã biết, chưa làm:** ảnh generate ra không bao giờ đính vào payload dispatch thật (cần Google Drive/storage uploader mới — quyết định kiến trúc cần Harry chốt, không tự xây).
- [x] File lỗi/temp/nháp: cả 2 repo `git status --short` sạch trước/sau — không có gì cần xoá.
- [x] Verify: 667/667 pytest pass (venho-ai-studio) · `tsc --noEmit` + `eslint` sạch + 127/127 vitest pass (venho-os).

Chi tiết đầy đủ từng lỗi: `task_memory.md` mục 14e. Việc liên quan `venho-os`: xem `venho-os/task_status.md`/`CHANGELOG.md` mục 2026-08-04.

---

### Growth Agent v3.1 — gpt-5.5 generator, Validator gate thật, fix hex-code leak, lên lịch tuần (2026-08-04)

**Status: DONE**

Yêu cầu liên tiếp của Harry trong 1 phiên: bài chờ duyệt sơ sài → sinh lại + lên lịch tuần · chuyển generator sang gpt-5.5 · lỗi bấm Phê Duyệt · Validator phải chấm điểm thật (text+ảnh), không pass phải làm lại · bài viết lộ mã hex/tiếng Anh kỹ thuật · nạp thêm credit.

- [x] `gpt_social_generator.py` (gpt-5.5, `response_format=json_object`) là generator mặc định thay `claude_social_generator.py`.
- [x] `M03ValidatorBridge` gọi `validator_studio.content_validator.validate_content()` thật — chỉ `APPROVE` mới `READY_FOR_REVIEW`; `daily_cycle.py` retry `MAX_TEXT_ATTEMPTS=3`/platform.
- [x] `_generate_topic_image()` retry `MAX_IMAGE_ATTEMPTS=2`, chỉ giữ ảnh khi qua `validate_image()` (kill-switch + APPROVE).
- [x] `_score_brand_fit` sửa gốc — bỏ overlap với `dna["invariant"]` (English/hex, xung đột với rule chống copy-nguyên-văn), chỉ tính overlap `prompt_rules.brand_dna`. Verify script: overall_score 81.59→91.12, brand_fit 57.86→95.0.
- [x] Hex-code/tiếng Anh kỹ thuật không còn lọt vào content — `content_prompt_builder.render_final_prompt()` + 3 system prompt trong `social_prompts.py` đều cấm copy nguyên văn.
- [x] Root-cause fix lỗi bấm Phê Duyệt (`shared/http.py::urllib_post`) — Make.com trả plain-text "Accepted" chứ không phải JSON, gây đúng lỗi Harry báo (`Expecting value: line 1 column 1 (char 0)`). Bắt `JSONDecodeError`, trả `{"raw": raw}`.
- [x] Fix ảnh MPO (iPhone portrait) không edit được — `reference_asset_resolver.py` re-encode PNG qua PIL trước khi gửi OpenAI.
- [x] `weekly_cycle.py` + CLI `venho-growth weekly-cycle`; `.github/workflows/growth-daily-cycle.yml` đổi cron còn Thứ 2 duy nhất (`0 1 * * 1`), Harry duyệt cả tuần 1 lần.
- [x] Registry rows ghi kèm `day`/`pillar`/`topic` để `venho-os` group theo chủ đề (đổi trong `daily_cycle.py`'s `registry.update()`).
- [x] Batch cuối: 15 publication cũ (thiếu field mới, generator cũ) → `SUPERSEDED`; `weekly-cycle` chạy lại → 16 publication mới `PENDING_APPROVAL`, verify đủ `day`/`pillar`/`topic`, 0 hex-code (grep trực tiếp `publication_registry.json`).
- [x] Verify: 655/655 pass; live `venho-growth list-pending` xác nhận 16 entry đúng field mới.

Chi tiết đầy đủ: `task_memory.md` mục 14d. Việc liên quan bên `venho-os` (redesign `GrowthApprovalQueue` UI): `venho-os/task_status.md`/`CHANGELOG.md` mục 2026-08-04.

---

### Growth Agent v3.1 — Review lần 2: đóng 7 gap DoD sau audit (2026-08-04)

**Harry: "Review lại task đang làm so với plan v3.1. Phần nào chưa làm xong, hoàn thiện nốt."**

Trước khi sửa, verify lại từng gap còn mập mờ trong audit trước bằng cách đọc code thật (không tin lại note cũ) — kết quả xác nhận 8 điểm cụ thể, sửa 7/8 (không sửa DoD #26 golden-set scorecard — xem lý do cuối).

**1) Brand Safety Gate — DoD #19 (yêu cầu ≥15 test case, thực tế trước đó là 0):**
- `tests/test_growth_brand_safety_gate.py` mới — 24 test: 9 category cấm × 1 (kill switch thắng cả khi giao với required_intersection hợp lệ), 5 required_intersection × 1, category khớp chính xác (không fuzzy "politics" vs "politics_governance"), gate rỗng, guard chính sách thật (`config/projects/venho_hotel/research/brand_safety.yaml` đủ 9 category, `human_approval: mandatory`), 3 test tích hợp qua `scan_trends()` thật (không có candidate nào lọt qua với status "approved" — chỉ "needs_human_approval"/"rejected", đúng TR-D3).

**2) Saturday loại-4 fallback — DoD #10 (logic có sẵn trong `special_lane.py` nhưng chưa ai gọi từ `daily_cycle.py`):**
- `daily_cycle._pick_topic()` giờ gọi thật `select_special_lane_candidate()` cho lane `special` — mỗi topic Thứ 7 giờ mang `special_lane_type`/`special_lane_reason`. Vì chưa có nguồn trend/event thật, mọi candidate mặc định `type: feature_story` (loại 4) — đúng thực tế, không giả vờ có trend scanning. Khi có nguồn thật, chỉ cần thêm `type: seasonal_nature/cultural_event/lifestyle_trend` vào 1 group trong `content_pillars.yaml`, logic ưu tiên có sẵn sẽ tự chọn đúng.
- Test mới: ưu tiên `seasonal_nature` trên `feature_story`, `cultural_event` không `verified_by_human` bị từ chối (raise đúng như thiết kế).

**3) `asset_version_ids` — DoD #7 (trước đó luôn là `[]` kể cả khi có ảnh thật):**
- `daily_cycle.py` giờ lấy `run_folder.name` (chính là `run_id` thật của `RunStore`) làm asset version, gán vào `package_snapshot["asset_version_ids"]`. Rỗng khi tắt sinh ảnh, đúng 1 id khi có ảnh — có test cho cả 2 nhánh.

**4) Feedback loop → research question mới — DoD #25 (code có sẵn từ Phase 7 nhưng chỉ dùng trong test riêng, `M08AnalyticsBridge.observe()` chưa từng gọi):**
- `M08AnalyticsBridge.observe()` giờ luôn gọi `generate_research_question_from_analytics()` sau khi tạo advisory, ghi câu hỏi thật vào `research/questions/` (vault Obsidian thật — `questions_root` tiêm được cho test, mặc định production là path thật). `INSUFFICIENT_DATA` → map sang `"INCONCLUSIVE"` (đúng string generator cần), `UNDERPERFORM` → `qbsr_drop=True`, còn lại dùng `advisory.analysis_summary` làm pattern.

**5) Cross-modal image validation — DoD #5 (validator có sẵn trong `validator_studio/`, `growth_orchestrator` chưa từng import):**
- `_generate_topic_image()` giờ gọi `validator_studio.image_validator.validate_image()` (DNA-match, provider mặc định `"mock"` — không tốn tiền, đúng kỷ luật 0-API-call của repo) ngay sau khi có ảnh thật, ghi `image_validation_report.json` cạnh artifact. `kill_switch.triggered=True` → loại ảnh (giống hệt nhánh lỗi sinh ảnh cũ, text vẫn lên hàng chờ duyệt).
- **Giới hạn thật:** provider mặc định `"mock"` không thực sự "nhìn" ảnh — chỉ đối chiếu tên file theo quy ước ("bad"/"forbidden"/"wrong"/"reject") để giả lập vi phạm, và `generate_image_run()` luôn đặt tên file cố định `generated.png` nên nhánh kill-switch trên thực tế không tự kích hoạt qua đường này (chỉ kiểm chứng được bằng cách tiêm thẳng report giả trong test). Cần Harry duyệt chi phí trước khi đổi sang provider vision thật.

**6) Idempotency / platform post ID — DoD #3 (phát hiện quan trọng: pipeline thật KHÔNG BAO GIỜ đạt trạng thái `PUBLISHED`):**
- Audit phát hiện `approve_and_dispatch()` chỉ đưa status tới `GATEWAY_ACCEPTED` (Make.com webhook bắn đi rồi bỏ qua response — xem docstring `MakeGatewayAdapter.send()`), không bao giờ set `platform_post_id`/`PUBLISHED`. Nghĩa là M08 Analytics tôi vừa nối ở lượt trước **không bao giờ chạy được thật ngoài test** (test cũ tự dựng row `PUBLISHED` giả, bỏ qua toàn bộ pipeline thật).
- `growth_orchestrator/application/reconcile_publication.py` mới + CLI `venho-growth reconcile --publication-id X --platform-post-id Y --reconciled-by harry` — thao tác thủ công: sau khi Make.com đăng thật, Harry (hoặc sau này 1 callback receiver thật) tự kiểm tra bài đã đăng trên Facebook/Instagram/Threads/Zalo rồi ghi `platform_post_id` vào registry, chuyển status sang `PUBLISHED`. Đây chính là "reconciliation evidence" DoD #3 chấp nhận thay platform post ID tự động.
- **Còn thiếu thật:** chưa có callback receiver tự động (`publishing_gateway/callback_receiver.py` có sẵn, cần HMAC signature/timestamp — thiết kế cho endpoint nhận webhook thật, không hợp để gọi tay) — cần venho-os deploy public URL để Make.com gọi ngược lại, là quyết định hạ tầng ngoài phạm vi code (tương tự quyết định Mac Mini đã hoãn).

**7) Blog SEO từ Research OS — DoD #11 (trước đó `build_blog_draft()` chỉ dùng DNA visual fact, không đụng `knowledge_studio.facts`):**
- `growth_orchestrator/application/run_blog_pipeline.py` mới + CLI `venho-growth blog --topic "..." --keyword "..."` — gọi `content_studio.generate_content()` thật (content_type="blog", không đổi gì trong content_studio), sau đó thêm 1 đoạn "grounded facts" build **chỉ từ fact đã `FactResolver` xác nhận approved + còn hiệu lực** (whitelist 4 key: room_count/address/website/agoda_overall — đúng 4 fact seed thật đã nạp). Fact chưa duyệt hoặc hết hạn tự động bị bỏ qua, không bịa.
- Verify chạy thật (không chỉ test): `venho-growth blog --topic "Mot ngay o Ho Tay"` → bài viết thật trích đúng "12 phòng, toạ lạc tại 181 Nguyen Dinh Thi..., đánh giá 8.5/10 trên Agoda", `facts_cited` đủ 4 key với `source_rs_id` đúng.
- **Chưa làm:** chưa có lịch blog cố định trong `cadence_policy.yaml` (Harry chưa quyết định tần suất/vị trí đăng blog) — đây là pipeline gọi tay, chưa vào cron.

**8) DoD #26 (golden-set scorecard ≥9.3/10) — KHÔNG làm lượt này:**
- `controlled_rollout/scorecard.py::evaluate_golden_set()` đã thật, đúng công thức 9 chiều theo `docs/growth/eval_golden_sets.md`, nhưng không có bộ dữ liệu golden thật nào trong repo — chỉ chạy trong test với dict giả lập. Xây bộ golden set cần Harry tự chọn ra các bài/ảnh "chuẩn" thật đã publish để làm chuẩn so sánh — không phải việc code có thể tự bịa, khác hẳn các gap còn lại (đều là glue code thuần).

**Sửa phụ:** `contracts/creative_brief.schema.json` không đổi thêm; `DailyCycleResult.topic` đổi type hint từ `dict[str, str]` sang `dict[str, Any]` (topic Thứ 7 giờ có field `verified_by_human: bool`).

**Verify:** `/usr/bin/python3 -m pytest -q` → 636 passed (598 cũ + 38 mới: 24 brand safety + 8 daily_cycle mới [3 special-lane + 1 asset_version rỗng + 2 image validation + đã tính lại] + 1 M08 research-question + 5 reconcile + 3 blog), `compileall` sạch toàn repo, `venho-growth --help` xác nhận 2 command mới (`blog`, `reconcile`) lên đúng CLI, chạy tay `venho-growth blog` cho ra bài thật trích đúng fact đã duyệt.

---

### Growth Agent v3.1 — Audit theo Definition of Done (27 điều kiện) + việc 1-5 (2026-08-04)

**Status: DONE việc 1-5 (đúng scope glue thật, có test) · việc 6 (hạ tầng) và phần "chạy thật 9 domain research" CHƯA làm — cần quyết định của Harry**

Đọc lại `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` Phần 18 (27 DoD) để audit chính xác thay vì áng chừng. Kết quả: ~3/27 đạt chắc, phần lớn chưa chạm — hệ thống đang ở khoảng Phase 3-4/8 theo roadmap gốc.

**Phát hiện quan trọng nhất trước khi sửa:** có 2 pipeline sinh nội dung song song chưa hợp nhất — `growth_orchestrator` chính thức (CreativeBrief LOCKED → M03 validate → approval_snapshot khoá version) và `daily_cycle.py` tôi build ở lượt trước (gọi thẳng `content_studio`, bỏ qua toàn bộ safety rail). Việc 1-2 dưới đây giải quyết đúng phát hiện này.

**1) Hợp nhất pipeline — `growth_orchestrator/bridges/m05_content_bridge.py`:**
- `M05ContentBridge.generate_candidates()` hết là stub 3-angle hard-code — giờ gọi `content_studio.generate_content()` thật, dựng `scene_summary.entities` từ `ScenarioRegistry` (không phải tự bịa).
- `growth_orchestrator/application/run_content_pipeline.py` thêm DI (`content_bridge`, `validator_bridge`) để test/daily_cycle tiêm được.
- `growth_orchestrator/application/daily_cycle.py` viết lại hoàn toàn: build `CreativeBrief` LOCKED thật cho từng platform (validate bằng `jsonschema` đúng `contracts/creative_brief.schema.json`), chạy qua `run_content_pipeline` → `M03ValidatorBridge` (claim + alignment gate) → **chỉ queue `PENDING_APPROVAL` khi package `READY_FOR_REVIEW`**; package `NEEDS_REVISION`/`UNVALIDATED` trả về trong `.packages` để thấy nhưng không lên hàng duyệt.
- `contracts/creative_brief.schema.json`: thêm `threads`/`zalo` vào `platforms` enum (schema gốc v2.x chỉ có facebook/instagram/website_blog/google_business_profile — thiếu 2 platform thật hệ thống đang dùng).
- Verify chạy thật (không phải chỉ test): `venho-growth daily-cycle --day friday` → 4/4 platform `READY_FOR_REVIEW`, nội dung đúng brand, Zalo đúng 0 hashtag.

**2) Exact-version approval — `automation_studio/approval_snapshot.py` (đã có sẵn, chưa ai dùng) nối vào `approve_and_dispatch.py`:**
- `daily_cycle.py` khi queue giờ đóng băng `package_snapshot` (copy_version_ids, asset_version_ids, validation_snapshot_id, brief_version_id) lên dòng registry.
- `approve_and_dispatch()`: nếu có `package_snapshot` → gọi `create_approval_snapshot()` + `assert_dispatch_allowed()` thật, lưu `approval_snapshot` (có checksum, `approved_by`, `approved_at`) vào registry — đúng DoD #7 "owner approval tham chiếu exact version". Không có snapshot (dòng cũ/thủ công) → fallback hành vi cũ, không crash.
- **Giới hạn thật:** chưa có store ContentPackage sống để so sánh "đã đổi chưa" tại thời điểm duyệt — hiện tại chưa có UI sửa nội dung sau khi queue nên check này chưa có gì để bắt thật; hạ tầng đã sẵn sàng cho khi có UI sửa.

**3) Research OS chạy thật — KHÔNG dùng weather (R2-T không bao giờ lên R3 theo đúng thiết kế, xem Phần 6.6 "Ranh giới quyết định"):**
- Phát hiện: `research/` vault đã có sẵn note thật (`RS-2026-08-0014` synthesis, `RS-2026-08-0001`/`RS-2026-08-0005` R1) và `config/projects/venho_hotel/growth/seed_facts.json` với 4 fact **đã ghi `approved_by: harry`** trong file git-committed — nhưng chưa từng được `FactStore` persist thật (`data/projects/venho_hotel/growth/facts/` rỗng trước khi tôi chạy).
- Thêm CLI `venho-research load-seed-facts` (trước đây `FactStore.load_seed_facts()` có code + test nhưng không có CLI nào gọi) — **đã chạy thật**, verify `FactResolver().resolve("hotel.room_count")`/`"review.agoda_overall"` trả về đúng, `approved_by: harry`.
- **KHÔNG tự ý promote fact MỚI nào** — `venho-research promote` yêu cầu `--approved-by` thật (founder gate, DoD #13 cấm auto-promote), tôi không tự ký thay Harry. Cần Harry xác nhận trước khi promote thêm — xem câu hỏi cuối báo cáo.
- **Còn thiếu thật:** 8/9 domain nghiên cứu chưa có chu kỳ chạy thật nào (guest_voice mới có 1 note mẫu, competitor/local_intel/platform_trend/brand_visual/market_pricing/social_trend/local_events/weather đều trống) — đây là nghiên cứu kinh doanh thật của Harry, tôi không thể tự bịa dữ liệu cạnh tranh/giá/sự kiện.

**4) Ảnh thật trong `daily_cycle.py`:**
- `agent_studio/growth/reference_asset_resolver.py` mới + `config/projects/venho_hotel/growth/reference_assets.yaml` mới — map `reference_asset_ids` (chuỗi ID trong `scenario_registry.yaml`) sang file ảnh thật đã tìm thấy trong `assets/raw/` (không phải venho-os như tưởng — ảnh gốc nằm ngay trong repo này). **Ảnh chọn là mặc định tạm** (ảnh đầu tiên tìm thấy mỗi thư mục), chưa qua QC/duyệt như bộ ref Linh An B3/A2/C/D — Harry nên tự chọn lại.
- `daily_cycle.py` sinh **1 ảnh thật/ngày** (dùng chung cho mọi platform, đúng thực tế Harry đăng cùng 1 ảnh nhiều nơi), qua `prompt_studio.build_image_prompt` (M02, đã có sẵn) → `GPTImageProvider`/`MockImageProvider` (tiêm được) → `generate_image_run`. Best-effort: provider tắt/ref thiếu → `image_run_path: None`, không chặn text vẫn lên hàng duyệt.
- **Chưa làm:** ảnh chưa được đính vào payload webhook Make.com thật (`MakeGatewayAdapter`/`ZaloOAAdapter` payload hiện chỉ có text) — cần thêm bước upload ảnh lấy URL công khai (như Google Drive upload của VenHoSocialManager cũ) trước khi Make.com dùng được.

**5) M08 Analytics thật — `growth_orchestrator/bridges/m08_analytics_bridge.py`:**
- `observe(publication_id)` hết trả `pending_observation` giả — đọc `PublicationRegistry`, nếu có `platform_post_id` thật thì chạy đúng chain `analytics_feedback` đã có sẵn (standardize → baseline → score → sentiment → advisory → report), lưu vào các store thật.
- **Giới hạn thật, nói rõ:** `metrics_adapter_factory` mặc định `MockMetricsAdapter` — **chưa có adapter thật gọi Facebook/Instagram Insights hay Zalo OA analytics** (cần API credentials riêng, là việc khác hẳn "nối M08 vào growth_orchestrator"). Khi có adapter thật, chỉ cần đổi factory, phần còn lại (scoring/sentiment/advisory) đã thật.

**Sửa phụ trong lượt này:**
- `image_studio_runtime/adapters/mock_image_provider.py`: thêm `reference_images` kwarg (không dùng) để cùng interface với `GPTImageProvider`, tránh `TypeError` khi test tiêm Mock vào code path có ref ảnh.
- **Phát hiện + né rủi ro thật:** `providers/openai_provider.py` gọi `load_dotenv(BASE_DIR / ".env")` ở top-level module — nếu bất kỳ test nào import module này (vd `tests/test_phase8.py`), nó nạp `OPENAI_API_KEY` thật từ file `.env` (khác `.env.local`) vào `os.environ` cho **cả tiến trình pytest**, khiến `run_daily_cycle`'s test không tiêm provider rõ ràng vô tình gọi API thật → 401 lỗi (key có vẻ đã hết hạn/sai). Đã tự sửa phần của mình (mọi test daily_cycle giờ luôn truyền `generate_image=False` hoặc provider giả tường minh, không dựa vào default đọc env). **Chưa sửa `providers/openai_provider.py`** — nằm ngoài phạm vi việc 1-5, nhưng đây là rủi ro thật (secret thật rò vào toàn bộ tiến trình test) nên cần Harry biết.
- `tests/test_growth_phase1_policy_registry.py`: thêm `reference_assets.yaml` vào danh sách file bắt buộc (test cũ enumerate chính xác, tôi thêm 1 file mới phải cập nhật theo).

**Verify:** `/usr/bin/python3 -m pytest -q` → 598 passed (588 prior + 10 mới thật sự chạy, không tính lại các test cũ), `compileall` sạch, chạy tay `venho-growth daily-cycle`/`list-pending`/`approve-and-dispatch`/`venho-research load-seed-facts` đều đúng như mô tả.

---

### Growth Agent v3.1 — 3 gap cutover: lịch + Approve bridge + ảnh thật (2026-08-04)

**Status: DONE (từng phần đúng scope, có test) · Xem "KHÔNG làm" cuối mỗi mục — vẫn còn việc thật trước khi tắt VenHoSocialManager**

Harry: "Làm cả 3, theo thứ tự" (lịch T2/T4/T6/T7 → Approve trên Dashboard → ảnh). Cả 3 đều DONE ở mức "glue thật, có test, không giả vờ" — không phải rebuild toàn bộ v3.1 master plan (trend scanning thật, special-lane candidate typing đầy đủ vẫn chưa có).

**1) `growth_orchestrator/application/daily_cycle.py::run_daily_cycle(day)` — mới:**
- Đọc `config/projects/venho_hotel/content/content_pillars.yaml` (thêm `special_topics` cho lane Saturday — khớp đúng field `saturday: type=special, lane=special` đã có sẵn trong `growth/cadence_policy.yaml`, hoá ra Harry's "thêm T7" đã match thiết kế cũ có sẵn, không phải xây từ đầu).
- Rotation cursor riêng cho lane `regular` (Mon/Wed/Fri) và `special` (Sat), lưu `data/projects/venho_hotel/growth/rotation_state.json`.
- Với mỗi platform (facebook/instagram/threads/zalo) gọi thật `content_studio.generate_content()` (không phải giả) → 1 draft/publication.
- Reserve 1 dòng `PENDING_APPROVAL` trong `PublicationRegistry` mỗi platform (tái dùng registry đã có, không tạo store mới) — **không dispatch gì cả**, đúng quyết định của Harry là publish do Approve kích hoạt chứ không phải cron.
- CLI: `venho-growth daily-cycle [--day monday]` (tự resolve theo Asia/Ho_Chi_Minh nếu không truyền `--day`).
- `.github/workflows/growth-daily-cycle.yml` mới: cron `0 1 * * 1,3,5,6` (01:00 UTC = 08:00 ICT, Mon/Wed/Fri/Sat) + `workflow_dispatch`. Vì `data/` bị gitignore, step cuối `git add -f` rotation_state.json + registry + content output rồi commit/push — cùng gotcha đã ghi nhận ở workflow cũ VenHoSocialManager.
- **Lưu ý xung đột giờ:** Harry nói 8AM trong hội thoại này; `cadence_policy.yaml` (khoá từ trước, comment "TR-D2: Harry locked this in directly") ghi `publish_time: "09:00"` với preflight 08:45. Tôi dùng 8AM theo yêu cầu mới nhất — nếu 09:00 mới đúng thì chỉ cần sửa 1 dòng cron.
- **KHÔNG làm:** brief thật từ trend-scanning (`trend_lane.py`/`special_lane.py` chưa có nguồn dữ liệu thật) — `special_topics` hiện là danh sách Harry tự biên soạn tay, không phải AI tự phát hiện sự kiện/xu hướng.

**2) Approve trên VENHO OS Dashboard → dispatch thật — mới:**
- `growth_orchestrator/application/approve_and_dispatch.py::approve_and_dispatch(publication_id, approved_by)` — chỉ approve được dòng đang `PENDING_APPROVAL`, gọi `M07PublishingBridge.dispatch()` thật (Make.com webhook, không phải mock), ghi `approved_by` + status mới vào registry. Lỗi dispatch → `GATEWAY_ERROR`, không tự revert approval (operator retry dispatch thay vì duyệt lại).
- CLI: `venho-growth list-pending`, `venho-growth approve-and-dispatch --publication-id X --approved-by Y`.
- **Cross-repo `venho-os` (Next.js, chạy `npm run dev` local trên máy Harry, chưa deploy public):** đọc code xong mới biết section "Publishing & Schedule" hiện tại là hệ thống **cũ** (duyệt topic cho VenHoSocialManager, không đụng Python). Đã thêm mới, theo đúng pattern shell-out `child_process.execFile` đã có sẵn cho `generate-image`/`observe` (không phải tự nghĩ ra cách mới):
  - `src/app/api/v1/studio/growth/pending/route.ts` (GET, shell `venho-growth list-pending`)
  - `src/app/api/v1/studio/growth/[id]/approve/route.ts` (POST, shell `venho-growth approve-and-dispatch`, `approved_by` lấy từ session email thật — không tin client gửi lên, giống pattern route Luna approve có sẵn)
  - `PublishingSection.tsx` thêm block `GrowthApprovalQueue` (bảng bài chờ duyệt + nút "Duyệt và đăng") phía trên bảng topic-schedule cũ (đổi tên block cũ thành "(legacy)" cho rõ)
  - Cả 3 file đã qua `tsc --noEmit` + `eslint` sạch. **`/api/v1/studio/**` đã có RBAC `studio:write` qua `proxy.ts` có sẵn — không cần thêm permission logic mới.**
  - **CHƯA test qua browser thật** (không mở dev server song song vì có thể trùng port với phiên Harry đang chạy) — chỉ verify tĩnh (typecheck/lint).
  - **⚠️ QUAN TRỌNG: KHÔNG commit gì bên `venho-os`.** Repo đó đang có rất nhiều thay đổi chưa commit của Harry (~60 file, có vẻ là 1 đợt refactor design-token/màu sắc xuyên suốt app) từ trước khi tôi động vào — trong đó `PublishingSection.tsx` cũng nằm trong đợt refactor đó. Diff của tôi giờ nằm lồng trên working tree hiện tại của Harry; tôi cố tình để nguyên chưa `git add`/`git commit` gì ở `venho-os` để Harry tự review và commit theo nhịp của Harry, tránh gộp nhầm 2 việc không liên quan vào 1 commit.

**3) `image_studio_runtime/adapters/gpt_image_provider.py::GPTImageProvider` — thật, không còn `NotImplementedError`:**
- `generate(prompt, size, quality, reference_images=None)` — text-to-image qua `client.images.generate()`, hoặc `client.images.edit()` khi có `reference_images` (khớp đúng yêu cầu CLAUDE.md "text-only 6-8.4/10, edit+ref 9/10"). `client` tiêm được (mặc định `openai.OpenAI()` đọc `OPENAI_API_KEY`) — test dùng fake client, 0 API call thật.
- `map_api_size`/`map_api_quality`: prompt_contract dùng size kiểu "1024x1280" (không phải size hợp lệ của API) → snap về đúng 1 trong 4 size gpt-image hỗ trợ (`1024x1024`/`1024x1536`/`1536x1024`/`auto`).
- `gpt_image_provider_from_env(env)` — chỉ bật khi có `OPENAI_API_KEY` thật (không phải placeholder `YOUR_...`).
- `image_studio_runtime/application/generate_image.py::generate_image_run()` thêm param `reference_images: list[bytes] | None` — forward xuống provider khi có, không đổi behaviour cũ khi không truyền (test cũ `test_growth_phase3_image_runtime.py` không cần sửa).
- **KHÔNG làm — gap thật còn lại:** chưa có bước resolve `reference_asset_ids` (chuỗi ID trong `scenario_registry.yaml`, ví dụ `venho_rooftop_railing_approved`) thành file ảnh thật trên đĩa để lấy `bytes` truyền vào `reference_images` — hiện tại `reference_images` phải truyền tay. Ảnh ref thật của Linh An/khách sạn nằm ở `venho-os/ops/VenHoSocialManager/assets/` (cross-repo). Và **`generate_image_run()` chưa được gọi từ `daily_cycle.py`** — content pipeline hàng ngày vẫn chưa tự sinh ảnh, chỉ mới "provider hoạt động thật khi được gọi".

**Verify:** `/usr/bin/python3 -m pytest -q` → 588 passed (572 prior + 16 mới: 4 daily_cycle + 4 approve_and_dispatch + 8 image_provider). `compileall` sạch toàn repo.

---

### Growth Agent v3.1 — M07 platform routing + Make adapter real webhook, + audit cutover thay VenHoSocialManager (2026-08-04)

**Status: DONE (phần trong repo này) · Cutover thật (schedule + Approve UI + ảnh) CHƯA làm — xem audit bên dưới**

Harry chốt: Growth Agent v3.1 **thay thế hoàn toàn** hệ thống cũ `VenHoSocialManager` (GitHub Actions T2/T4/T6, đăng thẳng FB/IG/Threads qua Make.com), không chạy song song. Thêm T7 (1 bài content đặc biệt) cùng giờ 8AM. Yêu cầu cụ thể + việc đã làm/audit:

**1+2. Nối M07 thật + tái dùng Make scenario cũ cho FB/IG/Threads — DONE:**
- `growth_orchestrator/bridges/m07_publishing_bridge.py::M07PublishingBridge.dispatch()` hết là stub — giờ route theo `command["platform"]`: `zalo`/`zalo_oa` → `ZaloOAAdapter`, còn lại (`facebook`/`instagram`/`threads`) → `MakeGatewayAdapter`. Thêm `m07_publishing_bridge_from_env(env)` build cả 2 adapter từ `.env.local` (disabled mặc định nếu thiếu config — không raise, vì rollout theo từng platform).
- `publishing_gateway/adapters/make_gateway.py::MakeGatewayAdapter` giờ bắn webhook thật (mirror y hệt pattern `ZaloOAAdapter` đã làm lượt trước) — `webhook_url`/`webhook_secret`/`http_post` tiêm được, ký HMAC `X-Venho-Signature` khi có secret, `GATEWAY_ERROR` khi webhook lỗi thay vì raise. `.env.example` thêm `MAKE_WEBHOOK_URL`/`MAKE_WEBHOOK_SECRET` — Harry trỏ vào đúng scenario Make.com cũ (Webhooks → HTTP Get a file → Facebook Pages Create a Post) để tái dùng thay vì tạo mới.
- `growth_orchestrator/application/daily_dispatch.py::daily_dispatch()` nhận thêm `bridge` param tiêm được (mặc định `M07PublishingBridge()` — backward-compat).
- Tests mới (+8) trong `tests/test_growth_v3_1_real_providers.py`: Make adapter forward/sign/error, bridge route đúng platform → đúng adapter, `daily_dispatch` dùng bridge tiêm vào, `m07_publishing_bridge_from_env` bật/tắt đúng theo env.

**3. Lịch T2/T4/T6/T7 8AM — CHƯA làm, phát hiện gap kiến trúc thật:** repo này **chưa có `.github/workflows/` nào cả** và **chưa có lệnh orchestrate "chạy cả ngày" nào** — `growth_orchestrator/` có các bước rời (`preflight`, `trend_lane`, `special_lane`, `run_content_pipeline`, `manage_queue`, `daily_dispatch`...) nhưng không có 1 CLI/command nào nối chúng thành pipeline sinh nội dung → xếp hàng duyệt → dispatch. VenHoSocialManager hiện làm tất cả trong 1 script chạy 1 lần/cron; Growth Agent v3.1 chưa có tương đương. Cần thiết kế trước khi build workflow, không phải chỉ thêm dòng cron.

**4. "Approve" trên VENHO OS Dashboard — CHƯA làm, phát hiện gap kiến trúc quan trọng hơn:** đã đọc `venho-os/src/components/os/sections/PublishingSection.tsx` + `venho-os/src/app/api/v1/studio/topic-schedule/route.ts` (cross-repo, chỉ đọc). Phần "Publishing & Schedule" hiện tại trên dashboard là **hệ thống cũ** — duyệt **topic** (title/brief/pillar) cho VenHoSocialManager generate sau, PATCH ghi + `git commit` thẳng vào 1 file JSON, **không hề gọi vào Python `venho-ai-studio` hay `PublicationRegistry`/M07 nào cả**. Nút "Approve" mà Harry mô tả (đăng ngay sau khi bấm) **không tồn tại** dưới dạng này trong code hiện tại — cần xây mới: 1 section/API route mới trong `venho-os` đọc `PublicationRegistry` (Python, qua CLI shell-out hoặc 1 API nội bộ) rồi gọi `M07PublishingBridge.dispatch()`.

**5. Tạo ảnh — CHƯA làm, audit xác nhận gap:** `content_studio/builders/social_builder.py::mock_social_generator` chỉ trả text field giả, không hề gọi AI thật — **Growth Agent hiện không tạo ảnh**. Tin tốt: `prompt_studio` (M02) đã build prompt ảnh thật từ DNA (`venho prompt --type image`, complete, có test) — thiếu đúng 1 bước là adapter gọi OpenAI images API (gpt-image-2 + ref ảnh) từ prompt đó, theo đúng pattern dependency-injected-HTTP đã dùng cho Tavily/Telegram/Zalo lượt trước. Đây là việc lớn nhất còn lại, cần làm riêng 1 lượt.

**6. Tắt VenHoSocialManager sau cutover — chưa tới, phụ thuộc 3+4+5 xong trước.**

**Verify:** `/usr/bin/python3 -m pytest -q` → 572 passed (564 prior + 8 mới), `compileall` sạch.

---

### Content Studio — Zalo platform rules + CTA hotline riêng (2026-08-03)

**Status: DONE**

Harry: khách Zalo ở Việt Nam thích ngắn gọn, trực diện, có thông tin liên hệ/đặt phòng rõ ràng — cần Zalo CTA riêng "Liên hệ Hotline/Zalo 0936871234 để đặt phòng view Hồ Tây ngay hôm nay". Thay vì dặn AI Agent bằng lời mỗi lần (dễ quên/không nhất quán), wire thẳng vào config + pipeline M02 Prompt Studio (deterministic, có test) — đúng nguyên tắc "config-first" của hệ thống.

- **`content_studio/schemas/content_request.py`:** thêm `"zalo_post"` vào `ContentType` Literal (trước đó `ContentRequest` không thể biểu diễn Zalo — thiếu hoàn toàn).
- **`content_studio/content_engine.py::_builder_for`:** route `zalo_post` vào `build_social_draft` (cùng nhóm social với facebook/instagram/threads/tiktok, không phải longform).
- **`config/projects/venho_hotel/content/platform_rules.yaml`:** thêm `zalo:` — `max_length: 300` (ngắn hơn cả `threads` 500, đúng yêu cầu "ngắn gọn hơn Facebook"), `max_hashtags: 0` (văn hoá Zalo không hashtag-search như FB/IG).
- **`config/projects/venho_hotel/prompt_rules.yaml`:** thêm `platform_cta_overrides.zalo` — đúng nguyên văn CTA Harry đưa, kèm SĐT `0936871234`. Đặt ở đây (prompt layer) chứ không phải `content/` — vì `load_content_config()` đã có sẵn quy tắc cứng cấm `content/cta_rules.yaml` tồn tại (raise `ContentConfigError`), buộc CTA phải sống ở tầng prompt.
- **`prompt_studio/builders/content_prompt_builder.py`:** `render_final_prompt()`/`build_content_prompt()` thêm tham số `platform: Optional[str] = None`; dòng `Call-to-action:` trong `final_prompt` giờ chọn `platform_cta_overrides[platform]` nếu có, fallback về `cta_rule` chung — backward-compat 100% (không truyền `platform` → hành vi y hệt cũ, test cũ không cần sửa).
- **`content_studio/prompt_bridge.py`:** truyền `platform=request.platform` (property có sẵn, tách từ `content_type`) vào `build_content_prompt`.
- Verify validator: `validator_studio/content_validator.py::_score_cta` chấm theo từ khoá chung (`CTA_TERMS` có "liên hệ", "đặt phòng") chứ không so khớp chuỗi `cta_rule` cụ thể → CTA Zalo mới vẫn được chấm điểm đúng, không cần sửa validator.
- Tests mới: 2 test trong `test_content_prompt_builder.py` (platform="zalo" → có override + SĐT; platform khác → giữ cta_rule chung, không có SĐT) + 1 test end-to-end trong `test_content_studio.py` (generate `zalo_post` → hashtags rỗng, `max_length` ngắn hơn facebook, `final_prompt` chứa SĐT).

**Lưu ý phạm vi:** đây là tầng *sinh nội dung* (M02/M05, dùng cho pipeline Growth Agent v3.1 mới). Hệ thống social cũ (`VenHoSocialManager` ở repo `venho-os`, chạy T2/T4/T6 qua GitHub Actions cho FB/IG/Threads) là pipeline riêng, không đọc `platform_rules.yaml`/`prompt_rules.yaml` này — nếu muốn Zalo CTA áp dụng ở đó cũng phải sửa riêng bên `venho-os`.

**Verify:** `python3 -m pytest -q` → 564 passed (561 prior + 3 new), 0 API call. `compileall` sạch.

### Growth Agent v3.1 — Zalo OA publish qua Make.com webhook (2026-08-03)

**Status: DONE (adapter-level) · Cross-repo wiring (nút Approve trên VENHO OS Dashboard → gọi adapter này) CHƯA làm**

Harry chốt quyết định kiến trúc: `ZaloOAAdapter` **không tự gọi API Zalo trực tiếp** — chỉ bắn webhook sang Make.com; module HTTP/Custom API Request trong Make.com (Harry tự cấu hình trong Make UI) mới là nơi gọi API Zalo OA thật, ngay sau khi bấm "Approve" trên VENHO OS Dashboard. Lý do hợp lý: Zalo OA không có API "đăng bài công khai" như Facebook Page, nên chọn đúng endpoint (broadcast/article/consultation message) là quyết định Harry tự làm trong Make.com, code không cần đoán.

- **`publishing_gateway/adapters/zalo_oa.py`:** `ZaloOAAdapter` thêm `webhook_url`, `webhook_secret` (optional, ký HMAC-SHA256 header `X-Venho-Signature` — cùng convention với `approval_verifier.build_approval_signature`), `access_token_provider` (callable, gọi 1 lần/`send()` để lấy access_token Zalo tươi — dùng để wrap `refresh_zalo_access_token` đã có, giữ toàn bộ logic OAuth refresh trong Python thay vì lặp lại trong Make.com), `http_post` (tiêm được, test không gọi mạng thật). **Không có `webhook_url` → giữ nguyên hành vi mock cũ** (backward-compat với `tests/test_growth_v3_1_cadence_infra.py` đã có, không sửa test cũ). Có `webhook_url` → POST payload `{publication_id, idempotency_key, platform: "zalo_oa", content, access_token?}` sang Make.com, lỗi HTTP trả về `GATEWAY_ERROR` thay vì raise (đúng pattern accept-async-then-callback đã có ở `callback_receiver.py`).
- `.env.example` thêm `ZALO_APP_ID`/`ZALO_APP_SECRET` (thiếu từ lượt trước) + `MAKE_ZALO_WEBHOOK_URL`/`MAKE_ZALO_WEBHOOK_SECRET` (mới).
- Tests mới trong `tests/test_growth_v3_1_real_providers.py` (+4): không có webhook_url → mock cũ; có webhook_url + access_token_provider → đúng URL/payload; có webhook_secret → đúng chữ ký; webhook lỗi → `GATEWAY_ERROR`.

**KHÔNG làm trong lượt này — đây là gap thật, không phải việc nhỏ:**
- **`growth_orchestrator/bridges/m07_publishing_bridge.py::M07PublishingBridge.dispatch()` vẫn là stub thuần** — trả `GATEWAY_ACCEPTED` giả, **không gọi `ZaloOAAdapter` hay adapter nào cả**. Route theo platform (`command["platform"] == "zalo_oa"` → gọi `ZaloOAAdapter.send()`) chưa được nối.
- **Nút "Approve" trên VENHO OS Dashboard nằm ở repo khác (`venho-os`, TypeScript/Next.js)** — chưa xác nhận nó gọi vào M07 của repo Python này bằng đường nào (CLI bridge? API nội bộ?). Đây là việc cross-repo, cần kiểm tra `venho-os` riêng trước khi nói "bấm Approve là tự đăng" đã hoạt động thật.
- Chưa test tay với `MAKE_ZALO_WEBHOOK_URL` thật (chưa có scenario Make.com nào được tạo).
- Callback ngược từ Make.com báo kết quả thật (PUBLISHED/FAILED) sau khi Zalo nhận tin — `callback_receiver.py` đã có sẵn cơ chế chung (HMAC + idempotency) nhưng chưa xác nhận Make.com scenario có gọi lại đúng shape.

**Verify:** `python3 -m pytest -q` → 561 passed (557 prior + 4 new), 0 API call. `compileall` sạch.

### Growth Agent v3.1 — Real provider wiring: Tavily + Telegram + Zalo token refresh (2026-08-03)

**Status: DONE (transport + Tavily + Telegram + Zalo refresh) · Zalo message-send CHƯA làm — cần Harry xác nhận use-case**

Harry đã có `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, `ZALO_ACCESS_TOKEN` + `ZALO_REFRESH_TOKEN` + `ZALO_APP_ID` + `ZALO_APP_SECRET` trong `.env.local`. **Phát hiện + vá ngay lỗ hổng bảo mật:** `.env.local` chưa từng nằm trong `.gitignore` (chỉ chặn đúng tên `.env`) — chưa từng bị commit (đã kiểm tra `git log`) nhưng có nguy cơ rò rỉ ở lần commit tới. Sửa `.gitignore` thành `.env.*` + `!.env.example`. Cũng đổi tên 2 biến gõ sai (`zalo_appp_id`, `app_secret_key`) thành `ZALO_APP_ID`/`ZALO_APP_SECRET` (chỉ đổi tên key, không đụng giá trị).

- **`shared/http.py` (mới):** `urllib_post`/`urllib_post_form`/`urllib_get` — transport HTTP dùng chuẩn thư viện (`urllib`), không thêm dependency mới (project chưa có `requests`/`httpx`). Mọi adapter nhận transport qua tham số tiêm vào (`http_post=None` → mặc định dùng transport thật), test luôn tiêm fake nên vẫn giữ 0 API call trong suite.
- **`shared/notify/telegram.py`:** `TelegramNotifier` giờ mặc định dùng `urllib_post` thật thay vì bắt buộc tiêm; thêm `telegram_notifier_from_env()` đọc `TELEGRAM_BOT_TOKEN` từ env, raise `KeyError` nếu thiếu.
- **`research_engine/trend_radar/collectors/tavily_search.py`:** thêm `collect_tavily_search(query, api_key=..., http_post=...)` gọi `https://api.tavily.com/search` thật, chuẩn hoá kết quả thành entry R0 (`id`/`title`/`source_uri`/`snippet`/`relevance_hint`) — phân loại geographic/thematic/actionability/brand_safety_category vẫn ở downstream (`scan_trends`), không đoán ở tầng collector. Giữ nguyên `collect_tavily_search_stub()` cũ.
- **`publishing_gateway/adapters/zalo_oa.py`:** thêm `refresh_zalo_access_token(app_id, app_secret, refresh_token)` — gọi đúng chuẩn Zalo OAuth v4 (`POST https://oauth.zalo.me/v4/oa/access_token`, body `x-www-form-urlencoded`, `app_secret` truyền qua header `secret_key`, không phải JSON/query string). **`ZaloOAAdapter.send()` thật (gửi tin) CHƯA làm** — Zalo OA không có API "đăng bài công khai" như Facebook Page; gửi tin thật cần nhắm vào một `user_id` follower cụ thể (cửa sổ tư vấn 7 ngày) hoặc template broadcast đã duyệt. Đoán sai endpoint/payload ở đây có thể tốn quota thật hoặc gửi nhầm đối tượng — để nguyên chờ Harry xác nhận: Zalo dùng làm kênh alert nội bộ (giống Telegram, gửi cho `user_id` của Harry) hay kênh publish content cho khách/follower?
- **Không tự bật feature flag nào** (`trend_radar_enabled`, `zalo_enabled`, `real_meta_insights_enabled`...) — có key thật rồi nhưng bật flag nghĩa là bắt đầu gọi API/gửi tin thật, để Harry chủ động quyết định sau khi review.
- Tests mới: `tests/test_growth_v3_1_real_providers.py` (8 test) — Telegram dùng đúng transport thật mặc định + gửi đúng URL/payload khi tiêm fake + `from_env` thiếu token raise; Tavily raise nếu thiếu key + chuẩn hoá đúng kết quả; Zalo refresh raise nếu thiếu credential + đúng form-body/header.

**KHÔNG làm trong lượt này:**
- `ZaloOAAdapter.send()` thật — cần Harry xác nhận use-case (alert nội bộ hay publish content) trước khi chọn đúng endpoint.
- Weather API, Exa, YouTube Data — Harry chưa cung cấp key cho các dịch vụ này.
- Bật bất kỳ feature flag nào hoặc gọi thử API thật (kể cả Telegram/Tavily) — chưa có test tay/manual smoke test với key thật.

**Verify:** `python3 -m pytest -q` → 557 passed (549 prior + 8 new), 0 API call. `python3 -m compileall` sạch.

### Growth Agent v3.1 — Delta so với v3.0 (cadence, weather, infra) (2026-08-03)

**Status: DONE (phần code/test) · Vật lý (Mac Mini thật, API key thật) là việc của Harry, ghi rõ bên dưới**

Đọc `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` và so khớp với những gì Codex đã build cho v3.0 (Phase 1–8). Phần lớn kiến trúc v3.1 đã có sẵn trong code cũ (contracts, jobs, budget, facts, image runtime, approval, scheduler, analytics, strategy memory, controlled rollout, và cả `research_engine/trend_radar/` với brand safety gate + relevance scoring + 5 collector stub). Delta thực sự cần build:

- **Cadence 4 bài/tuần (TR-D2, PB-001):** `config/.../growth/cadence_policy.yaml` v1→v2 — bỏ ramp A(3)→B(5)→C(7), cố định T2/T4/T6 (regular) + T7 (special) + blog SEO thứ 3. `growth_orchestrator/domain/publishing_slot.py` — state machine `OPEN→DRAFT_ASSIGNED→PENDING_APPROVAL→FILLED→DISPATCHED→COMPLETED` + nhánh `EVERGREEN_FALLBACK` + `MISSED` (chỉ hợp lệ sau khi evergreen cạn — có assert riêng). `growth_orchestrator/application/manage_slots.py` — sinh slot xác định (deterministic, idempotent) trước 14 ngày từ cadence policy.
- **Runway theo slot, không theo ngày (PB-003):** `queue_policy.yaml` đổi `runway_days`→`runway_slots` (healthy≥6, warning 4–5, critical 2–3, empty 0–1) theo đúng bảng §9.2; `manage_queue.runway_status()` cập nhật theo, giữ fallback đọc `runway_days` cũ nếu còn nơi nào dùng.
- **Special lane T3→T7, 4 loại có fallback bắt buộc (PB-008):** `growth_orchestrator/application/special_lane.py` — `select_special_lane_candidate()` ưu tiên seasonal_nature > cultural_event (chỉ nhận nếu `verified_by_human`) > lifestyle_trend > feature_story (fallback bắt buộc, raise nếu không có); `special_lane_timeline_state()` — cutoff cứng T6 20:00 rơi về `fallback_evergreen` nếu chưa duyệt.
- **Pre-flight 08:45 (PB-005):** `growth_orchestrator/application/preflight.py::run_preflight_check()` — kiểm fact hết hạn, approval còn hiệu lực, asset còn truy cập (hash khớp), event còn `verified_by_human` và chưa qua `event_end`, weather R2-T còn hạn. Trả về danh sách lý do fail cụ thể, không chỉ true/false.
- **Weather signal — R2-T, không bao giờ là claim (§5.5, §6.6):** `research_engine/trend_radar/domain/weather_signal.py::WeatherSignal` — field `fact_key` khóa cứng `Literal[None]` (Pydantic tự raise nếu ai cố gán giá trị khác None — enforce ở tầng type, không chỉ ở validator). `contracts/weather_signal.schema.json` cũng khóa `fact_key: const null`. `research_engine/trend_radar/application/scan_weather.py::scan_weather()` — `expires_at` luôn tính từ `weather_policy.yaml["expiry_hours"]` (24–48h), **không bao giờ lấy từ provider** (chống provider trả về TTL dài hơn policy cho phép). Collector `weather_api.py` là stub rỗng như 5 collector khác đã có.
- **Tavily/Exa collector (TR-002):** `tavily_search.py`, `exa_search.py` — stub rỗng cùng pattern với `news_rss.py`/`google_trends.py` đã có, feature-flag off, chờ API key thật.
- **`shared/notify/telegram.py` (IN-D4):** `MockTelegramNotifier` (mặc định trong test) + `TelegramNotifier` thật (cần `bot_token` + `http_post` tiêm vào, chưa gọi network thật ở đâu). `send_alert()` đọc `shared/notify/alert_policy.yaml` để map event→severity/channel, raise nếu event không có trong registry (chống gõ sai tên event).
- **`publishing_gateway/adapters/zalo_oa.py` (IN-D5):** mirror hệt `make_gateway.py` — `enabled=False` mặc định trả `DISABLED`, bật flag mới trả `GATEWAY_ACCEPTED` (không phải `PUBLISHED`).
- **`infra/` package mới hoàn toàn (Phần 10, IN-001/002/003):**
  - `heartbeat.py` — `build_heartbeat_payload()` + `send_heartbeat()` (nhận `http_post` tiêm vào, không tự gọi network) + `is_heartbeat_stale()`.
  - `deadman_config.yaml` — ngưỡng heartbeat 5 phút/stale 15 phút, mốc dispatch check 09:15/09:30/10:00 đúng §9.4.
  - `cloud_fallback/export_approved.py` — `export_approved_package()` chỉ nhận package đã `approval_status=approved`, ký HMAC-SHA256, ghi file; **không có tham số hay code path nào set `approval_status`** — bất biến bảo mật §10.4/§15.15 được enforce bằng cấu trúc hàm chứ không chỉ bằng lời hứa trong docstring. `verify_export_signature()` để bên nhận (cloud) verify trước khi replay.
  - `backup.sh` — `sqlite3 .backup` + copy artifacts + `rclone` off-site nếu remote `venho-cloud` đã cấu hình (bỏ qua có log rõ nếu chưa).
  - `launchd/*.plist` × 5 (research.daily, trend.scan, pipeline.worker, dashboard, dispatch) — đúng lịch trong §10.2.
  - `setup_macmini.md` — runbook `pmset`/`launchd`/Tailscale cho Harry, không phải code, chỉ tài liệu.
- **Contracts:** thêm `weather_signal.schema.json` + `publishing_slot.schema.json` + fixtures valid/invalid → tổng **17 schema** (đếm lại chính xác từ danh sách liệt kê §5.10 của plan — header ghi "16" nhưng liệt kê ra 17 mục, đây là lỗi đánh máy trong chính tài liệu v3.1, không phải lỗi ở đây).
- `pyproject.toml` — thêm `infra*` vào package discovery.
- Tests mới: `tests/test_growth_v3_1_cadence_infra.py` (31 test) — cadence/slot generation, PublishingSlot state machine (kể cả forbidden transition + MISSED-requires-evergreen-exhausted), runway theo slot, special lane 4 loại + fallback + cutoff, pre-flight (happy path + mọi lý do fail cùng lúc), weather signal không bao giờ có fact_key + expiry policy-driven, Telegram mock alert + unknown-event guard, Zalo adapter disabled/enabled, heartbeat + staleness, cloud fallback export (từ chối package chưa duyệt, ký/verify không tạo approval mới).

**KHÔNG làm trong lượt này (cần Harry, ngoài phạm vi code):**
- Mua/cấu hình Mac Mini M4 vật lý, chạy `pmset`/`launchd` thật, cài Tailscale — `infra/setup_macmini.md` là runbook, chưa có máy nào chạy nó.
- Đăng ký + lấy API key thật: Tavily/Exa (search), Weather API, YouTube Data API, Telegram Bot Token, Zalo OA app — mọi collector/adapter vẫn ở dạng stub/mock/flag-off cho tới khi có key.
- Cấu hình `healthchecks.io` hoặc Make.com data store làm endpoint heartbeat/cloud fallback thật.

**Verify:** `python3 -m pytest -q` → 549 passed (518 prior + 31 new), 0 API call. `python3 -m compileall` sạch trên toàn bộ package đã đổi.

### Growth Agent v3.0 — QC Pass on Phase 4–8 (2026-08-03)

**Status: DONE**

Senior QC review of the Codex-authored Phase 4–8 code (`shared/jobs` extensions, `shared/budget` extensions, `publishing_gateway/publication_registry.py` + `callback_receiver.py`/`reconciliation.py`/`adapters/make_gateway.py`, `automation_studio/approval_snapshot.py`, `controlled_rollout/`, `productize/`, `strategy_memory/`, `analytics_feedback` additions). 1 real bug fixed, covered by a new regression test in `tests/test_growth_qc_hardening.py`:

- **Concurrency bug (`publishing_gateway/publication_registry.py`):** `reserve()` and `update()` did an unlocked JSON-file load → modify → save. Two concurrent callers (e.g. a retried dispatch racing an inbound webhook callback) could both read the same on-disk state before either write landed, so the second writer would silently clobber the first — defeating the exact idempotency guarantee the registry exists to provide. The Phase 4 "duplicate chaos" test (`test_duplicate_chaos_reserves_one_publication`) only calls `reserve()` sequentially in a single thread, so it never actually exercised this race. Fixed by wrapping both methods in an `fcntl.flock` exclusive lock on a sibling `.lock` file, serializing the read-modify-write across processes/threads. Added `test_publication_registry_reserve_is_race_free_under_concurrent_threads` (20 real threads via `ThreadPoolExecutor`) to prove exactly one publication survives.
- Reviewed and found clean (no changes needed): `shared/jobs/job_store.py` extensions (heartbeat/lease-recovery/retry-requeue all remain single-atomic-statement SQLite ops, consistent with the earlier `claim()` fix), `shared/budget/ledger.py` (SQLite-backed, no cross-process race), `automation_studio/approval_snapshot.py` (pure deterministic checksum/revocation logic), `controlled_rollout/*`, `strategy_memory/*`, `analytics_feedback/attribution.py` + `metric_observation.py` + `meta_insights.py` + `research_question_generator.py` (the last already uses `shared/security.py::ensure_safe_slug()` from the Phase 1–3 QC pass — convention correctly picked up in new code).
- `growth_orchestrator/` re-checked: still zero references from any other package (`grep -rln growth_orchestrator`), confirms it remains inert/unwired scaffolding as flagged in the prior QC pass — no new risk introduced by Phase 4–8.
- `productize/hotel_content_engine.py` builds a path from a `project` string with no traversal guard, same pattern as the fixed `fact_key`/`rs_id` sinks — but `project` here is a deploy-time config identifier (like the existing `FactStore(project=...)` convention), not runtime-attacker-controlled input in current callers, so left as-is; worth revisiting with `ensure_safe_slug` if `project` ever becomes agent-/user-suppliable.
- Verify: `python3 -m pytest -q` → 518 passed (517 prior + 1 new), 0 API calls. `python3 -m compileall` clean across all touched packages.

### Growth Agent v3.0 — Phase 8 Controlled Rollout (2026-08-03)

**Status: DONE**

- Added `controlled_rollout/` with versioned golden scorecard evaluation, 90-day metrics readiness, rollout stage policy, rollback sequencing, and runbook validation.
- Added P8 golden gate: scorecard requires versioned eval set and `>=9.3/10`; duplicate publication and empty-day gates hard-fail.
- Added controlled rollout stages: `shadow -> pilot_25 -> pilot_50 -> pilot_100`, with human approval always required and trend lane blocked from auto-approval.
- Added rollback rules in code: dispatch must be disabled before rollback, migrations are forward-only, compatible reads required, approved artifacts immutable.
- Added `productize/hotel_content_engine.py` plus `.claude/skills/_productize/hotel-content-engine/SKILL.md`; verified hotel #2 runs by config only with `core_modified=False`.
- Added docs: `docs/growth/controlled_rollout_runbook.md` and `docs/growth/eval_golden_sets.md`, covering runbook/rollback/budget/ownership.
- Updated `pyproject.toml` package discovery for `controlled_rollout*`, `productize*`, and `strategy_memory*`.
- Tests added: `test_growth_phase8_controlled_rollout.py`.
- Verify: P8 tests -> 7 passed; Growth P1-P8/QC tests -> 63 passed; full `python3 -m pytest -q` -> 517 passed; compileall clean.

### Growth Agent v3.0 — Phase 7 Growth Intelligence Pilot (2026-08-03)

**Status: DONE**

- Added `strategy_memory/` with Bayesian-smoothed QBSR pattern inference, confidence, scope, evidence, limitations, expiry, and approval-gated promotion.
- Added `INCONCLUSIVE` handling: insufficient sample cannot become approved strategy memory.
- Added QBSR guardrail: weekly recommendations are suppressed when candidate QBSR drops below baseline guardrail.
- Added weekly strategy brief builder: advisory-only and `pending_approval` by default.
- Added M08 -> Research OS loop: analytics signals create written research questions through `M08SignalBridge`.
- Tests added: `test_growth_phase7_strategy_memory.py`.
- Verify: P7 tests -> 6 passed; Growth P1-P7/QC tests -> 56 passed; full `python3 -m pytest -q` -> 510 passed; compileall clean.

### Growth Agent v3.0 — Phase 6 Analytics + Attribution (2026-08-03)

**Status: DONE**

- Added M08 attribution helpers: `utm_content=publication_id`, direct/assisted/unattributed resolution, policy-driven dedupe fields, and SHA-256 contact pseudonymization.
- Added metric observation normalization that preserves `VALUE`, `ZERO`, `NULL`, and `UNAVAILABLE` as distinct states.
- Added source-match assertion so sample metric observations must match raw provider values.
- Added Meta Insights provider gate: real provider remains feature-flagged off; mock adapter is default.
- Updated collection windows to P6 set: `1h`, `24h`, `72h`, `7d`, `28d`.
- Added M10-style content performance view builder that reads M08 snapshots/scores only.
- Tests added: `test_growth_phase6_analytics_attribution.py`.
- Verify: P6 tests -> 6 passed; analytics + P6 tests -> 13 passed; Growth P1-P6/QC tests -> 50 passed; full `python3 -m pytest -q` -> 504 passed; compileall clean.

### Growth Agent v3.0 — Phase 5 Scheduler + Durable Ops (2026-08-03)

**Status: DONE**

- Extended `JobStore` with heartbeat tracking, lease extension, retryable-failure requeue, idempotency counting, and SQLite migration for existing DBs.
- Extended `Worker` with heartbeat and recovery helpers.
- Extended scheduler with idempotent daily dispatch enqueue and late-run alert payload.
- Extended `BudgetLedger` with committed spend projection, override recording, and policy-driven paid-call reservation.
- Added `BudgetPolicy` loader/evaluator for alert thresholds 70/85/100% and hard block at 100% unless manual override is recorded.
- Added P5 exit-gate tests: duplicate trigger creates one job, restart recovers expired lease, retry matrix requeues then terminal-fails, late run alerts, budget cap blocks with override trail.
- Tests added: `test_growth_phase5_scheduler_ops.py`.
- Verify: P5 tests -> 5 passed; Growth P1-P5/QC tests -> 44 passed; full `python3 -m pytest -q` -> 498 passed; compileall clean.

### Growth Agent v3.0 — Phase 4 Approval Exact-Versions + Reliable Publishing (2026-08-03)

**Status: DONE**

- Hardened M04 `approval_snapshot.py` with exact package-version checksum covering copy, asset, validation snapshot, fact versions, and brief version.
- Added dispatch gate: any edit after approval revokes/blocks dispatch with a stable reason.
- Added Final Review state builder for M10-style presentation: approved, pending approval, or blocked without recalculating validation in UI.
- Added M07 `PublicationRegistry` with idempotent reserve/update/find and publishable-evidence guard.
- Updated Make adapter semantics: `GATEWAY_ACCEPTED` means accepted by gateway only, never published.
- Extended callback receiver with registry application and published callback post-id requirement.
- Extended reconciliation to store `reconciliation_proof` when a platform post is found.
- Added chaos duplicate coverage: ten duplicate dispatch attempts reserve exactly one publication.
- Tests added: `test_growth_phase4_approval_publishing.py`.
- Verify: P4 tests -> 5 passed; Growth P1-P4 tests -> 33 passed; full `python3 -m pytest -q` -> 493 passed; compileall clean.

### Growth Agent v3.0 — QC Pass on Phase 1–3 (2026-08-03)

**Status: DONE**

Senior QC review of the Codex-authored Phase 1–3 code (`shared/jobs`, `shared/budget`, `knowledge_studio/facts`, `image_studio_runtime`, `research_engine`, `publishing_gateway` additions, `validator_studio` additions, `content_studio/generators`, `agent_studio/growth`). 4 real bugs fixed, all covered by new regression tests in `tests/test_growth_qc_hardening.py`:

- **Concurrency bug (`shared/jobs/job_store.py`):** `JobStore.claim()` did SELECT-then-UPDATE across two separate implicit transactions — two concurrent workers could both read the same READY job before either UPDATE landed, and both would win the claim. Rewrote as a single atomic `UPDATE ... WHERE id = (SELECT ...) RETURNING` statement (SQLite 3.51 on this machine supports `RETURNING`). Also added `PRAGMA busy_timeout = 5000` to `JobStore` and `BudgetLedger` connections to avoid spurious "database is locked" errors under concurrent access.
- **Security bug — replay protection bypass (`publishing_gateway/callback_receiver.py`):** `verify_callback_signature()` signed only the callback `body`, while `timestamp` (the actual replay-window guard) was passed in unsigned. An attacker could replay an old valid `(body, signature)` pair with a freshly forged `timestamp` and pass the "replay window" check untouched. Fixed by binding `timestamp` into the signed message (`f"{timestamp}." + body`), matching the existing HMAC convention already used in `publishing_gateway/approval_verifier.py`.
- **Security hardening — path traversal (`knowledge_studio/facts/fact_store.py`, `research_engine/adapters/notebooklm_handoff.py`, `research_engine/application/collect_sources.py`, `research_engine/application/synthesize_notes.py`):** `fact_key`, `topic_slug`, `rs_id`, `domain`, `title` were used verbatim as filesystem path components with no validation — a value like `../../etc/passwd` would escape the intended `data/` or `research/` directory on read or write. Added `shared/security.py::ensure_safe_slug()` and applied it at every sink that turns one of these identifiers into a path segment.
- `growth_orchestrator/` and `research_engine/trend_radar/` were reviewed and found to be **untested scaffolding for a later phase** (bridges return hardcoded stubs, e.g. `M07PublishingBridge.dispatch()` always returns `GATEWAY_ACCEPTED` without calling the real M07 gateway; `M05ContentBridge` reimplements a simplified 3-candidate generator instead of delegating to the real `content_studio/generators` rubric pipeline built in Phase 2). No tests reference either package. Left untouched — out of scope for this QC pass since they are not yet claimed "DONE," but flagged here so they are not mistaken for wired, safe-to-run code. `pyproject.toml` already exposes `venho-growth` as a real CLI entrypoint pointing at the stub dispatch bridge; do not run it expecting a real publish.
- Verify: `python3 -m pytest -q` → 488 passed (482 prior + 6 new), 0 API calls. `python3 -m compileall` clean across all touched packages.

### Growth Agent v3.0 — Phase 3 Image Runtime + Multimodal QC (2026-08-03)

**Status: DONE**

- Added `agent_studio/growth/scenario_registry.py` and expanded `scenario_registry.yaml` to resolve Visual DNA v2.7 subject, references, required/forbidden entities, and conflict rejection.
- Hardened `image_studio_runtime/`: mock provider with transient failure simulation, provider model metadata, immutable run storage, full paid manifest, scenario-driven DNA/reference fields, and run listing.
- Added paid image policy: one paid generation plus one targeted repair only; further repairs fail into review flow.
- Added 429/5xx provider backoff behavior: transient failure raises without creating a new run/variant artifact.
- Extended M03 `alignment_validator.py` and `derivative_validator.py` with required-subject omission, alignment score gate, crop safety, and OCR/critical text gate.
- Added `aggregate_image_verdict()` for P3 image QC final state: incomplete -> `UNVALIDATED`, kill/low alignment -> `NEEDS_REVIEW`, clean -> `APPROVED`.
- Tests added: `test_growth_phase3_image_runtime.py`.
- Verify: P3 tests -> 5 passed; Growth P1-P3 tests -> 28 passed; full `python3 -m pytest -q` -> 482 passed; compileall clean.

### Growth Agent v3.0 — Phase 1.5 Research OS Foundation (2026-08-03)

**Status: DONE**

- Added Research OS frontmatter validator and tightened `ResearchNote` invariants.
- Added R0 source collection, R1 structured note collection, R2 synthesis path, NotebookLM handoff verification, and R2/R2-T promotion policy tests.
- Added `venho-research promote` CLI path from reviewed R2 note to M01 approved KnowledgeFact through `M01FactsBridge`.
- Added stale fact detection plus approval revocation helper for packages referencing expired facts.
- Added repo seed research notes for `guest_voice`, `competitor`, and reviewed R2 guest voice synthesis.
- Enabled `research_os_enabled: true`; real providers and trend radar remain off.
- Tests added: `test_growth_phase15_research_os.py`.
- Verify: Phase tests -> 23 passed; full `python3 -m pytest -q` -> 477 passed.

### Growth Agent v3.0 — Phase 2 Knowledge Facts + Real Copy Foundation (2026-08-03)

**Status: DONE**

- Added tracked seed facts in `config/projects/venho_hotel/growth/seed_facts.json`: room count, address, Agoda review, website.
- Extended M01 `FactStore` with seed loader; `FactResolver` now handles timezone-aware validity windows.
- Improved M03 `ClaimValidator`: missing fact -> `UNSUPPORTED`, inactive/expired fact -> `EXPIRED`, critical unsupported claims kill publish path.
- Added M09 growth brief compiler + brief lifecycle: lock brief with active R3 proof points, checksum, supersede-on-edit.
- Added M05 text provider adapter, 3-candidate generator, rubric selector.
- Golden factual gate covered in tests: price, policy, review, distance claims without approved facts are blocked; approved review fact verifies.
- Harry approval gate covered: locked brief succeeds only with active R3 facts before paid generation.
- Tests added: `test_growth_phase2_knowledge_copy.py`.
- Verify: Phase tests -> 23 passed; full `python3 -m pytest -q` -> 477 passed.

### Growth Agent v3.0 — Phase 1 Contracts + Policy Registry (2026-08-03)

**Status: DONE**

- Added repo-level `contracts/` with the 15 required schemas: `creative_brief`, `knowledge_fact`, `research_note`, `trend_candidate`, `copy_candidate`, `content_package`, `image_prompt_contract`, `image_manifest`, `validation_report`, `approval_snapshot`, `publication_command`, `publication_callback`, `metric_observation`, `conversion_event`, `strategy_memory`.
- Added pass/fail fixtures under `contracts/fixtures/{schema_name}/{valid,invalid}/`.
- Added config registry under `config/projects/venho_hotel/growth/`: quality, model, budget, taxonomy, scenario, attribution, cadence, queue, feature flags.
- Added config registry under `config/projects/venho_hotel/research/`: domains, evidence, promotion, trend, brand safety, event sources.
- Added `shared/jobs/` SQLite job queue with idempotent enqueue, lease claim, expired lease recovery, completion/failure state.
- Added `shared/budget/` ledger with `RESERVE`, `COMMIT`, `RELEASE`, totals, and negative amount guard.
- Added CLI/package wiring in `pyproject.toml` for Growth-era packages and `jsonschema` test dependency.
- Tests added: `test_growth_phase1_contracts.py`, `test_growth_phase1_policy_registry.py`, `test_growth_phase1_jobs_and_budget.py`.
- Verify: `python3 -m pytest -q tests/test_growth_phase1_contracts.py tests/test_growth_phase1_policy_registry.py tests/test_growth_phase1_jobs_and_budget.py` -> 11 passed.
- Verify: `python3 -m pytest -q` -> 465 passed.

---

### SEC-01 / VAL-01 / LOC-01 — Real production blockers fixed (2026-07-17)
- **SEC-01 done.** Harry đã tự rotate API key từng lộ trong chat (ngoài repo, xác nhận trực tiếp).
- **VAL-01 fixed — root cause.** `validator_studio/prompts/observe_face_against_dna.md` chỉ đưa 1 ví dụ JSON gate (`identity_structure`), khiến LLM luôn trả về 1/3 gate dù rubric (`face_qc_rubric.yaml`) yêu cầu đủ 3 (`identity_structure`, `eye_ratio`, `forbidden_traits`) → mọi run thật bị chặn cứng bởi `Face gates mismatch`. Đã sửa prompt để yêu cầu rõ đủ 3 gate + tiêu chí chấm cho `eye_ratio`/`forbidden_traits`. Không cần sửa `face_validator.py` (logic assert đã đúng) hay OS (`requiredFaceGates` đã đúng từ trước).
- **LOC-01 fixed — root cause.** `config/projects/venho_hotel/subjects/westlake.overrides.yaml` (curated) vẫn ghi "green lamp posts, green metal lakeshore railing" — nhưng thực tế 2026 (Harry xác nhận): đường Nguyễn Đình Thi đã cải tạo, lan can hiện là **trắng ngà, không còn cột đèn xanh**, khớp với `venho-os/src/lib/studio/constants.ts`. Đã sửa overlay + re-render DNA qua `venho vision observe --mode b --project venho_hotel --subject westlake --input assets/raw/westlake --confirm-one-subject` (10/10 cache hit, 0 API call, chỉ re-render overlay).
- **Thêm cơ chế mới: scenario-aware overlay merge-at-validate-time.** `validator_studio/image_validator.py::validate_image` nhận thêm `scenario_profile_id` optional — nếu có file `config/projects/<project>/subjects/<subject>.<scenario_profile_id>.overrides.yaml`, merge overlay đó vào DNA **trong bộ nhớ lúc validate**, không đụng overlay chung, không ghi đè DNA JSON trên đĩa. Threaded qua `validation_pipeline.py`, CLI `--scenario-profile-id`, và `venho-os` (`ops/VenHoSocialManager/validate_generated.py`, `src/app/api/v1/studio/generate-image/route.ts` — `scenarioProfileId` dời lên tính sớm hơn, truyền vào `validationArgs`). File mới: `config/projects/venho_hotel/subjects/westlake.nguyen_dinh_thi_street_2026.overrides.yaml` (lan can trắng + mô tả cây khớp constants.ts).
- **Live verify thật (case E1, controlled_live_matrix.json):** running front-facing / mint_green / Nguyễn Đình Thi / face ref ON → **Image/DNA score 100, verdict approve** (xác nhận LOC-01 fix hoạt động — trước đó 84.91/revise). **Face score 85, verdict revise** (KHÔNG còn lỗi `Face gates mismatch` — xác nhận VAL-01 fix hoạt động; nhưng vẫn dưới ngưỡng approve ≥90 theo `controlled_live_matrix.json`, cần cải thiện thêm — ngoài phạm vi 2 fix này).
- **Case E5 bug fixed (2026-07-17, cùng phiên).** Root cause: `assets/Rooftop-Panorama-view.jpeg` là định dạng **MPO** (Multi Picture Object — ảnh iPhone portrait/burst chứa nhiều frame nhúng), không phải JPEG đơn thuần; `openai.images.edit` không parse được container này khi gửi làm ref-env thứ 2 → `400 invalid_image_file`. Đã convert sang PNG đơn-frame sạch (`assets/Rooftop-Panorama-view.png`, giữ nguyên file `.jpeg` gốc, không xoá) và cập nhật `ENV_REFERENCE_BY_SCENARIO["West Lake Landscape (Wide)"]` trong `constants.ts` trỏ sang file mới. **Live-verify lại E5 thành công:** HTTP 200, `referenceMode: face-and-environment`, Image/DNA score **100/approve**, Face score 83.5/revise (không lỗi contract). Lưu ý: 2 ảnh ref-env khác (`Rooftop-railing.png`, `View-Ho-room-from-inside.png`) đã kiểm tra là PNG chuẩn, không bị lỗi tương tự.
- **VAL-02 implemented (2026-07-17, cùng phiên).** Face Validator giờ so ảnh sinh ra trực tiếp với **4 ảnh reference thật** (`B3_Hero.png` primary, `A2_Front.png`, `C_LeftProfile.png`, `D_RightProfile.png`) thay vì chỉ text DNA. Thêm `shared/vision/providers/openai_vision.py::analyze_many` (multi-image payload, N ảnh/message) + `VisionClient.analyze_images`; `face_validator.py` nhận `reference_image_paths` optional (None = hành vi cũ, không phá test); thiếu file reference → raise lỗi rõ ràng trước khi gọi API (không âm thầm fallback). `venho-os/ops/VenHoSocialManager/validate_generated.py` tự truyền 4 đường dẫn chuẩn khi có `--face` — không cần sửa `generate-image/route.ts`. Test mới: `tests/test_vision_multi_image.py` (multi-image payload) + 3 test trong `test_validator_studio.py` (dùng reference, thiếu file raise lỗi, không reference giữ hành vi cũ). **450/450 pass.**
- **Live-verify E1 thật với reference thật:** report xác nhận `"compared against 4 approved reference image(s)"` và lý giải của model trích dẫn trực tiếp việc so sánh ảnh ("Comparison with reference images shows consistent facial shape..."). Face score = **82.5** (trước đó không có reference: 85) — **không cải thiện, thậm chí giảm nhẹ**. Đây là kết quả trung thực: điểm số giờ đáng tin cậy hơn (có căn cứ so sánh ảnh thật, không chỉ đoán theo text) nhưng bản thân model chấm khắt khe hơn ở `expression` (75) và `technical_quality` (70) khi có ảnh thật để đối chiếu — không phải bug, là giới hạn thật của chất lượng ảnh sinh ra.
- **Kết luận:** production-ready gate (2 run approved liên tiếp/case E1–E6) **vẫn CHƯA đạt**. Đã verify 3/6 case-run (E1 x2, E5 x1), còn E2–E4/E6 chưa chạy. Face score (82.5–85, tuỳ run) vẫn dưới ngưỡng approve 90 dù đã có VAL-02 — gap còn lại là chất lượng ảnh sinh ra thật (expression/technical_quality), không còn là lỗi validator/contract.

### ⚠️ Face Validator có dấu hiệu templating rõ ràng hơn — đã loại trừ bug cache, chưa fix (2026-07-17)
Phát hiện ban đầu: sau khi sửa prompt sinh ảnh (expression/technical_quality) và chạy live lại E1, 5 category score ra giống hệt tuyệt đối lần chạy trước (`90/85/80/75/70`).

**Đã điều tra và loại trừ nguyên nhân cache/bug code:** rà soát toàn bộ call path (`face_validator.py` → `VisionClient` → `OpenAIVisionProvider` → OpenAI API) — không có bất kỳ lớp cache/memoization nào (`grep cache|lru_cache|memoiz` toàn bộ `shared/vision/` và `validator_studio/` = 0 kết quả). Mỗi lần gọi đều tạo `VisionClient`/`OpenAI()` mới, gọi API thật. Kết luận: **không phải bug cache**, là hành vi thật của GPT-4o vision-judge ở `temperature=0.0`.

**Bằng chứng mạnh hơn từ full matrix run (xem QA-01 ở trên):** report E4 (không có face-reference, `text-to-image`) và E6 (có đủ face+env reference, `face-and-environment`) — 2 tình huống input khác biệt cực lớn — cho ra **`weighted_scores` giống hệt tuyệt đối** (`60/50/70/80/85`) và **văn bản lý giải gates giống hệt gần như từng chữ**. Ngược lại, các `gates` (True/False) thì vẫn phân biệt đúng theo có/không reference (case có identity thật sai → gates False đúng, case tạm ổn → gates True). Vậy: **phần binary gates của Face Validator đáng tin cậy; phần `weighted_scores`/text lý giải chi tiết có vẻ chỉ có ~2 "khuôn mẫu" phản hồi (một khi 'tạm ổn', một khi 'rõ ràng sai'), không thực sự phân giải theo từng ảnh cụ thể.**

**Đã xác nhận: KHÔNG PHẢI templating, mà là non-determinism thật (2026-07-17).** Thí nghiệm rẻ: chạy lại Face Validator 3 lần/ảnh trên 3 ảnh đã có sẵn (E3/E4/E6, chỉ gọi vision API chấm điểm, không tạo ảnh mới). Kết quả: E3 và E4 ổn định qua các lần lặp lại (đúng như run gốc). **E6 thì "lật kèo" thật** — cùng 1 file ảnh, cùng 4 ảnh reference, cùng code path, nhưng run gốc (qua venho-os) cho 0/reject (gates False) còn 3 lần lặp lại ngay sau đó đều cho 82.5/revise (gates True). Xác nhận: đây là non-determinism thật của GPT-4o vision-judge dù `temperature=0.0`, không phải bug code hay input khác nhau.

### Full matrix v2 với sampling — kết quả cuối cùng (2026-07-18)

Chạy lại toàn bộ E1–E6 với Face Validator sampling 3x mới (2 phiên, gián đoạn bởi 1 sự cố bảo mật — key OpenAI vô tình bị in ra transcript do lỗi lệnh `source <(...)`, đã yêu cầu Harry rotate key + kiểm tra billing — và 1 lần chạm billing hard limit thật của tài khoản, Harry đã xử lý xong cả 2):

| Case | Image | Face (sampling 3x) | Ghi chú |
|---|---:|---:|---|
| E1 | 100/approve | 82.5/revise | |
| E2 (lần 1) | 40/reject (green railing) | 83.5/revise | biến thiên ngẫu nhiên của model sinh ảnh |
| E2 (retry) | 100/approve | **0/reject** (gates False, majority vote thật) | |
| E3 | 100/approve | 82.5/revise | |
| E4 | 100/approve | 82.5/revise | |
| E5 | **40/reject** ("modern glass high-rise backdrop") | 82.83/revise | bỏ ref-env chỉ giảm bớt lỗi lẫn chi tiết sân thượng, KHÔNG giải quyết hết xu hướng model tự thêm nhà cao tầng ở góc panorama — cần siết thêm wording trong `ENV_BLOCKS` (chưa làm) |
| E6 | 100/approve | 68/regenerate | |

**Tổng kết trung thực toàn phiên (~13 run thật tính cả các vòng trước):** Face score **chưa từng đạt ngưỡng approve ≥90 dù chỉ 1 lần**, dao động 0–85 tuỳ run kể cả với cùng 1 ảnh (đã xác nhận non-determinism) và cùng sau khi có sampling 3x. Image/DNA validator giờ đáng tin cậy hơn nhiều (100/approve phần lớn, đúng khi reject — lamp post, high-rise, railing đều là lỗi thật được bắt đúng).

**Khuyến nghị cần Harry quyết định:** ngưỡng `face_identity_min: 90` trong `controlled_live_matrix.json` có thể không thực tế với khả năng hiện tại của gpt-image-2 + rubric 07F hiện có — sau ~13 run thật, chưa run nào chạm 90. Cần cân nhắc: (a) hạ ngưỡng xuống mức thực tế hơn dựa trên dữ liệu thật (vd 80-85), (b) đầu tư sâu hơn vào face fidelity (kỹ thuật khác ngoài prompt, vd inpainting/face-swap), hoặc (c) chấp nhận range hiện tại là "good enough" và định nghĩa lại production-ready. Đây là quyết định business/threshold, không phải bug — tôi không tự ý đổi ngưỡng.

**Đã fix (2026-07-17, commit `239e998` venho-ai-studio + `741f79d` venho-os):** thêm sampling — `validate_face()`/`_observe_face()` nhận tham số `samples` (mặc định 1, không đổi hành vi cũ); khi >1, gọi vision API nhiều lần và merge bằng `_merge_face_samples()`: majority-vote từng gate, trung bình từng weighted score — theo đúng pattern đã có sẵn cho Image Validator (`observe_adapter.py::_merge_samples`). `venho-os/validate_generated.py` mặc định `samples=3` cho mọi run thật (`--face-samples` để override). Live-verify qua CLI thật (3 lần gọi vision, không tạo ảnh mới) trên đúng ảnh E6 đã "lật kèo": sampling hoạt động đúng thiết kế, `observer.samples: 3`, note ghi rõ "aggregated from 3 vision samples". 451/451 test pass.

### GIT-01/GIT-02 — Đã commit theo nhóm scope (2026-07-17)
Toàn bộ thay đổi VAL-01/LOC-01/VAL-02/prompt-fix/MAN-01-gap-fix trong phiên này đã được commit riêng theo từng fix ở cả 2 repo (`venho-ai-studio`: 4 commit; `venho-os`: 5 commit) — không gộp bừa. Working tree `venho-ai-studio` sạch hoàn toàn; `venho-os` còn `ops/VenHoSocialManager/database/studio-jobs/` untracked (job-state test artifacts từ live QA, cố ý chưa thêm .gitignore — Harry chọn để sau).

### Verify lại các mục đã ghi "done" trước đó (2026-07-17)
- **DATA-01/MODEC-01/MODEC-02 — CONFIRMED chính xác**, không cần sửa gì. Đã verify bằng code thật: Mode C CLI có đủ `--outfit-id/--schema-subject/--display-label`; `run_mode_c` hard-code `allow_universal_schema=False` (khác Mode B mặc định `True`); `wardrobe_index.json` đúng `schema_subject: outfit_e_sport` cho cả `mint_green`/`nike_pink_running`; quarantine/legacy-alias là code thật (`linh-an-wardrobe-status/route.ts` lọc theo `wardrobe_manifest.json`); upload trùng tên trả `409`, không overwrite.
- **JOB-01 — 2 gap thật đã tìm ra và fix (2026-07-17, commit `85785b5` venho-os).**
  1. Server restart giữa lúc đang generate → job record kẹt vĩnh viễn ở `generating` (in-flight `AbortController` map chỉ sống trong memory). Fix: `job-store.ts::reconcileOrphanedJobs()` chạy 1 lần lúc module `jobs/route.ts` load — tại thời điểm đó `controllers` map chắc chắn rỗng, nên mọi job còn `queued/generating/validating` trên đĩa chắc chắn mồ côi từ process trước → đánh dấu `failed` với `error: "orphaned_by_restart"` thay vì treo vô thời hạn.
  2. **Bug thật thứ 2 mới tìm ra khi viết test:** `cancelJob()` fallback (khi không tìm thấy controller — job đã xong) trước đó **ép status thành `"cancelled"` vô điều kiện**, kể cả khi job đã `succeeded`/`failed` — DELETE lên 1 job đã xong sẽ âm thầm phá hỏng kết quả đã ghi. Đã sửa: chỉ cancel khi job còn đang in-progress; ngược lại trả `404`/`409` và giữ nguyên record.
  - Test mới: `job-store.test.ts` (reconcile đúng, không đụng job terminal, idempotent) + 2 test cancel trong `jobs-route.test.ts` (cancel job đã succeeded → 409, không đổi status; cancel job không tồn tại → 404). **78/78 test pass**, build clean.
- **MAN-01 — Đã tìm ra và fix 1 gap thật (xem commit `f15da8a` venho-os).** `manifest.references.faceReferenceSetVersion` trước đó là literal hardcode (`"linh_an_master_face_001"`) không hề liên kết với 4 ảnh reference VAL-02 thật (B3/A2/C/D) — đã sửa để lấy từ constant thật, thêm field `faceReferenceImages` liệt kê đúng 4 file. Cũng sửa luôn 1 bug điều kiện: field này trước gate theo `effectiveUseRef` (chuyện lúc generate) đáng lẽ phải gate theo `hasLinhAn` (chuyện lúc validate — 2 khái niệm khác nhau, độc lập với nhau).

### QA-01 — Full E1–E6 controlled matrix live run (2026-07-17)

Đã chạy đủ 6/6 case thật qua VenHo OS (không chỉ E1/E5 như trước):

| Case | Image/DNA | Face | Ghi chú |
|---|---:|---:|---|
| E1 | 100/approve | 82.5–85/revise | chạy 2 lần, ổn định |
| E2 | 40/reject → **100/approve sau fix** | 82.5/revise | ban đầu bị lamp-post forbidden (đã fix, xem dưới) |
| E3 | 100/approve | 82.5/revise | |
| E4 | 100/approve | **0/reject** (identity_structure + eye_ratio fail) | cycling tự tắt face-ref theo policy D-04 → mất identity thật, **đúng hành vi mong đợi**, không phải bug |
| E5 | 100/approve | 82.5–83.5/revise | chạy 2 lần, ổn định |
| E6 | **40/reject** ("tourist postcard aesthetic" forbidden) | **0/reject** (identity_structure + eye_ratio fail dù CÓ đủ face+env reference) | **Chưa fix — 2 vấn đề mới, xem bên dưới** |

**Fix đã áp dụng và verify lại thật (commit `88c19c6` venho-os):** E2 fail vì DNA cấm cột đèn (`lamp_post_presence: no`, đã sửa đúng ở LOC-01) nhưng `ENV_BLOCKS`/`NEGATIVE_BLOCK` trong `constants.ts` chưa từng cấm cột đèn rõ ràng trong prompt sinh ảnh thật (chỉ cấm "green railing"). Đã thêm "no lamp posts" vào `ENV_BLOCKS`, `SCENARIO_LOCATION_QC.forbidden`, và `NEGATIVE_BLOCK` toàn cục. **Verify lại E2 thật: 40/reject → 100/approve.**

**E6 vấn đề 1 — ĐÃ FIX (commit `531571c` venho-os).** Root cause thật: ảnh ref-env `Rooftop-Panorama-view.png` dùng cho scenario "West Lake Landscape (Wide)" thực chất chụp từ 1 sân thượng cụ thể (lan can đen, gạch nung, cục nóng điều hòa — xem trực tiếp ảnh AI sinh ra bằng Read tool, xác nhận đúng các chi tiết sân thượng bị lẫn vào, cộng thêm nhà cao tầng hiện đại thật trong ảnh ref). Đã bỏ ref-env cho scenario này (`ENV_REFERENCE_BY_SCENARIO: null`), dựa vào text `ENV_BLOCKS` đã mô tả đủ chi tiết.

**E6 vấn đề 2 — hoá ra không phải bug riêng của E6, mà là biểu hiện của vấn đề chung (xem mục Face Validator non-determinism bên dưới) — đã fix chung bằng sampling.**

**Bằng chứng mạnh hơn cho nghi vấn Face Validator templating (bổ sung mục ⚠️ bên dưới):** report E4 (không có face-ref) và E6 (có đủ face+env ref) cho ra **`weighted_scores` giống hệt tuyệt đối** (`60/50/70/80/85`) và **văn bản lý giải giống hệt gần như từng chữ**, dù input khác biệt rất lớn (có ref vs không ref). Đây là bằng chứng mạnh hơn nhiều so với phát hiện ban đầu — không còn coi là trùng hợp được nữa.

**Gap kỹ thuật khác phát hiện khi cố tính production-ready:** `config/quality/controlled_live_matrix.json`/`controlled_matrix.py` yêu cầu field `outfit_match` và `actor_geometry_ok` để tính gate, nhưng **Image/Face validator hiện tại không sinh ra 2 field này** — nghĩa là dù chạy đủ 6/6 case, hệ thống vẫn không có cách tự động tính "production_ready" theo đúng định nghĩa matrix. Cần bridge/field mới nếu muốn dùng `controlled_matrix.py` thật (chưa làm — ngoài phạm vi phiên này).

**Kết luận production-ready:** vẫn CHƯA đạt. Face score luôn dưới 90 ở mọi case đạt Image approve (82.5–85); E6 vẫn reject cả 2 phía. Không đủ điều kiện "2 run approved liên tiếp/case" cho case nào.

### QA/DOC — Phase 7 Closeout (2026-07-16)

## Tổng quan

| Module | Tên | Status | Tests |
|--------|-----|--------|-------|
| M01 | Knowledge Studio / DNA Studio / AI Vision Engine | ✅ COMPLETE | 258 |
| M02 | Prompt Studio | ✅ COMPLETE | 347 |
| M03 | Validator Studio | ✅ COMPLETE | 26 |
| M04 | Automation Studio | ✅ COMPLETE | 7 |
| M05 | Content Studio | ✅ COMPLETE — real Claude generator (2026-07-15) | 22 |
| M06 | Video Studio | ✅ COMPLETE (MVP — bugs fixed, design hardened) | 15 |
| M07 | Publishing Gateway | ✅ COMPLETE (offline dry-run MVP) | 19 |
| M08 | Analytics & Feedback Loop | ✅ COMPLETE (offline MVP) | 7 |
| M09 | Agent Studio | ✅ COMPLETE (offline planning/orchestration MVP) | 10 |
| M10 | **VenHo OS Dashboard** (Next.js `localhost:3000/os`) | ✅ COMPLETE v3.0 — Next.js OS Stage A+B+C (2026-07-13) · Streamlit đã xóa (2026-07-13): Workbench (Mode A+B SSE), Creative Studio, Knowledge (DNA Library+Vault Search+Mode C), Reports (DNA Status+Social Log), Shared UI, 7 API routes, 0 TS error | 0 |

> Tests ghi theo module-specific. Full suite hiện tại = 454 (cập nhật 2026-07-20; gồm regression test giữ outfit non-sport trong Wardrobe Index) — M01+M02+M03+M04+M05+M06+M07+M08+M09+shared — M10 runtime/API tests nằm ở repo `venho-os`.

### OUTFIT-01 — đã hoàn thành từ trước, không cần build lại (xác nhận 2026-07-17)
`venho-os/src/lib/studio/wardrobe-index.server.ts` đã đọc động từ `config/projects/linh_an/wardrobe_index.json` (có đủ baseline non-sport: `cafe_girl_classic`, `west_lake_sunset_classic`, `street_style_classic`, `business_travel_classic`; và sport: `mint_green`, `nike_pink_running`, tất cả `status: approved`); `constants.ts::OUTFIT_VARIANTS` chỉ còn là fallback an toàn khi thiếu file index, không phải nguồn chính. Thêm outfit mới ngày nay chỉ cần sửa `wardrobe_index.json`, không cần sửa TypeScript. Backlog item OUTFIT-01 trong roadmap v1.5 nên được đóng.

### QA/DOC — Phase 7 Closeout (2026-07-16)
- Roadmap v1.5 chỉ có Phase 0–6; Phase 7 được map vào backlog `QA-01` + `DOC-01`.
- Controlled live matrix canonical: `config/quality/controlled_live_matrix.json`.
- Offline evaluator: `validator_studio/controlled_matrix.py`.
- Production-ready image workflow yêu cầu 2 run approved liên tiếp cho mỗi case E1–E6.
- Missing validator/gate luôn là `UNVALIDATED`, không được tính approved.
- VenHo OS expose matrix qua `/api/v1/studio/quality-matrix`, không chạy paid generation.

### M04/M09/AiStudioPort/Living Lab — Phase 6 Ops integration (2026-07-16)
- M04 thêm `automation_studio.wardrobe_ingest`: tạo review file, validation fail chặn index update.
- M04 thêm `automation_studio.wardrobe_index_update`: chỉ update Wardrobe Index khi `validation_status=pass` và `approved_for_index=true`.
- M09 hard-stop khi thiếu required knowledge; không dispatch M04 kể cả dry-run/execute.
- `JobContract 1.0` tách transition `approved → executed → published`; không cho publish nhảy cóc.
- `AiStudioPort` expose coarse capabilities: `wardrobe_ingest`, `content_generate`, `video_package`, `publish_content`.
- Living Lab metrics ghi `output_used`, `approved_first_try`, retry, minutes saved, cost/run, decision `continue/simplify/pivot/kill`.

### M02/M03/M05/M06 — Phase 5 Contract Refs integration (2026-07-16)
- M02 prompt contracts có optional `contract_refs` để trace `character_id`, `outfit_id`, `scenario_profile`.
- Content prompt 1.0 vẫn backward compatible, nhưng khi request có `outfit_id` sẽ render Outfit Capsule có ID rõ ràng.
- M05 `ContentRequest` nhận `outfit_id`; output copy `contract_refs` từ M02, không tự chọn outfit.
- M06 `VideoRequest` nhận `outfit_id`; package ghi `contract_refs`, continuity thêm `outfit_id:<id>` và scene prompts khóa wardrobe xuyên shot.
- M03 prompt/content validator đọc `contract_refs` từ prompt contract; không suy luận outfit từ prose.
- Claude adapter đã có fake-client unit test; pytest không gọi production Claude API.

### M10 / Mode C — Data Integrity (2026-07-16)
- Mode C có CLI/runtime riêng: `venho vision observe --mode c`.
- Request tách `outfit_id`, `schema_subject`, `display_label`.
- Source-backed/locked sport variants hiện tại: `mint_green`, `nike_pink_running` → schema canonical `outfit_e_sport`; baseline non-sport vẫn là `manual_seed` approved trong `wardrobe_index.json`.
- Universal schema fallback bị chặn trong Mode C.
- Artifact output vẫn theo variant (`LINH_AN_NIKE_PINK_RUNNING_DNA.*`) nhưng schema lấy từ `outfit_e_sport`.
- VenHo OS status chỉ báo success khi artifact mới hơn run hiện tại; upload trùng tên bị chặn thay vì overwrite.
- `wardrobe_manifest.json` quarantine Nike Pink artifact cũ và đánh dấu `sport_active` upload folder là legacy alias.

### M03 / Image QC — Phase 2 contract hardening (2026-07-16)
- Face Validator bắt buộc đúng 3 gate: `identity_structure`, `eye_ratio`, `forbidden_traits`.
- Face Validator bắt buộc đúng 5 score keys: `facial_shape`, `eyes`, `hair`, `expression`, `technical_quality`.
- `weighted_scores` phải là điểm 0–100; payload dùng rubric weight 0–1 bị reject.
- VenHo OS Generation Manifest nâng lên `schemaVersion: 1.1` với `promptHash`, outfit trace, `scenarioProfile`, face reference set version, validation contract và latency.

---

## M01 — Knowledge Studio / DNA Studio / AI Vision Engine ✅ COMPLETE

**Plan:** `docs/dna_studio_master_plan_v2_5_qc.md` (v2.5 QC)
**Git:** `7a9e10b`, `0df848f`, `dfac10c`, `daf033e`, `3d38661`
**Tests:** 258/258 — xem `tests/test_mock.py`, `test_pass2a.py`, `test_phase5–8.py`, `test_vault.py`, `test_mode_a/b_contract.py`, `test_overlay_merge.py`, `test_cache.py`, `test_cli.py`, `test_subject_resolver.py`, `test_regeneration_policy.py`

**Các Phase hoàn thành:**
- Phase 0 Project Foundation · Phase 1 Shared Vision Core
- Phase 2 Mode A MVP · Phase 3 Mode B Core
- Phase 4 Project Layer + Overlay + Ven Hồ MVP
- Phase 5 Schema Bootstrap + Auto Classify
- Phase 6 Face Subject / Linh An (QC gate 07F)
- Phase 7 Hardening + Documentation (248 tests, contracts, docs đầy đủ)
- Phase 8 Studio Shell / UI (Next.js VenHo OS → localhost:3000/os)

**DNA subjects:** `lake_view_room` · `deluxe_double` · `lobby` · `facade` · `linh_an` · `westlake` · `outside`
**DNA contract:** `1.1` · **assets/raw/** và `output/` excluded khỏi git (.gitignore)

---

## M02 — Prompt Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_02_Prompt_Studio_Plan_v1.1.md`
**Git:** `07535a4`
**Tests:** 347/347 — xem `test_image_prompt_builder.py`, `test_video_prompt_builder.py`, `test_content_prompt_builder.py`, `test_seo_prompt_builder.py`, `test_prompt_manifest.py`, `test_optimizer.py`, `test_optimizer_mock.py`, `test_mvp_image_prompt.py`, `test_pipeline.py`, `test_pipeline_manifest_integration.py`, `test_knowledge_reader.py`, `test_template_loader.py`, `test_prompt_renderer_and_store.py`, `test_prompt_cli.py`, `test_step15_comprehensive.py`, `test_prompt_contract_schema.py`

**Các Stage hoàn thành:** 5 stages / 16 steps
- Stage 1 Foundation · Stage 2 Image Prompt · Stage 3 Video Prompt
- Stage 4 Content + SEO Prompt · Stage 5 Manifest + CLI + Optimization

**Pipeline:** Build → Validate #1 (structural) → Optimize (Claude, temp 0) → Validate #2 (faithfulness) → Manifest-aware Render/Store
**Prompt types:** `image` · `video` · `content` · `seo`
**Manifest + Regeneration Policy:** DNA/template không đổi → `no_change` · đổi → archive `_archive/` + bump version
**⚠️ Test discipline:** luôn dùng `optimize_fn=optimize_mock` — default gọi Claude API thật

---

## M03 — Validator Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_03_Validator_Studio_Plan_v1_1.md`
**Git:** `9b6c76b`
**Tests:** 26/26 — xem `test_validator.py`, `test_validator_studio.py`

**4 validator types hoàn thành:**
- `image_validator.py` — DNA match, forbidden kill-switch (cap=40 nếu severity=high), authenticity
- `prompt_validator.py` — advisory (không chặn M02), DNA coverage, forbidden conflict
- `face_validator.py` — 07F binary gates + weighted score; grounding OFF
- `content_validator.py` — brand_fit/tone/clarity/CTA/language_fit/production_readiness

**Scoring:** AI observe enum (match/partial/mismatch/not_visible) → code score deterministic
**Kill-switch:** forbidden severity=high → cap overall=40, verdict=regenerate
**CLI:** `venho validate image|prompt|face|content ...`
**Docs:** `docs/how_to_run_validator_studio.md`

---

## M04 — Automation Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_04_Automation_Studio_Plan_v1_1.md`
**Git:** `bceef45`
**Tests:** 7/7 — xem `test_automation_studio.py`

**Tính năng chính:**
- Workflow config YAML-first: `config/workflows/` (4 workflows sẵn)
- Action registry: 7 actions (3 knowledge, 1 prompt, 2 validator, 1 manual_gate)
- Run lock (chặn chạy song song) + Resume từ `resumable_from`
- `skip_dependents`: BFS transitive — bước fail → bước `needs` nó skip, không chạy input rỗng
- Dry-run: kiểm config/params/paths trước khi chạy thật
- Manual gate: two-half pipeline (Nửa 1: DNA→Prompt; Nửa 2: image→validate)
- Scheduler: parse nhưng chưa bật (manual first)

**CLI:** `venho auto run {workflow_id}` · `venho auto resume {run_id}` · `venho auto list` · `venho auto actions`

---

## M05 — Content Studio ✅ COMPLETE (deterministic + real Claude adapter gated)

**Plan:** `VENHO_AI_STUDIO_Module_05_Content_Studio_Plan_v1_1.md` (§19 ghi status hoàn thành)
**Git:** `8c95194`
**Tests:** 22/22 — xem `test_content_studio.py`, `test_content_prompt_builder.py`, `test_prompt_contract_schema.py`

**16 steps hoàn thành** (Giai đoạn 0–4):

| Giai đoạn | Steps | Nội dung |
|-----------|-------|---------|
| 0 Nền tảng | 0–2 | Module setup, Request/Output schema, Project content config |
| 1 Cầu nối | 3–4 | Prompt Bridge (gọi M02), Content Context Loader |
| 2 MVP Social | 5–8 | Social Builder, Renderer, Validator Bridge, Acceptance test |
| 3 Mở rộng | 9–13 | Blog SEO, Website, OTA, FAQ, Email |
| 4 Đa kênh | 14–16 | Campaign Generator, Content Calendar, Manifest + CLI |

**Content types:** social (FB/IG/Threads/TikTok) · blog SEO · website copy · OTA (Agoda+Google+direct) · FAQ · email draft · campaign · calendar

**Runtime policy:**
- Deterministic builders/mock generator vẫn là default trong tests — 0 API call.
- Real Claude adapter đã có và chỉ chạy khi được gọi rõ ràng với credentials; pytest dùng fake-client coverage.
- Phase 5 đã thêm `contract_refs/outfit_id` trace từ M02 → M05 → M03.

---

## M06 — Video Studio ✅ COMPLETE (MVP — bugs fixed, design hardened)

**Plan:** `VENHO_AI_STUDIO_Module_06_Video_Studio_Plan_v1_1.md`
**Git:** `155b5f9` scaffold; các bug fix 2026-07-09 và Phase 5/6/7 hardening đã commit trong lịch sử sau đó.
**Tests:** 15/15 — xem `tests/test_video_studio.py` (9) + `tests/test_video_prompt_builder.py` (6)

**Pipeline đầy đủ:**
- `video_engine.py` orchestrates: context → concept → storyboard → shot list → per-scene M02 prompt → engine format → M05 caption/hook/CTA → M03 validation bridge → MD/JSON output → manifest
- M02 bridge: scene prompts qua `build_video_prompt`, M06 không tự dựng prompt cảnh
- M05 bridge: caption/hook/CTA lấy từ Content Studio, M06 không tự sinh text
- M03 bridge: prompt validation per scene, degrade advisory (`warning`/`not_available`)
- Continuity: DNA invariants + Face DNA khi `include_character=true`; thiếu Face DNA → fail rõ
- Renderers: `.md` + `.json`; manifest `data/projects/<project>/video/video_manifest.json`
- CLI: `venho-video generate --topic "..." --duration 15 --type social_reel --subjects lake_view_room,westlake`

**Bugs đã fix (2026-07-09):**
- `engine_formatter.py` — aspect ratio thực (`"9:16"`) điền vào engine prompt, không còn là prose
- `content_bridge.py` — `youtube_shorts` → `tiktok_caption` (không còn fallback sai sang `facebook_post`)
- `validator_bridge.py` — subject lấy từ primary env DNA (non-linh_an/non-character) thay vì `[-1]`

**Design improvements (2026-07-09):**
- `storyboard_builder.py` — 5 bộ scene templates theo `video_type`: social_reel · character · hotel_lifestyle · website_hero · explainer
- `shot_list_builder.py` — angle/motion_note/lighting_note động theo scene position và camera_movement
- `engine_formatter.py` + `templates/*.yaml` — template notes được embed vào engine prompt (AI-facing, không còn internal references)
- Xóa `video_studio/video_request.py` (redundant re-export)
- `venho-video` CLI available trong PATH sau `pip install -e .`

**Ranh giới giữ nguyên:**
- Chỉ tạo pre-render package; không render, không upload, không publish
- Post-render video validation là future work
- Spatial/brand forbidden single-source qua M02/DNA; video config chỉ giữ motion/camera/character rules
- Phase 5 đã thêm `outfit_id` continuity lock và `contract_refs` vào video package.

---

## M07 — Publishing Gateway ✅ COMPLETE (offline dry-run MVP)

**Plan:** `VENHO_AI_STUDIO_Module_07_Publishing_Gateway_Development_Plan_v1_2_QC.md`
**Tests:** 19/19 — xem `tests/test_publishing_gateway_scaffold.py`, `tests/test_publishing_gateway.py`
**CLI smoke:** `python3 -m publishing_gateway.cli publish --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --approval-secret test-secret --dry-run --data-root /tmp/venho_m07_cli_check`

**Vai trò:** Nhận package đã duyệt từ M04 → kiểm contract/approval/brand/capability → queue/adapters → delivery receipt cho M08. Không tạo content, không sửa caption/hashtag, không quyết định giờ đăng, không chứa logic Agent.

**Đã hoàn thành:**
- Step 0–2 — Scaffold, schemas/contracts, base adapter + mock adapter
- Step 3–7 — Approval verifier (HMAC/TTL), contract validator, brand guard, platform capability, idempotency + receipt store
- Step 8–11 — Publisher queue, circuit breaker, rate-limit policy, token vault
- Step 12–15 — Facebook/Instagram Core MVP adapters + Threads/Google Business conditional adapters (offline payload mapping)
- Step 16–18 — Gateway router, delivery receipt JSON/Markdown, M08 handoff contract docs
- Step 19–20 — CLI publish/retry/receipt/queue/version + end-to-end dry-run acceptance
- Step 21 — Controlled real API checklist documented; not run in pytest

**MVP scope theo plan v1.2:**
- Core MVP: Facebook Page + Instagram Business
- Conditional MVP: Threads + Google Business Profile, mặc định feature-flag off
- Automated tests luôn offline, không đọc secret thật, không gọi API thật

**Artifacts chính:**
- Package: `publishing_gateway/`
- Config: `config/projects/venho_hotel/publishing/`
- Fixture: `data/projects/venho_hotel/publishing/fixtures/approved_package.json`
- Docs: `docs/how_to_run_publishing_gateway.md`, `docs/contracts/m07_to_m08_delivery_receipt.md`

**Ranh giới còn giữ:**
- Real API publish là controlled manual test, không chạy tự động.
- Adapter live chưa gọi network; hiện map payload và dry-run an toàn.
- M07 chỉ phân phối package đã duyệt, không sáng tạo hay chỉnh nội dung.

---

## M08 — Analytics & Feedback Loop ✅ COMPLETE (offline MVP, code reviewed)

**Plan:** `VENHO_AI_STUDIO_Module_08_Analytics_Feedback_Development_Plan_v1_2_QC.md`
**Tests:** 7/7 — xem `tests/test_analytics_feedback.py`
**Historical full suite at completion:** `430/430` pass, 0 API call. **Current full suite:** `454/454` pass.
**Code review:** 2026-07-09 — 5 bugs fixed (commit `373b1cc`)

**Vai trò:** Nhận Delivery Receipt từ M07 → tạo collection tasks → mock collect metrics → chuẩn hóa unified metrics → tính derived stats/baseline/score → sentiment guardrail → sinh alert/advisory/report. M08 chỉ sinh output advisory, không tự apply vào M01/M05.

**Đã hoàn thành MVP:**
- Step 0–2 — Scaffold, schemas/contracts, base metrics adapter + mock adapter offline
- Step 3–5 — Ingestion router, collection scheduler, raw/snapshot stores idempotent
- Step 6–9 — Unified Metrics Standardizer, stats calculator, baseline calculator, performance scorer, score store
- Step 10–11 — Rule-based sentiment scorer song ngữ vi/en + critical alert generator/store
- Step 12–14 — Feedback advisory generator, advisory/report renderers và stores
- CLI entrypoint: `venho-analytics` / `analytics_feedback.cli`

**Artifacts chính:**
- Package: `analytics_feedback/`
- Config: `config/projects/venho_hotel/analytics/`
- Test: `tests/test_analytics_feedback.py`

**Ranh giới còn giữ:**
- Không gọi API thật trong pytest; mock metrics adapter là mặc định.
- Không tự publish, không tự sửa Knowledge, không tự đổi Content Strategy.
- Advisory luôn `pending_approval`, `approval_required=true`, route qua `M04_AUTOMATION_STUDIO` / `M09_AGENT_STUDIO`.

---

## M09 — Agent Studio ✅ COMPLETE (offline planning/orchestration MVP, reviewed + bugs fixed)

**Plan:** `VENHO_AI_STUDIO_Module_09_Agent_Studio_Development_Plan_v2_2_QC.md`
**Tests:** 10/10 — xem `tests/test_agent_studio.py`
**Historical full suite at completion:** `430/430` pass, 0 API call. **Current full suite:** `454/454` pass.
**Code review:** 2026-07-09 — 3 bugs fixed (commit `373b1cc`)

**Vai trò:** Cognitive Interface / Agent Orchestration Layer. Nhận goal tự nhiên → validate request → route persona → load context → detect missing knowledge → tạo TaskPlan → classify risk → đóng gói ModuleRequest qua M04 → aggregate response Markdown/JSON. M09 không tự publish, không tự sửa Knowledge, không bypass M04.

**Đã hoàn thành MVP:**
- Step 0–2 — Scaffold, contracts/schemas, BaseAgent interface offline
- Step 3–7 — Request validator, router, persona resolver, context loader, missing knowledge detector
- Step 8–10 — Task planner, risk classifier đọc `agent_policy.yaml`, module request builder luôn route qua `M04_AUTOMATION_STUDIO`
- Step 11–13 — Automation bridge mock/dry-run, result aggregator + execution log, Markdown/JSON renderers
- Step 14–18 — Generic agent classes + templates: documentation, research, content planning, visual planning, analytics insight
- Step 19–23 — Base persona template, Ven Hồ agent policy, marketing agent config, Linh An brand agent config, project acceptance
- Step 24–26 — CLI `venho-agent` / `agent_studio.cli`, E2E dry-run, MVP acceptance

**Artifacts chính:**
- Package: `agent_studio/`
- Config: `config/projects/venho_hotel/agents/`
- Test: `tests/test_agent_studio.py`
- CLI: `venho-agent --agent marketing_agent --project venho_hotel --goal "..." --plan-only`

**Ranh giới còn giữ:**
- M09 chỉ lập kế hoạch và đóng gói yêu cầu; M04 là execution gateway.
- Publishing request chỉ thành manual gate / module request; M09 không gọi M07 trực tiếp.
- Required knowledge thiếu trả `ERR_MISSING_KNOWLEDGE`.
- Destructive action bị block theo policy; external impact yêu cầu approval.

**Phase 6 hardening đã xong:**
- Missing knowledge hiện hard-stop trước M04 dispatch và trả `ERR_MISSING_KNOWLEDGE`.
- `--execute` vẫn qua M04 boundary; execution thật phải dùng workflow runner/capability contract, không bypass M04.

---

## M10 — VenHo OS Dashboard ✅ COMPLETE v3.0 (Next.js OS Stage A+B+C — Streamlit đã xóa 2026-07-13)

**Plan:** `VENHO_AI_STUDIO_Module_10_Dashboard_Plan_v1_2.md`
**Repo runtime:** `venho-os` Next.js 16 App Router (`/os`)  
**Current OS tests:** `npm test -- --run` → 65/65; `npm run lint`; `npx tsc --noEmit`; `npm run build` pass  
**AI Studio Python suite:** 454/454 pass, 0 API call  

**Quyết định kiến trúc:** M10 đã chuyển hẳn khỏi Python/Streamlit. `venho-ai-studio` giữ engine/contracts M01–M09; `venho-os` giữ UI/BFF/job boundary.

**Current Image Studio trong `venho-os`:**
- Workbench: Mode A/B SSE, upload ảnh, normalize ảnh server-side, output dir dùng thật.
- Knowledge: DNA Library, Vault Search, Mode C Linh An, status artifact theo run, upload duplicate bị chặn.
- Creative Studio: Tạo Ảnh AI, Social Post, Video Script.
- Image generation: durable file-backed jobs, status API, cancel, history, manifest 1.1.
- Wardrobe: dynamic Wardrobe Index 1.0; selector không còn hardcode hai outfit trong UI.
- QC: image/face validation, manifest trace face/outfit/location/reference, partial validation errors là `UNVALIDATED`.
- QA: `/api/v1/studio/quality-matrix` đọc controlled live matrix; không chạy paid generation.

**Historical note:** Các dòng cũ về `ui/studio_app.py`, Streamlit path bugs và Command Palette là lịch sử trước 2026-07-13, không còn là runtime hiện tại.

---

## Git Log gần nhất liên quan AI Studio v1.5

```
AI Studio:
b975466 Add Phase 7 QA closeout matrix
b01c429 Add Phase 6 ops workflow controls
7291eeb Integrate contract refs across prompt content video validation
484dc20 Add Linh An wardrobe index
811c473 Enforce face validation contract
b8c34e3 Record Mode C wardrobe quarantine registry
976922b Add strict Mode C wardrobe routing
5d918d8 Sanitize Phase 0 baseline note

VenHo OS:
6beff50 Expose Studio quality matrix
7ce0548 Integrate dynamic Studio wardrobe index
0138168 Add durable Studio generation jobs
b54059e Complete image QC manifest handling
736c18e Upgrade image generation manifest contract
70a4ee7 Honor Mode C quarantine and Mode A output
836e503 Wire Mode C wardrobe data integrity
4aa6651 Isolate image route tests from production artifacts
6e2a93c Improve image generation identity controls
```

---

## Cách cập nhật file này

Cập nhật `task_status.md` mỗi khi:
- Hoàn thành một module hoặc stage quan trọng
- Test count thay đổi
- Commit mới liên quan đến status module

---

## Growth Agent — One-approval scheduled publishing / Step 1 COMPLETE (2026-08-10)

- Canonical production pipeline: `venho-ai-studio` Growth Agent.
- Legacy Social Content Agent: cron removed; manual recovery only.
- Growth `legacy_agent_active`: `false`.
- Verification passed: feature-flag regression test and GitHub Actions YAML parse.

---

## Growth Agent — One-approval scheduled publishing / Step 2 COMPLETE (2026-08-10)

- Fixed the Google Drive OAuth refresh crash in `GoogleDriveUploader`.
- OAuth client ID/secret are now supplied before credential construction, not assigned to read-only Google credential properties.
- Verification: `PYTHONPATH=. /usr/bin/python3 -m pytest -q tests/test_growth_google_drive_uploader.py tests/test_growth_phase1_policy_registry.py` → **7/7 passed** (no network call).

---

## Growth Agent — One-approval scheduled publishing / Step 3 COMPLETE (2026-08-10)

- Added atomic weekly approval command: `venho-growth approve-week`.
- Approved rows are now recorded as `APPROVED_SCHEDULED` with approver, timestamp and immutable approval snapshot; this action has no Make.com dispatch path.
- Added the VENHO OS “Duyệt toàn bộ tuần” API and dashboard action.
- Verification: Growth approval/OAuth/policy suite **43/43 passed**; VENHO OS suite **195/195 passed**; changed VENHO OS files pass ESLint. Full OS lint remains blocked by 2 pre-existing errors in `design_handoff_venho_os_cockpit/support.js`.

---

## Growth Agent — One-approval scheduled publishing / Step 4 COMPLETE (2026-08-10)

- Added independent due-slot dispatcher: `venho-growth dispatch-due`. It processes only `APPROVED_SCHEDULED` rows due at 09:00 Asia/Ho_Chi_Minh, with an atomic status claim before Make can be called.
- Retired the production CLI path `approve-and-dispatch`; weekly approval is now the only dashboard approval action and cannot trigger publishing.
- Added authenticated VENHO OS scheduler hook: `POST /api/v1/studio/growth/scheduler/dispatch`, protected by `GROWTH_SCHEDULER_TOKEN`. It is ready for a persistent external scheduler to invoke every five minutes.
- Verification: Growth approval/OAuth/policy/scheduler suite **45/45 passed**; Growth CLI help, VENHO OS TypeScript, changed-file ESLint, and diff checks passed.

---

## Growth Agent — One-approval scheduled publishing / Step 5 READY, AWAITING RUNTIME CONFIGURATION (2026-08-10)

- Added the `GROWTH_SCHEDULER_TOKEN` environment contract and the deployment runbook at `venho-os/docs/GROWTH_SCHEDULER_ROLLOUT.md`.
- The Make.com scheduler must POST only to the authenticated VENHO OS scheduler hook every five minutes; it must not publish to Facebook/Instagram itself.
- Activation is intentionally pending: this workspace has neither a public VENHO OS URL nor a configured runtime scheduler token. Calling a local URL from Make.com is impossible, and activating before these values exist can release overdue approved publications.

---

## Growth Agent — One-approval scheduled publishing / Step 5 COMPLETE: GitHub Actions Scheduler (2026-08-10)

- Replaced the cloud-callback rollout path with `.github/workflows/growth-publish-scheduler.yml`: GitHub Actions invokes `venho-growth dispatch-due` every five minutes and persists state in Git.
- Serialized weekly generation and dispatch in `growth-publication-state`, preventing registry/database commit races.
- Required GitHub Secrets before the first live dispatch: `MAKE_GROWTH_WEBHOOK_URL`; add `MAKE_GROWTH_WEBHOOK_SECRET` if the Make scenario validates it. No Mac Mini, public URL, or scheduler token is required.
- Scheduler intentionally does not use `--allow-shadow`; current `shadow` rollout state prevents an unreviewed production release.
- Verification: `pytest -q tests/test_growth_weekly_cycle.py tests/test_growth_approve_and_dispatch.py` → **43/43 passed**; `git diff --check` passed.
- GitHub Repository Secret `MAKE_GROWTH_WEBHOOK_URL` configured and verified present on 2026-08-10. No manual dispatch was run.

---

## Growth Agent — One-approval scheduled publishing / Step 6 COMPLETE: Migration & rollout validation (2026-08-10)

- Legacy nonterminal records were deliberately left unchanged: there are no `APPROVED_SCHEDULED` publications to migrate and replaying `GATEWAY_*`/`SHADOW_HELD` rows risks stale duplicate posts.
- Real rollout scorecard `growth-scheduler-2026-08`: **2.22/10**, **0** published samples; gate correctly keeps rollout at `shadow` and no dispatch was run.
- `venho-rollout runbook-validate` passed. Regression suite: **69/69 passed**; `git diff --check` passed.
- All source changes remain local and uncommitted; GitHub Actions will not run the new Scheduler until a scoped commit is pushed.

---

## Growth Agent — Remediation Step 7a COMPLETE: Empty approval queue UX (2026-08-10)

- Dashboard now keeps the sole **Duyệt toàn bộ tuần** control visible and disabled when its review queue is empty.
- Empty-week approval returns the explicit `NO_PENDING_APPROVAL` business state (HTTP 409), not `Command failed`.
- Verified: scoped ESLint and whitespace checks passed.

---

## Growth Agent — Remediation Step 7b COMPLETE: Slot/queue state diagnosis (2026-08-10)

- Current-week Slot state and registry are inconsistent: only an orphan T4 `PENDING_APPROVAL` Slot exists; all displayed publications are old `SHADOW_HELD` records.
- No `APPROVED_SCHEDULED` record exists and rollout remains `shadow`; therefore no Facebook/Instagram post can be dispatched.

---

## Growth Agent — Remediation Step 7c COMPLETE: Slot synchronization & approval-queue filter (2026-08-10)

- Ran `venho-growth ensure-slots --horizon-days 14`: **2** missing horizon slots created; existing current-week slots were preserved.
- `SHADOW_HELD` records are now excluded from `list-pending`; the Dashboard review table contains only records that can actually be acted on.
- Verification: `pytest -q tests/test_growth_approve_and_dispatch.py` → **38/38 passed**; `git diff --check` passed.
- Current-week content remains absent; the T4 orphan Slot will be reconciled by the weekly content-generation cycle in the next remediation step.

---

## Growth Agent — Remediation Step 7d COMPLETE: Automatic Weekly Cycle recovery (2026-08-10)

- Weekly Cycle now schedules automatic retry attempts at **08:00, 10:00 and 12:00 Monday (Asia/Ho_Chi_Minh)**. The weekly JobStore is idempotent: only one successful run can generate the week; a failed run is retried automatically.
- The 2026-08-10 scheduled GitHub run failed on remote SHA `4287651`, before the local OAuth fix existed. Local source must be committed and pushed before GitHub can run this recovered schedule.
- Verification: YAML schedule assertion passed; `pytest -q tests/test_growth_weekly_cycle.py` → **5/5 passed**; `git diff --check` passed.

---

## Growth Agent — Remediation Step 7e COMPLETE: Automation Cycle deployed to GitHub (2026-08-10)

- Pushed AI Studio automation to `main`: **f3ae89f**. VENHO OS approval UI/API: **db6db53**. Legacy Social Content cron retirement: **cda5641**.
- The AI Studio push was safely rebased onto concurrent Git-backed state commits; no remote registry/research state was overwritten.
- GitHub Actions now has the automatic Weekly Cycle and independent publish scheduler definitions on `main`.

---

## Growth Agent — Handoff: next debugging target (2026-08-10)

- Deployed state: AI Studio remote `main` **9792244** (automation workflow **f3ae89f**); VENHO OS **db6db53**; legacy scheduler retirement **cda5641**. GitHub reports both Growth workflows active.
- Next action: run the new Weekly Cycle for 2026-08-10, verify all four current-week slots are tied to generated `PENDING_APPROVAL` publications, then verify Dashboard review controls.
- No content was dispatched or published during this handoff; rollout stays `shadow`.

## Growth Agent — Two-week automation and missed-Monday recovery COMPLETE (2026-08-10)

- Weekly generation now runs Sunday 20:00 ICT with a 22:00 fallback and creates 8 posting occasions across two weeks (16 Facebook/Instagram publication variants).
- One approval action covers the complete 14-day batch.
- Rejected publications automatically queue a same-slot replacement immediately from VENHO OS, with a 15-minute GitHub Actions fallback.
- Monday catch-up dispatched the due Facebook/Instagram pair through Make; registry state is persisted as `PUBLISHED`. Instagram media ID: `17929423083379767`; Facebook permalink remains unverifiable because the Make response mapping returns placeholder fields.
- Scheduler persistence-order bug is fixed. Validation run `31389945843` completed successfully without duplicate dispatch.
- AI Studio commits deployed: `fc6d291`, `a04f09b`. VENHO OS commit deployed: `2632537`.
- Verification: Growth tests **48/48 passed**; VENHO OS TypeScript pass; registry sync tests **9/9 passed**.
- Task closed. Remaining external configuration defect is limited to Make.com's Facebook response-field mapping; it does not block the recorded gateway dispatch.

## Growth Agent — Master Prompt Factual Safety Rules COMPLETE (2026-08-11)

- Added five mandatory factual-safety groups to the Opus content generator master prompt: indirect social-proof prohibition, current-time grounding, no negative positioning, negative-interpretation review, and plain-text publishing output.
- Prompt load check passed through `social_prompts.MASTER_SYSTEM_PROMPT`.
- Deployed commit: `dc4b398` (`feat: add factual safety rules to master prompt`).
- Legacy Claude generator test file still has 3 pre-existing expectation failures unrelated to this prompt-only change.

## Action Composite v2 (Linh An / ComfyUI) — P7 hardening review COMPLETE (2026-08-12)

Senior QC review of the Codex-authored P1–P6 code in `image_studio_runtime/action_composite/`,
plus the three files it touched outside that package. All 18 pre-existing tests were green; two
serious defects were hiding behind them, both reproduced by running the code before fixing.

**Defects fixed (all covered by new regression tests):**

- [x] **Pixel Preservation Lock was inert** (`pipeline.py`) — the diff compared only the alpha
      channel, and `load_image` always converts to RGBA, so alpha never varies. Every RGB change
      outside the mask (body, wardrobe, hair, Hồ Tây, background) passed as clean. This is the
      central promise of the whole plan (§8.3, §50.6).
- [x] The locked region is `mask == 0`, not "outside the bbox" — a feathered mask blends over its
      own edge, so the obvious strict fix would fail every legitimate run. New shared helper
      `regression_guard.protected_region()`; the pipeline's divergent second copy is deleted.
- [x] The gate now judges the restorer's **raw output**, not the composite — `Image.composite`
      discards outside-mask pixels by construction, so validating it confirmed a tautology while
      a restorer that regenerated the whole scene still reported clean (§18, §34.3).
- [x] **QC status reported failures as `UNVALIDATED`** — `not identity_score` treated a real `0.0`
      as "not measured"; a pixel-preservation failure with no identity score was reported unscored.
- [x] **ComfyUI adapter never uploaded the images** — it POSTed workflow JSON alone, no base image,
      no mask, no A2 reference, so the POC could not have run. Added `/upload/image` for all three
      plus `inject_inputs()` binding them to loader nodes by `_meta.title` from config.
- [x] Adapter: fail fast on `status_str == "error"` instead of spinning to timeout; deterministic
      output selection; URL-encoded `/view` query; timeout from config.
- [x] **Service idempotency store was written, never read**; `submit` silently overwrote a live
      job on payload conflict; `RUNNING` jobs could be started twice; no lock on shared state.
- [x] **Resume destroyed the audit trail** (§22, §32) — wrote a fresh 2-record trail over the
      failed attempt; now continues the stored trail with monotonic iterations.
- [x] `StopCondition` hard-coded a second copy of the thresholds it had just asked the validator
      for, silently overruling a caller-supplied threshold.
- [x] Retry caps without a `region` key raised `KeyError`; `crop_for_identity(scale<1)` inverted
      the box; the A2 authority check matched folder names (`A2_benchmarks/candidate93.png` passed).
- [x] `ComfyUIConfig`: relative workflow path resolved against cwd, not the repo; malformed env
      values raised a bare `ValueError` without naming the variable.
- [x] `action_composite/__init__.py` declared `__all__` twice, discarding `ActionCompositePipeline`.

**Outside the package:**

- [x] `shared/vision/image_loader.py` — AVIF intake wrote a `.jpg` **into the user's photo folder**
      and reused a pre-existing same-stem `.jpg` that is a *different photo*; `sorted(set(...))`
      silently dropped an image when an `.avif` and a `.jpg` shared a stem (Mode B validates image
      counts); `.avif` bytes were labelled `image/jpeg` to the vision API. Now converts via Pillow
      (`features.check('avif')` confirmed True) into content-hashed `data/.cache/avif/`, with `sips`
      as fallback.
- [x] `knowledge_studio/vision/pipeline.py` — manifest was synced *before* the index write, so a
      failed index write left the manifest advertising an unregistered outfit; new families were
      hard-coded to `outfit_e_sport`; a string `value_range` indexed to a single character.

**Verification:** targeted suite **77/77 pass**. Full suite 812 pass / 99 fail — the 99 are
pre-existing, confirmed by stashing this work and re-running (identical 99 at baseline); they sit
in subject-resolver / validator / video-studio config, untouched here.

**Still open (unchanged):** identity-conditioning workflow + model files, and the 10-image A2
benchmark. The adapter is now complete enough to drive a real ComfyUI but **has never been run
against a live server** — that first real run remains the meaningful test.

## Action Composite v2 — P8 first live ComfyUI run: RAM-blocked, not code-blocked (2026-08-12)

Installed ComfyUI locally (`~/ComfyUI`, already present from an earlier session) and ran the
adapter against a real server for the first time — not the fake HTTP server the test suite uses.

**What was built:**
- `ComfyUI/custom_nodes/PuLID_ComfyUI` + deps (`facexlib`, `insightface`, `onnxruntime`, `ftfy`,
  `timm`) installed into `~/ComfyUI/.venv` (Python 3.12, torch 2.13, MPS available).
- Models downloaded: `ip-adapter_pulid_sdxl_fp16.safetensors` (755M), AntelopeV2 face-analysis
  ONNX set (344M), `sd_xl_base_1.0.safetensors` (6.5G), `sdxl_lightning_4step_lora.safetensors`.
- `config/comfyui/face_restore_v1_api.json` (committed) — API-format workflow: `base_image` +
  `face_mask` → `VAEEncodeForInpaint`, `identity_reference` → `ApplyPulid` (method=fidelity,
  weight=0.8), `KSampler` (4-step lightning, denoise=0.6) → `VAEDecode` → `SaveImage`. Node titles
  match `providers.DEFAULT_NODE_BINDINGS` exactly (`base_image`/`face_mask`/`identity_reference`),
  verified against the PuLID node's actual `INPUT_TYPES` before running, not guessed.
- 2 real action test images of Linh An generated via `venho-social-content-agent/generate_image.py`
  (gpt-image-2, `--ref A2_Front.png`, paid API call) — jogging + over-the-shoulder poses, chosen
  to stress-test angle/motion deviation from the A2 identity authority. Face bbox for each detected
  with InsightFace (antelopev2) rather than eyeballed. Not committed (`data/` is gitignored) and
  not brand-approved wardrobe — technical test images only, never for publishing.

**Result: both jobs timed out (240s) — root cause is the machine's RAM, not the pipeline code.**

- Host: Mac mini M4, 16GB unified memory. `vm.swapusage` during the run: **20.9GB / 21.5GB swap
  used**, 590MB free — the process was thrashing, not stuck on a bug. Job 1 ran 8.6 minutes and
  never completed a single 4-step KSampler pass.
- SDXL base checkpoint (6.5G) + PuLID + EVA-CLIP (~2G, downloaded on first use) + InsightFace
  (CPU) loaded simultaneously exceed 16GB comfortably even though PuLID was the lightest of the
  3 identity-model options evaluated (PuLID / IPAdapter FaceID SD1.5 / InstantID SDXL) — "lightest
  of three" was a relative comparison, not a fit-in-16GB guarantee, and that gap wasn't checked
  before downloading. Server killed to release memory once swap was confirmed near-exhausted.
- **This is a genuine, reproducible finding, not a config bug**: `health_check()` returned `True`,
  `/upload/image` succeeded for all 3 assets, `inject_inputs()` wired the nodes correctly (queue
  inspection via `/queue` showed the exact expected graph), and the fail-fast error path from the
  P7 hardening review never triggered because ComfyUI itself never reported `status_str == "error"`
  — it was alive, just swapping.

**Decision (Harry, 2026-08-12): stop here, do not retry with a longer timeout or switch model.**
Recorded as a known issue rather than pursued further this session.

**Still open:**
- [ ] Identity-conditioning pipeline does not fit in 16GB unified memory as configured. Next
      attempt needs either a lighter stack (SD1.5-based IPAdapter FaceID instead of SDXL PuLID —
      untested, expected to need roughly ⅓ the checkpoint size) or more memory (cloud GPU / bigger
      Mac) before another live run is worth attempting.
- [ ] 10-image A2 benchmark — still blocked behind the above; only 2 test images exist so far
      (`data/action_composite_test/`, gitignored, not real benchmark inputs since restoration
      never completed).
- [ ] `config/comfyui/face_restore_v1_api.json` has never actually executed to completion — its
      node wiring was verified by inspection and by ComfyUI accepting the queued graph without
      validation error, not by a finished image.

## Growth Agent — per-topic Duyệt + real slot_date exposed (2026-08-13)

- [x] `list_pending()` exposes `slot_date` per row (parsed from `slot_id`).
- [x] New `approve_publications()` + CLI `approve-group` — approves one topic's ids atomically, `approve_week` unchanged.
- [x] 4 new tests, 45/45 pass in `test_growth_approve_and_dispatch.py`.
- [x] Confirmed 30 pre-existing unrelated failures elsewhere (daily_cycle/weekly_cycle) via stash-and-rerun.
- [x] Committed `58ad88d`, pushed to `origin/main`. Live immediately via editable pip install (`venho-growth --help` confirms `approve-group` registered).
- Counterpart work in `venho-os` (new `approve-group` route, dashboard UI): see that repo's own `task_status.md`/`task_memory.md`/`CLAUDE.md`, same date.

## Growth Agent — diversify 4 weekly posts by cadence-day topic lanes (2026-08-13)

- [x] `content_pillars.yaml` restructured to `lanes.<day>` — 4 distinct topic pools (west_lake_life/local_discovery/hotel_experience/local_guide_trend), 8-10 topics each, matching the master prompt's 5 pillars. Old `pillars`/`special_topics` kept as documented deprecated fallback.
- [x] `topic_selector.py` (new) — cooldown (60d) + least-recently-used selection against real posting history, replaces the bare modulo cursor.
- [x] `local_intel.py` (new) — approved-only (`status=approved`) research facts feed Wednesday's topic candidates + `creative_brief.proof_points` (previously always `[]`). Expired `local_events` filtered by end date.
- [x] `daily_cycle._pick_scenario` — per-lane `scenario_pool` rotation replaces the 1:1 `SCENARIO_BY_DNA_SUBJECT` map; weather override generalized from Saturday-only to every cadence day.
- [x] `social_prompts.py` — `prompt_rules`-based system prompt selection, local_discovery "only supplied facts" rule, SEO keyword block (Harry's 4 exact keywords), recent-topics anti-repeat hint.
- [x] `weekly_cycle.WEEKLY_CYCLE_JOB_VERSION` 3 → 4 (required — topic-selection contract changed).
- [x] Fixed pre-existing stale-DNA-filename fixture bug blocking `test_growth_daily_cycle.py`/`test_growth_weekly_cycle.py`/`test_growth_budget_gate.py` entirely (unrelated to this change, confirmed via git-stash baseline).
- [x] 20 new tests + 3 corrected; full suite 863 pass (70 pre-existing unrelated failures elsewhere, confirmed unchanged vs baseline).
- [x] Live production run (Harry approved): rejected 4 stale near-duplicate pending posts, ran real `venho-growth daily-cycle` for all 4 cadence days. Queue now has 4 genuinely distinct topics — Monday (curated westlake), Wednesday (**research-backed**, Chợ Hoa Quảng Bá fact), Friday (curated, lobby — first-ever use of this dna_subject), Saturday (**Trend Radar**, Sen Tây Hồ festival).
- [x] Committed `843a273`, pushed to `origin/main` (clean rebase onto 3 unrelated same-day CI commits, no conflicts).
- Known pre-existing, unrelated behavior noted (not fixed, not in scope): content-validator retry-then-drop silently dropped Wednesday's Facebook draft and Saturday's Facebook+Zalo drafts this run — Instagram/Threads queued fine for both days.
## Gemini Flash latest migration — COMPLETE WITH LOCAL CHANGES (2026-08-13)

- [x] Gemini adapter/config wired for Mode A/B/C (`gemini-flash-latest`).
- [x] `.env.local` key detected without exposing its value.
- [x] Real one-image Gemini smoke test passed with structured JSON.
- [x] Targeted offline suite: 64 passed.
- [ ] Two pre-existing subject-resolver/schema tests remain failing; unrelated to Gemini.
- [ ] Changes are local only; not committed/pushed in this task.

## Growth Agent — "Replace Rejected Content" all-jobs-failed fix (2026-08-13)

- [x] Root-caused via `gh run view --log-failed`: `model: String should have at least 1 character` — CI's `CLAUDE_CONTENT_MODEL` repo var doesn't exist, so `vars.CLAUDE_CONTENT_MODEL` resolves to `""`, and `os.environ.get(key, default)` doesn't fall back for a present-but-empty key.
- [x] Fixed both Claude call sites (`claude_social_generator.py`, `claude_generator.py`) to `os.environ.get(...) or DEFAULT` — falls back on both "absent" and "empty".
- [x] Added regression test `test_content_model_falls_back_when_env_var_is_set_but_empty`; 9/9 pass in `test_claude_social_generator.py`.
- [x] Affects all 3 workflows sharing this env var (`growth-replace-rejected.yml`, `growth-daily-cycle.yml`, `growth-blog-seo.yml`) — one fix covers all.
- [x] Committed `b351b19`, pushed to `origin/main`.
## Growth Agent — weekly slot horizon audit (2026-08-13)

- [x] Audited missing 21/08, 22/08 and 24/08 against historical workflow logs and registry.
- [x] Re-ran `Growth Agent Weekly Cycle`; run `31695771922` completed successfully.
- [x] Confirmed the three dates now exist remotely for Facebook and Instagram with status
  `PENDING_APPROVAL`.
- [x] Documented root cause: the previous run generated only one cadence week; corrected
  two-week cycle is active.

## VENHO GPU Identity Restoration v2.1 — GW-P0 baseline (2026-08-19)

- [x] **GW-P0-T2 Golden-Master Test — CLOSED/PASS.** Three authoritative fixed golden
  cases are stored under `tests/identity_restoration/golden/`; exact restored/composite
  hashes, pixelLock (`mutatedPixelCount=0`), cropTransform, seed `42`, and three frozen
  Face QC values per case are covered by the offline regression test.
- [x] Golden regression: `python3 -m pytest -q tests/test_gw_p0_t2_golden.py` — `2 passed`.
- [x] Relevant identity-restoration tests — `20 passed`.
- [x] **GW-P0 commit-hash item — PASS.**
  - `venho-ai-studio`: `f3cf924920812e6591f9c11b5e009fd36b610416`
  - `venho-os`: `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3`
  - Recorded in `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`.
- [x] Current Python + OS test baseline recorded; suites were executed as-is.
- [x] A2 SHA-256 đã được pin trong `workflow_pins.yaml`.
- [x] v1.0 SUPERSEDED marker đã được ghi vào workflow cũ.
- [x] Legacy workflow archived at `workflows/_archive/face_restore_v1_api.json`.
- [ ] **Next roadmap item:** ADR set.

## VENHO GPU Identity Restoration v2.1 — GW-P0 phase closure (2026-08-19)

- [x] ADR set complete: exactly 8 files, no ADR-GW-009.
- [x] Golden Master offline: `python3 -m pytest -q tests/test_gw_p0_t2_golden.py` → `2 passed`.
- [x] A2 authority, workflow archive, baseline docs, and Golden artifacts are present.
- [x] T1 evidence artifact exists and records current call graph, coupling matrix, contracts,
  boundaries, Phase-2 seams, invariants, risks, and provenance.
- [x] No second ActionCompositePipeline definition; no direct ComfyUI references in `venho-os/src`.
- [x] GW-P0 CLOSED/PASS; no blocker remains.
- [x] **GW-P1 — Windows GPU Worker: CLOSED/PASS (2026-08-20).** Evidence:
  `C:\VenHoGPU\evidence\gw-p1-20260820-210513` trên host `HARRY-ROG`. Chi tiết đầy đủ
  ở mục "GW Plan v2.1 — GW-P1 verifier aggregation repair (2026-08-20)" phía trên.

## VENHO GPU Identity Restoration v2.1 — GW-P0 legacy workflow archived (2026-08-19)

- [x] Archived `config/comfyui/face_restore_v1_api.json` → `workflows/_archive/face_restore_v1_api.json`.
- [x] SHA-256 preserved: `f7d04802135eb06db94e6b096b0dc269a644c3bebe90ec61f3855567dde32361`.
- [x] Updated `workflow_pins.yaml`, example config, and Golden-Master lineage to the archive path.
- [x] Reason recorded: superseded by current v2.x authority; historical workflow remains auditable.
- [ ] **Next roadmap item:** ADR set.

## VENHO GPU Identity Restoration v2.1 — GW-P0 v1.0 superseded (2026-08-19)

- [x] Marked `config/comfyui/face_restore_v1_api.json` as `SUPERSEDED`.
- [x] Authority chain recorded: current v2.x architecture + `VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`; v2.1 overrides v2.0 on conflict.
- [x] Historical workflow content preserved at `workflows/_archive/face_restore_v1_api.json`.
- [!] Referenced v1.0 worker-roadmap markdown is absent from the workspace; no replacement file was created.
- [x] Archive completed; next roadmap item is ADR set.
- Scope guard: no QC4I, no QC4 backlog work, no threshold/image-quality tuning, and no
  production architecture changes in this closeout.

## VENHO GPU Identity Restoration v2.1 — GW-P0 current test baseline (2026-08-19)

- [x] `venho-ai-studio` at `f3cf924920812e6591f9c11b5e009fd36b610416`:
  `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **951 passed, 70 failed, 0 skipped, 0 errors**.
- [x] Python failure baseline only: missing Lake View Room DNA fixture; subject-resolver/schema/
  overlay expectation mismatches; one Action Composite config expectation; missing raw asset fixture.
  No failures repaired.
- [x] `venho-os` at `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3`:
  `npm test -- --run` → **400 passed, 0 failed, 0 skipped, 0 errors** across 71 files.
- [x] Results recorded in `docs/Image studio/VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md`.
- [x] A2 SHA-256 đã được pin trong `workflow_pins.yaml`.
- [x] v1.0 SUPERSEDED marker đã được ghi vào workflow cũ.
- [x] Legacy workflow archived at `workflows/_archive/face_restore_v1_api.json`.
- [ ] **Next roadmap item:** ADR set.

## VENHO GPU Identity Restoration v2.1 — GW-P0 Nano Banana baseline (2026-08-19)

- [x] Existing authoritative Nano Banana masked-edit evidence recorded: `run-202608132052/variant-001`.
- [x] Face QC: **88.1 / revise**; comparison baseline/fallback only, not a production winner or new threshold.
- [x] A2 authority and SHA-256 match `workflow_pins.yaml`.
- [x] No new generation, API cost, production-code change, or quality optimization.
- [x] v1.0 SUPERSEDED marker đã được ghi vào workflow cũ.
- [x] Legacy workflow archived at `workflows/_archive/face_restore_v1_api.json`.
- [ ] **Next roadmap item:** ADR set.

### GW-P4-T0.5.2f — Canonical B01 Smoke Request Builder (2026-08-24)

**GW-P4-T0.5.2f = PASS.** Added a canonical B01 `RestoreCommand` builder so
the remote bootstrap smoke no longer requires an external request JSON. The
builder reuses the production `InsightFaceGeometryExtractor`,
`crop_for_identity()`, and `hierarchical_face_masks()` path and fail-closes on
frozen B01/A2/workflow/seed/parameter/geometry authority mismatches. An
optional request override is retained only with canonical authority and
production-derived transform validation. No physical smoke was run;
`comfyui-remote` remains NOT_READY pending real smoke evidence.

### GW-P4-T0.5.2g — Mac Geometry Runtime Dependency Closure (2026-08-24)

**GW-P4-T0.5.2g = FAIL/BLOCKED.** The production extractor expects
InsightFace `buffalo_l` via `FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])`.
A local `~/.insightface/models/buffalo_l` directory exists, but no signed
`MODEL.LICENSE`, manifest, artifact checksum record, or approved commercial
license provenance is present. No package was installed and no model download
or initialization was attempted. B01 and A2 hashes remain valid; geometry
preflight cannot run until model provenance is resolved.

### GW-P4-T0.5.2h — YuNet Commercial Geometry Compatibility Gate (2026-08-24)

**GW-P4-T0.5.2h = PASS.** The existing geometry contract requires exactly one
face bbox and five ordered landmarks; downstream PnP, `crop_for_identity()`,
and `hierarchical_face_masks()` remain unchanged. Added an explicit
`YuNetGeometryExtractor` using the official OpenCV Zoo
`face_detection_yunet_2023mar.onnx`, SHA-256
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`, with
the retained MIT license and pinned provenance record. YuNet is opt-in via
`IDR_GEOMETRY_BACKEND=yunet`; no silent fallback or production-default switch
was made. Real frozen B01 offline detection succeeded with one face,
confidence `0.9136796594`, five landmarks, and valid crop/mask geometry.
No ComfyUI, restoration, Face QC, or official benchmark ran.

### GW-P4-T0.5.2i — Remote Workflow Output Geometry Contract Diagnosis (2026-08-24)

**GW-P4-T0.5.2i = PASS.** The frozen remote graph preserves the uploaded crop
through `ImagePadForOutpaint` only long enough for the VAE path, then node `19`
`ImageCrop` hard-codes `687×659` and feeds node `14` `SaveImage`. The persisted
remote history confirms node `14` was the only final output and the adapter/client
selected it correctly. For the YuNet B01 crop `830×1003`, this is a fixed-size
workflow design incompatible with the restoration-port geometry contract, not
an adapter output-selection or post-hoc resize bug. No workflow or production
behavior was changed; a versioned dimension-preserving workflow correction is
required before physical smoke.

### GW-P4-T0.5.2j — Versioned Dimension-Preserving Remote Workflow (2026-08-24)

**GW-P4-T0.5.2j = FAIL/BLOCKED pending Windows deployment verification.**
Created candidate workflow `face_restore_win_sd15_ipadapter_v2` with local
SHA-256 `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`.
The v1 workflow remains byte-exact and active. v2 applies request-driven
multiple-of-8 padding to image and mask and request-driven final crop sizes;
the remote adapter injects those values without resizing or rebuilding
geometry. Local tests pass, but HARRY-ROG deployment/copy SHA equality cannot
be verified from this Mac environment, so benchmark authority remains v1 and
no physical inference was run.

### GW-P4-T0.5.2k — Remote Smoke Evidence Acceptance (2026-08-24)

**GW-P4-T0.5.2k = PASS.** Accepted the persisted physical smoke evidence at
`evidence/gw-p4-t0-5-2d-20260824T134922Z-5325a724/smoke_manifest.json`.
The evidence is `NON_BENCHMARK/PREFLIGHT`, `status=PASS`, and records
`executorStatus=COMPLETED`, prompt ID
`c0710730-28d1-4af5-b642-dbc46d2b4a28`, HARRY-ROG GPU evidence, and the active
workflow `face_restore_win_sd15_ipadapter_v2` with SHA-256
`1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`.

The restored crop is `830x1003`; its SHA-256 differs from the production-
derived input crop bytes for the recorded B01 `cropTransform`, and
pixel-lock is `PASS`. B01/A2 authorities match the frozen hashes. Therefore
`GW-P4-T0.5.2a = PASS`, `GW-P4-T0.5.2 = PASS`, and `comfyui-remote = READY`.

Preflight result: `control=READY`, `comfyui-local=READY`,
`comfyui-remote=READY`, `nano-banana-edit=NOT_READY`;
`officialBenchmarkReady=true`, `officialExecutionReady=false`. The only
remaining blocker is the missing Nano Banana benchmark executor. No smoke
rerun, Face QC, benchmark, tuning, or architecture change was performed.

### GW-P4-T0.5.3 — Nano Banana-Edit Benchmark Executor (2026-08-24)

**GW-P4-T0.5.3 = FAIL/BLOCKED.** Added
`NanoBananaEditBenchmarkExecutor` as a benchmark-only wrapper around an
injected existing Nano Banana/action-composite production port. It does not
create a second `ActionCompositePipeline`, provider client, crop/mask
algorithm, retry policy, or fallback path. It validates frozen base/A2
authorities, requires `masked_edit`, records provider/model/request/run IDs,
truthful `seedSupported`, retry/runtime and fallback flags, and writes
append-only success/failure evidence.

The existing production path was located in sibling Venho OS:
`GenerateStudioImageUseCase` → `GeminiImageProvider`, with
`prepareMaskedFaceEdit()` / `compositeMaskedFaceCrop()`. No callable adapter
from that path is registered in this Python composition root, so default
preflight remains fail-closed: control/local/remote READY,
nano-banana-edit NOT_READY, `officialBenchmarkReady=true`,
`officialExecutionReady=false`. No paid physical smoke was executed.

### GW-P4-T0.5.3a — Register Nano Banana Benchmark Adapter (2026-08-24)

**GW-P4-T0.5.3a = PASS.** Added
`identity_restoration.infrastructure.restorers.nano_banana_edit_adapter.NanoBananaEditAdapter`
and optional composition-root registration through
`build_nano_banana_benchmark_executor()`. Registration requires the existing
provider capability, `IDR_NANO_BANANA_ENABLED`, an injected existing
production path, canonical A2, request factory, and evidence root. Missing
configuration or path remains unregistered and fail-closed.

The adapter delegates to the already-composed Nano Banana production path; it
does not create a provider client, duplicate `GenerateStudioImageUseCase`,
create another `ActionCompositePipeline`, tune prompts, retry/select outputs,
or add fallback. The existing provider path remains the Venho OS
`GenerateStudioImageUseCase` → `GeminiImageProvider` masked-edit path.

`GW-P4-T0.5.3` remains FAIL/BLOCKED pending exactly one allowed
NON_BENCHMARK physical Nano Banana smoke. No paid call was executed.

### GW-P4-T0.5.3b — One Physical Nano Banana-Edit Smoke (2026-08-24)

**GW-P4-T0.5.3b = FAIL/BLOCKED before provider execution.** Precheck verified
the frozen B01 SHA
`e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9` and the
canonical A2 SHA
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
Existing provider configuration is present without exposing secrets:
`IMAGE_GENERATION_GOOGLE_ENABLED=true` and a `GEMINI_API_KEY` is resolvable
from the existing social-agent dotenv path; model authority is
`nano-banana-2` / `gemini-3.1-flash-image`.

The exact frozen B01 artifact has no mask or edit-region/crop lineage in its
manifest. The existing production `masked_edit` contract requires exactly one
base, one mask, and one A2 reference. No unrelated mask may be substituted and
no geometry may be hand-created in this smoke. Therefore no provider call was
made, no output/evidence bundle was fabricated, and paid call count is `0`.
`GW-P4-T0.5.3`, `GW-P4-T0.5`, and `GW-P4-T0` remain FAIL/BLOCKED.

### GW-P4-T0.5.3c — Freeze B01 Nano Banana-Edit Mask Lineage (2026-08-24)

**GW-P4-T0.5.3c = PASS for offline lineage freeze; physical Nano Banana smoke remains BLOCKED.**
The exact frozen B01 frame was verified at SHA-256
`e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9`, with
canonical A2 SHA-256
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
The existing production path `YuNetGeometryExtractor -> crop_for_identity() ->
hierarchical_face_masks()` produced one-face geometry, crop transform
`(119, 0, 949, 1003)`, crop-local mask `830x1003`, and full-canvas mask
`1024x1024`. Artifacts and provenance are frozen at
`artifacts/identity-restoration/benchmark-geometry/v2.1/B01/` and referenced
from `contracts/identity_restoration/benchmark_set.yaml`.

The implementation lock was corrected to the supplied authoritative
64-character SHA-256. The actual local model and existing production
provenance agree on
`8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`; no model
or detector bytes were changed. The Nano request factory now returns the
full-canvas mask plus explicit crop-local/full-canvas lineage, and the
benchmark executor rejects missing or mismatched geometry authority before any
provider call. Offline identity-restoration tests passed; no Nano Banana,
Face QC, benchmark, or network call was executed. `GW-P4-T0.5.3` remains
FAIL/BLOCKED pending exactly one allowed physical smoke.

### GW-P4-T0.5.3d — Add Nano Banana Physical Smoke CLI (2026-08-24)

**GW-P4-T0.5.3d = PASS for offline CLI wiring only.** `venho-restore
benchmark smoke --branch nano-banana-edit --case B01 --a2-path <canonical-a2>
--evidence-root evidence` now dispatches through the existing
`NanoBananaEditBenchmarkExecutor` composition seam, which delegates through
`NanoBananaEditAdapter` to the already-composed
`GenerateStudioImageUseCase -> GeminiImageProvider` path. It loads the frozen
B01 YuNet geometry authority, validates B01/A2/mask lineage before provider
execution, writes NON_BENCHMARK/PREFLIGHT evidence through the existing
executor, and never invokes Face QC or creates an official benchmark run.

The remote smoke path remains unchanged. Offline tests, compileall, and
`git diff --check` pass. No paid call or network call was made. The Nano
production port remains fail-closed unless it is injected by the existing
composition root; therefore `nano-banana-edit` is not promoted to READY and
`GW-P4-T0.5.3` remains FAIL/BLOCKED pending exactly one physical B01 smoke.

### GW-P4-T0.5.3 — Complete Nano Banana Readiness (2026-08-24)

**GW-P4-T0.5.3 = PASS.** One real NON_BENCHMARK/PREFLIGHT B01 Nano Banana
smoke completed through `NanoBananaEditBenchmarkExecutor` ->
`NanoBananaEditAdapter` -> existing VenHo OS
`GenerateStudioImageUseCase` -> `GeminiImageProvider`.

Physical evidence:

- provider/model: `nano-banana-2` / `gemini-3.1-flash-image`
- paid provider calls: `1`; retry count: `0`; seed metadata: `42`, `seedSupported=false`
- B01 SHA: `e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9`
- A2 SHA: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`
- output SHA: `d5ed883ef12166bd9da313252854e832eb74016528d754bd5d1c37f6669af17c`
- output: valid `1024x1024` PNG; `executorStatus=COMPLETED`
- `mockUsed=false`, `fallbackUsed=false`, `silentFallback=false`
- Face QC: not called; official benchmark row: not created

Evidence bundle:
`evidence/gw-p4-t0-5-3b-20260824T142500Z/preflight-b01-nano-smoke-20260824T142530242068Z/b01-nano-smoke-1/`.
The failed pre-provider path-validation attempt is retained separately under
the same evidence root; it consumed no paid call.

Preflight now validates persisted physical smoke evidence. Final matrix:
`control=READY`, `comfyui-local=READY`, `comfyui-remote=READY`,
`nano-banana-edit=READY`, `officialBenchmarkReady=true`,
`officialExecutionReady=true`. GW-P4-T0.5, GW-P4-T0, and GW-P4 are CLOSED/PASS.
GW-P4-T1 is not started.

### GW-P4-T1 — Run 3 validity recovery execution (2026-08-25)

Run `benchmark-20260825T033150Z-aea9d71a` was created as a new immutable
30-row recovery run after internal cache, branch-semantics, exact evidence
classification, and ledger-reuse fixes. It finished `21 completed / 9 failed`:

- `control`: planned 10, valid quality 0, evidence failures 10;
- `nano-banana-edit`: planned 10, valid quality 0, validator failures 5,
  evidence failures 5;
- `comfyui-remote`: planned 10, valid quality 0, reused evidence 6,
  infrastructure failures 4.

Nano provider calls in Run 3: **0**. Ten Nano outputs were reused by SHA and
source lineage. Six Remote outputs were reused; B03/B06 were recovered from
the restoration ledger after output persistence preceded Validator failure.
The four missing Remote cases failed closed after HARRY-ROG probes returned
`OFFLINE`; no new GPU job was submitted. Five Validator Studio calls still
returned malformed JSON.

The remaining 21 evidence failures are explicit because the current
Validator Studio adapter has no authoritative geometry/anatomy/outfit/
environment regional producer. Those scores remain null; no fabricated score
or hidden subset was used. Run 3 is therefore `INELIGIBLE`, with no official
treatment median. Run 1 and Run 2 remain immutable. GW-P4-T1 stays
`EXTERNAL BLOCKED / DECISION INELIGIBLE`; GW-P4 remains `IN PROGRESS`.

### GW-P4-T1 — Run 4 final validity-recovery attempt (2026-08-25)

Run `benchmark-20260825T041020Z-0c7002c0` is immutable with 30 planned and 30
terminal rows. Result: `INELIGIBLE`; no quality median was calculated.

- control: 10 completed, 0 valid quality, 10 evidence failures;
- nano-banana-edit: 7 completed, 3 Validator `429 RESOURCE_EXHAUSTED` failures,
  7 evidence failures, 0 new provider calls;
- comfyui-remote: 4 completed/reused, 6 infrastructure failures, 4 evidence
  failures.

The production Regional authority is
`ActionCompositePipeline -> RegionalScoreGateway -> RegionalGate`. A
fail-closed adapter now reuses only a complete persisted Gateway envelope;
none of the Run 1–3 benchmark artifacts contains authoritative
geometry/anatomy/outfit/environment evidence. Face/image scores, intent
metadata, and pixel preservation were not repurposed as regional scores.

Validator parsing now preserves raw responses before parsing, records sample
index/parse status, accepts fenced or harmlessly wrapped JSON, and rejects
truncated/schema-invalid responses. Run 3's five malformed responses cannot be
reparsed because raw payloads were not persisted historically. Run 4's three
Nano failures were provider quota errors with no raw response.

Tailscale ping to HARRY-ROG succeeds, while the ComfyUI endpoint and
`/system_stats` time out. Classification: `COMFYUI_PROCESS_DOWN`. No remote
startup action was available from this environment; no VRAM threshold or
workflow setting was changed. A post-Run-4 code correction now inventories
all Run 1–3 ledger records for Remote reuse, including Run 2 B03/B06; Runs 1–4
remain immutable.

Verification: identity-restoration **146 passed**, Action Composite/regional
**53 passed**, structured-response recovery tests passed, compileall PASS,
`git diff --check` PASS. GW-P4-T1 remains `EXTERNAL BLOCKED / DECISION
INELIGIBLE`; GW-P4 remains `IN PROGRESS`; GW-P5 was not started.

### GW-P4-T1 — Run 5 and orthogonal validity semantics (2026-08-25)

Run `benchmark-20260825T042453Z-b86d8854` is immutable: 30/30 terminal,
21 completed, 9 failed. Decision-valid rows are Control `0/10`, Nano `0/10`,
Remote `0/10`. Control has 10 completed rows and Nano has 7 completed reused
rows, but all lack a complete authoritative `RegionalScoreGateway` envelope;
the values remain null and no score was fabricated. Nano's other 3 rows are
Validator `429 RESOURCE_EXHAUSTED` failures with zero new Nano calls.

The benchmark runner now distinguishes execution/evidence/Validator/
Regional/pixel/authority/decision validity from `qualityGatePass`. A measured
quality failure remains decision-valid and stays in the median population.
Control has no restored-crop/workflow/GPU requirement; Nano has no ComfyUI
requirement; Remote retains its frozen workflow requirements.

HARRY-ROG is Tailscale-reachable. HTTPS `/system_stats` serves the pinned
ComfyUI with GTX 1660 SUPER and approximately 5067 MiB free after normal
`/free` recovery. Run 5 created only B02 and B08 new Remote outputs; B03/B06
were reused, and B04/B10 were blocked by the unchanged VRAM gate. Because
Control/Nano are not 10/10 decision-valid, this is not yet a genuine final
`EXTERNAL_BLOCKED` decision; it remains `INELIGIBLE` pending authoritative
Regional evidence. GW-P4 remains IN PROGRESS and GW-P5 was not started.

Verification: focused benchmark validity 56 passed; identity-restoration
suite 150 passed; full suite 1114 passed with 76 pre-existing environment/
fixture failures; compileall and `git diff --check` pass.

### GW-P4-T1 — Regional authority resolution and offline Run-6 gate (2026-08-25)

Repository tracing proves `RegionalScoreGateway` is a real production mapper,
not an interface-only name: `build()` consumes explicit Validator Studio,
geometry, scene-candidate, and preservation evidence; `replay()` persists its
result; `ActionCompositePipeline` wires it before `RegionalGate.evaluate()`.
The approved GW-P4 roadmap requires a healthy Regional PASS/FAIL gate, while
the benchmark runner had overreached by requiring all seven numeric Regional
scores. Root cause: **R3 — CONTRACT_OVERREACH**.

The smallest alignment is implemented. Rows may now carry an authority-bound
`regionalGateEvidence` envelope with `passed`, `failures`, and `evidenceId`;
PASS and FAIL are both decision-valid when complete. Missing/corrupt/untrusted
evidence remains invalid. No second scorer and no inferred score were added.

Offline recovery over Runs 1–5 found 0 gate envelopes and 0 complete persisted
Regional production manifests for benchmark artifacts. Therefore Control,
Nano, and Remote cannot be promoted to decision-valid from existing evidence;
no Run 6 was created. Runs 1–5 remain unchanged. HARRY-ROG is not the current
Control/Nano blocker; this is not a genuine external-blocked decision.

Verification: focused benchmark/orchestration/gateway 48 passed; Action
Composite/regional 63 passed; identity-restoration 152 passed; full suite
1116 passed / 76 unrelated pre-existing environment/fixture failures;
compileall and `git diff --check` passed. GW-P4-T1 remains `INELIGIBLE`,
GW-P4 remains `IN PROGRESS`, and GW-P5 was not started.

### GW-P4-T1 — Materialize Regional evidence and complete missing Remote outputs (2026-08-25)

`BenchmarkRegionalEvidenceAdapter` now invokes the existing production
`RegionalScoreGateway`, uses production geometry and preservation adapters, and
persists immutable evidence under
`artifacts/identity-restoration/benchmarks/regional-evidence/materialized-20260825T054205Z/`.
Runs 1–5 were not modified.

- Control: 10/10 Regional evidence; 10/10 decision-valid. Two Regional PASS and eight valid Regional FAIL quality observations.
- Nano: 7/10 Regional evidence and decision-valid. B02/B04/B05 have no matching three-sample Validator evidence for their output SHA; no provider call was made.
- Remote: existing output artifacts were reused for B01/B02/B03/B05/B06/B07/B08/B09; only B04 and B10 were executed on HARRY-ROG. Both completed with the frozen workflow/seed/params and healthy GTX 1660 SUPER worker. Validator evidence is still available for only B01/B05/B07/B09, so Remote is 4/10 decision-valid.

A production Validator recovery probe returned `429 RESOURCE_EXHAUSTED`
(`prepayment credits are depleted`). No score was fabricated and no repeated
paid call was made. Same production validity dry-run: Control `10/10`, Nano
`7/10`, Remote `4/10`. Run 6 was not created because all branches must be
`10/10`; this does not qualify as genuine `EXTERNAL_BLOCKED` under the task
rule. Final status: **GW-P4-T1 INELIGIBLE; GW-P4 IN PROGRESS; GW-P5 NOT STARTED**.

Verification: identity-restoration **153 passed**; Action Composite/regional
**77 passed**; full suite **1117 passed / 76 unrelated pre-existing failures**;
compileall and `git diff --check` passed.

### GW-P4-T1 — Validator credit-recovery resume preflight (2026-08-25)

The required smallest readiness check was executed through the existing
`BenchmarkValidatorAdapter` on the frozen Nano B01 output, with provider
`gemini`, rubric `07F`, and `samples=3`. It failed on the first live request:
`429 RESOURCE_EXHAUSTED` — `Your prepayment credits are depleted.` No raw
provider response was available to persist, no score was parsed, and no
additional Validator call was attempted. The immutable preflight record is at
`artifacts/identity-restoration/benchmarks/validator-preflight-20260825T055001Z/result.json`.

No Nano generation, Remote inference, or Run 6 creation occurred. The last
valid pre-run evidence remains Control `10/10`, Nano `7/10`, Remote `4/10`;
missing evidence remains Nano B02/B04/B05 and Remote B02/B03/B04/B06/B08/B10
at the Validator/Regional evidence boundary. Final status for this resume
attempt: **GW-P4-T1 EXTERNAL_BLOCKED / INELIGIBLE; GW-P4 IN PROGRESS; GW-P5
NOT STARTED**. Human action is still required to restore Validator project
prepayment credits/quota; provider/model/configuration were not changed.

### GW-P4-T1 — Resume after Validator READY: recovery gate and final decision (2026-08-25)

Validator readiness was confirmed before execution with the unchanged
`gemini` / `gemini-3.5-flash` / `samples=3` / `mock=false` / `fallback=false`
configuration. Runs 1–5 remain immutable. A reuse index was extended for the
already-completed B04/B10 HARRY-ROG recovery artifacts; no Remote prompt was
submitted and no Nano provider call was submitted.

Recovery materialized evidence only through the production
`BenchmarkRegionalEvidenceAdapter -> RegionalScoreGateway -> RegionalGate`
path. Exact reusable Remote cases were B01/B02/B03/B04/B05/B06/B07/B08/B09/B10;
B04/B10 source artifacts are under `recovery-remote-20260825TB04` and
`recovery-remote-20260825TB10`. Final recovery evidence counts were Control
10/10, Nano 8/10, and Remote 8/10, all matching decision-valid counts. Nano
new generations were 0 and Remote new GPU jobs were 0.

Historical Validator evidence was reused for 21 branch rows. Five additional
three-sample evaluations completed (Nano B05; Remote B02/B03/B04/B10). Four
output cases remain unvalidated after controlled recovery attempts because the
production Gemini response was truncated: Nano B02/B04 and Remote B06/B08.
Their raw responses were persisted before parsing and rejected fail-closed; no
score was fabricated and no low valid score was discarded.

The pre-run-6 gate therefore remained false (`10/10`, `8/10`, `8/10`), so Run 6
was not created. Official treatment statistics and a PASS/QUALITY_FAIL result
are not decision-valid. This is a genuine external Validator dependency block
after internal reuse/recovery: **GW-P4-T1 = EXTERNAL_BLOCKED / INELIGIBLE**;
**GW-P4 = IN PROGRESS**; **GW-P5 = NOT STARTED**. No fallback, mock, prompt
tuning, workflow tuning, or best-of-N was used.

Face QC recovery matrix (`UNVALIDATED` means no complete three-sample report):

| Case | Control | Nano | Remote |
|---|---:|---:|---:|
| B01 | 94.92 | 96.35 | 93.32 |
| B02 | 94.18 | UNVALIDATED | 94.55 |
| B03 | 91.07 | 90.60 | 90.60 |
| B04 | 90.60 | UNVALIDATED | 90.82 |
| B05 | 87.17 | 88.65 | 88.00 |
| B06 | 85.78 | 88.55 | UNVALIDATED |
| B07 | 90.60 | 90.60 | 92.28 |
| B08 | 95.80 | 95.15 | UNVALIDATED |
| B09 | 93.85 | 93.65 | 91.85 |
| B10 | 65.58 | 68.45 | 0.00 |

Partial observed Remote QC (N=8, not an official treatment statistic) was
median 91.335, mean 80.1775, min 0, max 94.55. Quality gates were not
evaluated as an official decision because the 30-row population was not
decision-eligible.

Verification: recovery/reuse/Nano/Remote focused **57 passed**; Action
Composite/regional **97 passed**; full identity-restoration suite **153
passed**; full suite **1117 passed / 76 pre-existing environment/fixture
failures**; compileall and `git diff --check` passed.

### GW-P4-T2 — Offline truncation audit and bounded recovery authorization (2026-08-25)

Persisted C1/B03 raw response audit: 1091 bytes, parser input 1091 bytes,
parse failure at byte 1091 while opening `weighted_scores`. Ledger evidence:
`FinishReason.MAX_TOKENS`, prompt/input 5265, candidate output 1173. HTTP,
finish message, candidate/parts counts, thinking, total, and cached-content
fields were not persisted and remain null; no semantic repair was made.
Classification: **T1**. The smallest fix changed `max_output_tokens` 2048 →
4096; provider/model, DTO, rubric, samples=3 authority, and thinking remain
unchanged. Offline fixtures pass (`29 passed`, paid tests `0`). One recovery
request is bounded to C1/B03 sample 1; B04 and all downstream stages remain
untouched.

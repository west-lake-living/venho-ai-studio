# GW-P4 Controlled A2 Benchmark Report

## 1. Executive result

**Current GW-P4-T1 state: FAIL / RUN 6 QUALITY GATE FAILED. GW-P4: IN PROGRESS.**
Run 6 `benchmark-20260825T160000Z-gw-p4-t1` is the canonical reuse-only
consolidation. Runs 1–5 remain immutable; GW-P5 remains NOT STARTED.
The earlier EXTERNAL_BLOCKED runs below remain immutable historical evidence;
the paid-call-guarded recovery is recorded in section 4.10.
The Nano root cause was `EXPECTED_SERVICE_NOT_RUNNING`: `127.0.0.1:3000` is the
existing Venho OS Next.js service exposing
`GET/POST /api/v1/identity-restoration/nano-banana-smoke`. It was recovered with
the canonical `venho-os` `npm run dev`; zero-cost GET returned configured
`nano-banana-2` / `gemini-3.1-flash-image` with no fallback.

The first official attempt created 30 terminal failure rows but is invalid for
decision purposes: it exposed two internal integration defects (relative A2
path and dropped `providerConfigured`) and remote health was not yet a
preflight gate. A corrected attempt
(`benchmark-20260825T015837Z-7d0e4f0d`) is also invalid infrastructure
evidence: B01 Nano completed with real provider evidence, while B02–B10 hit a
B01-only route authority check and row persistence was incomplete. The existing
Venho OS route was corrected to use each case's authority; row writes now
flush. HARRY-ROG currently reports `DEGRADED` with 2.69 GiB free VRAM, below
the existing 4200 MB health gate. The approved `/free` call recovered the
worker to 5067 MB free, above the unchanged threshold.

New official run `benchmark-20260825T021915Z-157c9b14` is preserved as immutable
evidence, but its recorded `QUALITY_FAIL` is not decision-eligible. The audit
found 10 real Nano provider outputs, 5 real remote outputs, and downstream
validator/evidence failures; the reported remote median **91.85** used only
B05/B07/B09 (N=3), so it is not a decisive treatment median. No quality retry,
tuning, fallback, mock, or best-of-N was used.

After the internal audit fixes, a new 30-row validity run
`benchmark-20260825T030340Z-df1d875a` was executed with explicit artifact reuse.
It is also decision-ineligible: 30/30 terminal rows, 18 completed, 12 failed,
with classification counts `EVIDENCE_PIPELINE_FAIL=18`,
`VALIDATOR_FAIL=8`, `INFRA_EXECUTION_FAIL=4`, and zero valid quality rows.
Nano reused all 10 prior provider outputs and made zero new provider calls.

## 2. Frozen authorities

- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`
- Geometry: `yunet`, `face_detection_yunet_2023mar.onnx`, SHA-256
  `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- Remote workflow: `face_restore_win_sd15_ipadapter_v2`, SHA-256
  `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`
- Seed: `42`; Face QC samples: `3`
- Nano: `nano-banana-2` / `gemini-3.1-flash-image`; deterministic seed support
  remains provider-reported and is not fabricated.

## 3. Dataset and official branches

B01–B10 remain the locked frozen dataset. Every case has one authoritative
base frame and source SHA. Official branches are exactly:

1. `control`
2. `nano-banana-edit`
3. `comfyui-remote`

Official rows expected: **30**. `comfyui-local` remains an adapter and
rollback capability only.

## 4. Preflight and execution

Structural validation: PASS. Official plan: **30 rows**. The live composition
matrix was `control=READY`, `nano-banana-edit=READY`,
`comfyui-remote=READY` after VRAM recovery. During the batch, remote cases
failed closed when the pre-case health gate remained degraded after `/free`;
the recovery policy did not submit `/prompt` in that state.

Invalid attempts: `benchmark-20260824T150014Z-94c8cb21` (30/30 failed) and
`benchmark-20260825T015837Z-7d0e4f0d` (7 completed, 23 failed). Both are
retained as infrastructure evidence and are not quality results.

## 4.1 Benchmark Validity Audit — audited run

Run `benchmark-20260825T021915Z-157c9b14` remains immutable. The terminal
`FAILED` state was audited separately from quality:

| Case | Branch | Terminal | Execution/output evidence | Face QC | Classification |
|---|---|---:|---|---:|---|
| B01 | control | COMPLETED | source output; validator complete, regional fields absent | 94.92 | EVIDENCE_PIPELINE_FAIL |
| B01 | nano | FAILED | provider completed; output SHA `c9f701…`; pixel recalculation PASS | — | EVIDENCE_PIPELINE_FAIL |
| B01 | remote | FAILED | physical output exists; validator JSON failed | — | VALIDATOR_FAIL |
| B02 | control | COMPLETED | source output; regional fields absent | 94.18 | EVIDENCE_PIPELINE_FAIL |
| B02 | nano | FAILED | provider completed; output SHA `f8350a…`; validator JSON failed | — | VALIDATOR_FAIL |
| B02 | remote | FAILED | no prompt; VRAM health gate | — | INFRA_EXECUTION_FAIL |
| B03 | control | FAILED | no row evidence; base validator JSON failed | — | VALIDATOR_FAIL |
| B03 | nano | FAILED | provider completed; output SHA `b4fa90…`; base validator JSON failed | — | VALIDATOR_FAIL |
| B03 | remote | FAILED | physical output exists; base validator JSON failed | — | VALIDATOR_FAIL |
| B04 | control | COMPLETED | source output; regional fields absent | 90.60 | EVIDENCE_PIPELINE_FAIL |
| B04 | nano | FAILED | provider completed; output SHA `3b363e…`; validator JSON failed | — | VALIDATOR_FAIL |
| B04 | remote | FAILED | no prompt; VRAM health gate | — | INFRA_EXECUTION_FAIL |
| B05 | control | FAILED | base output exists; validator JSON failed | — | VALIDATOR_FAIL |
| B05 | nano | FAILED | provider completed; output SHA `e70853…`; validator JSON failed | — | VALIDATOR_FAIL |
| B05 | remote | COMPLETED | output SHA `d21207…`; regional fields absent | 88.00 | EVIDENCE_PIPELINE_FAIL |
| B06 | control | COMPLETED | source output; regional fields absent | 85.78 | EVIDENCE_PIPELINE_FAIL |
| B06 | nano | FAILED | provider completed; output SHA `e115f0…`; pixel recalculation PASS | — | EVIDENCE_PIPELINE_FAIL |
| B06 | remote | FAILED | no prompt; VRAM health gate | — | INFRA_EXECUTION_FAIL |
| B07 | control | FAILED | base validator JSON failed | — | VALIDATOR_FAIL |
| B07 | nano | FAILED | provider completed; output SHA `19f07c…`; base validator JSON failed | — | VALIDATOR_FAIL |
| B07 | remote | COMPLETED | output SHA `f51d9a…`; regional fields absent | 92.28 | EVIDENCE_PIPELINE_FAIL |
| B08 | control | COMPLETED | source output; regional fields absent | 95.80 | EVIDENCE_PIPELINE_FAIL |
| B08 | nano | FAILED | provider completed; output SHA `226273…`; pixel recalculation PASS | — | EVIDENCE_PIPELINE_FAIL |
| B08 | remote | FAILED | no prompt; VRAM health gate | — | INFRA_EXECUTION_FAIL |
| B09 | control | COMPLETED | source output; regional fields absent | 93.85 | EVIDENCE_PIPELINE_FAIL |
| B09 | nano | FAILED | provider completed; output SHA `7c5be0…`; pixel recalculation PASS | — | EVIDENCE_PIPELINE_FAIL |
| B09 | remote | COMPLETED | output SHA `69ae0d…`; regional fields absent | 91.85 | EVIDENCE_PIPELINE_FAIL |
| B10 | control | COMPLETED | source output; regional fields absent | 65.58 | EVIDENCE_PIPELINE_FAIL |
| B10 | nano | FAILED | provider completed; output SHA `5a25d3…`; pixel recalculation PASS | — | EVIDENCE_PIPELINE_FAIL |
| B10 | remote | FAILED | no prompt; VRAM health gate | — | INFRA_EXECUTION_FAIL |

Counts for this audit: `VALID_QUALITY_PASS=0`, `VALID_QUALITY_FAIL=0`,
`INFRA_EXECUTION_FAIL=5`, `VALIDATOR_FAIL=10`,
`EVIDENCE_PIPELINE_FAIL=15`, `AUTHORITY_FAIL=0`. Nano calls attempted/succeeded:
10/10; usable outputs recovered: 10; no Nano row had complete required
regional evidence. Remote executor attempts were 10; physical jobs produced
5 outputs (B01/B03/B05/B07/B09), while B02/B04/B06/B08/B10 were blocked by
the frozen VRAM health gate.

The original remote median **91.85** is exactly the median of
`B05=88.00`, `B07=92.28`, and `B09=91.85`. All three were terminal
`COMPLETED`, but the population was partial and their anatomy/outfit/
environment/geometry evidence was absent. No failed row was silently included
and no intended case was silently dropped from the 30-row plan.

## 4.2 Validity recovery run

Run `benchmark-20260825T030340Z-df1d875a` is a new immutable 30-row run created
after the audit fixes. It reused all 10 Nano provider artifacts and the 3
remote rows with verified output/lineage; no Nano provider call was repeated.
The frozen Nano `UNKNOWN` pixel evidence is recomputed offline and passes for
the reused artifacts. The run still cannot support a quality decision:

- `decisionEligible=false`; valid comparable rows are `0/10` for every branch.
- `EVIDENCE_PIPELINE_FAIL=18`: required regional/anatomy/outfit/environment/
  geometry scores are intentionally absent rather than fabricated.
- `VALIDATOR_FAIL=8`: Validator Studio returned malformed JSON for the affected
  artifact/base evaluations.
- `INFRA_EXECUTION_FAIL=4`: remote VRAM recovery was attempted once per case,
  then the worker remained below 4200 MB and execution was fail-closed.

New-run remote Face QC by frozen case is
`B01=93.32, B02=—, B03=—, B04=—, B05=88.00, B06=—, B07=92.28,
B08=—, B09=91.85, B10=—`; no median is decision-eligible.

This is an external validity block, not `QUALITY_FAIL`; no hard quality gate
may be asserted from either run.

## 5–18. Results, gates, taxonomy, cost, lineage, and decision

The audited run's historical branch statistics were control **93.85 / 88.67 /
65.58 / 95.80** across 7 completed rows, Nano **N=0** terminal completed rows,
and remote **91.85 / 90.71 / 88.00 / 92.28** across B05/B07/B09 only. The
validity recovery run reports no decisive median because all three branches
have fewer than 10 valid comparable rows. All 30 intended rows remain present
and terminal in each run; infrastructure and validator failures are retained,
not converted to zeros or dropped.

## 19. No-promotion statement

No image, workflow, provider strategy, production default, dashboard, or
registry was promoted or changed.

## 4.3 Run 3 — validity recovery execution

Run `benchmark-20260825T033150Z-aea9d71a` is the new immutable recovery run
created after the cache, branch-semantics, and ledger-reuse fixes. It contains
30 terminal rows: `21 completed / 9 failed`.

| Branch | Planned | Valid quality | Quality pass | Quality fail | Infra fail | Validator fail | Evidence fail | Authority fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control | 10 | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| nano-banana-edit | 10 | 0 | 0 | 0 | 0 | 5 | 5 | 0 |
| comfyui-remote | 10 | 0 | 0 | 0 | 4 | 0 | 6 | 0 |

Run 3 made zero new Nano provider calls. All ten Nano outputs were reused by
verified SHA and source evidence. Six Remote outputs were reused; B03/B06 were
rehydrated from the immutable restoration ledger after prior Validator failure,
without a new GPU job. Four missing Remote cases probed HARRY-ROG and failed
closed because the worker was `OFFLINE` from this environment. Validator Studio
produced five further malformed JSON responses.

The remaining 21 evidence failures are explicit: current Validator Studio
face/image reports provide Face QC, identity, eyes/brows, and global scores but
no authoritative geometry/anatomy/outfit/environment regional producer. Those
fields remain null by contract; no score was fabricated. Run 3 is therefore
`decisionEligible=false`, with `validQualityRows=0/10` for every branch and no
treatment median. Run 1 and Run 2 remain untouched and immutable.

## Validation

Focused transport/orchestration, infrastructure, classification, artifact
reuse, and action-composite tests: **116 passed**;
full repository suite: **1100 passed, 76 failed** on unrelated Google Drive
credential/DNA fixture issues. Geometry setup successfully derived and
persisted authorities for B01–B10; `compileall` and `git diff --check` pass.

## 4.4 Run 4 — final validity-recovery attempt

Run `benchmark-20260825T041020Z-0c7002c0` is immutable and contains exactly
30 planned and 30 terminal rows. It is **INELIGIBLE**, not a quality decision:

| Branch | Planned | Completed | Valid quality | Evidence fail | Validator fail | Infra fail |
|---|---:|---:|---:|---:|---:|---:|
| control | 10 | 10 | 0 | 10 | 0 | 0 |
| nano-banana-edit | 10 | 7 | 0 | 7 | 3 | 0 |
| comfyui-remote | 10 | 4 | 0 | 4 | 0 | 6 |

Regional authority was traced to `ActionCompositePipeline ->
RegionalScoreGateway -> RegionalGate`. The new adapter only rehydrates a
complete persisted `regional_scores` envelope from that production manifest;
it does not map image score, intent, or pixel preservation into anatomy,
outfit, or environment. No complete production Regional envelope exists for
the benchmark artifacts, so all completed rows correctly remain evidence
ineligible. Thresholds are unchanged.

Validator hardening now preserves raw provider text and sample index before
JSON/contract parsing, supports fenced or harmlessly wrapped JSON, and rejects
truncated/schema-invalid content without repair. Run 3's five malformed
responses have no retained raw payload, so they cannot be safely reparsed.
Run 4's three Nano failures were provider `429 RESOURCE_EXHAUSTED` failures;
no raw response existed. No score was inferred.

Artifact inventory before Run 4 found Control 10/10, Nano 10/10, and Remote
6/10 reusable outputs across Runs 1–3. Run 4 made **0 new Nano provider
calls** and produced no new Nano evidence directory. Four Remote composites
were reused in Run 4; a post-run correction now scans all immutable Run 1–3
ledger records, including Run 2 B03/B06, for the next recovery invocation.
Run 4 itself remains untouched.

Tailscale can ping `harry-rog` (1 ms), but `100.71.167.98:8188` and
`harry-rog:8188/system_stats` time out. Classification: `COMFYUI_PROCESS_DOWN`;
no startup or public exposure was attempted, and the 4200 MB VRAM threshold
was not changed.

Run 4 summary: `EVIDENCE_PIPELINE_FAIL=21`, `VALIDATOR_FAIL=3`,
`INFRA_EXECUTION_FAIL=6`, valid quality rows `0/30`, no treatment median, and
decision `INELIGIBLE`. GW-P4-T1 remains blocked by missing authoritative
Regional evidence, Validator provider exhaustion, and HARRY-ROG ComfyUI
unavailability; GW-P4 remains `IN PROGRESS`. GW-P5 was not started.

Post-recovery verification: identity-restoration tests **146 passed**;
Action Composite/regional tests **53 passed**; structured-response recovery
tests passed; `compileall` and `git diff --check` pass.

## 4.5 Run 5 — Control/Nano validity semantics and HARRY-ROG recovery attempt

Run `benchmark-20260825T042453Z-b86d8854` is a new immutable official run;
Runs 1–4 were not modified. It contains 30 planned and 30 terminal rows:
21 completed and 9 failed.

| Branch | Planned | Completed | Decision-valid | Quality pass | Quality fail | Evidence fail | Validator fail | Infra fail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control | 10 | 10 | 0 | 0 | 0 | 10 | 0 | 0 |
| nano-banana-edit | 10 | 7 | 0 | 0 | 0 | 7 | 3 | 0 |
| comfyui-remote | 10 | 4 | 0 | 0 | 0 | 4 | 4 | 2 |

The runner now records independent validity dimensions for execution,
evidence, Validator, Regional, pixel, authority, decision, and quality-gate
status. A complete row with Face QC below 90, Regional FAIL, or Pixel FAIL
remains decision-valid and participates in statistics. Control does not
require provider/workflow/GPU/restored-crop evidence; Nano does not require
ComfyUI fields; Remote retains its pinned workflow/crop/mask lineage.

The remaining Control/Nano root cause is not HARRY-ROG: completed rows have
output and three-sample QC but no complete persisted `RegionalScoreGateway`
envelope. The adapter remains fail-closed; no geometry/anatomy/outfit/
environment score was fabricated. Nano's three failed rows returned
`429 RESOURCE_EXHAUSTED`; Run 5 made zero new Nano provider calls.

Remote inventory before Run 5 contained six reusable outputs
(`B01,B03,B05,B06,B07,B09`). HARRY-ROG was Tailscale-reachable and HTTPS
`/system_stats` returned GTX 1660 SUPER with about 5067 MiB free. Only B02
and B08 created new GPU outputs; B03/B06 were reused and B04/B10 were later
blocked by the unchanged VRAM gate. No fallback, mock, public exposure,
threshold change, or quality retry occurred.

Run 5 remains `decisionEligible=false` and `INELIGIBLE`; no treatment median
or final quality gate is asserted. The task's condition for a genuine
`EXTERNAL_BLOCKED` final status—Control and Nano both 10/10 decision-valid—
has not been met because authoritative Regional evidence is still absent.

## 4.6 Regional Authority Resolution — R3 contract alignment (2026-08-25)

The repository trace resolves the remaining Regional ambiguity as **R3 —
CONTRACT_OVERREACH**, not R4 and not an external runtime blocker.

| Question | Repository proof |
|---|---|
| Port/interface and methods | `image_studio_runtime/action_composite/regional_score_gateway.py:RegionalScoreGateway` exposes `build(RegionalScoreEvidence)` and `replay(run_dir, evidence)`; the production gate is `workflow_v2:RegionalGate.evaluate()`. |
| Gateway inputs | Explicit Validator Studio face/image reports, explicit geometry evidence or score, explicit scene-candidate anatomy/outfit/environment evidence, and post-restoration preservation evidence. Missing values raise `RegionalScoreBlocked`; no default score exists. |
| Gateway output | `RegionalScoreResult(scores, sources, provenance)`; `ActionCompositePipeline` passes those scores into `RegionalGate` and persists the result in `manifest.json`. |
| Production wiring | `ActionCompositePipeline` constructs/uses `RegionalScoreGateway` when `regional_evidence` is supplied; `ProductionRunner` forwards that dependency. `RegionalGate` remains the final PASS/FAIL evaluator. |
| Roadmap intent | The approved GW-P4 gate is “median Face QC >= 90, regional/pixel gate healthy”; the Action Composite plan defines Anatomy, Outfit, and Environment as `PASS / FAIL`, not mandatory benchmark numeric scores. |
| Benchmark defect | The benchmark runner required all seven numeric Regional fields, even though the authoritative acceptance contract can be represented by a complete production `RegionalGate` PASS/FAIL envelope. |
| Contract/schema origin | `benchmark_runner.py` and `benchmark_row.schema.json` introduced the numeric row fields; the schema permits them to be null, while the runner incorrectly treated null as invalid even when a production gate result could be sufficient. |
| Test origin | Existing gateway tests prove fail-closed explicit-source mapping; benchmark tests encoded the stricter numeric-row assumption. New regression tests cover gate PASS/FAIL, missing authority, and no fabricated score. |
| Historical artifact origin | Runs 1–5 contain Face/Image QC, geometry manifests, and pixel/lineage data, but zero persisted production Regional gate envelopes for their benchmark outputs. |

The smallest correction is implemented: `benchmark_row.schema.json` accepts
`regionalGateEvidence`, and the runner accepts a complete, authority-bound
`RegionalGate` result with either `passed=true` or `passed=false`. A valid gate
FAIL is decision-valid and quality-fail; absent, malformed, or untrusted gate
evidence remains decision-invalid. Numeric `RegionalScoreGateway` envelopes
remain supported for compatibility. No second scoring implementation was
added, and no score is derived from Face QC, geometry alone, pixel counts,
intent metadata, or averages.

Offline recovery against Runs 1–5 found **0** benchmark rows with an explicit
`regionalGateEvidence` envelope and **0** companion benchmark manifests with a
complete persisted `regional_scores`/production Regional gate envelope. The
existing geometry manifests and Validator cache therefore cannot make any
Control, Nano, or Remote row decision-valid. Runs 1–5 remain byte-immutable;
their row SHA-256 values were rechecked after the audit.

Verification after alignment: focused benchmark/orchestration/gateway tests
**48 passed**; Action Composite/regional tests **63 passed**;
identity-restoration suite **152 passed**; full repository suite **1116 passed,
76 failed** on the pre-existing Google Drive token/DNA fixture environment;
`compileall` and `git diff --check` passed.

Run 6 was **not created** because the required authoritative Regional evidence
does not exist in the artifact pool. Current status remains
`GW-P4-T1 = INELIGIBLE`, `GW-P4 = IN PROGRESS`; no PASS, QUALITY_FAIL, or
genuine EXTERNAL_BLOCKED decision is asserted, and GW-P5 was not started.

## 4.7 Regional evidence materialization and Remote completion (2026-08-25)

The remaining execution used a thin benchmark adapter around the existing
production path:

`BenchmarkRegionalEvidenceAdapter -> RegionalScoreGateway -> RegionalGate`

The adapter uses persisted three-sample Validator Studio face/image reports,
the frozen YuNet geometry authority plus a fresh production observation, and
the existing `StagePreservationEvidenceAdapter`. It writes immutable evidence
under `artifacts/identity-restoration/benchmarks/regional-evidence/materialized-20260825T054205Z/`.
It does not calculate a benchmark-specific score, infer missing scene values,
or modify Runs 1–5.

| Branch | Regional evidence | Dry-run decision-valid | Notes |
|---|---:|---:|---|
| control | 10/10 | 10/10 | 2 Regional PASS, 8 valid Regional FAIL quality results |
| nano-banana-edit | 7/10 | 7/10 | B02/B04/B05 have no matching Validator evidence by output SHA |
| comfyui-remote | 4/10 | 4/10 | B01/B05/B07/B09 materialized; other output/QC evidence remains incomplete |

Remote output inventory was completed without rerunning reusable cases.
Existing authority-valid outputs covered B01, B02, B03, B05, B06, B07, B08,
and B09. Only genuinely missing outputs B04 and B10 were executed through
`ComfyUIRemoteBenchmarkExecutor` with the frozen workflow, SHA, seed 42,
parameters, and concurrency 1. Both completed on HARRY-ROG with the pinned
GTX 1660 SUPER and about 5065 MiB free VRAM. No fallback, mock, retry, or
tuning was used.

Validator recovery for an existing Nano artifact was attempted once through
the production Validator Studio adapter. The service returned
`429 RESOURCE_EXHAUSTED` because prepayment credits were depleted. No
Validator score was fabricated and no repeated paid call was made.

The same production validity logic therefore gives Control `10/10`, Nano
`7/10`, and Remote `4/10`. Because the required branches are not all `10/10`,
Run 6 was not created. This is not a genuine `EXTERNAL_BLOCKED` decision under
the task rule (Control and Nano must first both be `10/10`), and no treatment
median or final quality decision is asserted. Status remains
`GW-P4-T1 = INELIGIBLE`, `GW-P4 = IN PROGRESS`; GW-P5 was not started.

Focused verification: identity-restoration **153 passed**; Action Composite/
regional **77 passed**; full repository suite **1117 passed / 76 unrelated
pre-existing Google Drive credential and DNA-fixture failures**;
`compileall` and `git diff --check` pass.

## 4.8 Validator credit-recovery resume preflight (2026-08-25)

The required smallest post-recovery readiness check used the existing
`BenchmarkValidatorAdapter` on the frozen Nano B01 output. Provider, rubric,
project, subject, and `samples=3` remained unchanged. The first live request
returned `429 RESOURCE_EXHAUSTED` with the provider message that prepayment
credits are depleted. No raw response was available to persist, no score was
accepted, and no second paid call was attempted. The immutable preflight
record is:

`artifacts/identity-restoration/benchmarks/validator-preflight-20260825T055001Z/result.json`

No Nano output was regenerated, no Remote output was rerun, and Run 6 was not
created. Existing pre-run validity remains Control `10/10`, Nano `7/10`, and
Remote `4/10`; therefore the missing Validator/Regional evidence was not
completed. Final status for this resume attempt is
`GW-P4-T1 = EXTERNAL_BLOCKED / INELIGIBLE`, `GW-P4 = IN PROGRESS`, and
`GW-P5 = NOT STARTED`. Human action is still required to restore Validator
project prepayment credits/quota.

## 4.9 Resume after Validator READY: final recovery gate (2026-08-25)

The unchanged production Validator configuration was ready: `gemini`,
`gemini-3.5-flash`, `samples=3`, `mock=false`, `fallback=false`. Runs 1–5
remain immutable. Reuse covered every Remote case B01–B10; B04/B10 were
reused from the previously completed recovery artifacts, so no Remote prompt
was submitted and Nano generation calls remained zero.

Production Regional evidence materialization reached:

| Branch | Regional evidence | Decision-valid |
|---|---:|---:|
| control | 10/10 | 10/10 |
| nano-banana-edit | 8/10 | 8/10 |
| comfyui-remote | 8/10 | 8/10 |

Twenty-one historical branch Validator records were reused. Five new complete
three-sample evaluations were recovered. Nano B02/B04 and Remote B06/B08
remain blocked by truncated Gemini JSON responses after controlled recovery
attempts; raw responses were persisted before parse. No score was fabricated.

The pre-run-6 gate failed at 10/10, 8/10, 8/10, so Run 6 was not created and
there is no official treatment decision. Partial Remote observations (N=8)
were median 91.335, mean 80.1775, min 0, max 94.55; these are not official
decision statistics. Final status: **GW-P4-T1 EXTERNAL_BLOCKED / INELIGIBLE**,
**GW-P4 IN PROGRESS**, **GW-P5 NOT STARTED**.
## 4.10 Paid-call guardrails and missing Validator recovery (2026-08-25)

This recovery task changed only transport safety and missing Validator evidence.
The frozen authority remains `gemini/gemini-3.5-flash`, `samples=3`, with the
same rubric, thresholds, and thinking configuration. `PaidCallGuard` blocks
pytest before network, requires `VALIDATOR_LIVE_ENABLED=true` for production,
and enforces a 12-call recovery budget with an append-only sanitized ledger.

Historical evidence was searched before every call. Face samples were already
complete for Nano B02, Nano B04, Remote B06, and Remote B08. New image samples
were required only for Nano B02=3, Nano B04=3, Remote B06=3, and Remote B08=1.
The ledger records 11 transport attempts: 10 parsed samples succeeded and one
initial `MAX_TOKENS` malformed response was retried once. Input tokens were
29,590; output tokens were 28,592; cached tokens were 0. No authoritative
pricing rate is stored, so estimated cost is not computed. No Nano image or
Remote GPU job was run.

Gemini structured JSON output uses the existing Face/Image DTO schemas and an
8192 output ceiling. Raw responses were persisted before parsing; the initial
malformed response remains retained as failure history, with no unresolved
malformed target after recovery. Batch mode was not used: the existing
per-sample transport does not expose an authority-preserving Batch interface,
and introducing one would alter the recovery boundary.

Offline production RegionalScoreGateway materialization covered all 30 existing
artifacts. Final evidence-valid counts are Control 10/10, Nano 10/10, and
Remote 10/10. Face QC values (B01–B10) are:

| Branch | Face QC |
|---|---|
| Control | 94.92, 94.18, 91.07, 90.60, 87.17, 85.78, 90.60, 95.80, 93.85, 65.58 |
| Nano | 96.35, 93.62, 90.60, 90.48, 88.65, 88.55, 90.60, 95.15, 93.65, 68.45 |
| Remote | 93.32, 94.55, 90.60, 90.82, 88.00, 85.30, 92.28, 95.40, 91.85, 0.00 |

Remote treatment Face QC is median 91.335, mean 82.212, min 0.00, max 95.40.
Regional gate pass counts are Control 2/10, Nano 0/10, Remote 2/10. This task
therefore opened the pre-run validity gate. The official Run 6 decision is
recorded below.

## 4.11 Run 6 — authoritative offline quality decision

Run ID: `benchmark-20260825T160000Z-gw-p4-t1`. The run contains exactly 30
terminal rows and exactly 30 decision-valid rows. Every row reuses an existing
output, Validator cache, Pixel evidence, and Regional evidence; no branch
executor was instantiated.

### Regional aggregate policy

The repository trace is `ActionCompositePipeline ->
RegionalScoreGateway -> RegionalGate`. `RegionalGate.evaluate()` applies the
existing thresholds per row: identity 90, eyes/brows 90, geometry 92, anatomy
90, outfit 90, environment 90, global composite 90, plus pixel preservation.
There is no pass-rate threshold and no taxonomy-specific global exception. The
benchmark summary's Treatment aggregate is `all(10 row-level Regional gates
passed)`, so one valid Treatment Regional failure makes the global Regional
gate fail.

Root classification: **RG2 — BENCHMARK_DECISION_MAPPING_BUG**. The aggregate
policy already existed and was used for Regional; the summary field named
`anatomyRegionalHealthy` incorrectly mirrored the complete Regional gate. The
mapping was corrected to report the Anatomy sub-gate separately; no threshold
or policy was changed.

### Treatment Regional audit

| Case | evidenceId | passed | failures |
|---|---|---:|---|
| B01 | `83d79dd7edc6bfe4e75494d42e7ce2c1743ab2f096397371bd01f1df2655a1e1` | true | — |
| B02 | `416cb5f0297bdb7e7b079ae315e124a4236e6e47687654bb74ed7b12ecbf5bc3` | false | global_composite_below_threshold |
| B03 | `bcdc221f327d1309f33facd54a257fc70c9809e08bcbaae6bc78e36552aa960b` | false | global_composite_below_threshold |
| B04 | `3f44ec6dad816624a0c904ebb4b0e8e393345f9775f3c380a2b7ea60c3fa91b5` | false | global_composite_below_threshold |
| B05 | `42e31c462a5877b872af6e4cc444a4fdc820861619d134299c2508c3a7e2a0a5` | false | identity_below_threshold; eyes_brows_below_threshold; global_composite_below_threshold |
| B06 | `93dd5cd8c7e9db9fe50de1194412cf94d8148c80e5d65e130df8491ce14c3ea2` | false | identity_below_threshold; eyes_brows_below_threshold |
| B07 | `818ac9652143f455d69b9d66b6f2160a590e79707f22452ed5639a5e5609e326` | false | global_composite_below_threshold |
| B08 | `4f291ff57c00ce37ff438af4db644425e1d47a222309c104263909410dcd5ee3` | true | — |
| B09 | `8077c5ed1deac1ffe44e1b39778b0db47646dc7a61af4fcf42f2b286870aff8e` | false | global_composite_below_threshold |
| B10 | `3b256d6ea3bc4a839aa77c623344c6b764b74f4114d4a1d57a08b48df6d0911e` | false | identity_below_threshold; eyes_brows_below_threshold; geometry_below_threshold; global_composite_below_threshold |

Treatment Regional result: **2/10 row PASS, 8/10 row FAIL, aggregate FAIL**.
Anatomy result: **10/10 PASS**; no `anatomy_below_threshold` or
`anatomy_unvalidated` failure exists. Control is 2/10 Regional PASS and Nano
is 0/10; these are comparison diagnostics and are not added to the Treatment
hard-gate rule.

### Score integrity and B10 audit

All 30 rows have matching output SHA, three-sample Validator cache, final
Face QC, production Regional evidence ID, Pixel evidence, and reuse lineage.
No zero was inserted for a missing/error sample. Remote B10's `0.00` is
classification **A — legitimate Face QC from three valid samples**. Its cache
contains `samples=3`, `dna_match_score=0.0`, a triggered face binary gate for
the corrupted face, and the same output SHA as the Regional evidence. It is
included in all statistics.

### Run 6 statistics and hard gates

| Branch | Face QC B01–B10 | median | mean | min | max |
|---|---|---:|---:|---:|---:|
| Control | 94.92, 94.18, 91.07, 90.60, 87.17, 85.78, 90.60, 95.80, 93.85, 65.58 | 90.835 | 88.955 | 65.58 | 95.80 |
| Nano | 96.35, 93.62, 90.60, 90.48, 88.65, 88.55, 90.60, 95.15, 93.65, 68.45 | 90.60 | 89.610 | 68.45 | 96.35 |
| Remote (Treatment) | 93.32, 94.55, 90.60, 90.82, 88.00, 85.30, 92.28, 95.40, 91.85, 0.00 | 91.335 | 82.212 | 0.00 | 95.40 |

| Hard gate | Result |
|---|---|
| Treatment median Face QC >= 90 | PASS — 91.335 |
| Treatment Anatomy | PASS — 10/10 |
| Treatment Regional | FAIL — 2/10 row PASS; all 10 required |
| Treatment Pixel Preservation | PASS — 10/10 |
| Treatment Lineage | PASS — 10/10; workflow/A2/base/output/evidence lineage present |
| fallback/mock/cherry-picking | PASS — none detected; reuse-only |

Official decision: **QUALITY_FAIL**. GW-P4-T1 is FAIL and GW-P4 remains IN
PROGRESS / QUALITY GATE FAILED. The smallest next tuning target is the frozen
Remote workflow's `global_composite` gate for B02/B03/B04/B05/B07/B08/B09;
B06 and B10 additionally require identity/eyes work. No tuning was performed
in this task.

Cost: new Nano generation calls `0`; new Remote GPU jobs `0`; new Validator
calls `0`; paid calls during tests `0`. `validatorEvidenceComplete=true` and
`missingValidatorSamples=0`.

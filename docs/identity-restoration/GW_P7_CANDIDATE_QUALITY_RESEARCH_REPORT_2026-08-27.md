# GW-P7 Candidate Quality Research Report

**Date:** 2026-08-27  
**Candidate:** `comfyui-remote-face_restore_win_sd15_ipadapter_v2`  
**Decision:** `REJECTED_QUALITY` — no production promotion  
**Purpose:** preserve the completed engineering evidence and isolate the
measured output-quality problem for a future, separately authorized research
and remediation effort.

## 1. Executive conclusion

The Windows GPU worker, remote ComfyUI integration, benchmark evidence chain,
and physical smoke path are operating correctly enough to establish a valid
candidate evaluation. The candidate is not production-ready because its output
does not consistently satisfy the existing regional quality contract.

This is a quality result, not a runtime availability result:

- The authoritative post-remediation benchmark has **30/30 valid,
  decision-eligible rows**: 8 pass and 22 `VALID_QUALITY_FAIL`.
- Every blocking row is classified
  `RC1_TRUE_OUTPUT_QUALITY_FAILURE`. No concrete authority-mapping, QC
  implementation, stale/corrupt-evidence, or benchmark-contract defect was
  found.
- The candidate under consideration, `comfyui-remote`, has **7 failed cases
  out of 10**. Its median Face-QC measurement is **91.335**, above the median
  criterion of 90, but the regional gate is an all-required-dimensions gate;
  a good aggregate face measurement does not offset a failed regional
  dimension.
- A later physical remote smoke passed on HARRY-ROG / GTX 1660 SUPER. That
  proves the frozen remote worker can execute one bounded production-candidate
  request. It does not supersede the 10-case regional benchmark.

Therefore the correct current production state is
`REJECTED_QUALITY`, with promotion `BLOCKED` and human approval
`NOT_REQUESTED`.

## 2. What has been completed successfully

### 2.1 Runtime and infrastructure

| Capability | Verified result |
|---|---|
| Physical worker | HARRY-ROG GTX 1660 SUPER completed the authorized remote smoke. |
| Worker binding | Human verification established a single logical ComfyUI worker chain, bound only to `127.0.0.1:8188`. |
| Frozen runtime flags | `--listen 127.0.0.1 --port 8188 --lowvram --fp32-vae` verified. |
| VRAM recovery | Free VRAM increased from 1,734 MiB to approximately 5,132 MiB; preflight reached `READY`. |
| Physical smoke | `PASS`; smoke manifest SHA-256 `0b8b09647b32573df1db61e67f454422819920b342c6a036e784da4bded20c2d`. |
| Smoke output | SHA-256 `919e20a83aedb246f1124e8d919eab2a4c10d7ef6a5faba00982119508fa7be9`. |
| Remote workflow | Frozen workflow SHA-256 verified: `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`. |
| A2 authority | Frozen A2 SHA-256 verified: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`. |

The smoke proves a working execution path. It is deliberately only a smoke;
it is not a representative replacement for the locked benchmark population.

### 2.2 Benchmark, QC, and evidence integrity

| Item | Verified result |
|---|---|
| Benchmark population | 30 planned, 30 terminal, 30 valid and decision-eligible rows. |
| Quality result | 8 `VALID_QUALITY_PASS`; 22 `VALID_QUALITY_FAIL`. |
| Failure source | 22 RC1 true output-quality failures; RC2–RC5 each equal 0. |
| Authority validity | No authority failure rows; cached evidence is deterministic. |
| Execution / validator validity | No infrastructure, evidence-pipeline, or validator failure rows in the decisive post-remediation report. |
| Anatomy preservation | `PASS` / healthy. |
| Pixel preservation | `PASS` at the aggregate benchmark level. |
| Regional gate | `FAIL`. |
| Candidate registry | Exactly one candidate entry, recorded as `REJECTED_QUALITY` / `BLOCKED` / `NOT_REQUESTED`. |

The authoritative post-remediation report is
[`post_remediation_report.json`](../../artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/post_remediation_report.json)
with SHA-256
`de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`.

### 2.3 Lineage repair without altering history

The immutable T2 regional classification had one transposed source-report SHA
field:

| Field | Value |
|---|---|
| Correct T1 report bytes / T1 manifest / registry | `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6` |
| Incorrect field in immutable T2 classification | `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99cf4bf37632ee90b14d6` |

This was a `METADATA_REFERENCE_DEFECT`, not a quality or validator defect.
The original T2 bytes remain untouched. A new immutable correction artifact
was created at
[`lineage_correction.json`](../../artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json)
with SHA-256
`15d2afde5310e1cbcb4c6317f5eb8d6335d9deeb0a6641e59d33203fa8986834`.

The correction explicitly proves that source images, QC observations, row
decisions, scores, failure count, root cause, and candidate decision are all
unchanged. The evidence chain is now `PASS`.

## 3. What has not been achieved

### 3.1 Production acceptance

The candidate has not met the locked regional quality gate and therefore has
not been promoted. This is intentional fail-closed behavior.

- `REGIONAL_GATE = FAIL`
- `PRODUCTION_CANDIDATE = REJECTED_QUALITY`
- `PRODUCTION_PROMOTIONS = 0`
- `HUMAN_APPROVAL = NOT_REQUESTED`

No production default, workflow, model, A2 authority, QC threshold, or
architecture was changed to obtain a passing result.

### 3.2 Quality consistency across the benchmark

The remote candidate passes only B01, B04, and B08. It fails B02, B03, B05,
B06, B07, B09, and B10. Its image outputs thus have not shown the required
consistency across the locked case distribution.

The whole benchmark also shows failures in the two comparison branches:
`control` fails 7/10 and `nano-banana-edit` fails 8/10. This reinforces that
the decisive conclusion is evidence-backed quality failure; it does **not**
by itself establish that all three branches share one technical root cause.

## 4. Exact measured quality failure pattern

### 4.1 Aggregate failure dimensions

The T2 classification records 22 blocking rows. A row may fail more than one
gate, so gate counts are not a sum of row counts.

| Failing gate / dimension | Count | Locked requirement |
|---|---:|---|
| Global composite | 18 | score >= 90 |
| Face identity | 9 | score >= 90 |
| Eyes / brows | 9 | score >= 90 |
| Pixel preservation | 8 | PASS required |
| Geometry | 2 | score >= 92 |
| Anatomy | 0 | no blocking anatomy failure |
| Scenario authority / other | 0 | no blocking failure |

The treatment (remote) median Face-QC of 91.335 is not contradictory to the
rejection. It describes one aggregate face-QC statistic. The regional gate
also requires valid identity, eyes/brows, geometry, global composition, and
pixel-preservation results for each case.

### 4.2 Remote candidate scorecard

All rows below have valid cached evidence. `PASS` means no regional-gate
failure for that case; it does not loosen any threshold.

| Case | Identity | Eyes/brows | Geometry | Global composite | Pixel | Result / observed blocking gate |
|---|---:|---:|---:|---:|---|---|
| B01 | 93.32 | 91.33 | 98.36 | 94.29 | PASS | PASS |
| B02 | 94.55 | 94.00 | 97.34 | 89.06 | PASS | FAIL: global composite |
| B03 | 90.60 | 90.00 | 97.87 | 40.00 | PASS | FAIL: global composite |
| B04 | 90.82 | 90.00 | 96.72 | 93.91 | PASS | PASS |
| B05 | 88.00 | 86.67 | 96.86 | 83.96 | PASS | FAIL: identity, eyes/brows, global composite |
| B06 | 85.30 | 85.00 | 97.76 | 90.70 | PASS | FAIL: identity, eyes/brows |
| B07 | 92.28 | 92.67 | 99.03 | 87.92 | PASS | FAIL: global composite |
| B08 | 95.40 | 96.00 | 95.44 | 92.18 | PASS | PASS |
| B09 | 91.85 | 90.00 | 96.11 | 89.34 | PASS | FAIL: global composite |
| B10 | 0.00 | 6.67 | 77.52 | 73.78 | PASS | FAIL: identity, eyes/brows, geometry, global composite |

This table isolates the current candidate’s primary weakness: **global
composition/overall image quality fails in 6 of its 7 failed cases**, while
identity and eyes/brows fail together in B05, B06, and B10. Geometry is
generally strong but fails catastrophically in B10.

### 4.3 Distribution by case and backend

| Case | Blocking rows | Backends that failed |
|---|---:|---|
| B01 | 1 | nano-banana-edit |
| B02 | 3 | control, nano-banana-edit, comfyui-remote |
| B03 | 2 | control, comfyui-remote |
| B04 | 0 | none |
| B05 | 3 | control, nano-banana-edit, comfyui-remote |
| B06 | 3 | control, nano-banana-edit, comfyui-remote |
| B07 | 2 | nano-banana-edit, comfyui-remote |
| B08 | 2 | control, nano-banana-edit |
| B09 | 3 | control, nano-banana-edit, comfyui-remote |
| B10 | 3 | control, nano-banana-edit, comfyui-remote |

The pattern is concentrated rather than random. B02, B05, B06, B09, and B10
fail on every evaluated backend; B04 passes on every backend. These are useful
research controls, but they are not sufficient proof of a common cause without
a separate artifact-level study.

## 5. Why the candidate’s output quality remains low

### 5.1 Proven conclusions

1. **The output itself is the blocking artifact.** Each decisive failure is
   `RC1_TRUE_OUTPUT_QUALITY_FAILURE`; evidence and validator validity were
   present for every decisive row.
2. **The main measurable weakness is regional image quality, not worker
   operability.** The physical smoke passed and the benchmark's remote rows
   record `vramPeakMb=5065`, yet seven remote outputs still failed quality
   gates.
3. **Global composite quality is the dominant failure mode.** It fails in
   B02, B03, B05, B07, B09, and B10. B03 is especially severe at 40.00 despite
   identity, eyes/brows, and geometry meeting their thresholds.
4. **Identity detail is not robust in the difficult cases.** B05 and B06 fall
   below both identity and eyes/brows thresholds; B10 is far below both.
5. **B10 is the clearest compound failure.** Cached validator evidence for the
   remote output describes a full-body/distant shot where facial details are
   difficult to resolve, a hairstyle mismatch, and a resulting low identity,
   eyes/brows, geometry, and global-composite score. This is direct evidence
   of poor quality for that output, not an inference from system health.
6. **Pixel preservation is not the remote candidate’s blocker.** All ten
   remote rows have `PASS` pixel preservation. The aggregate benchmark’s eight
   pixel failures belong to other backend rows, principally
   `nano-banana-edit`.
7. **Anatomy preservation is not the current blocker.** Aggregate anatomy is
   healthy and no failed row was classified as an anatomy failure.

### 5.2 Evidence-backed interpretations to investigate (not yet proven)

The following are research hypotheses, not implemented changes and not final
root-cause findings:

| Hypothesis | Why it is worth testing | Evidence needed before accepting it |
|---|---|---|
| Face crop / scale is inadequate for some cases | B10’s distant, full-body composition makes facial DNA features hard to evaluate; B10 has the worst remote identity and eyes/brows scores. | Compare source crop, mask, IP-Adapter conditioning, generated crop, and face bounding boxes per case without changing the candidate. |
| The remote restoration is insufficiently identity-preserving in difficult poses | B05 and B06 fail both identity and eyes/brows while geometry remains high. | Per-case landmark, reference-conditioning, and raw validator-evidence review against passing controls B01/B04/B08. |
| Overall composition is degraded independently of face identity | B03 has acceptable identity/eyes/geometry but a global score of 40.00; B02/B07/B09 likewise fail global composite with acceptable face/geometry measurements. | Inspect image-validator category evidence and visual artifacts for B02/B03/B07/B09 against their source frames and passing controls. |
| Some dataset cases are intrinsically harder | B02, B05, B06, B09, and B10 fail all backends, whereas B04 passes all. | Contract-preserving difficulty analysis using the locked source frames and regional evidence; do not relabel or remove cases. |
| Frozen workflow capability is insufficient for the case mix | Valid remote runtime and locked workflow still yield 7/10 regional failures. | A separately authorized candidate comparison with a new, versioned workflow/model/configuration and a fresh benchmark; never retcon this candidate’s result. |

No hypothesis above authorizes a quality-tuning change. The current evidence
only proves rejection of the frozen candidate, not which new candidate will
pass.

## 6. Recommended research sequence for a future authorized task

1. **Perform an offline forensic review first.** For B02, B03, B05, B06, B07,
   B09, and B10, inspect the immutable source frame, mask, restored crop,
   composite, regional evidence, and validator explanations. Use B01, B04,
   and B08 as passing controls. Record findings without mutating evidence.
2. **Split failures by mechanism.** Keep at least three buckets: global-only
   (B02/B03/B07/B09), identity-detail (B05/B06), and compound pose/crop/
   composition (B10). This prevents an apparent average improvement from
   hiding a persistent failure mode.
3. **Define a new candidate separately.** Any workflow, conditioning, crop,
   mask, model, or prompt change must receive a new candidate ID and immutable
   evidence directory. Do not modify the frozen workflow or reuse this
   candidate’s quality result as if it belonged to a new configuration.
4. **Pre-register the comparison.** Keep the existing dataset, QC thresholds,
   authorities, seed policy, and regional gate unless governance explicitly
   changes the benchmark contract. Record the intended change and expected
   failure mechanism before running work.
5. **Run preflight and a bounded physical smoke for the new candidate, then
   evaluate the full locked benchmark.** A passing smoke is necessary for
   runtime confidence but is not sufficient for production acceptance.
6. **Promote only after all quality and evidence gates pass.** This requires a
   new evidence-backed `PASS` decision and the existing human approval path.

## 7. Current safety and operational state

| Control | Current state |
|---|---|
| AI Studio default | Environment-controlled; version-controlled fallback is mock; remote adapter is opt-in. |
| VenHo OS default restorer | Explicit `none`; GPU use requires deliberate selection. |
| Promotion | Human-controlled; registry blocks this candidate. |
| GPU work in final closure | 0 jobs. |
| Provider calls in final closure | 0. |
| Production promotions in final closure | 0. |
| Historical evidence | Preserved; T1, T2, and physical-smoke artifacts were not overwritten. |

## 8. Evidence index

- [Production registry](../../PRODUCTION_REGISTRY.md)
- [Task status](../../task_status.md)
- [Task memory](../../task_memory.md)
- [Authoritative T1 post-remediation report](../../artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/post_remediation_report.json)
- [T1 source rows](../../artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/rows.jsonl)
- [Immutable T2 regional classification](../../artifacts/identity-restoration/benchmarks/gw-p7-t2-regional-classification-20260827/classification.json)
- [T3-R1 lineage correction](../../artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json)
- [Physical smoke manifest](../../evidence/gw-p4-t0-5-2d-20260827T015106Z-88f18024/smoke_manifest.json)

## 9. Final status

The system is technically operational and the evidence chain is valid. The
frozen remote restoration candidate is rejected strictly because it does not
meet the measured regional quality bar across the required benchmark cases.
No production promotion has been performed.

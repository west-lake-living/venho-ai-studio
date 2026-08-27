# VENHO Production Registry

Tier-1 internal registry required by the GPU identity-restoration production
gate. Entries are evidence references only; `OFFICIAL` and
`PRODUCTION_APPROVED` are intentionally not valid states.

## Entry schema

Each entry records `candidate_id`, `backend`, frozen workflow and A2 hashes,
source benchmark, post-remediation evidence, physical-smoke evidence, gate
state, promotion state, and human approval state. Allowed gate states include
`PASS`, `QUALITY_FAIL`, `MISSING_EVIDENCE`, `BLOCKED`, and
`REJECTED_QUALITY`. Allowed promotion states are `VALIDATION_PENDING`,
`BLOCKED`, and `ELIGIBLE_FOR_HUMAN_REVIEW`.

## Entries

### comfyui-remote / face_restore_win_sd15_ipadapter_v2

- `candidate_id`: `comfyui-remote-face_restore_win_sd15_ipadapter_v2`
- `backend`: `comfyui-remote`
- `workflow_id`: `face_restore_win_sd15_ipadapter_v2`
- `workflow_version`: `2.1`
- `workflow_sha256`: `1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58`
- `a2_sha256`: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`
- `benchmark_source`: `benchmark-20260825T160000Z-gw-p4-t1`
- `historical_decision`: `QUALITY_FAIL`
- `post_remediation_evidence`: `artifacts/identity-restoration/benchmarks/gw-p7-t1-post-remediation-20260826/post_remediation_report.json`
- `post_remediation_report_sha256`: `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`
- `physical_smoke_state`: `PASS`
- `physical_smoke_evidence`: `evidence/gw-p4-t0-5-2d-20260827T015106Z-88f18024/smoke_manifest.json`
- `physical_smoke_evidence_sha256`: `0b8b09647b32573df1db61e67f454422819920b342c6a036e784da4bded20c2d`
- `physical_smoke_output_sha256`: `919e20a83aedb246f1124e8d919eab2a4c10d7ef6a5faba00982119508fa7be9`
- `regional_classification_evidence`: `artifacts/identity-restoration/benchmarks/gw-p7-t2-regional-classification-20260827/classification.json`
- `regional_classification_sha256`: `d2379e39c562e742c47e9546210bc302bcdae81ce17764aea7f7b987334a8f5c`
- `t2_lineage_metadata_defect`: `sourcePostRemediationReportSha256` in the
  immutable T2 classification was recorded as
  `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99cf4bf37632ee90b14d6`; T1
  report bytes, the T1 hash manifest, and this registry agree on
  `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`.
- `t3_r1_lineage_correction`: `artifacts/identity-restoration/benchmarks/gw-p7-t3-r1-lineage-correction-20260827T021930Z/lineage_correction.json`
- `t3_r1_lineage_correction_sha256`: `15d2afde5310e1cbcb4c6317f5eb8d6335d9deeb0a6641e59d33203fa8986834`
- `t3_r1_correct_authoritative_t1_sha256`: `de8f6d2e947130e5c7bf3b4150c263e0566c47ca54e99fc4bf37632ee90b14d6`
- `regional_gate`: `FAIL`
- `final_candidate_state`: `REJECTED_QUALITY`
- `gate_state`: `REJECTED_QUALITY`
- `promotion_state`: `BLOCKED`
- `human_approval_state`: `NOT_REQUESTED`
- `notes`: `GW-P4-R1 authority-only replay and GW-P7-T2 classification. All 22 rows are deterministic VALID_QUALITY_FAIL observations with RC1; original images, workflow, seed, and A2 lineage preserved. Physical smoke passed; no promotion or human approval requested.`

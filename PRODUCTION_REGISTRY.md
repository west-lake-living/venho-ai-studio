# VENHO Production Registry

Tier-1 internal registry required by the GPU identity-restoration production
gate. Entries are evidence references only; `OFFICIAL` and
`PRODUCTION_APPROVED` are intentionally not valid T1 states.

## Entry schema

Each entry records `candidate_id`, `backend`, frozen workflow and A2 hashes,
source benchmark, post-remediation evidence, gate state, promotion state, and
human approval state. Allowed T1 gate states are `PASS`, `QUALITY_FAIL`,
`MISSING_EVIDENCE`, and `BLOCKED`. Allowed promotion states are
`VALIDATION_PENDING`, `BLOCKED`, and `ELIGIBLE_FOR_HUMAN_REVIEW`.

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
- `gate_state`: `QUALITY_FAIL`
- `promotion_state`: `BLOCKED`
- `human_approval_state`: `NOT_REQUESTED`
- `notes`: `GW-P4-R1 authority-only replay; original images, workflow, seed, and A2 lineage preserved. No provider or GPU calls.`


# GW-P4-R1-T4 — Benchmark authority validation and remediation closure

## 1. Executive decision

**REMEDIATION_PASS.** `GW-P4-R1 = CLOSED / PASS`. The historical `GW-P4 = CLOSED / QUALITY FAIL` is preserved. Corrected, explicit authority supersedes the B03/B04 cause of that historical failure; it does not rewrite the historical run.

## 2. Evidence inspected

Read `task_status.md`, `task_memory.md`, the B01–B10 benchmark contract, the action authority profile, T1/T2/T3 reports and JSON, `benchmark_orchestration.py`, `image_validator.py`, `RegionalScoreGateway`, `RegionalGate`, T1 rows, and B03/B04 Regional/Face-QC/Pixel Lock artifacts.

## 3. Benchmark fixture authority matrix

| Case | Scenario / shot | Mode | Expected = resolved authority | Fallback | Resolution | Existing-artifact result |
|---|---|---|---|---|---|---|
| B01 | Close-up Front | static | canonical default | yes | PASS | NOT_APPLICABLE |
| B02 | Half-body | static | canonical default | yes | PASS | NOT_APPLICABLE |
| B03 | Full-body Standing | action | `action_full_body@1.0` | no | PASS | REPLAY_PASS |
| B04 | Running Front 3/4 | action | `action_full_body@1.0` | no | PASS | REPLAY_PASS |
| B05 | Running Side | action | canonical default; no explicit mapping | yes | PASS | NOT_APPLICABLE |
| B06 | Walking | action | canonical default; no explicit mapping | yes | PASS | NOT_APPLICABLE |
| B07 | Sitting | action | canonical default; no explicit mapping | yes | PASS | NOT_APPLICABLE |
| B08 | Hair Motion | action | canonical default; no explicit mapping | yes | PASS | NOT_APPLICABLE |
| B09 | West Lake | static | canonical default | yes | PASS | NOT_APPLICABLE |
| B10 | Ven Ho Hotel Interior | static | canonical default | yes | PASS | NOT_APPLICABLE |

All B01–B10 manifest fixtures are present. `NOT_APPLICABLE` means its authority is unchanged, so no re-score is authorized or needed; it does not fabricate a replacement for its historical artifact.

## 4. Authority resolution validation

The executor reads only explicit `identityRestorationAuthority` mappings. B03 and B04 resolve `action_full_body@1.0`; no taxonomy-derived mapping exists. Missing mappings deliberately resolve to canonical Linh An DNA. An explicitly named profile without a matching authority file now raises an error, so it cannot silently acquire action exclusions.

## 5. Scope regression validation

Only `shot_distance` and `hairstyle` outside the face mask are removed for B03/B04 Image-QC scoring. Tests prove that identity and face-geometry mismatches still score below 90, and a non-action/default case retains a `shot_distance` mismatch. Regional thresholds and Pixel Lock behavior are unchanged.

## 6. Existing-artifact replay

The T1 B01–B10 rows were read as historical baseline evidence. Their old scores are not reclassified by this remediation. Only B03/B04 have complete, affected raw Image-QC observations and are deterministically replayable under the new authority; all other fixtures are `NOT_APPLICABLE` rather than invented replays.

## 7. B03/B04 reproducibility

B03 raw B03 C1 evidence replays to **97.51 / APPROVE** and Regional PASS. B04 raw B04 C1 evidence replays to **94.14 / APPROVE** and Regional PASS. Both preserve Face-QC (`90.98`), geometry (`97.80` / `97.08`), and Pixel Lock PASS. The focused test reconstructs each report from its saved raw observation and evaluates the unchanged `RegionalGate`.

## 8. Default DNA integrity

Canonical `VENHO_HOTEL_LINH_AN_DNA.json` remains SHA-256 `71f839dff776ec6d6d085c5a1ab928295af8c32a9699f7929d78b04807ec0075`. The profile holds only scenario gate ownership; it neither forks nor edits character DNA.

## 9. Remaining true quality failures

None for the remediation target B03/B04. B03 `hair_length` partial and B04 `earring_type` mismatch remain observed and scored; neither fails the unchanged final gate. Historical baseline outcomes on unmapped fixtures remain historical evidence, not an authority regression or a new R1 tuning target.

## 10. Tuning candidate disposition

`R1-C1` (steps 28), `R1-C2` (FaceID v2 1.15), and `R1-C3` (LoRA 0.75) are **CANCELLED / NOT REQUIRED**: the affected B03/B04 final gates pass without a face-scope failure.

## 11. Remediation closure decision

**REMEDIATION_PASS.** Authority resolves deterministically, B03/B04 reproduce exactly, non-action fixtures do not inherit exclusions, face-scope violations still fail, and no B03/B04 quality tuning is justified. `GW-P4-R1 = CLOSED / PASS`; `GW-P4` stays historically closed/quality-fail.

## 12. Exact next task

`GW-P5-T0 — Hardening readiness / entry-gate review`

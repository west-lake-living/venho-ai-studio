# GW-P4-R1-T3 — Authority Completion & Offline Authority Replay

## 1. Executive decision

`AUTHORITY_CORRECTED_QUALITY_PASS`.

## 2. Previous authority defect

B03/B04 Image-QC ran against default Linh An DNA without a scenario authority. It penalized `shot_distance` and `hairstyle`, despite the frozen Stage B mask being face-only.

## 3. Human-approved scope

Stage B retains face identity, face geometry, eyes, brows, nose, mouth/lips, jaw/chin, skin/face texture, and face boundary/blending. For the approved action/full-body profile it excludes `shot_distance` and non-face-mask `hairstyle` from the Identity Restoration gate.

## 4. Implementation chosen

`linh_an.action_full_body.authority.yaml` is a versioned, data-driven authority profile. Image-QC applies its `exclude_observation_keys` before scoring. The benchmark executor forwards only an explicit case mapping; it never infers a profile.

## 5. Authority precedence

Explicit `identityRestorationAuthority.scenarioProfileId` on a benchmark case overrides default DNA ownership only for profile-excluded keys. Default Linh An DNA remains active for every retained field.

## 6. B03 mapping

`B03 -> action_full_body` (profile version `1.0`).

## 7. B04 mapping

`B04 -> action_full_body` (profile version `1.0`).

## 8. Regression tests

The focused suite proves explicit B03/B04 mapping, exclusion of `shot_distance`, exclusion of out-of-mask `hairstyle`, enforcement of a mismatched face field, and unchanged behavior for an unmapped scenario.

## 9. Offline replay B03

Original Image-QC was `86.61` (`global_composite`), with `hair_length` partial, `shot_distance` mismatch, and `hairstyle` mismatch. Replay used the saved parsed Image-QC observation and the same scoring configuration; it excluded only `shot_distance` and `hairstyle`.

Replay Image-QC is `97.51` / `APPROVE`; retained `hair_length` remains partial. Face-QC is `90.98` / APPROVE, Regional identity/eyes/geometry are `90.98/90.00/97.80`, Pixel Lock is PASS (`0` protected pixels changed), and all RegionalGate thresholds pass after replacing only `global_composite` with the replay score.

## 10. Offline replay B04

Original Image-QC was `83.76` (`global_composite`), with `earring_type`, `shot_distance`, and `hairstyle` mismatches. Replay used the saved parsed Image-QC observation and the same scoring configuration; it excluded only `shot_distance` and `hairstyle`.

Replay Image-QC is `94.14` / `APPROVE`; `earring_type` remains evaluated and mismatched. Face-QC is `90.98` / APPROVE, Regional identity/eyes/geometry are `90.98/90.00/97.08`, Pixel Lock is PASS (`0` protected pixels changed), and all RegionalGate thresholds pass after replacing only `global_composite` with the replay score.

## 11. Remaining true quality failures

None at the Identity Restoration gate for B03/B04. The retained diagnostics are B03 `hair_length` partial and B04 `earring_type` mismatch; neither violates a gate threshold. Scores changed because authority ownership changed, not because either image improved.

## 12. Final decision

`AUTHORITY_CORRECTED_QUALITY_PASS`. No GPU tuning required.

## 13. Exact next task

`GW-P4-R1-T4 — Validate corrected authority across benchmark fixtures / determine GW-P4 remediation closure`.

# Candidate v3 Quality Remediation R1 — R1-P1 Boundary

**Status:** `CLOSED / PASS`

**Scope:** boundary/composite remediation only. FACE_LOCAL and SCENARIO_GLOBAL are unchanged and remain outside this task.

## Baseline

The existing nine Candidate v3 outputs were evaluated offline without regeneration, provider calls, GPU calls, threshold changes, validator bypass, or case exclusion. The current validator returned `FAIL` for all nine BOUNDARY rows because `maxChannelSeamDelta` exceeded the locked pass threshold of `32`:

- minimum: `106.0`
- maximum: `200.0` (`B05`)
- mean: `169.000000`
- median: `177.0`
- nearest to pass: `B01` at `106.0`

A deterministic no-op experiment, evaluating the source base frame as both before and after, also exceeded `32` for every case. This isolates the dominant defect: the validator samples a natural high-contrast source edge, while the inverse composite has no local continuity postprocess to make the editable side agree with the immutable side. The current Phase 7 benchmark also supplies a binary mask as the feather mask; inverse interpolation therefore produces an edge transition, not a sufficient boundary continuation.

## Remediation

`apply_boundary_color_continuity` is now executed after inverse compositing and before pixel-lock evidence is emitted. It:

1. uses the existing locked 3px inner/outer seam rings and deterministic nearest-pair mapping;
2. seeds only editable inner-ring pixels from their immutable outer source samples;
3. applies a fixed deterministic 3x3 Gaussian softening;
4. bounds the resulting editable pixels by the existing policy pass envelope (`maxChannelSeamDelta <= 32`);
5. never writes outside the authoritative full-canvas editable mask.

The validator remains unchanged and is run on every derived output.

## Post-remediation

The same nine existing outputs, transformed offline by the production composite helper, produced `BOUNDARY PASS` for all nine cases. Pixel lock passed for all nine; `meanSeamDelta` and `localTextureDiscontinuity` also passed for all nine.

Detailed per-case evidence is in `per-sample-results.json`, each `B01`–`B09/BOUNDARY.json`, and `remediation-metrics.json`. The prior Phase 7 and R1-P0 evidence directories were not overwritten.

## Scope and locks

- FACE_LOCAL: unchanged.
- SCENARIO_GLOBAL: unchanged.
- Canonical transform, route policy, authority profiles, IdentityPack, v2/v2.1 paths: unchanged.
- Threshold: unchanged (`32`).
- Validator bypass: none.
- GPU/provider calls: `0`.
- Production feature flag: `OFF`; production remains ineligible.

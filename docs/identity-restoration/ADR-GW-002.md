# ADR-GW-002 — Bounded context and external QC authority

- Status: Accepted; architecture locked
- Decision IDs: GW-D2, GW-D12
- v2.1 amendment: no QC threshold change; the existing ≥90 authority remains external.

## Context

Identity Restoration belongs to the existing AI Studio architecture. Creating a new M-module or silently changing the Face QC threshold would create governance and contract drift.

## Decision

Keep Identity Restoration as the `identity_restoration/` bounded context inside `venho-ai-studio`; do not create M11 or another module. Face QC ≥90 remains owned by Character Bible 07F and its existing validator contract, not by this architecture plan.

## Rationale

The boundary avoids duplicate ownership and prevents a benchmark result from becoming an unauthorized policy change.

## Consequences

Implementation must reuse existing validator/QC authority. Any threshold change requires a separate approved Change Request to 07F.

## Rejected alternatives

- Creating a new M-module for GPU restoration.
- Lowering or editing the ≥90 threshold in the restoration code or plan.
- Treating the Nano Banana ≈88.x baseline as an acceptance threshold.

## Rollback / reversibility

Remove only future bounded-context implementation behind its existing contract; module ownership and QC policy remain unchanged.

## References

v2.0 §2.1 (GW-D2, GW-D12), §12, Character Bible 07F, v2.1 patch QC4 exclusions and Nano Banana baseline.

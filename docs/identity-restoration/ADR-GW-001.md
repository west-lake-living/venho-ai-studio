# ADR-GW-001 — Restorer port and adapter registry

- Status: Accepted; architecture locked
- Decision IDs: GW-D1, GW-D11
- v2.1 amendment: retain `comfyui-local` as the current local rollback/fallback path; Nano Banana remains a comparison adapter, not the production winner.

## Context

Identity restoration must be able to move compute hosts without changing domain behavior. The existing pipeline already has local behavior that is protected by the GW-P0 Golden Master, while future execution may use Windows ComfyUI, Nano Banana, or a mock.

## Decision

Define one `IdentityRestorerPort` and select implementations through a restorer registry. Windows ComfyUI is an adapter behind the port, not a system layer. The registry supports `comfyui-local`, `comfyui-remote`, `nano-banana-edit`, and `mock` where implemented. Domain commands and contracts remain independent of the selected adapter.

## Rationale

This preserves substitution, keeps the local behavior reversible, and prevents a second identity-restoration pipeline.

## Consequences

Adapters must honor the same crop, mask, pixel-lock, transform, artifact, and QC contracts. Selection is explicit and observable. The local adapter remains the immediate rollback target.

## Rejected alternatives

- Calling ComfyUI directly from domain or UI code.
- Making Nano Banana the implicit production winner.
- Duplicating the pipeline per provider.

## Rollback / reversibility

Set the restorer selection back to `comfyui-local` and retain the frozen Golden Master. No domain change is required.

## References

`VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md` §2.1, §6, §13; `VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` GW-P0 Golden Master and v2.1 authority notes.

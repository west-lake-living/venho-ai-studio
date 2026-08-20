# ADR-GW-003 — Python image plane and TypeScript control plane

- Status: Accepted; architecture locked
- Decision IDs: GW-D3, GW-D4
- v2.1 amendment: preserve the verified two-repository boundary; no direct ComfyUI access is added to `venho-os`.

## Context

Image operations and durable product orchestration have different ownership. The existing `venho-os` owns jobs, manifests, artifacts, cost, UI, and SSE, while Python owns image operations and the ComfyUI client.

## Decision

Python is the image plane: crop, mask, composite, pixel-lock, QC, and ComfyUI client. TypeScript is the control plane: job store, manifest, artifact store, cost ledger, UI, and SSE. Communication is through the existing subprocess plus JSON contract. `venho-os` never calls ComfyUI directly.

## Rationale

This prevents a second job store and keeps infrastructure dependencies out of the control plane.

## Consequences

Changes must stay on the owning side of the boundary. Boundary grep tests remain architectural guardrails.

## Rejected alternatives

- A second identity-restoration implementation in TypeScript.
- Direct `fetch` from `venho-os` to ComfyUI.
- Moving durable job/manifest ownership into Python.

## Rollback / reversibility

Revert only the bridge change while preserving the existing subprocess contract and Golden Master. No direct network path is introduced as a rollback.

## References

v2.0 §2.1 (GW-D3, GW-D4), §3, §5, §12; v2.1 patch boundary confirmation and no-direct-ComfyUI guard.

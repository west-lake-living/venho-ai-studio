# ADR-GW-004 — SD1.5 + IPAdapter FaceID POC direction

- Status: Accepted for POC; not activated by GW-P0
- Decision IDs: GW-D5
- v2.1 amendment: no GPU worker or image generation is started in Phase 0.

## Context

The target worker is a Windows machine with approximately 6 GB VRAM. The normalized crop size is a better fit for SD1.5 than an SDXL/PuLID production direction.

## Decision

The Windows GPU POC direction is SD1.5 plus IPAdapter FaceID. It is a future adapter/workflow direction behind `IdentityRestorerPort`; it does not replace the current `comfyui-local` behavior during baseline freeze.

## Rationale

The model and VRAM choice fit the hardware and crop contract while keeping the compute host replaceable.

## Consequences

Future workflow and model pins must be reproducible and tested on the worker. Phase 0 does not claim a live GPU result.

## Rejected alternatives

- Treating SDXL/PuLID v1 workflow as the new POC authority.
- Starting a paid or GPU generation during baseline freeze.
- Making model selection a UI/domain concern.

## Rollback / reversibility

Keep `comfyui-local` selected until the worker POC passes its own phase gates; discard only the future adapter attempt, not the Golden Master.

## References

v2.0 §2.1 GW-D5, §9, §13 GW-P1; v2.1 patch workflow supersession and rollback notes.

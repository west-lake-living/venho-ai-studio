# ADR-GW-007 — Tailscale security boundary

- Status: Accepted; architecture locked
- Decision IDs: GW-D9
- v2.1 amendment: security boundary is documented only in GW-P0; no worker/network setup is performed here.

## Context

ComfyUI does not provide sufficient application authentication. Binding a worker to a raw LAN address would expose a mutable compute endpoint to the local network.

## Decision

The Windows worker is reached through the Tailscale tailnet. ComfyUI binds locally and is exposed through the tailnet interface; it is not bound to `0.0.0.0` or exposed as a raw LAN service.

## Rationale

The existing stack already has a private tailnet boundary and this avoids adding an unauthenticated LAN endpoint.

## Consequences

Worker health and adapter configuration use the tailnet name. Network setup, firewall, and health proof belong to the Windows worker phase.

## Rejected alternatives

- Raw LAN IP access.
- Internet exposure or port forwarding.
- Treating security as a dashboard/UI concern.

## Rollback / reversibility

Disable the remote adapter and return to `comfyui-local`; never broaden the bind address as a rollback.

## References

v2.0 §2.1 GW-D9, §9, §16; v2.1 locked architecture and no-remote-work in GW-P0.

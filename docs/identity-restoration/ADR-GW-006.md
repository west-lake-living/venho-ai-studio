# ADR-GW-006 — Polling `/history` for the MVP

- Status: Accepted for MVP
- Decision IDs: GW-D8
- v2.1 amendment: no WebSocket or progress redesign is introduced during baseline freeze.

## Context

The worker must survive process restarts and allow durable reconciliation. WebSocket progress is attractive but does not provide the required resumability by itself.

## Decision

The MVP uses ComfyUI polling through `/history`. Detailed progress and WebSocket support are deferred enhancements, not part of the Phase 0 or current production contract.

## Rationale

Polling aligns with durable job recovery and keeps the adapter contract simple and restart-safe.

## Consequences

The adapter needs bounded polling, timeout, cancellation, and error mapping. Progress granularity is intentionally limited in the MVP.

## Rejected alternatives

- Making WebSocket connectivity a prerequisite for the MVP.
- Reporting completion from an in-memory socket event only.

## Rollback / reversibility

Keep the polling contract and replace only the transport behind the port in a later approved decision; existing recorded fixtures remain valid.

## References

v2.0 §2.1 GW-D8, §8.3, §15; existing job/manifest reconciliation contract.

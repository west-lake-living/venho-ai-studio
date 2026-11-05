# ADR-03 — Clean Architecture package boundary

**Status:** Decision recorded for this build on 2026-11-05.

## Context

The existing repository has a large legacy codebase. New publishing and approval rules need testable boundaries and must not accidentally import the old orchestration path.

## Decision

Place the new package at top-level `growth_engine/` with `domain`, `application` and `adapters` layers. Only `growth_engine.adapters.outbound.legacy` may import legacy packages. Keep legacy packages independent of `growth_engine`.

For data ownership, M01 facts remain in their existing store and are copied into immutable package snapshots. Research/trend candidates belong to Growth and move to the v2 database.

## Consequences

- Domain code stays pure and uses the standard library.
- Use cases depend on ports; concrete I/O stays in adapters.
- Architecture tests enforce the import boundaries.
- Temporary Track 0 v2 ports may be used without changing legacy modules; sharing them with v3.2 needs an explicit Change Request.
- Moving M01 facts into the v2 database is excluded; it requires a separate Change Request.

## Alternatives

- `growth_orchestrator/v2/`: rejected because it blurs old and new domain boundaries.
- Moving all M01 facts into v2: rejected for this release because M01 retains ownership.

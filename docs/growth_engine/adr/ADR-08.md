# ADR-08 — Separate publish and jobs worker lanes

**Status:** Decision recorded for this build on 2026-11-05.

## Context

Image generation, quality checks and metrics may take minutes. If they block the scheduler, a content job can cause a due 09:00 post to miss its window.

## Decision

Run `growth-engine-worker@publish` for scheduling, outbox dispatch, timeouts, verification and notifications, and `growth-engine-worker@jobs` for generation, media, QC, research/trend, metrics and backup jobs. Only the publish lane owns the scheduler tick.

## Consequences

- Long jobs do not block the publish scheduler.
- Both workers use the same release and SQLite database.
- Job claiming and concurrency must be protected by DB leases/fencing in P2.

## Alternatives

- One worker for all jobs: rejected because long-running AI/media jobs can delay due publication work.

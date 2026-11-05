# ADR-01 — Local SQLite storage

**Status:** Decision recorded for this build on 2026-11-05; runtime verification is recorded separately by P0-T01.

## Context

Growth needs one durable state store on the server. Git, Google Drive and network filesystems allow competing writers or weak transaction guarantees for publishing state.

## Decision

Use SQLite in WAL mode on local server disk as the single `growth_engine.db`. Require the SQLite version linked by the runtime Python to meet the plan's 3.51.3 minimum or a confirmed backport. Keep media and DB state outside the code checkout. Access storage through repository/UoW ports.

## Consequences

- No Postgres/Redis service is required for the single-host design.
- Only the API and the two workers in the same release may write the DB.
- Backups must capture the SQLite database consistently and be restorable.
- P0-T01 recorded runtime Python 3.11.16 / SQLite 3.53.1; rerun the final self-contained preflight before deployment.

## Alternatives

- Postgres: reconsider only for multiple writer hosts or measured SQLite lock contention.
- Drive/NFS/git: rejected because they do not provide the local transactional single-writer behavior required by the invariants.

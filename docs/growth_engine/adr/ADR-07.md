# ADR-07 — User-level deployment layout

**Status:** Default selected per ADR-07; final G-P0 acceptance and server deployment pending.

## Context

The current ASUS server runtime runs under a user account. Deploying as root or replacing state in place would add privilege and risk overwriting DB/media/secrets.

## Decision

Release code under `~/venho/growth-engine/releases/<sha>` with `current` symlink. Keep state under `~/venho/state/growth-engine/`. Run API and workers as `systemctl --user` units; do not deploy to the production server as part of this task.

## Consequences

- Code releases can be rolled back by switching the release symlink while state remains separate.
- User lingering and service permissions must be verified before deployment.
- The deploy script and units are delivered in P9-T01; deployment is a later gated operation.
- Backup archives use `age` with the private key held outside the server and are copied to a separate Google Drive folder. The jobs lane sends its heartbeat to healthchecks.io. P6 verifies tools, destination and recovery before any production setup.

## Alternatives

- Root-owned `/opt` and `/var/lib`: rejected for this single-user runtime because it requires elevated privileges and departs from the existing server setup.

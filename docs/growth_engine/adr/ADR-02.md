# ADR-02 — Growth Engine is the publishing authority

**Status:** Decision recorded for this build on 2026-11-05; production transition remains gated.

## Context

Legacy JSON state can be written by more than one process and synchronized through Git. That cannot safely coordinate approvals, per-channel delivery ownership and Make side effects.

## Decision

Use one `growth-engine-api` and its two workers as the only writers to `growth_engine.db`. Dashboard, Make and research ingestion call the API. GitHub Actions and the dashboard must not write the DB directly. Keep v3.2's existing publishing path frozen until the cutover gates pass.

The v2 publishing scope has three independent channel targets: `fb_hanoi`, `fb_venho`, and `ig_venho`. This corrects the earlier two-Page-only assumption; Instagram is a publishing channel and uses its own approved 4:5 variant, Make route, authorization principal and receipt. The three production channels remain disabled until their route and provider capabilities are verified.

GC2-D07 allows only the read-only Track 0 modules in parallel. Do not advance rollout, remove `--allow-shadow`, add a publishing workflow schedule, or change legacy dispatch/registry behavior during this build.

## Consequences

- DB transaction, audit record and outbox state can change atomically.
- A deploy must release API and workers from the same code version.
- A webhook 2xx is not evidence of publication; a platform receipt and verification are required.
- This decision reopens only the publishing portion deferred under Control Plane v4.x; it does not authorize a wider Control Plane migration.

## Alternatives

- Keep v3.2 as the only publishing authority and build analytics only: rejected for the selected Plan C.
- Let Dashboard CLI write the DB: rejected because separate checkouts could write concurrently.

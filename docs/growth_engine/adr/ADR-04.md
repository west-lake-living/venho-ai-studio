# ADR-04 — Single-gate publishing admission

**Status:** Default selected per GC2-D03; final G-P0 acceptance pending.

## Context

Make performs the external publish side effect, so approval or a webhook acknowledgment cannot prove that a post was created. A separate claim and authorize step would add lease state and more recovery cases.

## Decision

Use `envelope → Make downloads approved media → authorize → execute only when execute=true → create post → receipt`. Authorization is the single gate; the first compare-and-set wins. An uncertain result becomes `UNKNOWN` and requires reconciliation. Never infer that 2xx or `Accepted` means published.

Approval is grouped once across the three channel targets of a slot, while each delivery and its publishing outcome remains channel-specific.

## Consequences

- The make route cannot create a post before a valid authorization response.
- Once authorized, the command is not re-delivered automatically.
- Make retry/resume settings are part of the acceptance contract and must be tested in P0-T03/P5-T05.
- The design does not promise exactly-once behavior across DB, Make and Meta.

## Alternatives

- Two-step claim/authorize with a `PREPARING` state: rejected because it adds a lease/recovery path without removing the external side-effect uncertainty.

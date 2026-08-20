# ADR-GW-008 — Mock restorer as the test default

- Status: Accepted; architecture locked
- Decision IDs: GW-D10
- v2.1 amendment: Golden Master regression remains offline with zero network calls; no new validator or evidence adapter is added.

## Context

Repository tests must be deterministic and must not require a Windows worker, ComfyUI process, or paid provider. The existing contract requires zero network calls in tests.

## Decision

Use `mock` as the default restorer for tests, with recorded HTTP fixtures for contract tests where needed. Production selection is explicit and separate from the test default. Golden Master uses frozen/local artifacts and mock vision as already recorded.

## Rationale

This makes the contract testable in CI and prevents false confidence from unavailable infrastructure or accidental network calls.

## Consequences

Tests must prove adapter-independent domain invariants and must fail if a network call leaks into the default path. Mock output is not a production-quality claim.

## Rejected alternatives

- Defaulting tests to live ComfyUI.
- Defaulting tests to Nano Banana or another paid provider.
- Skipping contract tests when the worker is unavailable.

## Rollback / reversibility

Keep the mock default. Replace only recorded fixtures or an explicit adapter in a later approved change; do not weaken the zero-network invariant.

## References

v2.0 §2.1 GW-D10, §5, §12, §13; `tests/test_gw_p0_t2_golden.py`; v2.1 offline Golden Master contract.

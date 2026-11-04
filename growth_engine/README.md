# Growth Engine v2

This package owns the new Growth publishing workflow after the P9 cutover gates. Until then, v3.2 remains the live publishing authority.

## Layer rules

- `domain/` uses the Python standard library only and contains no I/O.
- `application/` depends on domain models and application ports, never adapters.
- `adapters/inbound/` invokes application use cases through the composition root.
- `adapters/outbound/` implements ports; only `adapters/outbound/legacy/` may bridge to legacy packages.
- `settings.py` reads `GE_*` environment variables. Production startup rejects empty values and `REQUIRED_FROM_P0` placeholders.

## Development checks

```bash
uv run --extra api --with pytest --with httpx pytest -q tests/growth_engine
uv run --with pytest pytest -q tests/growth_engine/architecture
```

Tests under `tests/growth_engine/` block non-loopback socket connections.

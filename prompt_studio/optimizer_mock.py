"""Mock optimizer (§9.4) — echoes the deterministic contract unchanged (still schema-valid).

No network call, no token cost. Lets pipeline tests run fully offline and deterministically,
same discipline as Module 01's mock provider. The real optimizer (§9, Step 9) will call this
same post-check so both share one schema-validity guard.
"""

from __future__ import annotations

from prompt_studio.schemas.prompt_contract import PromptContractBase
from shared.vision.errors import SchemaValidationError


def optimize_mock(contract: PromptContractBase) -> PromptContractBase:
    """Return an equivalent contract, only optimizer metadata changed. No AI call."""
    optimized = contract.model_copy(
        deep=True,
        update={
            "optimizer": contract.optimizer.model_copy(
                update={"used": True, "provider": "mock", "model": "mock", "temperature": 0}
            )
        },
    )
    assert_schema_valid(optimized)
    return optimized


def assert_schema_valid(contract: PromptContractBase) -> None:
    """Defensive re-validation any optimizer (mock or real) output must pass (§9.2, §8 Validate #2 gate)."""
    try:
        type(contract).model_validate(contract.model_dump())
    except Exception as exc:
        raise SchemaValidationError(
            f"optimizer produced an invalid {type(contract).__name__}", raw=str(exc)
        ) from exc

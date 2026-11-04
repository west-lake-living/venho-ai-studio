from __future__ import annotations

import pytest

from growth_engine.domain.ops.budget import budget_allows


def test_budget_includes_reserved_unknown_settled_and_new_amount() -> None:
    assert budget_allows(cap=1_000, reserved=100, unknown=200, settled=300, amount=400)
    assert not budget_allows(cap=999, reserved=100, unknown=200, settled=300, amount=400)
    assert budget_allows(cap=0, reserved=0, unknown=0, settled=0, amount=0)


@pytest.mark.parametrize("values", [(-1, 0, 0, 0, 0), (1, -1, 0, 0, 0), (1, 0, 0, 0, -1)])
def test_budget_rejects_negative_minor_units(values: tuple[int, int, int, int, int]) -> None:
    with pytest.raises(ValueError):
        budget_allows(
            cap=values[0],
            reserved=values[1],
            unknown=values[2],
            settled=values[3],
            amount=values[4],
        )

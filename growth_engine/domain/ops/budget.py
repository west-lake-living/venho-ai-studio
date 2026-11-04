from __future__ import annotations


def budget_allows(
    *,
    cap: int,
    reserved: int,
    unknown: int,
    settled: int,
    amount: int,
) -> bool:
    values = (cap, reserved, unknown, settled, amount)
    if any(type(value) is not int or value < 0 for value in values):
        raise ValueError("budget amounts must be non-negative integer minor units")
    return reserved + unknown + settled + amount <= cap

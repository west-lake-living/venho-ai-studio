from __future__ import annotations

import math
from collections.abc import Callable


RandomUniform = Callable[[float, float], float]


def full_jitter(attempt: int, rng: RandomUniform) -> float:
    """Return full-jitter delay in seconds for a zero-based retry attempt."""
    if type(attempt) is not int or attempt < 0:
        raise ValueError("attempt must be a non-negative integer")
    if not callable(rng):
        raise TypeError("rng must be callable")
    cap = min(300.0, 5.0 * (2**attempt))
    delay = rng(0.0, cap)
    if not isinstance(delay, (int, float)) or not math.isfinite(delay) or not 0 <= delay <= cap:
        raise ValueError("rng must return a finite value within the requested bounds")
    return float(delay)

from __future__ import annotations

from collections.abc import Iterable

from growth_orchestrator.weekly_theme.models import AngleType, Weekday


CADENCE: tuple[Weekday, ...] = ("monday", "wednesday", "friday", "saturday")
DEFAULT_ROTATION: tuple[AngleType, ...] = (
    AngleType.PRACTICAL,
    AngleType.OBSERVATION,
    AngleType.GUIDE,
    AngleType.STORY,
    AngleType.CONTEXT,
    AngleType.SERVICE,
)


def choose_angle_types(
    *,
    available: Iterable[AngleType] = DEFAULT_ROTATION,
    require_count: int = 4,
) -> tuple[list[AngleType], list[str]]:
    """Choose distinct types without weakening the diversity constraint.

    ``SERVICE`` is capped at one per plan.  Same-weekday collision avoidance
    against recent plans lives in ``planner.py`` because it needs the actual
    weekday order; if the available set cannot satisfy ``require_count`` the
    caller gets fewer angles plus a warning.
    """
    pool = list(dict.fromkeys(item if isinstance(item, AngleType) else AngleType(str(item)) for item in available))

    chosen: list[AngleType] = []
    warnings: list[str] = []
    for candidate in pool:
        if len(chosen) >= require_count:
            break
        if candidate is AngleType.SERVICE and any(item is AngleType.SERVICE for item in chosen):
            continue
        chosen.append(candidate)
    if len(chosen) < require_count:
        warnings.append(f"Tuần thiếu chất liệu, chỉ dựng được {len(chosen)} góc khác loại.")

    return chosen, warnings

from __future__ import annotations

from growth_orchestrator.weekly_theme.models import AngleType
from growth_orchestrator.weekly_theme.planner import plan_week


def test_plan_has_four_different_angle_types_and_local_spine() -> None:
    plan = plan_week(
        "2026-W37",
        local_beats=[{"title": "Đường Quảng An đang thi công", "concrete_details": ["Đường Quảng An", "Từ Hoa"]}],
    )
    assert plan.spine_source == "local_beat"
    assert len(plan.angles) == 4
    assert len({angle.angle_type for angle in plan.angles.values()}) == 4
    assert all(len(angle.concrete_details) >= 2 for angle in plan.angles.values())
    assert sum(angle.angle_type is AngleType.SERVICE for angle in plan.angles.values()) <= 1


def test_empty_inputs_return_three_angles_and_warning() -> None:
    plan = plan_week("2026-W37")
    assert len(plan.angles) == 3
    assert any("thiếu chất liệu" in warning for warning in plan.warnings)


def test_recent_same_weekday_angle_type_is_rotated() -> None:
    plan = plan_week(
        "2026-W37",
        evergreen=["Một buổi sáng quanh Hồ Tây"],
        recent_plans=[{
            "angles": {
                "monday": {"angle_type": "practical"},
                "wednesday": {"angle_type": "observation"},
            }
        }],
    )
    assert plan.angles["monday"].angle_type.value != "practical"
    assert plan.angles["wednesday"].angle_type.value != "observation"

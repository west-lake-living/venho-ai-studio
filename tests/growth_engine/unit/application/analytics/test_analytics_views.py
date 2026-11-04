from __future__ import annotations

import pytest

from growth_engine.application.queries.analytics_views import AnalyticsViews


def test_week_start_must_be_monday_and_checkpoint_must_be_named() -> None:
    views = AnalyticsViews(lambda: pytest.fail("validation must run before opening the database"))
    with pytest.raises(ValueError, match="Monday"):
        views.weekly(week_start="2026-11-03", checkpoint="7d")
    with pytest.raises(ValueError, match="checkpoint"):
        views.weekly(week_start="2026-11-02", checkpoint="adhoc")

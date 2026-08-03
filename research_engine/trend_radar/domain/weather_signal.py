from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class WeatherSignal(BaseModel):
    """R2-T only. Weather shapes which scenario/hook to use -- it is never a
    citable fact (fact_key is always None; §6.6 'R2-T shapes the ANGLE, R3
    supplies the FACT')."""

    rs_id: str
    type: Literal["weather"] = "weather"
    domain: Literal["weather_signal"] = "weather_signal"
    evidence_level: Literal["R2-T"] = "R2-T"
    forecast_date: str
    condition: Literal["morning_mist", "clear_sunrise", "rain", "heat", "cold_snap", "golden_sunset"]
    temperature_range: Optional[tuple[float, float]] = None
    visual_opportunity: Optional[str] = None
    matching_scenario_keys: list[str] = Field(default_factory=list)
    expires_at: str
    fact_key: Literal[None] = None

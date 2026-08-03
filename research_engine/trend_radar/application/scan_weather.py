from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from research_engine.trend_radar.domain.weather_signal import WeatherSignal


def build_weather_signal(forecast: dict[str, Any], *, policy: dict[str, Any], rs_id: str, generated_at: datetime) -> WeatherSignal:
    """Turn one raw forecast reading into an R2-T WeatherSignal note.

    `expires_at` is always derived from `policy["expiry_hours"]` relative to
    `generated_at` (24-48h per the master plan) -- it is never taken from the
    upstream provider, so a slow-changing forecast API can't accidentally
    hand back a signal that lives longer than the policy allows.
    """
    expiry_hours = policy.get("expiry_hours", 48)
    scenario_mapping = policy.get("scenario_mapping", {})
    condition = forecast["condition"]
    return WeatherSignal(
        rs_id=rs_id,
        forecast_date=forecast["forecast_date"],
        condition=condition,
        temperature_range=tuple(forecast["temperature_range"]) if forecast.get("temperature_range") else None,
        visual_opportunity=forecast.get("visual_opportunity"),
        matching_scenario_keys=scenario_mapping.get(condition, []),
        expires_at=(generated_at + timedelta(hours=expiry_hours)).isoformat(),
    )


def scan_weather(forecasts: list[dict[str, Any]], *, policy: dict[str, Any], generated_at: datetime) -> list[WeatherSignal]:
    return [
        build_weather_signal(forecast, policy=policy, rs_id=f"RS-weather-{forecast['forecast_date']}", generated_at=generated_at)
        for forecast in forecasts
    ]

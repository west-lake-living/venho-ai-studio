"""Real 3-day forecast for West Lake, mapped to the six shooting conditions.

Provider is Open-Meteo: free, no API key, no signup, no quota to run out
mid-week. For a one-person hotel that matters more than accuracy at the
third decimal -- a weather source that needs a paid key is a weather source
that stops working the month a card expires.

What this produces is R2-T and stays R2-T: weather decides the *angle* of a
Saturday post (which scenario to shoot, which hook to open with), never a
claim in it. `WeatherSignal.fact_key` is pinned to None for that reason.

Condition mapping is deliberately coarse. There are six conditions because
there are six shooting scenarios in weather_policy.yaml, not because the
weather has six states; anything that does not clearly match one of the
photogenic ones falls through to the nearest usable bucket rather than
inventing a seventh.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from shared.http import urllib_get

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes (Open-Meteo's `weathercode`).
_FOG_CODES = {45, 48}
_RAIN_CODES = set(range(51, 68)) | set(range(80, 83)) | set(range(95, 100))

# Hanoi thresholds, not generic ones: 33°C is when the rooftop stops being
# comfortable, 16°C is a real cold snap here and reads as one in a caption.
HEAT_MAX_C = 33.0
COLD_SNAP_MIN_C = 16.0


def collect_weather_forecast_stub() -> list[dict]:
    return []


def _condition_for(day: dict[str, Any]) -> str:
    """One condition per forecast day, in priority order.

    Rain first because it rules out every outdoor scenario regardless of
    what else is true; mist next because a misty West Lake sunrise is the
    single most valuable shot on this list and is easy to lose to a
    temperature rule firing first.
    """
    code = int(day.get("weathercode") or 0)
    tmax = day.get("temperature_max")
    tmin = day.get("temperature_min")
    if code in _RAIN_CODES:
        return "rain"
    if code in _FOG_CODES:
        return "morning_mist"
    if tmin is not None and tmin <= COLD_SNAP_MIN_C:
        return "cold_snap"
    if tmax is not None and tmax >= HEAT_MAX_C:
        return "heat"
    if code == 0:
        # Cloudless: both ends of the day are shootable. Sunrise wins --
        # the lake-view rooms face it, and it is the scenario the room
        # photography is built around.
        return "clear_sunrise"
    return "golden_sunset"


_VISUAL_OPPORTUNITY = {
    "morning_mist": "Sương sớm trên mặt hồ — cửa sổ phòng view hồ lúc bình minh",
    "clear_sunrise": "Trời quang lúc bình minh — mặt hồ phẳng, ánh sáng ấm",
    "golden_sunset": "Hoàng hôn vàng trên Hồ Tây — rooftop cuối ngày",
    "rain": "Mưa ngoài cửa kính — không gian ấm trong sảnh",
    "heat": "Nắng gắt — bóng râm rooftop, đồ uống mát",
    "cold_snap": "Trở lạnh — sảnh ấm, đèn vàng",
}


def collect_weather_forecast(
    *,
    lat: float,
    lon: float,
    horizon_hours: int = 72,
    http_get: Optional[Callable[..., dict[str, Any]]] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Forecast rows shaped the way `scan_weather` expects.

    Returns [] rather than raising on a provider failure: a missing forecast
    means the Saturday post loses a hint, and that must never be the reason
    a content run fails.
    """
    days = max(1, min(7, -(-horizon_hours // 24)))  # ceil, clamped to the API's range
    get = http_get or urllib_get
    try:
        payload = get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min",
                "timezone": "Asia/Bangkok",
                "forecast_days": days,
            },
        )
    except Exception:  # noqa: BLE001 - see docstring
        return []

    daily = (payload or {}).get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weathercode") or []
    maxima = daily.get("temperature_2m_max") or []
    minima = daily.get("temperature_2m_min") or []

    today = today or date.today()
    forecasts = []
    for index, forecast_date in enumerate(dates):
        # A provider that returns yesterday (timezone edges, cached responses)
        # would otherwise produce a signal that is already expired on arrival.
        if forecast_date < today.isoformat():
            continue
        row = {
            "weathercode": codes[index] if index < len(codes) else None,
            "temperature_max": maxima[index] if index < len(maxima) else None,
            "temperature_min": minima[index] if index < len(minima) else None,
        }
        condition = _condition_for(row)
        temperature_range = None
        if row["temperature_min"] is not None and row["temperature_max"] is not None:
            temperature_range = [float(row["temperature_min"]), float(row["temperature_max"])]
        forecasts.append(
            {
                "forecast_date": forecast_date,
                "condition": condition,
                "temperature_range": temperature_range,
                "visual_opportunity": _VISUAL_OPPORTUNITY[condition],
            }
        )
    return forecasts


def collect_weather_forecast_from_policy(
    policy: dict[str, Any],
    *,
    http_get: Optional[Callable[..., dict[str, Any]]] = None,
    today: Optional[date] = None,
) -> list[dict[str, Any]]:
    location = policy.get("location") or {}
    return collect_weather_forecast(
        lat=float(location.get("lat", 21.0583)),
        lon=float(location.get("lon", 105.82)),
        horizon_hours=int(policy.get("horizon_hours", 72)),
        http_get=http_get,
        today=today,
    )


def next_saturday(on_or_after: date) -> date:
    return on_or_after + timedelta(days=(5 - on_or_after.weekday()) % 7)


def signal_for_date(signals: list[Any], target: date, *, now: Optional[datetime] = None) -> Optional[Any]:
    """The still-valid signal covering `target`, or None.

    Expiry is checked here rather than trusted: a signal read off disk days
    later is exactly the case `expires_at` exists for, and preflight will
    fail the dispatch if an expired one reaches the package anyway.
    """
    now = now or datetime.now()
    for signal in signals:
        forecast_date = signal.forecast_date if hasattr(signal, "forecast_date") else signal.get("forecast_date")
        expires_at = signal.expires_at if hasattr(signal, "expires_at") else signal.get("expires_at")
        if forecast_date != target.isoformat():
            continue
        if expires_at and datetime.fromisoformat(expires_at) <= now:
            continue
        return signal
    return None

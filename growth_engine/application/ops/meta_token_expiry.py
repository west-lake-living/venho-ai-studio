from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo


WARN_WITHIN_DAYS = 14
_ICT = ZoneInfo("Asia/Ho_Chi_Minh")
_MONITORED_EXPIRIES = (
    ("IG_VENHO", "long-lived user token", "GE_META_TOKEN_EXPIRY_IG_VENHO"),
    ("IG_VENHO", "Data Access", "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO"),
)


@dataclass(frozen=True)
class ExpiryAlert:
    key: str
    message: str


@dataclass(frozen=True)
class MetaTokenExpiryReport:
    status: str
    detail: str
    alerts: tuple[ExpiryAlert, ...]


def evaluate_meta_token_expiry(
    token_expiries: Mapping[str, str],
    data_access_expiries: Mapping[str, str],
    *,
    now_ms: int,
) -> MetaTokenExpiryReport:
    if type(now_ms) is not int:
        raise ValueError("now_ms must be an integer")
    today = datetime.fromtimestamp(now_ms / 1000, timezone.utc).astimezone(_ICT).date()
    missing: list[str] = []
    due: list[tuple[str, date, int, ExpiryAlert]] = []
    configured: list[tuple[str, date, int]] = []

    for channel, label, variable in _MONITORED_EXPIRIES:
        values = token_expiries if variable == "GE_META_TOKEN_EXPIRY_IG_VENHO" else data_access_expiries
        raw = values.get(channel, "").strip()
        if not raw or "REQUIRED_FROM_P0" in raw:
            missing.append(variable)
            continue
        try:
            expires_on = date.fromisoformat(raw)
        except ValueError:
            missing.append(variable + " (invalid date)")
            continue
        days_remaining = (expires_on - today).days
        configured.append((variable, expires_on, days_remaining))
        if days_remaining <= WARN_WITHIN_DAYS:
            kind = label.lower().replace(" ", "-")
            key = f"meta-expiry:{channel}:{kind}:{expires_on.isoformat()}"
            message = (
                f"Meta IG_VENHO {label} expires on {expires_on.isoformat()} "
                f"({days_remaining} days remaining). Renew it and update {variable}."
            )
            due.append((label, expires_on, days_remaining, ExpiryAlert(key, message)))

    alerts = tuple(item[3] for item in due)
    if missing or due:
        details = []
        if due:
            details.extend(
                f"{label} {expires_on.isoformat()} ({days} ngày)"
                for label, expires_on, days, _alert in due
            )
        if missing:
            details.append("thiếu/ngày sai: " + ", ".join(missing))
        return MetaTokenExpiryReport("WARN", "; ".join(details), alerts)
    detail = "; ".join(
        f"{variable} còn {days} ngày ({expires_on.isoformat()})"
        for variable, expires_on, days in configured
    )
    return MetaTokenExpiryReport("PASS", detail or "Không có expiry được theo dõi.", alerts)


class MetaTokenExpiryMonitor:
    """Queue one durable Telegram notification per credential and expiry date."""

    def __init__(
        self,
        token_expiries: Mapping[str, str],
        data_access_expiries: Mapping[str, str],
        notification_queue: Any,
        now_ms: Callable[[], int],
    ) -> None:
        self._token_expiries = dict(token_expiries)
        self._data_access_expiries = dict(data_access_expiries)
        self._notification_queue = notification_queue
        self._now_ms = now_ms

    def execute(self) -> MetaTokenExpiryReport:
        now_ms = self._now_ms()
        report = evaluate_meta_token_expiry(
            self._token_expiries,
            self._data_access_expiries,
            now_ms=now_ms,
        )
        for alert in report.alerts:
            self._notification_queue.enqueue_unique(
                alert.key,
                alert.message,
                created_at_ms=now_ms,
            )
        return report

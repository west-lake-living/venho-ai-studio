from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import yaml


def runway_status(open_slot_count: int, policy: dict) -> str:
    """Runway measured in open PublishingSlots, not calendar days (v3.1 PB-003)."""
    runway = policy.get("runway_slots") or policy.get("runway_days", {})
    if open_slot_count >= runway.get("healthy_min", 6):
        return "healthy"
    if open_slot_count >= runway.get("warning_min", 4):
        return "warning"
    if open_slot_count >= runway.get("critical_min", 2):
        return "critical"
    return "empty"


def check_runway(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    config_root: Path = Path("config/projects"),
    horizon_days: Optional[int] = None,
    slot_store: Optional[Any] = None,
    notifier: Optional[Any] = None,
    chat_id: Optional[str] = None,
) -> dict[str, Any]:
    """Count still-`OPEN` PublishingSlots inside the rolling horizon and
    alert Telegram when the queue runway drops to critical/empty (PB-003).

    `OPEN` (not "generated but unapproved") is deliberate: `run_weekly_cycle`
    ensures a fresh 14-day horizon of OPEN slots every real run
    (`SlotStore.ensure_slots`, idempotent), so this count only shrinks
    toward zero if that job *stops running* -- a broken GitHub Actions cron,
    an expired token, a dead job queue. That makes this a real infra-health
    canary, not just a content backlog counter: it fires before a slot is
    ever at risk of going unfilled.

    Wired best-effort (never raises) from `run_weekly_cycle`'s tail so every
    real weekly run re-checks the horizon it just (re)ensured; also exposed
    standalone via CLI `check-runway` for an on-demand look.
    """
    from shared.jobs.slot_store import SlotStore
    from shared.notify.telegram import send_alert, telegram_notifier_or_mock_from_env

    policy_path = config_root / project / "growth" / "queue_policy.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) if policy_path.exists() else {}
    horizon = horizon_days if horizon_days is not None else 14

    slot_store = slot_store or SlotStore(db_path=data_root / project / "growth" / "growth.db")
    today = date.today()
    dates = [(today + timedelta(days=offset)).isoformat() for offset in range(horizon)]
    slots = slot_store.list_for_week(dates)
    open_count = sum(1 for slot in slots if slot.status == "OPEN")
    status = runway_status(open_count, policy)

    result: dict[str, Any] = {"open_slot_count": open_count, "status": status, "horizon_days": horizon}

    if status in ("critical", "empty"):
        resolved_chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        if resolved_chat_id:
            notifier = notifier or telegram_notifier_or_mock_from_env(os.environ)
            event = "runway_critical" if status == "critical" else "runway_empty"
            result["alert"] = send_alert(
                event,
                f"VENHO Growth runway {status}: {open_count} open slot(s) trong {horizon} ngày tới.",
                notifier=notifier,
                chat_id=resolved_chat_id,
            )
    return result

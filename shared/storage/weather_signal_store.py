"""Latest weather signals, for the Saturday special lane to read.

Written by the research cycle's `weather_signal` domain, read by
`daily_cycle` when it builds a special-lane package. A plain overwrite-in-
place file, unlike the trend/fact stores: a forecast has no decisions
attached to it and no history worth keeping, and yesterday's 3-day forecast
is not evidence of anything -- it is just wrong.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class WeatherSignalStore:
    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "research" / "weather_signals.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return payload.get("signals", []) if isinstance(payload, dict) else payload

    def replace(self, signals: list[dict[str, Any]]) -> int:
        self.path.write_text(
            json.dumps(
                {"generated_at": datetime.now().isoformat(), "signals": signals},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return len(signals)

    def valid_signals(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Only signals that have not expired. Callers building a content
        package must never see an expired one -- preflight would fail the
        dispatch on it (`weather_signal_expired`), which is the right outcome
        but a needlessly late one."""
        now = now or datetime.now()
        valid = []
        for signal in self.load():
            expires_at = signal.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) <= now:
                continue
            valid.append(signal)
        return valid

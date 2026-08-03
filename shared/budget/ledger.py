from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class BudgetLedger:
    def __init__(self, db_path: Path = Path("data/projects/venho_hotel/growth/growth.db")) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS budget_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reservation_id TEXT NOT NULL,
                  action TEXT NOT NULL,
                  amount_minor INTEGER NOT NULL,
                  currency TEXT NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS budget_overrides (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  reservation_id TEXT NOT NULL,
                  amount_minor INTEGER NOT NULL,
                  currency TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  approved_by TEXT NOT NULL,
                  created_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def reserve(self, reservation_id: str, amount_minor: int, currency: str = "VND") -> None:
        self._record(reservation_id, "RESERVE", amount_minor, currency)

    def commit(self, reservation_id: str, amount_minor: int, currency: str = "VND") -> None:
        self._record(reservation_id, "COMMIT", amount_minor, currency)

    def release(self, reservation_id: str, amount_minor: int, currency: str = "VND") -> None:
        self._record(reservation_id, "RELEASE", amount_minor, currency)

    def _record(self, reservation_id: str, action: str, amount_minor: int, currency: str) -> None:
        if amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")
        with self._connect() as db:
            db.execute(
                "INSERT INTO budget_events (reservation_id, action, amount_minor, currency, created_at) VALUES (?, ?, ?, ?, ?)",
                (reservation_id, action, amount_minor, currency, datetime.now().isoformat()),
            )

    def totals(self, currency: str = "VND") -> dict[str, int]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT action, COALESCE(SUM(amount_minor), 0) FROM budget_events WHERE currency=? GROUP BY action",
                (currency,),
            ).fetchall()
        totals = {"RESERVE": 0, "COMMIT": 0, "RELEASE": 0}
        totals.update({action: int(amount) for action, amount in rows})
        totals["OUTSTANDING"] = totals["RESERVE"] - totals["COMMIT"] - totals["RELEASE"]
        return totals

    def spend_minor(self, currency: str = "VND") -> int:
        totals = self.totals(currency)
        return totals["COMMIT"] + max(totals["OUTSTANDING"], 0)

    def record_override(self, reservation_id: str, amount_minor: int, *, reason: str, approved_by: str, currency: str = "VND") -> None:
        if amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")
        if not reason.strip() or not approved_by.strip():
            raise ValueError("budget override requires reason and approved_by")
        with self._connect() as db:
            db.execute(
                "INSERT INTO budget_overrides (reservation_id, amount_minor, currency, reason, approved_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (reservation_id, amount_minor, currency, reason.strip(), approved_by.strip(), datetime.now().isoformat()),
            )

    def overrides(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT reservation_id, amount_minor, currency, reason, approved_by, created_at FROM budget_overrides ORDER BY id"
            ).fetchall()
        return [
            {
                "reservation_id": row[0],
                "amount_minor": row[1],
                "currency": row[2],
                "reason": row[3],
                "approved_by": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]


class BudgetPolicy:
    def __init__(self, *, monthly_cap_minor: int, alert_thresholds: list[float], currency: str = "VND") -> None:
        self.monthly_cap_minor = monthly_cap_minor
        self.alert_thresholds = sorted(alert_thresholds)
        self.currency = currency

    @classmethod
    def from_file(cls, path: Path = Path("config/projects/venho_hotel/growth/budget_policy.yaml")) -> "BudgetPolicy":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            monthly_cap_minor=int(payload["monthly_cap_minor"]),
            alert_thresholds=[float(item) for item in payload.get("alert_thresholds", [0.7, 0.85, 1.0])],
            currency=payload.get("currency", "VND"),
        )

    def evaluate(self, ledger: BudgetLedger, *, pending_amount_minor: int = 0) -> dict[str, Any]:
        projected = ledger.spend_minor(self.currency) + pending_amount_minor
        ratio = projected / self.monthly_cap_minor if self.monthly_cap_minor else 1.0
        crossed = [threshold for threshold in self.alert_thresholds if ratio >= threshold]
        return {
            "currency": self.currency,
            "monthly_cap_minor": self.monthly_cap_minor,
            "projected_spend_minor": projected,
            "ratio": ratio,
            "alerts": [f"BUDGET_{int(threshold * 100)}" for threshold in crossed],
            "blocked": ratio >= 1.0,
        }

    def reserve_paid_call(
        self,
        ledger: BudgetLedger,
        reservation_id: str,
        amount_minor: int,
        *,
        override: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        evaluation = self.evaluate(ledger, pending_amount_minor=amount_minor)
        if evaluation["blocked"]:
            if not override:
                raise ValueError("budget cap reached: paid call blocked")
            ledger.record_override(
                reservation_id,
                amount_minor,
                reason=override["reason"],
                approved_by=override["approved_by"],
                currency=self.currency,
            )
        ledger.reserve(reservation_id, amount_minor, self.currency)
        return evaluation

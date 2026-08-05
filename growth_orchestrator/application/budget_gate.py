from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml

from shared.budget.ledger import BudgetLedger, BudgetPolicy

DEFAULT_COSTS_PATH_TEMPLATE = "config/projects/{project}/growth/paid_call_costs.yaml"


def load_paid_call_costs(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class BudgetGate:
    """Reserve/commit/release wrapper around `shared.budget.{BudgetLedger,
    BudgetPolicy}` for every real paid OpenAI call `daily_cycle.py` makes
    (Phase 5, plan §14 "budget ledger 70/85/100% -> block paid call unless
    override recorded").

    Before this (2026-08-06), `BudgetLedger`/`BudgetPolicy` had real,
    tested code but zero real caller -- every gpt-5.5/gpt-image-2/GPT-4o
    vision call in the actual weekly GitHub Actions cron ran completely
    unmetered against `budget_policy.yaml`'s cap.

    Cost estimates in `paid_call_costs.yaml` are approximate (documented as
    such in that file) -- not derived from real per-call token/pixel
    accounting, since neither the OpenAI text/image/vision adapters in this
    codebase surface real billed cost back to the caller. Good enough to
    make the cap actually bite; correct the numbers once real invoice data
    is available.

    A reservation_id must be unique per attempt (caller's responsibility,
    e.g. include a uuid) so a blocked/failed attempt never double-reserves
    against a retry's reservation.
    """

    def __init__(
        self,
        *,
        project: str = "venho_hotel",
        data_root: Path = Path("data/projects"),
        config_root: Path = Path("config/projects"),
        ledger: Optional[BudgetLedger] = None,
        policy: Optional[BudgetPolicy] = None,
        costs: Optional[dict[str, Any]] = None,
    ) -> None:
        self.ledger = ledger or BudgetLedger(db_path=data_root / project / "growth" / "growth.db")
        self.policy = policy or BudgetPolicy.from_file(config_root / project / "growth" / "budget_policy.yaml")
        self.costs = (
            costs if costs is not None else load_paid_call_costs(config_root / project / "growth" / "paid_call_costs.yaml")
        )

    def try_reserve(self, cost_key: str, reservation_id: str) -> tuple[bool, dict[str, Any]]:
        """Attempt to reserve `cost_key`'s configured amount. Returns
        (True, evaluation) if the call may proceed, (False, evaluation) if
        the monthly cap is reached and no override was recorded -- callers
        must not make the real API call when this returns False."""
        amount = int(self.costs.get(cost_key, 0))
        try:
            evaluation = self.policy.reserve_paid_call(self.ledger, reservation_id, amount)
            return True, evaluation
        except ValueError:
            return False, self.policy.evaluate(self.ledger, pending_amount_minor=amount)

    def commit(self, reservation_id: str, cost_key: str) -> None:
        self.ledger.commit(reservation_id, int(self.costs.get(cost_key, 0)))

    def release(self, reservation_id: str, cost_key: str) -> None:
        self.ledger.release(reservation_id, int(self.costs.get(cost_key, 0)))

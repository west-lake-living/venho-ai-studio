from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_STAGE = "shadow"


class RolloutStateStore:
    """Single JSON file tracking the Growth Agent's real rollout stage
    (`controlled_rollout.rollout_policy.STAGES`) and every transition
    decision made about it.

    Advancing this store's `current_stage` does not change system
    behaviour by itself -- `final_approval_required`/`m03_mandatory_before_review`
    stay hard-on regardless of stage (Part 14, "KHÔNG BAO GIỜ tắt"). It is a
    governance record: proof of when Harry (or the scorecard gate) decided
    the pilot earned more real-traffic share, and why, not a switch that
    turns off approval. Defaults to `"shadow"` because that is the real
    state the Growth Agent has been in since it first went live
    2026-08-03/04 -- nothing has advanced this yet.
    """

    def __init__(self, project: str = "venho_hotel", data_root: Path = Path("data/projects")) -> None:
        self.path = data_root / project / "rollout" / "rollout_state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"current_stage": _DEFAULT_STAGE, "history": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def status(self) -> dict[str, Any]:
        return self._load()

    def record_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Append a rollout decision (the dict shape `next_rollout_stage`
        returns) to history, and advance `current_stage` only if the
        decision was actually `allowed` -- a blocked decision is recorded
        for audit trail but never moves the stage."""
        data = self._load()
        entry = {**decision, "recorded_at": datetime.now(timezone.utc).isoformat()}
        data["history"].append(entry)
        if decision.get("allowed"):
            data["current_stage"] = decision["next_stage"]
        self._save(data)
        return data

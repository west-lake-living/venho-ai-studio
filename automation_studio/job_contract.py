from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal["draft", "approved", "executed", "published", "failed", "cancelled"]


class JobTransitionError(ValueError):
    pass


class JobContract(BaseModel):
    contract_version: str = "1.0"
    job_id: str
    capability: str
    project: str
    status: JobStatus = "draft"
    approval: Optional[dict[str, Any]] = None
    execution: Optional[dict[str, Any]] = None
    publication: Optional[dict[str, Any]] = None
    audit: list[dict[str, Any]] = Field(default_factory=list)

    def transition(self, next_status: JobStatus, *, actor: str, note: str = "") -> "JobContract":
        allowed = {
            "draft": {"approved", "cancelled", "failed"},
            "approved": {"executed", "cancelled", "failed"},
            "executed": {"published", "failed"},
            "published": set(),
            "failed": set(),
            "cancelled": set(),
        }
        if next_status not in allowed[self.status]:
            raise JobTransitionError(f"Invalid transition: {self.status} -> {next_status}")
        stamp = datetime.utcnow().isoformat()
        data = {"actor": actor, "at": stamp, "note": note}
        patch: dict[str, Any] = {"status": next_status, "audit": self.audit + [{"from": self.status, "to": next_status, **data}]}
        if next_status == "approved":
            patch["approval"] = data
        elif next_status == "executed":
            patch["execution"] = data
        elif next_status == "published":
            patch["publication"] = data
        return self.model_copy(update=patch)

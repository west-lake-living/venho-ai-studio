from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Approval(BaseModel):
    approved_by: str
    approved_at: str
    approval_signature: str
    validator_status: Optional[str] = "pass"

from __future__ import annotations

from dataclasses import dataclass

from growth_engine.domain.delivery.states import DeliveryEvent, DeliveryState


@dataclass(frozen=True)
class VerificationEvidence:
    delivery_state: DeliveryState
    existence: str
    ownership: str
    previous_visibility: str | None = None
    observed_visibility: str | None = None


def classify_verification(evidence: VerificationEvidence) -> DeliveryEvent | None:
    if evidence.delivery_state is DeliveryState.REPORTED_PUBLISHED:
        if evidence.existence == "EXISTS" and evidence.ownership == "MATCH":
            return DeliveryEvent.VERIFY_OK
        if evidence.existence in {"NOT_FOUND", "MISMATCH"}:
            return DeliveryEvent.VERIFY_MISMATCH
        return None
    if evidence.delivery_state is DeliveryState.PUBLISHED:
        if (
            evidence.previous_visibility is not None
            and evidence.observed_visibility is not None
            and evidence.previous_visibility != evidence.observed_visibility
        ):
            return DeliveryEvent.VISIBILITY_CHANGE
    return None

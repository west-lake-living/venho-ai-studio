from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class FacadeObservation(BaseObservation):
    """Observation output for a single hotel facade/exterior image."""
    subject: str = "facade"


class FacadeDNA(BaseDNA):
    """Consolidated DNA for the hotel facade subject."""
    subject: str = "facade"

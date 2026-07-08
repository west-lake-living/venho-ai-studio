from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class WestLakeObservation(BaseObservation):
    """Observation output for a single West Lake environment image."""
    subject: str = "westlake"


class WestLakeDNA(BaseDNA):
    """Consolidated DNA for the West Lake environment subject."""
    subject: str = "westlake"

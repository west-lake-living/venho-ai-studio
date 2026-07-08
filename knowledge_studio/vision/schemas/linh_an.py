from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class LinhAnObservation(BaseObservation):
    """Observation output for a single image of the Linh An character."""
    subject: str = "linh_an"


class LinhAnDNA(BaseDNA):
    """Consolidated DNA for the Linh An AI KOL character subject."""
    subject: str = "linh_an"

from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class LobbyObservation(BaseObservation):
    """Observation output for a single hotel lobby image."""
    subject: str = "lobby"


class LobbyDNA(BaseDNA):
    """Consolidated DNA for the hotel lobby subject."""
    subject: str = "lobby"

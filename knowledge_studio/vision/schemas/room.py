from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class RoomObservation(BaseObservation):
    subject: str = "room"


class RoomDNA(BaseDNA):
    subject: str = "room"

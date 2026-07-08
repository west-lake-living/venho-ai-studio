from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class UniversalObservation(BaseObservation):
    """Observation schema for Mode A — any subject, universal keys."""
    schema_id: str = "universal"


class UniversalDNA(BaseDNA):
    """DNA schema for Mode B with universal subject schema."""
    schema_id: str = "universal"

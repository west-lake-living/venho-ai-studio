from __future__ import annotations

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA


class FaceObservation(BaseObservation):
    """Observation schema for face subjects (e.g. Linh An).

    Grounding/web search MUST be disabled when using this schema.
    Only describes structural features — never identifies real people.
    Each character gets its own separate DNA — never shared across projects.
    """
    schema_id: str = "face"


class FaceDNA(BaseDNA):
    """DNA schema for face subjects.

    Invariant = structural identity features (face shape, eye shape, nose, lips, etc.)
    Variable = appearance features (lighting, expression, hairstyle, outfit)
    """
    schema_id: str = "face"

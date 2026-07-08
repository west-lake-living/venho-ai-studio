from __future__ import annotations

from typing import Type

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA
from knowledge_studio.vision.schemas.universal import UniversalObservation, UniversalDNA


def get_observation_cls(subject: str) -> Type[BaseObservation]:
    _map = {
        "room":     "knowledge_studio.vision.schemas.room.RoomObservation",
        "lobby":    "knowledge_studio.vision.schemas.lobby.LobbyObservation",
        "facade":   "knowledge_studio.vision.schemas.facade.FacadeObservation",
        "westlake": "knowledge_studio.vision.schemas.westlake.WestLakeObservation",
        "linh_an":  "knowledge_studio.vision.schemas.linh_an.LinhAnObservation",
        "face":     "knowledge_studio.vision.schemas.face.FaceObservation",
    }
    if subject not in _map:
        return UniversalObservation
    module_path, cls_name = _map[subject].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


def get_dna_cls(subject: str) -> Type[BaseDNA]:
    _map = {
        "room":     "knowledge_studio.vision.schemas.room.RoomDNA",
        "lobby":    "knowledge_studio.vision.schemas.lobby.LobbyDNA",
        "facade":   "knowledge_studio.vision.schemas.facade.FacadeDNA",
        "westlake": "knowledge_studio.vision.schemas.westlake.WestLakeDNA",
        "linh_an":  "knowledge_studio.vision.schemas.linh_an.LinhAnDNA",
        "face":     "knowledge_studio.vision.schemas.face.FaceDNA",
    }
    if subject not in _map:
        return UniversalDNA
    module_path, cls_name = _map[subject].rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)

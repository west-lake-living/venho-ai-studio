from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Type

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA

PROMPTS_DIR = Path(__file__).parent / "prompts"


@dataclass
class SubjectDef:
    name: str
    display_name: str
    observe_prompt: Path
    consolidate_prompt: Path
    observation_cls: Type[BaseObservation]
    dna_cls: Type[BaseDNA]
    dna_filename: str


def get_subject(name: str) -> SubjectDef:
    from knowledge_studio.vision.schemas.room import RoomObservation, RoomDNA
    from knowledge_studio.vision.schemas.lobby import LobbyObservation, LobbyDNA
    from knowledge_studio.vision.schemas.facade import FacadeObservation, FacadeDNA
    from knowledge_studio.vision.schemas.westlake import WestLakeObservation, WestLakeDNA
    from knowledge_studio.vision.schemas.linh_an import LinhAnObservation, LinhAnDNA

    _registry: dict[str, SubjectDef] = {
        "room": SubjectDef(
            name="room",
            display_name="Hotel Room",
            observe_prompt=PROMPTS_DIR / "observe_room.md",
            consolidate_prompt=PROMPTS_DIR / "consolidate_room.md",
            observation_cls=RoomObservation,
            dna_cls=RoomDNA,
            dna_filename="VENHO_ROOM_DNA",
        ),
        "lobby": SubjectDef(
            name="lobby",
            display_name="Hotel Lobby",
            observe_prompt=PROMPTS_DIR / "observe_lobby.md",
            consolidate_prompt=PROMPTS_DIR / "consolidate_lobby.md",
            observation_cls=LobbyObservation,
            dna_cls=LobbyDNA,
            dna_filename="VENHO_LOBBY_DNA",
        ),
        "facade": SubjectDef(
            name="facade",
            display_name="Hotel Facade",
            observe_prompt=PROMPTS_DIR / "observe_facade.md",
            consolidate_prompt=PROMPTS_DIR / "consolidate_facade.md",
            observation_cls=FacadeObservation,
            dna_cls=FacadeDNA,
            dna_filename="VENHO_FACADE_DNA",
        ),
        "westlake": SubjectDef(
            name="westlake",
            display_name="West Lake Environment",
            observe_prompt=PROMPTS_DIR / "observe_westlake.md",
            consolidate_prompt=PROMPTS_DIR / "consolidate_westlake.md",
            observation_cls=WestLakeObservation,
            dna_cls=WestLakeDNA,
            dna_filename="VENHO_WESTLAKE_DNA",
        ),
        "linh_an": SubjectDef(
            name="linh_an",
            display_name="Linh An — AI KOL Character",
            observe_prompt=PROMPTS_DIR / "observe_face.md",
            consolidate_prompt=PROMPTS_DIR / "consolidate_values.md",
            observation_cls=LinhAnObservation,
            dna_cls=LinhAnDNA,
            dna_filename="VENHO_LINH_AN_DNA",
        ),
    }

    if name not in _registry:
        available = list(_registry)
        raise ValueError(f"Unknown subject: '{name}'. Available: {available}")
    return _registry[name]


def list_subjects() -> list[str]:
    return ["room", "lobby", "facade", "westlake", "linh_an"]

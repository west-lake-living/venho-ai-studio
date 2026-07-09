"""Knowledge Reader (§3.4) — reads Module 01's merged DNA JSON and maps it into Prompt
Studio's vocabulary. Reads ONLY the DNA JSON (already merged with overrides.yaml by
Module 01); never reads overrides.yaml directly and never reads source images."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from prompt_studio.schemas.base import (
    AllowedImperfectionItem,
    AllowedVariationItem,
    ForbiddenItem,
    RequiredDnaItem,
    SourceKnowledgeEntry,
)

# Contract compatibility window this Prompt Studio version understands (§3.4, §17.6).
MIN_SUPPORTED_CONTRACT_VERSION: Tuple[int, int] = (1, 1)
MAX_SUPPORTED_CONTRACT_VERSION_EXCLUSIVE: Tuple[int, int] = (2, 0)

REQUIRED_TOP_LEVEL_FIELDS = (
    "contract_version",
    "project",
    "subject",
    "dna_version",
    "invariant",
    "variable",
    "allowed_imperfections",
    "forbidden",
)


class DnaReadError(Exception):
    """A DNA JSON file is missing a required field, or its contract_version is out of the
    range this Prompt Studio version supports (§3.4: 'báo lỗi rõ, không đoán')."""


def _parse_version(version: str, path: Path) -> Tuple[int, int]:
    parts = version.split(".")
    if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
        raise DnaReadError(f"{path.name}: contract_version '{version}' is not a parseable 'MAJOR.MINOR' version")
    return int(parts[0]), int(parts[1])


def _check_contract_version(version: str, path: Path) -> None:
    parsed = _parse_version(version, path)
    if not (MIN_SUPPORTED_CONTRACT_VERSION <= parsed < MAX_SUPPORTED_CONTRACT_VERSION_EXCLUSIVE):
        raise DnaReadError(
            f"{path.name}: dna_contract_version {version} is outside the supported range "
            f">={'.'.join(map(str, MIN_SUPPORTED_CONTRACT_VERSION))},"
            f"<{'.'.join(map(str, MAX_SUPPORTED_CONTRACT_VERSION_EXCLUSIVE))}"
        )


@dataclass
class KnowledgeDna:
    """One DNA JSON file, read and mapped into Prompt Studio's vocabulary."""

    path: Path
    project: str
    subject: str
    dna_version: str
    contract_version: str
    content_hash: str
    required_dna: List[RequiredDnaItem] = field(default_factory=list)
    allowed_variations: List[AllowedVariationItem] = field(default_factory=list)
    allowed_imperfections: List[AllowedImperfectionItem] = field(default_factory=list)
    forbidden: List[ForbiddenItem] = field(default_factory=list)

    def source_entry(self) -> SourceKnowledgeEntry:
        return SourceKnowledgeEntry(
            file=self.path.name,
            dna_version=self.dna_version,
            dna_contract_version=self.contract_version,
            hash=f"sha256:{self.content_hash}",
        )


def read_dna(path: Path) -> KnowledgeDna:
    """Read one merged DNA JSON file (Module 01 output) and map it (§3.4).

    Raises DnaReadError with a clear message if a required field is missing or the
    contract_version is out of the supported range. Never reads overrides.yaml or images.
    """
    path = Path(path)
    if not path.exists():
        raise DnaReadError(f"DNA file not found: {path}")

    raw_bytes = path.read_bytes()
    data = json.loads(raw_bytes.decode("utf-8"))

    missing = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in data]
    if missing:
        raise DnaReadError(f"{path.name}: missing required field(s): {missing}")

    _check_contract_version(data["contract_version"], path)

    required_dna = [RequiredDnaItem(key=item["key"], value=item["value"]) for item in data["invariant"]]
    allowed_variations = [
        AllowedVariationItem(key=item["key"], value_range=item["value_range"]) for item in data["variable"]
    ]
    allowed_imperfections = [AllowedImperfectionItem(**item) for item in data["allowed_imperfections"]]
    forbidden = [ForbiddenItem(**item) for item in data["forbidden"]]

    return KnowledgeDna(
        path=path,
        project=data["project"],
        subject=data["subject"],
        dna_version=data["dna_version"],
        contract_version=data["contract_version"],
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        required_dna=required_dna,
        allowed_variations=allowed_variations,
        allowed_imperfections=allowed_imperfections,
        forbidden=forbidden,
    )

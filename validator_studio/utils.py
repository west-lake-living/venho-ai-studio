from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9_\s-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def token_set(value: str) -> set[str]:
    stop = {
        "a", "an", "the", "and", "or", "of", "to", "is", "are", "with", "in",
        "on", "no", "not", "actual", "this", "that", "style", "look",
    }
    return {t for t in normalize_text(value).replace("_", " ").split() if len(t) > 2 and t not in stop}


def find_dna_path(project: str, subject: str, base_dir: Path = BASE_DIR) -> Path:
    knowledge_dir = base_dir / "data" / "projects" / project / "knowledge"
    candidates = [
        knowledge_dir / f"{project.upper()}_{subject.upper()}_DNA.json",
        knowledge_dir / f"VENHO_HOTEL_{subject.upper()}_DNA.json",
        knowledge_dir / f"{subject}_DNA.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(knowledge_dir.glob(f"*{subject.upper()}*DNA.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"DNA JSON not found for {project}/{subject} in {knowledge_dir}")


def validation_config(base_dir: Path = BASE_DIR) -> dict[str, Any]:
    data = load_yaml(base_dir / "config" / "validation.yaml")
    return data.get("validation", data)


from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Type

import yaml

from knowledge_studio.vision.schemas.base import BaseObservation, BaseDNA

BASE_DIR = Path(__file__).parent.parent.parent
PROMPTS_DIR = Path(__file__).parent / "prompts"
CONFIG_DIR = BASE_DIR / "config"


@dataclass
class SubjectDef:
    name: str
    display_name: str
    schema_id: str
    schema_yaml: Path
    aggregation_keys: list[dict]
    forbidden_defaults: list[str]
    observe_prompt: Path
    consolidate_prompt: Path
    observation_cls: Type[BaseObservation]
    dna_cls: Type[BaseDNA]
    dna_filename: str
    schema_source: str
    overlay_path: Optional[Path] = field(default=None)


def _load_schema_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _assert_schema_approved(schema_data: dict, path: Path) -> None:
    """Block raw bootstrap drafts from entering Pass 1."""
    if schema_data.get("approved_for_pass1") is False:
        raise ValueError(
            f"Schema is not approved for Pass 1: {path}. "
            "Review fixed keys/types/English enum values, then set approved_for_pass1: true."
        )


def _resolve_schema_path(project: str, subject: str) -> tuple[Path, str]:
    """Resolve schema YAML for (project, subject) via §6 lookup order.

    Returns (yaml_path, source_description).
    """
    candidates = [
        (
            CONFIG_DIR / "projects" / project / "subjects" / f"{subject}.yaml",
            f"config/projects/{project}/subjects/{subject}.yaml",
        ),
        (
            CONFIG_DIR / "projects" / "_shared_subjects" / f"{subject}.yaml",
            f"config/projects/_shared_subjects/{subject}.yaml",
        ),
        (
            CONFIG_DIR / "universal_schema.yaml",
            "config/universal_schema.yaml",
        ),
    ]
    for path, source in candidates:
        if path.exists():
            return path, source
    raise FileNotFoundError(
        f"No schema found for project='{project}' subject='{subject}'. "
        f"Checked: {[str(p) for p, _ in candidates]}"
    )


def _observe_prompt_path(subject: str) -> Path:
    specific = PROMPTS_DIR / f"observe_{subject}.md"
    if specific.exists():
        return specific
    return PROMPTS_DIR / "observe_universal.md"


def _consolidate_prompt_path(subject: str) -> Path:
    specific = PROMPTS_DIR / f"consolidate_{subject}.md"
    if specific.exists():
        return specific
    universal = PROMPTS_DIR / "consolidate_values.md"
    if universal.exists():
        return universal
    raise FileNotFoundError(f"No consolidate prompt found for subject '{subject}'")


def _dna_filename(project: str, subject: str) -> str:
    return f"{project.upper()}_{subject.upper()}_DNA"


def _resolve_overlay_path(project: str, subject: str) -> Optional[Path]:
    """Return overrides.yaml path if it exists (§6: only per-project location)."""
    path = CONFIG_DIR / "projects" / project / "subjects" / f"{subject}.overrides.yaml"
    return path if path.exists() else None


def resolve(project: str, subject: str) -> SubjectDef:
    """Resolve and return a SubjectDef for (project, subject).

    Raises FileNotFoundError if no schema found.
    """
    from knowledge_studio.vision._subject_classes import get_observation_cls, get_dna_cls

    schema_path, source = _resolve_schema_path(project, subject)
    schema_data = _load_schema_yaml(schema_path)
    _assert_schema_approved(schema_data, schema_path)

    schema_id = schema_data.get("schema_id", f"{project}.{subject}")
    display_name = schema_data.get("display_name", subject.replace("_", " ").title())
    aggregation_keys = schema_data.get("aggregation_keys", [])
    forbidden_defaults = schema_data.get("forbidden_defaults", [])

    observe_prompt = _observe_prompt_path(subject)
    consolidate_prompt = _consolidate_prompt_path(subject)

    observation_cls, dna_cls = get_observation_cls(subject), get_dna_cls(subject)
    filename = _dna_filename(project, subject)

    ov_path = _resolve_overlay_path(project, subject)

    print(f"  [schema] {source}")
    if ov_path:
        print(f"  [overlay] {ov_path.relative_to(BASE_DIR)}")

    return SubjectDef(
        name=subject,
        display_name=display_name,
        schema_id=schema_id,
        schema_yaml=schema_path,
        aggregation_keys=aggregation_keys,
        forbidden_defaults=forbidden_defaults,
        observe_prompt=observe_prompt,
        consolidate_prompt=consolidate_prompt,
        observation_cls=observation_cls,
        dna_cls=dna_cls,
        dna_filename=filename,
        schema_source=source,
        overlay_path=ov_path,
    )

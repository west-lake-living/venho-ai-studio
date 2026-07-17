from __future__ import annotations

from pathlib import Path
from typing import Optional

from knowledge_studio.vision.overlay_merge import load_overlay, apply_overlay
from knowledge_studio.vision.schemas.base import BaseDNA
from validator_studio.observe_adapter import observe_image_against_dna
from validator_studio.schemas.validation_base import ArtifactRef, ObserverInfo, PromptRef, SourceKnowledgeRef, ValidationReport
from validator_studio.scoring import score_image_observation
from validator_studio.utils import find_dna_path, load_json, sha256_file, validation_config


def _apply_scenario_overlay(project: str, subject: str, scenario_profile_id: Optional[str], dna: dict) -> dict:
    """Merge an optional per-scenario overrides.yaml onto an already-loaded DNA dict, in memory only.

    Looks for config/projects/<project>/subjects/<subject>.<scenario_profile_id>.overrides.yaml.
    Falls back silently to the unchanged dna dict when no scenario_profile_id is given or no such
    file exists — this never touches the general <subject>.overrides.yaml or the DNA file on disk.
    """
    if not scenario_profile_id:
        return dna
    scenario_overlay = load_overlay(project, f"{subject}.{scenario_profile_id}")
    if not scenario_overlay:
        return dna
    dna_obj = BaseDNA.model_validate(dna)
    return apply_overlay(dna_obj, scenario_overlay).model_dump()


def validate_image(
    project: str,
    subject: str,
    image_path: Path,
    prompt_path: Optional[Path] = None,
    provider: str = "mock",
    samples: Optional[int] = None,
    scenario_profile_id: Optional[str] = None,
) -> ValidationReport:
    config = validation_config()
    resolved_samples = samples or int(config.get("observe_samples", 1))
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    dna = _apply_scenario_overlay(project, subject, scenario_profile_id, dna)
    observation = observe_image_against_dna(image_path, dna, provider=provider, samples=resolved_samples)
    score = score_image_observation(observation, config)
    prompt_ref = None
    if prompt_path:
        prompt = load_json(prompt_path)
        prompt_ref = PromptRef(file=str(prompt_path), prompt_version=prompt.get("prompt_version"))
    report = ValidationReport(
        project=project,
        subject=subject,
        validation_type="image",
        artifact_ref=ArtifactRef(type="image", file=str(image_path), hash=sha256_file(image_path)),
        source_knowledge=[SourceKnowledgeRef(
            file=str(dna_path),
            dna_version=dna.get("dna_version"),
            dna_contract_version=dna.get("contract_version"),
            hash=sha256_file(dna_path),
        )],
        prompt_ref=prompt_ref,
        observer=ObserverInfo(provider=provider, model=provider if provider == "mock" else "configured", samples=resolved_samples),
        kill_switch=score.kill_switch,
        overall_score=score.overall_score,
        verdict=score.verdict,
        dna_match_score=score.dna_match_score,
        section_scores=score.section_scores,
        category_scores=score.category_scores,
        forbidden_violations=score.forbidden_violations,
        allowed_imperfections_check=score.allowed_imperfections_check,
        issues=score.issues,
        recommendation=score.recommendation,
        validation_notes=observation.notes,
        raw_observation=observation.model_dump(mode="json"),
    )
    return report

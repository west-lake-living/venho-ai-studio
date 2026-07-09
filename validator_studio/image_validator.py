from __future__ import annotations

from pathlib import Path
from typing import Optional

from validator_studio.observe_adapter import observe_image_against_dna
from validator_studio.schemas.validation_base import ArtifactRef, ObserverInfo, PromptRef, SourceKnowledgeRef, ValidationReport
from validator_studio.scoring import score_image_observation
from validator_studio.utils import find_dna_path, load_json, sha256_file, validation_config


def validate_image(
    project: str,
    subject: str,
    image_path: Path,
    prompt_path: Optional[Path] = None,
    provider: str = "mock",
    samples: Optional[int] = None,
) -> ValidationReport:
    config = validation_config()
    resolved_samples = samples or int(config.get("observe_samples", 1))
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
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

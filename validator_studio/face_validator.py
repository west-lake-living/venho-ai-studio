from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from shared.vision.client import VisionClient
from shared.vision.structured import extract_json

from validator_studio.observe_adapter import ObservationSchemaError
from validator_studio.schemas.face_validation import FaceGateResult, FaceValidationObservation
from validator_studio.schemas.validation_base import ArtifactRef, ObserverInfo, SourceKnowledgeRef, ValidationReport
from validator_studio.scoring import score_face_observation
from validator_studio.utils import BASE_DIR, find_dna_path, load_json, load_yaml, sha256_file, validation_config


def _load_face_rubric(project: str) -> dict:
    config = validation_config()
    rubric_file = config.get("face_validation", {}).get(
        "rubric_file",
        f"config/projects/{project}/face_qc_rubric.yaml",
    )
    path = BASE_DIR / rubric_file
    data = load_yaml(path)
    rubric = data.get("face_qc_rubric", data)
    if rubric.get("grounding") is not False:
        raise ValueError("Face validation requires grounding=false.")
    return rubric


def _mock_observe_face(image_path: Path, rubric: dict) -> FaceValidationObservation:
    forced_fail = any(flag in image_path.stem.lower() for flag in ("bad", "fail", "wrong", "reject"))
    gates = []
    for index, gate in enumerate(rubric.get("binary_gates", [])):
        gate_id = str(gate.get("id", f"gate_{index + 1}"))
        failed = forced_fail and index == 0
        gates.append(FaceGateResult(
            gate=gate_id,
            passed=not failed,
            reason="Mock forced face gate failure from artifact filename." if failed else "Mock face gate passed against fictional Face DNA.",
            evidence=str(gate.get("description", "")),
        ))
    weighted = {category: 88.0 for category in rubric.get("weighted", {})}
    return FaceValidationObservation(
        gates=gates,
        weighted_scores=weighted,
        notes=[
            "mock face observation; no network calls",
            "grounding/web search disabled; no real-person or celebrity matching performed",
        ],
    )


def _expected_face_gate_ids(rubric: dict) -> set[str]:
    return {str(gate.get("id")) for gate in rubric.get("binary_gates", []) if gate.get("id")}


def _expected_face_score_keys(rubric: dict) -> set[str]:
    weighted = rubric.get("weighted", {})
    return set(weighted) if weighted else {"facial_shape", "eyes", "hair", "expression", "technical_quality"}


def _assert_face_observation_contract(payload: Any, rubric: dict) -> None:
    if not isinstance(payload, dict):
        raise ObservationSchemaError("Face observe must return a JSON object")
    forbidden = {"overall_score", "verdict", "recommendation", "identity_match", "celebrity_match"}
    stack = [payload]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if key in forbidden:
                    raise ObservationSchemaError(f"Face observe must not return field: {key}")
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)

    gates = payload.get("gates")
    if not isinstance(gates, list):
        raise ObservationSchemaError("Face observe must return gates[]")
    actual_gates = {str(gate.get("gate")) for gate in gates if isinstance(gate, dict)}
    expected_gates = _expected_face_gate_ids(rubric)
    if actual_gates != expected_gates:
        raise ObservationSchemaError(
            f"Face gates mismatch. expected={sorted(expected_gates)} actual={sorted(actual_gates)}"
        )

    weighted_scores = payload.get("weighted_scores")
    if not isinstance(weighted_scores, dict):
        raise ObservationSchemaError("Face observe must return weighted_scores{}")
    expected_scores = _expected_face_score_keys(rubric)
    actual_scores = set(weighted_scores)
    if actual_scores != expected_scores:
        raise ObservationSchemaError(
            f"Face weighted score keys mismatch. expected={sorted(expected_scores)} actual={sorted(actual_scores)}"
        )
    for key, value in weighted_scores.items():
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 100:
            raise ObservationSchemaError(f"Face weighted score '{key}' must be on a 0-100 scale")
    if weighted_scores and all(0 <= float(score) <= 1 for score in weighted_scores.values()):
        raise ObservationSchemaError("Face weighted_scores must use 0-100 scale, not 0-1 rubric weights")


REFERENCE_LABELS = ["B3 Hero (primary)", "A2 Front", "C Left Profile", "D Right Profile"]


def _build_face_observe_prompt(dna: dict, rubric: dict, reference_count: int = 0) -> str:
    prompt_path = BASE_DIR / "validator_studio" / "prompts" / "observe_face_against_dna.md"
    base_prompt = prompt_path.read_text(encoding="utf-8")
    payload = {
        "face_dna": {
            "project": dna.get("project"),
            "subject": dna.get("subject"),
            "invariant": dna.get("invariant", []),
            "variable": dna.get("variable", []),
            "forbidden": dna.get("forbidden", []),
        },
        "rubric_07f": rubric,
    }
    reference_block = ""
    if reference_count:
        labels = REFERENCE_LABELS[:reference_count]
        labelled = ", ".join(f"image {i + 2} = {label}" for i, label in enumerate(labels))
        reference_block = (
            "\nREFERENCE IMAGES: image 1 is the generated candidate to be judged. "
            f"The remaining images are approved reference photos of the same fictional character "
            f"at different angles ({labelled}). "
            "Judge identity_structure and eye_ratio by directly comparing the candidate against these "
            "reference images, not only against the text Face DNA below. "
            "The text Face DNA and rubric still define what to look for and how forbidden_traits is judged.\n"
        )
    return (
        f"{base_prompt}\n"
        f"{reference_block}\n"
        "VALIDATION INPUT JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Hard rules: fictional character only, no real-person identification, no celebrity matching, grounding off."
    )


def _observe_face(
    image_path: Path,
    dna: dict,
    rubric: dict,
    provider: str,
    reference_image_paths: Optional[list[Path]] = None,
) -> FaceValidationObservation:
    if provider == "mock":
        return _mock_observe_face(image_path, rubric)
    reference_image_paths = reference_image_paths or []
    for reference_path in reference_image_paths:
        if not reference_path.exists():
            raise FileNotFoundError(f"Face validator reference image not found: {reference_path}")
    client = VisionClient(image_provider=provider, temperature=0.0)
    prompt = _build_face_observe_prompt(dna, rubric, reference_count=len(reference_image_paths))
    if reference_image_paths:
        response = client.analyze_images([image_path, *reference_image_paths], prompt)
    else:
        response = client.analyze_image(image_path, prompt)
    payload = response if isinstance(response, dict) and "gates" in response else extract_json(str(response))
    _assert_face_observation_contract(payload, rubric)
    observation = FaceValidationObservation.model_validate(payload)
    return observation.model_copy(update={
        "notes": [
            *observation.notes,
            f"{provider} face observation; grounding/web search disabled by prompt contract",
            "no real-person or celebrity matching requested",
            *([f"compared against {len(reference_image_paths)} approved reference image(s)"] if reference_image_paths else []),
        ]
    })


def validate_face(
    project: str,
    subject: str,
    image_path: Path,
    provider: str = "mock",
    reference_image_paths: Optional[list[Path]] = None,
) -> ValidationReport:
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    rubric = _load_face_rubric(project)
    observation = _observe_face(image_path, dna, rubric, provider, reference_image_paths)
    score = score_face_observation(observation, rubric)
    return ValidationReport(
        project=project,
        subject=subject,
        validation_type="face",
        artifact_ref=ArtifactRef(type="face", file=str(image_path), hash=sha256_file(image_path)),
        source_knowledge=[SourceKnowledgeRef(
            file=str(dna_path),
            dna_version=dna.get("dna_version"),
            dna_contract_version=dna.get("contract_version"),
            hash=sha256_file(dna_path),
        )],
        observer=ObserverInfo(provider=provider, model=provider if provider == "mock" else "configured", samples=1),
        kill_switch=score.kill_switch,
        overall_score=score.overall_score,
        verdict=score.verdict,
        dna_match_score=score.dna_match_score,
        section_scores=score.section_scores,
        category_scores=score.category_scores,
        issues=score.issues,
        recommendation=score.recommendation,
        validation_notes=observation.notes,
        raw_observation=observation.model_dump(mode="json"),
    )

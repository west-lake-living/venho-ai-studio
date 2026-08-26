from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Optional

from shared.vision.client import VisionClient
from shared.vision.structured import extract_json

from validator_studio.observe_adapter import ObservationSchemaError
from validator_studio.schemas.face_validation import FaceGateResult, FaceValidationObservation, FaceWeightedScores
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
    return set(weighted) if weighted else {
        "facial_shape", "eyes_and_brows", "nose", "mouth_and_chin", "technical_quality",
    }


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


def _build_face_observe_prompt(
    dna: dict,
    rubric: dict,
    reference_image_paths: Optional[list[Path]] = None,
) -> str:
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
    reference_image_paths = reference_image_paths or []
    if reference_image_paths:
        labels = [path.stem.replace("_plate", "").replace("_", " ") for path in reference_image_paths]
        labelled = ", ".join(f"image {i + 2} = {label}" for i, label in enumerate(labels))
        reference_block = (
            "\nREFERENCE IMAGES: image 1 is the generated candidate to be judged. "
            f"The remaining images are approved reference photos ({labelled}). "
            "Judge every identity category by direct candidate-to-reference comparison. "
            "The reference images are authoritative whenever their visible geometry conflicts with the text Face DNA. "
            "Do not reward resemblance to prose traits that are visibly absent from the authoritative reference.\n"
        )
    return (
        f"{base_prompt}\n"
        f"{reference_block}\n"
        "VALIDATION INPUT JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Hard rules: fictional character only, no real-person identification, no celebrity matching, grounding off."
    )


def _merge_face_samples(samples: list[FaceValidationObservation]) -> FaceValidationObservation:
    """Aggregate N independent vision-judge samples of the SAME image into one observation.

    Real-run testing found GPT-4o's face judging is not reliably deterministic even at
    temperature=0.0 — the identical image+reference set produced a passing verdict on one
    call and a hard-reject verdict on another. Majority-vote the binary gates and average
    the weighted scores across samples to reduce the chance that a single unlucky call
    flips a real production run's outcome.
    """
    if len(samples) == 1:
        return samples[0]
    gates_by_id: dict[str, list[FaceGateResult]] = {}
    for sample in samples:
        for gate in sample.gates:
            gates_by_id.setdefault(gate.gate, []).append(gate)
    merged_gates = []
    for gate_id, items in gates_by_id.items():
        votes = Counter(item.passed for item in items)
        majority_passed = votes[True] >= votes[False]
        merged_gates.append(items[0].model_copy(update={"passed": majority_passed}))

    score_keys = samples[0].weighted_scores.model_dump().keys()
    merged_scores = {
        key: round(sum(float(sample.weighted_scores.model_dump().get(key, 0)) for sample in samples) / len(samples), 2)
        for key in score_keys
    }
    return samples[0].model_copy(update={"gates": merged_gates, "weighted_scores": FaceWeightedScores.model_validate(merged_scores)})


def _observe_face(
    image_path: Path,
    dna: dict,
    rubric: dict,
    provider: str,
    reference_image_paths: Optional[list[Path]] = None,
    samples: int = 1,
    raw_response_sink: Optional[Callable[[dict[str, Any]], None]] = None,
) -> FaceValidationObservation:
    if provider == "mock":
        return _mock_observe_face(image_path, rubric)
    reference_image_paths = reference_image_paths or []
    for reference_path in reference_image_paths:
        if not reference_path.exists():
            raise FileNotFoundError(f"Face validator reference image not found: {reference_path}")
    client = VisionClient(image_provider=provider, temperature=0.0)
    prompt = _build_face_observe_prompt(dna, rubric, reference_image_paths=reference_image_paths)

    observed: list[FaceValidationObservation] = []
    for sample_index in range(max(samples, 1)):
        try:
            if raw_response_sink is not None:
                client.raw_response_sink = lambda raw, index=sample_index + 1: raw_response_sink({
                    "validator": "face", "sampleIndex": index, "rawResponse": raw,
                    "parseStatus": "raw_captured",
                })
            schema = FaceValidationObservation.model_json_schema()
            try:
                if reference_image_paths:
                    response = client.analyze_images([image_path, *reference_image_paths], prompt, response_schema=schema, sample_index=sample_index + 1)
                else:
                    response = client.analyze_image(image_path, prompt, response_schema=schema, sample_index=sample_index + 1)
            except TypeError as exc:
                if "unexpected keyword" not in str(exc):
                    raise
                if reference_image_paths:
                    response = client.analyze_images([image_path, *reference_image_paths], prompt)
                else:
                    response = client.analyze_image(image_path, prompt)
            raw = getattr(client, "last_raw_response", None)
            if raw_response_sink is not None:
                raw_response_sink({"validator": "face", "sampleIndex": sample_index + 1,
                                   "rawResponse": raw, "parseStatus": "before_contract"})
            payload = response if isinstance(response, dict) and "gates" in response else extract_json(str(response))
            _assert_face_observation_contract(payload, rubric)
            observation = FaceValidationObservation.model_validate(payload)
            if raw_response_sink is not None:
                raw_response_sink({"validator": "face", "sampleIndex": sample_index + 1,
                                   "rawResponse": raw, "parseStatus": "parsed",
                                   "parsedEvidence": observation.model_dump(mode="json")})
            observed.append(observation)
        except Exception as exc:
            if raw_response_sink is not None:
                raw_response_sink({"validator": "face", "sampleIndex": sample_index + 1,
                                   "rawResponse": getattr(client, "last_raw_response", None),
                                   "parseStatus": "failed", "parseError": str(exc)})
            raise

    observation = _merge_face_samples(observed)
    return observation.model_copy(update={
        "notes": [
            *observation.notes,
            f"{provider} face observation; grounding/web search disabled by prompt contract",
            "no real-person or celebrity matching requested",
            *([f"compared against {len(reference_image_paths)} approved reference image(s)"] if reference_image_paths else []),
            *([f"aggregated from {len(observed)} vision samples (majority-vote gates, averaged scores)"] if len(observed) > 1 else []),
        ]
    })


def validate_face(
    project: str,
    subject: str,
    image_path: Path,
    provider: str = "mock",
    reference_image_paths: Optional[list[Path]] = None,
    samples: int = 1,
    raw_response_sink: Optional[Callable[[dict[str, Any]], None]] = None,
) -> ValidationReport:
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    rubric = _load_face_rubric(project)
    observation = _observe_face(image_path, dna, rubric, provider, reference_image_paths, samples,
                                raw_response_sink=raw_response_sink)
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
        observer=ObserverInfo(
            provider=provider,
            model=provider if provider == "mock" else "configured",
            samples=max(samples, 1) if provider != "mock" else 1,
        ),
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


def report_from_face_observations(
    project: str,
    subject: str,
    image_path: Path,
    observations: list[FaceValidationObservation],
    provider: str,
    reference_image_paths: Optional[list[Path]] = None,
) -> ValidationReport:
    """Build the normal Face ValidationReport from parsed samples offline."""
    if not observations:
        raise ValueError("at least one parsed face observation is required")
    dna_path = find_dna_path(project, subject)
    dna = load_json(dna_path)
    rubric = _load_face_rubric(project)
    observation = _merge_face_samples(observations)
    score = score_face_observation(observation, rubric)
    return ValidationReport(
        project=project, subject=subject, validation_type="face",
        artifact_ref=ArtifactRef(type="face", file=str(image_path), hash=sha256_file(image_path)),
        source_knowledge=[SourceKnowledgeRef(file=str(dna_path), dna_version=dna.get("dna_version"), dna_contract_version=dna.get("contract_version"), hash=sha256_file(dna_path))],
        observer=ObserverInfo(provider=provider, model="configured", samples=len(observations)),
        kill_switch=score.kill_switch, overall_score=score.overall_score,
        verdict=score.verdict, dna_match_score=score.dna_match_score,
        section_scores=score.section_scores, category_scores=score.category_scores,
        issues=score.issues, recommendation=score.recommendation,
        validation_notes=[*observation.notes, f"recovered from {len(observations)} parsed Validator samples"],
        raw_observation=observation.model_dump(mode="json"),
    )

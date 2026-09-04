from __future__ import annotations

from pathlib import Path
import hashlib
import json

import pytest
import yaml

from identity_restoration.application.benchmark_orchestration import _scenario_profile_id
from image_studio_runtime.action_composite.workflow_v2 import RegionalGate
from validator_studio.image_validator import _apply_scenario_authority, report_from_image_observations
from validator_studio.schemas.image_validation import DnaMatchObservation, ImageObservation
from validator_studio.schemas.validation_base import MatchState
from validator_studio.scoring import score_image_observation
from validator_studio.utils import validation_config


ROOT = Path(__file__).resolve().parents[1]


def _observation(*items: DnaMatchObservation) -> ImageObservation:
    return ImageObservation(dna_matches=list(items))


def _match(key: str, state: MatchState = MatchState.MATCH) -> DnaMatchObservation:
    return DnaMatchObservation(key=key, expected=key, observed=key, match_state=state)


def test_action_cases_resolve_explicit_action_full_body_authority():
    contract = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
    cases = {case["id"]: case for case in contract["cases"]}

    for case_id in ("B03", "B04", "B05", "B06"):
        assert _scenario_profile_id(cases[case_id]) == "action_full_body"
    authority = yaml.safe_load((ROOT / "config/projects/venho_hotel/subjects/linh_an.action_full_body.authority.yaml").read_text())
    assert authority["profile_version"] == cases["B03"]["identityRestorationAuthority"]["profileVersion"] == "1.0"
    assert authority["profile_version"] == cases["B04"]["identityRestorationAuthority"]["profileVersion"]


def test_shot_distance_does_not_enter_face_only_restoration_gate():
    scoped = _apply_scenario_authority(
        "venho_hotel", "linh_an", "action_full_body",
        _observation(_match("shot_distance", MatchState.MISMATCH), _match("eye_shape")),
    )

    assert [item.key for item in scoped.dna_matches] == ["eye_shape"]


def test_hairstyle_outside_mask_does_not_enter_face_only_restoration_gate():
    scoped = _apply_scenario_authority(
        "venho_hotel", "linh_an", "action_full_body",
        _observation(_match("hairstyle", MatchState.MISMATCH), _match("jaw_line")),
    )

    assert [item.key for item in scoped.dna_matches] == ["jaw_line"]


def test_face_scope_field_remains_enforced():
    scoped = _apply_scenario_authority(
        "venho_hotel", "linh_an", "action_full_body",
        _observation(_match("shot_distance", MatchState.MISMATCH), _match("eye_shape", MatchState.MISMATCH)),
    )

    assert [item.key for item in scoped.dna_matches] == ["eye_shape"]
    assert score_image_observation(scoped, validation_config()).overall_score < 90


def test_face_geometry_violation_remains_enforced():
    scoped = _apply_scenario_authority(
        "venho_hotel", "linh_an", "action_full_body",
        _observation(_match("face_shape", MatchState.MISMATCH), _match("eye_shape", MatchState.MISMATCH)),
    )

    assert [item.key for item in scoped.dna_matches] == ["face_shape", "eye_shape"]
    assert score_image_observation(scoped, validation_config()).overall_score < 90


def test_non_action_case_keeps_default_dna_scope():
    original = _observation(_match("shot_distance", MatchState.MISMATCH), _match("eye_shape"))
    scoped = _apply_scenario_authority("venho_hotel", "linh_an", None, original)

    assert scoped == original


def test_scenario_without_authority_file_scores_all_fields():
    # An authority profile is optional (like the scenario overrides.yaml). A
    # scenario id with no <subject>.<id>.authority.yaml means "score every
    # observed field", not a hard failure — otherwise overrides-only scenarios
    # such as venho_rooftop_terrace_2026 could never pass Image-QC.
    original = _observation(_match("eye_shape"))
    scoped = _apply_scenario_authority(
        "venho_hotel", "linh_an", "unmapped_scenario", original,
    )
    assert scoped == original


def test_authority_precedence_is_explicit_and_default_is_intact():
    contract = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
    cases = {case["id"]: case for case in contract["cases"]}
    for case_id in ("B03", "B04", "B05", "B06"):
        assert _scenario_profile_id(cases[case_id]) == "action_full_body"
    for case_id in ("B01", "B02", "B07", "B08", "B09", "B10"):
        assert _scenario_profile_id(cases[case_id]) is None

    dna_path = ROOT / "data/projects/venho_hotel/knowledge/VENHO_HOTEL_LINH_AN_DNA.json"
    assert hashlib.sha256(dna_path.read_bytes()).hexdigest() == "71f839dff776ec6d6d085c5a1ab928295af8c32a9699f7929d78b04807ec0075"


@pytest.mark.parametrize(
    ("case_id", "artifact", "expected_score"),
    [
        ("B03", "gw-p4-t2h-c1-b03-regional-20260825-r15", 97.51),
        ("B04", "gw-p4-t2h-c1-b04-regional-20260825-r16", 94.14),
    ],
)
def test_action_authority_replay_is_reproducible(case_id: str, artifact: str, expected_score: float):
    payload = json.loads((ROOT / "artifacts/identity-restoration" / artifact / "regional.json").read_text())
    report = report_from_image_observations(
        "venho_hotel", "linh_an", Path(payload["imageQc"]["artifact_ref"]["file"]),
        [ImageObservation.model_validate(payload["imageQc"]["raw_observation"])],
        "offline-artifact-replay", scenario_profile_id="action_full_body",
    )
    regional = payload["regional"]["regional"]
    passed, failures = RegionalGate(
        identity=regional["identity"], eyes_brows=regional["eyes_brows"],
        geometry=regional["geometry"], anatomy=regional["anatomy"],
        outfit=regional["outfit"], environment=regional["environment"],
        global_composite=report.overall_score, pixel_preservation=True,
    ).evaluate()

    assert payload["case"] == case_id
    assert report.overall_score == expected_score
    assert passed, failures

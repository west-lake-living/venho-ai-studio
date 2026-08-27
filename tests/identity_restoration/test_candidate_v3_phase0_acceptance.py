from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import get_args

import jsonschema
import pytest

from identity_restoration.domain.value_objects import RestorerId
from identity_restoration.infrastructure.composition.env import RestorationEnv, read_restoration_env
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)
from identity_restoration.interface.json_bridge import (
    parse_candidate_v3_request,
    validate_candidate_v3_result_payload,
)
from tests.identity_restoration.contracts.test_candidate_v3_schemas import _request, _result


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = REPO_ROOT / "contracts" / "identity_restoration"
WORKFLOWS = REPO_ROOT / "identity_restoration" / "workflows"
V3_SCHEMAS = [
    "identity_pack_v1.schema.json",
    "scenario_authority_binding_v1.schema.json",
    "face_observability_v1.schema.json",
    "canonical_face_transform_v1.schema.json",
    "candidate_v3_request_v1.schema.json",
    "candidate_v3_result_v1.schema.json",
]
EXPECTED_RESTORER_IDS = {
    "comfyui-local",
    "comfyui-remote",
    "comfyui-candidate-v3",
    "nano-banana-edit",
    "mock",
}
EXPECTED_V2_WORKFLOW_SHA256 = "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"


def _load_schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def test_phase0_candidate_v3_contracts_and_boundary_exist() -> None:
    for name in V3_SCHEMAS:
        schema = _load_schema(name)
        jsonschema.Draft202012Validator.check_schema(schema)

    assert parse_candidate_v3_request(_request()).candidate_profile_id
    assert validate_candidate_v3_result_payload(_result())["schemaVersion"] == "1.0"


def test_phase0_feature_flag_defaults_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("IDR_CANDIDATE_V3_ENABLED", raising=False)

    assert read_restoration_env().candidate_v3_enabled is False


def test_phase0_disabled_candidate_v3_has_no_executable_registration(tmp_path: Path) -> None:
    env = RestorationEnv(candidate_v3_enabled=False, default_restorer="mock")
    module = build_identity_restoration_module(env, repo_root=tmp_path)

    assert set(get_args(RestorerId)) == EXPECTED_RESTORER_IDS
    assert set(module.registry.restorers) == {"mock"}
    assert not any("v3" in restorer_id or "candidate" in restorer_id
                   for restorer_id in module.registry.restorers)


def test_phase0_historical_and_candidate_boundaries_are_preserved() -> None:
    workflow = WORKFLOWS / "face_restore_win_sd15_ipadapter_v2.api.json"
    candidate_workflow = WORKFLOWS / "face_restore_win_sd15_ipadapter_v3.api.json"

    assert workflow.is_file()
    assert hashlib.sha256(workflow.read_bytes()).hexdigest() == EXPECTED_V2_WORKFLOW_SHA256
    assert candidate_workflow.is_file()
    assert candidate_workflow != workflow
    assert (CONTRACTS / "restoration_manifest_1_3.schema.json").is_file()

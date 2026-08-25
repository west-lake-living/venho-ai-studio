from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from identity_restoration.domain.errors import RestorationError
from identity_restoration.infrastructure.comfyui.graph_binder import bind_by_title
from identity_restoration.infrastructure.comfyui.workflow_repository import FileWorkflowRepository
from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_ID = "face_restore_win_sd15_ipadapter_v1"
WORKFLOW = ROOT / "identity_restoration" / "workflows" / "face_restore_win_sd15_ipadapter_v1.api.json"
STAGED = ROOT / "staging" / "gw-p3" / "windows-20260824-125915-425372"
LEGACY = ROOT / "workflows" / "_archive" / "face_restore_v1_api.json"
LEGACY_SHA = "b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25"


def test_imported_workflow_is_byte_exact_windows_authority() -> None:
    assert WORKFLOW.read_bytes() == (STAGED / "workflow_api.json").read_bytes()
    actual = hashlib.sha256(WORKFLOW.read_bytes()).hexdigest()
    recorded = (STAGED / "workflow_api.sha256").read_text().split()[0]
    assert actual == recorded == "7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8"


def test_workflow_repository_loads_pinned_workflow() -> None:
    workflow, descriptor = FileWorkflowRepository(
        workflow_root=ROOT / "identity_restoration" / "workflows",
        pins_path=ROOT / "config" / "projects" / "venho_hotel" / "identity_restoration" / "workflow_pins.yaml",
    ).load(WORKFLOW_ID)
    assert workflow["10"]["inputs"]["preset"] == "FACEID PLUS V2"
    assert descriptor.workflow_id == WORKFLOW_ID
    assert descriptor.sha256 == "7a320dd58c6e96b4d8c1c0e82c2ffe1d6ca6ace12a691f1aca5ebef8589f1ec8"


def test_workflow_repository_loads_dimension_preserving_v2_candidate() -> None:
    workflow, descriptor = FileWorkflowRepository(
        workflow_root=ROOT / "identity_restoration" / "workflows",
        pins_path=ROOT / "config" / "projects" / "venho_hotel" / "identity_restoration" / "workflow_pins.yaml",
    ).load("face_restore_win_sd15_ipadapter_v2")
    assert descriptor.sha256 == "1a6421a04ce7bdedd716beea93d196551f5dbe77c3da11d1e8a6bc4f1f06ee58"
    assert workflow["19"]["class_type"] == "ImageCrop"


def test_tampered_workflow_hard_fails(tmp_path: Path) -> None:
    workflow_root = tmp_path / "workflows"
    workflow_root.mkdir()
    tampered = json.loads(WORKFLOW.read_text())
    tampered["12"]["inputs"]["seed"] = 999
    (workflow_root / WORKFLOW.name).write_text(json.dumps(tampered), encoding="utf-8")
    pins = (ROOT / "config" / "projects" / "venho_hotel" / "identity_restoration" / "workflow_pins.yaml").read_text()
    pin_path = tmp_path / "pins.yaml"
    pin_path.write_text(pins, encoding="utf-8")
    with pytest.raises(RestorationError, match="sha256 mismatch"):
        FileWorkflowRepository(workflow_root=workflow_root, pins_path=pin_path).load(WORKFLOW_ID)


def test_titleless_authoritative_graph_binds_assets_and_runtime_values() -> None:
    workflow = json.loads(WORKFLOW.read_text())
    original = json.loads(json.dumps(workflow))
    bound = bind_by_title(workflow, {
        "VENHO_INPUT_CROP": "venho/run/crop.png",
        "VENHO_INPUT_MASK": "venho/run/mask.png",
        "VENHO_INPUT_A2_FRONT": "venho/run/a2.png",
    }, runtime_values={
        "seed": 4242, "denoise": 0.35, "steps": 20, "cfg": 6.0,
        "sampler": "euler", "scheduler": "normal",
    })
    assert bound["2"]["inputs"]["image"] == "venho/run/crop.png"
    assert bound["4"]["inputs"]["image"] == "venho/run/mask.png"
    assert bound["3"]["inputs"]["image"] == "venho/run/a2.png"
    assert bound["12"]["inputs"]["seed"] == 4242
    assert bound["12"]["inputs"]["denoise"] == 0.35
    assert workflow == original


def test_geometry_nodes_and_exact_output_crop_survive_remote_binding() -> None:
    workflow = json.loads(WORKFLOW.read_text())
    bound = bind_by_title(workflow, {
        "VENHO_INPUT_CROP": "venho/run/crop.png",
        "VENHO_INPUT_MASK": "venho/run/mask.png",
        "VENHO_INPUT_A2_FRONT": "venho/run/a2.png",
    }, runtime_values={"seed": 123456, "denoise": 0.35})
    assert bound["16"]["class_type"] == "ImagePadForOutpaint"
    assert bound["17"]["class_type"] == "ImagePadForOutpaint"
    assert bound["18"]["class_type"] == "ImageToMask"
    assert bound["19"]["class_type"] == "ImageCrop"
    assert bound["16"]["inputs"]["right"] == 1
    assert bound["16"]["inputs"]["bottom"] == 5
    assert bound["19"]["inputs"]["width"] == 687
    assert bound["19"]["inputs"]["height"] == 659
    assert bound["14"]["inputs"]["images"] == ["19", 0]


def test_semantic_binding_fails_closed_when_authority_node_is_ambiguous() -> None:
    workflow = json.loads(WORKFLOW.read_text())
    workflow["15"] = json.loads(json.dumps(workflow["2"]))
    with pytest.raises(RestorationError, match="VENHO_INPUT_CROP"):
        bind_by_title(workflow, {"VENHO_INPUT_CROP": "crop.png"})


def test_registry_gates_preserve_mock_local_and_remote(tmp_path: Path) -> None:
    def ids(**kwargs: object) -> set[str]:
        env = RestorationEnv(**kwargs)
        return set(build_identity_restoration_module(env=env, repo_root=ROOT).registry.restorers)

    assert ids() == {"mock"}
    assert ids(comfyui_enabled=True) == {"mock", "comfyui-local"}
    assert ids(comfyui_remote_enabled=True) == {"mock", "comfyui-remote"}
    assert ids(comfyui_enabled=True, comfyui_remote_enabled=True) == {
        "mock", "comfyui-local", "comfyui-remote"
    }


def test_legacy_golden_master_workflow_is_unchanged() -> None:
    assert hashlib.sha256(LEGACY.read_bytes()).hexdigest() == LEGACY_SHA

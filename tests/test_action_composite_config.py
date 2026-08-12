import json

import pytest

from image_studio_runtime.action_composite.config import ComfyUIConfig


def test_comfyui_config_loads_versioned_workflow_from_relative_path(tmp_path):
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps({"1": {"class_type": "CheckpointLoaderSimple", "inputs": {}}}), encoding="utf-8")
    config = ComfyUIConfig(workflow_path="workflow.json")
    assert config.load_workflow(tmp_path)["1"]["class_type"] == "CheckpointLoaderSimple"


def test_comfyui_config_from_env_is_deterministic():
    config = ComfyUIConfig.from_env({"VENHO_COMFYUI_ENDPOINT": "http://localhost:9999", "VENHO_COMFYUI_TIMEOUT_SECONDS": "9"})
    assert config.endpoint == "http://localhost:9999"
    assert config.timeout_seconds == 9


def test_empty_env_falls_back_to_defaults():
    config = ComfyUIConfig.from_env({})
    assert config.timeout_seconds == 120.0
    assert config.node_bindings["base"] == "base_image"


def test_unparseable_timeout_names_the_offending_variable():
    with pytest.raises(ValueError, match="VENHO_COMFYUI_TIMEOUT_SECONDS"):
        ComfyUIConfig.from_env({"VENHO_COMFYUI_TIMEOUT_SECONDS": "two minutes"})


def test_node_bindings_come_from_env_as_json():
    config = ComfyUIConfig.from_env({"VENHO_COMFYUI_NODE_BINDINGS": '{"base": "scene_loader"}'})
    assert config.node_bindings == {"base": "scene_loader"}


def test_relative_workflow_path_resolves_against_the_repo_not_the_cwd(monkeypatch, tmp_path):
    """Resolving against "." made the workflow load depend on where the worker
    happened to be started from."""
    from image_studio_runtime.action_composite.config import BASE_DIR

    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError) as error:
        ComfyUIConfig(workflow_path="config/comfyui/face_restore_v1_api.json").load_workflow()

    assert str(BASE_DIR / "config" / "comfyui" / "face_restore_v1_api.json") in str(error.value)

from __future__ import annotations

import json
from pathlib import Path

from identity_restoration.infrastructure.comfyui.error_mapper import (
    map_empty_outputs,
    map_history_status,
    map_prompt_submission_error,
)

FIXTURES = Path(__file__).resolve().parents[3] / "contracts" / "identity_restoration" / "fixtures" / "comfyui"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_oom_message_maps_to_vram_exhausted_and_is_retryable_once() -> None:
    history = _load("history_error_oom.json")
    item = history["8f3a2b10-example-prompt-id"]
    error = map_history_status(item["status"], prompt_id="8f3a2b10-example-prompt-id")
    assert error is not None
    assert error.code == "ERR_GW_VRAM_EXHAUSTED"
    assert error.retryable is True


def test_generic_error_status_maps_to_workflow_invalid_and_is_not_retryable() -> None:
    status = {"status_str": "error", "messages": [["execution_error", {"exception_message": "node input missing"}]]}
    error = map_history_status(status, prompt_id="x")
    assert error is not None
    assert error.code == "ERR_GW_WORKFLOW_INVALID"
    assert error.retryable is False


def test_success_status_maps_to_none() -> None:
    history = _load("history_completed.json")
    item = history["8f3a2b10-example-prompt-id"]
    assert map_history_status(item["status"], prompt_id="x") is None


def test_history_completed_empty_outputs_fixture_has_no_images() -> None:
    history = _load("history_completed_empty_outputs.json")
    item = history["8f3a2b10-example-prompt-id"]
    assert item["outputs"] == {}
    error = map_empty_outputs("8f3a2b10-example-prompt-id")
    assert error.code == "ERR_GW_EMPTY_OUTPUT"


def test_400_response_maps_to_workflow_invalid() -> None:
    error = map_prompt_submission_error(400, "node type mismatch")
    assert error.code == "ERR_GW_WORKFLOW_INVALID"
    assert error.retryable is False


def test_other_status_maps_to_upload_failed_and_is_retryable() -> None:
    error = map_prompt_submission_error(503, "server busy")
    assert error.code == "ERR_GW_UPLOAD_FAILED"
    assert error.retryable is True

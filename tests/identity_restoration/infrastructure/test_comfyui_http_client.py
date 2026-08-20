from __future__ import annotations

import json
from pathlib import Path

import pytest

from identity_restoration.domain.errors import RestorationError
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient

FIXTURES = Path(__file__).resolve().parents[3] / "contracts" / "identity_restoration" / "fixtures" / "comfyui"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload if isinstance(self._payload, bytes) else json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_submit_prompt_returns_prompt_id_from_recorded_fixture(monkeypatch) -> None:
    fixture = _load("prompt_queued.json")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(fixture)

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")
    prompt_id = client.submit_prompt({"1": {}})
    assert prompt_id == fixture["prompt_id"]


def test_poll_until_complete_returns_image_info_on_success(monkeypatch) -> None:
    history = _load("history_completed.json")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(history)

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.time.sleep", lambda s: None)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")

    result = client.poll_until_complete("8f3a2b10-example-prompt-id", timeout_seconds=30)

    assert result["filename"] == "restored_00001_.png"


def test_poll_until_complete_raises_structured_error_on_oom(monkeypatch) -> None:
    history = _load("history_error_oom.json")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(history)

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.time.sleep", lambda s: None)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")

    with pytest.raises(RestorationError) as exc_info:
        client.poll_until_complete("8f3a2b10-example-prompt-id", timeout_seconds=30)
    assert exc_info.value.code == "ERR_GW_VRAM_EXHAUSTED"


def test_poll_until_complete_raises_empty_output_when_completed_with_no_images(monkeypatch) -> None:
    history = _load("history_completed_empty_outputs.json")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(history)

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.time.sleep", lambda s: None)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")

    with pytest.raises(RestorationError) as exc_info:
        client.poll_until_complete("8f3a2b10-example-prompt-id", timeout_seconds=1)
    assert exc_info.value.code in {"ERR_GW_EMPTY_OUTPUT", "ERR_GW_WORKER_TIMEOUT"}


def test_download_returns_raw_bytes(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        return _FakeResponse(b"\x89PNG-fake-bytes")

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")
    data = client.download({"filename": "restored_00001_.png", "subfolder": "venho/x/y", "type": "output"})
    assert data == b"\x89PNG-fake-bytes"

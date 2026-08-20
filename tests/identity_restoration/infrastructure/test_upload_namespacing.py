from __future__ import annotations

import json

from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient

RENAMED_RESPONSE = {"name": "crop (1).png", "subfolder": "venho/run-example/attempt-1", "type": "input"}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_upload_uses_server_returned_name_not_requested_name(monkeypatch) -> None:
    """GW-E9: ComfyUI can rename on collision when overwrite=false. The
    adapter must bind using the RESPONSE's name, never the requested
    filename (v2.0 PHẦN 12.3 #6)."""
    captured_request = {}

    def fake_urlopen(request, timeout=None):
        captured_request["url"] = request.full_url
        captured_request["body_contains_overwrite_false"] = b'name="overwrite"' in request.data and b"false" in request.data
        return _FakeResponse(RENAMED_RESPONSE)

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)

    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")
    ref = client.upload_image(b"fake-png-bytes", "crop.png", run_id="run-example", attempt_id="attempt-1")

    assert ref.name == "crop (1).png"  # NOT "crop.png"
    assert ref.qualified_name == "venho/run-example/attempt-1/crop (1).png"
    assert captured_request["body_contains_overwrite_false"]


def test_upload_namespaces_by_run_and_attempt(monkeypatch) -> None:
    def fake_urlopen(request, timeout=None):
        assert b"venho/run-a/attempt-9" in request.data
        return _FakeResponse({"name": "mask.png", "subfolder": "venho/run-a/attempt-9", "type": "input"})

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", fake_urlopen)
    client = ComfyUIHttpClient(base_url="http://venho-gpu-win:8188")
    ref = client.upload_image(b"x", "mask.png", run_id="run-a", attempt_id="attempt-9")
    assert ref.subfolder == "venho/run-a/attempt-9"

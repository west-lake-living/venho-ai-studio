from __future__ import annotations

import time
from urllib.error import URLError

import pytest

from identity_restoration.domain.errors import RestorationError
from identity_restoration.infrastructure.comfyui.http_client import ComfyUIHttpClient


def test_dead_worker_connection_maps_to_canonical_error_without_waiting(monkeypatch) -> None:
    """GW-P5-T2: a refused worker connection must fail fast and be observable."""

    def refused(*args, **kwargs):
        raise URLError(ConnectionRefusedError("connection refused"))

    monkeypatch.setattr("identity_restoration.infrastructure.comfyui.http_client.urlopen", refused)
    client = ComfyUIHttpClient(base_url="http://127.0.0.1:1", timeout_s=30)

    started = time.perf_counter()
    with pytest.raises(RestorationError) as exc_info:
        client.submit_prompt({"1": {}})
    elapsed = time.perf_counter() - started

    assert exc_info.value.code == "ERR_GW_WORKER_OFFLINE"
    assert exc_info.value.retryable is True
    assert elapsed < 1.0


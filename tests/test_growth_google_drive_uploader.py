from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from shared.storage import google_drive as drive_module
from shared.storage.google_drive import GoogleDriveUploader, MockDriveUploader, google_drive_uploader_from_env


def test_mock_uploader_records_calls_and_returns_stable_url(tmp_path: Path) -> None:
    uploader = MockDriveUploader()
    file_path = tmp_path / "generated.png"
    file_path.write_bytes(b"fake-png-bytes")

    url = uploader.upload_and_publish(file_path, folder_path=["monday", "pkg-1"])

    assert url.startswith("https://drive.google.com/")
    assert uploader.uploads == [
        {"file_path": str(file_path), "folder_path": ["monday", "pkg-1"], "mimetype": "image/png"}
    ]


def test_google_drive_uploader_from_env_returns_mock_when_token_missing() -> None:
    uploader = google_drive_uploader_from_env({})
    assert isinstance(uploader, MockDriveUploader)


def test_google_drive_uploader_from_env_returns_mock_when_token_blank() -> None:
    uploader = google_drive_uploader_from_env({"GOOGLE_DRIVE_TOKEN_JSON": ""})
    assert isinstance(uploader, MockDriveUploader)


def test_drive_uploader_retries_transient_tls_eof(monkeypatch, tmp_path: Path) -> None:
    uploader = object.__new__(GoogleDriveUploader)
    calls = {"count": 0}
    sleeps: list[float] = []

    def upload_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("SSLEOFError: EOF occurred in violation of protocol")
        return "https://drive.google.com/uc?export=download&id=fresh-image"

    monkeypatch.setattr(uploader, "_upload_and_publish_once", upload_once)
    monkeypatch.setattr(drive_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(drive_module.random, "uniform", lambda start, end: 0.25)

    assert uploader.upload_and_publish(tmp_path / "image.png", folder_path=["monday", "pkg"]) == "https://drive.google.com/uc?export=download&id=fresh-image"
    assert calls["count"] == 2
    assert sleeps == [1.25]


def test_drive_uploader_does_not_retry_invalid_credentials(monkeypatch, tmp_path: Path) -> None:
    uploader = object.__new__(GoogleDriveUploader)
    calls = {"count": 0}

    def upload_once(*args, **kwargs):
        calls["count"] += 1
        raise RuntimeError("403 insufficient permissions")

    monkeypatch.setattr(uploader, "_upload_and_publish_once", upload_once)
    try:
        uploader.upload_and_publish(tmp_path / "image.png", folder_path=["monday", "pkg"])
    except RuntimeError as exc:
        assert "403" in str(exc)
    else:
        raise AssertionError("invalid credentials must fail immediately")
    assert calls["count"] == 1


def test_expired_token_uses_secret_client_config_before_refresh() -> None:
    """Regression: google-auth credentials do not allow client_id assignment."""
    token_json = json.dumps(
        {
            "token": "expired-access-token",
            "refresh_token": "refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "expiry": "2000-01-01T00:00:00Z",
        }
    )

    with patch("google.oauth2.credentials.Credentials.refresh") as refresh, patch(
        "googleapiclient.discovery.build"
    ) as build:
        GoogleDriveUploader(
            token_json=token_json,
            client_id="client-id-from-secret",
            client_secret="client-secret-from-secret",
        )

    credentials = build.call_args.kwargs["credentials"]
    assert credentials.client_id == "client-id-from-secret"
    assert credentials.client_secret == "client-secret-from-secret"
    refresh.assert_called_once()

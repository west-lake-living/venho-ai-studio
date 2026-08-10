from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

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

from __future__ import annotations

from pathlib import Path

from shared.storage.google_drive import MockDriveUploader, google_drive_uploader_from_env


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

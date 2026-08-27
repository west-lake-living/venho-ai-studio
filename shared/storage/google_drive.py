from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol


class DriveUploader(Protocol):
    def upload_and_publish(self, file_path: Path, *, folder_path: list[str], mimetype: str = "image/png") -> str: ...


@dataclass
class MockDriveUploader:
    """Default in tests and until GOOGLE_DRIVE_TOKEN_JSON is configured --
    0 network calls, no google-api-python-client dependency required to
    import this module or run the test suite.
    """

    uploads: list[dict[str, Any]] = field(default_factory=list)

    def upload_and_publish(self, file_path: Path, *, folder_path: list[str], mimetype: str = "image/png") -> str:
        record = {"file_path": str(file_path), "folder_path": list(folder_path), "mimetype": mimetype}
        self.uploads.append(record)
        return f"https://drive.google.com/uc?export=download&id=mock-{file_path.stem}"


class GoogleDriveUploader:
    """Real Google Drive uploader for images the Growth Agent generates that
    need a public URL for Make.com's "HTTP: Get a file" step to fetch before
    posting to Facebook/Instagram.

    Reuses the exact same OAuth token contract as the legacy
    `venho-social-content-agent/google_drive.py` (`GOOGLE_DRIVE_TOKEN_JSON` --
    a full `authorized_user`-format token JSON blob, refreshed silently via
    `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`) so Harry can point
    the same Google Cloud OAuth app + a freshly minted token at this repo's
    GitHub Actions secrets instead of provisioning a second app. See that
    repo's `google_drive.py` docstring for the one-time
    `python3 google_drive.py` local browser-consent flow that produces the
    token JSON to paste into `GOOGLE_DRIVE_TOKEN_JSON`.

    google-api-python-client / google-auth imports are deferred into
    __init__ (not module level) so the rest of this repo's 0-API-call test
    suite never needs those packages installed unless this class is actually
    instantiated (matches `image_studio_runtime`'s provider pattern).
    """

    def __init__(
        self,
        *,
        token_json: str,
        client_id: str | None = None,
        client_secret: str | None = None,
        root_folder: str = "VenhoGrowthAgentV3.1",
    ) -> None:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        info = json.loads(token_json)
        # Credentials exposes client_id/client_secret as read-only properties.
        # Put the GitHub secret values in the authorized-user payload before
        # constructing credentials, so an expired token can be refreshed.
        credential_info = dict(info)
        if client_id:
            credential_info["client_id"] = client_id
        if client_secret:
            credential_info["client_secret"] = client_secret
        scopes = credential_info.get("scopes") or ["https://www.googleapis.com/auth/drive.file"]
        creds = Credentials.from_authorized_user_info(credential_info, scopes)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise RuntimeError(
                    "GOOGLE_DRIVE_TOKEN_JSON is invalid/expired and has no refresh_token -- "
                    "re-run the local google_drive.py consent flow and update the secret."
                )
        self._service = build("drive", "v3", credentials=creds)
        self._root_folder = root_folder

    def _get_or_create_folder(self, name: str, parent_id: str | None) -> str:
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = self._service.files().list(q=query, fields="files(id)").execute()
        existing = results.get("files", [])
        if existing:
            return existing[0]["id"]
        meta: dict[str, Any] = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            meta["parents"] = [parent_id]
        return self._service.files().create(body=meta, fields="id").execute()["id"]

    @staticmethod
    def _is_transient_upload_error(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None) or getattr(getattr(exc, "resp", None), "status", None)
        if status in {408, 429, 500, 502, 503, 504}:
            return True
        message = str(exc).lower()
        return any(token in message for token in ("ssleoferror", "eof occurred", "ssl", "timeout", "timed out", "connection reset", "temporarily unavailable"))

    def _upload_and_publish_once(self, file_path: Path, *, folder_path: list[str], mimetype: str) -> str:
        from googleapiclient.http import MediaFileUpload

        parent_id: str | None = None
        for segment in [self._root_folder, *folder_path]:
            parent_id = self._get_or_create_folder(segment, parent_id)
        media = MediaFileUpload(str(file_path), mimetype=mimetype, resumable=False)
        created = (
            self._service.files()
            .create(body={"name": file_path.name, "parents": [parent_id]}, media_body=media, fields="id")
            .execute()
        )
        file_id = created["id"]
        # "anyone with the link can view" -- required for Make.com's HTTP
        # module (no Google auth) to fetch the bytes before posting.
        self._service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()
        return f"https://drive.google.com/uc?export=download&id={file_id}"

    def upload_and_publish(self, file_path: Path, *, folder_path: list[str], mimetype: str = "image/png") -> str:
        """Retry transient Drive transport failures before allowing fallback.

        A short TLS EOF during GitHub Actions previously caused an otherwise
        valid generated image to be discarded and a rotated fallback reused.
        Auth/permission errors still fail immediately so no invalid token is
        hidden behind retries.
        """
        attempts = 3
        for attempt in range(attempts):
            try:
                return self._upload_and_publish_once(file_path, folder_path=folder_path, mimetype=mimetype)
            except Exception as exc:
                if not self._is_transient_upload_error(exc) or attempt == attempts - 1:
                    raise
                delay = 2**attempt + random.uniform(0.0, 0.5)
                time.sleep(delay)
        raise AssertionError("unreachable")


def google_drive_uploader_from_env(env: Mapping[str, str]) -> "GoogleDriveUploader | MockDriveUploader":
    """Real uploader if GOOGLE_DRIVE_TOKEN_JSON is set, else the disabled/dev-safe Mock."""
    token_json = env.get("GOOGLE_DRIVE_TOKEN_JSON")
    if not token_json:
        return MockDriveUploader()
    return GoogleDriveUploader(
        token_json=token_json,
        client_id=env.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=env.get("GOOGLE_OAUTH_CLIENT_SECRET"),
    )

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Protocol

from PIL import Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover - optional where HEIC is not used
    pass


_FILE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_IMAGE_MIMES = {"image/jpeg", "image/png", "image/heic", "image/heif"}
MAX_DRIVE_IMAGE_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class DriveImage:
    file_id: str
    name: str
    mime_type: str
    data: bytes
    sha256: str


class DriveImageReader(Protocol):
    def read(self, file_id: str) -> DriveImage: ...


class DriveImageLibrary:
    """Read only explicitly allowlisted Drive image IDs; never list/search Drive."""

    def __init__(self, allowlist: Mapping[str, tuple[str, ...]], reader: DriveImageReader | None) -> None:
        normalized: dict[str, tuple[str, ...]] = {}
        seen: set[str] = set()
        for reference_id, file_ids in allowlist.items():
            if not isinstance(reference_id, str) or not reference_id.strip():
                raise ValueError("image library reference IDs must be non-empty strings")
            if not isinstance(file_ids, tuple):
                raise ValueError("image library file IDs must be tuples")
            ids: list[str] = []
            for file_id in file_ids:
                if not isinstance(file_id, str) or _FILE_ID.fullmatch(file_id) is None:
                    raise ValueError("image library contains an invalid Drive file ID")
                ids.append(file_id)
                seen.add(file_id)
            normalized[reference_id] = tuple(dict.fromkeys(ids))
        self.allowlist = normalized
        self.reader = reader
        self.allowed_file_ids = frozenset(seen)

    @classmethod
    def from_yaml(cls, path: Path, env: Mapping[str, str]) -> "DriveImageLibrary":
        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("image library config version must be 1")
        raw_allowlist = payload.get("allowlist", {})
        if not isinstance(raw_allowlist, dict):
            raise ValueError("image library allowlist must be a mapping")
        allowlist: dict[str, tuple[str, ...]] = {}
        for reference_id, value in raw_allowlist.items():
            if not isinstance(value, list):
                raise ValueError("image library allowlist entries must be lists")
            allowlist[str(reference_id)] = tuple(value)
        reader = GoogleDriveImageReader.from_env(env) if any(allowlist.values()) else None
        return cls(allowlist, reader)

    def resolve(self, reference_id: str, rotation_key: str, rotation_offset: int = 0) -> DriveImage | None:
        file_ids = self.allowlist.get(reference_id, ())
        if not file_ids:
            return None
        if self.reader is None:
            raise RuntimeError("Google Drive image library is configured but its reader credentials are unavailable")
        try:
            rotation = date.fromisoformat(rotation_key).toordinal()
        except ValueError:
            rotation = int.from_bytes(hashlib.sha256(rotation_key.encode("utf-8")).digest()[:4], "big")
        file_id = file_ids[(rotation + rotation_offset) % len(file_ids)]
        return self.read_allowlisted(file_id)

    def read_allowlisted(self, file_id: str) -> DriveImage:
        if file_id not in self.allowed_file_ids:
            raise ValueError("Drive image file ID is not on the configured allowlist")
        if self.reader is None:
            raise RuntimeError("Google Drive image library reader credentials are unavailable")
        image = self.reader.read(file_id)
        if image.file_id != file_id:
            raise ValueError("Google Drive returned a different file ID")
        if image.mime_type not in _IMAGE_MIMES:
            raise ValueError("allowlisted Drive file is not a supported image")
        if not image.data or len(image.data) > MAX_DRIVE_IMAGE_BYTES:
            raise ValueError("allowlisted Drive image is empty or exceeds 25 MiB")
        digest = hashlib.sha256(image.data).hexdigest()
        if image.sha256 != digest:
            raise ValueError("Google Drive image SHA-256 does not match its bytes")
        try:
            with Image.open(io.BytesIO(image.data)) as source:
                source.verify()
        except Exception as error:
            raise ValueError("allowlisted Drive file is not a decodable image") from error
        return image

    def read_for_reference(self, reference_id: str, file_id: str) -> DriveImage:
        if file_id not in self.allowlist.get(reference_id, ()):
            raise ValueError("Drive image file ID is not allowlisted for the selected reference asset")
        return self.read_allowlisted(file_id)


class GoogleDriveImageReader:
    """Google Drive v3 adapter using the legacy authorized-user token contract."""

    def __init__(self, service: Any) -> None:
        self._service = service

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "GoogleDriveImageReader | None":
        token_json = str(env.get("GOOGLE_DRIVE_TOKEN_JSON", "")).strip()
        if not token_json:
            return None
        try:
            credentials_info = json.loads(token_json)
            if not isinstance(credentials_info, dict):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise ValueError("GOOGLE_DRIVE_TOKEN_JSON must be an authorized-user JSON document") from None
        credentials_info = dict(credentials_info)
        if env.get("GOOGLE_OAUTH_CLIENT_ID"):
            credentials_info["client_id"] = env["GOOGLE_OAUTH_CLIENT_ID"]
        if env.get("GOOGLE_OAUTH_CLIENT_SECRET"):
            credentials_info["client_secret"] = env["GOOGLE_OAUTH_CLIENT_SECRET"]
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            credentials = Credentials.from_authorized_user_info(
                credentials_info,
                ["https://www.googleapis.com/auth/drive.file"],
            )
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                else:
                    raise ValueError
            return cls(build("drive", "v3", credentials=credentials, cache_discovery=False))
        except Exception as error:
            # Credential internals and Google error details must never reach logs.
            raise RuntimeError("Google Drive image reader could not initialize") from error

    def read(self, file_id: str) -> DriveImage:
        try:
            metadata = self._service.files().get(
                fileId=file_id,
                fields="id,name,mimeType,size,trashed",
                supportsAllDrives=True,
            ).execute()
        except Exception as error:
            raise DriveImageReadError("ERR_GC2_DRIVE_METADATA", "Could not read allowlisted Drive image metadata.") from error
        if metadata.get("id") != file_id or metadata.get("trashed") is True:
            raise ValueError("allowlisted Google Drive image is missing or trashed")
        mime_type = str(metadata.get("mimeType") or "")
        size_value = metadata.get("size")
        try:
            size = int(size_value)
        except (TypeError, ValueError):
            raise ValueError("Google Drive image size is unavailable") from None
        if mime_type not in _IMAGE_MIMES or size <= 0 or size > MAX_DRIVE_IMAGE_BYTES:
            raise ValueError("Google Drive image metadata is outside the accepted bounds")
        try:
            data = self._service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True,
            ).execute()
        except Exception as error:
            raise DriveImageReadError("ERR_GC2_DRIVE_DOWNLOAD", "Could not download allowlisted Drive image bytes.") from error
        if not isinstance(data, bytes):
            raise ValueError("Google Drive image download returned an invalid body")
        return DriveImage(
            file_id=file_id,
            name=str(metadata.get("name") or "drive-image"),
            mime_type=mime_type,
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
        )


class DriveImageReadError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.public_message = message
        super().__init__(message)

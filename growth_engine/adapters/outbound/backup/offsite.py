from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from growth_engine.adapters.outbound.backup.sqlite_backup import (
    AgeSubprocess,
    staged_backups,
    staging_directory,
)

CONFIG = Path("config/projects/venho_hotel/growth_engine/backup_offsite.json")
MAX_OFFSITE_AGE_MS = 26 * 3_600_000
MAX_LOCAL_AGE_MS = 3_600_000
FILE_NAME = re.compile(r"gc2-(\d{13})\.tar\.gz\.age", re.ASCII)
DRIVE_ID = re.compile(r"[A-Za-z0-9_-]{1,150}")
SHA256 = re.compile(r"[0-9a-f]{64}")
MD5 = re.compile(r"[0-9a-f]{32}")
MARKER = "venho-gc2-offsite-v1"
FOLDER_NAME = "VENHO GC2 Backups"
FOLDER_MIME = "application/vnd.google-apps.folder"
FIELDS = "id,name,parents,trashed,appProperties,size,md5Checksum,sha256Checksum"


class OffsiteError(ValueError):
    pass


class Drive(Protocol):
    def check_folder(self, folder: str) -> None: ...
    def upload(self, folder: str, source: Path, name: str, props: dict) -> dict: ...
    def get(self, file_id: str) -> dict: ...
    def mark_verified(self, file_id: str) -> None: ...
    def list(self, folder: str, owner: str) -> list[dict]: ...
    def trash(self, file_id: str) -> None: ...


def load_recipient(root: Path) -> tuple[str, str]:
    try:
        config = json.loads((root / CONFIG).read_text())
        recipient, checksum = config["recipient"], config["recipient_sha256"]
        if (not re.fullmatch(r"age1[023456789acdefghjklmnpqrstuvwxyz]{58}", recipient)
            or hashlib.sha256(recipient.encode("ascii")).hexdigest() != checksum):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError):
        raise OffsiteError("offsite_recipient_config_invalid") from None
    return recipient, checksum


def check_recipient(recipient: str) -> None:
    if not shutil.which("age"):
        raise OffsiteError("offsite_age_cli_missing")
    # Let age validate the actual Bech32 checksum and key encoding.
    try:
        subprocess.run(["age", "-r", recipient], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise OffsiteError("offsite_recipient_rejected_by_age") from None


def folder_id() -> str:
    value = os.environ.get("GE_BACKUP_DRIVE_FOLDER_ID", "")
    if not DRIVE_ID.fullmatch(value) or value == "root":
        raise OffsiteError("offsite_drive_folder_missing_or_invalid")
    return value


def _state_dir(db: Path) -> Path:
    return db.parent / "backup-offsite"


def _write_json(path: Path, value: dict) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".offsite-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def _lock(path: Path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _props(owner: str, sha256: str, md5: str) -> dict:
    return {"gc2Tool": MARKER, "gc2Owner": owner, "gc2CipherSha256": sha256, "gc2CipherMd5": md5}


def _owned(row: dict, folder: str, owner: str, *, verified: bool = True) -> bool:
    props = row.get("appProperties") or {}
    if not isinstance(props, dict):
        return False
    file_id = row.get("id") or ""
    sha = props.get("gc2CipherSha256") or ""
    md5 = props.get("gc2CipherMd5") or ""
    expected = _props(owner, sha, md5)
    if verified:
        expected["gc2FileId"] = file_id
    size = str(row.get("size", ""))
    return (
        bool(DRIVE_ID.fullmatch(file_id))
        and bool(FILE_NAME.fullmatch(row.get("name") or ""))
        and row.get("parents") == [folder]
        and row.get("trashed") is False
        and props == expected
        and bool(SHA256.fullmatch(sha))
        and (not row.get("sha256Checksum") or row["sha256Checksum"] == sha)
        and bool(MD5.fullmatch(md5))
        and row.get("md5Checksum") == md5
        and bool(re.fullmatch(r"[1-9][0-9]{0,19}", size))
    )


def _checksums(path: Path) -> tuple[str, str, int]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
            size += len(block)
    return md5.hexdigest(), sha256.hexdigest(), size


def _matches(row: dict, receipt: dict, folder: str, *, verified: bool = True) -> bool:
    return (
        _owned(row, folder, receipt["owner"], verified=verified)
        and row["id"] == receipt["file_id"]
        and row["name"] == receipt["name"]
        and row["appProperties"]["gc2CipherSha256"] == receipt["sha256"]
        and row["md5Checksum"] == receipt["md5"]
        and int(row["size"]) == receipt["size"]
    )


def _retain(drive: Drive, folder: str, owner: str, current: str) -> int:
    rows = sorted(
        (row for row in drive.list(folder, owner) if _owned(row, folder, owner)),
        key=lambda row: (row["name"], row["id"] == current, row["id"]), reverse=True,
    )
    local = ZoneInfo("Asia/Ho_Chi_Minh")
    keep = {current}
    for limit, bucket in ((14, lambda dt: dt.date()), (8, lambda dt: dt.isocalendar()[:2])):
        seen = set()
        for row in rows:
            when = datetime.fromtimestamp(int(FILE_NAME.fullmatch(row["name"])[1]) / 1000, local)
            key = bucket(when)
            if key not in seen:
                seen.add(key)
                keep.add(row["id"])
                if len(seen) >= limit:
                    break
    pruned = 0
    for row in rows:
        if row["id"] not in keep:
            # Recheck the direct parent and marker immediately before trashing.
            latest = drive.get(row["id"])
            if latest == row and _owned(latest, folder, owner):
                drive.trash(row["id"])
                pruned += 1
    return pruned


def receipt_status(db: Path, recipient_sha: str, now_ms: int) -> tuple[dict | None, str]:
    try:
        receipt = json.loads((_state_dir(db) / "latest.json").read_text())
        match = FILE_NAME.fullmatch(receipt["name"])
        if (
            receipt["folder_sha256"] != hashlib.sha256(folder_id().encode()).hexdigest()
            or receipt["recipient_sha256"] != recipient_sha
            or receipt["checksum_verified"] is not True
            or not match or int(match[1]) != receipt["snapshot_at_ms"]
            or not DRIVE_ID.fullmatch(receipt["file_id"])
            or not re.fullmatch(r"[0-9a-f]{32}", receipt["owner"])
            or not SHA256.fullmatch(receipt["sha256"]) or not MD5.fullmatch(receipt["md5"])
            or type(receipt["size"]) is not int or receipt["size"] <= 0
            or not receipt["snapshot_at_ms"] <= receipt["verified_at_ms"] <= now_ms
        ):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        return None, "offsite_receipt_missing_or_invalid"
    age = now_ms - receipt["snapshot_at_ms"]
    if not 0 <= age < MAX_OFFSITE_AGE_MS:
        return None, "offsite_backup_at_least_26_hours_old"
    return receipt, "offsite_checksum_verified"


def require_fresh_remote(
    db: Path, root: Path, clock: Callable[[], int], drive_factory: Callable[[], Drive],
) -> dict:
    _, checksum = load_recipient(root)
    receipt, reason = receipt_status(db, checksum, clock())
    if receipt is None:
        raise OffsiteError(reason)
    folder = folder_id()
    try:
        drive = drive_factory()
        drive.check_folder(folder)
        matches = _matches(drive.get(receipt["file_id"]), receipt, folder)
    except Exception:
        raise OffsiteError("offsite_remote_verification_failed") from None
    if not matches:
        raise OffsiteError("offsite_remote_checksum_or_metadata_mismatch")
    if not 0 <= clock() - receipt["snapshot_at_ms"] < MAX_OFFSITE_AGE_MS:
        raise OffsiteError("offsite_backup_at_least_26_hours_old")
    return receipt


def upload_latest(
    db: Path, root: Path, drive_factory: Callable[[], Drive],
    *, encrypt: Callable[[Path, Path, str], None] = AgeSubprocess().encrypt,
    clock: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
    alert: Callable[[str], None] | None = None,
) -> dict:
    state = _state_dir(db)
    state.mkdir(mode=0o700, exist_ok=True)
    if state.is_symlink() or state.stat().st_uid != os.getuid():
        raise OffsiteError("offsite_state_directory_invalid")
    state.chmod(0o700)
    with _lock(state / ".lock"):
        alert_marker = state / "failure.json"
        try:
            result = _upload(db, root, state, drive_factory, encrypt, clock)
        except OffsiteError as error:
            if alert and not alert_marker.exists():
                # Claim the episode before sending so an ambiguous Telegram reply cannot duplicate it.
                _write_json(alert_marker, {"reason": str(error), "at_ms": clock()})
                try:
                    alert(f"GC2 production: backup offsite FAIL ({error}).")
                except Exception:
                    raise OffsiteError(f"{error}_telegram_alert_failed") from None
            raise
        alert_marker.unlink(missing_ok=True)
        return result


def _upload(db: Path, root: Path, state: Path, drive_factory, encrypt, clock) -> dict:
    recipient, recipient_sha = load_recipient(root)
    folder = folder_id()
    owner_file = state / "owner.json"
    try:
        if not owner_file.exists():
            _write_json(owner_file, {"id": uuid4().hex})
        owner = json.loads(owner_file.read_text())["id"]
        if not re.fullmatch(r"[0-9a-f]{32}", owner):
            raise ValueError
    except (OSError, ValueError, TypeError, KeyError):
        raise OffsiteError("offsite_owner_state_invalid") from None

    staging = staging_directory(db)
    if not staging.is_dir() or staging.is_symlink():
        raise OffsiteError("offsite_local_snapshot_missing_or_stale")
    with tempfile.TemporaryDirectory(dir=state, prefix=".encrypted-") as temp:
        cipher = Path(temp) / "backup.age"
        with _lock(staging / ".lock"):
            copies = staged_backups(staging)
            if not copies or not 0 <= clock() - copies[0][0] < MAX_LOCAL_AGE_MS:
                raise OffsiteError("offsite_local_snapshot_missing_or_stale")
            stamp, source = copies[0]
            try:
                encrypt(source, cipher, recipient)
                md5, sha, size = _checksums(cipher)
                if size == 0:
                    raise ValueError
            except Exception:
                raise OffsiteError("offsite_encryption_failed") from None

        name = source.name + ".age"
        try:
            drive = drive_factory()
            drive.check_folder(folder)
            created = drive.upload(folder, cipher, name, _props(owner, sha, md5))
            remote = drive.get(created["id"])
        except OffsiteError:
            raise
        except Exception:
            raise OffsiteError("offsite_drive_upload_failed") from None
        receipt = {
            "file_id": created["id"], "name": name, "owner": owner, "md5": md5, "sha256": sha,
            "size": size, "recipient_sha256": recipient_sha, "snapshot_at_ms": stamp,
            "folder_sha256": hashlib.sha256(folder.encode()).hexdigest(), "verified_at_ms": clock(),
            "checksum_verified": True,
        }
        if not _matches(remote, receipt, folder, verified=False):
            raise OffsiteError("offsite_drive_checksum_or_metadata_mismatch")
        try:
            drive.mark_verified(receipt["file_id"])
            remote = drive.get(receipt["file_id"])
        except Exception:
            raise OffsiteError("offsite_drive_verification_record_failed") from None
        if not _matches(remote, receipt, folder):
            raise OffsiteError("offsite_drive_checksum_or_metadata_mismatch")
        try:
            pruned = _retain(drive, folder, owner, receipt["file_id"])
        except Exception:
            raise OffsiteError("offsite_drive_retention_failed") from None
        _write_json(state / "latest.json", receipt)
        return {"result": "PASS", "snapshot": name, "checksum": "PASS", "md5": md5,
                "sha256": sha, "retention_trashed": pruned}


class GoogleDrive:
    def __init__(self, service) -> None:
        self.service = service

    @classmethod
    def from_env(cls):
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        try:
            info = json.loads(os.environ["GOOGLE_DRIVE_TOKEN_JSON"])
            if info.get("type", "authorized_user") != "authorized_user":
                raise ValueError
            for field, key in (("client_id", "GOOGLE_OAUTH_CLIENT_ID"), ("client_secret", "GOOGLE_OAUTH_CLIENT_SECRET")):
                if os.environ.get(key):
                    info[field] = os.environ[key]
            scopes = info.get("scopes") or ["https://www.googleapis.com/auth/drive.file"]
            credentials = Credentials.from_authorized_user_info(info, scopes=scopes)
            # HTTP library diagnostics can contain resumable session URLs.
            logging.getLogger("googleapiclient").setLevel(logging.CRITICAL)
            logging.getLogger("google_auth_httplib2").setLevel(logging.CRITICAL)
            return cls(build("drive", "v3", http=AuthorizedHttp(credentials, http=httplib2.Http(timeout=60)),
                             cache_discovery=False))
        except Exception:
            raise OffsiteError("offsite_drive_oauth_unavailable") from None

    def create_folder(self) -> str:
        # A folder created by this OAuth client is accessible with drive.file.
        query = (
            f"name = '{FOLDER_NAME}' and mimeType = '{FOLDER_MIME}' and "
            "trashed = false and 'root' in parents and "
            f"appProperties has {{key='gc2Tool' and value='{MARKER}'}}"
        )
        page = self.service.files().list(q=query, fields="nextPageToken,incompleteSearch,files(id)").execute()
        folders = page.get("files", [])
        if len(folders) > 1 or page.get("nextPageToken") or page.get("incompleteSearch"):
            raise OffsiteError("offsite_drive_folder_ambiguous")
        if folders:
            return folders[0]["id"]
        row = self.service.files().create(
            body={"name": FOLDER_NAME, "mimeType": FOLDER_MIME, "appProperties": {"gc2Tool": MARKER}}, fields="id",
        ).execute()
        return row["id"]

    def check_folder(self, folder: str) -> None:
        row = self.service.files().get(fileId=folder, fields="name,mimeType,trashed,capabilities(canAddChildren)").execute()
        if (row.get("name") != FOLDER_NAME or row.get("mimeType") != FOLDER_MIME
            or row.get("trashed") is not False or not row.get("capabilities", {}).get("canAddChildren")):
            raise OffsiteError("offsite_dedicated_folder_required")

    def upload(self, folder: str, source: Path, name: str, props: dict) -> dict:
        from googleapiclient.http import MediaFileUpload

        media = MediaFileUpload(str(source), mimetype="application/octet-stream", chunksize=8 * 1024 * 1024, resumable=True)
        try:
            req = self.service.files().create(
                body={"name": name, "parents": [folder], "appProperties": props},
                media_body=media, fields="id",
            )
            result = None
            while result is None:
                _, result = req.next_chunk(num_retries=3)
            return result
        finally:
            media.stream().close()

    def get(self, file_id: str) -> dict:
        return self.service.files().get(fileId=file_id, fields=FIELDS).execute(num_retries=3)

    def list(self, folder: str, owner: str) -> list[dict]:
        query = f"'{folder}' in parents and trashed = false and appProperties has {{key='gc2Owner' and value='{owner}'}}"
        rows = []
        token = None
        while True:
            page = self.service.files().list(q=query, fields=f"nextPageToken,incompleteSearch,files({FIELDS})",
                                             pageSize=100, pageToken=token).execute(num_retries=3)
            if page.get("incompleteSearch"):
                raise OffsiteError("offsite_drive_list_incomplete")
            rows.extend(page.get("files", []))
            token = page.get("nextPageToken")
            if not token:
                return rows

    def mark_verified(self, file_id: str) -> None:
        self.service.files().update(
            fileId=file_id, body={"appProperties": {"gc2FileId": file_id}}, fields="id",
        ).execute(num_retries=3)

    def trash(self, file_id: str) -> None:
        self.service.files().update(fileId=file_id, body={"trashed": True}, fields="id").execute()

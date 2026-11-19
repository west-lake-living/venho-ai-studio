from __future__ import annotations

import hashlib
import io
import os
import re
import stat
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Mapping

from PIL import Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover - optional if no HEIC photos are configured
    pass


_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
MAX_LEGACY_IMAGE_BYTES = 25 * 1024 * 1024
MAX_LEGACY_IMAGE_PIXELS = 50_000_000
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|client[_-]?secret|password)"
    r"(\s*[:=]\s*|\s+)([^\s,;]+)"
)
_URL = re.compile(r"https?://[^\s\])}>,]+", re.IGNORECASE)
_LONG_SECRET = re.compile(r"\b[A-Za-z0-9_-]{48,}\b")
_API_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|EAA[A-Za-z0-9_-]{16,}|ya29\.[A-Za-z0-9._-]{16,})\b")


@dataclass(frozen=True)
class LocalLegacyImage:
    relative_path: str
    sha256: str
    mime_type: str
    data: bytes

    @property
    def name(self) -> str:
        return PurePosixPath(self.relative_path).name


@dataclass(frozen=True)
class LegacyImageIssue:
    reference_id: str
    relative_path: str
    code: str
    message: str

    def render(self) -> str:
        return f"{self.code}: {self.message}; group={self.reference_id}; file={self.relative_path}"


@dataclass(frozen=True)
class LegacyImageGroupStatus:
    reference_id: str
    valid_count: int
    issues: tuple[LegacyImageIssue, ...]

    @property
    def excluded_count(self) -> int:
        return len(self.issues)


class LegacyImageValidationError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        reference_id: str | None = None,
        relative_path: str | None = None,
        issues: tuple[LegacyImageIssue, ...] = (),
    ) -> None:
        self.code = code
        safe_message = _redact_public_message(message)
        self.reference_id = reference_id
        self.relative_path = relative_path
        self.issues = issues
        details = [safe_message]
        if reference_id:
            details.append(f"group={reference_id}")
        if relative_path:
            details.append(f"file={relative_path}")
        details.extend(issue.render() for issue in issues)
        self.public_message = _redact_public_message("; ".join(details))
        super().__init__(f"{code}: {self.public_message}")


class UnsupportedLegacyImageError(LegacyImageValidationError):
    """A candidate file is corrupt or its detected format is unsupported."""


class LocalLegacyImageLibrary:
    """Read hash-pinned photos under the legacy assets root without following symlinks."""

    def __init__(self, root: Path, allowlist: Mapping[str, tuple[Mapping[str, str], ...]]) -> None:
        self.root = Path(os.path.abspath(Path(root).expanduser()))
        _reject_symlink_components(self.root, allow_missing=True)
        if self.root.exists() and not self.root.is_dir():
            raise ValueError("legacy image root is not a directory")
        normalized: dict[str, tuple[dict[str, str], ...]] = {}
        for reference_id, entries in allowlist.items():
            if not isinstance(reference_id, str) or not reference_id.strip():
                raise ValueError("legacy image reference IDs must be non-empty")
            if not isinstance(entries, tuple):
                raise ValueError("legacy image allowlist groups must be tuples")
            normalized[reference_id] = tuple(self._normalize_entry(entry) for entry in entries)
        self.allowlist = normalized

    @classmethod
    def from_yaml(cls, path: Path, *, root: Path) -> "LocalLegacyImageLibrary":
        import yaml

        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise ValueError("legacy image library config version must be 1")
        if payload.get("source") != "local_legacy_library":
            raise ValueError("legacy image library source must be local_legacy_library")
        raw_allowlist = payload.get("allowlist", {})
        if not isinstance(raw_allowlist, dict):
            raise ValueError("legacy image allowlist must be a mapping")
        allowlist: dict[str, tuple[Mapping[str, str], ...]] = {}
        for reference_id, raw_entries in raw_allowlist.items():
            if not isinstance(raw_entries, list):
                raise ValueError("legacy image allowlist entries must be lists")
            allowlist[str(reference_id)] = tuple(raw_entries)
        return cls(root, allowlist)

    @staticmethod
    def _normalize_entry(entry: Mapping[str, str]) -> dict[str, str]:
        if not isinstance(entry, Mapping):
            raise ValueError("legacy image allowlist item must contain path and sha256")
        relative_path = entry.get("path")
        sha256 = entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(sha256, str):
            raise ValueError("legacy image allowlist item must contain path and sha256")
        _validate_relative_path(relative_path)
        if PurePosixPath(relative_path).suffix.lower() not in _IMAGE_SUFFIXES:
            raise ValueError("legacy image allowlist path is not a supported image type")
        if _SHA256.fullmatch(sha256) is None:
            raise ValueError("legacy image allowlist SHA-256 is invalid")
        return {"path": relative_path, "sha256": sha256}

    @property
    def allowed_reference_ids(self) -> frozenset[str]:
        return frozenset(self.allowlist)

    def validate_reference_ids(self, reference_ids: set[str]) -> tuple[LegacyImageIssue, ...]:
        reports = self.inspect_reference_ids(reference_ids)
        for report in reports:
            if not self.allowlist.get(report.reference_id):
                raise LegacyImageValidationError(
                    "ERR_GC2_LEGACY_IMAGE_GROUP_EMPTY",
                    "Nhóm không có ảnh trong allowlist.",
                    reference_id=report.reference_id,
                )
            if report.valid_count == 0:
                raise LegacyImageValidationError(
                    "ERR_GC2_LEGACY_IMAGE_GROUP_NO_VALID_FILES",
                    "Nhóm không còn ảnh hợp lệ sau khi kiểm tra nội dung.",
                    reference_id=report.reference_id,
                    issues=report.issues,
                )
        return tuple(issue for report in reports for issue in report.issues)

    def inspect_reference_ids(self, reference_ids: set[str]) -> tuple[LegacyImageGroupStatus, ...]:
        reports = []
        for reference_id in sorted(reference_ids):
            entries = self.allowlist.get(reference_id, ())
            if not entries:
                reports.append(LegacyImageGroupStatus(reference_id, 0, ()))
                continue
            valid_entries, issues = self._valid_entries(reference_id)
            reports.append(LegacyImageGroupStatus(reference_id, len(valid_entries), issues))
        return tuple(reports)

    def resolve(
        self,
        reference_id: str,
        rotation_key: str,
        rotation_offset: int = 0,
    ) -> LocalLegacyImage | None:
        valid_entries, issues = self._valid_entries(reference_id)
        if not valid_entries:
            if not self.allowlist.get(reference_id):
                return None
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_GROUP_NO_VALID_FILES",
                "Nhóm không còn ảnh hợp lệ sau khi kiểm tra nội dung.",
                reference_id=reference_id,
                issues=issues,
            )
        try:
            rotation = date.fromisoformat(rotation_key).toordinal()
        except ValueError:
            rotation = int.from_bytes(hashlib.sha256(rotation_key.encode("utf-8")).digest()[:4], "big")
        selected = valid_entries[(rotation + rotation_offset) % len(valid_entries)]
        return self.read_for_reference(reference_id, selected["path"], expected_sha256=selected["sha256"])

    def _valid_entries(
        self, reference_id: str
    ) -> tuple[tuple[dict[str, str], ...], tuple[LegacyImageIssue, ...]]:
        entries = self.allowlist.get(reference_id, ())
        if not entries:
            return (), ()
        valid: list[dict[str, str]] = []
        issues: list[LegacyImageIssue] = []
        for entry in entries:
            try:
                self.read_for_reference(reference_id, entry["path"], expected_sha256=entry["sha256"])
            except UnsupportedLegacyImageError as error:
                issues.append(LegacyImageIssue(reference_id, entry["path"], error.code, error.public_message))
            else:
                valid.append(entry)
        return tuple(valid), tuple(issues)

    def read_for_reference(
        self,
        reference_id: str,
        relative_path: str,
        *,
        expected_sha256: str | None = None,
    ) -> LocalLegacyImage:
        entries = self.allowlist.get(reference_id, ())
        entry = next((item for item in entries if item["path"] == relative_path), None)
        if entry is None:
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_NOT_ALLOWLISTED",
                "Đường dẫn không nằm trong allowlist của nhóm.",
                reference_id=reference_id,
                relative_path=relative_path,
            )
        expected = expected_sha256 or entry["sha256"]
        if expected != entry["sha256"]:
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_SHA256_CONFIG",
                "SHA-256 yêu cầu không khớp cấu hình allowlist.",
                reference_id=reference_id,
                relative_path=relative_path,
            )
        try:
            data = _read_beneath_no_symlinks(self.root, relative_path)
        except (OSError, ValueError) as error:
            errno = error.errno if isinstance(error, OSError) else 0
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_READ",
                f"Không thể đọc an toàn ảnh (errno={errno or 0}).",
                reference_id=reference_id,
                relative_path=relative_path,
            ) from None
        if not data or len(data) > MAX_LEGACY_IMAGE_BYTES:
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_SIZE",
                "Ảnh rỗng hoặc vượt giới hạn 25 MiB.",
                reference_id=reference_id,
                relative_path=relative_path,
            )
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != expected:
            raise LegacyImageValidationError(
                "ERR_GC2_LEGACY_IMAGE_SHA256_MISMATCH",
                "Bytes ảnh không khớp SHA-256 đã duyệt.",
                reference_id=reference_id,
                relative_path=relative_path,
            )
        try:
            mime_type = _validate_image(data)
        except UnsupportedLegacyImageError as error:
            raise UnsupportedLegacyImageError(
                error.code,
                error.public_message,
                reference_id=reference_id,
                relative_path=relative_path,
            ) from None
        return LocalLegacyImage(relative_path, actual_sha256, mime_type, data)


def _redact_public_message(message: str) -> str:
    value = _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", message)
    value = _URL.sub("[URL REDACTED]", value)
    value = _API_KEY.sub("[SECRET REDACTED]", value)
    value = _LONG_SECRET.sub("[SECRET REDACTED]", value)
    return " ".join(value.split())[:384]


def _validate_relative_path(value: str) -> tuple[str, ...]:
    if not value or value.startswith("/") or "\\" in value or any(ord(char) < 32 for char in value):
        raise ValueError("legacy image path must be a safe relative POSIX path")
    components = tuple(value.split("/"))
    if any(component in {"", ".", ".."} for component in components):
        raise ValueError("legacy image path contains an unsafe component")
    return components


def _read_beneath_no_symlinks(root: Path, relative_path: str) -> bytes:
    components = _validate_relative_path(relative_path)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    root_fd = _open_absolute_directory_no_symlinks(root, directory_flags, no_follow)
    current_fd = root_fd
    try:
        for component in components[:-1]:
            next_fd = os.open(component, directory_flags | no_follow, dir_fd=current_fd)
            if current_fd != root_fd:
                os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(components[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow, dir_fd=current_fd)
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                raise ValueError("legacy image is not a regular file")
            chunks: list[bytes] = []
            size = 0
            while True:
                chunk = os.read(file_fd, min(1024 * 1024, MAX_LEGACY_IMAGE_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_LEGACY_IMAGE_BYTES:
                    raise ValueError("legacy image exceeds 25 MiB")
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        if current_fd != root_fd:
            os.close(current_fd)
        os.close(root_fd)


def _open_absolute_directory_no_symlinks(root: Path, directory_flags: int, no_follow: int) -> int:
    if not root.is_absolute():
        raise ValueError("legacy image root must be absolute")
    descriptor = os.open(root.anchor, directory_flags | no_follow)
    try:
        for component in root.parts[1:]:
            next_fd = os.open(component, directory_flags | no_follow, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ValueError("legacy image root is not a directory")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _reject_symlink_components(path: Path, *, allow_missing: bool) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current = current / component
        try:
            details = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                break
            raise
        if stat.S_ISLNK(details.st_mode):
            raise ValueError("legacy image root contains a symlink component")


def _validate_image(data: bytes) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image_format = str(image.format or "").upper()
                if image.width * image.height > MAX_LEGACY_IMAGE_PIXELS:
                    raise UnsupportedLegacyImageError(
                        "ERR_GC2_LEGACY_IMAGE_PIXEL_LIMIT",
                        "Ảnh vượt giới hạn 50 triệu pixel.",
                    )
                image.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                if str(decoded.format or "").upper() != image_format:
                    raise UnsupportedLegacyImageError(
                        "ERR_GC2_LEGACY_IMAGE_FORMAT_MISMATCH",
                        "Định dạng giải mã không khớp chữ ký ảnh.",
                    )
                decoded.load()
    except UnsupportedLegacyImageError:
        raise
    except Exception:
        if _looks_like_heif(data):
            try:
                import pillow_heif  # noqa: F401
            except ImportError:
                raise UnsupportedLegacyImageError(
                    "ERR_GC2_LEGACY_IMAGE_HEIF_DECODER_MISSING",
                    "Nội dung là HEIF/HEIC nhưng pillow-heif chưa được cài.",
                ) from None
        raise UnsupportedLegacyImageError(
            "ERR_GC2_LEGACY_IMAGE_INVALID",
            "Bytes không phải ảnh JPEG/PNG/HEIF hợp lệ hoặc ảnh bị hỏng.",
        ) from None
    mime_type = {
        "JPEG": "image/jpeg",
        "MPO": "image/jpeg",
        "PNG": "image/png",
        "HEIC": "image/heic",
        "HEIF": "image/heif",
    }.get(image_format)
    if mime_type is None:
        raise UnsupportedLegacyImageError(
            "ERR_GC2_LEGACY_IMAGE_FORMAT_UNSUPPORTED",
            f"Định dạng ảnh theo nội dung không được hỗ trợ (format={image_format or 'unknown'}).",
        )
    return mime_type


def _looks_like_heif(data: bytes) -> bool:
    if len(data) < 12 or data[4:8] != b"ftyp":
        return False
    return data[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}

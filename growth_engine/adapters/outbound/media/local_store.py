from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Callable

from growth_engine.application.dto import StoredObject

CHUNK_SIZE = 64 * 1024


class MediaStoreError(ValueError):
    pass


@dataclass(frozen=True)
class _WrittenFile:
    sha256: str
    byte_size: int


class LocalMediaStore:
    """Filesystem media store with content-addressed keys and atomic writes."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_original(self, stream: BinaryIO, max_bytes: int) -> StoredObject:
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        target_parent = self.root / "originals"
        target_parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        digest = hashlib.sha256()
        size = 0
        try:
            with tempfile.NamedTemporaryFile(prefix=".tmp-", dir=self.root, delete=False) as output:
                temp_path = Path(output.name)
                while True:
                    chunk = stream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise MediaStoreError("original exceeds max_bytes")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            sha = digest.hexdigest()
            object_key = f"originals/{sha[:2]}/{sha}"
            target = self._path(object_key)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if not self.verify(object_key, sha):
                    raise MediaStoreError("existing original SHA-256 mismatch")
                temp_path.unlink(missing_ok=True)
                temp_path = None
            else:
                os.replace(temp_path, target)
                temp_path = None
                _fsync_directory(target.parent)
            return StoredObject(object_key=object_key, sha256=sha, byte_size=size)
        except OSError as exc:
            raise MediaStoreError("failed to store original atomically") from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def put_variant(self, data: bytes, sha256: str) -> str:
        _validate_sha(sha256)
        actual_sha = hashlib.sha256(data).hexdigest()
        if actual_sha != sha256.lower():
            raise MediaStoreError("variant SHA-256 does not match bytes")
        object_key = f"variants/{actual_sha[:2]}/{actual_sha}.jpg"
        target = self._path(object_key)
        self._atomic_write(target, lambda output: output.write(data))
        return object_key

    def open(self, object_key: str) -> BinaryIO:
        return self._path(object_key).open("rb")

    def verify(self, object_key: str, sha256: str) -> bool:
        _validate_sha(sha256)
        digest = hashlib.sha256()
        try:
            with self.open(object_key) as stream:
                while True:
                    chunk = stream.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    digest.update(chunk)
        except OSError:
            return False
        return digest.hexdigest() == sha256.lower()

    def _atomic_write(self, target: Path, write: Callable[[BinaryIO], object]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".tmp-", dir=target.parent, delete=False) as output:
                temp_path = Path(output.name)
                write(output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temp_path, target)
            temp_path = None
            _fsync_directory(target.parent)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _path(self, object_key: str) -> Path:
        if not isinstance(object_key, str) or not object_key or "\\" in object_key or "\x00" in object_key:
            raise MediaStoreError("invalid object key")
        if any(part in {"", ".", ".."} for part in object_key.split("/")):
            raise MediaStoreError("invalid object key")
        key = PurePosixPath(object_key)
        if key.is_absolute() or not key.parts:
            raise MediaStoreError("invalid object key")
        candidate = (self.root / Path(*key.parts)).resolve()
        if os.path.commonpath((str(self.root), str(candidate))) != str(self.root):
            raise MediaStoreError("invalid object key")
        return candidate


def _validate_sha(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise MediaStoreError("SHA-256 must be 64 hexadecimal characters")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

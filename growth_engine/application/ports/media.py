from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Protocol, runtime_checkable

from growth_engine.application.dto import NormalizedImage, StoredObject
from growth_engine.domain.media.media_policy import TransformSpec


@runtime_checkable
class ImageProcessor(Protocol):
    def normalize(self, original: Path, spec: TransformSpec) -> NormalizedImage: ...


@runtime_checkable
class MediaStore(Protocol):
    def put_original(self, stream: BinaryIO, max_bytes: int) -> StoredObject: ...
    def put_variant(self, data: bytes, sha256: str) -> str: ...
    def open(self, object_key: str) -> BinaryIO: ...
    def verify(self, object_key: str, sha256: str) -> bool: ...


@runtime_checkable
class SignedUrlIssuer(Protocol):
    def media_url(self, sha256: str, command_id: str, expires_at_ms: int) -> str: ...

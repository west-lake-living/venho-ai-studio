from __future__ import annotations

import hashlib
from pathlib import Path

from identity_restoration.infrastructure.persistence.atomic_file_artifact_sink import AtomicFileArtifactSink


def test_write_atomic_leaves_no_tmp_file_and_matches_sha256(tmp_path: Path) -> None:
    sink = AtomicFileArtifactSink(root=tmp_path)
    data = b"hello identity restoration"

    artifact = sink.write_atomic("run1/attempt1/composite.png", data)

    written = Path(artifact.path)
    assert written.is_file()
    assert written.read_bytes() == data
    assert artifact.sha256 == hashlib.sha256(data).hexdigest()
    leftovers = list(written.parent.glob(".tmp-*"))
    assert leftovers == []


def test_write_atomic_creates_parent_directories(tmp_path: Path) -> None:
    sink = AtomicFileArtifactSink(root=tmp_path)
    artifact = sink.write_atomic("a/b/c/file.png", b"x")
    assert Path(artifact.path).is_file()

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ...application.ports.artifact_sink import PersistedArtifact


@dataclass
class AtomicFileArtifactSink:
    root: Path

    def write_atomic(self, key: str, data: bytes) -> PersistedArtifact:
        target = self.root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=target.suffix)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        except BaseException:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
        return PersistedArtifact(path=str(target), sha256=hashlib.sha256(data).hexdigest())

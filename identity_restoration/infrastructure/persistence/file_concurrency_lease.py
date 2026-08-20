from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from ...application.ports.concurrency import Lease
from ...domain.errors import RestorationError


@dataclass
class FileConcurrencyLease:
    """max_concurrent=1 lease backed by an exclusive lock file.

    6 GB VRAM cannot run two workflows at once (v2.0 §6). A stale lock older
    than its own TTL is treated as abandoned and reclaimed, so a crashed
    process cannot deadlock every future job.
    """

    lock_path: Path
    max_concurrent: int = 1

    @contextmanager
    def acquire(self, key: str, ttl_seconds: int) -> Iterator[Lease]:
        if self.max_concurrent != 1:
            raise NotImplementedError("FileConcurrencyLease only supports max_concurrent=1 (v2.0 §6)")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder = f"{os.getpid()}:{key}"
        acquired = self._try_acquire(holder, ttl_seconds)
        if not acquired:
            raise RestorationError("ERR_GW_LEASE_UNAVAILABLE",
                                   f"concurrency lease {key!r} is held by another attempt", retryable=True)
        try:
            yield Lease(key=key, holder=holder)
        finally:
            try:
                self.lock_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _try_acquire(self, holder: str, ttl_seconds: int) -> bool:
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w") as handle:
                handle.write(f"{holder}:{time.time()}")
            return True
        except FileExistsError:
            if self._is_stale(ttl_seconds):
                self.lock_path.unlink(missing_ok=True)
                return self._try_acquire(holder, ttl_seconds)
            return False

    def _is_stale(self, ttl_seconds: int) -> bool:
        try:
            content = self.lock_path.read_text(encoding="utf-8")
            written_at = float(content.rsplit(":", 1)[-1])
        except (OSError, ValueError):
            return True
        return (time.time() - written_at) > ttl_seconds

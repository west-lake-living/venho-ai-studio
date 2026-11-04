from __future__ import annotations

import socket
import sys
from collections.abc import Callable
from itertools import count
from pathlib import Path
from uuid import UUID

import pytest


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))


_original_connect = socket.socket.connect


def _guarded_connect(sock: socket.socket, address: object) -> None:
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="replace")
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("network blocked in tests")
    _original_connect(sock, address)


socket.socket.connect = _guarded_connect


@pytest.fixture
def fake_clock() -> Callable[[], int]:
    return lambda: 1_800_000_000_000


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "growth.db"


class _DeterministicIds:
    def __init__(self) -> None:
        self._values = count(1)

    def new_id(self) -> str:
        return str(UUID(int=next(self._values)))


@pytest.fixture
def ids() -> _DeterministicIds:
    return _DeterministicIds()

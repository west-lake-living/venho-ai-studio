from __future__ import annotations

import socket

import pytest


def test_non_loopback_socket_connect_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="network blocked in tests"):
        socket.socket.connect(None, ("example.com", 443))


def test_deterministic_test_fixtures(fake_clock, tmp_db_path, ids) -> None:
    assert fake_clock() == 1_800_000_000_000
    assert tmp_db_path.name == "growth.db"
    assert ids.new_id() == "00000000-0000-0000-0000-000000000001"

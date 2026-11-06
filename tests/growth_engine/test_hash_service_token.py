from __future__ import annotations

import hashlib

from scripts.growth_engine import hash_service_token


def test_hash_helper_prints_principal_and_digest_but_not_bearer(monkeypatch, capsys) -> None:
    bearer = "  synthetic-test-bearer-unique  "
    monkeypatch.setattr(hash_service_token, "_read_bearer", lambda: bearer)

    assert hash_service_token.main(["--principal", "make-fb-hanoi"]) == 0

    output = capsys.readouterr().out
    expected = hashlib.sha256(b"synthetic-test-bearer-unique").hexdigest()
    assert output == f"make-fb-hanoi:{expected}\n"
    assert bearer not in output
    assert bearer.strip() not in output

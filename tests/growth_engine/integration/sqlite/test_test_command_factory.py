from __future__ import annotations

import argparse
import base64
import json
import sqlite3
import stat
from pathlib import Path

from scripts.growth_engine import send_test_command


def test_factory_persists_test_chain_and_private_envelope(tmp_path: Path, monkeypatch) -> None:
    page_id = "test-page-803531149684177"
    monkeypatch.setattr(
        send_test_command,
        "_test_channel_manifest",
        lambda expected_page_id: {
            "channel_id": "page_test",
            "environment": "test",
            "platform": "facebook",
            "display_name": "Synthetic TEST Page",
            "remote_page_id": expected_page_id,
            "make_route_ref": "GE_MAKE_WEBHOOK_URL_PAGE_TEST",
            "graph_api_version": "v-synthetic-test",
        },
    )
    key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
    database = tmp_path / "test.sqlite3"
    envelope_path = tmp_path / "private" / "command.json"
    environ = {
        "GE_ENV": "test",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(tmp_path / "media"),
        "GE_PUBLIC_BASE_URL": "https://test.example.invalid",
        "GE_CAPABILITY_KEYS": f"test-key:{key}",
        "GE_SERVICE_TOKENS": "synthetic-test-service-token",
        "GE_MAKE_WEBHOOK_URL_PAGE_TEST": "https://make.example.invalid/test-route",
        "GE_TEST_CHANNEL_ID": "7c8ecf79-a4db-4f83-a9e1-7c3f559d8a78",
        "GE_TEST_REMOTE_PAGE_ID": page_id,
    }
    args = argparse.Namespace(
        envelope_file=envelope_path,
        create_command=True,
        send=False,
        confirm_test_page_id=None,
    )

    result = send_test_command.run(args, environ)

    assert result["result"] == "DRY_RUN_VALIDATED"
    assert result["network_request_sent"] is False
    assert result["environment"] == "test"
    assert envelope_path.exists()
    assert stat.S_IMODE(envelope_path.stat().st_mode) == 0o600
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    assert envelope["environment"] == "test"
    assert envelope["remote_page_id"] == page_id
    assert envelope["channel_id"] == environ["GE_TEST_CHANNEL_ID"]

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        chain = connection.execute(
            """SELECT s.id AS slot_id, d.id AS delivery_id, d.state,
                      r.id AS revision_id, a.id AS approval_id, c.id AS command_id,
                      ch.environment, ch.channel_key
                  FROM slots s JOIN slot_targets st ON st.slot_id=s.id
               JOIN channels ch ON ch.id=st.channel_id
                   JOIN deliveries d ON d.target_id=st.id
               JOIN delivery_revisions r ON r.id=d.current_revision_id
                   JOIN approval_decisions a ON a.id=d.active_approval_id
               JOIN outbox_commands c ON c.delivery_id=d.id"""
        ).fetchone()
        assert chain is not None
        assert chain["environment"] == "test"
        assert chain["channel_key"] == "page_test"
        assert chain["state"] == "QUEUED"
        assert chain["slot_id"] == result["slot_id"]
        assert chain["delivery_id"] == result["delivery_id"]
        assert chain["revision_id"] == result["revision_id"]
        assert chain["command_id"] == result["command_id"]
        assert chain["approval_id"]
    finally:
        connection.close()

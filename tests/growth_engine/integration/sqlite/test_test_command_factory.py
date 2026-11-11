from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sqlite3
import stat
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest
import yaml
from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings
from scripts.growth_engine import send_test_command


def test_webhook_start_callback_runs_immediately_before_request(monkeypatch) -> None:
    events: list[str] = []

    class Response:
        status = 200

    class Connection:
        sock = None

        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def request(self, *_args, **_kwargs) -> None:
            events.append("request")

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            events.append("closed")

    monkeypatch.setattr(send_test_command.http.client, "HTTPSConnection", Connection)

    disposition, status = send_test_command._post_to_test_route(
        "https://make.example.invalid/webhook",
        {"schema_version": "growth.command.v2", "environment": "test"},
        on_request_start=lambda: events.append("start-marker"),
    )

    assert (disposition, status) == ("ACK", 200)
    assert events == ["start-marker", "request", "closed"]


@pytest.mark.parametrize("channel_key", ["fb_hanoi", "fb_venho", "ig_venho"])
def test_factory_persists_test_chain_and_private_envelope(tmp_path: Path, monkeypatch, channel_key: str) -> None:
    platform = "instagram" if channel_key == "ig_venho" else "facebook"
    page_id = "synthetic-instagram-test" if platform == "instagram" else "synthetic-page-test"
    config = tmp_path / "config/projects/venho_hotel/growth_engine/channels.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(yaml.safe_dump({"channels": [
        {"channel_id": "fb_hanoi", "environment": "production", "remote_page_id": "synthetic-production-page"},
        {"channel_id": "ig_venho", "environment": "production", "remote_account_id": "synthetic-production-ig"},
        {"channel_id": "page_test", "environment": "test", "platform": "facebook", "display_name": "Synthetic TEST Page",
         "remote_page_id": "synthetic-page-test", "make_route_ref": "GE_MAKE_WEBHOOK_URL_PAGE_TEST", "graph_api_version": "v-synthetic-test",
         "service_principals": {"fb_hanoi": "make-fb-hanoi", "fb_venho": "make-fb-venho"}},
        {"channel_id": "ig_test", "environment": "test", "platform": "instagram", "display_name": "Synthetic TEST Instagram",
         "remote_account_id": "synthetic-instagram-test", "make_route_ref": "GE_MAKE_WEBHOOK_URL_IG_TEST", "graph_api_version": "v-synthetic-test",
         "service_principal": "make-ig"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(send_test_command, "_REPOSITORY_ROOT", str(tmp_path))
    key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
    principal = {"fb_hanoi": "make-fb-hanoi", "fb_venho": "make-fb-venho", "ig_venho": "make-ig"}[channel_key]
    bearer = "synthetic-test-bearer"
    bearer_hash = hashlib.sha256(bearer.encode()).hexdigest()
    other_principal = "make-fb-venho" if channel_key == "fb_hanoi" else "make-fb-hanoi"
    other_bearer = "synthetic-other-channel-bearer"
    other_hash = hashlib.sha256(other_bearer.encode()).hexdigest()
    database = tmp_path / "test.sqlite3"
    envelope_path = tmp_path / "private" / "command.json"
    environ = {
        "GE_ENV": "test",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(tmp_path / "media"),
        "GE_PUBLIC_BASE_URL": "https://test.example.invalid",
        "GE_CAPABILITY_KEYS": f"test-key:{key}",
        "GE_SERVICE_TOKENS": f"{principal}:{bearer_hash},{other_principal}:{other_hash}",
        "GE_MAKE_WEBHOOK_URL_PAGE_TEST": "https://make.example.invalid/test-route",
        "GE_MAKE_WEBHOOK_URL_IG_TEST": "https://make.example.invalid/test-route",
        "GE_TEST_CHANNEL_KEY": channel_key,
        "GE_TEST_CHANNEL_ID": "7c8ecf79-a4db-4f83-a9e1-7c3f559d8a78",
        "GE_TEST_REMOTE_PAGE_ID": "synthetic-page-test",
        "GE_TEST_REMOTE_IG_ID": "synthetic-instagram-test",
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
    assert envelope["channel_key"] == channel_key
    assert envelope["platform"] == platform
    validate_args = argparse.Namespace(envelope_file=envelope_path, create_command=False, send=False, confirm_test_page_id=None)
    with pytest.raises(ValueError, match="require GE_ENV=test"):
        send_test_command.run(validate_args, {**environ, "GE_ENV": "production"})
    with pytest.raises(ValueError, match="does not match"):
        send_test_command._validate_test_envelope(
            {**envelope, "channel_key": "wrong-channel"},
            expected_channel_id=environ["GE_TEST_CHANNEL_ID"],
            expected_page_id=page_id,
            expected_channel_key=channel_key,
            expected_platform=platform,
            now_ms=time.time_ns() // 1_000_000,
            tokens=send_test_command.CapabilityTokenManager(send_test_command.parse_key_ring(environ["GE_CAPABILITY_KEYS"])),
        )

    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        chain = connection.execute(
            """SELECT s.id AS slot_id, d.id AS delivery_id, d.state,
                      r.id AS revision_id, a.id AS approval_id, c.id AS command_id,
                      c.state AS outbox_state,
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
        assert chain["channel_key"] == channel_key
        assert chain["state"] == "QUEUED"
        assert chain["slot_id"] == result["slot_id"]
        assert chain["delivery_id"] == result["delivery_id"]
        assert chain["revision_id"] == result["revision_id"]
        assert chain["command_id"] == result["command_id"]
        assert chain["outbox_state"] == "PENDING"
        assert chain["approval_id"]
    finally:
        connection.close()

    client = TestClient(create_app(build_container(Settings.from_env(environ))))
    media_url = urlsplit(envelope["media_url"])
    media_response = client.get(f"{media_url.path}?{media_url.query}")
    assert media_response.status_code == 200
    assert media_response.content
    assert media_response.headers["content-type"] == "image/jpeg"
    assert media_response.headers["cache-control"] == "private, no-store"

    body = {
            "schema_version": "growth.authorize.v2",
            "command_token": envelope["command_token"],
            "payload_hash": envelope["payload_hash"],
            "media_report": {"http_status": 200, "content_type": "image/jpeg"},
    }
    wrong = client.post("/internal/growth/v2/executions/authorize", headers={"Authorization": f"Bearer {other_bearer}"}, json=body)
    assert wrong.status_code == 403
    response = client.post("/internal/growth/v2/executions/authorize", headers={"Authorization": f"Bearer {bearer}"}, json=body)
    assert response.status_code == 200
    assert response.json()["execute"] is True
    assert response.json()["remote_page_id"] == page_id

    second_path = tmp_path / "private" / "command-2.json"
    second_args = argparse.Namespace(
        envelope_file=second_path,
        create_command=True,
        send=False,
        confirm_test_page_id=None,
    )
    second_result = send_test_command.run(second_args, environ)
    second_envelope = json.loads(second_path.read_text(encoding="utf-8"))
    assert second_result["channel_id"] == result["channel_id"]
    assert second_result["delivery_id"] != result["delivery_id"]
    assert second_result["command_id"] != result["command_id"]
    assert second_envelope["channel_id"] == envelope["channel_id"]
    assert second_envelope["delivery_id"] != envelope["delivery_id"]

    connection = sqlite3.connect(database)
    try:
        assert connection.execute(
            "SELECT count(*) FROM channels WHERE environment='test' AND channel_key=?", (channel_key,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM deliveries WHERE channel_id=(SELECT id FROM channels WHERE environment='test' AND channel_key=?)",
            (channel_key,),
        ).fetchone()[0] == 2
        assert connection.execute(
            "SELECT count(DISTINCT c.delivery_id) FROM outbox_commands c JOIN deliveries d ON d.id=c.delivery_id WHERE d.channel_id=(SELECT id FROM channels WHERE environment='test' AND channel_key=?)",
            (channel_key,),
        ).fetchone()[0] == 2
    finally:
        connection.close()


def test_test_manifest_rejects_production_destination(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config/projects/venho_hotel/growth_engine/channels.yaml"
    config.parent.mkdir(parents=True)
    payload = {"channels": [
        {"channel_id": "fb_hanoi", "environment": "production", "remote_page_id": "12345"},
        {"channel_id": "page_test", "environment": "test", "platform": "facebook", "remote_page_id": "12345"},
    ]}
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    monkeypatch.setattr(send_test_command, "_REPOSITORY_ROOT", str(tmp_path))

    with pytest.raises(ValueError, match="differ from production IDs"):
        send_test_command._test_channel_manifest("12345", "fb_hanoi")

    payload["channels"][1]["remote_page_id"] = "67890"
    payload["channels"][1]["service_principals"] = {"fb_hanoi": "make-fb-venho"}
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="principal must match"):
        send_test_command._test_channel_manifest("67890", "fb_hanoi")


def test_intentional_test_mutations_change_only_the_selected_envelope_field() -> None:
    original = {
        "command_token": "valid-command-token",
        "media_url": "https://ge-test.venhohotel.com/media/publish/" + "a" * 64 + ".jpg?t=v1.kid.command.expiry.signature",
        "caption": "TEST caption",
    }

    broken_media = send_test_command._mutate_test_envelope(
        original, corrupt_media=True, corrupt_command=False
    )
    bad_command = send_test_command._mutate_test_envelope(
        original, corrupt_media=False, corrupt_command=True
    )

    assert original["command_token"] == "valid-command-token"
    assert broken_media["command_token"] == original["command_token"]
    assert broken_media["media_url"] != original["media_url"]
    assert bad_command["media_url"] == original["media_url"]
    assert bad_command["command_token"] != original["command_token"]
    assert broken_media["caption"] == original["caption"]
    assert bad_command["caption"] == original["caption"]

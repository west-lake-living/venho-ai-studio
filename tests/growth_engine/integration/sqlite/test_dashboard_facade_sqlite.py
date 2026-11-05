from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.app import create_app
from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings
from tests.growth_engine.integration.sqlite.test_revision_store import _fixture


TOKEN = "synthetic-dashboard-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def _settings(database: Path, media: Path) -> Settings:
    return Settings(
        env="test",
        db_path=str(database),
        media_root=str(media),
        public_base_url="https://growth.example.test",
        service_tokens=f"bff:{hashlib.sha256(TOKEN.encode()).hexdigest()}",
    )


def test_dashboard_reads_compose_over_file_sqlite_and_redact_private_channel_config(tmp_path: Path) -> None:
    database, _uow, _slot, variant, _caption, revision = _fixture(tmp_path)
    container = build_container(_settings(database, tmp_path / "media"))
    client = TestClient(create_app(container))

    channels = client.get("/api/growth/v2/channels", headers=HEADERS)
    slots = client.get(
        "/api/growth/v2/slots?from=2026-11-05&to=2026-11-05", headers=HEADERS
    )
    deliveries = client.get(
        "/api/growth/v2/deliveries?state=APPROVED&limit=50", headers=HEADERS
    )
    review = client.get("/api/growth/v2/deliveries/delivery-synthetic/review", headers=HEADERS)

    assert channels.status_code == 200
    assert channels.json()["items"][0]["channel_key"] == "fb_hanoi"
    assert "make_route_ref" not in channels.text and "capability_json" not in channels.text
    assert slots.status_code == 200 and slots.json()["items"][0]["slot_id"] == "slot-synthetic"
    assert slots.json()["items"][0]["targets"][0]["delivery_state"] == "APPROVED"
    assert deliveries.status_code == 200
    assert deliveries.json()["items"][0]["delivery_id"] == "delivery-synthetic"
    assert review.status_code == 200
    assert review.headers["etag"] == '"delivery:delivery-synthetic:4"'
    assert review.json()["payload_hash"] == revision.payload_hash
    assert review.json()["preview_sha256"] == revision.payload["media"][0]["sha256"]


def test_dashboard_mutation_forwards_stale_etag_and_batch_conflicts(tmp_path: Path) -> None:
    database, uow, _slot, _variant, _caption, revision = _fixture(tmp_path)
    container = build_container(_settings(database, tmp_path / "media"))
    client = TestClient(create_app(container))

    stale = client.post(
        "/api/growth/v2/deliveries/delivery-synthetic/revisions",
        json={"caption": "changed caption"},
        headers={**HEADERS, "If-Match": '"delivery:delivery-synthetic:3"', "Idempotency-Key": "stale"},
    )
    conflict = client.post(
        "/api/growth/v2/approvals/batch",
        json={"items": [{
            "delivery_id": "delivery-synthetic",
            "revision_id": "revision-a",
            "payload_hash": revision.payload_hash,
            "expected_row_version": 3,
        }]},
        headers={**HEADERS, "Idempotency-Key": "batch-stale"},
    )

    assert stale.status_code == 412
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["error"]["details"]["conflicts"][0]["delivery_id"] == "delivery-synthetic"
    with uow().read_only() as tx:
        assert tx.connection.execute(
            "SELECT count(*) FROM approval_decisions WHERE decision='APPROVE'"
        ).fetchone()[0] == 1


def test_dashboard_maps_sqlite_open_failure_to_503_not_empty_lists(tmp_path: Path) -> None:
    database = tmp_path / "missing-parent" / "growth.sqlite"
    container = build_container(_settings(database, tmp_path / "media"))
    response = TestClient(create_app(container)).get("/api/growth/v2/channels", headers=HEADERS)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ERR_GC2_DB_BUSY"
    assert "items" not in response.json()


def test_dashboard_upload_saves_original_and_replays_durable_job_receipt(tmp_path: Path) -> None:
    database, uow, _slot, _variant, _caption, _revision = _fixture(tmp_path)
    client = TestClient(create_app(build_container(_settings(database, tmp_path / "media"))))
    headers = {**HEADERS, "Idempotency-Key": "upload-fixture-1"}

    first = client.post(
        "/api/growth/v2/assets",
        files={"file": ("fixture.jpg", b"synthetic-upload", "image/jpeg")},
        headers=headers,
    )
    replay = client.post(
        "/api/growth/v2/assets",
        files={"file": ("fixture.jpg", b"synthetic-upload", "image/jpeg")},
        headers=headers,
    )
    mismatch = client.post(
        "/api/growth/v2/assets",
        files={"file": ("different.jpg", b"different-body", "image/jpeg")},
        headers=headers,
    )

    assert first.status_code == replay.status_code == 202
    assert replay.json()["job_id"] == first.json()["job_id"]
    assert replay.json()["asset_id"] == first.json()["asset_id"]
    assert mismatch.status_code == 409
    assert "request_fingerprint" not in first.text
    job = client.get(f"/api/growth/v2/jobs/{first.json()['job_id']}", headers=HEADERS)
    assert job.status_code == 200 and job.json()["state"] == "SUCCEEDED"
    with uow().read_only() as tx:
        assert tx.connection.execute(
            "SELECT count(*) FROM jobs WHERE kind='asset_upload'"
        ).fetchone()[0] == 1
        assert tx.connection.execute(
            "SELECT count(*) FROM media_assets WHERE source_ref='dashboard-upload:upload-fixture-1'"
        ).fetchone()[0] == 1



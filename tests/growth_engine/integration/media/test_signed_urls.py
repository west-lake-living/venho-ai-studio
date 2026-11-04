from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from growth_engine.adapters.inbound.api.errors import domain_error_handler
from growth_engine.adapters.inbound.api.routers.media import router as media_router
from growth_engine.adapters.outbound.media.local_store import LocalMediaStore
from growth_engine.adapters.outbound.media.signed_urls import SignedMediaUrlIssuer
from growth_engine.adapters.outbound.persistence.sqlite.connection import connect
from growth_engine.bootstrap import build_container
from growth_engine.domain.kernel.errors import DomainError
from growth_engine.settings import Settings

MIGRATIONS = Path("growth_engine/adapters/outbound/persistence/sqlite/migrations")
_KEY = b"synthetic-media-signing-key-32bytes-long"
_KEY_CONFIG = "test-kid:" + base64.urlsafe_b64encode(_KEY).decode("ascii").rstrip("=")
_POST_BYTES = b"\xff\xd8\xffsynthetic-approved-jpeg"
_POST_SHA = hashlib.sha256(_POST_BYTES).hexdigest()
_NOW_MS = 1_800_000_000_000
_COMMAND_EXPIRY_MS = _NOW_MS + 60_000
_MEDIA_EXPIRY_MS = _COMMAND_EXPIRY_MS + 30 * 60 * 1000


class _FixedClock:
    def now_ms(self) -> int:
        return _NOW_MS


@pytest.fixture
def media_client(tmp_path: Path) -> tuple[TestClient, SignedMediaUrlIssuer]:
    database_path = tmp_path / "growth.db"
    settings = Settings(
        env="test",
        db_path=str(database_path),
        media_root=str(tmp_path / "media"),
        public_base_url="https://media.example.test",
        capability_keys=_KEY_CONFIG,
        service_tokens="",
    )
    container = build_container(settings)
    container.migration_service.run(database_path, check=False)
    _seed_approved_command(database_path, settings.media_root)
    app = FastAPI()
    app.state.container = container
    app.state.media_clock = _FixedClock()
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(media_router)
    issuer = SignedMediaUrlIssuer(settings.public_base_url, settings.capability_keys)
    return TestClient(app), issuer


def test_signed_url_serves_exact_approved_bytes_and_cache_headers(
    media_client: tuple[TestClient, SignedMediaUrlIssuer],
) -> None:
    client, issuer = media_client
    url = issuer.media_url(_POST_SHA, "command-1", _MEDIA_EXPIRY_MS)

    response = client.get(url)

    assert response.status_code == 200
    assert response.content == _POST_BYTES
    assert hashlib.sha256(response.content).hexdigest() == _POST_SHA
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize("case", ["expired", "wrong_sha", "path_traversal"])
def test_invalid_signed_media_requests_return_403_json(
    media_client: tuple[TestClient, SignedMediaUrlIssuer],
    case: str,
) -> None:
    client, issuer = media_client
    url = issuer.media_url(_POST_SHA, "command-1", _MEDIA_EXPIRY_MS)
    if case == "expired":
        url = issuer.media_url(_POST_SHA, "command-1", _NOW_MS - 1)
    elif case == "wrong_sha":
        url = url.replace(_POST_SHA, "0" * 64)
    else:
        url = "/media/publish/%2E%2E%2Fsecret.jpg?t=invalid"

    response = client.get(url)

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "ERR_GC2_CAPABILITY_INVALID"


def _seed_approved_command(database_path: Path, media_root: str) -> None:
    store = LocalMediaStore(Path(media_root))
    object_key = store.put_variant(_POST_BYTES, _POST_SHA)
    connection = connect(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """INSERT INTO channels
               (id, project_id, environment, channel_key, platform, remote_account_id, name,
                enabled, created_at)
               VALUES ('channel-fb', 'venho-test', 'test', 'fb_hanoi', 'facebook', 'page-test',
                       'Synthetic Page', 1, 1)"""
        )
        connection.execute(
            """INSERT INTO channel_configs
               (id, channel_id, version, make_route_ref, graph_api_version, capability_json,
                caption_profile, config_hash, created_at)
               VALUES ('config-1', 'channel-fb', 1, 'synthetic-route', 'TEST_VERSION', '{}',
                       'default', ?, 1)""",
            ("a" * 64,),
        )
        connection.execute(
            """INSERT INTO slots
               (id, project_id, local_date, local_time, timezone, lane, cadence_version,
                scheduled_at, deadline_at, created_at)
               VALUES ('slot-1', 'venho-test', '2026-11-04', '09:00', 'Asia/Ho_Chi_Minh',
                       'weekly', 'test-v1', ?, ?, 1)""",
            (_NOW_MS, _COMMAND_EXPIRY_MS),
        )
        connection.execute(
            "INSERT INTO slot_targets (id, slot_id, channel_id, required) VALUES ('target-1', 'slot-1', 'channel-fb', 1)"
        )
        connection.execute(
            """INSERT INTO content_packages
               (id, slot_id, topic_key, pillar, lane, source_snapshot_json, fact_snapshot_json,
                fact_snapshot_hash, generation_version, created_at)
               VALUES ('package-1', 'slot-1', 'topic', 'brand', 'weekly', '{}', '{}', ?, 'test', 1)""",
            ("b" * 64,),
        )
        connection.execute(
            """INSERT INTO media_assets
               (id, source_type, source_ref, source_revision, source_sha256, original_key,
                metadata_json, created_at)
               VALUES ('asset-1', 'upload', 'synthetic', 'r1', ?, 'originals/test', '{}', 1)""",
            ("c" * 64,),
        )
        connection.execute(
            """INSERT INTO media_variants
               (id, asset_id, transform_version, sha256, object_key, width, height, mime,
                byte_size, qc_status, created_at)
               VALUES ('variant-1', 'asset-1', 'test-profile', ?, ?, 64, 48, 'image/jpeg',
                       ?, 'PASS', 1)""",
            (_POST_SHA, object_key, len(_POST_BYTES)),
        )
        connection.execute(
            """INSERT INTO qc_reports
               (id, variant_id, caption_hash, ruleset_hash, fact_snapshot_hash, decision,
                coverage_gaps_json, result_json, created_at)
               VALUES ('qc-1', 'variant-1', ?, ?, ?, 'PASS', '[]', '{}', 1)""",
            ("d" * 64, "e" * 64, "b" * 64),
        )
        connection.execute(
            """INSERT INTO deliveries
               (id, target_id, channel_id, package_id, state, created_at, updated_at)
               VALUES ('delivery-1', 'target-1', 'channel-fb', 'package-1', 'DRAFT', 1, 1)"""
        )
        connection.execute(
            """INSERT INTO delivery_revisions
               (id, delivery_id, channel_id, revision_no, channel_config_id, variant_id,
                qc_report_id, scheduled_at, deadline_at, caption, payload_json, payload_hash,
                created_by, created_at)
               VALUES ('revision-1', 'delivery-1', 'channel-fb', 1, 'config-1', 'variant-1',
                       'qc-1', ?, ?, 'Synthetic approved caption', '{}', ?, 'pytest', 1)""",
            (_NOW_MS, _COMMAND_EXPIRY_MS, "f" * 64),
        )
        connection.execute(
            """INSERT INTO approval_decisions
               (id, revision_id, payload_hash, decision, actor_id, created_at)
               VALUES ('approval-1', 'revision-1', ?, 'APPROVE', 'pytest', 1)""",
            ("f" * 64,),
        )
        connection.execute(
            """UPDATE deliveries
               SET current_revision_id='revision-1', active_approval_id='approval-1', state='QUEUED'
               WHERE id='delivery-1'"""
        )
        connection.execute(
            """INSERT INTO outbox_commands
               (id, delivery_id, revision_id, sequence_no, kind, business_key, payload_hash,
                state, dispatch_epoch, expires_at, next_attempt_at, created_at, updated_at)
               VALUES ('command-1', 'delivery-1', 'revision-1', 1, 'PUBLISH',
                       'publish:delivery-1:revision-1:1', ?, 'ACKED', 'test-epoch', ?, ?, 1, 1)""",
            ("f" * 64, _COMMAND_EXPIRY_MS, _NOW_MS),
        )
        connection.commit()
    except BaseException:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()

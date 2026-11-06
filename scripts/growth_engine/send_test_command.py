from __future__ import annotations

import argparse
import http.client
import hashlib
import io
import json
import os
import re
import socket
import stat
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo


_REPOSITORY_ROOT = str(Path(__file__).resolve().parents[2])
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

from growth_engine.adapters.outbound.security.capability_tokens import (
    CapabilityTokenManager,
    parse_key_ring,
)
from growth_engine.domain.kernel.hashing import canonical_json_bytes

_TEST_TARGETS = {
    "fb_hanoi": ("page_test", "facebook", "remote_page_id", "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST"),
    "fb_venho": ("page_test", "facebook", "remote_page_id", "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST"),
    "ig_venho": ("ig_test", "instagram", "remote_account_id", "GE_TEST_REMOTE_IG_ID", "GE_MAKE_WEBHOOK_URL_IG_TEST"),
}
_TEST_PRINCIPALS = {"fb_hanoi": "make-fb-hanoi", "fb_venho": "make-fb-venho", "ig_venho": "make-ig"}


def _post_to_test_route(route_url: str, envelope: dict[str, Any]) -> tuple[str, int | None]:
    parsed = urlsplit(route_url)
    try:
        port = parsed.port or 443
    except ValueError as error:
        raise ValueError("TEST webhook URL has an invalid port.") from error
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    try:
        connection = http.client.HTTPSConnection(parsed.hostname, port, timeout=5)
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("TEST webhook URL is invalid.") from error
    try:
        connection.request(
            "POST",
            target,
            body=canonical_json_bytes(envelope),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if connection.sock is not None:
            connection.sock.settimeout(15)
        response = connection.getresponse()
        if 200 <= response.status < 300:
            return "ACK", response.status
        if response.status in {408, 425, 429} or response.status >= 500:
            return "RETRYABLE", response.status
        return "FATAL", response.status
    except (TimeoutError, socket.timeout, OSError, http.client.HTTPException):
        return "RETRYABLE", None
    finally:
        try:
            connection.close()
        except OSError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or send a command envelope created for the isolated TEST channel."
    )
    parser.add_argument(
        "--envelope-file",
        type=Path,
        default=None,
        help="Private JSON file with a previously created growth.command.v2 TEST envelope.",
    )
    parser.add_argument(
        "--create-command",
        action="store_true",
        help="Create an isolated TEST slot, delivery, revision, approval and command in SQLite.",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send to the webhook variable referenced by the TEST channel manifest; dry run is the default.",
    )
    parser.add_argument(
        "--confirm-test-remote-id", "--confirm-test-page-id",
        dest="confirm_test_page_id",
        help="Must exactly match the configured TEST Page or Instagram account ID when --send is set.",
    )
    return parser


def _read_private_envelope(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ValueError("TEST command envelope file is unavailable.") from error
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError("TEST command envelope must be a regular file with mode 0600 or stricter.")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("TEST command envelope is not readable JSON.") from error
    if not isinstance(value, dict):
        raise ValueError("TEST command envelope must be a JSON object.")
    return value


def _validate_test_envelope(
    envelope: dict[str, Any],
    *,
    expected_channel_id: str,
    expected_page_id: str,
    expected_channel_key: str,
    expected_platform: str,
    now_ms: int,
    tokens: CapabilityTokenManager,
) -> None:
    required_text = (
        "command_id",
        "delivery_id",
        "revision_id",
        "channel_id",
        "remote_page_id",
        "payload_hash",
        "dispatch_epoch",
        "media_url",
        "command_token",
        "idempotency_key",
    )
    for field in required_text:
        if not isinstance(envelope.get(field), str) or not envelope[field].strip():
            raise ValueError("TEST envelope is missing a required field.")
    if envelope.get("schema_version") != "growth.command.v2" or envelope.get("environment") != "test":
        raise ValueError("Only a growth.command.v2 envelope with environment=test is allowed.")
    if (
        envelope["channel_id"] != expected_channel_id
        or envelope["remote_page_id"] != expected_page_id
        or envelope.get("channel_key") != expected_channel_key
        or envelope.get("platform") != expected_platform
    ):
        raise ValueError("TEST envelope channel or Page ID does not match the configured TEST destination.")
    if not re.fullmatch(r"[0-9a-f]{64}", envelope["payload_hash"]):
        raise ValueError("TEST envelope payload hash is invalid.")
    expires_at_ms = envelope.get("execute_before_ms")
    if type(expires_at_ms) is not int or expires_at_ms < now_ms:
        raise ValueError("TEST command is expired or has an invalid deadline.")
    media_url = urlsplit(envelope["media_url"])
    if (
        media_url.scheme != "https"
        or not media_url.hostname
        or media_url.username
        or media_url.password
        or media_url.fragment
    ):
        raise ValueError("TEST media URL must be HTTPS and must not contain credentials.")
    expected_key_prefix = f"publish:{envelope['delivery_id']}:{envelope['revision_id']}:"
    idempotency_key = envelope["idempotency_key"]
    if not idempotency_key.startswith(expected_key_prefix) or not idempotency_key[len(expected_key_prefix):].isdigit():
        raise ValueError("TEST command idempotency key does not match its delivery and revision.")

    claims = tokens.verify(
        envelope["command_token"],
        audience=f"make-route:{expected_channel_id}",
        now_ms=now_ms,
    )
    if (
        claims.command_id != envelope["command_id"]
        or claims.revision_id != envelope["revision_id"]
        or claims.channel_id != expected_channel_id
        or claims.payload_hash != envelope["payload_hash"]
        or claims.dispatch_epoch != envelope["dispatch_epoch"]
        or claims.expires_at_ms != expires_at_ms
    ):
        raise ValueError("TEST capability claims do not match the envelope.")


def _test_destination_reference(expected_page_id: str, channel_key: str) -> str:
    test_channel = _test_channel_manifest(expected_page_id, channel_key)
    route_reference = test_channel.get("make_route_ref")
    if not isinstance(route_reference, str) or route_reference != _TEST_TARGETS[channel_key][4]:
        raise ValueError("TEST channel must use its dedicated TEST webhook variable.")
    return route_reference


def _test_channel_manifest(expected_page_id: str, channel_key: str) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as error:
        raise ValueError("PyYAML is required to verify the TEST destination manifest.") from error
    try:
        config_path = Path(_REPOSITORY_ROOT) / "config/projects/venho_hotel/growth_engine/channels.yaml"
        configuration = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError("Verified TEST destination configuration is unavailable.") from error
    if not isinstance(configuration, dict) or not isinstance(configuration.get("channels"), list):
        raise ValueError("Growth channels configuration is invalid.")
    manifest_key, platform, remote_field, _, _ = _TEST_TARGETS[channel_key]
    test_channels = [
        channel
        for channel in configuration["channels"]
        if isinstance(channel, dict)
        and channel.get("channel_id") == manifest_key
        and channel.get("environment") == "test"
        and channel.get("platform") == platform
    ]
    if len(test_channels) != 1:
        raise ValueError("Exactly one matching TEST destination must be configured.")
    test_channel = test_channels[0]
    production_ids = {
        str(channel.get(field) or "")
        for channel in configuration["channels"] if isinstance(channel, dict) and channel.get("environment") == "production"
        for field in ("remote_page_id", "remote_account_id")
    }
    if (
        test_channel.get(remote_field) != expected_page_id
        or expected_page_id == "REQUIRED_FROM_P0"
        or expected_page_id in production_ids
    ):
        raise ValueError("TEST destination ID must match the test manifest and differ from production IDs.")
    principals = test_channel.get("service_principals")
    principal = principals.get(channel_key) if isinstance(principals, dict) else test_channel.get("service_principal")
    if principal != _TEST_PRINCIPALS[channel_key]:
        raise ValueError("TEST destination principal must match the selected channel key.")
    return test_channel


def _test_target(environ: dict[str, str]) -> tuple[str, str, str, str]:
    channel_key = environ.get("GE_TEST_CHANNEL_KEY", "").strip()
    if channel_key not in _TEST_TARGETS:
        raise ValueError("GE_TEST_CHANNEL_KEY must be fb_hanoi, fb_venho, or ig_venho.")
    _, platform, _, remote_env, _ = _TEST_TARGETS[channel_key]
    channel_id = environ.get("GE_TEST_CHANNEL_ID", "").strip()
    remote_id = environ.get(remote_env, "").strip()
    if not channel_id or channel_id == "REQUIRED_FROM_P0" or not remote_id or remote_id == "REQUIRED_FROM_P0":
        raise ValueError("TEST channel UUID and remote destination ID must be verified before creating a command.")
    return channel_key, platform, channel_id, remote_id


def _create_test_command(environ: dict[str, str], output_path: Path) -> dict[str, object]:
    if environ.get("GE_ENV", "").strip().casefold() != "test":
        raise ValueError("--create-command requires GE_ENV=test.")
    channel_key, platform, channel_id, page_id = _test_target(environ)
    manifest = _test_channel_manifest(page_id, channel_key)
    route_reference = _test_destination_reference(page_id, channel_key)
    graph_version = manifest.get("graph_api_version")
    if not isinstance(graph_version, str) or not graph_version.strip() or "REQUIRED_FROM_P0" in graph_version:
        raise ValueError("TEST Graph API version must be verified before creating a command.")
    required = (
        "GE_DB_PATH", "GE_MEDIA_ROOT", "GE_PUBLIC_BASE_URL", "GE_CAPABILITY_KEYS",
        "GE_SERVICE_TOKENS", route_reference,
    )
    missing = [name for name in required if not environ.get(name, "").strip() or "REQUIRED_FROM_P0" in environ.get(name, "")]
    if missing:
        raise ValueError("Missing TEST runtime settings: " + ", ".join(missing) + ".")

    from PIL import Image, ImageDraw

    from growth_engine.adapters.outbound.make.envelope import MakeEnvelopeBuilder
    from growth_engine.adapters.outbound.media.local_store import LocalMediaStore
    from growth_engine.adapters.outbound.media.signed_urls import SignedMediaUrlIssuer
    from growth_engine.adapters.outbound.security.capability_tokens import CapabilityTokenManager, parse_key_ring
    from growth_engine.application.publishing.dispatch_outbox import DispatchLease
    from growth_engine.application.publishing.enqueue_due import EnqueueCommandClaims
    from growth_engine.bootstrap import build_container
    from growth_engine.domain.channels.channel import Channel, ChannelConfig, ChannelPlatform, config_hash
    from growth_engine.domain.content.package import ContentPackage
    from growth_engine.domain.delivery.approval import ApprovalDecision, ApprovalType
    from growth_engine.domain.delivery.delivery import Delivery
    from growth_engine.domain.delivery.revision import DeliveryRevision
    from growth_engine.domain.delivery.states import DeliveryState
    from growth_engine.domain.kernel.hashing import canonical_json_bytes, sha256_hex
    from growth_engine.domain.media.asset import MediaAsset, MediaVariant, VariantQcStatus
    from growth_engine.domain.media.qc import QcDecision, QcReport
    from growth_engine.domain.publishing.command import CommandState, OutboxCommand
    from growth_engine.domain.publishing.runtime_mode import PublishMode, RuntimeControls
    from growth_engine.domain.scheduling.slot import Slot, SlotTarget
    from growth_engine.settings import Settings

    settings = Settings.from_env(environ)
    if urlsplit(settings.public_base_url).scheme != "https":
        raise ValueError("GE_PUBLIC_BASE_URL must use HTTPS for a TEST command.")
    route_url = settings.make_webhook_urls.get(route_reference.removeprefix("GE_MAKE_WEBHOOK_URL_"), "").strip()
    parsed_route = urlsplit(route_url)
    if parsed_route.scheme != "https" or not parsed_route.hostname:
        raise ValueError(f"{route_reference} must be an HTTPS TEST route.")

    now_ms = time.time_ns() // 1_000_000
    ict_now = datetime.fromtimestamp(now_ms / 1000, ZoneInfo("Asia/Ho_Chi_Minh"))
    deadline_at_ms = now_ms + 30 * 60_000
    synthetic_note = "cần thay bằng fixture thật từ P0-T03/P0-T04"
    ids = {key: str(uuid4()) for key in (
        "config", "slot", "target", "package", "asset", "variant", "qc",
        "delivery", "revision", "approval",
    )}

    image = Image.new("RGB", (1080, 1350), color=(232, 239, 238))
    ImageDraw.Draw(image).text((32, 32), "GC2 TEST ONLY", fill=(20, 48, 52))
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="JPEG", quality=88, optimize=True)
    image_bytes = image_buffer.getvalue()
    media_sha = hashlib.sha256(image_bytes).hexdigest()
    fact_json = "{}"
    fact_hash = sha256_hex(fact_json.encode("utf-8"))
    caption = "Đây là bài kiểm tra hệ thống Growth Engine trên Trang thử nghiệm."
    caption_hash = sha256_hex(caption.encode("utf-8"))
    ruleset_hash = sha256_hex(b"gc2-test-command-factory-v1")
    media_key = LocalMediaStore(Path(settings.media_root)).put_variant(image_bytes, media_sha)

    container = build_container(settings)
    container.migration_service.run(Path(settings.db_path), check=False)
    channel = Channel(
        id=channel_id,
        project_id="venho_hotel",
        environment="test",
        channel_key=channel_key,
        platform=ChannelPlatform.FACEBOOK if platform == "facebook" else ChannelPlatform.INSTAGRAM,
        remote_account_id=page_id,
        name=str(manifest.get("display_name") or "Growth TEST Page"),
        enabled=True,
    )
    config = ChannelConfig(
        id=ids["config"], channel_id=channel.id, version=1,
        make_route_ref=route_reference, graph_api_version=graph_version,
        capability={"_synthetic": True, "note": synthetic_note}, caption_profile="default",
    )
    slot = Slot(
        ids["slot"], "venho_hotel", ict_now.date(), ict_now.strftime("%H:%M"),
        "Asia/Ho_Chi_Minh", "test", "gc2-test-factory-v1", now_ms, deadline_at_ms,
    )
    target = SlotTarget(ids["target"], slot.id, channel.id)
    package = ContentPackage(
        id=ids["package"], slot_id=slot.id, topic_key=f"test-command:{ids['delivery']}",
        pillar="test", lane="test",
        source_snapshot_json=canonical_json_bytes({"_synthetic": True, "note": synthetic_note}).decode(),
        fact_snapshot_json=fact_json, fact_snapshot_hash=fact_hash,
        generation_version="gc2-test-factory-v1", created_at_ms=now_ms,
    )
    asset = MediaAsset(
        id=ids["asset"], source_type="upload", source_ref="gc2-test-command-factory",
        source_revision=ids["variant"], source_sha256=media_sha, original_key=media_key,
        metadata_json=canonical_json_bytes({"_synthetic": True, "note": synthetic_note}).decode(),
        created_at_ms=now_ms,
    )
    variant = MediaVariant(
        id=ids["variant"], asset_id=asset.id, transform_version="gc2-test-factory-v1",
        sha256=media_sha, object_key=media_key, width=1080, height=1350,
        mime="image/jpeg", byte_size=len(image_bytes), qc_status=VariantQcStatus.PASS,
        created_at_ms=now_ms,
    )
    qc = QcReport(
        id=ids["qc"], variant_id=variant.id, caption_hash=caption_hash,
        ruleset_hash=ruleset_hash, fact_snapshot_hash=fact_hash,
        decision=QcDecision.PASS, coverage_gaps=(),
        result_json=canonical_json_bytes({"_synthetic": True, "note": synthetic_note}).decode(),
        created_at_ms=now_ms,
    )
    revision = DeliveryRevision.create(
        {
            "delivery_id": ids["delivery"], "revision_id": ids["revision"],
            "channel_id": channel.id, "remote_account_id": page_id,
            "channel_config_hash": config_hash(config), "caption": caption,
            "media": [{"sha256": media_sha, "mime": "image/jpeg", "width": 1080, "height": 1350}],
            "scheduled_at_ms": now_ms, "deadline_at_ms": deadline_at_ms,
            "qc_report_id": qc.id, "ruleset_hash": ruleset_hash,
            "fact_snapshot_hash": fact_hash,
        }
    )
    approval = ApprovalDecision(
        id=ids["approval"], revision_id=ids["revision"], payload_hash=revision.payload_hash,
        decision=ApprovalType.APPROVE, actor_id="test-command-factory", created_at_ms=now_ms,
    )
    with container.uow_factory().begin_immediate() as tx:
        existing = tx.connection.execute(
            "SELECT id FROM channels WHERE environment='test' AND channel_key=?", (channel_key,)
        ).fetchone()
        if existing is not None:
            raise ValueError("TEST channel already exists in this database; use an isolated TEST database.")
        controls = tx.controls.get("test")
        if controls is not None and (controls.mode is not PublishMode.LIVE_MANUAL or controls.global_pause):
            raise ValueError("TEST runtime controls must already be LIVE_MANUAL and unpaused.")
        tx.channels.save_channel(channel, created_at_ms=now_ms)
        tx.channels.save_config(config, created_at_ms=now_ms)
        tx.slots.save_slot(slot, created_at_ms=now_ms)
        tx.slots.save_target(target)
        tx.packages.save(package)
        tx.media.save_asset(asset)
        tx.media.save_variant(variant)
        tx.qc.save(qc)
        tx.deliveries.save(
            Delivery(ids["delivery"], DeliveryState.DRAFT), target_id=target.id,
            channel_id=channel.id, package_id=package.id,
            created_at_ms=now_ms, updated_at_ms=now_ms,
        )
        tx.deliveries.save_revision(
            revision, delivery_id=ids["delivery"], channel_id=channel.id,
            revision_no=1, channel_config_id=config.id, variant_id=variant.id,
            qc_report_id=qc.id, scheduled_at_ms=now_ms, deadline_at_ms=deadline_at_ms,
            caption=caption, created_by="test-command-factory", created_at_ms=now_ms,
        )
        tx.deliveries.save_approval(approval)
        tx.connection.execute(
            "UPDATE deliveries SET state='APPROVED', current_revision_id=?, active_approval_id=?, updated_at=? "
            "WHERE id=? AND state='DRAFT'",
            (ids["revision"], approval.id, now_ms, ids["delivery"]),
        )
        if controls is None:
            tx.controls.save(
                RuntimeControls(PublishMode.LIVE_MANUAL, f"test:{ids['slot']}"),
                environment="test", policy_version="gc2-test-factory-v1", updated_at_ms=now_ms,
            )

    enqueued = container.enqueue_due.execute(now_ms)
    if ids["delivery"] not in enqueued.enqueued_delivery_ids:
        raise ValueError("TEST command factory could not enqueue the approved TEST delivery.")
    with container.uow_factory().read_only() as tx:
        row = tx.connection.execute(
            """SELECT c.id, c.delivery_id, c.revision_id, c.sequence_no, c.business_key,
                      c.payload_hash, c.dispatch_epoch, c.expires_at, c.next_attempt_at,
                      c.transport_attempts, c.signing_key_id, ch.id AS channel_id,
                      ch.channel_key, ch.platform, ch.remote_account_id,
                      mv.sha256 AS media_sha256
               FROM outbox_commands c JOIN deliveries d ON d.id=c.delivery_id
               JOIN channels ch ON ch.id=d.channel_id
               JOIN delivery_revisions r ON r.id=d.current_revision_id
               JOIN media_variants mv ON mv.id=r.variant_id WHERE c.delivery_id=?""",
            (ids["delivery"],),
        ).fetchone()
    if row is None or not row["signing_key_id"]:
        raise ValueError("TEST outbox command was not persisted.")
    tokens = CapabilityTokenManager(parse_key_ring(settings.capability_keys))
    claims = EnqueueCommandClaims(
        command_id=row["id"], delivery_id=row["delivery_id"], revision_id=row["revision_id"],
        channel_id=row["channel_id"], remote_account_id=row["remote_account_id"],
        payload_hash=row["payload_hash"], dispatch_epoch=row["dispatch_epoch"],
        audience=f"make-route:{row['channel_id']}", expires_at_ms=row["expires_at"],
    )
    command = OutboxCommand(
        id=row["id"], delivery_id=row["delivery_id"], revision_id=row["revision_id"],
        sequence_no=row["sequence_no"], business_key=row["business_key"],
        expires_at_ms=row["expires_at"], next_attempt_at_ms=row["next_attempt_at"],
        envelope_token=tokens.issue(claims, key_id=row["signing_key_id"]),
        state=CommandState.PENDING, attempts=row["transport_attempts"],
    )
    lease = DispatchLease(
        command=command, lease_token="test-factory-no-network-lease", environment="test",
        channel_id=row["channel_id"], remote_page_id=row["remote_account_id"],
        channel_key=row["channel_key"], platform=row["platform"],
        payload_hash=row["payload_hash"], dispatch_epoch=row["dispatch_epoch"],
        route_ref=route_url, media_sha256=row["media_sha256"],
    )
    media_urls = SignedMediaUrlIssuer(settings.public_base_url, settings.capability_keys)
    envelope = MakeEnvelopeBuilder().build(
        lease,
        media_url=media_urls.media_url(row["media_sha256"], row["id"], row["expires_at"]),
    )
    _write_private_envelope(output_path, envelope)
    return {
        "slot_id": ids["slot"], "delivery_id": ids["delivery"],
        "revision_id": ids["revision"], "command_id": row["id"],
        "envelope_file": str(output_path),
    }


def _write_private_envelope(path: Path, envelope: dict[str, Any]) -> None:
    path = path.expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise ValueError("TEST command envelope output already exists; choose a new path.") from error
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(json.dumps(envelope, ensure_ascii=False, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, object]:
    if environ.get("GE_ENV", "").strip().casefold() != "test":
        raise ValueError("TEST command validation and sending require GE_ENV=test.")
    path = args.envelope_file or (
        Path(environ["GE_TEST_COMMAND_ENVELOPE_FILE"])
        if environ.get("GE_TEST_COMMAND_ENVELOPE_FILE")
        else None
    )
    factory_result: dict[str, object] = {}
    if args.create_command:
        if path is None:
            raise ValueError("--create-command requires --envelope-file or GE_TEST_COMMAND_ENVELOPE_FILE.")
        factory_result = _create_test_command(environ, path)
    if path is None:
        raise ValueError("Provide --envelope-file or GE_TEST_COMMAND_ENVELOPE_FILE.")
    channel_key, platform, channel_id, page_id = _test_target(environ)
    route_reference = _test_destination_reference(page_id, channel_key)
    envelope = _read_private_envelope(path)
    tokens = CapabilityTokenManager(parse_key_ring(environ.get("GE_CAPABILITY_KEYS", "")))
    _validate_test_envelope(
        envelope,
        expected_channel_id=channel_id,
        expected_page_id=page_id,
        expected_channel_key=channel_key,
        expected_platform=platform,
        now_ms=time.time_ns() // 1_000_000,
        tokens=tokens,
    )

    summary: dict[str, object] = {
        "environment": "test",
        "channel_id": channel_id,
        "remote_page_id": page_id,
        "command_id": envelope["command_id"],
        "envelope_sha256": hashlib.sha256(canonical_json_bytes(envelope)).hexdigest(),
        "network_request_sent": False,
        "post_verified": False,
    }
    summary.update(factory_result)
    if not args.send:
        summary["result"] = "DRY_RUN_VALIDATED"
        return summary

    confirm_id = args.confirm_test_page_id or ""
    if confirm_id != page_id:
        raise ValueError("--send requires --confirm-test-remote-id to match the verified TEST destination ID.")
    route_url = environ.get(route_reference, "").strip()
    parsed_route = urlsplit(route_url)
    if (
        parsed_route.scheme != "https"
        or not parsed_route.hostname
        or parsed_route.username
        or parsed_route.password
        or parsed_route.fragment
    ):
        raise ValueError(f"{route_reference} must be a configured HTTPS TEST route.")

    disposition, status = _post_to_test_route(route_url, envelope)
    summary.update(
        {
            "network_request_sent": True,
            "webhook_disposition": disposition,
            "http_status": status,
            "post_verified": False,
        }
    )
    return summary


def main() -> int:
    args = _parser().parse_args()
    try:
        result = run(args, dict(os.environ))
    except (ValueError, OSError) as error:
        print(json.dumps({"result": "REFUSED", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result.get("webhook_disposition") not in {None, "ACK"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

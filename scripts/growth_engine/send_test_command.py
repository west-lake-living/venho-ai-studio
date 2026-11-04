from __future__ import annotations

import argparse
import http.client
import hashlib
import json
import os
import re
import socket
import stat
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


_REPOSITORY_ROOT = str(Path(__file__).resolve().parents[2])
if _REPOSITORY_ROOT not in sys.path:
    sys.path.insert(0, _REPOSITORY_ROOT)

from growth_engine.adapters.outbound.security.capability_tokens import (
    CapabilityTokenManager,
    parse_key_ring,
)
from growth_engine.domain.kernel.hashing import canonical_json_bytes


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
        "--send",
        action="store_true",
        help="Send to the webhook variable referenced by the TEST channel manifest; dry run is the default.",
    )
    parser.add_argument(
        "--confirm-test-page-id",
        help="Must exactly match GE_TEST_REMOTE_PAGE_ID when --send is set.",
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
    if envelope["channel_id"] != expected_channel_id or envelope["remote_page_id"] != expected_page_id:
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


def _test_destination_reference(expected_page_id: str) -> str:
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
    test_channels = [
        channel
        for channel in configuration["channels"]
        if isinstance(channel, dict)
        and channel.get("channel_id") == "page_test"
        and channel.get("environment") == "test"
        and channel.get("platform") == "facebook"
    ]
    if len(test_channels) != 1:
        raise ValueError("Exactly one TEST Facebook destination must be configured.")
    test_channel = test_channels[0]
    if (
        test_channel.get("remote_page_id") != expected_page_id
        or expected_page_id == "REQUIRED_FROM_P0"
    ):
        raise ValueError("TEST Page ID must match the verified page_test manifest entry.")
    route_reference = test_channel.get("make_route_ref")
    if not isinstance(route_reference, str) or route_reference != "GE_MAKE_WEBHOOK_URL_PAGE_TEST":
        raise ValueError("TEST channel must use its dedicated TEST webhook variable.")
    return route_reference


def run(args: argparse.Namespace, environ: dict[str, str]) -> dict[str, object]:
    path = args.envelope_file or (
        Path(environ["GE_TEST_COMMAND_ENVELOPE_FILE"])
        if environ.get("GE_TEST_COMMAND_ENVELOPE_FILE")
        else None
    )
    if path is None:
        raise ValueError("Provide --envelope-file or GE_TEST_COMMAND_ENVELOPE_FILE.")
    channel_id = environ.get("GE_TEST_CHANNEL_ID", "").strip()
    page_id = environ.get("GE_TEST_REMOTE_PAGE_ID", "").strip()
    if not channel_id or channel_id == "REQUIRED_FROM_P0" or not page_id or page_id == "REQUIRED_FROM_P0":
        raise ValueError("TEST channel UUID and remote Page ID must be verified before sending.")
    route_reference = _test_destination_reference(page_id)
    envelope = _read_private_envelope(path)
    tokens = CapabilityTokenManager(parse_key_ring(environ.get("GE_CAPABILITY_KEYS", "")))
    _validate_test_envelope(
        envelope,
        expected_channel_id=channel_id,
        expected_page_id=page_id,
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
    if not args.send:
        summary["result"] = "DRY_RUN_VALIDATED"
        return summary

    confirm_id = args.confirm_test_page_id or ""
    if confirm_id != page_id:
        raise ValueError("--send requires --confirm-test-page-id to match the verified TEST Page ID.")
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

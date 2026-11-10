#!/usr/bin/env python3
"""Safely prepare and optionally send one fb_hanoi TEST command."""

from __future__ import annotations

import getpass
import hashlib
import hmac
import http.client
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qsl, quote, urlsplit
from uuid import UUID, uuid4


CHANNEL_KEY = "fb_hanoi"
MANIFEST_CHANNEL_ID = "page_test"
REMOTE_PAGE_ID = "1363761820162798"
WEBHOOK_VARIABLE = "GE_MAKE_WEBHOOK_URL_PAGE_TEST"
ENV_VARIABLES = {
    "GE_TEST_CHANNEL_KEY": CHANNEL_KEY,
    "GE_TEST_REMOTE_PAGE_ID": REMOTE_PAGE_ID,
}
SAFE_OS_ENV_KEYS = ("HOME", "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR")
VALID_COMMAND_STATES = {"PENDING", "DELIVERING", "ACKED", "AUTHORIZED", "CANCELLED", "EXPIRED"}
VALID_EXECUTION_STATES = {"AUTHORIZED", "REPORTED", "NO_SIDE_EFFECT", "UNKNOWN"}
VALID_RECEIPT_STATES = {"RECEIVED", "APPLIED", "QUARANTINED", "IGNORED_STALE", "TIMEOUT"}
VALID_OUTCOMES = {"POST_CREATED", "REJECTED_NO_SIDE_EFFECT", "OUTCOME_UNKNOWN"}
VALID_FAILED_STEPS = {"FETCH_MEDIA", "AUTHORIZE", "CREATE_POST"}
FACEBOOK_POST_ID_RE = re.compile(r"^1363761820162798_[0-9]{1,40}$")
MEDIA_PATH_RE = re.compile(r"^/media/publish/([0-9a-f]{64})\.jpg$")
MAX_MEDIA_BYTES = 5 * 1024 * 1024


class RunTestError(Exception):
    """Safe-to-display operational error; never includes secret values."""


class RunTestRefused(RunTestError):
    """A child command refused before sending its TEST webhook."""

    def __init__(self, reason: Any) -> None:
        self.reason_code = _safe_refusal_reason(reason)
        super().__init__(f"REFUSED reason={self.reason_code}")


def _safe_refusal_reason(reason: Any) -> str:
    if reason == "TEST channel already exists in this database; use an isolated TEST database.":
        return "TEST_CHANNEL_ALREADY_EXISTS"
    if isinstance(reason, str) and reason.startswith("Missing TEST runtime settings: "):
        return "TEST_RUNTIME_SETTINGS_MISSING"
    if reason == "TEST Graph API version must be verified before creating a command.":
        return "TEST_GRAPH_API_VERSION_UNVERIFIED"
    if reason == "TEST destination ID must match the test manifest and differ from production IDs.":
        return "TEST_DESTINATION_ID_INVALID"
    if reason == "TEST destination principal must match the selected channel key.":
        return "TEST_DESTINATION_PRINCIPAL_INVALID"
    return "REFUSED_UNCLASSIFIED"


def _read_env_file(path: Path) -> tuple[list[str], dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise RunTestError("test_env_file_unavailable")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RunTestError("test_env_file_must_be_mode_600")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RunTestError("test_env_file_unreadable") from error

    values: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise RunTestError("test_env_file_format_invalid")
        name, value = stripped.split("=", 1)
        if not re.fullmatch(r"GE_[A-Z0-9_]+", name) or name in values:
            raise RunTestError("test_env_file_format_invalid")
        values[name] = value
    return lines, values


def _safe_webhook_url(value: str) -> bool:
    if not value or value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return False
    hostname = (parsed.hostname or "").casefold()
    return (
        parsed.scheme == "https"
        and bool(hostname)
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
        and not hostname.endswith(".invalid")
        and hostname != "ge-test.venhohotel.com"
    )


def _test_paths(home: Path, values: dict[str, str]) -> tuple[Path, Path]:
    test_state = (home / "venho/state/growth-engine-test").resolve()
    try:
        database_setting = Path(values["GE_DB_PATH"]).expanduser()
        media_setting = Path(values["GE_MEDIA_ROOT"]).expanduser()
        if database_setting.is_symlink() or media_setting.is_symlink():
            raise RunTestError("test_db_or_media_path_must_not_be_symlink")
        database = database_setting.resolve()
        media_root = media_setting.resolve()
    except (KeyError, OSError) as error:
        raise RunTestError("test_db_or_media_path_invalid") from error
    if test_state not in database.parents or test_state not in media_root.parents:
        raise RunTestError("test_db_or_media_path_not_isolated")
    if database.is_symlink() or media_root.is_symlink():
        raise RunTestError("test_db_or_media_path_must_not_be_symlink")
    if values.get("GE_ENV") != "test":
        raise RunTestError("environment_must_be_test")
    if values.get("GE_PUBLIC_BASE_URL") != "https://ge-test.venhohotel.com":
        raise RunTestError("test_public_base_url_mismatch")
    for name in ("GE_CAPABILITY_KEYS", "GE_SERVICE_TOKENS"):
        if not values.get(name) or "REQUIRED_FROM_P0" in values[name]:
            raise RunTestError("test_runtime_secret_missing")
    return database, media_root


def _write_env_values(path: Path, lines: list[str], values: dict[str, str], updates: dict[str, str]) -> bool:
    for name, expected in updates.items():
        existing = values.get(name)
        if existing and existing != expected and "REQUIRED_FROM_P0" not in existing:
            raise RunTestError("test_env_setting_conflicts_with_first_run")
    effective = {name: values.get(name, "") for name in updates}
    effective.update(updates)
    if all(values.get(name) == value for name, value in effective.items()):
        return False

    rendered: list[str] = []
    written: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            rendered.append(line)
            continue
        name = stripped.split("=", 1)[0]
        if name in updates:
            if name not in written:
                rendered.append(f"{name}={updates[name]}")
                written.add(name)
        else:
            rendered.append(line)
    for name, value in updates.items():
        if name not in written:
            rendered.append(f"{name}={value}")
    encoded = ("\n".join(rendered) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".growth-engine-test-env.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise RunTestError("test_env_atomic_update_failed") from error
    return True


def add_first_run_settings(env_path: Path, webhook_url: str, home: Path) -> tuple[dict[str, str], bool]:
    if not _safe_webhook_url(webhook_url):
        raise RunTestError("test_webhook_url_invalid")
    lines, values = _read_env_file(env_path)
    _test_paths(home, values)
    for name, expected in ENV_VARIABLES.items():
        existing = values.get(name)
        if existing and existing != expected:
            raise RunTestError("test_env_target_conflicts_with_fb_hanoi")
    channel_id = values.get("GE_TEST_CHANNEL_ID", "")
    if channel_id:
        try:
            if str(UUID(channel_id)) != channel_id:
                raise ValueError
        except ValueError as error:
            raise RunTestError("test_channel_id_must_be_canonical_uuid") from error
    else:
        channel_id = str(uuid4())
    existing_webhook = values.get(WEBHOOK_VARIABLE, "")
    if existing_webhook and existing_webhook != webhook_url and "REQUIRED_FROM_P0" not in existing_webhook:
        raise RunTestError("test_webhook_env_value_conflicts")
    updates = {**ENV_VARIABLES, "GE_TEST_CHANNEL_ID": channel_id}
    updates[WEBHOOK_VARIABLE] = webhook_url
    changed = _write_env_values(env_path, lines, values, updates)
    _, refreshed = _read_env_file(env_path)
    _test_paths(home, refreshed)
    return refreshed, changed


def validate_manifest(manifest: dict[str, Any]) -> None:
    channels = manifest.get("channels")
    if not isinstance(channels, list):
        raise RunTestError("test_channel_manifest_invalid")
    matches = [
        item
        for item in channels
        if isinstance(item, dict)
        and item.get("channel_id") == MANIFEST_CHANNEL_ID
        and item.get("environment") == "test"
        and item.get("platform") == "facebook"
    ]
    if len(matches) != 1:
        raise RunTestError("test_fb_hanoi_manifest_target_missing_or_duplicate")
    channel = matches[0]
    principals = channel.get("service_principals")
    graph_version = channel.get("graph_api_version")
    if (
        channel.get("remote_page_id") != REMOTE_PAGE_ID
        or channel.get("make_route_ref") != WEBHOOK_VARIABLE
        or not isinstance(principals, dict)
        or principals.get(CHANNEL_KEY) != "make-fb-hanoi"
    ):
        raise RunTestError("test_fb_hanoi_manifest_does_not_match_target")
    if not isinstance(graph_version, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+", graph_version):
        raise RunTestError("test_fb_hanoi_graph_api_version_not_configured")


def load_manifest(repo_root: Path) -> dict[str, Any]:
    try:
        import yaml

        path = repo_root / "config/projects/venho_hotel/growth_engine/channels.yaml"
        result = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise RunTestError("test_channel_manifest_unavailable") from error
    if not isinstance(result, dict):
        raise RunTestError("test_channel_manifest_invalid")
    validate_manifest(result)
    return result


def _child_environment(values: dict[str, str], operating_system: dict[str, str]) -> dict[str, str]:
    child = {name: operating_system[name] for name in SAFE_OS_ENV_KEYS if operating_system.get(name)}
    child.update(values)
    child["GE_ENV"] = "test"
    if child.get("GE_TEST_CHANNEL_KEY") != CHANNEL_KEY:
        raise RunTestError("test_channel_key_not_fb_hanoi")
    try:
        if str(UUID(child.get("GE_TEST_CHANNEL_ID", ""))) != child.get("GE_TEST_CHANNEL_ID"):
            raise ValueError
    except ValueError as error:
        raise RunTestError("test_channel_id_must_be_canonical_uuid") from error
    if child.get("GE_TEST_REMOTE_PAGE_ID") != REMOTE_PAGE_ID:
        raise RunTestError("test_remote_page_id_not_verified")
    return child


def _read_envelope_summary(path: Path, expected_channel_id: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RunTestError("test_envelope_file_unavailable")
    metadata = path.stat()
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RunTestError("test_envelope_file_must_be_mode_600")
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        command_id = str(UUID(envelope["command_id"]))
        execute_before_ms = envelope["execute_before_ms"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, ValueError, TypeError) as error:
        raise RunTestError("test_envelope_metadata_invalid") from error
    if (
        envelope.get("channel_key") != CHANNEL_KEY
        or envelope.get("channel_id") != expected_channel_id
        or envelope.get("remote_page_id") != REMOTE_PAGE_ID
        or type(execute_before_ms) is not int
    ):
        raise RunTestError("test_envelope_target_mismatch")
    execute_before = datetime.fromtimestamp(execute_before_ms / 1000, timezone.utc).isoformat(timespec="seconds")
    return {
        "channel_key": CHANNEL_KEY,
        "remote_page_id": REMOTE_PAGE_ID,
        "command_id": command_id,
        "execute_before": execute_before,
    }


def _read_envelope_media_url(path: Path, public_base_url: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise RunTestError("test_envelope_file_unavailable")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RunTestError("test_envelope_file_must_be_mode_600")
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        media_url = envelope["media_url"]
        parsed = urlsplit(media_url)
        public = urlsplit(public_base_url)
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RunTestError("test_envelope_media_url_invalid") from error
    match = MEDIA_PATH_RE.fullmatch(parsed.path) if isinstance(media_url, str) else None
    valid_token = len(query) == 1 and query[0][0] == "t" and len(query[0][1].split(".")) == 5
    if (
        not isinstance(media_url, str)
        or not match
        or not valid_token
        or parsed.scheme != "https"
        or parsed.netloc != public.netloc
        or public.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise RunTestError("test_envelope_media_url_invalid")
    return media_url


def check_local_media_url(
    media_url: str,
    public_base_url: str,
    *,
    connection_factory: Callable[..., Any] = http.client.HTTPConnection,
) -> None:
    """Fetch the signed TEST media directly from the local API without printing its URL."""
    try:
        parsed = urlsplit(media_url)
        public = urlsplit(public_base_url)
        match = MEDIA_PATH_RE.fullmatch(parsed.path)
        query = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        if (
            not match
            or parsed.scheme != "https"
            or parsed.netloc != public.netloc
            or public.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.fragment
            or len(query) != 1
            or query[0][0] != "t"
            or len(query[0][1].split(".")) != 5
        ):
            raise RunTestError("test_media_preflight_failed")
        request_target = parsed.path + "?" + parsed.query
        connection = connection_factory("127.0.0.1", 8023, timeout=15)
        try:
            connection.request("GET", request_target, headers={"Host": public.netloc})
            response = connection.getresponse()
            content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().casefold()
            cache_control = {
                directive.strip().casefold()
                for directive in response.getheader("Cache-Control", "").split(",")
            }
            body = response.read(MAX_MEDIA_BYTES + 1)
            if (
                response.status != 200
                or content_type != "image/jpeg"
                or not {"private", "no-store"}.issubset(cache_control)
                or not body
                or len(body) > MAX_MEDIA_BYTES
                or not hmac.compare_digest(hashlib.sha256(body).hexdigest(), match.group(1))
            ):
                raise RunTestError("test_media_preflight_failed")
        finally:
            connection.close()
    except RunTestError:
        raise
    except (OSError, http.client.HTTPException, TypeError, ValueError) as error:
        raise RunTestError("test_media_preflight_failed") from error


def _run_send_cli(
    repo_root: Path,
    envelope_path: Path,
    child_env: dict[str, str],
    *,
    create: bool,
    send: bool,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any] | None:
    script = repo_root / "scripts/growth_engine/send_test_command.py"
    args = [sys.executable, str(script), "--envelope-file", str(envelope_path)]
    if create:
        args.append("--create-command")
    if send:
        args.extend(("--send", "--confirm-test-remote-id", REMOTE_PAGE_ID))
    try:
        result = runner(
            args,
            cwd=str(repo_root),
            env=child_env,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    try:
        summary = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as error:
        raise RunTestError("send_test_command_return_invalid") from error
    if not isinstance(summary, dict):
        raise RunTestError("send_test_command_return_invalid")
    if summary.get("result") == "REFUSED":
        raise RunTestRefused(summary.get("reason"))
    if result.returncode not in ({0, 1} if send else {0}):
        raise RunTestError("send_test_command_refused")
    if send and summary.get("network_request_sent") is not True:
        raise RunTestError("send_test_command_not_sent")
    return summary


def _safe_value(value: Any, allowed: set[str] | None = None) -> str:
    if not isinstance(value, str):
        return "NONE"
    if allowed is not None:
        return value if value in allowed else "UNKNOWN"
    return "REDACTED"


def read_db_status(database_path: Path, command_id: str) -> dict[str, str]:
    if database_path.is_symlink() or not database_path.is_file():
        return {"command_state": "NOT_FOUND", "execution_state": "NOT_FOUND", "receipt_state": "NOT_FOUND", "outcome": "NONE", "platform_post_id": "NONE", "failed_step": "NONE"}
    uri = f"file:{quote(str(database_path.resolve()))}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=1.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        command = connection.execute(
            "SELECT c.state, d.id AS delivery_id, d.platform_post_id "
            "FROM outbox_commands c JOIN deliveries d ON d.id=c.delivery_id WHERE c.id=?",
            (command_id,),
        ).fetchone()
        execution = connection.execute(
            "SELECT id, state, external_outcome, grant_id FROM executions WHERE command_id=?",
            (command_id,),
        ).fetchone()
        receipts = connection.execute(
            "SELECT processing_state, body_json FROM receipt_inbox "
            "WHERE json_extract(body_json, '$.command_id')=? ORDER BY received_at DESC LIMIT 1",
            (command_id,),
        ).fetchone()
        connection.close()
    except sqlite3.Error as error:
        raise RunTestError("test_database_read_failed") from error

    receipt_body: dict[str, Any] = {}
    if receipts is not None:
        try:
            parsed_body = json.loads(receipts["body_json"])
            if isinstance(parsed_body, dict):
                receipt_body = parsed_body
        except (json.JSONDecodeError, TypeError):
            receipt_body = {}
    execution_outcome = execution["external_outcome"] if execution is not None else None
    delivery_post_id = command["platform_post_id"] if command is not None else None
    outcome = receipt_body.get("outcome") or execution_outcome
    post_id = receipt_body.get("platform_post_id") or delivery_post_id
    return {
        "command_state": _safe_value(command["state"] if command is not None else None, VALID_COMMAND_STATES),
        "execution_state": _safe_value(execution["state"] if execution is not None else None, VALID_EXECUTION_STATES),
        "receipt_state": _safe_value(receipts["processing_state"] if receipts is not None else None, VALID_RECEIPT_STATES),
        "outcome": _safe_value(outcome, VALID_OUTCOMES),
        "platform_post_id": post_id if isinstance(post_id, str) and FACEBOOK_POST_ID_RE.fullmatch(post_id) else "REDACTED",
        "failed_step": _safe_value(receipt_body.get("failed_step"), VALID_FAILED_STEPS),
    }


def wait_for_db_status(
    database_path: Path,
    command_id: str,
    *,
    timeout_seconds: int = 120,
    interval_seconds: int = 2,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[dict[str, str], bool]:
    deadline = monotonic() + timeout_seconds
    while True:
        status = read_db_status(database_path, command_id)
        if status["receipt_state"] != "NOT_FOUND":
            return status, False
        remaining = deadline - monotonic()
        if remaining <= 0:
            return status, True
        sleep(min(interval_seconds, remaining))


def _emit_summary(envelope_summary: dict[str, Any], emit: Callable[[str], None]) -> None:
    for key in ("channel_key", "remote_page_id", "command_id", "execute_before"):
        emit(f"{key}={envelope_summary[key]}")


def run_first_command(
    *,
    home: Path | None = None,
    repo_root: Path | None = None,
    input_fn: Callable[[str], str] = input,
    secret_input: Callable[[str], str] = getpass.getpass,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    media_preflight: Callable[[str, str], None] = check_local_media_url,
    emit: Callable[[str], None] = print,
    database_wait_seconds: int = 120,
) -> int:
    home = (home or Path(os.environ.get("HOME", "~"))).expanduser().resolve()
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    if repo_root != (home / "venho/gc2-src").resolve():
        raise RunTestError("run_from_home_venho_gc2_src_only")
    load_manifest(repo_root)
    env_path = home / "venho/secrets/growth-engine-test.env"
    webhook_url = secret_input("Webhook URL TEST (hidden): ")
    values, _changed = add_first_run_settings(env_path, webhook_url, home)
    database_path, _media_root = _test_paths(home, values)
    state_root = (home / "venho/state/growth-engine-test").resolve()
    if state_root.is_symlink() or not state_root.is_dir():
        raise RunTestError("test_state_directory_unavailable")
    lock_path = state_root / ".run-test-command.lock"
    try:
        lock_path.mkdir(mode=0o700)
    except FileExistsError as error:
        raise RunTestError("another_test_command_run_is_active") from error
    try:
        envelope_path = state_root / "fb_hanoi-first-command.envelope.json"
        child_env = _child_environment(values, dict(os.environ))
        if envelope_path.exists():
            _run_send_cli(
                repo_root,
                envelope_path,
                child_env,
                create=False,
                send=False,
                runner=runner,
            )
        else:
            _run_send_cli(
                repo_root,
                envelope_path,
                child_env,
                create=True,
                send=False,
                runner=runner,
            )
        envelope_summary = _read_envelope_summary(envelope_path, values["GE_TEST_CHANNEL_ID"])
        media_url = _read_envelope_media_url(envelope_path, values["GE_PUBLIC_BASE_URL"])
        _emit_summary(envelope_summary, emit)
        try:
            media_preflight(media_url, values["GE_PUBLIC_BASE_URL"])
        except RunTestError:
            emit("media_preflight=FAIL")
            raise
        emit("media_preflight=PASS")

        if input_fn("Gõ ACTIVE để xác nhận scenario TEST đang Active; Enter khác để dừng: ") != "ACTIVE":
            emit("Chưa xác nhận scenario Active; không gửi webhook. Envelope TEST mode 600 được giữ lại.")
            return 0
        if input_fn("Gõ GUI để gửi lệnh đăng thử lên Page TEST") != "GUI":
            emit("Không gửi lệnh; envelope TEST mode 600 được giữ lại.")
            return 0

        refused_reason: str | None = None
        try:
            send_result = _run_send_cli(
                repo_root,
                envelope_path,
                child_env,
                create=False,
                send=True,
                runner=runner,
            )
        except RunTestRefused as error:
            refused_reason = error.reason_code
            send_result = None
            emit(f"result=REFUSED reason={refused_reason}")
        except RunTestError:
            # A malformed/ambiguous child response after GUI must be reconciled locally, never retried.
            send_result = None
        disposition = "UNKNOWN"
        if refused_reason is not None:
            disposition = "NOT_SENT"
        if send_result is not None:
            candidate = send_result.get("webhook_disposition")
            disposition = candidate if candidate in {"ACK", "RETRYABLE", "FATAL"} else "UNKNOWN"
        emit(f"webhook_disposition={disposition}")
        if refused_reason is not None:
            status = read_db_status(database_path, envelope_summary["command_id"])
            timed_out = False
        else:
            status, timed_out = wait_for_db_status(
                database_path,
                envelope_summary["command_id"],
                timeout_seconds=database_wait_seconds,
                sleep=sleep,
                monotonic=monotonic,
            )
        emit(f"command_state={status['command_state']}")
        emit(f"execution_state={status['execution_state']}")
        emit(f"receipt_state={status['receipt_state']}")
        emit(f"outcome={status['outcome']}")
        emit(f"platform_post_id={status['platform_post_id']}")
        emit(f"failed_step={status['failed_step']}")
        if refused_reason is not None:
            emit("receipt_wait=NOT_SENT; child refused before webhook request")
        elif timed_out:
            emit("receipt_wait=TIMEOUT_120S; no resend was attempted")
        else:
            emit("receipt_wait=RECEIVED")
        return 0
    finally:
        try:
            lock_path.rmdir()
        except OSError:
            pass


def main() -> int:
    if not sys.stdin.isatty():
        print("run-test-command: interactive terminal required; no secrets were read", file=sys.stderr)
        return 2
    try:
        return run_first_command()
    except RunTestError as error:
        print(f"run-test-command: {error}", file=sys.stderr)
        return 2
    except Exception:
        print("run-test-command: failed safely; no secret values were displayed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

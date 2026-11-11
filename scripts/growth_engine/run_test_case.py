#!/usr/bin/env python3
"""Run one explicitly confirmed Make TEST case against a fresh isolated TEST DB."""

from __future__ import annotations

import getpass
import json
import os
import re
import sqlite3
import stat
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.request import urlopen
from uuid import uuid4
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.growth_engine.run_test_command import (  # noqa: E402
    RunTestError,
    _safe_webhook_url,
    check_local_media_url,
)
from scripts.growth_engine.send_test_command import _mutate_test_envelope  # noqa: E402


API_BASE_UNIT = "growth-engine-api-test-src"
API_PORT = 8023
EXPECTED_TEST_HOST = "https://ge-test.venhohotel.com"
FINAL_RECEIPTS = {"APPLIED", "QUARANTINED", "IGNORED_STALE", "TIMEOUT"}
FINAL_EXECUTIONS = {"REPORTED", "NO_SIDE_EFFECT", "UNKNOWN"}
ALLOWED_COMMAND_STATES = {"PENDING", "DELIVERING", "ACKED", "AUTHORIZED", "CANCELLED", "EXPIRED"}
ALLOWED_RECEIPT_STATES = {"RECEIVED", "APPLIED", "QUARANTINED", "IGNORED_STALE", "TIMEOUT"}
ALLOWED_EXECUTION_STATES = {"AUTHORIZED", "REPORTED", "NO_SIDE_EFFECT", "UNKNOWN"}


@dataclass(frozen=True)
class CaseSpec:
    name: str
    channel_key: str
    platform: str
    manifest_channel_id: str
    remote_id: str
    remote_env_key: str
    webhook_env_key: str
    mutation: str | None = None


CASES = {
    "ig_venho": CaseSpec(
        "ig_venho", "ig_venho", "instagram", "ig_test", "17841472240799413",
        "GE_TEST_REMOTE_IG_ID", "GE_MAKE_WEBHOOK_URL_IG_TEST",
    ),
    "duplicate": CaseSpec(
        "duplicate", "fb_hanoi", "facebook", "page_test", "1363761820162798",
        "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST",
    ),
    "broken-media": CaseSpec(
        "broken-media", "fb_hanoi", "facebook", "page_test", "1363761820162798",
        "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST", "broken_media_signature",
    ),
    "bad-token": CaseSpec(
        "bad-token", "fb_hanoi", "facebook", "page_test", "1363761820162798",
        "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST", "invalid_command_token",
    ),
    "sequential": CaseSpec(
        "sequential", "fb_hanoi", "facebook", "page_test", "1363761820162798",
        "GE_TEST_REMOTE_PAGE_ID", "GE_MAKE_WEBHOOK_URL_PAGE_TEST",
    ),
}


class TestCaseError(Exception):
    """Safe operational error code; never includes environment or request values."""


def _read_env(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise TestCaseError("test_env_file_unavailable_or_not_mode_600")
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise TestCaseError("test_env_file_unreadable") from error
    for line in lines:
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        if "=" not in value:
            raise TestCaseError("test_env_file_format_invalid")
        name, item = value.split("=", 1)
        if not re.fullmatch(r"GE_[A-Z0-9_]+", name) or name in values or "\n" in item or "\r" in item:
            raise TestCaseError("test_env_file_format_invalid")
        values[name] = item
    return values


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    content = "".join(f"{key}={value}\n" for key, value in sorted(values.items()))
    if any("\n" in value or "\r" in value for value in values.values()):
        raise TestCaseError("test_env_value_invalid")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, 0o600)


def _validate_base_env(values: dict[str, str], home: Path) -> Path:
    if values.get("GE_ENV", "").casefold() != "test":
        raise TestCaseError("environment_must_be_test")
    if values.get("GE_PUBLIC_BASE_URL") != EXPECTED_TEST_HOST:
        raise TestCaseError("test_public_base_url_mismatch")
    for key in ("GE_CAPABILITY_KEYS", "GE_SERVICE_TOKENS"):
        if not values.get(key) or "REQUIRED_FROM_P0" in values[key]:
            raise TestCaseError("test_runtime_secret_missing")
    state_root = (home / "venho/state/growth-engine-test").resolve()
    for name in ("GE_DB_PATH", "GE_MEDIA_ROOT"):
        raw = values.get(name, "")
        if not raw:
            raise TestCaseError("test_db_or_media_path_missing")
        candidate = Path(raw).expanduser()
        if candidate.is_symlink():
            raise TestCaseError("test_db_or_media_path_must_not_be_symlink")
        resolved = candidate.resolve()
        if state_root not in resolved.parents:
            raise TestCaseError("test_db_or_media_path_not_isolated")
    return state_root


def _manifest_target(repo_root: Path, spec: CaseSpec) -> None:
    try:
        import yaml

        document = yaml.safe_load(
            (repo_root / "config/projects/venho_hotel/growth_engine/channels.yaml").read_text(encoding="utf-8")
        )
    except Exception as error:
        raise TestCaseError("test_channel_manifest_unavailable") from error
    channels = document.get("channels") if isinstance(document, dict) else None
    matches = [
        item for item in channels or []
        if isinstance(item, dict)
        and item.get("channel_id") == spec.manifest_channel_id
        and item.get("environment") == "test"
        and item.get("platform") == spec.platform
    ]
    if len(matches) != 1:
        raise TestCaseError("test_manifest_target_missing_or_ambiguous")
    item = matches[0]
    remote_field = "remote_account_id" if spec.platform == "instagram" else "remote_page_id"
    principal = {"fb_hanoi": "make-fb-hanoi", "ig_venho": "make-ig"}[spec.channel_key]
    principals = item.get("service_principals")
    configured_principal = (
        principals.get(spec.channel_key)
        if isinstance(principals, dict)
        else item.get("service_principal")
    )
    graph_version = item.get("graph_api_version")
    if (
        item.get(remote_field) != spec.remote_id
        or item.get("make_route_ref") != spec.webhook_env_key
        or configured_principal != principal
        or not isinstance(graph_version, str)
        or not re.fullmatch(r"v[0-9]+\.[0-9]+", graph_version)
    ):
        raise TestCaseError("test_manifest_target_not_verified")


def _prepare_case_env(
    *,
    base_values: dict[str, str],
    state_root: Path,
    secrets_root: Path,
    spec: CaseSpec,
    webhook_url: str,
    run_id: str,
) -> tuple[dict[str, str], Path, Path, Path]:
    run_root = state_root / "cases" / f"{spec.name}-{run_id}"
    run_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    media_root = run_root / "media"
    media_root.mkdir(mode=0o700)
    database_path = run_root / "growth_engine.db"
    env_values = dict(base_values)
    env_values.update(
        {
            "GE_DB_PATH": str(database_path),
            "GE_MEDIA_ROOT": str(media_root),
            "GE_ENV": "test",
            "GE_TEST_CHANNEL_KEY": spec.channel_key,
            "GE_TEST_CHANNEL_ID": str(uuid4()),
            spec.remote_env_key: spec.remote_id,
            spec.webhook_env_key: webhook_url,
        }
    )
    env_path = secrets_root / "growth-engine-test-cases" / f"{spec.name}-{run_id}.env"
    _write_env(env_path, env_values)
    return env_values, run_root, database_path, env_path


def _run_process(
    command: list[str],
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    env: dict[str, str] | None = None,
    timeout: int = 45,
) -> subprocess.CompletedProcess[str]:
    try:
        return runner(command, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TestCaseError("test_runtime_command_failed") from error


def _systemd_transient(
    *, runner: Callable[..., subprocess.CompletedProcess[str]],
    env_path: Path, unit: str, args: list[str], wait: bool,
) -> None:
    command = ["systemd-run", "--user"]
    if wait:
        command.extend(("--pipe", "--wait", "--collect"))
    command.extend(
        (
            f"--unit={unit}",
            f"--property=EnvironmentFile={env_path}",
            f"--property=WorkingDirectory={REPO_ROOT}",
            "--setenv=GE_ENV=test",
            *args,
        )
    )
    result = _run_process(command, runner=runner, timeout=120 if wait else 30)
    if result.returncode != 0:
        raise TestCaseError("test_transient_unit_failed")


def _unit_active(unit: str, runner: Callable[..., subprocess.CompletedProcess[str]]) -> bool:
    result = _run_process(["systemctl", "--user", "is-active", unit], runner=runner, timeout=15)
    return result.returncode == 0 and result.stdout.strip() == "active"


def _restore_base_api(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    env_path: Path,
    repo_root: Path,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    ready: Callable[..., None] | None = None,
) -> str | None:
    """Restart an existing transient unit or recreate it if systemd unloaded it."""

    def is_ready() -> bool:
        try:
            (ready or _wait_local_api)(timeout_seconds=30, sleep=sleep, monotonic=monotonic)
            return True
        except TestCaseError:
            return False

    reset = ["systemctl", "--user", "reset-failed", API_BASE_UNIT]
    _run_process(reset, runner=runner, timeout=15)

    restarted = _run_process(
        ["systemctl", "--user", "restart", API_BASE_UNIT], runner=runner, timeout=30
    )
    if restarted.returncode == 0 and is_ready():
        return "restart"

    # systemd-run units can be unloaded when stopped, so `systemctl start` alone
    # may have no unit definition to start. Recreate with the original TEST env.
    _run_process(["systemctl", "--user", "stop", API_BASE_UNIT], runner=runner, timeout=20)
    _run_process(reset, runner=runner, timeout=15)
    command = [
        "systemd-run",
        "--user",
        f"--unit={API_BASE_UNIT}",
        f"--property=EnvironmentFile={env_path}",
        f"--property=WorkingDirectory={repo_root}",
        "--setenv=GE_ENV=test",
        str(repo_root / ".venv/bin/venho-engine"),
        "api",
        "--host",
        "127.0.0.1",
        "--port",
        str(API_PORT),
    ]
    recreated = _run_process(command, runner=runner, timeout=30)
    if recreated.returncode == 0 and is_ready():
        return "transient-recreated"

    started = _run_process(
        ["systemctl", "--user", "start", API_BASE_UNIT], runner=runner, timeout=30
    )
    if started.returncode == 0 and is_ready():
        return "start-existing"
    return None


def _wait_local_api(
    *, timeout_seconds: int, sleep: Callable[[float], None], monotonic: Callable[[], float]
) -> None:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        try:
            with urlopen(f"http://127.0.0.1:{API_PORT}/health/ready", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        sleep(1)
    raise TestCaseError("test_api_case_not_ready")


def _database_counts(database_path: Path, command_id: str) -> dict[str, int]:
    uri = f"file:{database_path.resolve()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.execute("PRAGMA query_only=ON")
        execution_count = connection.execute(
            "SELECT count(*) FROM executions WHERE command_id=?", (command_id,)
        ).fetchone()[0]
        receipt_count = connection.execute(
            "SELECT count(*) FROM receipt_inbox WHERE json_extract(body_json, '$.command_id')=?",
            (command_id,),
        ).fetchone()[0]
        connection.close()
    except sqlite3.Error as error:
        raise TestCaseError("test_database_read_failed") from error
    return {"execution_count": int(execution_count), "receipt_count": int(receipt_count)}


def _read_status(database_path: Path, command_id: str, spec: CaseSpec) -> dict[str, Any]:
    uri = f"file:{database_path.resolve()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        command = connection.execute(
            "SELECT c.state AS outbox_command_state, d.id AS delivery_id, d.platform_post_id "
            "FROM outbox_commands c "
            "JOIN deliveries d ON d.id=c.delivery_id WHERE c.id=?", (command_id,),
        ).fetchone()
        execution = connection.execute(
            "SELECT state FROM executions WHERE command_id=?", (command_id,)
        ).fetchone()
        receipt = connection.execute(
            "SELECT processing_state, body_json FROM receipt_inbox "
            "WHERE json_extract(body_json, '$.command_id')=? ORDER BY received_at DESC LIMIT 1",
            (command_id,),
        ).fetchone()
        connection.close()
    except sqlite3.Error as error:
        raise TestCaseError("test_database_read_failed") from error

    body: dict[str, Any] = {}
    if receipt is not None:
        try:
            parsed = json.loads(receipt["body_json"])
            if isinstance(parsed, dict):
                body = parsed
        except (TypeError, json.JSONDecodeError):
            body = {}
    raw_state = command["outbox_command_state"] if command else None
    execution_state = execution["state"] if execution else None
    receipt_state = receipt["processing_state"] if receipt else None
    raw_post_id = (command["platform_post_id"] if command else None) or body.get("platform_post_id")
    if spec.platform == "facebook":
        post_id_pattern = rf"^{re.escape(spec.remote_id)}_[0-9]{{1,40}}$"
    else:
        post_id_pattern = r"^[0-9]{1,40}$"
    post_id = raw_post_id if isinstance(raw_post_id, str) and re.fullmatch(post_id_pattern, raw_post_id) else "NONE"
    return {
        "command_state": raw_state if raw_state in ALLOWED_COMMAND_STATES else "UNKNOWN",
        "outbox_command_state": raw_state if raw_state in ALLOWED_COMMAND_STATES else "UNKNOWN",
        "execution_state": execution_state if execution_state in ALLOWED_EXECUTION_STATES else "NONE",
        "receipt_state": receipt_state if receipt_state in ALLOWED_RECEIPT_STATES else "NONE",
        "outcome": body.get("outcome") if body.get("outcome") in {"POST_CREATED", "REJECTED_NO_SIDE_EFFECT", "OUTCOME_UNKNOWN"} else "NONE",
        "platform_post_id": post_id,
    }


def _call_sender(
    *,
    env: dict[str, str],
    envelope_path: Path,
    spec: CaseSpec,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    create: bool = False,
    mutation: str | None = None,
    send_start_marker: Path | None = None,
) -> dict[str, Any]:
    python = REPO_ROOT / ".venv/bin/python"
    args = [str(python), str(REPO_ROOT / "scripts/growth_engine/send_test_command.py"), "--envelope-file", str(envelope_path)]
    if create:
        args.append("--create-command")
    else:
        args.extend(("--send", "--confirm-test-remote-id", spec.remote_id))
        if send_start_marker is not None:
            args.extend(("--send-start-marker", str(send_start_marker)))
        if mutation == "broken_media_signature":
            args.append("--test-corrupt-media-url")
        elif mutation == "invalid_command_token":
            args.append("--test-corrupt-command-token")
    result = _run_process(args, runner=runner, env=env, timeout=60)
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as error:
        raise TestCaseError("test_sender_result_invalid") from error
    if not isinstance(payload, dict):
        raise TestCaseError("test_sender_result_invalid")
    if payload.get("result") == "REFUSED" or result.returncode not in {0, 1}:
        raise TestCaseError("test_sender_refused_before_or_during_send")
    if create and payload.get("result") != "DRY_RUN_VALIDATED":
        raise TestCaseError("test_command_creation_not_validated")
    if not create and payload.get("network_request_sent") is not True:
        raise TestCaseError("test_webhook_not_sent")
    return payload


def _wait_send_start_marker(
    path: Path,
    *,
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    timeout_seconds: float = 10,
) -> int:
    deadline = monotonic() + timeout_seconds
    while monotonic() < deadline:
        try:
            if path.is_file() and not path.is_symlink():
                if stat.S_IMODE(path.stat().st_mode) != 0o600:
                    raise TestCaseError("sequential_send_marker_permissions_invalid")
                started_at_ms = int(path.read_text(encoding="ascii").strip())
                if started_at_ms <= 0:
                    raise ValueError
                return started_at_ms
        except (OSError, UnicodeError, ValueError) as error:
            raise TestCaseError("sequential_send_marker_invalid") from error
        sleep(min(0.01, max(0, deadline - monotonic())))
    raise TestCaseError("sequential_first_webhook_did_not_start")


def _format_ict_timestamp(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(
        timespec="milliseconds"
    ) + " ICT"


def _run_apply_receipts(
    *,
    env_path: Path,
    run_id: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    attempt: int = 1,
) -> bool:
    result_unit = f"growth-engine-test-receipt-{run_id[:8]}-{attempt}"
    _systemd_transient(
        runner=runner,
        env_path=env_path,
        unit=result_unit,
        args=[str(REPO_ROOT / ".venv/bin/venho-engine"), "apply-test-receipts"],
        wait=True,
    )
    return True


def _await_receipts(
    *,
    database_path: Path,
    command_ids: list[str],
    spec: CaseSpec,
    env_path: Path,
    run_id: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    timeout_seconds: int = 120,
) -> tuple[dict[str, dict[str, Any]], bool]:
    deadline = monotonic() + timeout_seconds
    applied_receipts: set[str] = set()
    apply_attempt = 0
    while True:
        statuses = {
            command_id: _read_status(database_path, command_id, spec)
            for command_id in command_ids
        }
        pending = [
            command_id for command_id, status in statuses.items()
            if status["receipt_state"] == "RECEIVED" and command_id not in applied_receipts
        ]
        if pending:
            apply_attempt += 1
            _run_apply_receipts(
                env_path=env_path,
                run_id=run_id,
                runner=runner,
                attempt=apply_attempt,
            )
            applied_receipts.update(pending)
            continue
        if all(
            status["receipt_state"] in FINAL_RECEIPTS
            and status["execution_state"] in FINAL_EXECUTIONS
            for status in statuses.values()
        ):
            return statuses, False
        remaining = deadline - monotonic()
        if remaining <= 0:
            return statuses, True
        sleep(min(2, remaining))


def _await_receipt(
    *,
    database_path: Path,
    command_id: str,
    spec: CaseSpec,
    env_path: Path,
    run_id: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    timeout_seconds: int = 120,
) -> tuple[dict[str, Any], bool]:
    deadline = monotonic() + timeout_seconds
    apply_attempted = False
    while True:
        status = _read_status(database_path, command_id, spec)
        if status["receipt_state"] == "RECEIVED" and not apply_attempted:
            apply_attempted = True
            _run_apply_receipts(env_path=env_path, run_id=run_id, runner=runner)
        elif (
            status["receipt_state"] in FINAL_RECEIPTS
            or status["execution_state"] in FINAL_EXECUTIONS
        ):
            return status, False
        remaining = deadline - monotonic()
        if remaining <= 0:
            return status, True
        sleep(min(2, remaining))


def _await_negative_case(
    *,
    database_path: Path,
    command_id: str,
    spec: CaseSpec,
    env_path: Path,
    run_id: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    settle_seconds: int,
    timeout_seconds: int = 120,
) -> tuple[dict[str, Any], bool]:
    """Wait for Make to finish a negative case and apply any unexpected receipt."""
    deadline = monotonic() + timeout_seconds
    quiet_since: float | None = None
    while True:
        status = _read_status(database_path, command_id, spec)
        counts = _database_counts(database_path, command_id)
        if status["receipt_state"] == "RECEIVED":
            return _await_receipt(
                database_path=database_path,
                command_id=command_id,
                spec=spec,
                env_path=env_path,
                run_id=run_id,
                runner=runner,
                sleep=sleep,
                monotonic=monotonic,
                timeout_seconds=max(1, int(deadline - monotonic())),
            )
        if (
            status["receipt_state"] in FINAL_RECEIPTS
            or status["execution_state"] in FINAL_EXECUTIONS
        ):
            return status, False
        if counts["execution_count"] or counts["receipt_count"]:
            quiet_since = None
        elif quiet_since is None:
            quiet_since = monotonic()
        elif monotonic() - quiet_since >= settle_seconds:
            return status, False
        remaining = deadline - monotonic()
        if remaining <= 0:
            return status, True
        sleep(min(2, remaining))


def _write_safe_result(path: Path, result: dict[str, Any]) -> None:
    safe = {key: value for key, value in result.items() if key not in {"webhook_url", "media_url", "token"}}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(safe, stream, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _replace_safe_result(path: Path, result: dict[str, Any]) -> None:
    safe = {key: value for key, value in result.items() if key not in {"webhook_url", "media_url", "token"}}
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(safe, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _operator_history_check(case_name: str, input_fn: Callable[[str], str]) -> bool:
    prompts = {
        "ig_venho": "Make History confirms I1=200 image/jpeg, Meta fetched the signed URL, Instagram returned a media ID, and receipt completed? Type PASS: ",
        "duplicate": "Second Make History run shows authorize reason ALREADY_AUTHORIZED and no Facebook post module? Type PASS: ",
        "broken-media": "Make History shows F1 error → Ignore, no authorize/post, and the scenario remains Active? Type PASS: ",
        "bad-token": "Make History shows authorize rejection → Ignore, no Facebook post, and the scenario remains Active? Type PASS: ",
        "sequential": "Make History: run thứ hai bắt đầu sau khi run thứ nhất kết thúc? Gõ PASS: ",
    }
    return input_fn(prompts[case_name]).strip().upper() == "PASS"


def run_case(
    case_name: str,
    *,
    home: Path | None = None,
    repo_root: Path = REPO_ROOT,
    input_fn: Callable[[str], str] = input,
    secret_input: Callable[[str], str] = getpass.getpass,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    emit: Callable[[str], None] = print,
    settle_seconds: int = 15,
) -> int:
    if case_name not in CASES:
        raise TestCaseError("unknown_test_case")
    spec = CASES[case_name]
    home = (home or Path.home()).expanduser().resolve()
    repo_root = repo_root.resolve()
    if repo_root != (home / "venho/gc2-src").resolve():
        raise TestCaseError("run_from_home_venho_gc2_src_only")
    if not (repo_root / ".venv/bin/venho-engine").is_file():
        raise TestCaseError("growth_engine_virtualenv_unavailable")
    _manifest_target(repo_root, spec)

    base_env_path = home / "venho/secrets/growth-engine-test.env"
    base_values = _read_env(base_env_path)
    state_root = _validate_base_env(base_values, home)
    webhook_url = base_values.get(spec.webhook_env_key, "")
    if not _safe_webhook_url(webhook_url):
        webhook_url = secret_input(f"Webhook URL TEST {spec.channel_key} (hidden): ").strip()
    if not _safe_webhook_url(webhook_url):
        raise TestCaseError("test_webhook_url_invalid")

    run_id = uuid4().hex
    values, run_root, database_path, env_path = _prepare_case_env(
        base_values=base_values,
        state_root=state_root,
        secrets_root=home / "venho/secrets",
        spec=spec,
        webhook_url=webhook_url,
        run_id=run_id,
    )
    envelope_path = run_root / "command.envelope.json"
    case_unit = f"growth-engine-api-test-{spec.name}-{run_id[:8]}"
    migration_unit = f"growth-engine-test-migrate-{run_id[:10]}"
    base_stopped = False
    case_api_started = False
    manual_result = False
    outcome: dict[str, Any] = {
        "case": spec.name,
        "channel_key": spec.channel_key,
        "platform": spec.platform,
        "remote_id": spec.remote_id,
        "channel_id": values["GE_TEST_CHANNEL_ID"],
        "database_relative_path": str(database_path.relative_to(state_root)),
        "command_id": "NONE",
        "command_state": "NONE",
        "outbox_command_state": "NONE",
        "execution_state": "NONE",
        "receipt_state": "NONE",
        "outcome": "NONE",
        "platform_post_id": "NONE",
        "history_confirmation": "PENDING",
        "test_api_restore": "PENDING",
    }

    try:
        if not _unit_active(API_BASE_UNIT, runner):
            raise TestCaseError("base_test_api_unit_must_be_active_before_case")
        try:
            result = _run_process(["systemctl", "--user", "stop", API_BASE_UNIT], runner=runner, timeout=30)
        except TestCaseError:
            raise TestCaseError("base_test_api_stop_failed") from None
        if result.returncode != 0:
            raise TestCaseError("base_test_api_stop_failed")
        base_stopped = True

        _systemd_transient(
            runner=runner,
            env_path=env_path,
            unit=migration_unit,
            args=[str(repo_root / ".venv/bin/venho-engine"), "migrate"],
            wait=True,
        )
        _systemd_transient(
            runner=runner,
            env_path=env_path,
            unit=case_unit,
            args=[str(repo_root / ".venv/bin/venho-engine"), "api", "--host", "127.0.0.1", "--port", str(API_PORT)],
            wait=False,
        )
        case_api_started = True
        _wait_local_api(timeout_seconds=30, sleep=sleep, monotonic=monotonic)

        child_env = dict(values)
        child_env["GE_ENV"] = "test"
        created = _call_sender(
            env=child_env,
            envelope_path=envelope_path,
            spec=spec,
            runner=runner,
            create=True,
        )
        command_id = created.get("command_id")
        if not isinstance(command_id, str) or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", command_id
        ):
            raise TestCaseError("test_command_id_invalid")
        delivery_id = created.get("delivery_id")
        if not isinstance(delivery_id, str) or not re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", delivery_id
        ):
            raise TestCaseError("test_delivery_id_invalid")
        outcome["command_id"] = command_id
        outcome["command_ids"] = [command_id]
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        media_url = envelope.get("media_url")
        if not isinstance(media_url, str):
            raise TestCaseError("test_envelope_media_url_missing")
        try:
            check_local_media_url(media_url, values["GE_PUBLIC_BASE_URL"])
        except RunTestError as error:
            raise TestCaseError("media_preflight_failed_no_webhook_sent") from error

        sequential_commands: list[tuple[str, str, Path, int]] = [
            (command_id, delivery_id, envelope_path, int(envelope["execute_before_ms"]))
        ]
        if spec.name == "sequential":
            second_envelope_path = run_root / "command-2.envelope.json"
            second_created = _call_sender(
                env=child_env,
                envelope_path=second_envelope_path,
                spec=spec,
                runner=runner,
                create=True,
            )
            second_command_id = second_created.get("command_id")
            second_delivery_id = second_created.get("delivery_id")
            if not isinstance(second_command_id, str) or not re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", second_command_id
            ):
                raise TestCaseError("second_test_command_id_invalid")
            if not isinstance(second_delivery_id, str) or not re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", second_delivery_id
            ):
                raise TestCaseError("second_test_delivery_id_invalid")
            second_envelope = json.loads(second_envelope_path.read_text(encoding="utf-8"))
            second_media_url = second_envelope.get("media_url")
            if not isinstance(second_media_url, str):
                raise TestCaseError("second_test_envelope_media_url_missing")
            try:
                check_local_media_url(second_media_url, values["GE_PUBLIC_BASE_URL"])
            except RunTestError as error:
                raise TestCaseError("second_media_preflight_failed_no_webhook_sent") from error
            if (
                second_command_id == command_id
                or second_delivery_id == sequential_commands[0][1]
                or second_envelope.get("channel_id") != envelope.get("channel_id")
            ):
                raise TestCaseError("sequential_commands_must_be_distinct_deliveries_on_same_channel")
            sequential_commands.append(
                (second_command_id, str(second_delivery_id or ""), second_envelope_path,
                 int(second_envelope["execute_before_ms"]))
            )
            outcome["command_ids"] = [command_id, second_command_id]
            outcome["delivery_ids"] = [sequential_commands[0][1], str(second_delivery_id)]
        emit(f"case={spec.name}")
        emit(f"channel_key={spec.channel_key}")
        emit(f"remote_id={spec.remote_id}")
        emit(f"command_id={command_id}")
        emit(f"delivery_id={sequential_commands[0][1]}")
        emit("media_preflight=PASS")
        if spec.name == "sequential":
            second_command_id, second_delivery_id, _, second_deadline = sequential_commands[1]
            emit(f"command_id_2={second_command_id}")
            emit(f"delivery_id_2={second_delivery_id}")
            emit(f"execute_before_2_ms={second_deadline}")
            emit("media_preflight_2=PASS")

        if spec.mutation == "broken_media_signature":
            deliberately_broken = _mutate_test_envelope(
                envelope, corrupt_media=True, corrupt_command=False
            )["media_url"]
            try:
                check_local_media_url(deliberately_broken, values["GE_PUBLIC_BASE_URL"])
            except RunTestError:
                emit("intentional_bad_media_preflight=EXPECTED_FAIL")
            else:
                raise TestCaseError("intentional_bad_media_preflight_unexpectedly_passed")

        if input_fn(
            "Gõ ACTIVE chỉ sau khi blueprint 26-module đã import và scenario TEST đang Active; Enter khác để dừng: "
        ).strip() != "ACTIVE":
            emit("send=NOT_SENT; scenario activation was not confirmed")
            return 0
        case_prompt = {
            "ig_venho": "Gõ GUI để đăng bài thử lên Instagram TEST",
            "duplicate": "Gõ GUI để đăng một bài TEST rồi gửi lại đúng envelope một lần",
            "broken-media": "Gõ GUI để cố ý gửi media URL hỏng và kiểm tra F1 Ignore",
            "bad-token": "Gõ GUI để cố ý gửi command_token sai và kiểm tra authorize Ignore",
            "sequential": "Gõ GUI để gửi liên tiếp hai command fb_hanoi TEST độc lập",
        }[spec.name]
        if input_fn(case_prompt).strip() != "GUI":
            emit("send=NOT_SENT; explicit GUI confirmation was not received")
            return 0

        if spec.name == "sequential":
            first_marker = run_root / "webhook-1.started"
            second_marker = run_root / "webhook-2.started"
            with ThreadPoolExecutor(max_workers=1) as executor:
                first_future = executor.submit(
                    _call_sender,
                    env=child_env,
                    envelope_path=sequential_commands[0][2],
                    spec=spec,
                    runner=runner,
                    send_start_marker=first_marker,
                )
                first_started_at_ms = _wait_send_start_marker(
                    first_marker, sleep=sleep, monotonic=monotonic
                )
                second_sent = _call_sender(
                    env=child_env,
                    envelope_path=sequential_commands[1][2],
                    spec=spec,
                    runner=runner,
                    send_start_marker=second_marker,
                )
                first_sent = first_future.result(timeout=60)
            second_started_at_ms = _wait_send_start_marker(
                second_marker, sleep=sleep, monotonic=monotonic
            )
            gap_ms = second_started_at_ms - first_started_at_ms
            emit(f"webhook_1_sent_at={_format_ict_timestamp(first_started_at_ms)}")
            emit(f"webhook_2_sent_at={_format_ict_timestamp(second_started_at_ms)}")
            emit(f"webhook_gap_ms={gap_ms}")
            emit(f"webhook_1_disposition={first_sent.get('webhook_disposition', 'UNKNOWN')}")
            emit(f"webhook_2_disposition={second_sent.get('webhook_disposition', 'UNKNOWN')}")
            gap_ok = 0 <= gap_ms < 1000
            emit(f"webhooks_sent_less_than_1s_apart={'PASS' if gap_ok else 'FAIL'}")
            statuses, timed_out = _await_receipts(
                database_path=database_path,
                command_ids=[sequential_commands[0][0], sequential_commands[1][0]],
                spec=spec,
                env_path=env_path,
                run_id=run_id,
                runner=runner,
                sleep=sleep,
                monotonic=monotonic,
            )
            if timed_out:
                emit("receipt_wait=TIMEOUT_120S; no resend was attempted")
            db_checks: list[bool] = []
            post_ids: list[str] = []
            for index, (one_command_id, one_delivery_id, _, _) in enumerate(sequential_commands, start=1):
                status = statuses.get(one_command_id, {})
                counts = _database_counts(database_path, one_command_id)
                valid = (
                    status.get("execution_state") == "REPORTED"
                    and status.get("receipt_state") == "APPLIED"
                    and status.get("outcome") == "POST_CREATED"
                    and status.get("platform_post_id") not in {None, "NONE"}
                    and counts == {"execution_count": 1, "receipt_count": 1}
                )
                db_checks.append(valid)
                post_ids.append(str(status.get("platform_post_id", "NONE")))
                emit(f"command_{index}_execution_state={status.get('execution_state', 'NONE')}")
                emit(f"command_{index}_receipt_inbox.processing_state={status.get('receipt_state', 'NONE')}")
                emit(f"command_{index}_delivery_id={one_delivery_id}")
                emit(f"command_{index}_platform_post_id={status.get('platform_post_id', 'NONE')}")
            db_result = (
                all(db_checks)
                and len(set(post_ids)) == 2
                and first_sent.get("webhook_disposition") == "ACK"
                and second_sent.get("webhook_disposition") == "ACK"
            )
            emit(f"two_distinct_posts_and_applied_receipts={'PASS' if db_result else 'FAIL'}")
            manual_result = _operator_history_check(spec.name, input_fn)
            emit(f"make_history_confirmation={'PASS' if manual_result else 'PENDING'}")
            outcome.update({
                "history_confirmation": "PASS" if manual_result else "PENDING",
                "case_database_check": "PASS" if db_result else "FAIL",
                "webhook_gap_ms": gap_ms,
                "result": "PASS" if manual_result and db_result and gap_ok and not timed_out else "PENDING_REVIEW",
                "command_ids": [item[0] for item in sequential_commands],
                "delivery_ids": [item[1] for item in sequential_commands],
                "platform_post_ids": post_ids,
            })
            emit(f"case_result={outcome['result']}")
            _write_safe_result(run_root / "result.redacted.json", outcome)
            return 0

        sent = _call_sender(
            env=child_env,
            envelope_path=envelope_path,
            spec=spec,
            runner=runner,
            mutation=spec.mutation,
        )
        disposition = sent.get("webhook_disposition")
        emit(f"webhook_disposition={disposition if disposition in {'ACK', 'RETRYABLE', 'FATAL'} else 'UNKNOWN'}")
        if disposition != "ACK":
            emit("result=UNKNOWN; no resend was attempted")
            return 0

        if spec.name in {"ig_venho", "duplicate"}:
            status, timed_out = _await_receipt(
                database_path=database_path,
                command_id=command_id,
                spec=spec,
                env_path=env_path,
                run_id=run_id,
                runner=runner,
                sleep=sleep,
                monotonic=monotonic,
            )
            if timed_out:
                emit("receipt_wait=TIMEOUT_120S; no resend was attempted")
                outcome.update(status)
                return 0
            outcome.update(status)
            if (
                status["execution_state"] != "REPORTED"
                or status["receipt_state"] != "APPLIED"
                or status["outcome"] != "POST_CREATED"
                or status["platform_post_id"] == "NONE"
            ):
                emit("result=REVIEW_REQUIRED; receipt did not reach POST_CREATED/REPORTED/APPLIED")
                return 0
            emit(f"execution_state={status['execution_state']}")
            emit(f"outbox_commands.state={status['outbox_command_state']}")
            emit(f"receipt_inbox.processing_state={status['receipt_state']}")
            emit(f"outcome={status['outcome']}")
            emit(f"platform_post_id={status['platform_post_id']}")

            if spec.name == "duplicate":
                first_counts = _database_counts(database_path, command_id)
                second = _call_sender(
                    env=child_env,
                    envelope_path=envelope_path,
                    spec=spec,
                    runner=runner,
                )
                emit(f"replay_webhook_disposition={second.get('webhook_disposition', 'UNKNOWN')}")
                emit("expected_authorize_reason=ALREADY_AUTHORIZED (confirm in Make History)")
                sleep(settle_seconds)
                repeated = _read_status(database_path, command_id, spec)
                second_counts = _database_counts(database_path, command_id)
                duplicate_safe = (
                    first_counts == {"execution_count": 1, "receipt_count": 1}
                    and second_counts == first_counts
                    and repeated["platform_post_id"] == status["platform_post_id"]
                )
                emit(f"replay_no_second_execution_or_receipt={'PASS' if duplicate_safe else 'FAIL'}")
                outcome["duplicate_database_guard"] = "PASS" if duplicate_safe else "FAIL"
            else:
                duplicate_safe = True
        else:
            status, timed_out = _await_negative_case(
                database_path=database_path,
                command_id=command_id,
                spec=spec,
                env_path=env_path,
                run_id=run_id,
                runner=runner,
                sleep=sleep,
                monotonic=monotonic,
                settle_seconds=settle_seconds,
            )
            if timed_out:
                emit("case_wait=TIMEOUT_120S; inspect Make History before proceeding")
                outcome.update(status)
                return 0
            counts = _database_counts(database_path, command_id)
            no_authorize = (
                counts == {"execution_count": 0, "receipt_count": 0}
                and status["command_state"] == "PENDING"
            )
            emit(f"execution_state={status['execution_state']}")
            emit(f"outbox_commands.state={status['outbox_command_state']}")
            emit(f"receipt_inbox.processing_state={status['receipt_state']}")
            emit(f"no_authorize_or_receipt={'PASS' if no_authorize else 'FAIL'}")
            outcome.update(status)
            duplicate_safe = no_authorize

        manual_result = _operator_history_check(spec.name, input_fn)
        emit(f"make_history_confirmation={'PASS' if manual_result else 'PENDING'}")
        db_result = duplicate_safe
        outcome["history_confirmation"] = "PASS" if manual_result else "PENDING"
        outcome["case_database_check"] = "PASS" if db_result else "FAIL"
        overall = "PASS" if manual_result and db_result else "PENDING_REVIEW"
        outcome["result"] = overall
        emit(f"case_result={overall}")
        _write_safe_result(run_root / "result.redacted.json", outcome)
        return 0
    finally:
        result_file = run_root / "result.redacted.json"
        case_unit_stopped = True
        if case_api_started:
            stopped = _run_process(["systemctl", "--user", "stop", case_unit], runner=runner, timeout=30)
            if stopped.returncode != 0:
                _run_process(["systemctl", "--user", "stop", case_unit], runner=runner, timeout=30)
                case_unit_stopped = not _unit_active(case_unit, runner)
                if not case_unit_stopped:
                    emit("test_api_restore=FAILED; case API unit is still active")
        if base_stopped:
            if case_unit_stopped:
                restore_method = _restore_base_api(
                    runner=runner,
                    env_path=base_env_path,
                    repo_root=repo_root,
                    sleep=sleep,
                    monotonic=monotonic,
                )
                outcome["test_api_restore"] = "PASS" if restore_method else "FAILED"
                if restore_method:
                    outcome["test_api_restore_method"] = restore_method
                emit(
                    "test_api_restore=PASS "
                    f"method={restore_method}"
                    if restore_method
                    else "test_api_restore=FAILED; base API did not become ready after restart/recreate"
                )
            else:
                outcome["test_api_restore"] = "FAILED"
        elif outcome["test_api_restore"] == "PENDING":
            outcome["test_api_restore"] = "NOT_REQUIRED"
        if outcome.get("result") == "PASS" and outcome["test_api_restore"] != "PASS":
            outcome["result"] = "PENDING_REVIEW"
            emit("case_result_after_restore=PENDING_REVIEW")
        if outcome["command_id"] != "NONE":
            outcome.setdefault("result", "INCOMPLETE")
            try:
                if result_file.exists():
                    _replace_safe_result(result_file, outcome)
                else:
                    _write_safe_result(result_file, outcome)
            except OSError:
                emit("result_record=FAILED")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=tuple(CASES))
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        print("run-test-case: interactive terminal required; no TEST request was sent", file=sys.stderr)
        return 2
    try:
        return run_case(args.case)
    except TestCaseError as error:
        print(f"run-test-case: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("run-test-case: interrupted; TEST API restore attempted", file=sys.stderr)
        return 130
    except Exception:
        print("run-test-case: failed safely; no credential or request value was displayed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

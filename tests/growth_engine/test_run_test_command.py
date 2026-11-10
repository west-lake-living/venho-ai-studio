from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import stat
import subprocess
from pathlib import Path
from uuid import UUID

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/growth_engine/run_test_command.py"
SPEC = importlib.util.spec_from_file_location("run_test_command", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)

FAKE_WEBHOOK = "https://hook.eu1.make.com/fake-private-path"
FAKE_CAPABILITY_KEY = "test-key:fake-capability-key"
FAKE_SERVICE_TOKENS = "make-fb-hanoi:" + "a" * 64
COMMAND_ID = "11111111-1111-4111-8111-111111111111"
POST_ID = "1363761820162798_998877665544"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    state = home / "venho/state/growth-engine-test"
    secrets = home / "venho/secrets"
    state.mkdir(parents=True)
    secrets.mkdir(parents=True)
    (state / "media").mkdir()
    database = state / "growth_engine.db"
    sqlite3.connect(database).close()
    env = {
        "GE_ENV": "test",
        "GE_DB_PATH": str(database),
        "GE_MEDIA_ROOT": str(state / "media"),
        "GE_PUBLIC_BASE_URL": "https://ge-test.venhohotel.com",
        "GE_CAPABILITY_KEYS": FAKE_CAPABILITY_KEY,
        "GE_SERVICE_TOKENS": FAKE_SERVICE_TOKENS,
    }
    path = secrets / "growth-engine-test.env"
    path.write_text("".join(f"{key}={value}\n" for key, value in env.items()), encoding="utf-8")
    path.chmod(0o600)
    return home


def _repo(home: Path, *, graph_api_version: str = "v27.0") -> Path:
    root = home / "venho/gc2-src"
    manifest = root / "config/projects/venho_hotel/growth_engine/channels.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "channels:\n"
        "  - channel_id: page_test\n"
        "    environment: test\n"
        "    platform: facebook\n"
        '    remote_page_id: "1363761820162798"\n'
        "    make_route_ref: GE_MAKE_WEBHOOK_URL_PAGE_TEST\n"
        f"    graph_api_version: {graph_api_version}\n"
        "    service_principals:\n"
        "      fb_hanoi: make-fb-hanoi\n",
        encoding="utf-8",
    )
    script = root / "scripts/growth_engine/send_test_command.py"
    script.parent.mkdir(parents=True)
    script.write_text("# fake command runner target\n", encoding="utf-8")
    return root


def _create_db_schema(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.executescript(
            "CREATE TABLE outbox_commands (id TEXT PRIMARY KEY, state TEXT, delivery_id TEXT);"
            "CREATE TABLE executions (id TEXT PRIMARY KEY, command_id TEXT, delivery_id TEXT, "
            "state TEXT, external_outcome TEXT, grant_id TEXT, updated_at INTEGER);"
            "CREATE TABLE deliveries (id TEXT PRIMARY KEY, platform_post_id TEXT);"
            "CREATE TABLE receipt_inbox (processing_state TEXT, body_json TEXT, received_at INTEGER);"
        )


def test_manifest_requires_verified_fb_hanoi_graph_version() -> None:
    manifest = {
        "channels": [
            {
                "channel_id": "page_test",
                "environment": "test",
                "platform": "facebook",
                "remote_page_id": "1363761820162798",
                "make_route_ref": "GE_MAKE_WEBHOOK_URL_PAGE_TEST",
                "graph_api_version": "REQUIRED_FROM_P0",
                "service_principals": {"fb_hanoi": "make-fb-hanoi"},
            }
        ]
    }

    with pytest.raises(RUNNER.RunTestError, match="test_fb_hanoi_graph_api_version_not_configured"):
        RUNNER.validate_manifest(manifest)


def test_repository_manifest_fills_test_targets_and_leaves_production_graph_versions_null() -> None:
    manifest = RUNNER.load_manifest(REPO_ROOT)
    channels = {item["channel_id"]: item for item in manifest["channels"]}

    assert channels["page_test"]["make_scenario_id"] == "6924867"
    assert channels["page_test"]["remote_page_id"] == "1363761820162798"
    assert channels["page_test"]["graph_api_version"] == "v27.0"
    assert channels["page_test"]["owner"] == "Harry"
    assert channels["page_test"]["verified_on"] == "2026-11-10"
    assert channels["ig_test"]["make_scenario_id"] == "6924867"
    assert channels["ig_test"]["remote_account_id"] == "17841472240799413"
    assert channels["ig_test"]["graph_api_version"] == "v27.0"
    assert channels["ig_test"]["owner"] == "Harry"
    assert channels["ig_test"]["verified_on"] == "2026-11-10"
    assert channels["page_test"]["make_connection_ref"] == "Ven Ho Hotel Hanoi (Ha Pham)"
    assert channels["ig_test"]["make_connection_ref"] == "Ven Ho Hotel Hanoi (Ha Pham)"
    assert all(
        channel["graph_api_version"] is None
        for channel in manifest["channels"]
        if channel["environment"] == "production"
    )


def test_env_settings_are_idempotent_and_leave_backup_untouched(tmp_path: Path) -> None:
    home = _home(tmp_path)
    env_path = home / "venho/secrets/growth-engine-test.env"
    backup = home / "venho/secrets/growth-engine-test.env.bak-20261110102217"
    backup.write_text("GE_ENV=test\nKEEP=fake-backup\n", encoding="utf-8")
    backup.chmod(0o600)
    backup_before = backup.read_bytes()

    values, changed = RUNNER.add_first_run_settings(env_path, "https://hook.eu1.make.com/fake-path", home)
    first_content = env_path.read_bytes()
    assert changed is True
    assert values["GE_TEST_CHANNEL_KEY"] == "fb_hanoi"
    assert str(UUID(values["GE_TEST_CHANNEL_ID"])) == values["GE_TEST_CHANNEL_ID"]
    assert values["GE_TEST_REMOTE_PAGE_ID"] == "1363761820162798"
    assert values["GE_MAKE_WEBHOOK_URL_PAGE_TEST"] == "https://hook.eu1.make.com/fake-path"
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600

    values_again, changed_again = RUNNER.add_first_run_settings(env_path, "https://hook.eu1.make.com/fake-path", home)
    assert changed_again is False
    assert values_again["GE_TEST_CHANNEL_ID"] == values["GE_TEST_CHANNEL_ID"]
    assert env_path.read_bytes() == first_content
    assert backup.read_bytes() == backup_before


def test_env_refuses_wrong_page_and_webhook_values_without_echoing(tmp_path: Path) -> None:
    home = _home(tmp_path)
    env_path = home / "venho/secrets/growth-engine-test.env"
    content = env_path.read_text(encoding="utf-8") + "GE_TEST_REMOTE_PAGE_ID=wrong-fake-id\n"
    env_path.write_text(content, encoding="utf-8")
    env_path.chmod(0o600)

    with pytest.raises(RUNNER.RunTestError, match="test_env_target_conflicts_with_fb_hanoi"):
        RUNNER.add_first_run_settings(env_path, "https://hook.eu1.make.com/fake-path", home)


def test_child_environment_drops_inherited_production_values(tmp_path: Path) -> None:
    home = _home(tmp_path)
    env_path = home / "venho/secrets/growth-engine-test.env"
    values, _ = RUNNER.add_first_run_settings(env_path, "https://hook.eu1.make.com/fake-path", home)
    child = RUNNER._child_environment(
        values,
        {"HOME": str(home), "PATH": "/fake/bin", "GE_ENV": "production", "GE_DB_PATH": "/prod/db"},
    )

    assert child["GE_ENV"] == "test"
    assert child["GE_DB_PATH"] == values["GE_DB_PATH"]
    assert child["GE_DB_PATH"] != "/prod/db"


def test_run_requires_active_and_gui_before_fake_send_and_reports_db_receipt(tmp_path: Path) -> None:
    home = _home(tmp_path)
    repo = _repo(home)
    database = home / "venho/state/growth-engine-test/growth_engine.db"
    _create_db_schema(database)
    prompts: list[str] = []
    outputs: list[str] = []
    calls: list[list[str]] = []

    def fake_runner(args, *, cwd, env, **kwargs):
        calls.append(args)
        assert cwd == str(repo)
        assert env["GE_ENV"] == "test"
        assert env["GE_DB_PATH"] == str(database)
        envelope_path = Path(args[args.index("--envelope-file") + 1])
        if "--create-command" in args:
            envelope = {
                "command_id": COMMAND_ID,
                "channel_key": "fb_hanoi",
                "channel_id": env["GE_TEST_CHANNEL_ID"],
                "remote_page_id": "1363761820162798",
                "execute_before_ms": 1_900_000_000_000,
                "command_token": "fake-private-token-value",
                "media_url": "https://ge-test.venhohotel.com/fake-private-signed-url",
            }
            envelope_path.write_text(json.dumps(envelope), encoding="utf-8")
            envelope_path.chmod(0o600)
            with sqlite3.connect(database) as connection:
                connection.execute("INSERT INTO deliveries VALUES ('delivery-test', NULL)")
                connection.execute("INSERT INTO outbox_commands VALUES (?, 'ACKED', 'delivery-test')", (COMMAND_ID,))
            return subprocess.CompletedProcess(args, 0, json.dumps({"network_request_sent": False}), "")

        assert "--send" in args
        assert "--confirm-test-remote-id" in args
        assert prompts[-1] == "Gõ GUI để gửi lệnh đăng thử lên Page TEST"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO executions VALUES ('execution-test', ?, 'delivery-test', 'REPORTED', "
                "'POST_CREATED', 'grant-test', 1)",
                (COMMAND_ID,),
            )
            body = {
                "command_id": COMMAND_ID,
                "outcome": "POST_CREATED",
                "platform_post_id": POST_ID,
                "failed_step": None,
            }
            connection.execute(
                "INSERT INTO receipt_inbox VALUES ('APPLIED', ?, 1)", (json.dumps(body),)
            )
            connection.execute("UPDATE deliveries SET platform_post_id=? WHERE id='delivery-test'", (POST_ID,))
        return subprocess.CompletedProcess(
            args,
            0,
            json.dumps({"network_request_sent": True, "webhook_disposition": "ACK", "http_status": 200}),
            "",
        )

    answers = iter(["ACTIVE", "GUI"])

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    exit_code = RUNNER.run_first_command(
        home=home,
        repo_root=repo,
        input_fn=fake_input,
        secret_input=lambda _prompt: FAKE_WEBHOOK,
        runner=fake_runner,
        sleep=lambda _seconds: None,
        monotonic=lambda: 10.0,
        emit=outputs.append,
        database_wait_seconds=0,
    )

    assert exit_code == 0
    assert len(calls) == 2
    assert "--create-command" in calls[0] and "--send" not in calls[0]
    assert "--send" in calls[1]
    assert "remote_page_id=1363761820162798" in outputs
    assert f"command_id={COMMAND_ID}" in outputs
    assert "outcome=POST_CREATED" in outputs
    assert f"platform_post_id={POST_ID}" in outputs
    assert "failed_step=NONE" in outputs
    for secret in (FAKE_WEBHOOK, FAKE_CAPABILITY_KEY, FAKE_SERVICE_TOKENS, "fake-private-token-value", "fake-private-signed-url"):
        assert secret not in "\n".join(outputs)


@pytest.mark.parametrize("answers", [["", "GUI"], ["ACTIVE", "gui"]])
def test_nonmatching_confirmation_never_invokes_send(tmp_path: Path, answers: list[str]) -> None:
    home = _home(tmp_path)
    repo = _repo(home)
    calls: list[list[str]] = []

    def fake_runner(args, *, cwd, env, **kwargs):
        calls.append(args)
        path = Path(args[args.index("--envelope-file") + 1])
        path.write_text(
            json.dumps(
                {
                    "command_id": COMMAND_ID,
                    "channel_key": "fb_hanoi",
                    "channel_id": env["GE_TEST_CHANNEL_ID"],
                    "remote_page_id": "1363761820162798",
                    "execute_before_ms": 1_900_000_000_000,
                }
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)
        return subprocess.CompletedProcess(args, 0, json.dumps({"network_request_sent": False}), "")

    answers_iterator = iter(answers)
    prompts: list[str] = []
    result = RUNNER.run_first_command(
        home=home,
        repo_root=repo,
        input_fn=lambda prompt: (prompts.append(prompt), next(answers_iterator))[1],
        secret_input=lambda _prompt: "https://hook.eu1.make.com/fake-path",
        runner=fake_runner,
        emit=lambda _line: None,
        database_wait_seconds=0,
    )

    assert result == 0
    assert len(calls) == 1
    assert "--send" not in calls[0]


def test_runner_preflights_manifest_before_reading_webhook_or_writing_env(tmp_path: Path) -> None:
    home = _home(tmp_path)
    repo = _repo(home, graph_api_version="REQUIRED_FROM_P0")
    env_path = home / "venho/secrets/growth-engine-test.env"
    before = env_path.read_bytes()

    with pytest.raises(RUNNER.RunTestError, match="test_fb_hanoi_graph_api_version_not_configured"):
        RUNNER.run_first_command(
            home=home,
            repo_root=repo,
            secret_input=lambda _prompt: pytest.fail("must fail before reading webhook"),
            input_fn=lambda _prompt: pytest.fail("must fail before confirmation"),
            runner=lambda *args, **kwargs: pytest.fail("must fail before subprocess"),
        )
    assert env_path.read_bytes() == before


def test_database_summary_redacts_noncanonical_ids_and_unknown_state_values(tmp_path: Path) -> None:
    database = tmp_path / "growth_engine.db"
    _create_db_schema(database)
    secret = "EAA-fake-private-token_123"
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO deliveries VALUES ('delivery-test', ?)", (secret,))
        connection.execute("INSERT INTO outbox_commands VALUES (?, ?, 'delivery-test')", (COMMAND_ID, secret))
        connection.execute(
            "INSERT INTO executions VALUES ('execution-test', ?, 'delivery-test', ?, ?, 'grant-test', 1)",
            (COMMAND_ID, secret, secret),
        )
        body = {
            "command_id": COMMAND_ID,
            "outcome": secret,
            "platform_post_id": secret,
            "failed_step": secret,
        }
        connection.execute("INSERT INTO receipt_inbox VALUES (?, ?, 1)", (secret, json.dumps(body)))

    summary = RUNNER.read_db_status(database, COMMAND_ID)
    assert summary == {
        "command_state": "UNKNOWN",
        "execution_state": "UNKNOWN",
        "receipt_state": "UNKNOWN",
        "outcome": "UNKNOWN",
        "platform_post_id": "REDACTED",
        "failed_step": "UNKNOWN",
    }
    assert secret not in " ".join(summary.values())

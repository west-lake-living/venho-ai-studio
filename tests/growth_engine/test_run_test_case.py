from __future__ import annotations

import stat
import sqlite3
import yaml

from scripts.growth_engine import run_test_case as runner


def test_case_matrix_uses_verified_ig_destination_and_fb_only_for_fault_cases() -> None:
    instagram = runner.CASES["ig_venho"]
    assert instagram.channel_key == "ig_venho"
    assert instagram.platform == "instagram"
    assert instagram.manifest_channel_id == "ig_test"
    assert instagram.remote_id == "17841472240799413"
    assert instagram.remote_env_key == "GE_TEST_REMOTE_IG_ID"

    assert runner.CASES["duplicate"].channel_key == "fb_hanoi"
    assert runner.CASES["broken-media"].mutation == "broken_media_signature"
    assert runner.CASES["bad-token"].mutation == "invalid_command_token"


def test_case_environment_gets_fresh_db_channel_and_private_env_file(tmp_path) -> None:
    home = tmp_path
    state = home / "venho/state/growth-engine-test"
    secrets = home / "venho/secrets"
    state.mkdir(parents=True)
    spec = runner.CASES["ig_venho"]
    values, run_root, database, env_path = runner._prepare_case_env(
        base_values={
            "GE_ENV": "test",
            "GE_DB_PATH": str(state / "growth_engine.db"),
            "GE_MEDIA_ROOT": str(state / "media"),
            "GE_CAPABILITY_KEYS": "test-key:synthetic",
            "GE_SERVICE_TOKENS": "make-ig:" + "a" * 64,
            "GE_PUBLIC_BASE_URL": runner.EXPECTED_TEST_HOST,
        },
        state_root=state,
        secrets_root=secrets,
        spec=spec,
        webhook_url="https://hooks.example.test/ig-test",
        run_id="0123456789abcdef",
    )

    assert values["GE_TEST_CHANNEL_KEY"] == "ig_venho"
    assert values["GE_TEST_REMOTE_IG_ID"] == "17841472240799413"
    assert values["GE_MAKE_WEBHOOK_URL_IG_TEST"] == "https://hooks.example.test/ig-test"
    assert database == run_root / "growth_engine.db"
    assert database != state / "growth_engine.db"
    assert values["GE_TEST_CHANNEL_ID"]
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    loaded = runner._read_env(env_path)
    assert loaded["GE_DB_PATH"] == str(database)
    assert loaded["GE_TEST_CHANNEL_ID"] == values["GE_TEST_CHANNEL_ID"]


def test_ig_manifest_accepts_verified_singular_service_principal(tmp_path) -> None:
    manifest = tmp_path / "config/projects/venho_hotel/growth_engine/channels.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "channels": [
                    {
                        "channel_id": "ig_test",
                        "environment": "test",
                        "platform": "instagram",
                        "remote_account_id": "17841472240799413",
                        "make_route_ref": "GE_MAKE_WEBHOOK_URL_IG_TEST",
                        "service_principal": "make-ig",
                        "graph_api_version": "v27.0",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    runner._manifest_target(tmp_path, runner.CASES["ig_venho"])


def test_status_reports_outbox_authorized_separately_from_applied_receipt(tmp_path) -> None:
    database = tmp_path / "status.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE outbox_commands (id TEXT PRIMARY KEY, state TEXT, delivery_id TEXT);
        CREATE TABLE deliveries (id TEXT PRIMARY KEY, platform_post_id TEXT);
        CREATE TABLE executions (id TEXT PRIMARY KEY, command_id TEXT, state TEXT);
        CREATE TABLE receipt_inbox (received_at INTEGER, processing_state TEXT, body_json TEXT);
        """
    )
    connection.execute("INSERT INTO outbox_commands VALUES (?, ?, ?)", ("cmd", "AUTHORIZED", "delivery"))
    connection.execute(
        "INSERT INTO deliveries VALUES (?, ?)",
        ("delivery", "1363761820162798_122106835935535879"),
    )
    connection.execute("INSERT INTO executions VALUES (?, ?, ?)", ("execution", "cmd", "REPORTED"))
    connection.execute(
        "INSERT INTO receipt_inbox VALUES (?, ?, ?)",
        (1, "APPLIED", '{"command_id":"cmd","outcome":"POST_CREATED",'
         '"platform_post_id":"1363761820162798_122106835935535879"}'),
    )
    connection.commit()
    connection.close()

    status = runner._read_status(database, "cmd", runner.CASES["duplicate"])

    assert status["outbox_command_state"] == "AUTHORIZED"
    assert status["execution_state"] == "REPORTED"
    assert status["receipt_state"] == "APPLIED"
    assert status["outcome"] == "POST_CREATED"
    assert status["platform_post_id"] == "1363761820162798_122106835935535879"

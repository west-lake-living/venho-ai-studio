from __future__ import annotations

from pathlib import Path

from growth_engine.bootstrap import build_container
from growth_engine.settings import Settings


def test_production_image_source_doctor_requires_each_legacy_group_and_drive_token(
    tmp_path: Path, monkeypatch
) -> None:
    config = tmp_path / "config/projects/venho_hotel"
    (config / "growth").mkdir(parents=True)
    (config / "growth_engine").mkdir(parents=True)
    (config / "growth/scenario_registry.yaml").write_text(
        "scenarios:\n"
        "  rooftop:\n    reference_asset_ids: [venho_rooftop_railing_approved]\n"
        "  room:\n    reference_asset_ids: [venho_room_lake_view_approved]\n",
        encoding="utf-8",
    )
    image_config = config / "growth_engine/image_library.yaml"
    image_config.write_text(
        "version: 1\n"
        "allowlist:\n"
        "  venho_rooftop_railing_approved: [synthetic-drive-id-001]\n"
        "  venho_room_lake_view_approved: []\n",
        encoding="utf-8",
    )
    settings = Settings(
        env="test",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="http://localhost:8021",
    )
    doctor = build_container(settings).doctor_service
    doctor._repo_root = tmp_path

    monkeypatch.delenv("GOOGLE_DRIVE_TOKEN_JSON", raising=False)
    missing = doctor._p4_image_source_check()
    assert missing.status == "FAIL"
    assert "venho_room_lake_view_approved" in missing.detail
    assert "GOOGLE_DRIVE_TOKEN_JSON" in missing.detail

    image_config.write_text(
        "version: 1\n"
        "allowlist:\n"
        "  venho_rooftop_railing_approved: [synthetic-drive-id-001]\n"
        "  venho_room_lake_view_approved: [synthetic-drive-id-002]\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GOOGLE_DRIVE_TOKEN_JSON", "synthetic-authorized-user-json")
    ready = doctor._p4_image_source_check()
    assert ready.status == "PASS"
    assert "allowlisted_reference_groups=2" in ready.detail
    assert "synthetic-authorized-user-json" not in ready.detail

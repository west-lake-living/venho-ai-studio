from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from growth_engine.bootstrap import _legacy_reference_subjects, build_container
from growth_engine.settings import Settings


def _write_jpeg(path: Path, color: tuple[int, int, int]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (30, 20), color).save(path, format="JPEG")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_production_image_source_doctor_uses_catalog_mappings_and_ignores_uncatalogued_groups(
    tmp_path: Path,
) -> None:
    config = tmp_path / "config/projects/venho_hotel"
    (config / "growth").mkdir(parents=True)
    (config / "growth_engine").mkdir(parents=True)
    (config / "growth/scenario_registry.yaml").write_text(
        "scenarios:\n"
        "  rooftop:\n    dna_subject: outside\n    reference_asset_ids: [venho_rooftop_railing_approved]\n"
        "  room:\n    dna_subject: lake_view_room\n    reference_asset_ids: [venho_room_lake_view_approved]\n"
        "  person:\n    dna_subject: linh_an\n    reference_asset_ids: [linh_an_public_approved]\n",
        encoding="utf-8",
    )
    (config / "growth/reference_assets.yaml").write_text(
        "assets:\n"
        "  venho_rooftop_railing_approved: assets/raw/outside\n"
        "  venho_room_lake_view_approved: assets/raw/room\n",
        encoding="utf-8",
    )
    root = tmp_path / "legacy/assets/raw"
    rooftop_sha = _write_jpeg(root / "outside/roof.jpg", (20, 60, 100))
    room_sha = _write_jpeg(root / "room/view.jpg", (40, 80, 120))
    image_config = config / "growth_engine/image_library.yaml"
    image_config.write_text(
        "version: 1\nsource: local_legacy_library\nallowlist:\n"
        "  venho_rooftop_railing_approved: []\n"
        "  venho_room_lake_view_approved: []\n",
        encoding="utf-8",
    )
    settings = Settings(
        env="production",
        db_path=str(tmp_path / "growth.db"),
        media_root=str(tmp_path / "media"),
        public_base_url="https://growth.example.invalid",
        image_library_config=str(image_config),
        legacy_assets_root=str(root),
    )
    doctor = build_container(settings).doctor_service
    doctor._repo_root = tmp_path
    assert _legacy_reference_subjects(tmp_path) == {
        "venho_rooftop_railing_approved": "outside",
        "venho_room_lake_view_approved": "lake_view_room",
    }

    missing = doctor._p4_image_source_check()
    assert missing.status == "FAIL"
    assert missing.detail == (
        "missing_allowlist_groups=venho_rooftop_railing_approved,venho_room_lake_view_approved"
    )

    image_config.write_text(
        "version: 1\nsource: local_legacy_library\nallowlist:\n"
        "  venho_rooftop_railing_approved:\n"
        "    - path: outside/roof.jpg\n"
        f"      sha256: {rooftop_sha}\n"
        "  venho_room_lake_view_approved:\n"
        "    - path: room/view.jpg\n"
        f"      sha256: {room_sha}\n",
        encoding="utf-8",
    )
    ready = doctor._p4_image_source_check()
    assert ready.status == "PASS"
    assert "legacy_reference_groups=2" in ready.detail
    assert "ignored_uncatalogued_scenario_groups=1" in ready.detail

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from growth_orchestrator.application.image_choice import notify_image_options, select_image, upload_image
from growth_orchestrator.application.image_options import topic_scenario
from publishing_gateway.publication_registry import PublicationRegistry

_OPTIONS = [
    {"id": "A", "kind": "ai", "url": "https://img/a", "asset_version_id": "run-a"},
    {"id": "B", "kind": "ai", "url": "https://img/b", "asset_version_id": "run-b"},
    {"id": "C", "kind": "photo", "url": "https://img/c"},
]
_POOL = [
    "venho_west_lake_landscape", "venho_nguyen_dinh_thi_street", "venho_rooftop_sunrise",
    "venho_rooftop_sunset", "venho_lobby_cozy", "venho_lake_view_room_sunrise",
]


def _registry(tmp_path: Path, status: str = "PENDING_APPROVAL") -> PublicationRegistry:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    for pid, platform in (("fb", "facebook"), ("ig", "instagram")):
        registry.reserve({"publication_id": pid, "content_package_id": f"{pid}-pkg", "idempotency_key": f"{pid}-k", "platform": platform})
        registry.update(
            pid, status=status, slot_id="slot-2026-10-26-monday", topic="Hoa sữa đường Thanh Niên",
            content={"text": "caption", "image_public_url": "https://img/a", "image_is_fallback": False,
                     "image_options": _OPTIONS, "image_option_selected": "A"},
            package_snapshot={"id": f"{pid}-pkg", "asset_version_ids": ["run-a"]},
        )
    return registry


@pytest.mark.parametrize(
    ("topic", "expected"),
    [
        ("sương sớm trên mặt hồ, trước khi Hà Nội thức giấc", "venho_west_lake_landscape"),
        ("Hoàng hôn trên rooftop nhìn ra Hồ Tây", "venho_rooftop_sunset"),
        ("góc đọc sách ở lobby vào ngày mưa", "venho_lobby_cozy"),
        ("tầm nhìn từ cửa sổ phòng lúc 6 giờ sáng", "venho_lake_view_room_sunrise"),
        ("Mùi hoa sữa dọc đường Thanh Niên", "venho_nguyen_dinh_thi_street"),
        ("dịch vụ nghỉ dưỡng cuối tuần", None),
    ],
)
def test_topic_words_pick_the_scene(topic: str, expected: str | None) -> None:
    assert topic_scenario(topic, _POOL) == expected


def test_topic_match_is_limited_to_the_lane_pool() -> None:
    assert topic_scenario("góc đọc sách ở lobby", ["venho_west_lake_landscape"]) is None


def test_selecting_an_option_updates_both_platforms_and_the_snapshot(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    select_image("fb", "B", selected_by="harry", registry=registry)

    for pid in ("fb", "ig"):
        row = registry.find(pid)
        assert row["content"]["image_public_url"] == "https://img/b"
        assert row["content"]["image_option_selected"] == "B"
        assert row["package_snapshot"]["asset_version_ids"] == ["run-b"]

    select_image("ig", "C", selected_by="harry", registry=registry)
    assert registry.find("fb")["package_snapshot"]["asset_version_ids"] == []  # a real photo has no AI run
    assert registry.find("fb")["content"]["image_is_fallback"] is False  # dispatch keeps it as chosen


def test_image_cannot_change_after_approval(tmp_path: Path) -> None:
    registry = _registry(tmp_path, status="APPROVED_SCHEDULED")
    with pytest.raises(ValueError, match="before Duyệt"):
        select_image("fb", "B", selected_by="harry", registry=registry)


def test_unknown_option_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no image option"):
        select_image("fb", "Z", selected_by="harry", registry=_registry(tmp_path))


def test_upload_adds_and_selects_harrys_photo(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    photo = tmp_path / "harry.jpg"
    Image.new("RGB", (1080, 1350), (200, 180, 150)).save(photo)

    class FakeUploader:
        def upload_and_publish(self, path, *, folder_path, mimetype):
            assert Path(path).suffix == ".png"
            return "https://drive/harry"

    upload_image("fb", photo, uploaded_by="harry", registry=registry, uploader=FakeUploader())

    content = registry.find("ig")["content"]
    assert content["image_option_selected"] == "U1"
    assert content["image_public_url"] == "https://drive/harry"
    assert [o["id"] for o in content["image_options"]] == ["A", "B", "C", "U1"]


def test_telegram_album_per_new_pending_slot(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    calls: list[tuple[str, dict]] = []

    def post(url, *, json, timeout):
        calls.append((url.rsplit("/", 1)[-1], json))
        return {"ok": True}

    sent = notify_image_options(since="2000-01-01T00:00:00", registry=registry, post=post, token="t", chat_id="c")

    assert sent == 1  # fb + ig of one slot = one album
    method, payload = calls[0]
    assert method == "sendMediaGroup" and [m["media"] for m in payload["media"]] == ["https://img/a", "https://img/b", "https://img/c"]
    assert "Hoa sữa" in payload["media"][0]["caption"]
    assert "A = AI" in calls[1][1]["text"]

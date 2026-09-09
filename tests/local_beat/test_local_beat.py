from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from research_engine.local_beat.differ import build_beat_items, diff_week
from research_engine.local_beat.angle_extractor import extract_guest_angle
from research_engine.local_beat.entities import BeatEntity, SearchResult, WeekSnapshot
from research_engine.local_beat.scanner import JsonSearchProvider, scan_week
from research_engine.local_beat.timeline_store import TimelineStore


def _entity() -> BeatEntity:
    return BeatEntity(
        id="ho-tay-project", name="Dự án cải tạo Hồ Tây", queries=("cải tạo Hồ Tây",),
        category="infrastructure", guest_relevance="high", tracked_since="2026-01",
    )


def _result(title: str = "Hồ Tây bắt đầu thi công") -> SearchResult:
    return SearchResult(
        url="https://example.test/west-lake", title=title,
        snippet="Dự án cải tạo Hồ Tây đang thi công, người dân cần lưu ý.",
        content="Dự án cải tạo Hồ Tây đang thi công.", published_at="2026-09-08", source="example.test",
    )


def test_diff_detects_state_change_and_is_idempotent() -> None:
    entity = _entity()
    current = build_beat_items(entity, [_result()], detected_at="2026-09-09T00:00:00+00:00")
    assert len(current) == 1
    assert diff_week(current, None) == current
    assert diff_week(current, WeekSnapshot(week="2026-W37", items=tuple(current))) == []


def test_scanner_filters_entity_mentions_and_writes_snapshot_and_vault(tmp_path: Path) -> None:
    input_file = tmp_path / "results.json"
    input_file.write_text(
        '[{"url":"https://example.test/1","title":"Dự án cải tạo Hồ Tây đã được duyệt",'
        '"snippet":"Chủ trương đầu tư dự án cải tạo Hồ Tây.","content":"",'
        '"published_at":"2026-09-08"},'
        '{"url":"https://example.test/2","title":"Tin khác", "snippet":"Không liên quan", "content":""}]',
        encoding="utf-8",
    )
    watchlist = tmp_path / "watchlist.yaml"
    watchlist.write_text(
        "version: 1\nentities:\n" + "\n".join(
            f"  - id: entity-{index}\n    name: Entity {index}\n    queries: [\"Entity {index}\"]\n    category: culture\n    guest_relevance: medium\n    tracked_since: '2026-01'"
            for index in range(15)
        ),
        encoding="utf-8",
    )
    # Make the first configured entity match the fixture while keeping the
    # production watchlist cardinality contract in the scanner.
    watchlist.write_text(watchlist.read_text(encoding="utf-8").replace("name: Entity 0", "name: Dự án cải tạo Hồ Tây").replace("queries: [\"Entity 0\"]", "queries: [\"cải tạo Hồ Tây\"]"), encoding="utf-8")
    store = TimelineStore(tmp_path / "data")
    first = scan_week(
        "2026-W37", provider=JsonSearchProvider(input_file), watchlist_path=watchlist,
        store=store, vault_root=tmp_path / "vault", now=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    second = scan_week(
        "2026-W37", provider=JsonSearchProvider(input_file), watchlist_path=watchlist,
        store=store, vault_root=tmp_path / "vault", now=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    assert len(first) == 1
    assert second == []
    assert (tmp_path / "data" / "snapshots" / "2026-W37.json").exists()
    assert (tmp_path / "vault" / "local_beat" / "entity-0.md").exists()


def test_guest_angle_rejects_fact_id_that_is_not_active_r3() -> None:
    item = build_beat_items(_entity(), [_result()], detected_at="2026-09-09T00:00:00+00:00")[0]

    def provider(_item):
        return {
            "entity_id": item.entity_id,
            "beat_item_id": item.id,
            "status": item.status.value,
            "guest_question": "Đường có bị rào không?",
            "concrete_details": ["Đường Quảng An", "Từ Hoa"],
            "what_we_can_say": "Chia sẻ hướng đi thực dụng.",
            "what_we_cannot_claim": ["Mốc hoàn thành chưa có R3."],
            "evidence_urls": [item.url],
            "evidence_date": "2026-09-09",
            "fact_ids_r3": ["fact.not-approved"],
        }

    assert extract_guest_angle(item, provider, active_fact_ids_r3={"fact.approved"}) is None

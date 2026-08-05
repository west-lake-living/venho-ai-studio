from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from analytics_feedback.stores import AttributionEventStore, SnapshotStore
from publishing_gateway.publication_registry import PublicationRegistry
from strategy_memory.cli import app
from strategy_memory.collect_pilot_evidence import collect_pilot_snapshots

runner = CliRunner()


def _seed_real_pilot_data(data_root: Path, *, n: int = 5) -> None:
    """Real registry + real SnapshotStore + real AttributionEventStore rows
    -- same shape daily_cycle/M08AnalyticsBridge/the `attribute` CLI would
    produce, not synthetic strategy_memory-only fixtures."""
    registry = PublicationRegistry("venho_hotel", data_root=data_root)
    snapshot_store = SnapshotStore("venho_hotel", data_root)
    attribution_store = AttributionEventStore("venho_hotel", data_root)

    for index in range(n):
        publication_id = f"pub-p7-{index}"
        reserved = registry.reserve(
            {
                "publication_id": publication_id,
                "content_package_id": f"pkg-p7-{index}",
                "idempotency_key": f"idem-p7-{index}",
                "platform": "zalo",
            }
        )
        registry.update(reserved["publication_id"], status="PUBLISHED", pillar="lake_view_rooms")

        snapshot_store.save(
            f"snap-p7-{index}",
            {
                "snapshot_id": f"snap-p7-{index}",
                "package_id": f"pkg-p7-{index}",
                "platform": "zalo",
                "pillar": "lake_view_rooms",
                "metrics": {"reach": 100},
            },
        )
        attribution_store.save(
            f"conv-p7-{index}",
            {"id": f"conv-p7-{index}", "publication_id": publication_id, "attribution_status": "direct"},
        )


def test_collect_pilot_snapshots_joins_real_registry_snapshot_and_attribution_stores(tmp_path: Path) -> None:
    _seed_real_pilot_data(tmp_path)

    rows = collect_pilot_snapshots(project="venho_hotel", data_root=tmp_path)

    assert len(rows) == 5
    assert all(row["pillar"] == "lake_view_rooms" and row["platform"] == "zalo" for row in rows)
    assert all(row["qualified_booking_signals"] == 1 for row in rows)
    assert all(row["eligible_reach"] == 100 for row in rows)


def test_collect_pilot_snapshots_excludes_unattributed_events_and_orphan_snapshots(tmp_path: Path) -> None:
    registry = PublicationRegistry("venho_hotel", data_root=tmp_path)
    reserved = registry.reserve(
        {"publication_id": "pub-orphan", "content_package_id": "pkg-orphan", "idempotency_key": "idem-orphan", "platform": "zalo"}
    )
    registry.update(reserved["publication_id"], status="PUBLISHED", pillar="guest_voice")
    SnapshotStore("venho_hotel", tmp_path).save(
        "snap-orphan", {"snapshot_id": "snap-orphan", "package_id": "pkg-orphan", "platform": "zalo", "pillar": "guest_voice", "metrics": {"reach": 50}}
    )
    AttributionEventStore("venho_hotel", tmp_path).save(
        "conv-unattributed", {"id": "conv-unattributed", "publication_id": "pub-orphan", "attribution_status": "unattributed"}
    )
    # A snapshot with no matching publication (package_id typo/stale) must be skipped, not crash.
    SnapshotStore("venho_hotel", tmp_path).save(
        "snap-no-pub", {"snapshot_id": "snap-no-pub", "package_id": "pkg-does-not-exist", "platform": "zalo", "pillar": "x", "metrics": {"reach": 999}}
    )

    rows = collect_pilot_snapshots(project="venho_hotel", data_root=tmp_path)

    assert len(rows) == 1
    assert rows[0]["publication_id"] == "pub-orphan"
    assert rows[0]["qualified_booking_signals"] == 0  # unattributed does not count


def test_weekly_brief_cli_produces_a_real_recommendation_once_sample_size_is_met(tmp_path: Path) -> None:
    _seed_real_pilot_data(tmp_path, n=5)

    result = runner.invoke(
        app,
        [
            "weekly-brief", "--week-id", "2026-W32", "--baseline-qbsr", "0.0", "--min-sample-size", "5",
            "--data-root", str(tmp_path), "--questions-root", str(tmp_path / "research_questions"),
        ],
    )
    assert result.exit_code == 0, result.output
    brief = json.loads(result.output)
    assert brief["advisory_only"] is True
    assert brief["status"] == "pending_approval"
    assert len(brief["recommendations"]) == 1
    assert brief["recommendations"][0]["scope"] == {"pillar": "lake_view_rooms", "platform": "zalo"}
    assert brief["recommendations"][0]["id"]


def test_weekly_brief_cli_is_inconclusive_below_sample_size(tmp_path: Path) -> None:
    _seed_real_pilot_data(tmp_path, n=2)  # below the default min_sample_size=5

    result = runner.invoke(
        app,
        ["weekly-brief", "--week-id", "2026-W32", "--data-root", str(tmp_path), "--questions-root", str(tmp_path / "research_questions")],
    )

    assert result.exit_code == 0, result.output
    brief = json.loads(result.output)
    assert brief["recommendations"] == []
    # INCONCLUSIVE must also write the real research-question feedback loop
    # (plan §14: "vòng phản hồi analytics -> research/questions/").
    assert list((tmp_path / "research_questions").glob("*.md"))


def test_promote_then_list_promoted_round_trip(tmp_path: Path) -> None:
    _seed_real_pilot_data(tmp_path, n=5)
    brief_result = runner.invoke(
        app,
        [
            "weekly-brief", "--week-id", "2026-W32", "--min-sample-size", "5",
            "--data-root", str(tmp_path), "--questions-root", str(tmp_path / "research_questions"),
        ],
    )
    pattern = json.loads(brief_result.output)["recommendations"][0]["pattern"]

    promote_result = runner.invoke(
        app,
        ["promote", "--week-id", "2026-W32", "--pattern", pattern, "--approved-by", "harry", "--data-root", str(tmp_path)],
    )
    assert promote_result.exit_code == 0, promote_result.output
    assert json.loads(promote_result.output)["promoted"]["status"] == "approved"

    list_result = runner.invoke(app, ["list-promoted", "--data-root", str(tmp_path)])
    assert list_result.exit_code == 0, list_result.output
    promoted = json.loads(list_result.output)
    assert len(promoted) == 1
    assert promoted[0]["approved_by"] == "harry"


def test_promote_rejects_a_pattern_not_in_any_saved_brief(tmp_path: Path) -> None:
    _seed_real_pilot_data(tmp_path, n=5)
    runner.invoke(
        app,
        [
            "weekly-brief", "--week-id", "2026-W32", "--min-sample-size", "5",
            "--data-root", str(tmp_path), "--questions-root", str(tmp_path / "research_questions"),
        ],
    )

    result = runner.invoke(
        app,
        ["promote", "--week-id", "2026-W32", "--pattern", "made up pattern that was never generated", "--approved-by", "harry", "--data-root", str(tmp_path)],
    )

    assert result.exit_code == 1

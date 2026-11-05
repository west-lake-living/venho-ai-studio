from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
import pytest

from analytics_feedback.insights_backfill import _read_one_metric, backfill_insights, insights_report
from shared.meta.graph_client import MetaErrorKind, MetaGraphError


class _FakeClient:
    def __init__(self):
        self.calls = []

    def get_insights(self, object_id, metrics, period):
        self.calls.append((object_id, tuple(metrics), period))
        value = 42 if object_id == "post-hanoi-synthetic" else 7
        return {"data": [{"name": metrics[0], "values": [{"value": value}], "_synthetic": True}]}


class _MetricClient:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def get_insights(self, object_id, metrics, period):
        if self.error:
            raise self.error
        return {"data": [{"name": metrics[0], "values": [{"value": self.value}], "_synthetic": True}]}


def _write_yaml(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _sources(tmp_path: Path):
    config_root = tmp_path / "config"
    data_root = tmp_path / "data"
    channels = {
        "timezone": "Asia/Ho_Chi_Minh",
        "channels": [
            {"channel_id": "fb_hanoi", "environment": "production", "platform": "facebook", "remote_page_id": "page-hanoi"},
            {"channel_id": "fb_venho", "environment": "production", "platform": "facebook", "remote_page_id": "page-venho"},
        ],
    }
    candidates = {
        "api_version": "vTEST",
        "channels": {
            channel_id: {"api_version": "vTEST", "token_env": f"TOKEN_{channel_id}", "collection_edge": "posts"}
            for channel_id in ("fb_hanoi", "fb_venho")
        },
    }
    metrics = {"metrics": [{"name": "synthetic_reach", "provider_field": "synthetic_reach", "scope": "post", "period": "lifetime", "availability": "VERIFIED"}]}
    registry = {
        "_synthetic": True,
        "publications": [{
            "publication_id": "pub-hanoi-synthetic", "platform": "facebook", "status": "PUBLISHED",
            "platform_post_id": "post-hanoi-synthetic", "published_at": "2026-11-04T09:10:00+07:00",
            "updated_at": "2026-11-04T09:10:00+07:00", "pillar": "local_discovery",
            "content": {"image_run_path": "synthetic.jpg", "text": "Synthetic caption"},
        }],
    }
    _write_yaml(config_root / "growth_engine" / "channels.yaml", channels)
    _write_yaml(config_root / "growth_engine" / "meta_probe_candidates.yaml", candidates)
    _write_yaml(config_root / "growth_engine" / "metrics_registry.yaml", metrics)
    registry_path = data_root / "venho_hotel" / "publishing" / "publication_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    report_root = tmp_path / "outside-git" / "growth-reports"
    reconcile = report_root / "channel_reconcile" / "2026-11-05.json"
    reconcile.parent.mkdir(parents=True, exist_ok=True)
    reconcile.write_text(json.dumps({"_synthetic": True, "results": [{
        "channel_id": "fb_venho", "status": "UNTRACKED", "post_id": "post-venho-synthetic",
        "created_at_ms": int(datetime(2026, 11, 4, 9, 15, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")).timestamp() * 1000),
    }]}), encoding="utf-8")
    return config_root, data_root, report_root


def test_backfill_uses_external_sqlite_schema_and_is_idempotent_per_observation(tmp_path: Path) -> None:
    config_root, data_root, report_root = _sources(tmp_path)
    client = _FakeClient()
    now = datetime(2026, 11, 5, 9, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    factory = lambda channel_id, candidates_path, env: (client, "vTEST")

    first = backfill_insights(
        days=90, config_root=config_root, data_root=data_root, reports_root=report_root,
        now=now, env={}, client_factory=factory,
    )
    second = backfill_insights(
        days=90, config_root=config_root, data_root=data_root, reports_root=report_root,
        now=now, env={}, client_factory=factory,
    )

    assert first["inserted"] == 2
    assert second["inserted"] == 0
    assert len(client.calls) == 4
    assert all(len(call[1]) == 1 for call in client.calls)  # each metric is fetched separately
    database = report_root / "insights.db"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT delivery_id, value, value_state, dimensions_json FROM metric_observations ORDER BY delivery_id"
        ).fetchall()
        assert connection.execute("PRAGMA foreign_key_list(metric_observations)").fetchall() == []
    assert len(rows) == 2
    by_delivery = {row[0]: row for row in rows}
    assert by_delivery["pub-hanoi-synthetic"][2] == "VALUE" and by_delivery["pub-hanoi-synthetic"][1] == 42
    manual = by_delivery["manual:fb_venho:post-venho-synthetic"]
    assert manual[2] == "VALUE" and manual[1] == 7
    assert json.loads(manual[3])["channel_id"] == "fb_venho"
    assert Path(first["database"]).is_relative_to(report_root)

    output = insights_report(reports_root=report_root, now=now)
    report_text = output.read_text(encoding="utf-8")
    assert "fb_hanoi" in report_text and "fb_venho" in report_text
    assert "đăng tay" in report_text


def test_unverified_metrics_are_skipped_without_meta_calls(tmp_path: Path) -> None:
    config_root, data_root, report_root = _sources(tmp_path)
    metrics_path = config_root / "growth_engine" / "metrics_registry.yaml"
    _write_yaml(metrics_path, {"metrics": [{"name": "reach", "provider_field": "REQUIRED_FROM_P0", "availability": "AWAITING_P0_T04"}]})

    result = backfill_insights(
        days=90, config_root=config_root, data_root=data_root, reports_root=report_root,
        now=datetime(2026, 11, 5, 9, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")), env={},
        client_factory=lambda *args: (_ for _ in ()).throw(AssertionError("unverified metric must not call Meta")),
    )

    assert result["inserted"] == 0
    assert all(item["reason"] == "no_verified_metrics" for item in result["skipped"])


@pytest.mark.parametrize(
    ("client", "expected"),
    [
        (_MetricClient(0), (0, "ZERO", None)),
        (_MetricClient(None), (None, "NULL", None)),
        (_MetricClient(error=MetaGraphError(None, 400)), (None, "UNAVAILABLE", "UNSUPPORTED")),
        (_MetricClient(error=MetaGraphError(MetaErrorKind.PERMISSION, 403)), (None, "ERROR", "META_PERMISSION")),
    ],
)
def test_metric_value_states_keep_zero_null_unsupported_and_error_distinct(client, expected) -> None:
    result = _read_one_metric(
        client,
        {"post_id": "post-synthetic"},
        {"provider_field": "metric_synthetic", "period": "lifetime"},
    )

    assert result == expected

from __future__ import annotations

# _synthetic: true — cần thay bằng fixture thật từ P0-T03/P0-T04.

from pathlib import Path

import yaml

from scripts.growth_engine.probe_meta_read import DEFAULT_CANDIDATES, _parser, run_probe
from shared.meta.graph_client import MetaGraphError


class _FakeClient:
    def __init__(self, *, api_version, access_token, collection_edge):
        self.api_version = api_version
        self.access_token = access_token
        self.collection_edge = collection_edge
        self.insight_calls = []
        self.list_calls = []
        self.object_calls = []

    def get_object(self, object_id, fields):
        self.object_calls.append((object_id, tuple(fields)))
        if fields == ["id"]:
            return {"id": object_id, "_synthetic": True}
        return {fields[0]: f"synthetic-{fields[0]}", "_synthetic": True}

    def get_insights(self, object_id, metrics, period):
        self.insight_calls.append((object_id, tuple(metrics), period))
        if metrics[0] == "metric_unavailable":
            raise MetaGraphError(None, 400)
        return {"data": [{"name": metrics[0], "values": [{"value": 1}], "_synthetic": True}]}

    def list_recent_posts(self, account_id, since_ms, until_ms, fields, max_pages):
        self.list_calls.append((account_id, tuple(fields), max_pages))
        return [{"id": "post-synthetic", "message": "caption", "_synthetic": True}]


def _write_yaml(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _config(tmp_path: Path, *, channel_id: str, mode: str = "post"):
    account_id = {"fb_hanoi": "page-hanoi", "fb_venho": "page-venho", "ig_venho": "ig-account"}[channel_id]
    post_fields = ["id", "message"]
    if channel_id.startswith("fb_"):
        post_fields.extend(
            [
                "reactions.summary(total_count).limit(0)",
                "comments.summary(total_count).limit(0)",
            ]
        )
    candidate = {
        "api_version": "vTEST", "platform": "facebook" if channel_id.startswith("fb_") else "instagram",
        "account_id": account_id, "token_env": f"TOKEN_{channel_id}", "collection_edge": "posts",
        "list_recent": mode == "recent", "recent_days": 7, "max_pages": 2,
        "post_fields": post_fields, "metrics": [
            {"name": "metric_unavailable", "period": "lifetime"},
            {"name": "metric_readable", "period": None},
        ],
    }
    if mode == "post":
        candidate["post_id"] = "post-id-synthetic"
    candidates_path = tmp_path / "meta_probe_candidates.yaml"
    _write_yaml(candidates_path, {"api_version": "vTEST", "channels": {channel_id: candidate}, "_synthetic": True})
    channels_path = tmp_path / "channels.yaml"
    _write_yaml(channels_path, {"channels": [{
        "channel_id": channel_id, "environment": "production", "platform": candidate["platform"],
        "remote_page_id" if channel_id.startswith("fb_") else "remote_account_id": account_id,
    }], "_synthetic": True})
    args = _parser().parse_args(["--channel", channel_id, "--list-recent"] if mode == "recent" else ["--channel", channel_id])
    args.candidates = candidates_path
    args.channels = channels_path
    return args


def test_probe_marks_metric_errors_unsupported_and_continues(tmp_path: Path) -> None:
    args = _config(tmp_path, channel_id="fb_hanoi")
    client = _FakeClient(api_version="vTEST", access_token="synthetic-token", collection_edge="posts")

    result = run_probe(args, {"TOKEN_fb_hanoi": "synthetic-token"}, client_factory=lambda **kwargs: client)

    assert [row["result"] for row in result["metrics"]] == ["UNSUPPORTED", "READABLE"]
    assert [call[1][0] for call in client.insight_calls] == ["metric_unavailable", "metric_readable"]
    assert client.insight_calls[0][2] == "lifetime"
    assert client.insight_calls[1][2] is None
    assert "synthetic-token" not in str(result)


def test_probe_includes_safe_meta_error_identifiers(tmp_path: Path) -> None:
    args = _config(tmp_path, channel_id="fb_hanoi")

    class _ErrorClient(_FakeClient):
        def get_insights(self, object_id, metrics, period):
            raise MetaGraphError(None, 400, provider_code=100, provider_subcode=33, provider_type="GraphMethodException")

    result = run_probe(
        args,
        {"TOKEN_fb_hanoi": "synthetic-token"},
        client_factory=lambda **kwargs: _ErrorClient(**kwargs),
    )

    first_metric = result["metrics"][0]
    assert first_metric["meta_error_code"] == 100
    assert first_metric["meta_error_subcode"] == 33
    assert first_metric["meta_error_type"] == "GraphMethodException"


def test_probe_uses_posts_edge_for_fb_venho_list_recent(tmp_path: Path) -> None:
    args = _config(tmp_path, channel_id="fb_venho", mode="recent")
    client = _FakeClient(api_version="vTEST", access_token="synthetic-token", collection_edge="posts")

    result = run_probe(args, {"TOKEN_fb_venho": "synthetic-token"}, client_factory=lambda **kwargs: client)

    assert result["recent_posts"][0]["id"] == "post-synthetic"
    assert client.list_calls[0][0] == "page-venho"
    assert client.list_calls[0][2] == 2


def test_facebook_post_id_and_list_recent_use_the_same_engagement_field_list() -> None:
    candidates = yaml.safe_load(DEFAULT_CANDIDATES.read_text(encoding="utf-8"))["channels"]
    hanoi_fields = candidates["fb_hanoi"]["post_fields"]
    venho_fields = candidates["fb_venho"]["post_fields"]
    assert hanoi_fields == venho_fields
    assert {
        "reactions.summary(total_count).limit(0)",
        "comments.summary(total_count).limit(0)",
    }.issubset(hanoi_fields)

    post_args = _parser().parse_args(["--channel", "fb_hanoi"])
    recent_args = _parser().parse_args(["--channel", "fb_hanoi", "--list-recent"])
    post_client = _FakeClient(api_version="v27.0", access_token="synthetic-token", collection_edge="posts")
    recent_client = _FakeClient(api_version="v27.0", access_token="synthetic-token", collection_edge="posts")
    environment = {"GE_META_READ_TOKEN_FB_HANOI": "synthetic-token"}

    run_probe(post_args, environment, client_factory=lambda **kwargs: post_client)
    run_probe(recent_args, environment, client_factory=lambda **kwargs: recent_client)

    post_fields = [fields[0] for object_id, fields in post_client.object_calls if object_id == candidates["fb_hanoi"]["post_id"]]
    recent_fields = list(recent_client.list_calls[0][1])
    assert post_fields == recent_fields == hanoi_fields

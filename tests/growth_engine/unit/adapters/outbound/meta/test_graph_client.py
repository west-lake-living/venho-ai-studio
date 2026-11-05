from __future__ import annotations

import json
from collections import deque
from typing import Any

import pytest

from growth_engine.adapters.outbound.meta.graph_client import (
    GraphClient,
    MetaErrorKind,
    MetaGraphError,
)
from shared.meta.graph_client import ReadOnlyGraphClient


_SYNTHETIC = {"_synthetic": True}


class FakeResponse:
    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = json.dumps(body).encode("utf-8")


class FakeTransport:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = deque(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, *, headers: dict[str, str], timeout: float) -> FakeResponse:
        self.calls.append({"method": "GET", "url": url, "headers": headers, "timeout": timeout})
        return self.responses.popleft()


def _client(transport: FakeTransport) -> GraphClient:
    return GraphClient(
        api_version="vTEST",
        access_token="synthetic-secret-token",
        collection_edge="synthetic-post-edge",
        transport=transport,
    )


def test_get_object_uses_pinned_version_and_never_puts_token_in_url() -> None:
    transport = FakeTransport([FakeResponse(200, {"id": "object-1", **_SYNTHETIC})])
    client = _client(transport)

    result = client.get_object("object-1", ["field_x", "field_y"])

    assert result["id"] == "object-1"
    assert "/vTEST/object-1" in transport.calls[0]["url"]
    assert "fields=field_x%2Cfield_y" in transport.calls[0]["url"]
    assert "synthetic-secret-token" not in transport.calls[0]["url"]
    assert transport.calls[0]["headers"]["Authorization"] == "Bearer synthetic-secret-token"
    assert "synthetic-secret-token" not in repr(client)


def test_list_recent_posts_stops_after_max_pages_and_follows_same_host_cursor() -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "data": [{"id": "one", **_SYNTHETIC}],
                    "paging": {"next": "https://graph.facebook.com/vTEST/account/synthetic-post-edge?after=cursor"},
                },
            ),
            FakeResponse(
                200,
                {
                    "data": [{"id": "two", **_SYNTHETIC}],
                    "paging": {"next": "https://graph.facebook.com/vTEST/account/synthetic-post-edge?after=more"},
                },
            ),
        ]
    )
    client = _client(transport)

    result = client.list_recent_posts("account", 1000, 2000, ["field_x"], max_pages=2)

    assert [item["id"] for item in result] == ["one", "two"]
    assert len(transport.calls) == 2
    assert "since=1" in transport.calls[0]["url"]
    assert "until=2" in transport.calls[0]["url"]
    assert "after=cursor" in transport.calls[1]["url"]
    assert all(call["method"] == "GET" for call in transport.calls)


def test_list_recent_posts_rejects_next_url_on_another_host() -> None:
    transport = FakeTransport(
        [
            FakeResponse(
                200,
                {
                    "data": [],
                    "paging": {"next": "https://example.invalid/vTEST/account/edge?after=cursor"},
                },
            )
        ]
    )

    with pytest.raises(MetaGraphError) as caught:
        _client(transport).list_recent_posts("account", 1000, 2000, ["field_x"], max_pages=3)

    assert caught.value.kind is MetaErrorKind.TRANSIENT
    assert len(transport.calls) == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, MetaErrorKind.AUTH),
        (403, MetaErrorKind.PERMISSION),
        (404, MetaErrorKind.NOT_FOUND),
        (429, MetaErrorKind.RATE_LIMIT),
        (503, MetaErrorKind.TRANSIENT),
    ],
)
def test_http_status_errors_are_classified_without_exposing_body_or_token(
    status: int, expected: MetaErrorKind
) -> None:
    transport = FakeTransport(
        [FakeResponse(status, {"message": "synthetic-secret-token", **_SYNTHETIC})]
    )

    with pytest.raises(MetaGraphError) as caught:
        _client(transport).get_object("object-1", ["field_x"])

    assert caught.value.kind is expected
    assert "synthetic-secret-token" not in str(caught.value)
    assert "synthetic-secret-token" not in repr(caught.value)


def test_get_insights_passes_requested_metrics_and_period_without_post_surface() -> None:
    transport = FakeTransport([FakeResponse(200, {"data": [{"name": "metric_x", **_SYNTHETIC}]})])
    client = _client(transport)

    result = client.get_insights("object-1", ["metric_x", "metric_y"], "period_x")

    assert result["data"][0]["name"] == "metric_x"
    assert "metric=metric_x%2Cmetric_y" in transport.calls[0]["url"]
    assert "period=period_x" in transport.calls[0]["url"]
    assert not hasattr(client, "post")
    assert not hasattr(client, "delete")
    assert transport.calls[0]["method"] == "GET"


def test_get_insights_can_omit_period_for_media_level_candidate_metrics() -> None:
    transport = FakeTransport([FakeResponse(200, {"data": [{"name": "metric_x", **_SYNTHETIC}]})])
    client = _client(transport)

    client.get_insights("media-1", ["metric_x"])

    assert "metric=metric_x" in transport.calls[0]["url"]
    assert "period=" not in transport.calls[0]["url"]
    assert transport.calls[0]["method"] == "GET"


@pytest.mark.parametrize("version", ["", "latest", "REQUIRED_FROM_P0"])
def test_api_version_must_be_configured_and_pinned(version: str) -> None:
    with pytest.raises(ValueError):
        GraphClient(
            api_version=version,
            access_token="synthetic-secret-token",
            collection_edge="synthetic-post-edge",
            transport=FakeTransport([]),
        )


def test_growth_adapter_wraps_the_shared_read_only_graph_client() -> None:
    assert issubclass(GraphClient, ReadOnlyGraphClient)

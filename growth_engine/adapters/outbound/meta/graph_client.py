from __future__ import annotations

from shared.meta.graph_client import (
    GraphResponse,
    GraphTransport,
    MetaErrorKind,
    MetaGraphError,
    ReadOnlyGraphClient,
    UrllibGetTransport,
)


class GraphClient(ReadOnlyGraphClient):
    """Growth Engine adapter over the GET-only client shared with legacy code."""


__all__ = [
    "GraphClient",
    "GraphResponse",
    "GraphTransport",
    "MetaErrorKind",
    "MetaGraphError",
    "UrllibGetTransport",
]

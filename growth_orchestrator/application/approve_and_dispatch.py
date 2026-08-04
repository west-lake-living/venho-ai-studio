from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from growth_orchestrator.bridges.m07_publishing_bridge import (
    M07PublishingBridge,
    m07_publishing_bridge_from_env,
)
from publishing_gateway.publication_registry import PublicationRegistry

PENDING_STATUS = "PENDING_APPROVAL"


def list_pending(
    *,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
) -> list[dict]:
    registry = registry or PublicationRegistry(project, data_root=data_root)
    return [item for item in registry.load()["publications"] if item.get("status") == PENDING_STATUS]


def approve_and_dispatch(
    publication_id: str,
    *,
    approved_by: str,
    project: str = "venho_hotel",
    data_root: Path = Path("data/projects"),
    registry: Optional[PublicationRegistry] = None,
    bridge: Optional[M07PublishingBridge] = None,
) -> dict:
    """Approve a queued draft and immediately dispatch it (Approve-triggers-publish).

    Only PENDING_APPROVAL rows (produced by `daily_cycle.run_daily_cycle`) can
    be approved -- this is the human gate between content prep (cron) and the
    real Make.com webhook firing (this function). Dispatch failure does not
    revert the approval: the row is marked GATEWAY_ERROR so the operator can
    retry the dispatch instead of re-approving.
    """
    registry = registry or PublicationRegistry(project, data_root=data_root)
    publication = registry.find(publication_id)
    if publication is None:
        raise KeyError(f"Unknown publication_id: {publication_id}")
    if publication.get("status") != PENDING_STATUS:
        raise ValueError(f"publication_id {publication_id} is not {PENDING_STATUS} (status={publication.get('status')})")

    bridge = bridge or m07_publishing_bridge_from_env(os.environ)
    command = {
        "publication_id": publication["publication_id"],
        "idempotency_key": publication["idempotency_key"],
        "content_package_id": publication["content_package_id"],
        "platform": publication["platform"],
        "content": publication.get("content"),
    }
    response = bridge.dispatch(command)
    return registry.update(
        publication_id,
        status=response["status"],
        gateway_status=response["status"],
        approved_by=approved_by,
    )

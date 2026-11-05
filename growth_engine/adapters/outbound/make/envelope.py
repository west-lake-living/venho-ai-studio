from __future__ import annotations

from urllib.parse import urlsplit

from growth_engine.application.publishing.dispatch_outbox import DispatchLease


class MakeEnvelopeBuilder:
    """Map a leased command to the fixed growth.command.v2 webhook contract."""

    def build(self, lease: DispatchLease, *, media_url: str) -> dict[str, object]:
        parsed = urlsplit(media_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("signed media URL must use HTTPS")
        command = lease.command
        return {
            "schema_version": "growth.command.v2",
            "environment": lease.environment,
            "command_id": command.id,
            "delivery_id": command.delivery_id,
            "revision_id": command.revision_id,
            "channel_id": lease.channel_id,
            "channel_key": lease.channel_key,
            "platform": lease.platform,
            "remote_page_id": lease.remote_page_id,
            "idempotency_key": command.business_key,
            "payload_hash": lease.payload_hash,
            "dispatch_epoch": lease.dispatch_epoch,
            "execute_before_ms": command.expires_at_ms,
            "media_url": media_url,
            "command_token": command.envelope_token,
        }

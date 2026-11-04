from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Mapping
from uuid import uuid4


class InjectedCrash(RuntimeError):
    pass


AFTER_AUTHORIZE_COMMIT = "after_authorize_commit_before_response"
AFTER_POST_CREATE = "after_post_create_before_receipt"
AFTER_RECEIPT_APPLY = "between_receipt_apply_and_response"


@dataclass(frozen=True)
class FakeAuthorization:
    execute: bool
    execution_id: str | None = None
    grant_id: str | None = None
    reason: str | None = None


class FakeAuthorizeEndpoint:
    """Idempotent local stand-in for the internal authorize route."""

    def __init__(self, *, rejected_pages: set[str] | None = None) -> None:
        self.rejected_pages = set(rejected_pages or ())
        self.grants_by_command: dict[str, FakeAuthorization] = {}
        self.calls: Counter[str] = Counter()

    def __call__(self, envelope: Mapping[str, object]) -> FakeAuthorization:
        command_id = str(envelope["command_id"])
        page_id = str(envelope["remote_page_id"])
        self.calls[command_id] += 1
        existing = self.grants_by_command.get(command_id)
        if existing is not None:
            return FakeAuthorization(False, reason="ALREADY_AUTHORIZED")
        if page_id in self.rejected_pages:
            return FakeAuthorization(False, reason="PAGE_REJECTED")
        grant = FakeAuthorization(True, execution_id=str(uuid4()), grant_id=str(uuid4()))
        self.grants_by_command[command_id] = grant
        return grant


class FakeReceiptEndpoint:
    """Deduplicates the deterministic event key before applying a receipt."""

    def __init__(self) -> None:
        self.receipts: dict[str, dict[str, object]] = {}
        self.apply_count: Counter[str] = Counter()

    def __call__(self, body: dict[str, object]) -> bool:
        event_id = str(body["event_id"])
        existing = self.receipts.get(event_id)
        if existing is not None:
            if existing != body:
                raise ValueError("same receipt event ID has a different payload")
            return False
        self.receipts[event_id] = dict(body)
        self.apply_count[event_id] += 1
        return True


class FakeMake:
    """Local Make blueprint model with one counted post mutation per command."""

    def __init__(self) -> None:
        self.posts_by_command: dict[str, dict[str, object]] = {}
        self.mutation_counter: Counter[str] = Counter()
        self.delivery_calls: Counter[str] = Counter()

    def deliver(
        self,
        envelope: Mapping[str, object],
        *,
        authorize: Callable[[Mapping[str, object]], FakeAuthorization],
        receipt: Callable[[dict[str, object]], bool],
        crash_at: str | None = None,
    ) -> dict[str, object]:
        command_id = str(envelope["command_id"])
        delivery_id = str(envelope["delivery_id"])
        self.delivery_calls[command_id] += 1
        grant = authorize(envelope)
        if not grant.execute:
            return {"result": grant.reason or "NOT_AUTHORIZED", "post_id": None}
        if crash_at == AFTER_AUTHORIZE_COMMIT:
            raise InjectedCrash(AFTER_AUTHORIZE_COMMIT)

        post = self.posts_by_command.get(command_id)
        if post is None:
            post = {
                "post_id": f"fake-post-{uuid4()}",
                "page_id": str(envelope["remote_page_id"]),
                "delivery_id": delivery_id,
                "caption_hash": envelope.get("caption_hash"),
                "media_sha256": envelope.get("media_sha256"),
            }
            self.posts_by_command[command_id] = post
            self.mutation_counter[delivery_id] += 1
        if crash_at == AFTER_POST_CREATE:
            raise InjectedCrash(AFTER_POST_CREATE)

        event_id = f"{grant.grant_id}:POST_CREATED"
        receipt_body = {
            "event_id": event_id,
            "execution_id": grant.execution_id,
            "grant_id": grant.grant_id,
            "command_id": command_id,
            "delivery_id": delivery_id,
            "remote_page_id": str(envelope["remote_page_id"]),
            "outcome": "POST_CREATED",
            "platform_post_id": post["post_id"],
            "payload_hash": envelope["payload_hash"],
        }
        receipt(receipt_body)
        if crash_at == AFTER_RECEIPT_APPLY:
            raise InjectedCrash(AFTER_RECEIPT_APPLY)
        return {"result": "POST_CREATED", **post}

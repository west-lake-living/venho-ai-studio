from __future__ import annotations

from typing import Protocol, runtime_checkable

from growth_engine.application.dto import NotificationMessage, NotifyResult


@runtime_checkable
class Notifier(Protocol):
    def send(self, message: NotificationMessage) -> NotifyResult: ...

from __future__ import annotations

from collections.abc import Mapping


class ApplicationError(Exception):
    code = "ERR_GC2_APPLICATION"

    def __init__(self, message: str, details: Mapping[str, object] | None = None) -> None:
        self.message = message
        self.details = dict(details or {})
        super().__init__(message)


class NotFound(ApplicationError):
    code = "ERR_GC2_NOT_FOUND"


class PreconditionFailed(ApplicationError):
    code = "ERR_GC2_REVISION_CONFLICT"


class Conflict(ApplicationError):
    code = "ERR_GC2_STATE_CONFLICT"

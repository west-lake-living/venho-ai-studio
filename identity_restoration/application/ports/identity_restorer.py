from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ...domain.entities import RestorationRequest, RestoredCrop
from ...domain.value_objects import RestorerId

# THE MOST IMPORTANT FILE IN THIS DOCUMENT (v2.0 PHẦN 6). This Port is the
# only contract between business logic and compute hardware.
#
# READ BEFORE EDITING:
#   This Port does not know ComfyUI exists. Does not know HTTP exists. Does
#   not know Windows exists. If you add a vendor-named parameter here, you
#   have turned "swap compute host" into "edit business logic" — exactly what
#   ADR-GW-001 exists to prevent.


@dataclass(frozen=True)
class RestorerDescriptor:
    """Static metadata for manifest lineage: model ids, workflow sha, capability.
    Must not perform any network call."""

    restorer_id: RestorerId
    workflow_id: str | None
    workflow_sha256: str | None
    model_identifiers: tuple[str, ...] = ()


class IdentityRestorerPort(Protocol):
    restorer_id: RestorerId

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        """Restore identity inside the editable region of the crop.

        CALLER GUARANTEES (adapters do not need to redo these):
          - A2 authority sha256 already verified.
          - crop and mask are the same size; mask is L-mode.
          - concurrency lease already held.
          - cancel request already checked.

        ADAPTER OBLIGATIONS:
          - Call the backend EXACTLY ONCE. Retry is the use case's job, not
            the adapter's (an adapter that retries silently hides cost and
            corrupts the ledger).
          - Return valid PNG bytes at the requested size.
          - Raise RestorationError with a structured ERR_GW_* code, never a
            raw library exception.
          - Do NOT write an official artifact. Do NOT run QC. Do NOT decide
            pass/fail.
        """
        ...

    def describe(self) -> RestorerDescriptor:
        """Static metadata only. No network call."""
        ...

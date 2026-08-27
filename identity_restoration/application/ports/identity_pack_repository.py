from __future__ import annotations

from typing import Protocol

from ..identity_pack import IdentityPack


class IdentityPackRepositoryPort(Protocol):
    def get(self, identity_pack_id: str) -> IdentityPack:
        """Load and integrity-check an IdentityPack by stable ID."""
        ...

    def get_approved(self, identity_pack_id: str) -> IdentityPack:
        """Load an IdentityPack and require status APPROVED."""
        ...

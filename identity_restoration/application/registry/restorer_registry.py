from __future__ import annotations

from dataclasses import dataclass

from ...domain.value_objects import RestorerId
from ..ports.identity_restorer import IdentityRestorerPort


@dataclass
class RestorerRegistry:
    """Resolves a validated ``restorerId`` to a concrete Port implementation.

    restorerId is an ENUM at the contract boundary (schema §5.1) precisely so
    a free-form vendor string can never leak into the system the way
    `model: "gpt-image-2"` leaked into route.ts in v2.1 — this registry is the
    second half of that guard: even a valid enum value must be a *registered*
    restorer, or it fails loudly instead of silently no-op'ing.
    """

    restorers: dict[RestorerId, IdentityRestorerPort]
    default_id: RestorerId

    def resolve(self, restorer_id: RestorerId | None = None) -> IdentityRestorerPort:
        resolved_id = restorer_id or self.default_id
        try:
            return self.restorers[resolved_id]
        except KeyError as exc:
            available = ", ".join(sorted(self.restorers)) or "(none registered)"
            raise KeyError(f"Unknown or unregistered restorerId {resolved_id!r}. Available: {available}") from exc

from __future__ import annotations

# Kept as a re-export so call sites can depend on application/dto/ without
# reaching into application/ports/ directly; the type is owned by the Port
# module since it is part of the Port's return contract.
from ..ports.identity_restorer import RestorerDescriptor

__all__ = ["RestorerDescriptor"]

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PublishMode(str, Enum):
    DISABLED = "DISABLED"
    DRY_RUN = "DRY_RUN"
    LIVE_MANUAL = "LIVE_MANUAL"


@dataclass(frozen=True)
class RuntimeControls:
    mode: PublishMode
    dispatch_epoch: str
    global_pause: bool = False

    def __post_init__(self) -> None:
        if not self.dispatch_epoch.strip():
            raise ValueError("dispatch_epoch is required")
        if type(self.global_pause) is not bool:
            raise ValueError("global_pause must be a boolean")

    def can_dispatch(
        self,
        *,
        expected_epoch: str,
        channel_enabled: bool = True,
        channel_paused: bool = False,
    ) -> bool:
        return (
            self.mode is PublishMode.LIVE_MANUAL
            and not self.global_pause
            and self.dispatch_epoch == expected_epoch
            and channel_enabled
            and not channel_paused
        )

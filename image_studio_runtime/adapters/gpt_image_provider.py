from __future__ import annotations


class GPTImageProvider:
    model = "gpt-image-2"

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    def generate(self, prompt: str, *, size: str, quality: str) -> bytes:
        if not self.enabled:
            raise RuntimeError("Real image provider is disabled by feature flag")
        raise NotImplementedError("Wire gpt-image-2 client during optimization handoff")

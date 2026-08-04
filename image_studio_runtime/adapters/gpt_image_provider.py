from __future__ import annotations

import base64
from io import BytesIO
from typing import Any, Mapping, Optional

# gpt-image-1/2 only accept these exact size strings -- prompt_contract carries
# a portrait/square/landscape "WxH" convention (e.g. "1024x1280") from
# image_studio_runtime's own domain model, so it has to be snapped to the
# nearest API-valid size rather than passed straight through.
_VALID_API_SIZES = {"1024x1024", "1024x1536", "1536x1024", "auto"}
_VALID_QUALITIES = {"low", "medium", "high", "auto"}


def map_api_size(size: str) -> str:
    if size in _VALID_API_SIZES:
        return size
    try:
        width, height = (int(part) for part in size.lower().split("x"))
    except (ValueError, AttributeError):
        return "auto"
    if width == height:
        return "1024x1024"
    return "1024x1536" if height > width else "1536x1024"


def map_api_quality(quality: str) -> str:
    return quality if quality in _VALID_QUALITIES else "medium"


class GPTImageProvider:
    """Real gpt-image-2 provider -- text-to-image via `images.generate`, or
    `images.edit` when `reference_images` is given (CLAUDE.md: "text-only
    6-8.4/10, edit+ref 9/10" -- ref-based edit is the quality bar this
    universe already holds every other image pipeline to).

    `client` is dependency-injected (defaults to a lazily-constructed real
    `openai.OpenAI()` reading `OPENAI_API_KEY` from the environment) so tests
    can inject a fake with `.images.generate()`/`.images.edit()` and make 0
    real API calls, same discipline as `shared/http.py`'s adapters.
    """

    model = "gpt-image-2"

    def __init__(self, enabled: bool = False, *, client: Optional[Any] = None) -> None:
        self.enabled = enabled
        self._client = client

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client
        from openai import OpenAI

        return OpenAI()

    def generate(
        self,
        prompt: str,
        *,
        size: str,
        quality: str,
        reference_images: Optional[list[bytes]] = None,
    ) -> bytes:
        if not self.enabled:
            raise RuntimeError("Real image provider is disabled by feature flag")
        client = self._client_or_default()
        api_size = map_api_size(size)
        api_quality = map_api_quality(quality)

        if reference_images:
            files = [BytesIO(data) for data in reference_images]
            for index, buffer in enumerate(files):
                buffer.name = f"reference_{index}.png"
            response = client.images.edit(
                model=self.model,
                image=files if len(files) > 1 else files[0],
                prompt=prompt,
                size=api_size,
                quality=api_quality,
            )
        else:
            response = client.images.generate(
                model=self.model,
                prompt=prompt,
                size=api_size,
                quality=api_quality,
            )
        b64_data = response.data[0].b64_json
        if not b64_data:
            raise RuntimeError("gpt-image-2 response had no b64_json image data")
        return base64.b64decode(b64_data)


def gpt_image_provider_from_env(env: Mapping[str, str], *, client: Optional[Any] = None) -> GPTImageProvider:
    """Enable the real provider only when an OpenAI key is actually configured."""
    api_key = env.get("OPENAI_API_KEY")
    return GPTImageProvider(enabled=bool(api_key) and not api_key.startswith("YOUR_"), client=client)

from __future__ import annotations

from urllib.parse import urlparse


def is_valid_media_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

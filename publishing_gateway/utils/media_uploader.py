from __future__ import annotations

import hashlib
from typing import Iterable, List


def mock_upload_manifest(media_urls: Iterable[str]) -> List[dict]:
    return [{"source_url": url, "integrity": hashlib.sha256(url.encode("utf-8")).hexdigest()} for url in media_urls]

from __future__ import annotations

import re

_SAFE_SLUG = re.compile(r"^[A-Za-z0-9_.-]+$")


def ensure_safe_slug(value: str, *, field: str = "value") -> str:
    """Reject path-traversal-capable identifiers before they reach the filesystem.

    Values here (fact_key, rs_id, topic_slug, ...) are used verbatim as path
    components; without this guard a value like "../../etc/passwd" would
    escape the intended data directory.
    """
    if not value or not _SAFE_SLUG.match(value) or ".." in value:
        raise ValueError(f"{field} contains unsafe characters: {value!r}")
    return value

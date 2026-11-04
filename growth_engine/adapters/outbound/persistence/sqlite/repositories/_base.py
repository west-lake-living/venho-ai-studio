from __future__ import annotations

import json
import sqlite3
from typing import Any

from growth_engine.domain.kernel.hashing import canonical_json_bytes


def canonical_json(value: object) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def parse_json(value: str) -> Any:
    return json.loads(value)


def canonical_json_text(value: str) -> str:
    return canonical_json(parse_json(value))


class SqliteRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

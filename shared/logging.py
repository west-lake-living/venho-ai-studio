from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_LOG_FILE: Path | None = None


def init_log(log_path: Path) -> None:
    global _LOG_FILE
    _LOG_FILE = log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    # Machine-facing CLI commands reserve stdout for exactly one JSON
    # document. Human/provider diagnostics belong on stderr (and the optional
    # durable log file), otherwise a valid result is corrupted at the process
    # boundary.
    print(line, file=sys.stderr, flush=True)
    if _LOG_FILE:
        with _LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

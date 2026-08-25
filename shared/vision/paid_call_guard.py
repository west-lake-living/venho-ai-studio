"""Fail-closed guard and append-only ledger for paid Validator transports."""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping


class PaidCallBlocked(RuntimeError):
    """Raised before a paid provider transport can be reached."""


_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "validator_paid_call_context", default={}
)


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


@contextlib.contextmanager
def paid_call_context(values: Mapping[str, Any]) -> Iterator[None]:
    token = _context.set(dict(values))
    try:
        yield
    finally:
        _context.reset(token)


def current_paid_call_context() -> dict[str, Any]:
    return dict(_context.get())


class PaidCallGuard:
    """One guard for all Gemini Validator calls.

    Tests are always blocked before the SDK transport. Production live calls
    require the explicit VALIDATOR_LIVE_ENABLED gate and a finite budget.
    """

    def __init__(self, *, ledger_path: Path | None = None, max_calls: int | None = None) -> None:
        self.ledger_path = ledger_path or Path(
            os.environ.get(
                "VALIDATOR_PAID_CALL_LEDGER",
                "artifacts/identity-restoration/benchmarks/validator-paid-call-ledger.jsonl",
            )
        )
        self.max_calls = max_calls if max_calls is not None else int(os.environ.get("VALIDATOR_MAX_NEW_CALLS", "12"))

    def _records(self) -> list[dict[str, Any]]:
        if not self.ledger_path.is_file():
            return []
        records: list[dict[str, Any]] = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                records.append(item)
        return records

    def _append(self, payload: Mapping[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")

    def _common(self, *, model: str, sample_index: int, config: Mapping[str, Any]) -> dict[str, Any]:
        context = current_paid_call_context()
        return {
            "benchmarkId": context.get("benchmarkId"),
            "branch": context.get("branch"),
            "imageSha256": context.get("imageSha256"),
            "sampleIndex": sample_index,
            "provider": "gemini",
            "model": model,
            "validatorConfig": dict(config),
            "reason": context.get("reason", "missing Validator sample after historical evidence audit"),
            "historicalEvidenceSearch": context.get("historicalEvidenceSearch"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def before_call(self, *, model: str, sample_index: int, config: Mapping[str, Any]) -> dict[str, Any]:
        if os.environ.get("PYTEST_CURRENT_TEST") or _truthy("VALIDATOR_TEST_MODE"):
            raise PaidCallBlocked("paid Validator transport blocked during tests")
        if not _truthy("VALIDATOR_LIVE_ENABLED"):
            raise PaidCallBlocked("VALIDATOR_LIVE_ENABLED=true is required for live Validator calls")
        records = self._records()
        attempted = sum(1 for item in records if item.get("event") == "intent")
        if attempted >= self.max_calls:
            raise PaidCallBlocked(f"Validator paid-call budget exhausted: {attempted}/{self.max_calls}")
        record = self._common(model=model, sample_index=sample_index, config=config)
        record.update({"event": "intent", "callNumber": attempted + 1, "budgetRemaining": self.max_calls - attempted - 1})
        self._append(record)
        return record

    def after_call(self, intent: Mapping[str, Any], *, response: Any = None, error: Exception | None = None, raw_path: str | None = None, parsed_path: str | None = None) -> None:
        usage = getattr(response, "usage_metadata", None)
        candidates = getattr(response, "candidates", None) or []
        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        record = dict(intent)
        record.update({
            "event": "result",
            "httpStatus": getattr(response, "status_code", None) if response is not None else None,
            "inputTokens": getattr(usage, "prompt_token_count", None),
            "outputTokens": getattr(usage, "candidates_token_count", None),
            "cachedTokens": getattr(usage, "cached_content_token_count", None),
            "finishReason": str(finish_reason) if finish_reason is not None else None,
            "success": error is None,
            "error": str(error) if error is not None else None,
            "rawResponsePath": raw_path,
            "parsedEvidencePath": parsed_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._append(record)

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


# Billable usage of every guarded call made by this process. A caller that owns the process
# (faceless-video runs one validation per subprocess) prices it from usage_summary().
_usage: dict[str, Any] = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "thought_tokens": 0, "complete": True}
# Holds the response objects themselves (not id()s, which are reused after collection).
_counted_responses: list[Any] = []


def _token_count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _record_usage(response: Any) -> None:
    if response is not None:
        # analyze_many reports a parse failure for a response already counted by _generate.
        if any(seen is response for seen in _counted_responses):
            return
        _counted_responses.append(response)
    _usage["calls"] += 1
    usage = getattr(response, "usage_metadata", None) if response is not None else None
    prompt = _token_count(getattr(usage, "prompt_token_count", None))
    candidates = _token_count(getattr(usage, "candidates_token_count", None))
    thoughts_raw = getattr(usage, "thoughts_token_count", None)
    # The SDK reports None (not 0) when the model produced no thinking tokens.
    thoughts = 0 if thoughts_raw is None else _token_count(thoughts_raw)
    if prompt is None or candidates is None or thoughts is None:
        _usage["complete"] = False
        return
    _usage["input_tokens"] += prompt
    _usage["output_tokens"] += candidates
    _usage["thought_tokens"] += thoughts


def usage_summary() -> dict[str, Any]:
    """Token totals of this process's guarded calls; complete=False when any call is unpriceable."""
    return dict(_usage)


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
        # A caller that owns one bounded attempt (faceless-video: one validation job attempt)
        # passes VALIDATOR_RUN_ID so the budget counts only that attempt's intents. Without it
        # the budget stays cumulative over the whole ledger (benchmark campaigns).
        self.run_id = os.environ.get("VALIDATOR_RUN_ID", "").strip() or None

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
        attempted = sum(
            1
            for item in records
            if item.get("event") == "intent" and (self.run_id is None or item.get("runId") == self.run_id)
        )
        if attempted >= self.max_calls:
            scope = f" for run {self.run_id}" if self.run_id else ""
            raise PaidCallBlocked(f"Validator paid-call budget exhausted{scope}: {attempted}/{self.max_calls}")
        record = self._common(model=model, sample_index=sample_index, config=config)
        record.update({
            "event": "intent", "runId": self.run_id,
            "callNumber": attempted + 1, "budgetRemaining": self.max_calls - attempted - 1,
        })
        self._append(record)
        return record

    def after_call(self, intent: Mapping[str, Any], *, response: Any = None, error: Exception | None = None, raw_path: str | None = None, parsed_path: str | None = None) -> None:
        # A call that reached the transport is billable even when it later failed to parse; one
        # that raised before any response has unknown usage.
        _record_usage(response)
        usage = getattr(response, "usage_metadata", None)
        candidates = getattr(response, "candidates", None) or []
        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        record = dict(intent)
        record.update({
            "event": "result",
            "httpStatus": getattr(response, "status_code", None) if response is not None else None,
            "inputTokens": getattr(usage, "prompt_token_count", None),
            "outputTokens": getattr(usage, "candidates_token_count", None),
            "thoughtsTokens": getattr(usage, "thoughts_token_count", None),
            "cachedTokens": getattr(usage, "cached_content_token_count", None),
            "finishReason": str(finish_reason) if finish_reason is not None else None,
            "success": error is None,
            "error": str(error) if error is not None else None,
            "rawResponsePath": raw_path,
            "parsedEvidencePath": parsed_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._append(record)

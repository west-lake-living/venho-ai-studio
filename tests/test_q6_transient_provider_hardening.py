from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from shared.vision.providers import gemini_vision
from shared.vision.paid_call_guard import PaidCallBlocked


class _Guard:
    calls: list[int] = []
    budget: int = 99

    def before_call(self, **_kwargs):
        if len(self.calls) >= self.budget:
            raise PaidCallBlocked("budget exhausted")
        self.calls.append(len(self.calls) + 1)
        return {"callNumber": self.calls[-1]}

    def after_call(self, *_args, **_kwargs):
        return None


def _provider(monkeypatch, outcomes, *, budget=99):
    guard = _Guard()
    guard.calls = []
    guard.budget = budget
    monkeypatch.setattr(gemini_vision, "PaidCallGuard", lambda: guard)
    monkeypatch.setattr(gemini_vision.time, "sleep", lambda _seconds: None)
    provider = object.__new__(gemini_vision.GeminiVisionProvider)
    provider.model = "gemini-test"
    provider.temperature = 0.0
    provider.raw_response_sink = None
    provider.transport_event_sink = None
    provider.last_transport_attempt_index = 0
    provider.client = SimpleNamespace()

    class _Models:
        def generate_content(self, **_kwargs):
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return SimpleNamespace(text=outcome, usage_metadata=None, candidates=[])

    provider.client.models = _Models()
    return provider, guard


def test_three_logical_samples_all_succeed_first_try(monkeypatch):
    provider, guard = _provider(
        monkeypatch, ["{}", "{}", "{}"]
    )
    for index in range(1, 4):
        provider._generate([], "prompt", sample_index=index)
    assert guard.calls == [1, 2, 3]


def test_sample_two_503_retries_same_logical_sample(monkeypatch):
    provider, guard = _provider(
        monkeypatch, ["{}", RuntimeError("503 UNAVAILABLE"), "{}", "{}"]
    )
    for index in (1, 2, 3):
        provider._generate([], "prompt", sample_index=index)
    assert guard.calls == [1, 2, 3, 4]
    assert provider.last_transport_attempt_index == 1


def test_sample_two_503_exhaustion_fails_closed_without_aggregate(monkeypatch):
    provider, guard = _provider(monkeypatch, ["{}", RuntimeError("503 UNAVAILABLE"), RuntimeError("503 UNAVAILABLE")])
    provider._generate([], "prompt", sample_index=1)
    with pytest.raises(RuntimeError, match="503 UNAVAILABLE"):
        provider._generate([], "prompt", sample_index=2)
    assert guard.calls == [1, 2, 3]


def test_non_retryable_provider_error_is_not_retried(monkeypatch):
    provider, guard = _provider(monkeypatch, [RuntimeError("400 INVALID_ARGUMENT")])
    with pytest.raises(RuntimeError, match="400 INVALID_ARGUMENT"):
        provider._generate([], "prompt", sample_index=1)
    assert guard.calls == [1]


def test_retry_budget_is_checked_before_retry_request(monkeypatch):
    provider, guard = _provider(monkeypatch, [RuntimeError("503 UNAVAILABLE")], budget=1)
    with pytest.raises(PaidCallBlocked, match="budget exhausted"):
        provider._generate([], "prompt", sample_index=1)
    assert guard.calls == [1]


def test_transport_events_are_durable_and_retry_keeps_sample_index(monkeypatch):
    provider, _guard = _provider(monkeypatch, [RuntimeError("503 UNAVAILABLE"), "{}"])
    events = []
    provider.transport_event_sink = events.append
    provider._generate([], "prompt", sample_index=2)
    finished = [event for event in events if event["phase"] == "request_finished"]
    assert [event["logicalSampleIndex"] for event in finished] == [2, 2]
    assert [event["transportAttemptIndex"] for event in finished] == [1, 2]
    assert finished[0]["errorCode"] == "PROVIDER_503"
    assert finished[1]["transportStatus"] == "200"


def test_face_cycle_checkpoints_each_success_and_aggregates_three(monkeypatch):
    import validator_studio.face_validator as face_module

    rubric = {
        "binary_gates": [{"id": "identity_structure"}],
        "weighted": {
            "facial_shape": 0.3, "eyes_and_brows": 0.25,
            "nose": 0.2, "mouth_and_chin": 0.15, "technical_quality": 0.1,
        },
    }
    payload = {
        "gates": [{"gate": "identity_structure", "passed": True}],
        "weighted_scores": {key: 90 for key in rubric["weighted"]}, "notes": [],
    }

    class _Client:
        last_raw_response = "{}"
        last_transport_attempt_index = 1

        def __init__(self, *args, **kwargs):
            self.raw_response_sink = None
            self.transport_event_sink = None

        def analyze_image(self, *_args, **_kwargs):
            return payload

    monkeypatch.setattr(face_module, "VisionClient", _Client)
    events: list[dict] = []
    observation = face_module._observe_face(
        Path("candidate.png"), {"project": "venho_hotel", "subject": "linh_an"},
        rubric, provider="gemini", samples=3, raw_response_sink=events.append,
        validation_cycle_id="cycle-q6",
    )
    assert observation.weighted_scores.facial_shape == 90
    checkpoints = [event for event in events if event.get("checkpointed")]
    assert [event["logicalSampleIndex"] for event in checkpoints] == [1, 2, 3]
    assert {event["cycleId"] for event in checkpoints} == {"cycle-q6"}


def test_cycle_ids_isolate_checkpoint_evidence(monkeypatch):
    import validator_studio.face_validator as face_module

    rubric = {
        "binary_gates": [{"id": "identity_structure"}],
        "weighted": {"facial_shape": 0.3, "eyes_and_brows": 0.25, "nose": 0.2,
                      "mouth_and_chin": 0.15, "technical_quality": 0.1},
    }
    payload = {"gates": [{"gate": "identity_structure", "passed": True}],
               "weighted_scores": {key: 90 for key in rubric["weighted"]}, "notes": []}

    class _Client:
        last_raw_response = "{}"
        last_transport_attempt_index = 1

        def __init__(self, *args, **kwargs):
            self.raw_response_sink = None
            self.transport_event_sink = None

        def analyze_image(self, *_args, **_kwargs):
            return payload

    monkeypatch.setattr(face_module, "VisionClient", _Client)
    first, second = [], []
    for cycle, sink in (("cycle-a", first), ("cycle-b", second)):
        face_module._observe_face(Path("candidate.png"), {"project": "venho_hotel", "subject": "linh_an"},
                                  rubric, provider="gemini", samples=1,
                                  raw_response_sink=sink.append, validation_cycle_id=cycle)
    assert {event["cycleId"] for event in first if event.get("checkpointed")} == {"cycle-a"}
    assert {event["cycleId"] for event in second if event.get("checkpointed")} == {"cycle-b"}

import socket

import pytest

from prompt_studio.optimizer_mock import optimize_mock
from prompt_studio.schemas.image_prompt import ImagePromptContract
from tests.test_prompt_contract_schema import SAMPLE_IMAGE


def _no_network(*args, **kwargs):
    raise AssertionError("optimizer_mock must not touch the network")


def test_optimize_mock_returns_unchanged_prompt_and_marks_metadata(monkeypatch):
    monkeypatch.setattr(socket, "socket", _no_network)
    contract = ImagePromptContract.model_validate(SAMPLE_IMAGE)

    optimized = optimize_mock(contract)

    assert optimized.final_prompt == contract.final_prompt
    assert optimized.negative_prompt == contract.negative_prompt
    assert optimized.required_dna == contract.required_dna
    assert optimized.optimizer.used is True
    assert optimized.optimizer.provider == "mock"
    assert optimized.optimizer.temperature == 0


def test_optimize_mock_is_deterministic_across_runs():
    contract = ImagePromptContract.model_validate(SAMPLE_IMAGE)
    first = optimize_mock(contract)
    second = optimize_mock(contract)
    assert first.model_dump() == second.model_dump()

from __future__ import annotations

import pytest

from identity_restoration.infrastructure.composition.env import read_restoration_env
from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)
from identity_restoration.infrastructure.restorers.comfyui_candidate_v3_adapter import (
    ComfyUiCandidateV3Adapter,
)
from identity_restoration.infrastructure.persistence.production_release_state import (
    ProductionReleaseState,
    write_production_release_state,
)
from pathlib import Path


FEATURE_FLAG = "IDR_CANDIDATE_V3_ENABLED"
ROOT = Path(__file__).resolve().parents[3]


def test_missing_candidate_v3_flag_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(FEATURE_FLAG, raising=False)

    assert read_restoration_env().candidate_v3_enabled is False


@pytest.mark.parametrize("value", ["false", "0", "off", "no", "FALSE", " Off "])
def test_explicit_false_values_disable_candidate_v3(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(FEATURE_FLAG, value)

    assert read_restoration_env().candidate_v3_enabled is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " On "])
def test_explicit_true_values_enable_the_configuration_flag(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv(FEATURE_FLAG, value)

    assert read_restoration_env().candidate_v3_enabled is True


def test_unknown_value_fails_closed_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(FEATURE_FLAG, "banana")

    assert read_restoration_env().candidate_v3_enabled is False


def test_explicit_candidate_v3_flag_registers_pinned_adapter_without_execution(tmp_path: Path) -> None:
    module = build_identity_restoration_module(
        RestorationEnv(candidate_v3_enabled=True, production_release_path=str(tmp_path / "missing-release.json")),
        repo_root=ROOT,
    )

    adapter = module.registry.resolve("comfyui-candidate-v3")
    assert isinstance(adapter, ComfyUiCandidateV3Adapter)
    assert adapter.gpu_execution_authorized is False


def test_human_active_release_selects_candidate_and_authorizes_only_its_gpu_path(tmp_path: Path) -> None:
    release = tmp_path / "production_release.json"
    write_production_release_state(release, ProductionReleaseState(
        active_production_version="candidate-v3", active_production_route="candidate-v3",
        feature_flag_state="ON", release_id="candidate-v3-test", promotion_authority="HUMAN",
        promotion_timestamp="2026-09-02T10:15:00Z", rollback_target="comfyui-local",
    ))
    module = build_identity_restoration_module(
        RestorationEnv(production_release_path=str(release)), repo_root=ROOT,
    )

    adapter = module.registry.resolve("comfyui-candidate-v3")
    assert isinstance(adapter, ComfyUiCandidateV3Adapter)
    assert adapter.gpu_execution_authorized is True
    assert module.registry.default_id == "comfyui-candidate-v3"

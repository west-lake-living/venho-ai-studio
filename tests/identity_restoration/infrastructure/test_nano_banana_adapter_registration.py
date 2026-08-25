from __future__ import annotations

from pathlib import Path

from identity_restoration.application.benchmark_executor import (
    NanoBananaEditRequest,
    NanoBananaEditResult,
)
from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)


ROOT = Path(__file__).resolve().parents[3]
A2 = ROOT / "staging/gw-p3/mac-final-20260824-dual-mask/evidence/input_a2.png"


class ExistingProductionPath:
    """Test double for the already-composed Venho OS production capability."""

    def capabilities(self):
        return {
            "ready": True,
            "providerConfigured": True,
            "fallbackEnabled": False,
            "provider": "nano-banana-2",
            "model": "gemini-3.1-flash-image",
            "blockers": [],
        }

    def masked_edit(self, request: NanoBananaEditRequest, *, run_id: str, attempt_id: str):
        raise AssertionError("physical provider must not be called by registration tests")


def _env(*, enabled: bool) -> RestorationEnv:
    return RestorationEnv(
        nano_banana_enabled=enabled,
        a2_path=str(A2.relative_to(ROOT)),
    )


def _factory(case, run_id, attempt_id, seed):
    return NanoBananaEditRequest(
        base_path=Path(case["baseFrame"]["path"]),
        a2_path=A2,
        mask_path=None,
        crop_transform=None,
        mask_version=None,
        seed_supported=False,
    )


def test_composition_registers_existing_path_only_when_enabled(tmp_path: Path):
    production_path = ExistingProductionPath()
    module = build_identity_restoration_module(
        _env(enabled=True),
        repo_root=ROOT,
        nano_banana_path=production_path,
        nano_banana_request_factory=_factory,
        benchmark_evidence_root=tmp_path / "evidence",
        canonical_a2_path=A2,
    )

    executor = module.nano_banana_executor
    assert executor is not None
    capability = executor.capabilities()["nano-banana-edit"]
    assert capability["ready"] is True
    assert capability["productionPathReused"] is True
    assert capability["provider"] == "nano-banana-2"
    assert capability["model"] == "gemini-3.1-flash-image"
    assert executor.edit_path.production_path is production_path


def test_absent_provider_configuration_does_not_register_adapter(tmp_path: Path):
    module = build_identity_restoration_module(
        _env(enabled=False),
        repo_root=ROOT,
        nano_banana_path=ExistingProductionPath(),
        nano_banana_request_factory=_factory,
        benchmark_evidence_root=tmp_path / "evidence",
        canonical_a2_path=A2,
    )
    assert module.nano_banana_executor is None


def test_incomplete_registration_fails_closed_even_when_enabled(tmp_path: Path):
    module = build_identity_restoration_module(
        _env(enabled=True),
        repo_root=ROOT,
        nano_banana_path=None,
        nano_banana_request_factory=_factory,
        benchmark_evidence_root=tmp_path / "evidence",
        canonical_a2_path=A2,
    )
    assert module.nano_banana_executor is None

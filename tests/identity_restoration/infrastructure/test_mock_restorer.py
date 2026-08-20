from __future__ import annotations

from identity_restoration.domain.entities import RestorationRequest
from identity_restoration.infrastructure.restorers.mock_restorer import MockIdentityRestorer


def _request(crop_png, mask_set, a2, seed=42, **kwargs):
    from identity_restoration.domain.value_objects import RestorationParams
    params = RestorationParams(denoise=0.45, steps=28, cfg=5.5, sampler="dpmpp_2m", scheduler="karras")
    return RestorationRequest(run_id="r", attempt_id="a", crop_png=crop_png, mask=mask_set, a2=a2,
                              workflow_id="mock-workflow", seed=seed, params=params)


def test_mock_restorer_output_differs_from_input(crop_png, mask_set, a2_png) -> None:
    from identity_restoration.domain.entities import A2Authority
    a2 = A2Authority.from_bytes(a2_png)
    restorer = MockIdentityRestorer()

    restored = restorer.restore(_request(crop_png, mask_set, a2))

    assert restored.png_bytes != crop_png
    assert (restored.width, restored.height) == (16, 16)


def test_mock_restorer_is_deterministic_given_same_seed(crop_png, mask_set, a2_png) -> None:
    from identity_restoration.domain.entities import A2Authority
    a2 = A2Authority.from_bytes(a2_png)
    restorer = MockIdentityRestorer()

    first = restorer.restore(_request(crop_png, mask_set, a2, seed=7))
    second = restorer.restore(_request(crop_png, mask_set, a2, seed=7))

    assert first.png_bytes == second.png_bytes


def test_mock_restorer_describe_has_no_workflow() -> None:
    descriptor = MockIdentityRestorer().describe()
    assert descriptor.restorer_id == "mock"
    assert descriptor.workflow_sha256 is None

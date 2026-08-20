from __future__ import annotations

import pytest

from identity_restoration.domain.entities import CropTransform
from identity_restoration.domain.policies.geometry import assert_crop_transform_round_trips


@pytest.mark.parametrize("box", [(0, 0, 100, 100), (201, 0, 888, 659), (17, 42, 900, 731)])
def test_crop_transform_round_trips(box: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = box
    transform = CropTransform.from_box(left, top, right, bottom, target_size=right - left)
    assert transform.round_trips()
    assert_crop_transform_round_trips(transform)


def test_crop_transform_to_box_matches_source_fields() -> None:
    transform = CropTransform(source_x=10, source_y=20, source_w=30, source_h=40, target_size=30)
    assert transform.to_box() == (10, 20, 40, 60)

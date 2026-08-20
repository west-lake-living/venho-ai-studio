from __future__ import annotations

from ..entities import CropTransform


def assert_crop_transform_round_trips(transform: CropTransform) -> None:
    """CropTransform must be invertible: box -> transform -> box must be exact.

    If this ever fails, compositing a restored crop back into the canvas will
    silently land pixels a few units off — very hard to notice by eye, very
    easy to fail a byte-exact golden-master comparison for the wrong reason.
    """
    if not transform.round_trips():
        raise ValueError(f"CropTransform does not round-trip: {transform!r}")

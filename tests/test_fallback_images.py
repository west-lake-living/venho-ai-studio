from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from publishing_gateway.fallback_images import (
    DEFAULT_FALLBACK_IMAGES,
    FALLBACK_IMAGES_BY_DNA_SUBJECT,
    fallback_image_url,
)

# The photos are served off the public website, which is a sibling repo, so
# the on-disk check can only run where that checkout exists (Harry's machine).
# It is skipped, never failed, in CI -- see
# test_every_pool_entry_is_under_the_website_images_root for the part that
# always runs.
WEBSITE_IMAGES_ROOT = Path(
    os.environ.get(
        "VENHO_WEBSITE_IMAGES_ROOT",
        Path(__file__).resolve().parents[3] / "Ven Ho Hotel" / "public" / "images",
    )
)

INSTAGRAM_MIN_RATIO, INSTAGRAM_MAX_RATIO = 0.80, 1.91


def _all_pool_entries() -> set[str]:
    entries = set(DEFAULT_FALLBACK_IMAGES)
    for pool in FALLBACK_IMAGES_BY_DNA_SUBJECT.values():
        entries |= set(pool)
    return entries


@pytest.mark.skipif(not WEBSITE_IMAGES_ROOT.is_dir(), reason="website repo not checked out here")
def test_every_pool_photo_exists_on_disk() -> None:
    """A typo here is a dead image URL, which fails the post Make-side after
    this codebase has already recorded GATEWAY_ACCEPTED -- the same class of
    silent, after-the-fact failure the aspect-ratio bug caused."""
    missing = [name for name in sorted(_all_pool_entries()) if not (WEBSITE_IMAGES_ROOT / name).exists()]
    assert not missing, f"fallback photos referenced but not present: {missing}"


@pytest.mark.skipif(not WEBSITE_IMAGES_ROOT.is_dir(), reason="website repo not checked out here")
def test_every_pool_photo_is_inside_instagrams_aspect_ratio_window() -> None:
    """Instagram rejects anything outside 0.80-1.91 with `(36003)`, inside
    Make, after dispatch. This is what kept 25 of the hotel's 41 photos out
    of the pools until they were padded into Social-pad/ (2026-09-07)."""
    offenders = []
    for name in sorted(_all_pool_entries()):
        path = WEBSITE_IMAGES_ROOT / name
        if not path.exists():
            continue
        with Image.open(path) as image:
            ratio = image.width / image.height
        if not INSTAGRAM_MIN_RATIO <= ratio <= INSTAGRAM_MAX_RATIO:
            offenders.append(f"{name} ({ratio:.2f})")
    assert not offenders, f"fallback photos Instagram would reject: {offenders}"


def test_no_subject_pool_is_a_single_photo_except_the_documented_thin_ones() -> None:
    """A one-entry pool is a guaranteed repeat on every post for that subject.
    `lobby`/`linh_an` are capped at 2 by how many common-area photos actually
    exist -- that needs a camera, not a code change -- but nothing else may
    silently shrink back to one.
    """
    thin = {name: pool for name, pool in FALLBACK_IMAGES_BY_DNA_SUBJECT.items() if len(set(pool)) < 2}
    assert not thin, f"subject pools that can only ever show one photo: {sorted(thin)}"


def test_lake_and_room_subjects_do_not_share_photos() -> None:
    """`westlake` pulled lake-view-6/-7 until 2026-09-07 -- both bedroom
    interiors -- so posts about the lake showed a bed. Keep the two apart."""
    lake = set(FALLBACK_IMAGES_BY_DNA_SUBJECT["westlake"]) | set(FALLBACK_IMAGES_BY_DNA_SUBJECT["outside"])
    rooms = set(FALLBACK_IMAGES_BY_DNA_SUBJECT["lake_view_room"]) | set(
        FALLBACK_IMAGES_BY_DNA_SUBJECT["deluxe_double"]
    )
    assert not (lake & rooms), f"outdoor subjects sharing room interiors: {sorted(lake & rooms)}"


def test_rotation_walks_the_whole_westlake_pool_over_a_season() -> None:
    """The point of widening the pools: a run of posts must not keep landing
    on the same handful of photos."""
    dates = [f"2026-{month:02d}-{day:02d}" for month in (9, 10, 11) for day in (1, 8, 15, 22)]
    seen = {fallback_image_url("westlake", rotation_key=d) for d in dates}
    assert len(seen) >= 6, f"only {len(seen)} distinct photos across 12 slots"

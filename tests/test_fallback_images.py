from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from publishing_gateway.fallback_images import (
    default_fallback_images,
    fallback_images_by_dna_subject,
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
    entries = set(default_fallback_images())
    for pool in fallback_images_by_dna_subject().values():
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
    thin = {name: pool for name, pool in fallback_images_by_dna_subject().items() if len(set(pool)) < 2}
    assert not thin, f"subject pools that can only ever show one photo: {sorted(thin)}"


def test_lake_and_room_subjects_do_not_share_photos() -> None:
    """`westlake` pulled lake-view-6/-7 until 2026-09-07 -- both bedroom
    interiors -- so posts about the lake showed a bed. Keep the two apart."""
    pools = fallback_images_by_dna_subject()
    lake = set(pools["westlake"]) | set(pools["outside"])
    rooms = set(pools["lake_view_room"]) | set(pools["deluxe_double"])
    assert not (lake & rooms), f"outdoor subjects sharing room interiors: {sorted(lake & rooms)}"


def test_rotation_walks_the_whole_westlake_pool_over_a_season() -> None:
    """The point of widening the pools: a run of posts must not keep landing
    on the same handful of photos."""
    dates = [f"2026-{month:02d}-{day:02d}" for month in (9, 10, 11) for day in (1, 8, 15, 22)]
    seen = {fallback_image_url("westlake", rotation_key=d) for d in dates}
    assert len(seen) >= 6, f"only {len(seen)} distinct photos across 12 slots"


@pytest.mark.parametrize("weekday_of_first_post", range(7))
def test_a_fixed_weekday_lane_still_reaches_every_photo(weekday_of_first_post: int) -> None:
    """Each cadence lane posts on ONE weekday. The old `week*4 + offset` index
    stepped such a lane by 4 every week, so it only ever showed
    pool_size/gcd(pool_size,4) photos -- 3 of 12 here, 1 of 2 for `lobby`,
    and adding photos did nothing. A weekly (7-day) step must now cover the
    whole pool."""
    from datetime import date, timedelta

    for subject, pool in fallback_images_by_dna_subject().items():
        start = date(2026, 9, 7) + timedelta(days=weekday_of_first_post)
        weekly_keys = [(start + timedelta(weeks=w)).isoformat() for w in range(len(set(pool)) * 2)]
        seen = {fallback_image_url(subject, rotation_key=k) for k in weekly_keys}
        assert len(seen) == len(set(pool)), (
            f"{subject}: a weekday-{weekday_of_first_post} lane reached "
            f"{len(seen)}/{len(set(pool))} photos"
        )

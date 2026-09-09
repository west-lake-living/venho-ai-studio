"""Public fallback photos for posts that reach Make.com without a generated image.

Why this exists (2026-08-06): Facebook Pages "Create a Post with Photos" and
Instagram "Create a photo post" both *require* a photo, and the Make scenario
fetches it with an "HTTP: Download a file" module whose `url` field is
mandatory. A growth publication with `image_public_url = None` therefore blew
up Make-side with `BundleValidationError: Missing value of required parameter
'url'` -- the whole dispatch failed, text and all. Growth currently generates
no images in most runs (Content Studio only emits a `visual_note`), and the
Drive upload is best-effort on top of that, so `None` is the common case, not
the edge case.

The images are real photographs of the hotel, served off the public website so
Make can fetch them without any auth (`Ven Ho Hotel/public/images/`). They must
be public URLs: Make runs in the cloud and cannot read anything on Harry's
machine -- which is why this pool is the *website* library and has nothing to
do with `venho-ai-studio/assets/raw/`, the separate reference set that gets fed
INTO gpt-image-2 and is never posted directly.

It started (2026-08-06) as the per-pillar set `venho-social-content-agent`
already used (`pillars.json` -> `ref_image`); it now spans the whole usable
website library (2026-09-07, see the pool comments below).

A fallback is a real hotel photo, so posting one is honest; it is still second
best to a generated image, hence `image_is_fallback` is carried on the content
payload so the dashboard/reviewer can see which posts got one.

Aspect ratio is a hard constraint, not a preference: Instagram rejects anything
outside 4:5 (0.80) to 1.91:1 with `(36003) The aspect ratio is not supported`,
and it does so *inside* Make, after this codebase has already recorded
GATEWAY_ACCEPTED. The first real IG dispatch died that way on a 659x1440 (0.46)
facade shot; it was padded to 1200x1440 (0.83) on cream #F7F4EF. Any photo added
here must be checked against that window -- including generated ones, since
gpt-image-2's portrait size is 1024x1536 (0.67) and would fail identically.
"""

from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path
import hashlib
import json

FALLBACK_IMAGE_BASE_URL = "https://venhohotel.com/images"

# --- The pool manifest -------------------------------------------------------
#
# Widened 2026-09-07 from 8 hand-typed filenames to 38, then (2026-09-09)
# switched from a hardcoded dict to this JSON manifest, built by
# `scripts/refresh_fallback_pool.py` scanning the real website photo library
# (`Ven Ho Hotel/public/images/`). That script is the source of truth for
# what's in the pool; run it after adding photos, then commit the manifest.
# This module never touches the filesystem beyond reading it -- it cannot
# scan the website repo itself, because `publishing_gateway` runs in
# venho-ai-studio's GitHub Actions, which never checks that (private) repo
# out.
#
# The original 2026-09-07 fix is still true and is why the manifest looks
# the way it does:
# 1. Adding a photo to public/images/ used to change nothing -- the dict was
#    the library as far as posting was concerned. Now the manifest is
#    regenerated from the actual folder contents.
# 2. Portrait photos (3:4 = 0.75) are just under Instagram's 0.80 aspect
#    ratio floor and get rejected in-scenario with `(36003)`. The refresh
#    script auto-pads them into Social-pad/ (1200x1440 on brand cream
#    #F7F4EF) instead of skipping them.
# 3. Subject mapping is still curated by hand inside the refresh script
#    (`FOLDER_TO_SUBJECT` / `FILE_OVERRIDES`), because a folder's contents
#    don't map 1:1 to a DNA subject (e.g. Lake-view/ holds both room-interior
#    shots and one lake-only shot).
_MANIFEST_PATH = Path(__file__).parent / "fallback_pool_manifest.json"

_PAD = "Social-pad"  # portrait originals re-framed to 0.83 on brand cream

# Last-resort safety net if the manifest is missing or fails to parse --
# fallback_image_url() must never return None, so this small hand-picked set
# stays embedded rather than depending on a file read succeeding.
DEFAULT_FALLBACK_IMAGES = (
    "Exterior/exterior-2.jpg",
    "Social-fallback/hotel-front-view.jpg",
    f"{_PAD}/Exterior/exterior-4.jpg",
    "Hero-lake/hero-lake.jpg",
    "Lake-sunset/lake-sunset-1.jpg",
    f"{_PAD}/Activity/activity-2.jpg",
)


@lru_cache(maxsize=1)
def _load_manifest() -> dict[str, object]:
    try:
        raw = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"default": list(DEFAULT_FALLBACK_IMAGES), "by_dna_subject": {}}
    if not raw.get("default"):
        raw["default"] = list(DEFAULT_FALLBACK_IMAGES)
    return raw


def default_fallback_images() -> tuple[str, ...]:
    """The safe-default pool, as actually loaded (manifest, or the embedded
    fallback if it's missing/corrupt). Exposed for tests and tooling that
    need the real pool, not just the last-resort constant above."""
    return tuple(_load_manifest().get("default") or DEFAULT_FALLBACK_IMAGES)


def fallback_images_by_dna_subject() -> dict[str, tuple[str, ...]]:
    """The per-subject pools, as actually loaded from the manifest."""
    return {subject: tuple(pool) for subject, pool in _load_manifest().get("by_dna_subject", {}).items()}


def _rotation_index(rotation_key: str | None, pool_size: int) -> int:
    """Deterministic pick within a pool, stable for a slot but varied over time.

    Same convention as agent_studio.growth.reference_asset_resolver._rotation_index:
    a calendar key advances by the raw ordinal day, anything else falls back
    to a stable hash.

    The raw ordinal matters. Each cadence lane posts on ONE fixed weekday, so
    the earlier `(week * 4 + cadence_offset)` scheme stepped a given lane's
    index by exactly 4 between its consecutive posts -- it could only ever
    reach `pool_size / gcd(pool_size, 4)` photos: 3 of 12 for the lake lanes,
    1 of 2 for `lobby`. Adding more photos to the pool changed nothing.
    Stepping by the ordinal day advances a fixed-weekday lane by 7 each week,
    and gcd(7, N) == 1 for every current pool, so the whole pool is used.
    """
    if pool_size <= 1 or not rotation_key:
        return 0
    try:
        base = date.fromisoformat(rotation_key).toordinal()
    except ValueError:
        digest = hashlib.sha256(rotation_key.encode("utf-8")).digest()
        base = int.from_bytes(digest[:4], "big")
    return base % pool_size


def fallback_image_url(dna_subject: str | None = None, *, rotation_key: str | None = None) -> str:
    """Public URL of the on-brand stand-in photo for `dna_subject`.

    Never returns None -- an unknown/missing subject falls back to the exterior
    shot, because the caller's whole purpose is to guarantee Make gets a `url`.
    """
    manifest = _load_manifest()
    by_subject = manifest.get("by_dna_subject", {})
    pool = by_subject.get(dna_subject or "") or manifest.get("default") or DEFAULT_FALLBACK_IMAGES
    filename = pool[_rotation_index(rotation_key, len(pool))]
    return f"{FALLBACK_IMAGE_BASE_URL}/{filename}"

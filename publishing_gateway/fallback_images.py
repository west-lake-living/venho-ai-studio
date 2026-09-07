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

from datetime import date, timedelta
import hashlib

FALLBACK_IMAGE_BASE_URL = "https://venhohotel.com/images"

# --- The pools -------------------------------------------------------------
#
# Widened 2026-09-07 from 8 filenames to 38. The old list was a hand-picked
# handful, so a fallback post could only ever show one of eight photos no
# matter how many the hotel actually had -- `Social-fallback/lobby.jpg` alone
# accounted for 16 of the 64 fallback rows in the registry, and the `lobby`
# and `linh_an` pools held exactly ONE entry each, i.e. a guaranteed repeat
# every single time. Harry saw it as "the posts keep using the same images".
#
# Three things were wrong and all three are fixed here:
#
# 1. The pool was not the photo library. Adding a photo to public/images/
#    changed nothing, because this list is the library as far as posting is
#    concerned. It now covers everything usable there.
# 2. Two thirds of the library was locked out by aspect ratio. 25 of 41
#    photos are 3:4 portrait (0.75), just under Instagram's 0.80 floor, so
#    they would have been rejected in-scenario with `(36003)`. They are
#    served from Social-pad/, padded to 1200x1440 (0.83) on brand cream
#    #F7F4EF -- the same treatment the facade shot already got in 2026-08-06.
#    Originals under public/images/ are untouched; the website still uses them.
# 3. Subjects were mis-mapped. `westlake` was pulling lake-view-6/-7, which
#    are BEDROOM interiors -- posts about the lake were showing a bed -- and
#    `deluxe_double` contained no Deluxe room photo at all, only lake shots.
#    Meanwhile the seven Activity/ frames (bicycle at the lakeshore railing,
#    Nguyen Dinh Thi under the flame trees) -- the most on-DNA West Lake
#    material in the library -- had never been used once.
#
# Adding a photo here: check the 0.80-1.91 window first (see the module
# docstring); if it is portrait, pad it into Social-pad/ rather than adding
# the raw file.

_PAD = "Social-pad"  # portrait originals re-framed to 0.83 on brand cream

# Brand/exterior shot: the safe default for any subject not mapped below.
DEFAULT_FALLBACK_IMAGES = (
    "Exterior/exterior-2.jpg",
    "Social-fallback/hotel-front-view.jpg",
    f"{_PAD}/Exterior/exterior-4.jpg",
    "Hero-lake/hero-lake.jpg",
    "Lake-sunset/lake-sunset-1.jpg",
    f"{_PAD}/Activity/activity-2.jpg",
)

# Keyed by DNA subject (config/projects/venho_hotel/content/content_pillars.yaml
# -> dna_subject), not by pillar id: the subject *is* what the photo shows, and
# it survives pillars being renamed or added.
FALLBACK_IMAGES_BY_DNA_SUBJECT = {
    # The lake itself and the lakeside street -- never a room interior.
    "westlake": (
        "Hero-lake/hero-lake.jpg",
        "Lake-sunset/lake-sunset-1.jpg",
        f"{_PAD}/Lake-sunset/lake-sunset-2.jpg",
        f"{_PAD}/Activity/activity-1.jpg",
        f"{_PAD}/Activity/activity-2.jpg",
        f"{_PAD}/Activity/activity-3.jpg",
        f"{_PAD}/Activity/activity-4.jpg",
        f"{_PAD}/Activity/activity-6.jpg",
        f"{_PAD}/Activity/activity-7.jpg",
        f"{_PAD}/Lake-night/lake-night.jpg",
        "Lake-view/lake-view-1.jpg",
    ),
    # Street level / balcony / rooftop -- the hotel's surroundings.
    "outside": (
        f"{_PAD}/Activity/activity-5.jpg",
        f"{_PAD}/Activity/activity-4.jpg",
        f"{_PAD}/Activity/activity-7.jpg",
        "Lake-view/lake-view-1.jpg",
        "Exterior/exterior-2.jpg",
        f"{_PAD}/Activity/activity-3.jpg",
        f"{_PAD}/Activity/activity-1.jpg",
        "Lake-sunset/lake-sunset-1.jpg",
    ),
    # Rooms whose window actually looks over the lake.
    "lake_view_room": (
        "Lake-view/lake-view-6.JPG",
        "Lake-view/lake-view-7.JPG",
        f"{_PAD}/Lake-view/lake-view-2.jpg",
        f"{_PAD}/Lake-view/lake-view-3.jpg",
        f"{_PAD}/Lake-view/lake-view-4.jpg",
        f"{_PAD}/Lake-view/lake-view-8.jpg",
        f"{_PAD}/Lake-view/lake-view-9.jpg",
        "Social-fallback/lake-view-room.jpg",
        f"{_PAD}/Lake-view/lake-view-5.jpg",
    ),
    # Deluxe / standard room interiors (previously: no room photo at all).
    "deluxe_double": (
        f"{_PAD}/Deluxe-double/deluxe-double-1.jpg",
        f"{_PAD}/Deluxe-double/deluxe-double-3.jpg",
        "Standard-triple/standard-triple-1.jpg",
        "Standard-triple/standard-triple-3.JPG",
        f"{_PAD}/Deluxe-double/deluxe-double-2.jpg",
        "Standard-triple/standard-triple-2.jpg",
        f"{_PAD}/Standard-triple/standard-triple-4.jpg",
        "Bathroom/bathroom-1.JPG",
        "Bathroom/bathroom-3.jpg",
    ),
    "facade": (
        "Exterior/exterior-2.jpg",
        "Social-fallback/hotel-front-view.jpg",
        f"{_PAD}/Exterior/exterior-4.jpg",
        f"{_PAD}/Exterior/exterior-3.jpg",
        f"{_PAD}/Exterior/exterior-6.jpg",
        f"{_PAD}/Exterior/exterior-5.jpg",
    ),
    # Only two real interior-common-area photos exist. Genuinely thin --
    # this is the one pool that needs new photography, not a code change.
    "lobby": (
        "Social-fallback/lobby.jpg",
        "Social-fallback/reception.jpg",
    ),
    # Linh An is an AI character with no real photograph; the reception and
    # lobby frames stand in for a "someone is here" post.
    "linh_an": (
        "Social-fallback/reception.jpg",
        "Social-fallback/lobby.jpg",
    ),
}


def _rotation_index(rotation_key: str | None, pool_size: int) -> int:
    if pool_size <= 1 or not rotation_key:
        return 0
    try:
        slot_date = date.fromisoformat(rotation_key)
    except ValueError:
        digest = hashlib.sha256(rotation_key.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % pool_size

    monday = slot_date - timedelta(days=slot_date.weekday())
    cadence_offset = {0: 0, 2: 1, 4: 2, 5: 3}.get(slot_date.weekday(), slot_date.weekday())
    return ((monday.toordinal() // 7) * 4 + cadence_offset) % pool_size


def fallback_image_url(dna_subject: str | None = None, *, rotation_key: str | None = None) -> str:
    """Public URL of the on-brand stand-in photo for `dna_subject`.

    Never returns None -- an unknown/missing subject falls back to the exterior
    shot, because the caller's whole purpose is to guarantee Make gets a `url`.
    """
    pool = FALLBACK_IMAGES_BY_DNA_SUBJECT.get(dna_subject or "", DEFAULT_FALLBACK_IMAGES)
    filename = pool[_rotation_index(rotation_key, len(pool))]
    return f"{FALLBACK_IMAGE_BASE_URL}/{filename}"

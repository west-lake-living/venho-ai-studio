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

The images are the same real-hotel reference set `venho-social-content-agent`
already uses per pillar (`pillars.json` -> `ref_image`), re-encoded and served
off the public website so Make can fetch them without any auth:
`Ven Ho Hotel/public/images/Social-fallback/`. Reusing that set (Harry's call)
keeps the fallback on-brand -- these are photos of the actual hotel, not stock.

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

FALLBACK_IMAGE_BASE_URL = "https://venhohotel.com/images/Social-fallback"

# Brand/exterior shot: the safe default for any subject not mapped below.
DEFAULT_FALLBACK_IMAGE = "hotel-front-view.jpg"

# Keyed by DNA subject (config/projects/venho_hotel/content/content_pillars.yaml
# -> dna_subject), not by pillar id: the subject *is* what the photo shows, and
# it survives pillars being renamed or added.
FALLBACK_IMAGE_BY_DNA_SUBJECT = {
    "westlake": "lake-view-room.jpg",
    "lake_view_room": "lake-view-room.jpg",
    "deluxe_double": "lake-view-room.jpg",
    "lobby": "lobby.jpg",
    "linh_an": "reception.jpg",
    "facade": "hotel-front-view.jpg",
    "outside": "hotel-front-view.jpg",
}


def fallback_image_url(dna_subject: str | None = None) -> str:
    """Public URL of the on-brand stand-in photo for `dna_subject`.

    Never returns None -- an unknown/missing subject falls back to the exterior
    shot, because the caller's whole purpose is to guarantee Make gets a `url`.
    """
    filename = FALLBACK_IMAGE_BY_DNA_SUBJECT.get(dna_subject or "", DEFAULT_FALLBACK_IMAGE)
    return f"{FALLBACK_IMAGE_BASE_URL}/{filename}"

"""Rebuild the fallback-photo manifest that `publishing_gateway.fallback_images`
reads at runtime, by scanning the real website photo library.

Why this exists (2026-09-09): before this script, adding a photo to
`Ven Ho Hotel/public/images/` did nothing -- `fallback_images.py` posted from a
Python dict of hand-typed filenames, so a new photo needed a manual code edit
to ever be used. This script closes that gap for the common case: drop a
`.jpg` into the right subject folder, run this script, commit both repos.

It cannot be fully automatic end-to-end because `publishing_gateway` runs in
venho-ai-studio's GitHub Actions, which does not check out the website repo
(private, separate repo) -- so the pool is baked into a manifest JSON checked
into THIS repo instead of scanned live at publish time. Run this script
locally after adding photos; `fallback_image_url()` just reads the manifest.

What it does:
1. Walks `Ven Ho Hotel/public/images/<Folder>/*.jpg` (skips `Social-pad/`,
   that is the *output* of step 2, not an input).
2. Maps each folder to a DNA subject via FOLDER_TO_SUBJECT below. A handful
   of individual files don't follow their folder's default subject (e.g.
   Lake-view/lake-view-1.jpg is a lake shot, not a room-interior shot even
   though it lives next to the room photos) -- those go in FILE_OVERRIDES.
3. Checks Instagram's aspect ratio window (0.80-1.91). Anything narrower is
   auto-padded to 1200x1440 on brand cream #F7F4EF and saved under
   `Social-pad/<Folder>/`, mirroring the treatment already applied to the
   first 23 photos on 2026-09-08. Anything wider is skipped with a warning
   (rare -- no wide-panorama source photos exist today).
4. Writes `publishing_gateway/fallback_pool_manifest.json`, sorted by
   relative path per subject so the existing date-based rotation
   (`_rotation_index`) stays deterministic.

Usage:
    python scripts/refresh_fallback_pool.py
    python scripts/refresh_fallback_pool.py --website-root "/path/to/Ven Ho Hotel"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

MIN_RATIO = 0.80
MAX_RATIO = 1.91
PAD_SIZE = (1200, 1440)
PAD_COLOR = "#F7F4EF"
PAD_FOLDER = "Social-pad"

# Folder -> default DNA subject. Keep in sync with
# config/projects/venho_hotel/content/content_pillars.yaml's dna_subject list.
FOLDER_TO_SUBJECT = {
    "Hero-lake": "westlake",
    "Lake-sunset": "westlake",
    "Lake-night": "westlake",
    "Activity": "westlake",
    "Lake-view": "lake_view_room",  # see FILE_OVERRIDES for the exceptions
    "Deluxe-double": "deluxe_double",
    "Standard-triple": "deluxe_double",
    "Bathroom": "deluxe_double",
    "Exterior": "facade",
    "Lobby": "lobby",  # real common-area photos, added 2026-09-09
}

# Individual files whose subject differs from their folder's default --
# curated by hand, checked when this script runs so a re-run never loses them.
FILE_OVERRIDES = {
    "Lake-view/lake-view-1.jpg": "westlake",
}

# Photos that exist in the folder but should never be posted -- bad
# composition, not a fixable aspect-ratio issue. Padding still "fixes" the
# ratio for these, so aspect ratio alone can't catch them; they were dropped
# by hand from the original 2026-09-08 padding batch and stay excluded here
# so a re-run doesn't silently bring them back.
EXCLUDE_FILES = {
    "Exterior/exterior-1.jpg",  # 0.46 ratio -- padding would be mostly cream
    "Bathroom/bathroom-4.jpg",  # door-handle close-up, not a room shot
}

# Seeded manifest entries. `lobby` also has a real scanned folder now
# (FOLDER_TO_SUBJECT), so these two hand-named files are just added to that
# pool. `linh_an` has no real photo of its own and stays an alias of the
# common-area shots.
MANUAL_POOLS = {
    "lobby": ["Social-fallback/lobby.jpg", "Social-fallback/reception.jpg"],
    "linh_an": ["Social-fallback/reception.jpg", "Social-fallback/lobby.jpg"],
}

DEFAULT_POOL = [
    "Exterior/exterior-2.jpg",
    "Social-fallback/hotel-front-view.jpg",
    f"{PAD_FOLDER}/Exterior/exterior-4.jpg",
    "Hero-lake/hero-lake.jpg",
    "Lake-sunset/lake-sunset-1.jpg",
    f"{PAD_FOLDER}/Activity/activity-2.jpg",
]

IMAGE_SUFFIXES = {".jpg", ".jpeg"}

# Make.com fetches the fallback photo on every post and Facebook/Instagram
# reject an upload over ~8 MB. Straight-from-the-phone shots are 5-7 MB, so
# anything past this gets a web-sized copy written next to the pads.
MAX_BYTES = 2_000_000
WEB_MAX_EDGE = 2048


def _pad_into_social_pad(src: Path, images_root: Path, rel_folder: str) -> str:
    """Pad a portrait photo onto brand cream, reusing an existing pad if present."""
    dest_dir = images_root / PAD_FOLDER / rel_folder
    dest = dest_dir / src.name
    rel_dest = f"{PAD_FOLDER}/{rel_folder}/{src.name}"
    if dest.exists():
        return rel_dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        # Phone photos carry their orientation in EXIF, not the pixels --
        # without this a portrait shot pads sideways.
        im = ImageOps.exif_transpose(im).convert("RGB")
        canvas = Image.new("RGB", PAD_SIZE, PAD_COLOR)
        scale = min(PAD_SIZE[0] / im.width, PAD_SIZE[1] / im.height)
        new_size = (round(im.width * scale), round(im.height * scale))
        resized = im.resize(new_size, Image.LANCZOS)
        offset = ((PAD_SIZE[0] - new_size[0]) // 2, (PAD_SIZE[1] - new_size[1]) // 2)
        canvas.paste(resized, offset)
        canvas.save(dest, "JPEG", quality=92)
    return rel_dest


def _websize_into_social_pad(src: Path, images_root: Path, rel_folder: str) -> str:
    """Shrink an oversized in-ratio photo, keeping its aspect (no cream bars)."""
    dest_dir = images_root / PAD_FOLDER / rel_folder
    dest = dest_dir / src.name
    rel_dest = f"{PAD_FOLDER}/{rel_folder}/{src.name}"
    if dest.exists():
        return rel_dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        scale = min(1.0, WEB_MAX_EDGE / max(im.width, im.height))
        if scale < 1.0:
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        im.save(dest, "JPEG", quality=88)
    return rel_dest


def build_manifest(website_root: Path) -> dict[str, list[str]]:
    images_root = website_root / "public" / "images"
    if not images_root.is_dir():
        raise SystemExit(f"Not found: {images_root}")

    pools: dict[str, list[str]] = {subject: list(files) for subject, files in MANUAL_POOLS.items()}
    warnings: list[str] = []

    for folder, default_subject in FOLDER_TO_SUBJECT.items():
        folder_path = images_root / folder
        if not folder_path.is_dir():
            continue
        for src in sorted(folder_path.iterdir()):
            if not src.is_file() or src.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            rel = f"{folder}/{src.name}"
            if rel in EXCLUDE_FILES:
                continue
            subject = FILE_OVERRIDES.get(rel, default_subject)

            with Image.open(src) as im:
                # Respect EXIF orientation so a landscape phone photo stored
                # with rotated pixels is not mistaken for a portrait.
                oriented = ImageOps.exif_transpose(im)
                ratio = oriented.width / oriented.height

            if ratio < MIN_RATIO:
                rel_out = _pad_into_social_pad(src, images_root, folder)
            elif ratio > MAX_RATIO:
                warnings.append(f"skipped (ratio {ratio:.2f} > {MAX_RATIO}): {rel}")
                continue
            elif src.stat().st_size > MAX_BYTES:
                rel_out = _websize_into_social_pad(src, images_root, folder)
            else:
                rel_out = rel

            pools.setdefault(subject, [])
            if rel_out not in pools[subject]:
                pools[subject].append(rel_out)

    # "outside" (street level / balcony / rooftop) has no folder of its own --
    # its old hand-picked pool was a subset of the same lakeside/exterior
    # photos "westlake" already covers, so alias it rather than leaving it
    # empty (an empty pool would silently fall through to DEFAULT_POOL).
    if "westlake" in pools:
        pools.setdefault("outside", list(pools["westlake"]))

    for subject in pools:
        pools[subject] = sorted(pools[subject])

    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    return pools


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3] / "Ven Ho Hotel"
    parser.add_argument("--website-root", type=Path, default=default_root)
    args = parser.parse_args()

    pools = build_manifest(args.website_root)
    manifest = {"default": DEFAULT_POOL, "by_dna_subject": pools}

    out_path = Path(__file__).resolve().parents[1] / "publishing_gateway" / "fallback_pool_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for subject, files in sorted(pools.items()):
        print(f"{subject}: {len(files)} photos")
    print(f"\nWrote {out_path}")
    print("Commit this file in venho-ai-studio, and any new files under")
    print(f"{args.website_root}/public/images/{PAD_FOLDER}/ in Ven Ho Hotel.")


if __name__ == "__main__":
    main()

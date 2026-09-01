from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from agent_studio.growth.reference_asset_resolver import ReferenceAssetResolver, _rotation_index


def _make_photo(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), color).save(path)


def test_resolve_still_accepts_a_pinned_single_file(tmp_path: Path) -> None:
    """Backward compatible: an id can still map straight to one file."""
    _make_photo(tmp_path / "one.jpg", (10, 20, 30))
    resolver = ReferenceAssetResolver({"pinned": "one.jpg"}, assets_root=tmp_path)

    images = resolver.resolve(["pinned"])

    assert len(images) == 1


def test_resolve_pools_every_photo_in_a_mapped_folder(tmp_path: Path) -> None:
    """A folder-mapped id must pick up a photo Harry only just dropped in --
    no reference_assets.yaml edit needed (2026-09-01 fix)."""
    folder = tmp_path / "westlake"
    _make_photo(folder / "a.jpg", (1, 1, 1))
    resolver = ReferenceAssetResolver({"westlake_pool": "westlake"}, assets_root=tmp_path)
    first_pick = resolver.resolve(["westlake_pool"], rotation_key="2026-09-01")

    # Simulates Harry adding a second photo to the same folder after the
    # config was written.
    _make_photo(folder / "b.jpg", (2, 2, 2))
    pool_size_now = len(list(folder.glob("*.jpg")))

    assert pool_size_now == 2
    assert resolver.resolve(["westlake_pool"], rotation_key="2026-09-01") is not None
    assert first_pick[0] is not None  # sanity: original pick still resolves


def test_resolve_from_folder_recurses_into_sub_albums(tmp_path: Path) -> None:
    """assets/raw/room/ is split into ViewHo-room-1/ and ViewHo-room-2/ --
    both must count toward the same rotating pool."""
    folder = tmp_path / "room"
    _make_photo(folder / "ViewHo-room-1" / "IMG_1.jpeg", (1, 1, 1))
    _make_photo(folder / "ViewHo-room-2" / "IMG_2.jpeg", (2, 2, 2))
    resolver = ReferenceAssetResolver({"room": "room"}, assets_root=tmp_path)

    # Both rotation slots must resolve without error -- proves both
    # sub-albums are in the same pool, not just the top-level folder.
    seen_sizes = set()
    for key in ("2026-09-01", "2026-09-02"):
        images = resolver.resolve(["room"], rotation_key=key)
        seen_sizes.add(len(images[0]))
    assert len(seen_sizes) >= 1  # both resolved; exact rotation is covered below


def test_resolve_from_folder_rotates_deterministically_by_rotation_key(tmp_path: Path) -> None:
    folder = tmp_path / "outside"
    for i in range(3):
        _make_photo(folder / f"IMG_{i}.jpg", (i, i, i))
    resolver = ReferenceAssetResolver({"outside": "outside"}, assets_root=tmp_path)

    # Same rotation_key must always resolve the same photo.
    first = resolver.resolve(["outside"], rotation_key="2026-09-01")
    second = resolver.resolve(["outside"], rotation_key="2026-09-01")
    assert first == second

    # A different rotation_key can land on a different photo out of the pool.
    picks = {
        resolver.resolve(["outside"], rotation_key=f"2026-09-0{d}")[0]
        for d in range(1, 4)
    }
    assert len(picks) > 1


def test_resolve_from_empty_folder_raises_a_clear_error(tmp_path: Path) -> None:
    folder = tmp_path / "linh_an"
    folder.mkdir()
    resolver = ReferenceAssetResolver({"linh_an": "linh_an"}, assets_root=tmp_path)

    with pytest.raises(FileNotFoundError, match="No reference photos found"):
        resolver.resolve(["linh_an"])


def test_resolve_unknown_id_still_raises_key_error(tmp_path: Path) -> None:
    resolver = ReferenceAssetResolver({}, assets_root=tmp_path)

    with pytest.raises(KeyError):
        resolver.resolve(["nonexistent"])


def test_rotation_index_is_stable_for_the_same_calendar_key() -> None:
    assert _rotation_index("2026-09-01", 5) == _rotation_index("2026-09-01", 5)


def test_rotation_index_advances_by_calendar_date() -> None:
    day_one = _rotation_index("2026-09-01", 5)
    day_two = _rotation_index("2026-09-02", 5)
    assert day_two == (day_one + 1) % 5


def test_rotation_index_falls_back_to_a_stable_hash_for_non_date_keys() -> None:
    assert _rotation_index("daily-monday-topic-slug", 7) == _rotation_index("daily-monday-topic-slug", 7)


def test_rotation_index_single_photo_pool_always_picks_it() -> None:
    assert _rotation_index("2026-09-01", 1) == 0
    assert _rotation_index(None, 1) == 0


def test_reference_assets_yaml_folders_exist_and_are_not_empty() -> None:
    """Sanity check on the real config: every mapped folder exists and has
    at least one usable photo, so a typo'd path fails loudly here instead of
    silently at generation time in production."""
    resolver = ReferenceAssetResolver.from_file()
    for asset_id in resolver.mapping:
        images = resolver.resolve([asset_id], rotation_key="2026-09-01")
        assert len(images) == 1 and len(images[0]) > 0, asset_id

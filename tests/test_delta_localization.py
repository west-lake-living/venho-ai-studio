import numpy as np
from PIL import Image

from image_studio_runtime.action_composite.delta_localization import (
    diagnostic_zone_masks,
    geometry_drift,
    region_delta_metrics,
    replace_crop_regions,
    resize_restored_for_analysis,
    rgb_delta,
)
from image_studio_runtime.action_composite.models import BoundingBox


def test_delta_computation_and_metrics_are_deterministic():
    original = Image.new("RGB", (4, 4), (10, 20, 30))
    restored = Image.new("RGB", (4, 4), (20, 20, 30))
    absolute, normalized = rgb_delta(original, restored)
    assert absolute.shape == (4, 4, 3)
    assert int(absolute[..., 0].mean()) == 10
    assert int(normalized.mean()) == 10
    metrics = region_delta_metrics(absolute, {"all": np.ones((4, 4), dtype=bool)})
    assert metrics["all"].mean_absolute_rgb_delta == 10 / 3
    assert metrics["all"].changed_pixel_percentage == 100.0


def test_zone_coordinates_map_full_face_into_crop_and_partition_pixels():
    crop_box = BoundingBox(left=100, top=50, right=300, bottom=250)
    masks = diagnostic_zone_masks(crop_size=(200, 200), face_bbox_full_frame=(150, 90, 250, 190), crop_box=crop_box)
    assert masks["forehead_upper_head"][40:66, 50:150].all()
    assert masks["surrounding_context"][0, 0]
    combined = np.zeros((200, 200), dtype=np.int8)
    for mask in masks.values():
        combined += mask.astype(np.int8)
    assert combined.min() == combined.max() == 1


def test_replacement_only_modifies_declared_pixels_and_base_is_immutable():
    base = np.zeros((8, 8, 3), dtype=np.uint8)
    original = base.copy()
    restored = np.full((4, 4, 3), 255, dtype=np.uint8)
    crop_box = BoundingBox(left=2, top=2, right=6, bottom=6)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1:3, 1:3] = True
    output = replace_crop_regions(base, restored, crop_box, {"suspect": mask}, ["suspect"])
    assert np.array_equal(base, original)
    assert output[3:5, 3:5].min() == 255
    assert output[2, 2].max() == 0
    assert output[:2].max() == 0


def test_reverse_experiment_restores_original_pixels_in_declared_region():
    base = np.zeros((8, 8, 3), dtype=np.uint8)
    restored = np.full((4, 4, 3), 255, dtype=np.uint8)
    crop_box = BoundingBox(left=2, top=2, right=6, bottom=6)
    mask = np.zeros((4, 4), dtype=bool)
    mask[1:3, 1:3] = True
    failed = replace_crop_regions(base, restored, crop_box, {"suspect": mask}, ["suspect"])
    recovered = failed.copy()
    recovered_crop = recovered[2:6, 2:6]
    recovered_crop[mask] = base[2:6, 2:6][mask]
    assert recovered[3:5, 3:5].max() == 0


def test_analysis_resize_has_requested_dimensions_without_mutating_source():
    raw = Image.new("RGB", (3, 2), "red")
    result = resize_restored_for_analysis(raw, (6, 4))
    assert raw.size == (3, 2)
    assert result.size == (6, 4)


def test_geometry_drift_reports_measurements_without_thresholds():
    result = geometry_drift((10, 20, 30, 60), (11, 22, 31, 62))
    assert result["bbox_center_delta_px"] == [1.0, 2.0]
    assert result["bbox_width_ratio"] == 1.0
    assert result["bbox_height_ratio"] == 1.0
    assert result["yaw_delta"] is None


def test_geometry_drift_preserves_yaw_pitch_roll_mapping():
    result = geometry_drift(
        (10, 20, 30, 60),
        (11, 22, 31, 62),
        reference_angles=(10.0, 20.0, 30.0),
        observed_angles=(7.0, 26.0, 29.5),
        reference_face_scale=0.25,
        observed_face_scale=0.25,
    )
    assert result["yaw_delta"] == -3.0
    assert result["pitch_delta"] == 6.0
    assert result["roll_delta"] == -0.5
    assert result["face_scale_delta"] == 0.0

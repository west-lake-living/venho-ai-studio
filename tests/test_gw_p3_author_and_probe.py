import pytest

from scripts.windows.gw_p3_author_and_probe import ProbeError, build_graph, validate_graph
from scripts.windows.gw_p3_author_and_probe import geometry_plan


CLASSES = {
    "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": ["STRING"]}}},
    "LoadImage": {"input": {"required": {"image": ["STRING"]}}},
    "LoadImageMask": {"input": {"required": {"image": ["STRING"], "channel": ["STRING"]}}},
    "ImagePadForOutpaint": {"input": {"required": {
        "image": ["IMAGE"], "left": ["INT"], "top": ["INT"], "right": ["INT"],
        "bottom": ["INT"], "feathering": ["INT"]}}},
    "ImageCrop": {"input": {"required": {
        "image": ["IMAGE"], "width": ["INT"], "height": ["INT"], "x": ["INT"], "y": ["INT"]}}},
    "MaskToImage": {"input": {"required": {"mask": ["MASK"]}}},
    "ImageToMask": {"input": {"required": {"image": ["IMAGE"], "channel": ["STRING"]}}},
    "VAEEncode": {"input": {"required": {"pixels": ["IMAGE"], "vae": ["VAE"]}}},
    "VAEDecode": {"input": {"required": {"samples": ["LATENT"], "vae": ["VAE"]}}},
    "SetLatentNoiseMask": {"input": {"required": {"samples": ["LATENT"], "mask": ["MASK"]}}},
    "CLIPTextEncode": {"input": {"required": {"clip": ["CLIP"], "text": ["STRING"]}}},
    "KSampler": {"input": {"required": {
        "model": ["MODEL"], "positive": ["CONDITIONING"], "negative": ["CONDITIONING"],
        "latent_image": ["LATENT"], "seed": ["INT"], "steps": ["INT"], "cfg": ["FLOAT"],
        "sampler_name": [["euler"]], "scheduler": [["normal"]], "denoise": ["FLOAT"]}}},
    "SaveImage": {"input": {"required": {"images": ["IMAGE"], "filename_prefix": ["STRING"]}}},
    "IPAdapterInsightFaceLoader": {"input": {"required": {
        "provider": [["CPU", "CUDA"]], "model_name": [["buffalo_l", "antelopev2"]]}}},
    "IPAdapterUnifiedLoaderFaceID": {"input": {"required": {
        "model": ["MODEL"], "preset": [["FACEID", "FACEID PLUS V2"]],
        "lora_strength": ["FLOAT"], "provider": [["CPU", "CUDA"]]},
        "optional": {"ipadapter": ["IPADAPTER"]}}},
    "IPAdapterFaceID": {"input": {"required": {
        "model": ["MODEL"], "ipadapter": ["IPADAPTER"], "image": ["IMAGE"],
        "weight": ["FLOAT"], "weight_faceidv2": ["FLOAT"], "weight_type": [["linear"]],
        "combine_embeds": [["concat"]], "start_at": ["FLOAT"], "end_at": ["FLOAT"],
        "embeds_scaling": [["V only"]]}, "optional": {"insightface": ["INSIGHTFACE"]}}},
}


def test_exact_live_faceid_schema_is_bound_without_lora_path():
    graph, lineage = build_graph(CLASSES, "crop.png", "mask.png", "a2.png", 123456, 0.35,
                                 crop_size=(687, 659))

    assert lineage == "runtime_schema_derived_sd15_faceid_v2_exact_geometry"
    unified = graph["10"]["inputs"]
    assert unified == {
        "model": ["1", 0], "preset": "FACEID PLUS V2",
        "lora_strength": 0.6, "provider": "CUDA",
    }
    assert not {"lora", "lora_name", "lora_file", "lora_path"}.intersection(unified)

    insight = graph["9"]["inputs"]
    assert insight == {"provider": "CUDA", "model_name": "buffalo_l"}

    adapter = graph["11"]["inputs"]
    assert adapter["model"] == ["10", 0]
    assert adapter["ipadapter"] == ["10", 1]
    assert adapter["image"] == ["3", 0]
    assert adapter["insightface"] == ["9", 0]
    assert adapter["weight_faceidv2"] == 1.0
    assert adapter["combine_embeds"] == "concat"
    assert graph["16"]["inputs"] == {
        "image": ["2", 0], "left": 0, "top": 0, "right": 1, "bottom": 5, "feathering": 0,
    }
    assert graph["17"]["inputs"]["image"] == ["15", 0]
    assert graph["18"]["inputs"] == {"image": ["17", 0], "channel": "red"}
    assert graph["5"]["inputs"]["pixels"] == ["16", 0]
    assert graph["6"]["inputs"]["mask"] == ["18", 0]
    assert graph["19"]["inputs"] == {"image": ["13", 0], "width": 687, "height": 659, "x": 0, "y": 0}
    validate_graph(graph, CLASSES)


def test_geometry_plan_is_right_bottom_only_and_multiple_of_eight():
    assert geometry_plan(687, 659) == {
        "original_width": 687, "original_height": 659,
        "pad_left": 0, "pad_top": 0, "pad_right": 1, "pad_bottom": 5,
        "padded_width": 688, "padded_height": 664, "multiple": 8,
    }


def test_graph_requires_original_geometry():
    with pytest.raises(ProbeError, match="original crop dimensions"):
        build_graph(CLASSES, "crop.png", "mask.png", "a2.png", 1, 0.35)


def test_graph_fails_closed_when_exact_geometry_node_schema_is_unavailable():
    changed = {name: {
        "input": {section: dict(values) for section, values in definition["input"].items()}
    } for name, definition in CLASSES.items()}
    del changed["ImageCrop"]
    with pytest.raises(ProbeError, match="ImageCrop"):
        build_graph(changed, "crop.png", "mask.png", "a2.png", 1, 0.35,
                    crop_size=(687, 659))


@pytest.mark.parametrize("class_name,input_name", [
    ("IPAdapterUnifiedLoaderFaceID", "preset"),
    ("IPAdapterInsightFaceLoader", "model_name"),
    ("IPAdapterFaceID", "weight_faceidv2"),
])
def test_required_live_schema_change_fails_closed(class_name, input_name):
    changed = {name: {"input": {
        section: dict(values)
        for section, values in definition["input"].items()
    }} for name, definition in CLASSES.items()}
    for section in ("required", "optional"):
        changed[class_name]["input"].get(section, {}).pop(input_name, None)

    with pytest.raises(ProbeError):
        build_graph(changed, "crop.png", "mask.png", "a2.png", 1, 0.35,
                    crop_size=(687, 659))

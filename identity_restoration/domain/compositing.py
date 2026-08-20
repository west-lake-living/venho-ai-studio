from __future__ import annotations

from io import BytesIO

from PIL import Image

from .entities import CropTransform, RestoredCrop

# Extract, don't recreate (patch v2.1 §2.2): this reproduces exactly the
# paste-through-mask compositing that image_studio_runtime/action_composite's
# ComfyUIIdentityRestorer.restore() already performs when a crop/crop_box is
# supplied (providers.py lines ~102-109), and that ActionCompositePipeline.run()
# performs for the whole-canvas case (`Image.composite(restored, base, mask)`).
# It is renamed and given a Port-shaped signature; the pixel math is identical,
# which is what keeps the golden-master byte-exact.


def composite_crop_into_canvas(*, base_canvas_png: bytes, restored: RestoredCrop,
                                transform: CropTransform, editable_mask_png: bytes) -> bytes:
    """Paste ``restored`` back into ``base_canvas_png`` at ``transform``'s box.

    Only the region covered by ``editable_mask_png`` (already sized to the full
    canvas) may change; everything else is byte-identical by construction
    because paste() never touches pixels outside the mask.
    """
    base = Image.open(BytesIO(base_canvas_png)).convert("RGBA")
    patch = Image.open(BytesIO(restored.png_bytes)).convert("RGBA")
    mask = Image.open(BytesIO(editable_mask_png)).convert("L")
    left, top, right, bottom = transform.to_box()
    expected = (right - left, bottom - top)
    if patch.size != expected:
        raise ValueError(f"restored crop is {patch.size}, expected {expected} from crop transform")
    crop_mask = mask.crop((left, top, right, bottom))
    output = base.copy()
    output.paste(patch, (left, top), crop_mask)
    buffer = BytesIO()
    output.save(buffer, format="PNG")
    return buffer.getvalue()

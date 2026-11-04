"""Phone photos keep rotation in EXIF; to_upload_jpeg must bake it into pixels
(26/10/2026 upload of Phu Tay Ho was published sideways on 04/11)."""
from PIL import Image

from growth_orchestrator.application.image_options import to_upload_jpeg


def test_exif_rotated_photo_is_uploaded_upright(tmp_path):
    source = tmp_path / "phone.jpg"
    # Sensor stores landscape 400x300; EXIF 6 = display rotated 90deg CW -> portrait.
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (400, 300), "red").save(source, format="JPEG", exif=exif.tobytes())

    out = to_upload_jpeg(source)

    with Image.open(out) as image:
        assert image.size == (300, 400)
        assert image.getexif().get(274) in (None, 1)


def test_photo_without_exif_is_unchanged_in_shape(tmp_path):
    source = tmp_path / "plain.jpg"
    Image.new("RGB", (400, 300), "blue").save(source, format="JPEG")

    with Image.open(to_upload_jpeg(source)) as image:
        assert image.size == (400, 300)

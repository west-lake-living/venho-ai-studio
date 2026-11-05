from __future__ import annotations

from io import BytesIO

from PIL import Image

from publishing_gateway.adapters.make_gateway import MakeGatewayAdapter
from publishing_gateway.output_image_gate import check_output_image


def _jpeg(*, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", (800, 1000), (20, 40, 60))
    output = BytesIO()
    exif = Image.Exif()
    if orientation is not None:
        exif[274] = orientation
    image.save(output, "JPEG", exif=exif)
    return output.getvalue()


def test_gate_rejects_exif_orientation_html_oversize_and_fetch_errors() -> None:
    fetch = lambda _: _jpeg(orientation=6)
    assert check_output_image("https://image.test/a.jpg", fetch) == ["OUTPUT_IMAGE_EXIF_ORIENTATION"]
    assert check_output_image("https://image.test/a.jpg", lambda _: b"<html>bad</html>") == [
        "OUTPUT_IMAGE_NOT_JPEG"
    ]
    assert check_output_image("https://image.test/a.jpg", lambda _: b"\xff\xd8\xff" + b"x" * (6 * 1024 * 1024)) == [
        "OUTPUT_IMAGE_TOO_LARGE"
    ]
    assert check_output_image("https://image.test/a.jpg", lambda _: (_ for _ in ()).throw(OSError())) == [
        "OUTPUT_IMAGE_FETCH_FAILED"
    ]


def test_gateway_does_not_post_when_image_gate_fails() -> None:
    posts: list[dict[str, object]] = []
    adapter = MakeGatewayAdapter(
        enabled=True,
        webhook_url="https://hook.test/synthetic",
        http_post=lambda *args, **kwargs: posts.append(kwargs) or {"raw": "Accepted"},
        image_fetch=lambda _: b"<html>bad</html>",
    )

    result = adapter.send(
        {
            "publication_id": "synthetic-pub",
            "idempotency_key": "synthetic-idempotency",
            "platform": "facebook",
            "content": {"image_public_url": "https://image.test/synthetic.jpg"},
        }
    )

    assert result["status"] == "GATEWAY_ERROR"
    assert result["error"] == "OUTPUT_IMAGE_NOT_JPEG"
    assert posts == []


def test_valid_jpeg_passes_the_legacy_gate() -> None:
    assert check_output_image("https://image.test/a.jpg", lambda _: _jpeg()) == []

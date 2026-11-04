from __future__ import annotations

import hashlib
import importlib.metadata
import warnings
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from growth_engine.application.dto import NormalizedImage
from growth_engine.domain.media.media_policy import MediaProfile, TransformSpec

MAX_INPUT_BYTES = 25 * 1024 * 1024
MAX_INPUT_PIXELS = 50_000_000
MEDIA_INPUT_TOO_LARGE = "MEDIA_INPUT_TOO_LARGE"
MEDIA_PIXEL_LIMIT_EXCEEDED = "MEDIA_PIXEL_LIMIT_EXCEEDED"
MEDIA_UNSUPPORTED_FORMAT = "MEDIA_UNSUPPORTED_FORMAT"
MEDIA_DECODE_FAILED = "MEDIA_DECODE_FAILED"
MEDIA_OUTPUT_TOO_LARGE = "MEDIA_OUTPUT_TOO_LARGE"
_SUPPORTED_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}


class MediaProcessingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PillowImageProcessor:
    """Decode untrusted image inputs and produce deterministic JPEG variants."""

    def normalize(self, original: Path, spec: TransformSpec) -> NormalizedImage:
        try:
            with original.open("rb") as stream:
                data = stream.read(MAX_INPUT_BYTES + 1)
        except OSError as exc:
            raise MediaProcessingError(MEDIA_DECODE_FAILED, "Cannot read image input") from exc
        if len(data) > MAX_INPUT_BYTES:
            raise MediaProcessingError(MEDIA_INPUT_TOO_LARGE, "Image input exceeds 25 MiB")

        expected_format = _detect_format(data)
        if expected_format is None:
            raise MediaProcessingError(MEDIA_UNSUPPORTED_FORMAT, "Image signature is unsupported")
        if expected_format == "HEIF":
            try:
                import pillow_heif

                pillow_heif.register_heif_opener()
            except ImportError as exc:
                raise MediaProcessingError(MEDIA_UNSUPPORTED_FORMAT, "HEIC decoding is unavailable") from exc

        image = _decode_fully(data, expected_format)
        oriented: Image.Image | None = None
        rgb: Image.Image | None = None
        background: Image.Image | None = None
        normalized: Image.Image | None = None
        try:
            oriented = ImageOps.exif_transpose(image)
            rgb = _to_srgb_rgb(oriented)
            background = Image.new("RGB", rgb.size, _parse_color(spec.background))
            if rgb.mode == "RGBA":
                background.paste(rgb, mask=rgb.getchannel("A"))
            else:
                background.paste(rgb)
            rgb.close()
            rgb = None
            normalized = background

            if spec.aspect_ratio.value == "pad_4_5":
                normalized = _pad_to_four_by_five(normalized, _parse_color(spec.background))
                background.close()
                background = None
            normalized.thumbnail(
                (spec.max_long_side_px, spec.max_long_side_px),
                Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            normalized.save(
                output,
                format="JPEG",
                quality=spec.jpeg_quality,
                progressive=True,
                optimize=True,
            )
            encoded = output.getvalue()
            output_width, output_height = normalized.size
        except MediaProcessingError:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise MediaProcessingError(MEDIA_PIXEL_LIMIT_EXCEEDED, "Image pixel limit exceeded") from exc
        except Exception as exc:
            raise MediaProcessingError(MEDIA_DECODE_FAILED, "Image could not be normalized") from exc
        finally:
            if normalized is not None:
                normalized.close()
            if background is not None:
                background.close()
            if rgb is not None:
                rgb.close()
            if oriented is not None and oriented is not image:
                oriented.close()
            image.close()

        if len(encoded) > spec.max_bytes:
            raise MediaProcessingError(MEDIA_OUTPUT_TOO_LARGE, "Normalized JPEG exceeds profile byte limit")
        _validate_output(encoded, spec)
        return NormalizedImage(
            data=encoded,
            width=output_width,
            height=output_height,
            sha256=hashlib.sha256(encoded).hexdigest(),
            mime="image/jpeg",
        )


def transform_version(profile: MediaProfile) -> str:
    """Return an immutable transform key incorporating the configured dependencies."""
    versions = {
        "profile": profile.name,
        "pillow_version": Image.__version__ if hasattr(Image, "__version__") else importlib.metadata.version("Pillow"),
        "pillow_heif_version": _distribution_version("pillow-heif"),
    }
    return "|".join(f"{name}={versions[name]}" for name in profile.spec.transform_version_includes)


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _detect_format(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if len(data) >= 16 and data[4:8] == b"ftyp":
        brands = {data[8:12]}
        brands.update(data[offset : offset + 4] for offset in range(16, min(len(data) - 3, 128), 4))
        if brands.intersection({b"avif", b"avis"}):
            return None
        if brands.intersection(_SUPPORTED_HEIF_BRANDS):
            return "HEIF"
    return None


def _decode_fully(data: bytes, expected_format: str) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as check:
                if check.format != expected_format:
                    raise MediaProcessingError(MEDIA_UNSUPPORTED_FORMAT, "Image signature and decoder format differ")
                if check.width * check.height > MAX_INPUT_PIXELS:
                    raise MediaProcessingError(MEDIA_PIXEL_LIMIT_EXCEEDED, "Image pixel limit exceeded")
                check.verify()
            with Image.open(BytesIO(data)) as opened:
                if opened.format != expected_format:
                    raise MediaProcessingError(MEDIA_UNSUPPORTED_FORMAT, "Image signature and decoder format differ")
                if opened.width * opened.height > MAX_INPUT_PIXELS:
                    raise MediaProcessingError(MEDIA_PIXEL_LIMIT_EXCEEDED, "Image pixel limit exceeded")
                opened.load()
                return opened.copy()
    except MediaProcessingError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise MediaProcessingError(MEDIA_PIXEL_LIMIT_EXCEEDED, "Image pixel limit exceeded") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise MediaProcessingError(MEDIA_DECODE_FAILED, "Image could not be fully decoded") from exc


def _to_srgb_rgb(image: Image.Image) -> Image.Image:
    icc = image.info.get("icc_profile")
    has_alpha = "A" in image.getbands() or "transparency" in image.info
    alpha_source = image.convert("RGBA") if has_alpha else None
    alpha = alpha_source.getchannel("A") if alpha_source is not None else None
    converted = image.convert("RGB") if has_alpha or image.mode == "P" else image
    if icc:
        try:
            source_profile = ImageCms.ImageCmsProfile(BytesIO(icc))
            srgb_profile = ImageCms.createProfile("sRGB")
            srgb = ImageCms.profileToProfile(converted, source_profile, srgb_profile, outputMode="RGB")
            if converted is not image:
                converted.close()
            converted = srgb
        except (ImageCms.PyCMSError, OSError, ValueError) as exc:
            if converted is not image:
                converted.close()
            if alpha is not None:
                alpha.close()
            if alpha_source is not None:
                alpha_source.close()
            raise MediaProcessingError(MEDIA_DECODE_FAILED, "Image color profile is invalid") from exc
    elif converted is image:
        converted = image.convert("RGB")
    if alpha is not None:
        converted.putalpha(alpha)
        alpha.close()
    if alpha_source is not None:
        alpha_source.close()
    return converted


def _pad_to_four_by_five(image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    width, height = image.size
    unit = max((width + 3) // 4, (height + 4) // 5)
    canvas = Image.new("RGB", (4 * unit, 5 * unit), color)
    canvas.paste(image, ((canvas.width - width) // 2, (canvas.height - height) // 2))
    return canvas


def _parse_color(value: str) -> tuple[int, int, int]:
    try:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise MediaProcessingError(MEDIA_DECODE_FAILED, "Image background color is invalid") from exc


def _validate_output(data: bytes, spec: TransformSpec) -> None:
    try:
        with Image.open(BytesIO(data)) as reopened:
            if reopened.format != "JPEG":
                raise MediaProcessingError(MEDIA_DECODE_FAILED, "Normalized output is not JPEG")
            reopened.load()
            if max(reopened.size) > spec.max_long_side_px:
                raise MediaProcessingError(MEDIA_DECODE_FAILED, "Normalized image dimensions exceed profile")
            if spec.aspect_ratio.value == "pad_4_5" and reopened.width * 5 != reopened.height * 4:
                raise MediaProcessingError(MEDIA_DECODE_FAILED, "Normalized Instagram image is not 4:5")
            if 274 in reopened.getexif():
                raise MediaProcessingError(MEDIA_DECODE_FAILED, "Normalized image retains EXIF orientation")
    except MediaProcessingError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MediaProcessingError(MEDIA_DECODE_FAILED, "Normalized output could not be decoded") from exc

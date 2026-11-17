from __future__ import annotations

from growth_engine.adapters.inbound.workers.content_jobs import _format_error
from growth_engine.adapters.outbound.media.local_legacy_image_library import LegacyImageValidationError


def test_content_job_error_keeps_machine_code_and_sanitized_message() -> None:
    error = ValueError(
        "download failed at https://drive.example.invalid/file?id=secret Authorization: Bearer EAA"
        + "A" * 64
    )

    safe = _format_error(error)

    assert safe.startswith("ERR_GC2_JOB_VALUE_ERROR: ")
    assert "download failed" in safe
    assert "[URL REDACTED]" in safe
    assert "[REDACTED]" in safe
    assert "EAA" not in safe
    assert "drive.example.invalid" not in safe


def test_content_job_preserves_media_error_code_and_public_message() -> None:
    class MediaError(RuntimeError):
        code = "MEDIA_DECODE_FAILED"
        public_message = "Image could not be normalized."

    safe = _format_error(MediaError("unfiltered private detail"))

    assert safe == "ERR_GC2_MEDIA_DECODE_FAILED: Image could not be normalized."
    assert "private detail" not in safe


def test_content_job_media_library_error_keeps_group_and_file_without_secret() -> None:
    error = LegacyImageValidationError(
        "ERR_GC2_LEGACY_IMAGE_INVALID",
        "Decode failed access_token=EAA" + "x" * 50,
        reference_id="venho_lobby_approved",
        relative_path="lobby/IMG_0001.jpeg",
    )

    safe = _format_error(error)

    assert safe.startswith("ERR_GC2_LEGACY_IMAGE_INVALID:")
    assert "group=venho_lobby_approved" in safe
    assert "file=lobby/IMG_0001.jpeg" in safe
    assert "EAA" not in safe
    assert "[REDACTED]" in safe

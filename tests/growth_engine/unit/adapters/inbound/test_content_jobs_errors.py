from __future__ import annotations

from growth_engine.adapters.inbound.workers.content_jobs import _format_error


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

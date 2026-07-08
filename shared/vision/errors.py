from __future__ import annotations


class VisionError(Exception):
    """Base error for all vision pipeline failures."""


class SchemaValidationError(VisionError):
    """AI returned JSON that does not match the expected schema."""

    def __init__(self, message: str, raw: str | None = None) -> None:
        super().__init__(message)
        self.raw = raw


class ProviderError(VisionError):
    """Error from the AI provider (API call failed)."""

    def __init__(self, message: str, provider: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class RetryExhausted(VisionError):
    """All retry attempts failed for a single image."""

    def __init__(self, image_file: str, attempts: int, last_error: Exception) -> None:
        super().__init__(f"Retry exhausted after {attempts} attempts for {image_file}: {last_error}")
        self.image_file = image_file
        self.attempts = attempts
        self.last_error = last_error


class ImageLoadError(VisionError):
    """Could not read or decode an image file."""

from __future__ import annotations


class ImageProviderTransientError(RuntimeError):
    def __init__(self, status_code: int, message: str = "transient image provider error") -> None:
        super().__init__(message)
        self.status_code = status_code


class MockImageProvider:
    model = "mock-image-provider"

    def __init__(self, *, fail_with_status: int | None = None) -> None:
        self.fail_with_status = fail_with_status
        self.calls = 0

    def generate(self, prompt: str, *, size: str, quality: str, reference_images: list[bytes] | None = None) -> bytes:
        self.calls += 1
        if self.fail_with_status:
            raise ImageProviderTransientError(self.fail_with_status)
        ref_note = f"refs={len(reference_images)}\n" if reference_images else ""
        return f"MOCK_IMAGE\nsize={size}\nquality={quality}\n{ref_note}prompt={prompt}\n".encode("utf-8")

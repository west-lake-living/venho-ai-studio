from abc import ABC, abstractmethod
from pathlib import Path


class BaseImageProvider(ABC):
    @abstractmethod
    def analyze_batch(self, images: list[Path], category: str) -> dict:
        """Phân tích một batch ảnh, trả về raw DNA dict."""
        ...


class BaseTextProvider(ABC):
    @abstractmethod
    def merge_knowledge(self, batch_results: list[dict], category: str) -> dict:
        """Tổng hợp nhiều batch DNA results thành một DNA dict cuối."""
        ...

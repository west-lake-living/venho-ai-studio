from pathlib import Path
from core.logger import log


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def load_images(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder không tồn tại: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Không phải folder: {folder}")

    images = sorted([
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    if not images:
        raise ValueError(f"Không tìm thấy ảnh nào trong: {folder}")

    log(f"Tìm thấy {len(images)} ảnh trong '{folder.name}'")
    for img in images:
        log(f"  • {img.name}")

    return images

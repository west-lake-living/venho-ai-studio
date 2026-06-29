from pathlib import Path
from core.logger import log


def make_batches(images: list[Path], batch_size: int = 5) -> list[list[Path]]:
    if batch_size < 1:
        raise ValueError("batch_size phải >= 1")

    batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]

    log(f"Chia thành {len(batches)} batch (batch_size={batch_size})")
    for i, batch in enumerate(batches, 1):
        names = ", ".join(p.name for p in batch)
        log(f"  Batch {i}/{len(batches)}: {names}")

    return batches

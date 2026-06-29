from pathlib import Path
from core.logger import log
from core.media_loader import load_images
from core.batch_manager import make_batches
from providers.openai_provider import OpenAIProvider


def extract_dna(folder: Path, category: str, batch_size: int, model: str = "gpt-4o") -> list[dict]:
    images = load_images(folder)
    batches = make_batches(images, batch_size)

    provider = OpenAIProvider(model=model)
    results = []

    for i, batch in enumerate(batches, 1):
        log(f"--- Batch {i}/{len(batches)} ---")
        result = provider.analyze_batch(batch, category)
        result["_batch_index"] = i
        result["_batch_images"] = [p.name for p in batch]
        results.append(result)

    log(f"Extraction hoàn tất: {len(results)} batch processed")
    return results

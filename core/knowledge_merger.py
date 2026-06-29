from core.logger import log
from providers.claude_provider import ClaudeProvider


def merge_dna(batch_results: list[dict], category: str, model: str = "claude-sonnet-4-6") -> dict:
    if not batch_results:
        raise ValueError("batch_results rỗng — không có gì để merge")

    if len(batch_results) == 1:
        log("Chỉ có 1 batch — skip merge, dùng trực tiếp")
        single = batch_results[0]
        single.pop("_batch_index", None)
        single.pop("_batch_images", None)
        return single

    log(f"Bắt đầu merge {len(batch_results)} batch results với Claude...")
    provider = ClaudeProvider(model=model)
    merged = provider.merge_knowledge(batch_results, category)
    log("Merge hoàn tất")
    return merged

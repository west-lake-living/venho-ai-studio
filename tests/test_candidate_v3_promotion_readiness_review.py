from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_candidate_v3_promotion_readiness_review.py"


def test_readiness_review_is_review_only_and_stops_on_unpinned_winner() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"qualityProviderCalls": 0' in source
    assert '"gpuJobs": 0' in source
    assert '"WINNING_CONFIG_NOT_PINNED"' in source
    assert '"NOT_READY_FOR_PROMOTION"' in source
    assert "runtimeBindsRequestParams" in source


def test_readiness_review_preserves_feature_and_promotion_safety() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"featureFlag": "OFF"' in source
    assert '"productionPromotion": "NO"' in source
    assert '"autoPromotionAllowed"' in source

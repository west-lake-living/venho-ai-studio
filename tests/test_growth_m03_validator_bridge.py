from __future__ import annotations

import growth_orchestrator.bridges.m03_validator_bridge as bridge_module
from growth_orchestrator.bridges.m03_validator_bridge import M03ValidatorBridge


def _brief(project: str = "venho_hotel") -> dict:
    return {"project": project, "visual": {"required_entities": [], "forbidden_entities": []}}


def _candidate(**overrides) -> dict:
    base = {
        "claims": [],
        "scene_summary": {},
        "content_package_paths": {"markdown": "some/path.md"},
        "dna_subject": "westlake",
        "platform": "facebook",
        "language": "vi",
    }
    base.update(overrides)
    return base


def test_validate_package_fails_closed_when_content_validator_raises(monkeypatch) -> None:
    """Part 2.1 invariant #8: validator fail/timeout/malformed input must
    fail-closed to UNVALIDATED, never silently pass through as READY_FOR_REVIEW.
    Regression test for the previously-unguarded validate_content() call."""

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated provider timeout")

    monkeypatch.setattr(bridge_module, "validate_content", _boom)

    result = M03ValidatorBridge().validate_package(_brief(), _candidate())

    assert result["verdict"] == "UNVALIDATED"


def test_validate_package_skips_content_report_when_markdown_path_missing() -> None:
    """No markdown/dna_subject/project -- content_report stays None, verdict
    driven only by claim/alignment (unchanged pre-existing behavior)."""
    result = M03ValidatorBridge().validate_package(_brief(), _candidate(content_package_paths={}))

    assert result["verdict"] == "READY_FOR_REVIEW"


def test_validate_package_scores_publishable_caption_not_markdown_scaffold(tmp_path) -> None:
    """Internal artifact metadata must not lower an otherwise valid caption."""
    markdown = tmp_path / "draft.md"
    markdown.write_text("internal metadata " * 600, encoding="utf-8")
    candidate = _candidate(
        content_package_paths={"markdown": str(markdown)},
        title="Một buổi chiều bên Hồ Tây",
        hook="Hồ Tây mang lại một nhịp nghỉ khác trong hành trình khám phá Hà Nội.",
        body=(
            "Từ phố Nguyễn Đình Thi, mặt hồ mở ra trong ánh sáng dịu. Ven Ho Hotel là "
            "một điểm dừng chân boutique mid-range gần nhịp sống địa phương, gọn gàng và "
            "ấm áp. Một khoảng nghỉ vừa đủ để bắt đầu hành trình Hà Nội nhẹ nhàng, rồi trở "
            "về sau những giờ khám phá thành phố."
        ),
        cta="Nhắn Ven Ho Hotel để kiểm tra phòng còn trống cho lịch của bạn.",
        hashtags=["#VenHoHotelHanoi", "#HoTay", "#HaNoi"],
    )

    result = M03ValidatorBridge().validate_package(_brief(), candidate)

    assert result["verdict"] == "READY_FOR_REVIEW"
    content_report = next(report for report in result["reports"] if report.get("validation_type") == "content")
    assert content_report["overall_score"] >= 90

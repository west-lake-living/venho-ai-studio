from __future__ import annotations

from content_studio.generators.social_prompts import build_user_message
from content_studio.schemas.content_request import ContentRequest


def _request(**overrides) -> ContentRequest:
    base = dict(
        content_type="facebook_post",
        topic="Đường Quảng An",
        project="venho_hotel",
        target_audience="Vietnamese leisure guests",
        content_pillar="context",
        tone="warm",
    )
    base.update(overrides)
    return ContentRequest(**base)


def test_theme_angle_values_are_interpolated_not_left_as_placeholders() -> None:
    request = _request(theme_angle={
        "angle_type": "practical",
        "premise": "Đường Quảng An đang mở rộng",
        "concrete_details": ["Đường Quảng An", "6h sáng", "Từ Hoa"],
        "guest_question": "Đường trước khách sạn có bị rào không?",
        "what_we_can_say": "Ven Hồ nằm ngay tuyến này nên biết rõ tình hình đi lại.",
        "what_we_cannot_claim": ["Mốc hoàn thành chưa có fact R3."],
    })
    message = build_user_message(request, "FINAL")

    assert "angle_type: practical" in message
    assert "Đường Quảng An đang mở rộng" in message
    assert "6h sáng" in message
    assert "Đường trước khách sạn có bị rào không?" in message
    # Regression: the Jinja-style "{{ angle_type }}" template was never
    # substituted by str.format and leaked literal braces into the prompt.
    assert "{" not in message and "}" not in message


def test_rewrite_feedback_block_lists_rule_ids() -> None:
    request = _request(
        rewrite_round=2,
        rewrite_feedback=[
            {"rule_id": "LX-OPEN", "message": "Mở bài bị cấm", "suggestion": "Mở bằng quan sát cụ thể"},
        ],
    )
    message = build_user_message(request, "FINAL")

    assert "rewrite_round: 2" in message
    assert "LX-OPEN" in message


def test_operator_copy_with_braces_does_not_break_assembly() -> None:
    request = _request(
        banned_phrases=["cụm {lạ} có ngoặc"],
        voice_exemplars=["Đoạn mẫu có ký tự { và } trong câu."],
    )
    message = build_user_message(request, "FINAL")

    assert "cụm {lạ} có ngoặc" in message
    assert "ký tự { và }" in message

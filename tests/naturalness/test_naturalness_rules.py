from __future__ import annotations

from validator_studio.naturalness.emoji_check import check_emoji
from validator_studio.naturalness.repetition_guard import check_repetition
from validator_studio.naturalness.specificity_check import specificity_score
from validator_studio.naturalness.structural_check import check_structure


def test_specificity_counts_local_place_time_and_object() -> None:
    text = "6 giờ sáng ở Nguyễn Đình Thi, mặt hồ Hồ Tây cạnh ban công phòng lake view."
    assert specificity_score(text) >= 4.0


def test_structural_gate_catches_question_opener_and_parallel_triple() -> None:
    findings = check_structure("Bạn đã đến Hồ Tây chưa? Yên bình, thư thái, gần gũi.")
    assert {item.rule_id for item in findings} >= {"ST-02", "ST-01"}


def test_repetition_gate_catches_exact_reuse() -> None:
    old = "6 giờ sáng ở Hồ Tây. Nguyễn Đình Thi còn vắng và mặt hồ phẳng."
    findings = check_repetition(old, [old])
    assert any(item.rule_id in {"RP-01", "RP-02"} for item in findings)


def test_emoji_gate_catches_machine_pattern() -> None:
    findings = check_emoji("🌿 Một ý\n🌊 Hai ý\n☕ Ba ý")
    assert any(item.rule_id == "EM-01" for item in findings)
